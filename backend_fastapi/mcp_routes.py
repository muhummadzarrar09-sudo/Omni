"""
OMNI MCP - FastAPI router (Phase 13). Connect to the MCP ecosystem.
Fully local.
"""
from fastapi import APIRouter
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
router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class ToolDef(BaseModel):
    name: str
    description: str = ""
    inputSchema: Dict[str, Any] = {}


class AddServerRequest(BaseModel):
    name: str
    tools: List[ToolDef] = []
    handlers: Dict[str, Any] = {}


@router.get("/status")
def status() -> Dict[str, Any]:
    return {"ok": True, "status": _controller.mcp_stats()}


@router.get("/servers")
def list_servers() -> Dict[str, Any]:
    return _controller.mcp_list()


@router.post("/servers")
def add_server(req: AddServerRequest) -> Dict[str, Any]:
    tools = [t.model_dump() for t in req.tools]
    return _controller.mcp_add_server(req.name, tools, req.handlers)
