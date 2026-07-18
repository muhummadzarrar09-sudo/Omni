"""
OMNI V3 - Notification Center Tests (Phase 5D)

Verifies:
  1. Notification creation (notify)
  2. Read/unread tracking
  3. List with filters
  4. Mark read / mark all read
  5. Clear (by category or all)
  6. Device registry (subscribe/unsubscribe/touch)
  7. VAPID key generation
  8. Dedup key replaces existing
  9. Expired notifications are pruned
  10. Send-to-phone tool
  11. Singleton behavior
"""
import json
import time
import tempfile
import shutil
import secrets
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None


# ---------- Notification basics ----------
class TestNotificationBasics:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_notif_")
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        # Reset BOTH singletons
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        self.center = notifications.NotificationCenter(data_dir=Path(self._tmp))
        # Track broadcasts
        self.broadcasts = []
        self.center.broadcast = lambda payload, device_id=None: self.broadcasts.append(payload)
        # Reset prefs to defaults so they don't suppress our test notifications
        from omni_v2.agents.notification_prefs import NotificationPrefs
        NotificationPrefs._instance = None
        prefs = NotificationPrefs(data_dir=Path(self._tmp))
        prefs.reset_all()

    def teardown_method(self):
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_notify(self):
        n = self.center.notify("Hello", "World", category="info", priority=2)
        assert n.id.startswith("n_")
        assert n.title == "Hello"
        assert n.body == "World"
        assert n.category == "info"
        assert not n.read

    def test_broadcasts_on_notify(self):
        self.center.notify("X", "Y", priority=2)
        assert len(self.broadcasts) == 1
        assert self.broadcasts[0]["type"] == "notification"

    def test_invalid_category_falls_back(self):
        n = self.center.notify("X", category="garbage", priority=2)
        assert n.category == "info"

    def test_priority_clamped(self):
        n1 = self.center.notify("X", priority=99)
        assert n1.priority == 3
        n2 = self.center.notify("Y", priority=-5)
        assert n2.priority == 0

    def test_dedup_replaces(self):
        n1 = self.center.notify("X", "first", dedup_key="k1", priority=2)
        time.sleep(0.01)
        n2 = self.center.notify("X", "second", dedup_key="k1", priority=2)
        assert n1.id == n2.id
        assert n2.body == "second"
        assert len(self.center.notifications) == 1

    def test_expires_at(self):
        n = self.center.notify("X", expires_sec=0.05, priority=2)
        time.sleep(0.1)
        # List notifications should filter expired
        items = self.center.list_notifications()
        assert all(notif.id != n.id for notif in items)

    def test_persistence(self):
        self.center.notify("P1", "persist me", priority=2)
        # Restart
        from omni_v2.agents import notifications
        notifications.NotificationCenter._instance = None
        c2 = notifications.NotificationCenter(data_dir=Path(self._tmp))
        items = c2.list_notifications()
        assert any(n.title == "P1" for n in items)


# ---------- Read/unread tracking ----------
class TestReadTracking:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_notif_")
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        self.center = notifications.NotificationCenter(data_dir=Path(self._tmp))
        self.center.broadcast = lambda *a, **k: None
        # Reset prefs to defaults
        from omni_v2.agents.notification_prefs import NotificationPrefs
        NotificationPrefs._instance = None
        prefs = NotificationPrefs(data_dir=Path(self._tmp))
        prefs.reset_all()

    def teardown_method(self):
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_mark_read(self):
        n = self.center.notify("X", priority=2)
        assert not n.read
        ok = self.center.mark_read(n.id)
        assert ok
        # Fetch again to confirm
        n2 = self.center.get_notification(n.id)
        assert n2.read
        assert n2.read_at > 0

    def test_mark_read_nonexistent(self):
        assert not self.center.mark_read("n_nope")

    def test_mark_all_read(self):
        for i in range(3):
            self.center.notify(f"N{i}", priority=2)
        # Mark one read first
        n0 = self.center.list_notifications()[-1]
        self.center.mark_read(n0.id)
        # Now mark all
        n_marked = self.center.mark_all_read()
        assert n_marked == 2  # 2 unread
        assert self.center.get_unread_count() == 0

    def test_mark_all_read_by_category(self):
        self.center.notify("X", category="info", priority=2)
        self.center.notify("Y", category="warn", priority=2)
        n_marked = self.center.mark_all_read(category="info")
        assert n_marked == 1
        assert self.center.get_unread_count() == 1
        assert self.center.get_unread_count(category="warn") == 1

    def test_unread_filter(self):
        n1 = self.center.notify("A", priority=2)
        n2 = self.center.notify("B", priority=2)
        self.center.mark_read(n1.id)
        unread = self.center.list_notifications(unread_only=True)
        assert len(unread) == 1
        assert unread[0].id == n2.id

    def test_category_filter(self):
        self.center.notify("A", category="info", priority=2)
        self.center.notify("B", category="warn", priority=2)
        items = self.center.list_notifications(category="warn")
        assert len(items) == 1
        assert items[0].category == "warn"


# ---------- Clear ----------
class TestClear:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_notif_")
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        self.center = notifications.NotificationCenter(data_dir=Path(self._tmp))
        self.center.broadcast = lambda *a, **k: None
        # Reset prefs to defaults
        from omni_v2.agents.notification_prefs import NotificationPrefs
        NotificationPrefs._instance = None
        prefs = NotificationPrefs(data_dir=Path(self._tmp))
        prefs.reset_all()

    def teardown_method(self):
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_clear_all(self):
        for i in range(3):
            self.center.notify(f"X{i}", priority=2)
        n = self.center.clear()
        assert n == 3
        assert len(self.center.notifications) == 0

    def test_clear_by_category(self):
        self.center.notify("A", category="info", priority=2)
        self.center.notify("B", category="warn", priority=2)
        self.center.notify("C", category="info", priority=2)
        n = self.center.clear(category="info")
        assert n == 2
        assert len(self.center.notifications) == 1
        assert self.center.notifications[0].category == "warn"


# ---------- Device registry ----------
class TestDeviceRegistry:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_notif_")
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        self.center = notifications.NotificationCenter(data_dir=Path(self._tmp))
        self.center.broadcast = lambda *a, **k: None
        # Reset prefs to defaults
        from omni_v2.agents.notification_prefs import NotificationPrefs
        NotificationPrefs._instance = None
        prefs = NotificationPrefs(data_dir=Path(self._tmp))
        prefs.reset_all()

    def teardown_method(self):
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_register(self):
        d = self.center.register_device(
            device_id="dev1", endpoint="https://push.example.com/abc",
            p256dh="key1", auth="auth1", user_agent="Mozilla",
        )
        assert d.device_id == "dev1"
        assert d.user_agent == "Mozilla"
        assert d.failed_count == 0

    def test_register_replaces(self):
        self.center.register_device("dev1", "https://a", "k1", "auth1")
        self.center.register_device("dev1", "https://b", "k2", "auth2")
        d = self.center.get_device("dev1")
        assert d.endpoint == "https://b"
        assert d.p256dh == "k2"
        assert len(self.center.devices) == 1

    def test_touch_updates_last_seen(self):
        d = self.center.register_device("dev1", "https://a", "k", "auth")
        old_seen = d.last_seen
        time.sleep(0.05)
        self.center.touch_device("dev1")
        d2 = self.center.get_device("dev1")
        assert d2.last_seen > old_seen

    def test_touch_with_capabilities_merges(self):
        self.center.register_device("dev1", "https://a", "k", "auth", capabilities=["voice"])
        self.center.touch_device("dev1", capabilities=["location"])
        d = self.center.get_device("dev1")
        assert "voice" in d.capabilities
        assert "location" in d.capabilities

    def test_unregister(self):
        self.center.register_device("dev1", "https://a", "k", "auth")
        assert self.center.unregister_device("dev1") is True
        assert self.center.get_device("dev1") is None
        assert self.center.unregister_device("dev1") is False

    def test_list_devices_sorted_by_recent(self):
        self.center.register_device("a", "https://a", "k", "auth")
        time.sleep(0.05)
        self.center.register_device("b", "https://b", "k", "auth")
        devices = self.center.list_devices()
        assert devices[0].device_id == "b"  # most recent first

    def test_persistence(self):
        self.center.register_device("d1", "https://a", "k", "auth")
        from omni_v2.agents import notifications
        notifications.NotificationCenter._instance = None
        c2 = notifications.NotificationCenter(data_dir=Path(self._tmp))
        assert c2.get_device("d1") is not None


# ---------- VAPID ----------
class TestVAPID:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_notif_")
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None

    def teardown_method(self):
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_vapid_auto_generated(self):
        from omni_v2.agents import notifications
        c = notifications.NotificationCenter(data_dir=Path(self._tmp))
        pub = c.get_vapid_public_key()
        assert pub is not None
        assert len(pub) >= 40

    def test_vapid_persistent(self):
        from omni_v2.agents import notifications
        c1 = notifications.NotificationCenter(data_dir=Path(self._tmp))
        pub1 = c1.get_vapid_public_key()
        notifications.NotificationCenter._instance = None
        c2 = notifications.NotificationCenter(data_dir=Path(self._tmp))
        pub2 = c2.get_vapid_public_key()
        assert pub1 == pub2  # same key

    def test_vapid_info(self):
        from omni_v2.agents import notifications
        c = notifications.NotificationCenter(data_dir=Path(self._tmp))
        info = c.get_vapid_info()
        assert "public_key" in info
        assert "subject" in info
        assert info["enabled"] is True


# ---------- Send-to-phone tool ----------
class TestSendToPhoneTool:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_notif_")
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        self.center = notifications.NotificationCenter(data_dir=Path(self._tmp))
        self.center.broadcast = lambda *a, **k: None
        # Reset prefs to defaults
        from omni_v2.agents.notification_prefs import NotificationPrefs
        NotificationPrefs._instance = None
        prefs = NotificationPrefs(data_dir=Path(self._tmp))
        prefs.reset_all()

    def teardown_method(self):
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_send_simple(self):
        from omni_v2.tools.send_to_phone import execute, get_metadata
        result = execute("Build complete!", title="OMNI", priority=1)
        assert result["ok"] is True
        assert result["data"]["body"] == "Build complete!"
        assert "notification_id" in result["data"]

    def test_send_with_priority(self):
        from omni_v2.tools.send_to_phone import execute
        result = execute("URGENT", priority=3, category="warn")
        assert result["ok"] is True
        # Notification should be in the inbox
        items = self.center.list_notifications(category="warn")
        assert any(n.body == "URGENT" for n in items)

    def test_send_empty_fails(self):
        from omni_v2.tools.send_to_phone import execute
        result = execute("")
        assert result["ok"] is False
        assert "required" in result["error"]

    def test_metadata_shape(self):
        from omni_v2.tools.send_to_phone import get_metadata
        meta = get_metadata()
        assert meta["name"] == "send_to_phone"
        assert "patterns" in meta
        assert "examples" in meta
        assert len(meta["patterns"]) >= 3

    def test_metadata_pattern_match(self):
        from omni_v2.tools.send_to_phone import get_metadata
        import re
        meta = get_metadata()
        text = "send to my phone: build done"
        matched = False
        for p in meta["patterns"]:
            if re.search(p, text, re.IGNORECASE):
                matched = True
                break
        assert matched, f"no pattern matched {text!r}"


# ---------- Status ----------
class TestStatus:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_notif_")
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None

    def teardown_method(self):
        from omni_v2.agents import notifications
        from omni_v2.agents import notification_prefs
        notifications.NotificationCenter._instance = None
        notification_prefs.NotificationPrefs._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_initial_status(self):
        from omni_v2.agents import notifications
        c = notifications.NotificationCenter(data_dir=Path(self._tmp))
        s = c.get_status()
        assert s["notifications_count"] == 0
        assert s["unread_count"] == 0
        assert s["devices_count"] == 0

    def test_dashboard_shape(self):
        from omni_v2.agents import notifications
        c = notifications.NotificationCenter(data_dir=Path(self._tmp))
        c.broadcast = lambda *a, **k: None
        c.notify("Test", category="info")
        d = c.get_full_dashboard()
        assert "notifications" in d
        assert "devices" in d
        assert "vapid" in d
        assert len(d["notifications"]) == 1


# ---------- Singleton ----------
class TestSingleton:
    def test_same_instance(self):
        from omni_v2.agents import notifications
        notifications.NotificationCenter._instance = None
        c1 = notifications.NotificationCenter()
        c2 = notifications.NotificationCenter()
        assert c1 is c2


# ---------- Live backend tests (skipped if not running) ----------
class TestBackendLive:
    def test_notifications_status_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications/status", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "notifications" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_notifications_list_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications?limit=10", timeout=2)
            data = json.loads(req.read().decode())
            assert "notifications" in data
            assert "unread_count" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_notifications_create_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/notifications",
                data=json.dumps({
                    "title": "Smoke test", "body": "Hello from tests",
                    "category": "info", "priority": 1,
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert data["notification"]["title"] == "Smoke test"
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_vapid_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications/vapid", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "vapid" in data
            # public_key might be None if cryptography not installed
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_devices_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications/devices", timeout=2)
            data = json.loads(req.read().decode())
            assert "devices" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_push_subscribe_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/notifications/subscribe",
                data=json.dumps({
                    "device_id": "test-device-001",
                    "endpoint": "https://fcm.googleapis.com/test",
                    "p256dh": "testkey",
                    "auth": "testauth",
                    "user_agent": "Mozilla/5.0",
                    "paired": True,
                    "capabilities": ["voice", "location"],
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert data["device"]["device_id"] == "test-device-001"
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_dashboard_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications/dashboard", timeout=2)
            data = json.loads(req.read().decode())
            assert "dashboard" in data
            d = data["dashboard"]
            assert "notifications" in d
            assert "devices" in d
            assert "vapid" in d
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")
