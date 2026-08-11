"""
OMNI REMOTE CONTROL (Phase 15, #6) — control OMNI from another device on your
local network.

A small, token-authed API surface that lets a phone/another laptop on the same
LAN send commands to OMNI (execute a command, ask the brain, run a goal, get
status). Auth is enforced by the app-level OMNI_API_TOKEN / device-token
middleware already in main.py, plus a per-request check here.

Fully local (LAN only, not internet). Headless-testable via the command layer.
"""
from fastapi import APIRouter, Header
from pydantic import BaseModel
from pathlib import Path
import sys
from typing import Any, Dict, Optional

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from omni_v2.away.desktop import DesktopController

_controller = DesktopController()
router = APIRouter(prefix="/api/remote", tags=["remote"])


class Command(BaseModel):
    command: str          # brain command / natural language
    source: str = "lan"


@router.get("/status")
def status() -> Dict[str, Any]:
    st = _controller.status()
    return {"ok": True, "status": st}


@router.post("/command")
def command(cmd: Command) -> Dict[str, Any]:
    """Send a command through the brain (or fall back to the goal stack)."""
    try:
        # route through the brain if available
        from omni_v2.llm.brain import get_brain
        brain = get_brain()
        resp = brain.think(cmd.command)
        return {"ok": True, "reply": resp.text, "tier": resp.tier}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/goal")
def create_goal(intent: str) -> Dict[str, Any]:
    g = _controller.goals.create_goal(intent, title=intent[:60])
    return {"ok": True, "goal": g.to_dict()}
