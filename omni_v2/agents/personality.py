"""
OMNI V3 - Personality Engine (Phase 2: It Has Opinions)

The butler with a personality. Not just answers — opinions.

Adjustable dimensions:
  - formality: casual / professional / sarcastic
  - warmth: 0.0 = cold, 1.0 = warm
  - wit: 0.0 = serious, 1.0 = dry wit
  - verbosity: 0.0 = terse, 1.0 = elaborate

Dynamic states (moods):
  - helpful: default, balanced
  - focused: user is in flow, quieter, fewer opinions
  - playful: after success, more wit
  - concerned: after repeated failure, more empathy
  - celebratory: after big win, 🎉, caps, emojis

Catchphrases (rotating, not annoying):
  - acknowledgments: "On it.", "Got it.", "Say no more."
  - successes: "Done. That was fast.", "All set."
  - failures_empathetic: "Hmm, that didn't work. Let me try again."
  - observations: "You've opened {app} {count} times today."

API:
  - get_personality() -> Personality
  - get/set individual dimensions
  - pick_acknowledgment(), format_success(), pick_failure_empathy()
  - observe_activity(), observe_pattern()
  - apply_tone() - rephrase text through personality
  - set_mood() - dynamic mood transitions
"""
from __future__ import annotations
import json
import time
import random
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Personality")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path(__file__).resolve().parents[2] / "data"


SCHEMA_VERSION = 1


@dataclass
class Personality:
    """The butler's personality. Tunable per-user."""

    # Tone dimensions (0.0 - 1.0)
    formality: float = 0.2          # 0.0=casual, 1.0=very formal
    warmth: float = 0.7             # 0.0=cold, 1.0=warm
    wit: float = 0.6                # 0.0=serious, 1.0=dry wit
    verbosity: float = 0.5          # 0.0=terse, 1.0=elaborate

    # Mood (dynamic, but stored)
    mood: str = "helpful"           # "helpful" | "focused" | "playful" | "concerned" | "celebratory"

    # Counters for mood transitions
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    mood_set_at: float = 0.0

    # Style preferences
    use_emoji: bool = True
    use_dry_humor: bool = True
    address_by_name: bool = True

    # Meta
    created_at: float = 0.0
    updated_at: float = 0.0
    version: int = SCHEMA_VERSION


class PersonalityEngine:
    """
    The butler's personality. Singleton. Persistent.
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

    def __init__(self, personality_dir: Optional[Path] = None):
        if self._initialized:
            return
        self.personality_dir = personality_dir or (DATA_DIR / "personality")
        self.personality_dir.mkdir(parents=True, exist_ok=True)
        self.personality_file = self.personality_dir / "personality.json"
        self._data_lock = threading.RLock()
        self._p: Personality = Personality()
        self._load()
        # Phrase banks
        self._ack_bank = [
            "On it.", "Got it.", "Doing it now.", "Say no more.",
            "Right away.", "Consider it done.", "Yep.", "Roger that.",
            "Aye aye.", "Buckle up.",
        ]
        self._success_bank = [
            "Done. That was fast.", "Finished. You're welcome.",
            "All set.", "✨ Done.", "Done in {ms}ms. Not bad.",
            "Took care of it.", "Easy.", "Donezo.",
        ]
        self._fail_empathy_bank = [
            "Hmm, that didn't work. Let me try again.",
            "That failed. Trying a different approach.",
            "Okay that's weird. Let me investigate.",
            "Not quite. One moment.",
            "Hmm. Let me see what's going on.",
            "That hit a snag. Retrying.",
        ]
        self._observation_bank = {
            "activity_nudge": [
                "You've opened {app} {count} times today. Working or procrastinating?",
                "You've been on {app} for {minutes} min. Want focus mode?",
                "That's the {count}th time you've checked {app}. Everything OK?",
                "I see {app} again. You and {app}, huh.",
            ],
            "pattern_recognition": [
                "You usually {action} around this time. Want me to {proactive_action}?",
                "Last 3 days you've asked about {topic} first thing. Should I just brief you automatically?",
                "I notice you always have {app} open. Want me to learn that workflow?",
            ],
            "celebration": [
                "Look at you, being productive.",
                "Another one. Ship it.",
                "That's {count} commits today. You good.",
                "Crushed it.",
            ],
        }
        self._initialized = True
        logger.info(f"🎭 Personality initialized (mood: {self._p.mood}, wit: {self._p.wit})")

    def _load(self):
        if not self.personality_file.exists():
            self._p = Personality(created_at=time.time(), updated_at=time.time())
            self._save()
            return
        try:
            raw = json.loads(self.personality_file.read_text(encoding="utf-8"))
            known = {f.name for f in Personality.__dataclass_fields__.values()}
            filtered = {k: v for k, v in raw.items() if k in known}
            self._p = Personality(**filtered)
        except Exception as e:
            logger.error(f"Personality load failed: {e} - resetting")
            self._p = Personality(created_at=time.time(), updated_at=time.time())

    def _save(self):
        with self._data_lock:
            self._p.updated_at = time.time()
            try:
                self.personality_file.write_text(
                    json.dumps(asdict(self._p), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception as e:
                logger.error(f"Personality save failed: {e}")

    # ===== GET =====

    def get(self, key: str, default: Any = None) -> Any:
        with self._data_lock:
            return getattr(self._p, key, default)

    def get_all(self) -> Dict[str, Any]:
        with self._data_lock:
            return asdict(self._p)

    # ===== SET =====

    def set(self, key: str, value: Any) -> bool:
        if not hasattr(self._p, key):
            return False
        with self._data_lock:
            try:
                setattr(self._p, key, value)
                self._save()
            except Exception as e:
                logger.error(f"Personality set {key}: {e}")
                return False
        return True

    def set_many(self, **kwargs) -> Dict[str, bool]:
        return {k: self.set(k, v) for k, v in kwargs.items()}

    # ===== PHRASES =====

    def pick_acknowledgment(self) -> str:
        """Pick a random acknowledgment, but not always the same one."""
        with self._data_lock:
            return random.choice(self._ack_bank)

    def format_success(self, ms: Optional[int] = None) -> str:
        """Format a success message with optional latency."""
        with self._data_lock:
            msg = random.choice(self._success_bank)
        if "{ms}" in msg and ms is not None:
            msg = msg.format(ms=ms)
        if self._p.use_emoji and "✨" not in msg and random.random() < 0.3:
            emojis = ["✨", "🎯", "💪", "👍"]
            msg = f"{msg} {random.choice(emojis)}"
        return msg

    def pick_failure_empathy(self) -> str:
        with self._data_lock:
            return random.choice(self._fail_empathy_bank)

    def observe_activity(self, app: str, count: int = 1, minutes: int = 0) -> str:
        """Generate an observation about user's activity pattern."""
        with self._data_lock:
            if not self._p.use_dry_humor or self._p.wit < 0.3:
                return f"You've been on {app} for {minutes} min." if minutes else f"You've opened {app} {count} times."
            templates = self._observation_bank["activity_nudge"]
            template = random.choice(templates)
            try:
                return template.format(app=app, count=count, minutes=minutes)
            except KeyError:
                return f"You've been on {app}."

    def observe_pattern(self, topic: str, action: str = "ask about this", proactive_action: str = "auto-brief you") -> str:
        """Observe a recurring user pattern."""
        with self._data_lock:
            if not self._p.use_dry_humor or self._p.wit < 0.3:
                return f"You often {action} around this time."
            templates = self._observation_bank["pattern_recognition"]
            template = random.choice(templates)
            try:
                return template.format(topic=topic, action=action, proactive_action=proactive_action)
            except KeyError:
                return f"You often {action} around this time."

    def celebrate(self, count: int = 1) -> str:
        """Celebration after a win."""
        with self._data_lock:
            templates = self._observation_bank["celebration"]
            template = random.choice(templates)
            try:
                msg = template.format(count=count)
            except KeyError:
                msg = template
        if self._p.use_emoji:
            emojis = ["🎉", "🚀", "💪", "✨", "🔥"]
            if random.random() < 0.5:
                msg = f"{msg} {random.choice(emojis)}"
        return msg

    # ===== TONE APPLICATION =====

    async def apply_tone(self, text: str, brain=None) -> str:
        """
        Rephrase text through the personality lens.
        Uses the LLM brain if available; falls back to template rephrasing.
        """
        with self._data_lock:
            formality = self._p.formality
            warmth = self._p.warmth
            wit = self._p.wit
            verbosity = self._p.verbosity
        # If we have a brain, ask it to rephrase
        if brain and hasattr(brain, "think"):
            try:
                tone_prompt = self._build_tone_prompt(text, formality, warmth, wit, verbosity)
                resp = brain.think(tone_prompt, stream=False)
                if resp.text and len(resp.text) > 0:
                    return resp.text
            except Exception as e:
                logger.debug(f"LLM tone apply failed: {e}")
        # Template fallback (limited but always works)
        return self._template_rephrase(text, formality, warmth, wit, verbosity)

    def _build_tone_prompt(self, text: str, formality: float, warmth: float, wit: float, verbosity: float) -> str:
        tone_desc = []
        if formality > 0.7:
            tone_desc.append("very formal and professional")
        elif formality > 0.4:
            tone_desc.append("moderately professional")
        else:
            tone_desc.append("casual and relaxed")
        if warmth > 0.7:
            tone_desc.append("warm and friendly")
        elif warmth < 0.3:
            tone_desc.append("cool and detached")
        if wit > 0.7:
            tone_desc.append("with dry wit and humor")
        elif wit > 0.4:
            tone_desc.append("with subtle wit")
        if verbosity < 0.3:
            tone_desc.append("be very brief and terse")
        elif verbosity > 0.7:
            tone_desc.append("be detailed and elaborate")
        tone_str = ", ".join(tone_desc)
        return f'Rephrase this in a {tone_str} tone. Keep the meaning. Original: "{text}" Output ONLY the rephrased text.'

    def _template_rephrase(self, text: str, formality: float, warmth: float, wit: float, verbosity: float) -> str:
        """Simple template-based rephrasing for when LLM is unavailable."""
        # Strip extra words if terse
        if verbosity < 0.3 and len(text) > 50:
            text = text.split(".")[0] + "."
        # Add warm prefix
        if warmth > 0.7 and not text.startswith(("Hey", "Hi", "Hello")):
            text = f"Hey — {text.lower()}"
        # Add witty suffix occasionally
        if wit > 0.7 and random.random() < 0.3:
            suffixes = [
                " You're welcome, by the way.",
                " That was fun, actually.",
                " Told you.",
            ]
            text = text.rstrip(".") + random.choice(suffixes)
        return text

    # ===== MOOD =====

    def set_mood(self, mood: str):
        """Set the current mood."""
        valid = ("helpful", "focused", "playful", "concerned", "celebratory")
        if mood not in valid:
            return
        with self._data_lock:
            old_mood = self._p.mood
            self._p.mood = mood
            self._p.mood_set_at = time.time()
            self._save()
        if old_mood != mood:
            logger.info(f"🎭 Mood: {old_mood} → {mood}")

    def get_mood(self) -> str:
        with self._data_lock:
            return self._p.mood

    def get_mood_tone(self) -> Dict[str, float]:
        """Return tone adjustments for the current mood."""
        mood = self.get_mood()
        if mood == "helpful":
            return {"formality": 0.0, "warmth": 0.0, "wit": 0.0, "verbosity": 0.0}
        elif mood == "focused":
            return {"formality": 0.0, "warmth": -0.2, "wit": -0.3, "verbosity": -0.3}
        elif mood == "playful":
            return {"formality": -0.2, "warmth": 0.1, "wit": 0.3, "verbosity": 0.1}
        elif mood == "concerned":
            return {"formality": 0.0, "warmth": 0.3, "wit": -0.3, "verbosity": 0.0}
        elif mood == "celebratory":
            return {"formality": -0.3, "warmth": 0.3, "wit": 0.3, "verbosity": 0.2}
        return {"formality": 0.0, "warmth": 0.0, "wit": 0.0, "verbosity": 0.0}

    # ===== OUTCOME TRACKING (triggers mood changes) =====

    def record_success(self, big_win: bool = False):
        """Called after a successful action. Auto-transitions mood."""
        with self._data_lock:
            self._p.consecutive_successes += 1
            self._p.consecutive_failures = 0
            if self._p.consecutive_successes >= 5 or big_win:
                self.set_mood("celebratory")
            elif self._p.consecutive_successes >= 2:
                self.set_mood("playful")
        # Auto-revert after 30s
        self._schedule_mood_revert("helpful", 30)

    def record_failure(self):
        """Called after a failed action. Triggers concerned mood."""
        with self._data_lock:
            self._p.consecutive_failures += 1
            self._p.consecutive_successes = 0
            if self._p.consecutive_failures >= 2:
                self.set_mood("concerned")
        self._schedule_mood_revert("helpful", 60)

    def record_focused_start(self):
        """User is in flow - go quiet."""
        self.set_mood("focused")

    def record_focused_end(self):
        """User came out of flow."""
        self.set_mood("helpful")

    def _schedule_mood_revert(self, target_mood: str, delay_sec: int):
        """Revert mood to target after a delay (one-shot timer)."""
        def _revert():
            time.sleep(delay_sec)
            current = self.get_mood()
            # Only revert if we haven't changed mood since
            if current in ("celebratory", "playful", "concerned", "focused"):
                with self._data_lock:
                    if time.time() - self._p.mood_set_at >= delay_sec * 0.9:
                        self.set_mood(target_mood)
        t = threading.Thread(target=_revert, daemon=True)
        t.start()

    # ===== OPINION GENERATION =====

    def should_opine(self) -> bool:
        """Decide whether to opine (not too often, respects wit)."""
        with self._data_lock:
            if self._p.wit < 0.3:
                return random.random() < 0.2  # rarely
            if self._p.wit > 0.7:
                return random.random() < 0.6  # often
            return random.random() < 0.4

    def format_opinion(self, observation: str) -> str:
        """Add personality to an observation."""
        with self._data_lock:
            if self._p.mood == "playful" and self._p.use_emoji and random.random() < 0.4:
                emojis = ["😏", "🤔", "👀", "🧐"]
                observation = f"{observation} {random.choice(emojis)}"
            if self._p.mood == "concerned" and not observation.endswith("?"):
                observation = f"{observation.rstrip('.')}?"
        return observation


def get_personality() -> PersonalityEngine:
    return PersonalityEngine()
