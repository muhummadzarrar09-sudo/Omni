"""
OMNI BRAIN - FastAPI router for the Jarvis Identity Core (Phase 9).

Exposes the persistent sense-of-self (B1) + user model (B7) over HTTP so the
UI / desktop app can read and update it. Fully local.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import sys
from typing import Any, Dict, Optional, List

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from omni_v2.brain.identity import IdentityCore

_identity = IdentityCore()
router = APIRouter(prefix="/api/brain", tags=["brain"])


class IdentityUpdate(BaseModel):
    name: Optional[str] = None
    persona: Optional[str] = None
    values: Optional[List[str]] = None
    mood: Optional[str] = None
    goals_today: Optional[List[str]] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    style: Optional[str] = None
    tone: Optional[str] = None
    likes: Optional[List[str]] = None
    dislikes: Optional[List[str]] = None
    comm_prefs: Optional[Dict[str, Any]] = None


class ReflectionAdd(BaseModel):
    text: str
    kind: str = "note"


@router.get("/identity")
def get_identity() -> Dict[str, Any]:
    return _identity.stats()


@router.post("/identity")
def update_identity(u: IdentityUpdate) -> Dict[str, Any]:
    data = u.model_dump(exclude_none=True)
    if "name" in data:
        _identity.set_name(data["name"])
    if "persona" in data:
        _identity.set_persona(data["persona"])
    if "values" in data:
        _identity.set_values(data["values"])
    if "mood" in data:
        _identity.set_mood(data["mood"])
    if "goals_today" in data:
        _identity.set_goals_today(data["goals_today"])
    return _identity.stats()


@router.post("/identity/mood")
def set_mood(mood: str) -> Dict[str, Any]:
    _identity.set_mood(mood)
    return {"mood": _identity.mood}


@router.get("/identity/user")
def get_user() -> Dict[str, Any]:
    return _identity.user.to_dict()


@router.post("/identity/user")
def update_user(u: UserUpdate) -> Dict[str, Any]:
    data = u.model_dump(exclude_none=True)
    return _identity.update_user(**data)


@router.post("/identity/reflections")
def add_reflection(r: ReflectionAdd) -> Dict[str, Any]:
    item = _identity.add_reflection(r.text, kind=r.kind)
    return {"reflection": item, "count": len(_identity.reflections)}


@router.get("/identity/prompt-block")
def prompt_block() -> Dict[str, Any]:
    return {"block": _identity.to_prompt_block()}


@router.get("/compaction")
def compaction() -> Dict[str, Any]:
    """Context auto-compaction status (Phase 13 #3)."""
    from omni_v2.llm.compaction import Compactor
    return {"ok": True, "status": Compactor().stats()}


@router.get("/router")
def router() -> Dict[str, Any]:
    """LLM router v2 status (Phase 13 #6)."""
    from omni_v2.llm.router_v2 import LLMRouterV2
    return {"ok": True, "status": LLMRouterV2().stats()}


@router.get("/benchmark")
def benchmark() -> Dict[str, Any]:
    """Self-improvement benchmark (Phase 14 #2)."""
    from omni_v2.away.desktop import DesktopController
    return {"ok": True, "report": DesktopController().benchmark_report().get("report", {})}


@router.get("/sandbox")
def sandbox() -> Dict[str, Any]:
    """Skill sandbox status (Phase 14 #3)."""
    from omni_v2.skills.sandbox import SkillSandbox
    return {"ok": True, "status": SkillSandbox().stats()}


@router.get("/vault")
def vault() -> Dict[str, Any]:
    """Credential vault status (Phase 14 #4) - lists names, never values."""
    from omni_v2.away.desktop import DesktopController
    return {"ok": True, **DesktopController().vault_list()}


@router.get("/personal")
def personal() -> Dict[str, Any]:
    """Personal context (Phase 14 #5): calendar + contacts status."""
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    return {
        "ok": True,
        "calendar": c.calendar.stats() if c.calendar else {"events_total": 0},
        "contacts": c.contacts.stats() if c.contacts else {"contacts": 0},
        "citations": True,
    }


@router.get("/wake")
def wake() -> Dict[str, Any]:
    """Wake routine status (Phase 14 #7)."""
    from omni_v2.away.desktop import DesktopController
    return {"ok": True, **DesktopController().wake_status()}


@router.get("/leaderboard")
def leaderboard() -> Dict[str, Any]:
    """Harness leaderboard (Phase 14 #8b)."""
    from omni_v2.away.desktop import DesktopController
    return DesktopController().leaderboard_report()


@router.get("/schedule")
def schedule() -> Dict[str, Any]:
    """Recurring scheduler status (Phase 15 #1)."""
    from omni_v2.away.desktop import DesktopController
    return DesktopController().schedule_list()


@router.get("/history")
def history(n: int = 50) -> Dict[str, Any]:
    """Action journal (Phase 15 #2)."""
    from omni_v2.away.desktop import DesktopController
    return DesktopController().history_list(n)


@router.get("/photos")
def photos() -> Dict[str, Any]:
    """Photo memory status (Phase 15 #3)."""
    from omni_v2.away.desktop import DesktopController
    pm = DesktopController()._get_photo_memory()
    return {"ok": True, "status": pm.stats() if pm else {"images_indexed": 0}}


@router.get("/backups")
def backups() -> Dict[str, Any]:
    """Backup & restore status (Phase 15 #4)."""
    from omni_v2.away.desktop import DesktopController
    return DesktopController().backup_list()
