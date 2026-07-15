"""
OMNI V3 - Demo Mode (Phase 3B: The 2-Minute Wow)

Pre-scripted cinematic demo. 8 scenes that show off everything OMNI can do.
Auto-advances on user input or timer. Can be triggered with: "omni demo" or button.

Scenes:
  1. Welcome — "I'm OMNI, a local AGI"
  2. I can hear you — wait for speech
  3. I can think — "what's on my plate today?" → multi-tool execution
  4. I can take action — "open github" → browser opens
  5. I can recover — simulated failure → self-healing fallback
  6. I can remember — "what did I do yesterday?" → memory recall
  7. I can speak first — proactive suggestion triggered
  8. I'm yours — closing statement
"""
from __future__ import annotations
import time
import threading
import json
import asyncio
import random
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field, asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("DemoMode")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


@dataclass
class DemoScene:
    """A single scene in the demo script."""
    id: int
    title: str
    narration: str
    action: str  # "say" | "execute" | "wait_for_speech" | "trigger_proactive" | "simulate_failure" | "end"
    command: str = ""
    duration_sec: int = 8
    expected: List[str] = field(default_factory=list)  # expected speech for wait
    shows: List[str] = field(default_factory=list)  # what to highlight in UI


DEMO_SCRIPT = [
    DemoScene(
        id=1,
        title="Welcome to OMNI",
        narration=(
            "I'm OMNI V3 — a local, private AGI. "
            "I run entirely on this laptop. No cloud, no spying. "
            "I have a 1.5 billion parameter brain, 100+ tools, and I remember everything."
        ),
        action="say",
        duration_sec=12,
        shows=["brain", "stats"],
    ),
    DemoScene(
        id=2,
        title="I can hear you",
        narration="Say something — anything. I'll show you the live transcription.",
        action="wait_for_speech",
        expected=["hello", "hi", "hey", "test", "yo", "anything"],
        duration_sec=12,
        shows=["stt", "audio_level"],
    ),
    DemoScene(
        id=3,
        title="I can think",
        narration="Now watch me think. Ask me what's on your plate today.",
        action="execute",
        command="what's on my plate today",
        duration_sec=18,
        shows=["thought_stream", "tool_cards", "calendar", "inbox"],
    ),
    DemoScene(
        id=4,
        title="I can take action",
        narration="And then I just do it. Open github.",
        action="execute",
        command="open github",
        duration_sec=12,
        shows=["browser", "profile_isolated"],
    ),
    DemoScene(
        id=5,
        title="I can recover",
        narration="Sometimes things fail. Watch me try again.",
        action="simulate_failure",
        command="open this_doesnt_exist.exe",
        duration_sec=18,
        shows=["failure", "self_healing", "fallback"],
    ),
    DemoScene(
        id=6,
        title="I can remember",
        narration="Ask me what you did yesterday. I'll look it up.",
        action="execute",
        command="what did I do yesterday",
        duration_sec=14,
        shows=["memory_panel", "yesterday_digest"],
    ),
    DemoScene(
        id=7,
        title="I can speak first",
        narration="And sometimes I tell YOU what to do. Watch this.",
        action="trigger_proactive",
        duration_sec=12,
        shows=["proactive_banner", "mood_change"],
    ),
    DemoScene(
        id=8,
        title="I'm yours",
        narration=(
            "All local. All private. All yours. "
            "Welcome to your AGI. Now let's get to work."
        ),
        action="end",
        duration_sec=8,
    ),
]


class DemoMode:
    """
    The 2-minute cinematic demo. Singleton.
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

    def __init__(self, on_scene: Optional[Callable[[DemoScene], None]] = None):
        if self._initialized:
            return
        self.on_scene = on_scene
        self._running = False
        self._paused = False
        self._current_scene_idx = 0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._start_time: float = 0.0
        self._initialized = True
        logger.info("🎬 DemoMode initialized (8 scenes, ~76s total)")

    def start(self) -> None:
        """Start the demo from scene 1."""
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._paused = False
        self._current_scene_idx = 0
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._run, name="DemoMode", daemon=True)
        self._thread.start()
        logger.info("🎬 Demo started")

    def stop(self) -> None:
        """Stop the demo."""
        self._stop_event.set()
        self._running = False
        logger.info("🎬 Demo stopped")

    def pause(self) -> None:
        """Pause the demo."""
        self._paused = True
        logger.info("🎬 Demo paused")

    def resume(self) -> None:
        """Resume the demo."""
        self._paused = False
        logger.info("🎬 Demo resumed")

    def skip_to(self, scene_id: int) -> None:
        """Skip to a specific scene (1-indexed)."""
        idx = scene_id - 1
        if 0 <= idx < len(DEMO_SCRIPT):
            self._current_scene_idx = idx
            # Fire the scene
            if self.on_scene:
                try:
                    self.on_scene(DEMO_SCRIPT[idx])
                except Exception as e:
                    logger.error(f"on_scene callback: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "paused": self._paused,
            "current_scene_id": self._current_scene_idx + 1 if self._running else 0,
            "current_scene_title": DEMO_SCRIPT[self._current_scene_idx].title if self._running else None,
            "elapsed_sec": time.time() - self._start_time if self._running else 0,
            "total_scenes": len(DEMO_SCRIPT),
        }

    def get_script(self) -> List[Dict[str, Any]]:
        """Return the full demo script for the UI."""
        return [s.to_dict() if hasattr(s, 'to_dict') else asdict(s) for s in DEMO_SCRIPT]

    def _run(self) -> None:
        """Main demo loop."""
        try:
            while self._running and not self._stop_event.is_set():
                if self._current_scene_idx >= len(DEMO_SCRIPT):
                    break
                scene = DEMO_SCRIPT[self._current_scene_idx]
                # Fire scene
                if self.on_scene:
                    try:
                        self.on_scene(scene)
                    except Exception as e:
                        logger.error(f"on_scene callback: {e}")
                logger.info(f"🎬 Scene {scene.id}: {scene.title}")
                # Wait for the scene duration (or until stopped)
                waited = 0.0
                while waited < scene.duration_sec and self._running and not self._stop_event.is_set():
                    if not self._paused:
                        time.sleep(0.5)
                        waited += 0.5
                if not self._running or self._stop_event.is_set():
                    break
                self._current_scene_idx += 1
            if self._running:
                logger.info("🎬 Demo complete")
                self._running = False
        except Exception as e:
            logger.error(f"Demo loop error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self._running = False


def get_demo_mode(on_scene: Optional[Callable] = None) -> DemoMode:
    return DemoMode(on_scene=on_scene)
