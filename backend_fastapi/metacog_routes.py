"""
OMNI METACOGNITION - FastAPI router (Jarvis Brain Phase 9 Step 4).

Evaluate an action's outcome -> structured Verdict, and feed it back into a
goal (replan / ask user / escalate). Fully local.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from omni_v2.brain.metacog import Metacog, Verdict
from omni_v2.brain.goals import GoalStack

_metacog = Metacog()
_goals = GoalStack()
router = APIRouter(prefix="/api/metacog", tags=["metacog"])


class EvaluateRequest(BaseModel):
    message: str = ""
    error: str = ""
    succeeded: bool = False
    goal_id: Optional[str] = None
    wants_deep: bool = False


class ApplyRequest(BaseModel):
    goal_id: str
    verdict: Dict[str, Any]


@router.post("/evaluate")
def evaluate(req: EvaluateRequest) -> Dict[str, Any]:
    v = _metacog.decide(req.succeeded, message=req.message, error=req.error,
                        wants_deep=req.wants_deep, goal_has_plan=bool(req.goal_id))
    result = {"verdict": v.to_dict()}
    if req.goal_id:
        result["goal"] = _metacog.apply_to_goal(_goals, req.goal_id, v, do_replan=True).to_dict()
    return result


@router.post("/apply")
def apply(req: ApplyRequest) -> Dict[str, Any]:
    v = Verdict.from_dict(req.verdict)
    g = _metacog.apply_to_goal(_goals, req.goal_id, v, do_replan=True)
    if g is None:
        raise HTTPException(404, "goal not found")
    return {"goal": g.to_dict()}


@router.get("/history")
def history(limit: int = 20) -> Dict[str, Any]:
    return {"records": _metacog.history(limit)}


@router.get("/stats")
def stats() -> Dict[str, Any]:
    return _metacog.stats()
