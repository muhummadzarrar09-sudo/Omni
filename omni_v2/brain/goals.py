"""
OMNI GOAL STACK (Jarvis Brain, Phase 9 — Step 3).

A persistent "task/goal brain" that lets OMNI own long-running work the way
Jarvis does:
  - Decompose a big intent into steps (LLM deep tier if available, else a
    deterministic plan).
  - Track progress ACROSS sessions (persisted to data/brain/goals.json).
  - Steps can depend on each other (a simple plan graph), so ordering is
    respected.
  - Replan on failure: a failed step records why and a suggested fix becomes a
    new sub-step (metacognition hook).
  - Follow-through: a goal can schedule a reminder / "report when done" via the
    scheduler + messenger so OMNI comes back to you.

Fully local. The decompose step uses a pluggable `decomposer` (usually the Brain
deep tier); if none is supplied it returns a sensible deterministic plan, so the
core is unit-testable offline with no model.
"""
from __future__ import annotations
import json
import time
import uuid
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Goals")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

GOALS_PATH = DATA_DIR / "brain" / "goals.json"

# statuses
ST_PENDING = "pending"
ST_ACTIVE = "active"
ST_DONE = "done"
ST_ABANDONED = "abandoned"
ST_BLOCKED = "blocked"

# step statuses
STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_DONE = "done"
STEP_FAILED = "failed"


@dataclass
class GoalStep:
    desc: str
    status: str = STEP_PENDING
    depends_on: List[str] = field(default_factory=list)  # step indexes
    result: Optional[Dict[str, Any]] = None
    error: str = ""
    attempts: int = 0
    suggested_fix: str = ""
    tool_hint: str = ""          # e.g. "research", "browser", "files_write"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GoalStep":
        return GoalStep(**d)


@dataclass
class Goal:
    id: str
    title: str
    intent: str
    status: str = ST_PENDING
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    progress: float = 0.0
    steps: List[GoalStep] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    follow_up: Optional[Dict[str, Any]] = None   # {"type": "reminder"/"report", ...}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Goal":
        g = Goal(id=d["id"], title=d["title"], intent=d["intent"])
        g.status = d.get("status", ST_PENDING)
        g.created_at = d.get("created_at", time.time())
        g.deadline = d.get("deadline")
        g.progress = d.get("progress", 0.0)
        g.steps = [GoalStep.from_dict(s) for s in d.get("steps", [])]
        g.history = d.get("history", []) or []
        g.follow_up = d.get("follow_up")
        return g

    # -- progress ---------------------------------------------------------
    def update_progress(self) -> None:
        if not self.steps:
            self.progress = 0.0
            return
        done = sum(1 for s in self.steps if s.status == STEP_DONE)
        self.progress = round(done / len(self.steps), 2)
        if self.progress >= 1.0:
            self.status = ST_DONE
        elif self.status == ST_PENDING:
            self.status = ST_ACTIVE


class GoalStack:
    """Persistent goal manager with decompose / progress / replan / follow-up."""

    def __init__(self, goals_path: Optional[Path] = None,
                 decomposer: Optional[Callable[[str], List[str]]] = None,
                 notifier: Optional[Callable[[str], Any]] = None):
        self.goals_path = Path(goals_path) if goals_path else GOALS_PATH
        self.goals_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        # decomposer(intent) -> list of step descriptions
        self.decomposer = decomposer
        # notifier(text) -> push a message (messenger) for follow-through
        self.notifier = notifier
        self._goals: Dict[str, Goal] = {}
        self._load()

    # -- persistence --------------------------------------------------------
    def _save(self) -> None:
        with self._lock:
            try:
                self.goals_path.write_text(
                    json.dumps({k: v.to_dict() for k, v in self._goals.items()}, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                logger.warning(f"Goals save failed: {e}")

    def _load(self) -> None:
        try:
            if self.goals_path.exists():
                data = json.loads(self.goals_path.read_text(encoding="utf-8"))
                self._goals = {k: Goal.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Goals load failed: {e}")

    # -- lifecycle -----------------------------------------------------------
    def create_goal(self, intent: str, title: str = "", deadline: Optional[float] = None,
                    steps: Optional[List[str]] = None) -> Goal:
        """Create a goal and decompose it into steps."""
        intent = intent.strip()
        if not intent:
            raise ValueError("goal intent cannot be empty")
        with self._lock:
            gid = uuid.uuid4().hex[:12]
            g = Goal(id=gid, title=title or intent[:60], intent=intent, deadline=deadline)
            if steps is None:
                steps = self._decompose(intent)
            g.steps = [GoalStep(desc=s) for s in steps]
            g.update_progress()
            self._goals[gid] = g
            self._save()
            self._log(g, f"goal created with {len(g.steps)} step(s)")
            return g

    def _decompose(self, intent: str) -> List[str]:
        """Decompose an intent into steps. Uses the deep LLM if provided, else deterministic."""
        if self.decomposer is not None:
            try:
                steps = self.decomposer(intent)
                if steps:
                    return steps
            except Exception as e:
                logger.warning(f"decomposer failed ({e}); using deterministic plan")
        return self._deterministic_plan(intent)

    @staticmethod
    def _deterministic_plan(intent: str) -> List[str]:
        """A sensible default plan when no LLM decomposer is available."""
        t = intent.lower()
        if any(w in t for w in ["research", "investigate", "find out", "learn about"]):
            return [
                f"Research: gather information about '{intent}'",
                "Synthesize findings into a summary",
                "Save a report to disk",
            ]
        if any(w in t for w in ["build", "create", "make", "write", "develop"]):
            return [
                f"Plan the build for: '{intent}'",
                "Generate the code / content",
                "Verify it works (tests / run)",
                "Save the result and summarize",
            ]
        if any(w in t for w in ["organize", "clean", "sort", "tidy"]):
            return [
                f"Audit what needs organizing for: '{intent}'",
                "Execute the organization",
                "Report what changed",
            ]
        # generic
        return [
            f"Understand the goal: '{intent}'",
            "Gather required context / inputs",
            "Execute the main action",
            "Verify outcome and report",
        ]

    # -- read --------------------------------------------------------------
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)

    def list_goals(self, limit: int = 30) -> List[Goal]:
        return sorted(self._goals.values(), key=lambda g: g.created_at, reverse=True)[:limit]

    def active_goals(self) -> List[Goal]:
        return [g for g in self._goals.values() if g.status in (ST_PENDING, ST_ACTIVE, ST_BLOCKED)]

    # -- progress & step execution -----------------------------------------
    def next_step(self, goal_id: str) -> Optional[GoalStep]:
        """Return the next runnable step (respecting dependencies) or None."""
        g = self._goals.get(goal_id)
        if g is None or g.status == ST_DONE:
            return None
        for i, s in enumerate(g.steps):
            if s.status != STEP_PENDING:
                continue
            deps_ok = all(
                g.steps[j].status == STEP_DONE for j in s.depends_on
                if j < len(g.steps)
            )
            if deps_ok:
                return s
        return None

    def begin_step(self, goal_id: str) -> Optional[GoalStep]:
        s = self.next_step(goal_id)
        if s is not None:
            s.status = STEP_RUNNING
            s.attempts += 1
            g = self._goals.get(goal_id)
            if g:
                self._log(g, f"begin step: {s.desc}")
                self._save()
        return s

    def complete_step(self, goal_id: str, result: Optional[Dict[str, Any]] = None) -> Goal:
        g = self._goals.get(goal_id)
        if g is None:
            raise KeyError(goal_id)
        for s in g.steps:
            if s.status == STEP_RUNNING:
                s.status = STEP_DONE
                s.result = result or {"ok": True}
        g.update_progress()
        self._log(g, f"step completed; progress={g.progress}")
        if g.status == ST_DONE:
            self._log(g, "GOAL COMPLETE")
            self._maybe_follow_up(g)
        self._save()
        return g

    def fail_step(self, goal_id: str, error: str = "",
                  suggested_fix: str = "", replan: bool = True) -> Goal:
        """Mark the running step failed; optionally add the suggested fix as a new step."""
        g = self._goals.get(goal_id)
        if g is None:
            raise KeyError(goal_id)
        for s in g.steps:
            if s.status == STEP_RUNNING:
                s.status = STEP_FAILED
                s.error = error
                s.suggested_fix = suggested_fix
        if replan and suggested_fix:
            g.steps.append(GoalStep(desc=suggested_fix))
            self._log(g, f"replanned: added fix step '{suggested_fix}'")
        g.status = ST_BLOCKED if not g.status == ST_DONE else g.status
        self._log(g, f"step failed: {error}")
        self._save()
        return g

    def retry_failed(self, goal_id: str) -> Goal:
        """Reset failed steps to pending so they can be re-attempted."""
        g = self._goals.get(goal_id)
        if g is None:
            raise KeyError(goal_id)
        for s in g.steps:
            if s.status == STEP_FAILED:
                s.status = STEP_PENDING
        if g.status == ST_BLOCKED:
            g.status = ST_ACTIVE
        self._log(g, "retried failed step(s)")
        self._save()
        return g

    def abandon(self, goal_id: str) -> Goal:
        g = self._goals.get(goal_id)
        if g is None:
            raise KeyError(goal_id)
        g.status = ST_ABANDONED
        self._log(g, "goal abandoned")
        self._save()
        return g

    # -- follow-through -------------------------------------------------------
    def schedule_follow_up(self, goal_id: str, fu_type: str = "report",
                           message: str = "") -> Goal:
        """Attach a follow-up (reminder / report-when-done) to a goal."""
        g = self._goals.get(goal_id)
        if g is None:
            raise KeyError(goal_id)
        g.follow_up = {"type": fu_type, "message": message or f"Goal '{g.title}' is done."}
        self._log(g, f"follow-up scheduled ({fu_type})")
        self._save()
        return g

    def _maybe_follow_up(self, g: Goal) -> None:
        if g.follow_up and self.notifier is not None:
            try:
                self.notifier(g.follow_up.get("message", f"Goal '{g.title}' complete."))
                self._log(g, "follow-up notification sent")
            except Exception as e:
                logger.warning(f"follow-up notify failed: {e}")

    # -- internal -------------------------------------------------------------
    def _log(self, g: Goal, msg: str) -> None:
        g.history.append({"ts": time.time(), "msg": msg})
        g.history = g.history[-200:]
        logger.info(f"[goal {g.id}] {msg}")

    def stats(self) -> Dict[str, Any]:
        counts = {}
        for g in self._goals.values():
            counts[g.status] = counts.get(g.status, 0) + 1
        return {
            "goals_total": len(self._goals),
            "goals_by_status": counts,
            "goals_path": str(self.goals_path),
        }


_instance = None
_lock = threading.Lock()


def get_goal_stack(**kwargs) -> GoalStack:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GoalStack(**kwargs)
    return _instance
