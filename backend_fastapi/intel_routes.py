"""
OMNI INTEL - FastAPI router for Knowledge Graph, Morning Briefing, Skill Installer.
Fully local.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
import sys
from typing import Any, Dict, Optional

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from omni_v2.graph.knowledge_graph import KnowledgeGraphBuilder
from omni_v2.memory.hybrid_memory import get_hybrid_memory
from omni_v2.memory.session_memory import SessionMemoryStore
from omni_v2.briefing.briefing import MorningBriefing
from omni_v2.brain.goals import GoalStack
from omni_v2.brain.identity import IdentityCore
from omni_v2.brain.reflect import Reflector
from omni_v2.skills.installer import SkillInstaller

router = APIRouter(prefix="/api", tags=["intel"])

try:
    _session = SessionMemoryStore()
except Exception:
    _session = None
_kb = KnowledgeGraphBuilder(memory=get_hybrid_memory(), session_memory=_session)


class BriefingRequest(BaseModel):
    research_topic: str = ""
    save_report: bool = True
    push: bool = True


class SkillRequest(BaseModel):
    source: str
    allow_network: bool = False
    force: bool = False


@router.get("/knowledge-graph")
def knowledge_graph() -> Dict[str, Any]:
    return _kb.build()


@router.post("/briefing")
def briefing(req: BriefingRequest) -> Dict[str, Any]:
    from omni_v2.away.messenger import MessengerRouter
    b = MorningBriefing(
        goals=GoalStack(), reflector=Reflector(session_memory=_session),
        reporter=None, messenger=MessengerRouter(), identity=IdentityCore(),
    )
    return b.deliver(research_topic=req.research_topic,
                     save_report=req.save_report, push=req.push)


@router.post("/skills/install")
def install_skill(req: SkillRequest) -> Dict[str, Any]:
    inst = SkillInstaller()
    return inst.install(req.source, allow_network=req.allow_network, force=req.force)


@router.get("/skills/list")
def list_skills() -> Dict[str, Any]:
    return SkillInstaller().list_installed()
