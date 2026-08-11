"""
OMNI AUTOMATION - FastAPI router (Phase 13, #5).
Webhook/schedule/file triggers that wake OMNI. Fully local.
"""
from fastapi import APIRouter, Header
from pydantic import BaseModel
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
