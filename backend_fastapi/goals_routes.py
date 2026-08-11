"""
OMNI GOALS - FastAPI router for the Jarvis Brain goal stack (Phase 9 Step 3).

Exposes persistent goals (create / list / status / advance / fail / abandon /
follow-up) over HTTP so the UI / desktop app can drive OMNI's long-running work.
Fully local.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from omni_v2.brain.goals import GoalStack

_goals = GoalStack()
router = APIRouter(prefix="/api/goals", tags=["goals"])


class GoalCreate(BaseModel):
    intent: str
    title: str = ""
    deadline: Optional[float] = None


class StepResult(BaseModel):
    ok: bool = True
    note: str = ""


class FailRequest(BaseModel):
    error: str = ""
    suggested_fix: str = ""


class FollowUp(BaseModel):
    fu_type: str = "report"
    message: str = ""


@router.get("")
def list_goals(limit: int = 20) -> Dict[str, Any]:
    return {"goals": [g.to_dict() for g in _goals.list_goals(limit)]}


@router.post("")
def create_goal(req: GoalCreate) -> Dict[str, Any]:
    g = _goals.create_goal(req.intent, title=req.title, deadline=req.deadline)
    return {"goal": g.to_dict()}


@router.get("/{goal_id}")
def get_goal(goal_id: str) -> Dict[str, Any]:
    g = _goals.get_goal(goal_id)
    if g is None:
        raise HTTPException(404, "goal not found")
    return {"goal": g.to_dict()}


@router.post("/{goal_id}/advance")
def advance(goal_id: str) -> Dict[str, Any]:
    s = _goals.begin_step(goal_id)
    if s is None:
        g = _goals.get_goal(goal_id)
        return {"runnable": False, "status": g.status if g else "missing"}
    _goals.complete_step(goal_id, result={"ok": True})
    return {"runnable": True, "step": s.desc, "goal": _goals.get_goal(goal_id).to_dict()}


@router.post("/{goal_id}/fail")
def fail(goal_id: str, req: FailRequest) -> Dict[str, Any]:
    g = _goals.fail_step(goal_id, error=req.error, suggested_fix=req.suggested_fix)
    return {"goal": g.to_dict()}


@router.post("/{goal_id}/follow-up")
def follow_up(goal_id: str, req: FollowUp) -> Dict[str, Any]:
    g = _goals.schedule_follow_up(goal_id, fu_type=req.fu_type, message=req.message)
    return {"goal": g.to_dict()}


@router.post("/{goal_id}/abandon")
def abandon(goal_id: str) -> Dict[str, Any]:
    g = _goals.abandon(goal_id)
    return {"goal": g.to_dict()}


@router.post("/{goal_id}/delegate")
def delegate(goal_id: str) -> Dict[str, Any]:
    """Sub-agent delegation (Phase 13 #4): run the goal's steps as parallel
    sub-agents and report back compactly."""
    from omni_v2.away.desktop import DesktopController
    return DesktopController().delegate_goal(goal_id)
