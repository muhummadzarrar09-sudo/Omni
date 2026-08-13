"""
OMNI REFLECTION - FastAPI router (Jarvis Brain Phase 9 Step 5).

Episodic recaps + pattern awareness over HTTP. Fully local.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List

from omni_v2.brain.reflect import Reflector
from omni_v2.memory.session_memory import SessionMemoryStore
from omni_v2.memory.hybrid_memory import get_hybrid_memory
from omni_v2.brain.identity import IdentityCore

_reflector = Reflector(session_memory=SessionMemoryStore(),
                       hybrid_memory=get_hybrid_memory(), identity=IdentityCore())
router = APIRouter(prefix="/api/reflect", tags=["reflect"])


class DaysQuery(BaseModel):
    days: int = 7


@router.post("/today")
def reflect_today() -> Dict[str, Any]:
    ep = _reflector.reflect_today()
    return {"episode": ep.to_dict()}


@router.post("/patterns")
def patterns(q: DaysQuery) -> Dict[str, Any]:
    return {"patterns": _reflector.detect_patterns(q.days)}


@router.get("/episodes")
def episodes(limit: int = 20) -> Dict[str, Any]:
    return {"episodes": [e.to_dict() for e in _reflector.episodes(limit)]}


@router.get("/stats")
def stats() -> Dict[str, Any]:
    return _reflector.stats()
