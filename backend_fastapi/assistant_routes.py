"""
OMNI ASSISTANT - FastAPI router for Voice Loop + Guardian (Phase 10).

Exposes the hands-free voice loop and proactive guardian over HTTP so the web
UI / desktop can drive them. Fully local.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from omni_v2.away.desktop import DesktopController

_controller = DesktopController()
router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class SayRequest(BaseModel):
    text: str


class ScanRequest(BaseModel):
    pass


@router.get("/voice/status")
def voice_status() -> Dict[str, Any]:
    return {"ok": True, "status": _controller.voice_stats()}


@router.post("/voice/start")
def voice_start() -> Dict[str, Any]:
    return _controller.voice_start()


@router.post("/voice/stop")
def voice_stop() -> Dict[str, Any]:
    return _controller.voice_stop()


@router.post("/voice/say")
def voice_say(req: SayRequest) -> Dict[str, Any]:
    return _controller.voice_respond(req.text)


@router.get("/guardian/status")
def guardian_status() -> Dict[str, Any]:
    g = _controller._get_guardian()
    return {"ok": True, "status": g.stats() if g else {"running": False}}


@router.post("/guardian/start")
def guardian_start() -> Dict[str, Any]:
    return _controller.guardian_start()


@router.post("/guardian/stop")
def guardian_stop() -> Dict[str, Any]:
    return _controller.guardian_stop()


@router.post("/guardian/scan")
def guardian_scan() -> Dict[str, Any]:
    return _controller.guardian_run_once()


@router.get("/guardian/recent")
def guardian_recent(limit: int = 30) -> Dict[str, Any]:
    return {"observations": (_controller.guardian_recent()[:limit] if _controller.guardian else [])}
