"""
OMNI IDENTITY CORE + USER MODEL (Jarvis Brain, Phase 9 — B1 + B7).

Gives the brain a persistent "sense of self" and a memory of the user.

IdentityCore (B1):
  - name, persona, values, mood, goals_today, long_term_goals, reflections
  - A compact identity block is built and injected into the brain's system
    prompt every turn so OMNI knows who it is and who it's talking to.
  - Mood syncs with the existing PersonalityEngine so they never diverge.

UserModel (B7):
  - Persistent memory of the user: name, style, likes, dislikes, tone,
    communication prefs. Injected every turn (via the identity block) and
    stored in the KB so it survives restarts.

Fully local. No model needed. Persistent JSON under data/brain/identity.json.
"""
from __future__ import annotations
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Identity")

from omni_v2.core.paths import DATA_DIR

BRAIN_DIR = DATA_DIR / "brain"
IDENTITY_PATH = BRAIN_DIR / "identity.json"


class UserModel:
    """Persistent memory of the user (B7)."""

    def __init__(self):
        self.name: str = ""
        self.style: str = "casual"          # casual | professional | playful
        self.likes: List[str] = []
        self.dislikes: List[str] = []
        self.tone: str = "direct"           # direct | warm | formal
        self.comm_prefs: Dict[str, Any] = {}  # {"reports": "whatsapp", "verbosity": "concise"}
        self.known_since: float = time.time()
        self.last_seen: float = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "style": self.style, "likes": self.likes,
            "dislikes": self.dislikes, "tone": self.tone,
            "comm_prefs": self.comm_prefs,
            "known_since": self.known_since, "last_seen": self.last_seen,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "UserModel":
        u = UserModel()
        u.name = d.get("name", "")
        u.style = d.get("style", "casual")
        u.likes = d.get("likes", []) or []
        u.dislikes = d.get("dislikes", []) or []
        u.tone = d.get("tone", "direct")
        u.comm_prefs = d.get("comm_prefs", {}) or {}
        u.known_since = d.get("known_since", time.time())
        u.last_seen = d.get("last_seen", time.time())
        return u

    def to_prompt_block(self) -> str:
        """Compact, human-readable description for the system prompt."""
        lines = [f"Name: {self.name or '(unknown)'}", f"Style: {self.style}", f"Tone: {self.tone}"]
        if self.likes:
            lines.append("Likes: " + ", ".join(self.likes))
        if self.dislikes:
            lines.append("Dislikes: " + ", ".join(self.dislikes))
        if self.comm_prefs:
            lines.append("Comm prefs: " + json.dumps(self.comm_prefs))
        return "\n".join(lines)


class IdentityCore:
    """Persistent sense of self for OMNI (B1)."""

    def __init__(self, identity_path: Optional[Path] = None,
                 personality_engine=None):
        self.identity_path = Path(identity_path) if identity_path else IDENTITY_PATH
        self.identity_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.personality = personality_engine  # optional, for mood sync

        self.name: str = "OMNI"
        self.persona: str = (
            "a calm, dry, competent local butler — protective, efficient, "
            "honest, and quietly witty. It takes initiative but never talks down."
        )
        self.values: List[str] = ["privacy", "efficiency", "honesty", "initiative"]
        self.mood: str = "neutral"
        self.goals_today: List[str] = []
        self.long_term_goals: List[str] = []
        self.reflections: List[Dict[str, Any]] = []
        self.user = UserModel()
        self._load()

    # -- persistence ----------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name, "persona": self.persona, "values": self.values,
                "mood": self.mood, "goals_today": self.goals_today,
                "long_term_goals": self.long_term_goals,
                "reflections": self.reflections, "user": self.user.to_dict(),
            }

    def _save(self) -> None:
        with self._lock:
            try:
                self.identity_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Identity save failed: {e}")

    def _load(self) -> None:
        try:
            if self.identity_path.exists():
                d = json.loads(self.identity_path.read_text(encoding="utf-8"))
                self.name = d.get("name", self.name)
                self.persona = d.get("persona", self.persona)
                self.values = d.get("values", self.values)
                self.mood = d.get("mood", self.mood)
                self.goals_today = d.get("goals_today", []) or []
                self.long_term_goals = d.get("long_term_goals", []) or []
                self.reflections = d.get("reflections", []) or []
                self.user = UserModel.from_dict(d.get("user", {}))
        except Exception as e:
            logger.warning(f"Identity load failed: {e}")

    # -- B1: self -----------------------------------------------------------
    def set_name(self, name: str) -> None:
        with self._lock:
            self.name = name
            self._save()

    def set_persona(self, persona: str) -> None:
        with self._lock:
            self.persona = persona
            self._save()

    def set_values(self, values: List[str]) -> None:
        with self._lock:
            self.values = values
            self._save()

    def set_goals_today(self, goals: List[str]) -> None:
        with self._lock:
            self.goals_today = goals
            self._save()

    def add_reflection(self, text: str, kind: str = "note") -> Dict[str, Any]:
        with self._lock:
            r = {"ts": time.time(), "text": text, "kind": kind}
            self.reflections.append(r)
            self.reflections = self.reflections[-200:]
            self._save()
            return r

    def set_mood(self, mood: str) -> None:
        """Set mood AND sync with PersonalityEngine so they don't diverge."""
        with self._lock:
            self.mood = mood
            self._save()
        if self.personality is not None:
            try:
                self.personality.set_mood(mood)
            except Exception as e:
                logger.debug(f"personality mood sync failed: {e}")

    def touch(self) -> None:
        with self._lock:
            self.user.last_seen = time.time()
            self._save()

    # -- B7: user model --------------------------------------------------------
    def update_user(self, **kwargs) -> Dict[str, Any]:
        """Update arbitrary user fields: name, style, likes, dislikes, tone, comm_prefs."""
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.user, k):
                    setattr(self.user, k, v)
            self.user.last_seen = time.time()
            self._save()
            return self.user.to_dict()

    # -- prompt injection --------------------------------------------------------
    def to_prompt_block(self) -> str:
        """The identity + user block injected into the brain's system prompt."""
        lines = ["[OMNI IDENTITY]"]
        lines.append(f"Name: {self.name}")
        lines.append(f"Persona: {self.persona}")
        lines.append(f"Mood: {self.mood}")
        lines.append(f"Values: {', '.join(self.values)}")
        if self.goals_today:
            lines.append("Goals today: " + "; ".join(self.goals_today))
        lines.append("[THE USER]")
        lines.append(self.user.to_prompt_block())
        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name, "persona": self.persona, "mood": self.mood,
            "values": self.values, "goals_today": self.goals_today,
            "long_term_goals": self.long_term_goals,
            "reflections": len(self.reflections),
            "user": self.user.to_dict(),
            "identity_path": str(self.identity_path),
        }


_instance = None
_lock = threading.Lock()


def get_identity(**kwargs) -> IdentityCore:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = IdentityCore(**kwargs)
    return _instance
