"""
OMNI EPISODIC REFLECTION + PATTERN AWARENESS (Jarvis Brain, Phase 9 — Step 5).

The last Jarvis piece: OMNI "notices things on its own" instead of just
responding.

Two halves:
  1. EPISODIC REFLECTION
     At session end (or on demand), build a short "today was..." recap from
     session memory and save it as an episodic memory (kind="episodic") in the
     hybrid RAG+CAG store, plus a reflection entry in the Identity core. This is
     how OMNI accumulates a long-term sense of its own history.

  2. PATTERN AWARENESS
     Scan recent session/episodic records for repeatable patterns and surface
     them as observations/suggestions, e.g.:
       - "You've opened <app/topic> N times today."
       - "You've been stuck on <topic> for N days."  (repeated failure / same
         tool failing)
       - "Most of today was research." (activity blend)
       - "You keep switching tasks." (context switching)

Fully local. No model needed — the reflection summary and patterns are produced
with deterministic rules over the session data, so it's unit-testable offline.
A pluggable `summarizer` can be supplied (e.g. the deep LLM) for richer prose.
"""
from __future__ import annotations
import time
import re
import threading
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Reflect")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

EPISODES_PATH = DATA_DIR / "brain" / "episodes.json"


@dataclass
class Episode:
    ts: float
    day: str
    summary: str
    activity: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Episode":
        return Episode(**d)


class Reflector:
    """Builds episodic recaps and detects patterns from session memory."""

    def __init__(self, session_memory=None, hybrid_memory=None, identity=None,
                 episodes_path: Optional[Path] = None,
                 summarizer: Optional[Callable[[str], str]] = None):
        self.session = session_memory
        self.hybrid = hybrid_memory
        self.identity = identity
        self.episodes_path = Path(episodes_path) if episodes_path else EPISODES_PATH
        self.episodes_path.parent.mkdir(parents=True, exist_ok=True)
        self.summarizer = summarizer  # optional LLM for richer prose
        self._lock = threading.RLock()
        self._episodes: List[Episode] = []
        self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self) -> None:
        try:
            if self.episodes_path.exists():
                self._episodes = [Episode.from_dict(e) for e in
                                  __import__("json").loads(self.episodes_path.read_text(encoding="utf-8"))]
        except Exception as e:
            logger.warning(f"episodes load failed: {e}")

    def _save(self) -> None:
        try:
            import json
            self.episodes_path.write_text(
                json.dumps([e.to_dict() for e in self._episodes], indent=2),
                encoding="utf-8")
        except Exception as e:
            logger.warning(f"episodes save failed: {e}")

    # -- episodic reflection --------------------------------------------------
    def reflect_today(self, days: int = 1) -> Episode:
        """
        Build a "today was..." recap from session memory, save it as an episode,
        store it in hybrid memory (kind=episodic), and log a reflection in the
        Identity core.
        """
        commands, tool_calls, topics = self._collect_session_data(days)
        activity = self._activity_profile(commands, tool_calls)
        summary = self._compose_summary(commands, tool_calls, topics, activity)

        day = time.strftime("%Y-%m-%d")
        ep = Episode(ts=time.time(), day=day, summary=summary, activity=activity)
        with self._lock:
            # avoid duplicate episodes for the same day
            self._episodes = [e for e in self._episodes if e.day != day]
            self._episodes.append(ep)
            self._episodes = self._episodes[-365:]
            self._save()

        # store as episodic memory in the hybrid store (long-term RAG)
        if self.hybrid is not None:
            try:
                self.hybrid.remember(summary, kind="episodic", source="reflection",
                                     title=f"Episodic recap {day}", importance=0.6)
            except Exception as e:
                logger.debug(f"hybrid episodic store failed: {e}")
        # log a reflection in the identity core
        if self.identity is not None:
            try:
                self.identity.add_reflection(summary, kind="episodic")
            except Exception as e:
                logger.debug(f"identity reflection failed: {e}")
        return ep

    def _collect_session_data(self, days: int):
        commands: List[str] = []
        tool_calls: List[str] = []
        topics: List[str] = []
        if self.session is not None:
            try:
                sessions = self.session.recall_sessions(days=days)
                for s in sessions:
                    d = s.to_dict() if hasattr(s, "to_dict") else s
                    commands.extend(d.get("commands", []) or [])
                    tool_calls.extend(d.get("tool_calls", []) or [])
            except Exception as e:
                logger.debug(f"session recall failed: {e}")
        topics = self._extract_topics(" ".join(commands))
        return commands, tool_calls, topics

    @staticmethod
    def _extract_topics(text: str) -> List[str]:
        if not text:
            return []
        words = re.findall(r"[a-z][a-z-]{2,}", text.lower())
        stop = {"the", "and", "for", "you", "your", "omni", "open", "please",
                "with", "that", "this", "from", "have", "what", "how", "can",
                "want", "need", "about", "into", "after", "should", "could"}
        return [w for w in words if w not in stop]

    def _activity_profile(self, commands, tool_calls) -> Dict[str, Any]:
        return {
            "commands": len(commands),
            "tool_calls": len(tool_calls),
            "top_commands": dict(Counter(commands).most_common(5)) if commands else {},
            "top_tools": dict(Counter(tool_calls).most_common(5)) if tool_calls else {},
        }

    def _compose_summary(self, commands, tool_calls, topics, activity) -> str:
        # Optional LLM summarizer for richer prose; else deterministic.
        if self.summarizer is not None:
            try:
                raw = " ".join(commands[:80])
                return self.summarizer(raw) or self._deterministic_summary(commands, activity)
            except Exception:
                pass
        return self._deterministic_summary(commands, activity)

    def _deterministic_summary(self, commands, activity) -> str:
        n = activity["commands"]
        if n == 0:
            return "No notable activity recorded."
        top = list(activity["top_commands"].keys())[:3]
        lines = [f"Today had {n} command(s)."]
        if top:
            lines.append("Most frequent: " + ", ".join(top) + ".")
        return " ".join(lines)

    # -- pattern awareness ------------------------------------------------------
    def detect_patterns(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Scan session data and episodes for patterns. Returns a list of
        observation dicts: {kind, title, body, severity(0-2)}.
        """
        patterns: List[Dict[str, Any]] = []
        commands, tool_calls, topics = self._collect_session_data(days)

        # 1) topic/command repetition
        cc = Counter(commands)
        for cmd, count in cc.most_common(6):
            if count >= 3:
                patterns.append({
                    "kind": "repeat",
                    "title": f"You've done this {count} times",
                    "body": f"'{cmd}' has appeared {count} time(s). Want me to turn it into a goal or shortcut?",
                    "severity": 1,
                })

        # 2) tool repetition (could indicate a task loop)
        tc = Counter(tool_calls)
        for tool, count in tc.most_common(4):
            if count >= 4:
                patterns.append({
                    "kind": "tool_loop",
                    "title": f"Heavy use of {tool}",
                    "body": f"'{tool}' was called {count} time(s). Possible repetitive task or a loop.",
                    "severity": 1,
                })

        # 3) stuck on a topic across days (from episodes)
        stuck = self._detect_stuck_topic()
        if stuck:
            patterns.append(stuck)

        # 4) activity blend (mostly research vs build)
        if commands:
            researchish = sum(1 for c in commands if any(w in c.lower() for w in
                              ["research", "search", "find", "what is", "explain"]))
            if len(commands) >= 5 and researchish / len(commands) >= 0.6:
                patterns.append({
                    "kind": "blend",
                    "title": "Research-heavy session",
                    "body": "Most of the recent activity was research/lookup. Consider a digest of what you learned.",
                    "severity": 0,
                })

        return patterns

    def _detect_stuck_topic(self) -> Optional[Dict[str, Any]]:
        """If the same reflective topic appears in multiple recent episodes, flag it."""
        if len(self._episodes) < 2:
            return None
        recent = self._episodes[-7:]
        day_counts = Counter(e.day for e in recent)
        topic_hits: Dict[str, int] = {}
        for e in recent:
            for w in self._extract_topics(e.summary):
                topic_hits[w] = topic_hits.get(w, 0) + 1
        for topic, n in sorted(topic_hits.items(), key=lambda x: -x[1]):
            if n >= 3 and len(day_counts) >= 2:
                return {
                    "kind": "stuck",
                    "title": f"Repeated theme: {topic}",
                    "body": f"'{topic}' keeps coming up across {n} reflections over several days. "
                            "You may be stuck — want me to plan it as a goal?",
                    "severity": 2,
                }
        return None

    def proactive_suggestions(self, days: int = 7) -> List[Dict[str, Any]]:
        """Patterns that could drive proactive suggestions / notifications."""
        return [p for p in self.detect_patterns(days) if p["severity"] >= 1]

    # -- API ------------------------------------------------------------------
    def episodes(self, n: int = 20) -> List[Episode]:
        with self._lock:
            return self._episodes[-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"episodes": len(self._episodes), "episodes_path": str(self.episodes_path)}


_instance = None
_lock = threading.Lock()


def get_reflector(**kwargs) -> Reflector:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = Reflector(**kwargs)
    return _instance
