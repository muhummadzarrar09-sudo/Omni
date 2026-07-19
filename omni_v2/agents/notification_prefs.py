"""
OMNI V3 - Notification Preferences (Phase 5E)

User-controlled notification settings:
  - Per-category mute (info, success, warn, error, etc.)
  - Do-Not-Disturb hours (e.g. 10pm-7am, no notifications)
  - Daily limit per category
  - Snooze duration (mute all for N minutes)
  - Quiet mode toggle
  - Auto-mark-read on view

Persistent JSON. Thread-safe. Singleton.

This module complements notifications.py by adding USER PREFERENCES
on top of the raw notification stream.
"""
from __future__ import annotations
import json
import time
import threading
import tempfile
import os
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("NotifPrefs")


# Default preferences
DEFAULTS = {
    "enabled": True,                # Global on/off
    "muted_categories": [],         # categories to suppress
    "category_limits": {            # max notifications per category per day
        "info": 50,
        "success": 30,
        "warn": 20,
        "error": 100,
        "action_required": 100,
        "geofence": 30,
        "proactive": 20,
        "schedule": 30,
        "wake": 50,
        "tool": 50,
    },
    "dnd_enabled": False,
    "dnd_start_hour": 22,           # 10pm
    "dnd_end_hour": 7,              # 7am
    "dnd_days": [0, 1, 2, 3, 4, 5, 6],  # every day
    "snoozed_until": 0.0,           # timestamp; suppress all until then
    "auto_mark_read_on_view": True,
    "play_sound": True,
    "vibrate": True,
    "show_preview": True,           # show notification body (vs just title)
    "group_by_category": True,
    "min_priority": 0,              # 0=show all, 3=only urgent
    "tag_filters": [],              # only show these tags (empty = all)
    "tag_blocklist": [],            # never show these tags
    "version": 1,
}


@dataclass
class SnoozeState:
    """Active snooze."""
    until: float           # Unix timestamp
    reason: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def is_active(self) -> bool:
        return time.time() < self.until

    @property
    def remaining_sec(self) -> float:
        return max(0, self.until - time.time())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NotificationPrefs:
    """Singleton, persistent, thread-safe."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: Optional[Path] = None):
        if self._initialized:
            return
        try:
            from omni_v2.core.paths import DATA_DIR
            base = Path(DATA_DIR) if not isinstance(DATA_DIR, str) else Path(DATA_DIR)
        except Exception:
            base = Path.cwd() / "data"
        self.data_dir = (data_dir or (base / "notifications"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.prefs_file = self.data_dir / "preferences.json"
        self.snooze_file = self.data_dir / "snooze.json"
        self._data_lock = threading.RLock()
        self.prefs: Dict[str, Any] = {}
        self.snooze: Optional[SnoozeState] = None
        # Stats: per-day count per category (for limit checking)
        self._daily_counts: Dict[str, Dict[str, int]] = {}  # {date: {category: count}}
        self._last_reset_date: str = ""
        self._load()
        self._initialized = True
        logger.info(f"⚙️ NotificationPrefs loaded (enabled={self.prefs.get('enabled')}, dnd={self.prefs.get('dnd_enabled')})")

    # ===== Persistence =====

    def _load(self):
        with self._data_lock:
            try:
                if self.prefs_file.exists():
                    raw = json.loads(self.prefs_file.read_text(encoding="utf-8"))
                    # Merge with defaults so missing keys get filled
                    self.prefs = {**DEFAULTS, **raw}
                else:
                    self.prefs = dict(DEFAULTS)
            except Exception as e:
                logger.warning(f"Load prefs: {e}")
                self.prefs = dict(DEFAULTS)
            try:
                if self.snooze_file.exists():
                    raw = json.loads(self.snooze_file.read_text(encoding="utf-8"))
                    self.snooze = SnoozeState(**raw) if raw else None
            except Exception as e:
                logger.debug(f"Load snooze: {e}")
                self.snooze = None

    def _save_prefs(self):
        with self._data_lock:
            self._atomic_write(self.prefs_file, self.prefs)

    def _save_snooze(self):
        with self._data_lock:
            if self.snooze:
                self._atomic_write(self.snooze_file, self.snooze.to_dict())
            else:
                try: self.snooze_file.unlink()
                except Exception: pass

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
            logger.error(f"Prefs write failed: {e}")

    # ===== Preferences =====

    def get(self, key: str, default: Any = None) -> Any:
        with self._data_lock:
            return self.prefs.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        if key not in DEFAULTS and key not in ("version",):
            logger.warning(f"Unknown pref key: {key}")
            return False
        with self._data_lock:
            self.prefs[key] = value
            self._save_prefs()
        return True

    def update(self, **kwargs) -> Dict[str, bool]:
        """Update preferences in one locked write."""
        with self._data_lock:
            results = {k: (k in DEFAULTS or k == "version") for k in kwargs}
            if not all(results.values()):
                return results
            self.prefs.update(kwargs)
            self._save_prefs()
            return results

    def reset_all(self) -> None:
        with self._data_lock:
            self.prefs = dict(DEFAULTS)
            self._save_prefs()

    def get_all(self) -> Dict[str, Any]:
        with self._data_lock:
            return dict(self.prefs)

    # ===== Snooze =====

    def snooze_for(self, minutes: float, reason: str = "") -> SnoozeState:
        """Mute all notifications for N minutes."""
        until = time.time() + (minutes * 60)
        with self._data_lock:
            self.snooze = SnoozeState(until=until, reason=reason)
            self._save_snooze()
        logger.info(f"🔕 Snoozed for {minutes} min (until {time.strftime('%H:%M', time.localtime(until))})")
        return self.snooze

    def unsnooze(self) -> bool:
        with self._data_lock:
            if self.snooze and self.snooze.is_active:
                self.snooze = None
                self._save_snooze()
                return True
        return False

    def get_snooze(self) -> Optional[SnoozeState]:
        # Auto-cleanup expired
        with self._data_lock:
            if self.snooze and not self.snooze.is_active:
                self.snooze = None
                self._save_snooze()
            return self.snooze

    # ===== Should-notify logic =====

    def should_notify(self, category: str, priority: int = 1, tag: str = "") -> bool:
        """Returns True if a notification with these attributes should be shown."""
        with self._data_lock:
            # Global off
            if not self.prefs.get("enabled", True):
                return False
            # Snoozed
            if self.snooze and self.snooze.is_active:
                return False
            # Min priority
            min_prio = self.prefs.get("min_priority", 0)
            if priority < min_prio:
                return False
            # Category muted
            if category in self.prefs.get("muted_categories", []):
                return False
            # DND
            if self._in_dnd_window():
                return False
            # Tag filter
            tag_blocklist = self.prefs.get("tag_blocklist", [])
            if tag and tag in tag_blocklist:
                return False
            tag_filters = self.prefs.get("tag_filters", [])
            if tag_filters and tag and tag not in tag_filters:
                return False
            # Daily limit
            limit = self.prefs.get("category_limits", {}).get(category, 100)
            if self._get_daily_count(category) >= limit:
                return False
            return True

    def _in_dnd_window(self) -> bool:
        if not self.prefs.get("dnd_enabled", False):
            return False
        from datetime import datetime
        now = datetime.now()
        # Day of week (0=Mon)
        if now.weekday() not in self.prefs.get("dnd_days", list(range(7))):
            return False
        start = self.prefs.get("dnd_start_hour", 22)
        end = self.prefs.get("dnd_end_hour", 7)
        h = now.hour
        if start <= end:
            return start <= h < end
        else:  # crosses midnight
            return h >= start or h < end

    def _get_daily_count(self, category: str) -> int:
        """Get count of notifications for category today."""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._last_reset_date:
            self._daily_counts = {}
            self._last_reset_date = today
        return self._daily_counts.get(today, {}).get(category, 0)

    def record_sent(self, category: str) -> None:
        """Increment the daily count for this category."""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_reset_date != today:
            # New day — reset
            self._daily_counts = {}
            self._last_reset_date = today
        if today not in self._daily_counts:
            self._daily_counts[today] = {}
        self._daily_counts[today][category] = self._daily_counts[today].get(category, 0) + 1
        # Prune old days
        if len(self._daily_counts) > 30:
            self._daily_counts = {k: v for k, v in self._daily_counts.items() if k >= today}

    # ===== Status =====

    def get_status(self) -> Dict[str, Any]:
        with self._data_lock:
            snooze = self.snooze
            return {
                "enabled": self.prefs.get("enabled"),
                "dnd_active": self._in_dnd_window(),
                "snoozed": snooze.is_active if snooze else False,
                "snooze_remaining_sec": snooze.remaining_sec if snooze and snooze.is_active else 0,
                "muted_categories": list(self.prefs.get("muted_categories", [])),
                "min_priority": self.prefs.get("min_priority"),
                "category_limits": self.prefs.get("category_limits", {}),
                "today_counts": dict(self._daily_counts.get(self._last_reset_date, {})),
            }

    def get_full_dashboard(self) -> Dict[str, Any]:
        return {
            "prefs": self.get_all(),
            "snooze": self.snooze.to_dict() if self.snooze and self.snooze.is_active else None,
            "status": self.get_status(),
        }


def get_notification_prefs() -> NotificationPrefs:
    return NotificationPrefs()


# ---------- Filter helper ----------

def filter_and_record(notification, prefs: Optional[NotificationPrefs] = None) -> bool:
    """Returns True if the notification should be delivered (and records it)."""
    p = prefs or get_notification_prefs()
    if p.should_notify(notification.category, notification.priority, notification.tag):
        p.record_sent(notification.category)
        return True
    return False
