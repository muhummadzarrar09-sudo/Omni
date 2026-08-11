"""
OMNI AUTOMATION - FastAPI router (Phase 13, #5).
Webhook/schedule/file triggers that wake OMNI. Fully local.
"""
from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from omni_v2.away.desktop import DesktopController

_controller = DesktopController()
router = APIRouter(prefix="/api/automation", tags=["automation"])


class AddTriggerRequest(BaseModel):
    name: str
    trigger: str   # webhook | schedule | file
    action: str    # goal | research | notify | away
    action_args: Dict[str, Any] = {}
    secret: str = ""


@router.get("/status")
def status() -> Dict[str, Any]:
    return {"ok": True, "status": _controller.trigger_stats()}


@router.get("/triggers")
def list_triggers() -> Dict[str, Any]:
    return _controller.trigger_list()


@router.post("/triggers")
def add_trigger(req: AddTriggerRequest) -> Dict[str, Any]:
    return _controller.trigger_add(req.name, req.trigger, req.action,
                                   req.action_args, secret=req.secret)


@router.post("/webhook/{name}")
def webhook(name: str, payload: Dict[str, Any],
            x_omni_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Public webhook endpoint: POST body fires the automation."""
    return _controller.trigger_fire(name, payload or {})
