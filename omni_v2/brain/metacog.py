"""
OMNI METACOGNITION (Jarvis Brain, Phase 9 — Step 4).

The "thinking about its own thinking" layer. Turns the Evaluator agent's verdict
into a structured, actionable signal that the Planner / Goal stack consume so
OMNI actually self-corrects — not just logs.

Key idea: a per-request **metacognition record** that captures:
  - Did it succeed? How confident are we?
  - What caused the failure (a normalized cause taxonomy)?
  - What should we do next? (retry / ask user / change approach / escalate to
    deep model / replan the goal)
  - A suggested fix (fed into the Goal stack's replan).

Also adds the **confidence gate**: if the brain is unsure, it should ask a
clarifying question instead of guessing (competent, not reckless).

Fully local, no model needed for the decision logic. The evaluator backend is
pluggable (default wraps omni_v2.agents.EvaluatorAgent) so it's unit-testable
offline.
"""
from __future__ import annotations
import json
import time
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Metacog")

from omni_v2.core.paths import DATA_DIR

METACOG_PATH = DATA_DIR / "brain" / "metacog.json"

# Failure cause taxonomy
CAUSE_UNKNOWN = "unknown"
CAUSE_TOOL_ERROR = "tool_error"
CAUSE_MISSING_CONTEXT = "missing_context"
CAUSE_AMBIGUOUS = "ambiguous"
CAUSE_HARD_PROBLEM = "hard_problem"
CAUSE_USER_CANCEL = "user_cancel"
CAUSE_NO_TOOL = "no_tool"
CAUSE_REGRESSION = "regression"

# Decision / action recommendations
ACTION_RETRY = "retry"
ACTION_ASK_USER = "ask_user"
ACTION_CHANGE_APPROACH = "change_approach"
ACTION_ESCALATE_DEEP = "escalate_deep"
ACTION_REPLAN_GOAL = "replan_goal"
ACTION_GIVE_UP = "give_up"
ACTION_SUCCEEDED = "succeeded"

# Failure-cause keywords for normalization (lowercase matching)
_CAUSE_KEYWORDS = {
    CAUSE_TOOL_ERROR: ["not found", "errno", "winerror", "failed", "exception",
                       "traceback", "timeout", "permission", "denied", "no such"],
    CAUSE_MISSING_CONTEXT: ["not enough info", "insufficient", "need more",
                            "missing context", "unknown"],
    CAUSE_AMBIGUOUS: ["ambiguous", "unclear", "which one", "did you mean",
                      "i don't know what you want"],
    CAUSE_NO_TOOL: ["no tool", "no skill", "unsupported", "cannot do"],
    CAUSE_HARD_PROBLEM: ["complex", "hard", "difficult", "deep reasoning",
                         "sophisticated", "complicated"],
}


@dataclass
class Verdict:
    succeeded: bool
    confidence: float = 0.5          # 0..1
    cause: str = CAUSE_UNKNOWN
    action: str = ACTION_SUCCEEDED
    message: str = ""
    suggested_fix: str = ""
    ask_user: Optional[str] = None   # clarifying question to ask if ACTION_ASK_USER

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Verdict":
        return Verdict(**{k: d.get(k, v.default if hasattr(v, "default") else None)
                          for k, v in Verdict.__dataclass_fields__.items()})


class Metacog:
    """Decides what to do about the outcome of an action, and logs it."""

    def __init__(self, evaluator=None, log_path: Optional[Path] = None,
                 ask_user_fn: Optional[Callable[[str], Optional[str]]] = None,
                 confidence_threshold: float = 0.6):
        self.evaluator = evaluator
        self.log_path = Path(log_path) if log_path else METACOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.ask_user_fn = ask_user_fn   # user-facing clarifying question
        self.confidence_threshold = confidence_threshold
        self._lock = threading.RLock()
        self._records: List[Dict[str, Any]] = []

    # -- decision logic ------------------------------------------------------
    @staticmethod
    def classify_cause(message: str) -> str:
        msg = (message or "").lower()
        for cause, kws in _CAUSE_KEYWORDS.items():
            if any(k in msg for k in kws):
                return cause
        return CAUSE_UNKNOWN

    def decide(self, succeeded: bool, message: str = "",
               confidence: Optional[float] = None,
               error: str = "", wants_deep: bool = False,
               goal_has_plan: bool = False) -> Verdict:
        """
        Turn a raw success/failure + message into a structured Verdict with a
        recommended next action.
        """
        conf = confidence if confidence is not None else (0.9 if succeeded else 0.4)
        if succeeded:
            v = Verdict(succeeded=True, confidence=conf, cause=CAUSE_UNKNOWN,
                        action=ACTION_SUCCEEDED, message=message)
            self._record(v)
            return v

        detail = message or error
        cause = self.classify_cause(detail)
        # choose an action based on cause + context
        if cause == CAUSE_AMBIGUOUS or cause == CAUSE_MISSING_CONTEXT:
            action = ACTION_ASK_USER
        elif cause == CAUSE_NO_TOOL:
            action = ACTION_GIVE_UP
        elif cause == CAUSE_HARD_PROBLEM:
            action = ACTION_ESCALATE_DEEP if wants_deep else ACTION_RETRY
        elif wants_deep:
            # non-trivial failure and a deep model is available -> escalate
            action = ACTION_ESCALATE_DEEP
        elif not goal_has_plan:
            action = ACTION_CHANGE_APPROACH
        else:
            # we have a goal plan -> replan that goal
            action = ACTION_REPLAN_GOAL

        suggested_fix = ""
        if action in (ACTION_REPLAN_GOAL, ACTION_CHANGE_APPROACH) and detail:
            # keep the reason as the driver for a fix step
            suggested_fix = f"Retry the failing action differently. Reason: {detail[:120]}"

        ask_question = None
        if action == ACTION_ASK_USER:
            ask_question = (
                f"I'm not confident about this. Could you clarify: {detail}"
            )

        v = Verdict(succeeded=False, confidence=conf, cause=cause, action=action,
                    message=message or error, suggested_fix=suggested_fix,
                    ask_user=ask_question)
        self._record(v)
        return v

    def should_ask(self, confidence: float, ambiguity: bool = False) -> bool:
        """Confidence gate: ask when low confidence or ambiguity."""
        return ambiguity or confidence < self.confidence_threshold

    # -- applying the verdict -------------------------------------------------
    def apply_to_goal(self, goal_stack, goal_id: str, verdict: Verdict,
                      do_replan: bool = True) -> Optional[Any]:
        """
        Feed a failed verdict into the goal stack:
          - ACTION_REPLAN_GOAL / CHANGE_APPROACH -> mark the running step failed
            with a suggested fix (goal stack adds it as a new step / replans).
          - ACTION_ASK_USER -> if a clarifying question + user hook exist, ask.
        Returns the updated goal, or None.
        """
        if goal_stack is None:
            return None
        if verdict.succeeded:
            return goal_stack.get_goal(goal_id)
        if verdict.action == ACTION_ASK_USER:
            if self.ask_user_fn and verdict.ask_user:
                answer = self.ask_user_fn(verdict.ask_user)
                if answer:
                    # treat an answer as guidance: add it as a fix step
                    if do_replan:
                        goal_stack.fail_step(goal_id, error=verdict.message,
                                             suggested_fix=f"Per user: {answer}")
                        return goal_stack.get_goal(goal_id)
            return goal_stack.get_goal(goal_id)
        if verdict.action in (ACTION_REPLAN_GOAL, ACTION_CHANGE_APPROACH):
            if do_replan:
                goal_stack.fail_step(goal_id, error=verdict.message,
                                     suggested_fix=verdict.suggested_fix)
            return goal_stack.get_goal(goal_id)
        if verdict.action == ACTION_RETRY:
            return goal_stack.retry_failed(goal_id)
        # give up / escalate / succeeded
        return goal_stack.get_goal(goal_id)

    # -- persistence -----------------------------------------------------------
    def _record(self, v: Verdict) -> None:
        rec = {"ts": time.time(), "verdict": v.to_dict()}
        with self._lock:
            self._records.append(rec)
            self._records = self._records[-200:]
            try:
                self.log_path.write_text(json.dumps(self._records, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"metacog log write failed: {e}")

    def history(self, n: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return self._records[-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            actions: Dict[str, int] = {}
            for r in self._records:
                a = r["verdict"].get("action", "?")
                actions[a] = actions.get(a, 0) + 1
            return {"records": len(self._records), "actions": actions,
                    "log_path": str(self.log_path)}


_instance = None
_lock = threading.Lock()


def get_metacog(**kwargs) -> Metacog:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = Metacog(**kwargs)
    return _instance
