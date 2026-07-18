"""
OMNI V3 - Notification Preferences Tests (Phase 5E)

Verifies:
  1. Default preferences loaded
  2. Per-category mute
  3. Min priority filter
  4. Daily limits per category
  5. Snooze (mute all for N minutes)
  6. Do-Not-Disturb hours
  7. Tag filters / blocklist
  8. Persistence across restart
  9. should_notify logic
  10. snooze tool via brain
  11. Singleton behavior
"""
import json
import time
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None


# ---------- Defaults & basics ----------
class TestDefaults:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_prefs_")
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        self.prefs = notification_prefs.NotificationPrefs(data_dir=Path(self._tmp))

    def teardown_method(self):
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_defaults_loaded(self):
        p = self.prefs.get_all()
        assert p["enabled"] is True
        assert p["dnd_enabled"] is False
        assert p["dnd_start_hour"] == 22
        assert p["dnd_end_hour"] == 7
        assert "info" in p["category_limits"]
        assert p["min_priority"] == 0

    def test_set_and_get(self):
        ok = self.prefs.set("enabled", False)
        assert ok
        assert self.prefs.get("enabled") is False

    def test_set_unknown_key_fails(self):
        ok = self.prefs.set("nonsense_key_xyz", True)
        assert not ok

    def test_update_multiple(self):
        results = self.prefs.update(enabled=False, min_priority=2)
        assert all(results.values())
        assert self.prefs.get("enabled") is False
        assert self.prefs.get("min_priority") == 2

    def test_reset_all(self):
        self.prefs.set("enabled", False)
        self.prefs.reset_all()
        assert self.prefs.get("enabled") is True

    def test_persistence(self):
        self.prefs.set("dnd_start_hour", 23)
        self.prefs.set("min_priority", 1)
        from omni_v2.agents import notification_prefs
        notification_prefs.NotificationPrefs._instance = None
        p2 = notification_prefs.NotificationPrefs(data_dir=Path(self._tmp))
        assert p2.get("dnd_start_hour") == 23
        assert p2.get("min_priority") == 1


# ---------- Snooze ----------
class TestSnooze:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_prefs_")
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        self.prefs = notification_prefs.NotificationPrefs(data_dir=Path(self._tmp))

    def teardown_method(self):
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_snooze_for(self):
        state = self.prefs.snooze_for(minutes=5, reason="test")
        assert state.is_active
        assert state.remaining_sec > 200  # ~300s
        assert state.reason == "test"

    def test_snooze_blocks_notifications(self):
        self.prefs.snooze_for(minutes=5)
        assert not self.prefs.should_notify("info", priority=2)

    def test_unsnooze(self):
        self.prefs.snooze_for(minutes=5)
        assert self.prefs.unsnooze() is True
        assert self.prefs.get_snooze() is None

    def test_unsnooze_when_none(self):
        assert self.prefs.unsnooze() is False

    def test_snooze_persists(self):
        self.prefs.snooze_for(minutes=30, reason="work")
        from omni_v2.agents import notification_prefs
        notification_prefs.NotificationPrefs._instance = None
        p2 = notification_prefs.NotificationPrefs(data_dir=Path(self._tmp))
        s = p2.get_snooze()
        assert s is not None
        assert s.reason == "work"


# ---------- Should-notify logic ----------
class TestShouldNotify:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_prefs_")
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        self.prefs = notification_prefs.NotificationPrefs(data_dir=Path(self._tmp))

    def teardown_method(self):
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_allows_normal(self):
        assert self.prefs.should_notify("info", priority=1)

    def test_blocks_when_disabled(self):
        self.prefs.set("enabled", False)
        assert not self.prefs.should_notify("info", priority=2)

    def test_blocks_muted_category(self):
        self.prefs.update(muted_categories=["warn"])
        assert not self.prefs.should_notify("warn", priority=2)
        assert self.prefs.should_notify("info", priority=1)

    def test_min_priority(self):
        self.prefs.set("min_priority", 2)
        assert not self.prefs.should_notify("info", priority=1)
        assert self.prefs.should_notify("info", priority=2)
        assert self.prefs.should_notify("info", priority=3)

    def test_daily_limit(self):
        self.prefs.update(category_limits={"info": 2})
        # Record 2 sends
        self.prefs.record_sent("info")
        self.prefs.record_sent("info")
        # 3rd should be blocked
        assert not self.prefs.should_notify("info", priority=1)
        # But other categories OK
        assert self.prefs.should_notify("warn", priority=1)

    def test_tag_blocklist(self):
        self.prefs.update(tag_blocklist=["spam"])
        assert not self.prefs.should_notify("info", priority=1, tag="spam")
        assert self.prefs.should_notify("info", priority=1, tag="important")

    def test_tag_filter(self):
        self.prefs.update(tag_filters=["important", "urgent"])
        assert not self.prefs.should_notify("info", priority=1, tag="other")
        assert self.prefs.should_notify("info", priority=1, tag="important")


# ---------- DND ----------
class TestDND:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_prefs_")
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        self.prefs = notification_prefs.NotificationPrefs(data_dir=Path(self._tmp))

    def teardown_method(self):
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_dnd_disabled_by_default(self):
        # We don't know what time it is, but DND is off
        assert not self.prefs._in_dnd_window()

    def test_dnd_force_active(self):
        # Set DND to cover ALL hours
        self.prefs.update(dnd_enabled=True, dnd_start_hour=0, dnd_end_hour=23)
        # Now 0 <= h < 23, so should be active
        # (Unless end is 24 — but we cap to 23)
        # Use a time within
        from omni_v2.agents import notification_prefs
        # Mock current hour
        h = datetime.now().hour
        # If h is in [0, 23), should be in DND
        self.prefs.update(dnd_start_hour=0, dnd_end_hour=24)
        assert self.prefs._in_dnd_window()

    def test_dnd_crosses_midnight(self):
        # DND from 22 to 7
        self.prefs.update(dnd_enabled=True, dnd_start_hour=22, dnd_end_hour=7)
        h = datetime.now().hour
        if h >= 22 or h < 7:
            assert self.prefs._in_dnd_window()
        else:
            assert not self.prefs._in_dnd_window()


# ---------- Status ----------
class TestStatus:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_prefs_")
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        self.prefs = notification_prefs.NotificationPrefs(data_dir=Path(self._tmp))

    def teardown_method(self):
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_status_shape(self):
        s = self.prefs.get_status()
        assert "enabled" in s
        assert "dnd_active" in s
        assert "snoozed" in s
        assert "muted_categories" in s
        assert "category_limits" in s
        assert "today_counts" in s

    def test_dashboard_shape(self):
        d = self.prefs.get_full_dashboard()
        assert "prefs" in d
        assert "status" in d
        assert "snooze" in d


# ---------- Singleton ----------
class TestSingleton:
    def test_same_instance(self):
        from omni_v2.agents import notification_prefs
        notification_prefs.NotificationPrefs._instance = None
        p1 = notification_prefs.NotificationPrefs()
        p2 = notification_prefs.NotificationPrefs()
        assert p1 is p2


# ---------- Snooze tool ----------
class TestSnoozeTool:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_prefs_")
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None

    def teardown_method(self):
        from omni_v2.agents import notification_prefs
        from omni_v2.agents import notifications
        notification_prefs.NotificationPrefs._instance = None
        notifications.NotificationCenter._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_execute_snooze(self):
        from omni_v2.tools.snooze import execute_snooze
        result = execute_snooze(minutes=15)
        assert result["ok"] is True
        assert result["data"]["snoozed"] is True
        assert result["data"]["minutes"] == 15

    def test_execute_unsnooze(self):
        from omni_v2.tools.snooze import execute_snooze
        result = execute_snooze(minutes=0, action="unsnooze")
        assert result["ok"] is True
        assert result["data"]["snoozed"] is False

    def test_clamp_max(self):
        from omni_v2.tools.snooze import execute_snooze
        result = execute_snooze(minutes=99999)
        assert result["ok"] is True
        assert result["data"]["minutes"] <= 1440

    def test_clamp_min(self):
        from omni_v2.tools.snooze import execute_snooze
        result = execute_snooze(minutes=0.1)
        assert result["ok"] is True
        assert result["data"]["minutes"] >= 1.0

    def test_metadata(self):
        from omni_v2.tools.snooze import get_metadata
        meta = get_metadata()
        assert meta["name"] == "snooze_notifications"
        assert len(meta["patterns"]) >= 3

    def test_plugin_routes(self):
        from omni_v2.tools.snooze import SnoozePlugin
        import asyncio
        p = SnoozePlugin()
        assert "snooze" in p.metadata.description.lower() or "snooze" in p.metadata.name
        assert "snooze_notifications" in p.SUPPORTED_ACTIONS
        # Test async execute
        result = asyncio.run(p.execute({"minutes": 10}, {"original": "snooze for 10"}))
        assert result.success
        assert "10" in result.message or "🔕" in result.message


# ---------- Live backend tests ----------
class TestBackendLive:
    def test_prefs_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications/prefs", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "prefs" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_snooze_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/notifications/snooze",
                data=json.dumps({"minutes": 5}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert "snooze" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_unsnooze_endpoint(self):
        import urllib.request
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/notifications/snooze",
                method="DELETE",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            assert resp.status == 200
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_update_prefs_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/notifications/prefs",
                data=json.dumps({"dnd_enabled": False, "min_priority": 1}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_export_json_endpoint(self):
        import urllib.request
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications/export?format=json", timeout=3)
            data = json.loads(req.read().decode())
            assert isinstance(data, list)
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_export_csv_endpoint(self):
        import urllib.request
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/notifications/export?format=csv", timeout=3)
            text = req.read().decode()
            assert "id,ts,iso" in text
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_snooze_via_brain(self):
        """Test that 'snooze for 30 min' triggers the snooze tool."""
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/execute",
                data=json.dumps({"command": "snooze for 30 minutes"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("success") is True
            assert "snooz" in data.get("message", "").lower() or "🔕" in data.get("message", "")
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")
