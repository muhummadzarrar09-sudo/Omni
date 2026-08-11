"""
OMNI CONTINUAL HARNESS - FastAPI router (Phase 12).
Exposes the self-refining skills/memory/lessons store over HTTP. Fully local.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from omni_v2.away.desktop import DesktopController

_controller = DesktopController()
router = APIRouter(prefix="/api/harness", tags=["harness"])


class RefineRequest(BaseModel):
    goal_id: str
    success: Optional[bool] = None
    repeated: bool = False


class RollbackRequest(BaseModel):
    kind: str
    name: str


class ContextRequest(BaseModel):
    topic: str = ""


@router.get("/status")
def status() -> Dict[str, Any]:
    return {"ok": True, "status": _controller.harness_stats()}


@router.get("/list")
def list(kind: str = "") -> Dict[str, Any]:
    return _controller.harness_list(kind)


@router.post("/refine")
def refine(req: RefineRequest) -> Dict[str, Any]:
    return _controller.harness_refine_goal(req.goal_id, success=req.success,
                                           repeated=req.repeated)


@router.post("/rollback")
def rollback(req: RollbackRequest) -> Dict[str, Any]:
    return _controller.harness_rollback(req.kind, req.name)


@router.post("/context")
def context(req: ContextRequest) -> Dict[str, Any]:
    return {"ok": True, "context": _controller.harness_context(req.topic)}
