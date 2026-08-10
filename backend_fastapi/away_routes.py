"""
OMNI AWAY MODE - FastAPI router (Phase 7 / Away Mode).

Exposes the local RAG+CAG knowledge base, autonomous research, away task queue
and messenger/reporting through HTTP so the UI (or a local dashboard) can drive
it. Everything stays local; the messenger channel (file/whatsapp/telegram) is
the only external-facing part and is configurable.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import sys
from typing import Any, Dict, Optional

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from omni_v2.away.context import build_away_stack

# Build the shared away stack (KnowledgeBase + AwayAgent + Reporter + Messenger)
_stack = build_away_stack()
_agent = _stack["away_agent"]
_kb = _stack["knowledge_base"]
_reporter = _stack["reporter"]

router = APIRouter(prefix="/api/away", tags=["away-mode"])


class KBAddRequest(BaseModel):
    target: str = Field(..., description="file path, folder, or URL to ingest")


class KBQueryRequest(BaseModel):
    question: str
    k: int = 5


class TaskRequest(BaseModel):
    kind: str = Field(..., description="research | digest | notify")
    brief: str


@router.get("/status")
def status() -> Dict[str, Any]:
    st = _agent.stats()
    st["kb"] = _kb.stats()
    st["messenger"] = _stack["messenger"].channel
    st["reports_recent"] = _reporter.list_recent(n=5)
    return st


@router.get("/tasks")
def list_tasks(limit: int = 20) -> Dict[str, Any]:
    return {"tasks": [t.to_dict() for t in _agent.list_tasks(limit=limit)]}


@router.post("/tasks")
def submit_task(req: TaskRequest) -> Dict[str, Any]:
    if req.kind not in ("research", "digest", "notify"):
        raise HTTPException(400, "kind must be research | digest | notify")
    task = _agent.submit(req.kind, req.brief)
    return {"task": task.to_dict()}


@router.post("/tasks/run")
def run_pending(task_id: Optional[str] = None) -> Dict[str, Any]:
    if task_id:
        t = _agent.run_task(task_id)
        return {"ran": [t.to_dict()]}
    done = _agent.run_pending()
    return {"ran": [t.to_dict() for t in done]}


@router.get("/kb/stats")
def kb_stats() -> Dict[str, Any]:
    return _kb.stats()


@router.post("/kb/add")
def kb_add(req: KBAddRequest) -> Dict[str, Any]:
    try:
        n = _kb.add_file(req.target)
    except FileNotFoundError:
        if "://" in req.target:
            n = _kb.add_url(req.target)
        else:
            raise HTTPException(404, f"not found: {req.target}")
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    return {"ingested_chunks": n, "target": req.target}


@router.post("/kb/query")
def kb_query(req: KBQueryRequest) -> Dict[str, Any]:
    return _kb.query(req.question, k=req.k)


@router.post("/research")
def research(topic: str) -> Dict[str, Any]:
    report = _stack["research_agent"].research(topic)
    rep = _reporter.build_research_report(report)
    return {"report": report.to_dict(), "markdown": report.to_markdown(), "saved_path": str(rep.path)}


@router.post("/reports/digest")
def build_digest(label: str = "api") -> Dict[str, Any]:
    task = _agent.submit("digest", label)
    _agent.run_task(task.id)
    return {"task": task.to_dict()}
