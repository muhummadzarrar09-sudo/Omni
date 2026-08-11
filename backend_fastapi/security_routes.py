"""
OMNI SECURITY - FastAPI router (Phase 8) exposed over HTTP.

Exposes the local camera guard + lockdown so the web UI / desktop can drive it:
  status, enroll owner (multi-sample), arm/disarm guard, snapshot verdict,
  manual lock, lockdown history. Fully local.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import sys
from typing import Any, Dict, Optional

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from omni_v2.security.face_auth import FaceAuth
from omni_v2.security.guard_monitor import GuardMonitor
from omni_v2.security.lockdown import LockdownController

_face_auth = FaceAuth()
_lockdown = LockdownController()
_guard = GuardMonitor(face_auth=_face_auth, lockdown=_lockdown)
router = APIRouter(prefix="/api/security", tags=["security"])


class EnrollRequest(BaseModel):
    frames: int = 6
    delay: float = 0.25


class LockRequest(BaseModel):
    reason: str = "manual lock from OMNI"


@router.get("/status")
def status() -> Dict[str, Any]:
    st = _face_auth.stats()
    st["guard"] = _guard.stats()
    st["lockdown_history"] = _lockdown.history(n=5)
    return st


@router.post("/enroll")
def enroll(req: EnrollRequest) -> Dict[str, Any]:
    try:
        res = _face_auth.enroll_from_camera(frames=req.frames, delay=req.delay)
        return {"ok": True, "detail": f"enrolled (backend={res['backend']}, samples={res['samples']})"}
    except Exception as e:
        raise HTTPException(400, f"enroll failed: {e}") from e


@router.post("/guard/arm")
def arm() -> Dict[str, Any]:
    ok = _guard.arm()
    return {"ok": ok, "detail": "armed" if ok else "cannot arm (enroll owner / no camera)"}


@router.post("/guard/disarm")
def disarm() -> Dict[str, Any]:
    _guard.disarm()
    return {"ok": True, "detail": "disarmed"}


@router.get("/guard/snapshot")
def snapshot() -> Dict[str, Any]:
    return _guard.snapshot()


@router.post("/lock")
def lock(req: LockRequest) -> Dict[str, Any]:
    ev = _lockdown.lock_with_countdown(reason=req.reason, block=False)
    return {"ok": True, "detail": f"lock in {ev['countdown']}s", "event": ev}
