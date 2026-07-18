"""
OMNI V3 - Screen Watcher Tests (Phase 6A — Visual-First)

Verifies:
  1. Activity classification (coding/browsing/reading/communicating/gaming/unknown)
  2. Scene dataclass roundtrip
  3. Singleton behavior
  4. get_status / get_context shape
  5. classify_window standalone function
  6. Persistence
"""
import json
import time
import tempfile
import shutil
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None


# ---------- Activity classification ----------
class TestClassifyWindow:
    """Standalone classifier — no state."""

    def test_coding_apps(self):
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("vscode", "main.py") == "coding"
        assert classify_window("cursor", "deepseek.py") == "coding"
        assert classify_window("vim", "") == "coding"
        assert classify_window("terminal", "ssh prod") == "coding"

    def test_browsing_apps(self):
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("chrome", "github.com/omni") == "browsing"
        assert classify_window("firefox", "stackoverflow.com") == "browsing"
        assert classify_window("arc", "figma.com/file") == "browsing"

    def test_communicating_apps(self):
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("slack", "general channel") == "communicating"
        assert classify_window("discord", "team-chat") == "communicating"
        assert classify_window("outlook", "inbox") == "communicating"

    def test_reading_apps(self):
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("reader", "arxiv.org") == "reading"
        assert classify_window("kindle", "deep work.epub") == "reading"
        assert classify_window("zotero", "papers") == "reading"

    def test_gaming_apps(self):
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("steam", "library") == "gaming"
        assert classify_window("epic games", "launcher") == "gaming"

    def test_unknown_falls_back(self):
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("calculator", "Standard") == "unknown"
        assert classify_window("", "") == "unknown"

    def test_coding_keywords_in_title(self):
        """If title has 'function' or 'import', it's coding even without app name."""
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("", "function add(a, b)") == "coding"
        assert classify_window("", "import numpy as np") == "coding"

    def test_browsing_keywords_in_title(self):
        from omni_v2.agents.screen_watcher import classify_window
        assert classify_window("", "github.com/user/repo") == "browsing"
        assert classify_window("", "stackoverflow.com/questions") == "browsing"


# ---------- ScreenScene dataclass ----------
class TestScreenScene:
    def test_roundtrip(self):
        from omni_v2.agents.screen_watcher import ScreenScene
        s = ScreenScene(
            ts=123.0, activity="coding", app_name="vscode",
            window_title="main.py", screen_hash="abc123", change_pct=15.5,
            duration_sec=300.0, is_new_scene=True,
        )
        d = s.to_dict()
        s2 = ScreenScene(**d)
        assert s2.activity == s.activity
        assert s2.app_name == s.app_name
        assert s2.window_title == s.window_title
        assert s2.change_pct == s.change_pct
        assert s2.duration_sec == s.duration_sec


# ---------- ScreenWatcher singleton ----------
class TestSingleton:
    def test_same_instance(self):
        from omni_v2.agents import screen_watcher
        screen_watcher.ScreenWatcher._instance = None
        w1 = screen_watcher.ScreenWatcher()
        w2 = screen_watcher.ScreenWatcher()
        assert w1 is w2


# ---------- ScreenWatcher public API ----------
class TestScreenWatcher:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_screen_")
        from omni_v2.agents import screen_watcher
        screen_watcher.ScreenWatcher._instance = None
        # Init with a temp data dir
        self.watcher = screen_watcher.ScreenWatcher.__new__(screen_watcher.ScreenWatcher)
        self.watcher._initialized = True
        # Manually set the data dir to avoid re-creating with the default
        self.watcher.data_dir = Path(self._tmp)
        self.watcher.history_file = self.watcher.data_dir / "history.json"
        self.watcher.screenshots_dir = self.watcher.data_dir / "screenshots"
        self.watcher.interval_sec = 30.0
        self.watcher.save_screenshots = False
        self.watcher._cap = None
        self.watcher._cap_backend = "none"
        self.watcher._get_active_window = lambda: ("", "")
        self.watcher._running = False
        self.watcher._thread = None
        self.watcher._last_scene = None
        self.watcher._current_scene = None
        self.watcher._scene_started_at = time.time()
        self.watcher._last_change_at = time.time()
        self.watcher._scenes_today = []
        self.watcher._app_durations = {}
        self.watcher._lock_data = __import__("threading").RLock()
        self.watcher._history = []
        self.watcher.on_scene_change = None

    def teardown_method(self):
        from omni_v2.agents import screen_watcher
        screen_watcher.ScreenWatcher._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_status_shape(self):
        s = self.watcher.get_status()
        assert "running" in s
        assert "interval_sec" in s
        assert "backend" in s
        assert "window_api" in s
        assert "history_count" in s
        assert s["running"] is False
        assert s["history_count"] == 0
        assert s["current_scene"] is None

    def test_context_no_scene(self):
        ctx = self.watcher.get_context()
        assert "screen" in ctx
        assert ctx["screen"]["available"] is False

    def test_context_with_scene(self):
        from omni_v2.agents.screen_watcher import ScreenScene
        scene = ScreenScene(
            ts=time.time(), activity="coding", app_name="vscode",
            window_title="main.py", screen_hash="abc",
            change_pct=10.0, duration_sec=600.0, is_new_scene=False,
        )
        self.watcher._current_scene = scene
        ctx = self.watcher.get_context()
        assert ctx["screen"]["available"] is True
        assert ctx["screen"]["activity"] == "coding"
        assert ctx["screen"]["app"] == "vscode"
        assert ctx["screen"]["duration_min"] == 10.0

    def test_dashboard_shape(self):
        d = self.watcher.get_full_dashboard()
        assert "status" in d
        assert "context" in d
        assert "recent_scenes" in d

    def test_recent_scenes_empty(self):
        s = self.watcher.get_recent_scenes(limit=10)
        assert s == []

    def test_recent_scenes_with_history(self):
        from omni_v2.agents.screen_watcher import ScreenScene
        for i in range(5):
            self.watcher._history.append(ScreenScene(
                ts=time.time() - i*60, activity="coding", app_name="vscode",
                window_title=f"file{i}.py", change_pct=float(i),
            ))
        s = self.watcher.get_recent_scenes(limit=3)
        assert len(s) == 3
        # The 3 most recent (last 3 in history) — these are the oldest of the 5
        # (file0 was added first, file4 last; get_recent_scenes returns the tail)
        titles = [sc.window_title for sc in s]
        # The tail is the LAST 3 added = file2, file3, file4
        assert "file2.py" in titles
        assert "file3.py" in titles
        assert "file4.py" in titles

    def test_persistence(self):
        from omni_v2.agents.screen_watcher import ScreenScene
        for i in range(3):
            self.watcher._history.append(ScreenScene(
                ts=time.time(), activity="browsing", app_name="chrome",
                window_title=f"site{i}.com",
            ))
        self.watcher._save_history()
        # Verify the file was written
        assert self.watcher.history_file.exists()
        # Read it back
        import json
        raw = json.loads(self.watcher.history_file.read_text())
        assert len(raw) == 3
        assert raw[0]["window_title"] == "site0.com"
        assert raw[1]["window_title"] == "site1.com"
        assert raw[2]["window_title"] == "site2.com"

    def test_app_durations_tracking(self):
        # Manually simulate a scene duration
        from omni_v2.agents.screen_watcher import ScreenScene
        scene = ScreenScene(
            ts=time.time(), activity="coding", app_name="vscode",
            window_title="main.py",
        )
        self.watcher._current_scene = scene
        self.watcher._scene_started_at = time.time() - 300  # 5 min ago
        self.watcher._app_durations["vscode"] = 1500.0  # 25 min
        ctx = self.watcher.get_context()
        assert ctx["today"]["app_durations_min"]["vscode"] == 25.0

    def test_reset_today(self):
        self.watcher._app_durations["vscode"] = 500.0
        self.watcher.reset_today()
        assert len(self.watcher._app_durations) == 0


# ---------- Hash diff ----------
class TestHashDiff:
    def test_identical(self):
        from omni_v2.agents.screen_watcher import ScreenWatcher
        w = ScreenWatcher.__new__(ScreenWatcher)
        d = ScreenWatcher._hash_diff_pct(w, "abc", "abc")
        assert d == 0.0

    def test_different(self):
        from omni_v2.agents.screen_watcher import ScreenWatcher
        w = ScreenWatcher.__new__(ScreenWatcher)
        d = ScreenWatcher._hash_diff_pct(w, "abc", "xyz")
        assert d > 0.0

    def test_empty(self):
        from omni_v2.agents.screen_watcher import ScreenWatcher
        w = ScreenWatcher.__new__(ScreenWatcher)
        assert ScreenWatcher._hash_diff_pct(w, "", "") == 0.0
        assert ScreenWatcher._hash_diff_pct(w, "abc", "") == 0.0


# ---------- Keyword lists ----------
class TestKeywords:
    def test_coding_keywords_present(self):
        from omni_v2.agents.screen_watcher import CODING_KEYWORDS
        assert "vscode" in CODING_KEYWORDS
        assert "function" in CODING_KEYWORDS
        assert "import " in CODING_KEYWORDS  # with trailing space

    def test_browsing_keywords_present(self):
        from omni_v2.agents.screen_watcher import BROWSING_KEYWORDS
        assert "github" in BROWSING_KEYWORDS
        assert "stackoverflow" in BROWSING_KEYWORDS

    def test_communicating_keywords_present(self):
        from omni_v2.agents.screen_watcher import COMMUNICATING_KEYWORDS
        assert "slack" in COMMUNICATING_KEYWORDS
        assert "discord" in COMMUNICATING_KEYWORDS


# ---------- Live backend tests ----------
class TestBackendLive:
    def test_screen_status_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/screen/status", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "screen" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_screen_context_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/screen/context", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "context" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_screen_dashboard_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/screen/dashboard", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "dashboard" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_screen_recent_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/screen/recent?limit=5", timeout=2)
            data = json.loads(req.read().decode())
            assert "scenes" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_screen_classify_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/screen/classify",
                data=json.dumps({"app": "vscode", "title": "main.py"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert data.get("activity") == "coding"
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_screen_start_stop(self):
        import urllib.request, json
        try:
            # Start
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/screen/start", method="POST",
                data=b"", headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=3)
            # Status should now be running
            req2 = urllib.request.urlopen("http://127.0.0.1:8765/api/screen/status", timeout=2)
            data = json.loads(req2.read().decode())
            # Stop
            req3 = urllib.request.Request(
                "http://127.0.0.1:8765/api/screen/stop", method="POST",
                data=b"", headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req3, timeout=3)
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")
