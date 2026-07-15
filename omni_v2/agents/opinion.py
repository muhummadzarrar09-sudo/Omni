"""
OMNI V3 - Opinion Engine (Phase 2: It Has Opinions)

The "it has opinions" brain. Decides WHEN to add a comment to a response
based on context: activity patterns, time, success/failure, repetition.

Rules:
  - User opened same app 3+ times in 30 min → "You've opened X 4 times..."
  - User spent >2hrs without break → break reminder
  - User asked about same topic 3+ times today → "Last 3 days you..."
  - User's disk is filling up → "FYI: your disk is sad"
  - It's Friday afternoon → "Friday wrap-up?"
  - User just finished a hard task → celebrate
  - User failed at something twice → encourage
  - User just had a big commit → "Look at you, being productive"

Limits:
  - Max 1 opinion per response
  - Max 3 opinions per hour
  - Respects personality.wit
  - Disabled in "focused" mood
"""
from __future__ import annotations
import time
import threading
import random
from pathlib import Path
from typing import Optional, Dict, List, Any
from collections import defaultdict
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("OpinionEngine")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


class OpinionEngine:
    """
    The butler that has opinions. Singleton. Bounded.
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

    def __init__(self):
        if self._initialized:
            return
        # State for opinion generation
        self._command_timestamps: Dict[str, List[float]] = defaultdict(list)  # command -> timestamps
        self._tool_timestamps: Dict[str, List[float]] = defaultdict(list)    # tool -> timestamps
        self._opinions_this_hour: List[float] = []  # list of timestamps
        self._last_opinion_at: float = 0.0
        self._data_lock = threading.RLock()
        self._initialized = True
        logger.info("💬 OpinionEngine initialized")

    def _prune_old(self, timestamps: List[float], window_sec: float) -> List[float]:
        """Remove timestamps older than window_sec."""
        cutoff = time.time() - window_sec
        return [t for t in timestamps if t >= cutoff]

    def record_command(self, command: str) -> None:
        """Record a command for repetition analysis."""
        with self._data_lock:
            key = command.lower().strip()[:80]
            self._command_timestamps[key].append(time.time())
            # Auto-prune (keep only last hour)
            self._command_timestamps[key] = self._prune_old(self._command_timestamps[key], 3600)

    def record_tool_call(self, tool: str) -> None:
        """Record a tool call for repetition analysis."""
        with self._data_lock:
            self._tool_timestamps[tool].append(time.time())
            self._tool_timestamps[tool] = self._prune_old(self._tool_timestamps[tool], 3600)

    def _should_opine(self) -> bool:
        """Check rate limits."""
        with self._data_lock:
            now = time.time()
            # Prune old
            self._opinions_this_hour = [t for t in self._opinions_this_hour if now - t < 3600]
            # Max 1 per 30 seconds, max 3 per hour
            if now - self._last_opinion_at < 30:
                return False
            if len(self._opinions_this_hour) >= 3:
                return False
            # Check personality
            try:
                from omni_v2.agents.personality import get_personality
                p = get_personality()
                if not p.should_opine():
                    return False
                # Don't opine in focused mood
                if p.get_mood() == "focused":
                    return False
            except Exception:
                pass
            return True

    def _emit(self, opinion: str) -> None:
        """Record that we emitted an opinion."""
        with self._data_lock:
            self._opinions_this_hour.append(time.time())
            self._last_opinion_at = time.time()
        logger.info(f"💬 Opinion: {opinion[:100]}")

    def maybe_opine(self, action: str, result: Any, context: Optional[Dict] = None) -> Optional[str]:
        """
        Called after every action. Returns an opinion or None.
        Strategy: try rules in order; first match wins.
        """
        context = context or {}
        if not self._should_opine():
            return None

        # Rule priority order
        rules = [
            self._rule_repeating_command,
            self._rule_repeating_tool,
            self._rule_friday_evening,
            self._rule_late_night,
            self._rule_success_celebration,
            self._rule_failure_encouragement,
            self._rule_morning_pattern,
        ]
        for rule in rules:
            try:
                opinion = rule(action, result, context)
                if opinion:
                    self._emit(opinion)
                    return opinion
            except Exception as e:
                logger.debug(f"Opinion rule {rule.__name__}: {e}")
        return None

    def _rule_repeating_command(self, action: str, result: Any, context: Dict) -> Optional[str]:
        """Same command 3+ times in 30 min"""
        key = action.lower().strip()[:80]
        with self._data_lock:
            recent = self._prune_old(self._command_timestamps.get(key, []), 1800)
            self._command_timestamps[key] = recent
        if len(recent) >= 3:
            try:
                from omni_v2.agents.personality import get_personality
                p = get_personality()
                # Extract subject from command
                subject = action.split()[1] if len(action.split()) > 1 else "that"
                return p.observe_activity(subject, count=len(recent))
            except Exception:
                return f"You've asked that {len(recent)} times in 30 min."
        return None

    def _rule_repeating_tool(self, action: str, result: Any, context: Dict) -> Optional[str]:
        """Same tool 5+ times in 30 min"""
        if action not in self._tool_timestamps:
            return None
        with self._data_lock:
            recent = self._prune_old(self._tool_timestamps[action], 1800)
        if len(recent) >= 5:
            # Only fire occasionally
            if random.random() > 0.3:
                return None
            try:
                from omni_v2.agents.personality import get_personality
                p = get_personality()
                # Format tool name: browser_navigate -> browser
                app = action.split("_")[0] if "_" in action else action
                return p.observe_activity(app, count=len(recent))
            except Exception:
                return None
        return None

    def _rule_friday_evening(self, action: str, result: Any, context: Dict) -> Optional[str]:
        """Friday after 4pm: wrap-up nudge"""
        now = datetime.now()
        if now.weekday() != 4:  # Friday
            return None
        if not (16 <= now.hour < 18):
            return None
        if random.random() > 0.2:
            return None
        if action in ("code_commit", "git_commit", "files_write"):
            return "It's Friday and you've shipped something. Want me to wrap up your week?"
        return None

    def _rule_late_night(self, action: str, result: Any, context: Dict) -> Optional[str]:
        """After 11pm: gentle 'go to sleep' nudge"""
        now = datetime.now()
        if not (23 <= now.hour or now.hour < 3):
            return None
        if random.random() > 0.1:
            return None
        return "It's late. Consider wrapping up — your future self will thank you."

    def _rule_success_celebration(self, action: str, result: Any, context: Dict) -> Optional[str]:
        """Celebrate after successful commits or big actions"""
        if not result or not getattr(result, "success", False):
            return None
        if action in ("code_commit", "git_commit", "git_push", "vscode_save"):
            try:
                from omni_v2.agents.user_profile import get_user_profile
                profile = get_user_profile()
                # Count commits today
                # We don't have a perfect count, so use the recent tool timestamps
                count = len(self._tool_timestamps.get(action, []))
                if count > 1:  # only celebrate on 2nd+ commit
                    from omni_v2.agents.personality import get_personality
                    p = get_personality()
                    return p.celebrate(count=count)
            except Exception:
                return "Shipped it. 🎉"
        return None

    def _rule_failure_encouragement(self, action: str, result: Any, context: Dict) -> Optional[str]:
        """Encourage after failures (max 1 per failure)"""
        if not result or getattr(result, "success", True):
            return None
        # Don't opine if we just opined
        if time.time() - self._last_opinion_at < 60:
            return None
        try:
            from omni_v2.agents.personality import get_personality
            p = get_personality()
            return p.pick_failure_empathy()
        except Exception:
            return "Hmm, that didn't work. Retrying."

    def _rule_morning_pattern(self, action: str, result: Any, context: Dict) -> Optional[str]:
        """Morning: if user opens same app 2+ times, suggest focus mode"""
        now = datetime.now()
        if not (7 <= now.hour < 10):
            return None
        if action in ("browser_navigate", "browser_search") and result.success:
            if random.random() > 0.15:
                return None
            return "Morning deep-work mode? I can mute non-urgent notifications for the next 2 hours."
        return None

    def opine_proactive(self) -> Optional[str]:
        """Called by the proactive engine to generate an unsolicited opinion."""
        if not self._should_opine():
            return None
        try:
            from omni_v2.agents.personality import get_personality
            p = get_personality()
            # Pattern recognition based on time
            now = datetime.now()
            if 13 <= now.hour < 14:
                return "It's lunchtime. Step away from the screen for 15 min."
            elif 15 <= now.hour < 16:
                return "Afternoon slump. Want a 5-min break or some lo-fi?"
            elif 17 <= now.hour < 18:
                return "Almost end of day. Want me to prep your shutdown?"
            return None
        except Exception:
            return None


def get_opinion_engine() -> OpinionEngine:
    return OpinionEngine()
