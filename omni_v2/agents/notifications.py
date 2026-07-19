"""
OMNI V3 - Notification Center (Phase 5D)

In-app + push notifications for OMNI.

The notification center:
  - Stores notifications in a persistent JSON log (no external service)
  - Broadcasts to all connected WebSocket clients (real-time)
  - Optionally pushes to web (VAPID) if a public key is configured
  - Categorizes: info / success / warn / error / action_required
  - Tracks read/unread state
  - Per-device delivery state

Web Push:
  - Uses standard Web Push API (RFC 8030) with VAPID
  - VAPID keys can be auto-generated on first run
  - Phone subscribes via the mobile PWA
  - Server pushes via the pywebpush library (if installed)
  - Falls back to WebSocket-only if not configured

In-app inbox:
  - /api/notifications — list, filter, mark read
  - /api/notifications/{id}/read — mark single as read
  - /api/notifications/read-all — mark all as read
  - /api/notifications/vapid — get VAPID public key for subscription
  - /api/notifications/subscribe — store a device push subscription
  - /api/notifications/unsubscribe — remove a device's subscription
"""
from __future__ import annotations
import json
import time
import threading
import tempfile
import os
import secrets
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger("Notifications")


# Categories
CAT_INFO = "info"
CAT_SUCCESS = "success"
CAT_WARN = "warn"
CAT_ERROR = "error"
CAT_ACTION = "action_required"
CAT_GEOFENCE = "geofence"
CAT_PROACTIVE = "proactive"
CAT_SCHEDULE = "schedule"
CAT_WAKE = "wake"
CAT_TOOL = "tool"

VALID_CATEGORIES = {CAT_INFO, CAT_SUCCESS, CAT_WARN, CAT_ERROR, CAT_ACTION,
                    CAT_GEOFENCE, CAT_PROACTIVE, CAT_SCHEDULE, CAT_WAKE, CAT_TOOL}


@dataclass
class Notification:
    """A single notification."""
    id: str
    title: str
    body: str
    category: str = CAT_INFO
    priority: int = 1              # 0=low, 1=normal, 2=high, 3=urgent
    icon: str = "🔔"
    tag: str = ""                  # For grouping (e.g. "geofence_home")
    data: Dict[str, Any] = field(default_factory=dict)  # arbitrary payload
    actions: List[Dict[str, str]] = field(default_factory=list)  # [label, command]
    url: str = ""                  # optional link
    ts: float = field(default_factory=time.time)
    expires_at: float = 0.0        # 0 = never
    read: bool = False
    read_at: float = 0.0
    delivered_to: List[str] = field(default_factory=list)  # device_ids
    webpush_sent: bool = False
    # For grouping/dedup
    dedup_key: str = ""            # If set, replaces existing with same key

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at


@dataclass
class DeviceSubscription:
    """A device's web-push subscription endpoint."""
    device_id: str
    endpoint: str
    p256dh: str                    # encryption key
    auth: str                      # auth secret
    user_agent: str = ""
    paired: bool = False
    capabilities: List[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    failed_count: int = 0          # consecutive delivery failures

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Max notifications to keep
MAX_NOTIFICATIONS = 500

# VAPID key length
VAPID_KEY_LENGTH = 32  # bytes (base64url-encoded to 43 chars)


def generate_vapid_keys() -> Dict[str, str]:
    """
    Generate a VAPID key pair for Web Push.
    Returns: {"public_key": "...", "private_key": "..."}
    Both keys are base64url-encoded (no padding).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        import base64

        key = ec.generate_private_key(ec.SECP256R1())
        priv_bytes = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # We need the raw private key (32 bytes) for pywebpush
        priv_raw = key.private_numbers().private_value.to_bytes(32, "big")
        pub_raw = key.public_key().public_numbers().x.to_bytes(32, "big") + \
                  key.public_key().public_numbers().y.to_bytes(32, "big")
        return {
            "private_key": base64.urlsafe_b64encode(priv_raw).rstrip(b"=").decode("ascii"),
            "public_key": base64.urlsafe_b64encode(pub_raw).rstrip(b"=").decode("ascii"),
        }
    except ImportError:
        # cryptography not installed — return random placeholder
        # Real webpush won't work but the in-app flow does
        return {
            "private_key": secrets.token_urlsafe(43),
            "public_key": secrets.token_urlsafe(43),
        }


class NotificationCenter:
    """
    Singleton. Thread-safe. Persistent.
    Receives notifications, broadcasts via WS, optionally pushes via web.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: Optional[Path] = None, vapid_subject: str = "mailto:[email protected]"):
        if self._initialized:
            return
        try:
            from omni_v2.core.paths import DATA_DIR
            base = Path(DATA_DIR) if not isinstance(DATA_DIR, str) else Path(DATA_DIR)
        except Exception:
            base = Path.cwd() / "data"
        self.data_dir = (data_dir or (base / "notifications"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.notif_file = self.data_dir / "notifications.json"
        self.devices_file = self.data_dir / "devices.json"
        self.vapid_file = self.data_dir / "vapid.json"

        self._data_lock = threading.RLock()
        self.notifications: List[Notification] = []
        self.devices: Dict[str, DeviceSubscription] = {}
        self.vapid: Dict[str, str] = {}

        # WebSocket broadcast hook (set by backend)
        self.broadcast: Optional[Callable[[Dict[str, Any]], Any]] = None

        self._load()
        # Auto-generate VAPID if missing
        if not self.vapid:
            self._generate_vapid()
        self._initialized = True
        logger.info(f"🔔 Notification center: {len(self.notifications)} notifs, {len(self.devices)} devices")

    def shutdown(self) -> None:
        """Detach delivery callbacks during application shutdown."""
        with self._data_lock:
            self.broadcast = None
            self._save_notifications()
            self._save_devices()

    # ===== Persistence =====

    def _load(self):
        with self._data_lock:
            try:
                if self.notif_file.exists():
                    raw = json.loads(self.notif_file.read_text(encoding="utf-8"))
                    self.notifications = [Notification(**n) for n in raw[-MAX_NOTIFICATIONS:]]
            except Exception as e:
                logger.warning(f"Load notifications: {e}")
            try:
                if self.devices_file.exists():
                    raw = json.loads(self.devices_file.read_text(encoding="utf-8"))
                    for d in raw:
                        try:
                            self.devices[d["device_id"]] = DeviceSubscription(**d)
                        except Exception as e:
                            logger.debug(f"Skip bad device: {e}")
            except Exception as e:
                logger.warning(f"Load devices: {e}")
            try:
                if self.vapid_file.exists():
                    self.vapid = json.loads(self.vapid_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.debug(f"No VAPID: {e}")

    def _save_notifications(self):
        with self._data_lock:
            self.notifications = [n for n in self.notifications if not n.is_expired]
            self.notifications = self.notifications[-MAX_NOTIFICATIONS:]
            self._atomic_write(self.notif_file, [n.to_dict() for n in self.notifications])

    def _save_devices(self):
        with self._data_lock:
            self._atomic_write(self.devices_file, [d.to_dict() for d in self.devices.values()])

    def _save_vapid(self):
        with self._data_lock:
            self._atomic_write(self.vapid_file, self.vapid)

    def _atomic_write(self, path: Path, data: Any):
        try:
            fd, tmp = tempfile.mkstemp(
                dir=str(self.data_dir), prefix=f".{path.stem}_", suffix=".json.tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(tmp, path)
            except Exception:
                try: os.unlink(tmp)
                except Exception: pass
                raise
        except Exception as e:
            logger.error(f"Notification write failed: {e}")

    def _generate_vapid(self):
        try:
            keys = generate_vapid_keys()
            self.vapid = {
                "public_key": keys["public_key"],
                "private_key": keys["private_key"],
                "subject": "mailto:[email protected]",
            }
            self._save_vapid()
            logger.info(f"🔑 VAPID keys generated (pub={keys['public_key'][:20]}...)")
        except Exception as e:
            logger.warning(f"VAPID gen failed: {e}")

    # ===== Notification creation =====

    def notify(self, title: str, body: str = "", category: str = CAT_INFO,
               priority: int = 1, icon: str = "🔔", tag: str = "",
               data: Optional[Dict] = None, actions: Optional[List[Dict]] = None,
               url: str = "", expires_sec: float = 0,
               dedup_key: str = "", device_id: Optional[str] = None,
               skip_prefs: bool = False) -> Notification:
        """
        Create and broadcast a notification.
        If dedup_key is set, replaces existing notification with same key.
        If device_id is set, only sends to that device.
        If skip_prefs is True, bypasses user preferences (e.g. for critical alerts).
        """
        if category not in VALID_CATEGORIES:
            category = CAT_INFO
        if priority < 0: priority = 0
        if priority > 3: priority = 3
        # Check user preferences (Phase 5E)
        if not skip_prefs:
            try:
                from omni_v2.agents.notification_prefs import get_notification_prefs
                prefs = get_notification_prefs()
                if not prefs.should_notify(category, priority, tag):
                    logger.debug(f"Notification suppressed by prefs: {title!r} ({category})")
                    # Still create a "suppressed" record? No, just skip
                    # Create a placeholder notif so the user can see it was blocked
                    notif = Notification(
                        id=f"n_{secrets.token_hex(4)}",
                        title=title, body=body, category=category, priority=priority,
                        icon=icon, tag=tag, data=data or {}, actions=actions or [],
                        url=url, expires_at=(time.time() + expires_sec) if expires_sec > 0 else 0,
                        dedup_key=dedup_key,
                    )
                    notif.read = True
                    notif.read_at = time.time()
                    notif.data["__suppressed__"] = True
                    with self._data_lock:
                        self.notifications.append(notif)
                        self._save_notifications()
                    return notif
                # Record that we sent this (for daily limits)
                prefs.record_sent(category)
            except Exception as e:
                logger.debug(f"Prefs check failed: {e}")
        # Dedup
        if dedup_key:
            for i, n in enumerate(self.notifications):
                if n.dedup_key == dedup_key:
                    n.title = title
                    n.body = body
                    n.ts = time.time()
                    n.read = False
                    n.read_at = 0.0
                    n.priority = priority
                    self._save_notifications()
                    self._broadcast(n, device_id=device_id)
                    return n
        notif = Notification(
            id=f"n_{secrets.token_hex(4)}",
            title=title, body=body, category=category, priority=priority,
            icon=icon, tag=tag, data=data or {}, actions=actions or [],
            url=url, expires_at=(time.time() + expires_sec) if expires_sec > 0 else 0,
            dedup_key=dedup_key,
        )
        with self._data_lock:
            self.notifications.append(notif)
            self._save_notifications()
        self._broadcast(notif, device_id=device_id)
        return notif

    def _broadcast(self, notif: Notification, device_id: Optional[str] = None):
        """Broadcast via WS + try web push."""
        import asyncio
        payload = {
            "type": "notification",
            "notification": notif.to_dict(),
            "ts": time.time(),
        }
        # WebSocket broadcast (to all or specific device)
        if self.broadcast:
            try:
                if asyncio.iscoroutinefunction(self.broadcast):
                    # Schedule the coroutine
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.ensure_future(self.broadcast(payload, device_id=device_id))
                    except RuntimeError:
                        # No running loop (test mode) — skip
                        pass
                else:
                    # Sync callback (used in tests + dev)
                    self.broadcast(payload, device_id=device_id)
            except Exception as e:
                logger.debug(f"WS broadcast failed: {e}")
        # Web push (best-effort)
        if notif.priority >= 2:
            self._webpush(notif, device_id=device_id)

    def _webpush(self, notif: Notification, device_id: Optional[str] = None):
        """Send web push to subscribed devices."""
        try:
            from pywebpush import webpush, WebPushException
        except ImportError:
            return  # not installed
        if not self.vapid or not self.vapid.get("private_key"):
            return
        payload = json.dumps({
            "title": notif.title,
            "body": notif.body,
            "icon": notif.icon,
            "tag": notif.tag,
            "data": notif.data,
            "url": notif.url,
        })
        targets = [d for d in self.devices.values()
                   if (device_id is None or d.device_id == device_id)
                   and d.failed_count < 5]
        for d in targets:
            try:
                webpush(
                    subscription_info={
                        "endpoint": d.endpoint,
                        "keys": {"p256dh": d.p256dh, "auth": d.auth},
                    },
                    data=payload,
                    vapid_private_key=self.vapid["private_key"],
                    vapid_claims={"sub": self.vapid.get("subject", "mailto:[email protected]")},
                )
                d.last_seen = time.time()
                d.failed_count = 0
                notif.webpush_sent = True
            except WebPushException as e:
                d.failed_count += 1
                logger.debug(f"Web push failed for {d.device_id}: {e}")
            except Exception as e:
                logger.debug(f"Web push error: {e}")
        self._save_devices()
        self._save_notifications()

    # ===== Device registry =====

    def register_device(self, device_id: str, endpoint: str, p256dh: str, auth: str,
                        user_agent: str = "", paired: bool = False,
                        capabilities: Optional[List[str]] = None) -> DeviceSubscription:
        with self._data_lock:
            d = self.devices.get(device_id) or DeviceSubscription(
                device_id=device_id, endpoint=endpoint, p256dh=p256dh, auth=auth,
                user_agent=user_agent, paired=paired, capabilities=capabilities or [],
            )
            d.endpoint = endpoint
            d.p256dh = p256dh
            d.auth = auth
            d.user_agent = user_agent[:300]
            d.paired = paired
            d.capabilities = capabilities or d.capabilities
            d.last_seen = time.time()
            d.failed_count = 0
            self.devices[device_id] = d
            self._save_devices()
        logger.info(f"📱 Device registered: {device_id} (paired={paired})")
        return d

    def touch_device(self, device_id: str, capabilities: Optional[List[str]] = None):
        """Update last_seen (called by WS heartbeat)."""
        with self._data_lock:
            d = self.devices.get(device_id)
            if d:
                d.last_seen = time.time()
                if capabilities:
                    d.capabilities = list(set(d.capabilities + capabilities))
                # Don't save every touch — too much IO
                if int(time.time()) % 30 == 0:
                    self._save_devices()

    def unregister_device(self, device_id: str) -> bool:
        with self._data_lock:
            if device_id in self.devices:
                del self.devices[device_id]
                self._save_devices()
                return True
        return False

    def list_devices(self) -> List[DeviceSubscription]:
        with self._data_lock:
            return sorted(self.devices.values(), key=lambda d: -d.last_seen)

    def get_device(self, device_id: str) -> Optional[DeviceSubscription]:
        return self.devices.get(device_id)

    # ===== Inbox =====

    def list_notifications(self, limit: int = 50, category: Optional[str] = None,
                           unread_only: bool = False) -> List[Notification]:
        with self._data_lock:
            # Filter out expired first
            items = [n for n in self.notifications if not n.is_expired]
            if category:
                items = [n for n in items if n.category == category]
            if unread_only:
                items = [n for n in items if not n.read]
            items.sort(key=lambda n: -n.ts)
            return items[:limit]

    def get_notification(self, notif_id: str) -> Optional[Notification]:
        with self._data_lock:
            for n in self.notifications:
                if n.id == notif_id:
                    return n
        return None

    def mark_read(self, notif_id: str) -> bool:
        with self._data_lock:
            for n in self.notifications:
                if n.id == notif_id and not n.read:
                    n.read = True
                    n.read_at = time.time()
                    self._save_notifications()
                    return True
        return False

    def mark_all_read(self, category: Optional[str] = None) -> int:
        count = 0
        with self._data_lock:
            for n in self.notifications:
                if not n.read and (not category or n.category == category):
                    n.read = True
                    n.read_at = time.time()
                    count += 1
            if count:
                self._save_notifications()
        return count

    def clear(self, category: Optional[str] = None) -> int:
        with self._data_lock:
            before = len(self.notifications)
            if category:
                self.notifications = [n for n in self.notifications if n.category != category]
            else:
                self.notifications = []
            self._save_notifications()
            return before - len(self.notifications)

    def get_unread_count(self, category: Optional[str] = None) -> int:
        with self._data_lock:
            return sum(1 for n in self.notifications
                       if not n.read and (not category or n.category == category))

    # ===== VAPID =====

    def get_vapid_public_key(self) -> Optional[str]:
        if not self.vapid:
            return None
        return self.vapid.get("public_key")

    def get_vapid_info(self) -> Dict[str, Any]:
        return {
            "public_key": self.get_vapid_public_key(),
            "subject": self.vapid.get("subject", ""),
            "enabled": bool(self.vapid.get("private_key")),
        }

    # ===== Status =====

    def get_status(self) -> Dict[str, Any]:
        with self._data_lock:
            return {
                "notifications_count": len(self.notifications),
                "unread_count": self.get_unread_count(),
                "devices_count": len(self.devices),
                "vapid_enabled": bool(self.vapid.get("private_key")),
                "data_dir": str(self.data_dir),
            }

    def get_full_dashboard(self) -> Dict[str, Any]:
        return {
            "notifications": [n.to_dict() for n in self.list_notifications(limit=100)],
            "unread_count": self.get_unread_count(),
            "devices": [d.to_dict() for d in self.list_devices()],
            "vapid": self.get_vapid_info(),
            "status": self.get_status(),
        }


def get_notification_center() -> NotificationCenter:
    return NotificationCenter()


# Convenience helpers (callers don't need to know about the singleton)
def push_notification(title: str, body: str = "", **kwargs) -> Notification:
    """Quick helper: get the center and notify."""
    return get_notification_center().notify(title, body, **kwargs)
