"""
OMNI V3 - Screen Watcher (Phase 6A — Visual-First)

The brain watches your screen periodically and builds high-level context.
Detects:
  - What app/window is active
  - What the user is doing (coding, browsing, reading, idle, etc.)
  - When the screen changes significantly (new scene)
  - Sustained activities (2+ hours of coding)

The context feeds into the proactive engine so OMNI can:
  - Suggest breaks after long focus
  - Offer to summarize what you're reading
  - Detect when you switch to a new task
  - Trigger automation when specific apps open

This is privacy-first: all processing happens locally. No images leave
the laptop unless the user explicitly requests a vision analysis.
"""
from __future__ import annotations
import os
import time
import json
import threading
import tempfile
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger("ScreenWatcher")


# Default interval (seconds)
DEFAULT_INTERVAL_SEC = 30

# Scene change detection: hash diff threshold
HASH_CHANGE_THRESHOLD = 5  # Different bytes in hash means changed

# Idle detection: seconds of no change
IDLE_THRESHOLD_SEC = 60

# Coding detection: keywords that appear in active window
CODING_KEYWORDS = [
    "code", "py", "js", "ts", "html", "css", "json", "yaml", "toml",
    "function", "class", "def ", "import ", "return ", "var ", "let ",
    "if ", "else", "for ", "while", "git ", "terminal", "powershell",
    "vscode", "visual studio", "intellij", "pycharm", "sublime", "atom",
    "vim", "nvim", "emacs", "code -", "cursor",
]

BROWSING_KEYWORDS = [
    "chrome", "firefox", "edge", "safari", "brave", "arc",
    "github", "stackoverflow", "reddit", "twitter", "x.com",
    "youtube", "netflix", "spotify", "docs.", ".dev",
    "wikipedia", "gitlab", "figma", "notion", "linear",
]

READING_KEYWORDS = [
    "pdf", "epub", ".md", "readme", "documentation", "tutorial",
    "arxiv", "research", "paper", "book", "kindle",
]

COMMUNICATING_KEYWORDS = [
    "slack", "discord", "telegram", "whatsapp", "messenger",
    "outlook", "thunderbird", "mail", "gmail", "inbox",
    "zoom", "meet", "teams", "skype", "webex",
]

GAMING_KEYWORDS = [
    "steam", "epic games", "riot", "valorant", "league",
    "minecraft", "fortnite", "battlenet", "origin",
]


@dataclass
class ScreenScene:
    """A snapshot of the screen at a point in time."""
    ts: float
    activity: str               # "coding" | "browsing" | "reading" | "communicating" | "gaming" | "idle" | "unknown"
    app_name: str = ""          # "vscode", "chrome", etc.
    window_title: str = ""      # The active window title
    screen_hash: str = ""       # Hash of the screen content
    change_pct: float = 0.0     # % of pixels that changed from last frame
    duration_sec: float = 0.0   # How long the user has been in this scene
    is_new_scene: bool = True   # True if this is a different scene from last
    image_path: str = ""        # Path to the screenshot (if saved)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScreenWatcher:
    """
    Singleton. Watches the screen periodically. Thread-safe.
    Builds a context dictionary that the proactive engine can query.
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

    def __init__(self, interval_sec: float = DEFAULT_INTERVAL_SEC,
                 save_screenshots: bool = False, data_dir: Optional[Path] = None):
        if self._initialized:
            return
        self.interval_sec = interval_sec
        self.save_screenshots = save_screenshots
        try:
            from omni_v2.core.paths import DATA_DIR
            base = Path(DATA_DIR) if not isinstance(DATA_DIR, str) else Path(DATA_DIR)
        except Exception:
            base = Path.cwd() / "data"
        self.data_dir = (data_dir or (base / "screen_watcher"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "history.json"
        self.screenshots_dir = self.data_dir / "screenshots"
        if self.save_screenshots:
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Try to import the screen capture backend
        self._cap = None
        self._cap_backend = "none"
        try:
            from omni_v2.vision.screen import ScreenCapture
            self._cap = ScreenCapture()
            self._cap_backend = self._cap.backend or "none"
        except Exception as e:
            logger.debug(f"ScreenCapture not available: {e}")

        # Try to import the platform-specific window list (Windows/macOS/Linux)
        self._get_active_window = self._detect_get_active_window()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_scene: Optional[ScreenScene] = None
        self._current_scene: Optional[ScreenScene] = None
        self._scene_started_at: float = time.time()
        self._last_change_at: float = time.time()
        self._scenes_today: List[ScreenScene] = []
        self._app_durations: Dict[str, float] = {}  # app -> total seconds today
        self._lock_data = threading.RLock()
        self._history: List[ScreenScene] = []
        # On-context hooks (called when scene changes)
        self.on_scene_change: Optional[Callable[[ScreenScene, Optional[ScreenScene]], None]] = None

        self._load_history()
        self._initialized = True
        logger.info(f"👁 ScreenWatcher initialized (interval: {interval_sec}s, "
                    f"backend: {self._cap_backend}, window API: {self._get_active_window.__name__})")

    def _detect_get_active_window(self):
        """Detect the best platform-specific function to get the active window."""
        # Try Windows
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # Kernel32 GetForegroundWindow + GetWindowTextW
            def win_active():
                try:
                    hwnd = user32.GetForegroundWindow()
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length == 0:
                        return "", ""
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    # Get process name from PID
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    app = ""
                    try:
                        import psutil
                        app = psutil.Process(pid.value).name()
                    except Exception:
                        pass
                    return app, title
                except Exception:
                    return "", ""
            return win_active
        except Exception:
            pass
        # Try macOS
        try:
            import subprocess
            def mac_active():
                try:
                    out = subprocess.run(
                        ["osascript", "-e",
                         'tell application "System Events" to get name of (first application process whose frontmost is true) & "|" & name of front window of (first application process whose frontmost is true)'],
                        capture_output=True, text=True, timeout=1,
                    )
                    parts = out.stdout.strip().split("|", 1)
                    app = parts[0] if parts else ""
                    title = parts[1] if len(parts) > 1 else ""
                    return app, title
                except Exception:
                    return "", ""
            return mac_active
        except Exception:
            pass
        # Linux fallback: try xdotool, then wmctrl
        try:
            import subprocess
            def linux_active():
                try:
                    out = subprocess.run(
                        ["xdotool", "getactivewindow", "getwindowname"],
                        capture_output=True, text=True, timeout=1,
                    )
                    title = out.stdout.strip()
                    return "xdotool", title
                except Exception:
                    return "", ""
            return linux_active
        except Exception:
            pass
        # Default: return empty
        def noop():
            return "", ""
        return noop

    def _load_history(self):
        try:
            if self.history_file.exists():
                raw = json.loads(self.history_file.read_text(encoding="utf-8"))
                self._history = []
                for entry in raw[-1000:]:  # last 1000
                    try:
                        self._history.append(ScreenScene(**entry))
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Load history: {e}")

    def _save_history(self):
        try:
            with self._lock_data:
                self._atomic_write(self.history_file, [s.to_dict() for s in self._history[-1000:]])
        except Exception as e:
            logger.debug(f"Save history: {e}")

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
            logger.error(f"ScreenWatcher write failed: {e}")

    # ===== Lifecycle =====

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="ScreenWatcher", daemon=True)
        self._thread.start()
        logger.info("🟢 ScreenWatcher daemon started")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._save_history()
        logger.info("🔴 ScreenWatcher stopped")

    def _loop(self):
        while self._running:
            try:
                time.sleep(self.interval_sec)
                if not self._running:
                    break
                self._tick()
            except Exception as e:
                logger.debug(f"ScreenWatcher tick error: {e}")

    def _tick(self):
        """One pass: capture screen, classify, update state."""
        scene = self._capture_scene()
        if scene is None:
            return
        with self._lock_data:
            # Determine if it's a new scene
            is_new = self._is_new_scene(scene)
            scene.is_new_scene = is_new
            now = time.time()
            if is_new:
                # Close out previous scene
                if self._current_scene is not None:
                    self._current_scene.duration_sec = now - self._scene_started_at
                    self._app_durations[self._current_scene.app_name or "unknown"] = \
                        self._app_durations.get(self._current_scene.app_name or "unknown", 0) + \
                        self._current_scene.duration_sec
                self._scene_started_at = now
            else:
                scene.duration_sec = now - self._scene_started_at
            # Update current
            self._current_scene = scene
            self._last_scene = scene
            self._last_change_at = now
            # Save to history (rate-limited)
            self._history.append(scene)
            if len(self._history) > 1500:
                self._history = self._history[-1500:]
            # Fire on_scene_change hook
        if is_new and self.on_scene_change:
            try:
                self.on_scene_change(scene, prev)
            except Exception:
                pass
        # Periodically save
        if len(self._history) % 20 == 0:
            self._save_history()

    def _is_new_scene(self, scene: ScreenScene) -> bool:
        """Compare to last scene. Returns True if app/activity changed significantly."""
        if self._last_scene is None:
            return True
        # App changed → new scene
        if scene.app_name and self._last_scene.app_name and \
                scene.app_name != self._last_scene.app_name:
            return True
        # Activity changed → new scene
        if scene.activity != self._last_scene.activity:
            return True
        # Screen changed significantly → not a "new scene" per se, but a "continued"
        return False

    def _capture_scene(self) -> Optional[ScreenScene]:
        """Take a screenshot + active window info, classify activity."""
        # Get active window
        try:
            app, title = self._get_active_window()
        except Exception:
            app, title = "", ""
        # Get screen hash
        screen_hash = ""
        if self._cap and self._cap_backend != "none":
            try:
                img = self._cap.capture()
                if img is not None:
                    screen_hash = self._hash_image(img)
                    if self.save_screenshots:
                        try:
                            from datetime import datetime
                            path = self.screenshots_dir / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                            img.save(str(path), "JPEG", quality=60)
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Screen capture failed: {e}")
        # Classify activity
        activity = self._classify_activity(app, title, screen_hash)
        # Change percentage
        change_pct = 0.0
        if self._last_scene and self._last_scene.screen_hash and screen_hash:
            change_pct = self._hash_diff_pct(self._last_scene.screen_hash, screen_hash)
        return ScreenScene(
            ts=time.time(),
            activity=activity,
            app_name=app or "",
            window_title=title or "",
            screen_hash=screen_hash,
            change_pct=change_pct,
            is_new_scene=True,  # will be updated by _tick
            duration_sec=0.0,
        )

    def _hash_image(self, img) -> str:
        """Hash a PIL image (downsampled for speed)."""
        try:
            from PIL import Image
            small = img.resize((64, 36)).convert("L")
            return hashlib.sha256(small.tobytes()).hexdigest()[:32]
        except Exception as e:
            return ""

    def _hash_diff_pct(self, h1: str, h2: str) -> float:
        """Crude change percentage: how many hex chars differ between two hashes."""
        if not h1 or not h2 or len(h1) != len(h2):
            return 0.0
        diff = sum(1 for a, b in zip(h1, h2) if a != b)
        return (diff / len(h1)) * 100.0

    def _classify_activity(self, app: str, title: str, screen_hash: str) -> str:
        """Determine what the user is doing based on app + window title."""
        text = f"{app} {title}".lower()
        if not text.strip():
            return "idle"
        # Check for idle (no recent change)
        if self._last_change_at and (time.time() - self._last_change_at) > IDLE_THRESHOLD_SEC:
            return "idle"
        # Coding?
        if any(kw in text for kw in CODING_KEYWORDS):
            return "coding"
        # Browsing?
        if any(kw in text for kw in BROWSING_KEYWORDS):
            return "browsing"
        # Communicating?
        if any(kw in text for kw in COMMUNICATING_KEYWORDS):
            return "communicating"
        # Reading?
        if any(kw in text for kw in READING_KEYWORDS):
            return "reading"
        # Gaming?
        if any(kw in text for kw in GAMING_KEYWORDS):
            return "gaming"
        return "unknown"

    # ===== Public API =====

    def get_current_scene(self) -> Optional[ScreenScene]:
        with self._lock_data:
            return self._current_scene

    def get_context(self) -> Dict[str, Any]:
        """Build a context dict for the proactive engine."""
        with self._lock_data:
            scene = self._current_scene
            if scene is None:
                return {"screen": {"available": False, "reason": "no capture yet"}}
            duration_min = scene.duration_sec / 60.0
            return {
                "screen": {
                    "available": True,
                    "activity": scene.activity,
                    "app": scene.app_name,
                    "window_title": scene.window_title,
                    "duration_min": round(duration_min, 1),
                    "change_pct": round(scene.change_pct, 1),
                    "captured_at": scene.ts,
                    "is_new_scene": scene.is_new_scene,
                    "backend": self._cap_backend,
                },
                "today": {
                    "scene_count": len(self._scenes_today) + 1,
                    "app_durations_min": {
                        k: round(v / 60, 1) for k, v in self._app_durations.items()
                    },
                },
            }

    def get_recent_scenes(self, limit: int = 20) -> List[ScreenScene]:
        with self._lock_data:
            return list(self._history[-limit:])

    def get_status(self) -> Dict[str, Any]:
        with self._lock_data:
            return {
                "running": self._running,
                "interval_sec": self.interval_sec,
                "backend": self._cap_backend,
                "window_api": self._get_active_window.__name__,
                "history_count": len(self._history),
                "current_scene": self._current_scene.to_dict() if self._current_scene else None,
            }

    def get_full_dashboard(self) -> Dict[str, Any]:
        with self._lock_data:
            return {
                "status": self.get_status(),
                "context": self.get_context(),
                "recent_scenes": [s.to_dict() for s in self._history[-30:]],
            }

    def reset_today(self) -> None:
        with self._lock_data:
            self._app_durations.clear()
            self._scenes_today.clear()


def get_screen_watcher() -> ScreenWatcher:
    return ScreenWatcher()


# Convenience: classify a window title without running the watcher
def classify_window(app: str = "", title: str = "") -> str:
    """Standalone activity classifier (no state)."""
    text = f"{app} {title}".lower()
    if not text.strip():
        return "unknown"
    if any(kw in text for kw in CODING_KEYWORDS):
        return "coding"
    if any(kw in text for kw in BROWSING_KEYWORDS):
        return "browsing"
    if any(kw in text for kw in COMMUNICATING_KEYWORDS):
        return "communicating"
    if any(kw in text for kw in READING_KEYWORDS):
        return "reading"
    if any(kw in text for kw in GAMING_KEYWORDS):
        return "gaming"
    return "unknown"
