"""
OMNI V3 - Onboarding Experience (Phase 3A: First Impression)

The 2-minute first-run experience. Anyone who opens OMNI for the first time
gets a guided tour that shows off the magic. Skip-able after first run.

Flow:
  Step 1: Welcome — "Hi, I'm OMNI. I'm a local AGI. All private, all yours."
  Step 2: Mic Test — "Let me make sure I can hear you. Say something."
  Step 3: Name — "What should I call you?"
  Step 4: First Command — "Try: 'open github' — I'll do it for you."
  Step 5: Wake Word — "I can also be always-listening. Say 'Hey OMNI'."

State: data/onboarding/state.json
  {completed: bool, current_step: int, skipped: bool, completed_at: float}
"""
from __future__ import annotations
import json
import time
import threading
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Onboarding")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


@dataclass
class OnboardingStep:
    """A single step in the onboarding flow."""
    id: int
    title: str
    body: str
    expected_input: str = ""  # what the user should say/do
    action_command: str = ""  # command to run if user clicks "do it for me"
    duration_sec: int = 8
    next_step_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "expected_input": self.expected_input,
            "action_command": self.action_command,
            "duration_sec": self.duration_sec,
            "next_step_id": self.next_step_id,
        }


ONBOARDING_STEPS = [
    OnboardingStep(
        id=1,
        title="Hi, I'm OMNI",
        body=(
            "I'm a local, private AGI — a butler that knows you. "
            "Everything runs on this laptop. No cloud, no spying. "
            "I have 100+ tools, a 1.5B-parameter brain, and a memory that "
            "remembers what you did yesterday."
        ),
        duration_sec=8,
        next_step_id=2,
    ),
    OnboardingStep(
        id=2,
        title="Let's test the mic",
        body=(
            "I want to make sure I can hear you. "
            "Say anything — 'hello', your name, whatever. "
            "I'll transcribe it and show you."
        ),
        expected_input="hello",
        duration_sec=10,
        next_step_id=3,
    ),
    OnboardingStep(
        id=3,
        title="What should I call you?",
        body=(
            "I'll use your name in greetings, proactive nudges, "
            "and morning briefs. Your data stays local."
        ),
        expected_input="Your name (e.g. 'Zarrar')",
        action_command="set my name to Zarrar",
        duration_sec=8,
        next_step_id=4,
    ),
    OnboardingStep(
        id=4,
        title="Let's do something",
        body=(
            "Try saying: 'open github'. "
            "Watch my brain reason, pick a tool, and execute it. "
            "This is what I do all day."
        ),
        expected_input="'open github'",
        action_command="open github",
        duration_sec=10,
        next_step_id=5,
    ),
    OnboardingStep(
        id=5,
        title="Hey OMNI",
        body=(
            "I can also be always-listening. Just say 'Hey OMNI' "
            "and I'll wake up, listen, and do whatever you ask. "
            "Want to enable it?"
        ),
        duration_sec=8,
        next_step_id=None,
    ),
]


class OnboardingState:
    """Tracks the user's onboarding progress."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, state_dir: Optional[Path] = None):
        if self._initialized:
            return
        self.state_dir = state_dir or (DATA_DIR / "onboarding")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        self._data_lock = threading.RLock()
        self.completed: bool = False
        self.current_step: int = 1
        self.skipped: bool = False
        self.completed_at: float = 0.0
        self.name: str = ""
        self._load()
        self._initialized = True
        logger.info(f"📋 OnboardingState loaded (completed={self.completed})")

    def _load(self):
        if not self.state_file.exists():
            self._save()
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.completed = data.get("completed", False)
            self.current_step = data.get("current_step", 1)
            self.skipped = data.get("skipped", False)
            self.completed_at = data.get("completed_at", 0.0)
            self.name = data.get("name", "")
        except Exception as e:
            logger.error(f"Onboarding load failed: {e}")

    def _save(self):
        with self._data_lock:
            data = {
                "completed": self.completed,
                "current_step": self.current_step,
                "skipped": self.skipped,
                "completed_at": self.completed_at,
                "name": self.name,
            }
            try:
                fd, tmp = tempfile.mkstemp(dir=str(self.state_dir), prefix=".onb_", suffix=".json.tmp")
                with __import__("os").fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                __import__("os").replace(tmp, self.state_file)
            except Exception as e:
                logger.error(f"Onboarding save failed: {e}")

    def should_show(self) -> bool:
        """Returns True if onboarding should be shown to the user."""
        return not self.completed and not self.skipped

    def advance(self, name: str = "") -> Optional[OnboardingStep]:
        """Move to the next step. Returns the new current step or None if done."""
        with self._data_lock:
            if name:
                self.name = name
            self.current_step += 1
            if self.current_step > len(ONBOARDING_STEPS):
                self.completed = True
                self.completed_at = time.time()
                self._save()
                return None
            self._save()
            return ONBOARDING_STEPS[self.current_step - 1]

    def get_current(self) -> Optional[OnboardingStep]:
        """Get the current step, or None if done."""
        if self.completed or self.current_step > len(ONBOARDING_STEPS):
            return None
        return ONBOARDING_STEPS[self.current_step - 1]

    def get_step(self, step_id: int) -> Optional[OnboardingStep]:
        for s in ONBOARDING_STEPS:
            if s.id == step_id:
                return s
        return None

    def skip(self) -> None:
        with self._data_lock:
            self.skipped = True
            self.completed_at = time.time()
            self._save()

    def reset(self) -> None:
        """Reset to step 1 (for re-onboarding)."""
        with self._data_lock:
            self.completed = False
            self.current_step = 1
            self.skipped = False
            self.completed_at = 0.0
            self._save()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completed": self.completed,
            "current_step": self.current_step,
            "skipped": self.skipped,
            "completed_at": self.completed_at,
            "name": self.name,
            "should_show": self.should_show(),
            "current_step_data": self.get_current().to_dict() if self.get_current() else None,
        }


def get_onboarding_state() -> OnboardingState:
    return OnboardingState()
