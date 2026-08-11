"""
OMNI AWAY AGENT - runs unattended while you are away, then reports back.

What it does:
  * Maintains a persistent task queue (data/away/tasks.json). Tasks survive
    restarts, so "do this while I'm out" keeps working.
  * Task kinds:
      research : autonomous research on a topic -> saved to KB -> report
      digest   : summarize recent activity (from session memory) -> report
      notify   : send a one-off message/reminder via the messenger
  * On completion, builds a report (Reporter) and pushes a summary to the
    configured messenger (WhatsApp/Telegram/file).
  * Findings from research are stored in the hybrid RAG+CAG knowledge base.

Fully local / offline-safe: if no LLM or search provider is available it still
produces digests and enqueues/reports gracefully. It never requires the cloud.
"""
from __future__ import annotations
import json
import time
import uuid
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("AwayAgent")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

try:
    from omni_v2.away.messenger import MessengerRouter, load_away_config
except Exception:  # pragma: no cover
    MessengerRouter = None
    load_away_config = lambda: {}

try:
    from omni_v2.away.reporter import Reporter
except Exception:  # pragma: no cover
    Reporter = None

try:
    from omni_v2.away.research import ResearchAgent, ResearchReport
except Exception:  # pragma: no cover
    ResearchAgent = None
    ResearchReport = None

try:
    from omni_v2.away.knowledge_base import KnowledgeBase
except Exception:  # pragma: no cover
    KnowledgeBase = None


@dataclass
class AwayTask:
    id: str
    kind: str                 # research | digest | notify
    brief: str                # the prompt / topic / message
    status: str = "pending"   # pending | running | done | error
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AwayTask":
        return AwayTask(**d)


class AwayAgent:
    """Owns the away-mode task queue and runner."""

    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        reporter: Optional[Reporter] = None,
        research_agent: Optional[ResearchAgent] = None,
        messenger: Optional[Any] = None,
        tasks_path: Optional[Path] = None,
        digest_fn: Optional[Any] = None,
    ):
        self.kb = knowledge_base or (KnowledgeBase() if KnowledgeBase else None)
        self.reporter = reporter or (Reporter() if Reporter else None)
        self.research_agent = research_agent or (ResearchAgent(knowledge_base=self.kb) if ResearchAgent else None)
        self.messenger = messenger
        self.tasks_path = Path(tasks_path) if tasks_path else (DATA_DIR / "away" / "tasks.json")
        self.tasks_path.parent.mkdir(parents=True, exist_ok=True)
        # digest_fn: callable() -> str summarizing recent activity
        self.digest_fn = digest_fn
        self._lock = threading.RLock()
        self._tasks: Dict[str, AwayTask] = {}
        self._active = False
        self._load()

    # -- persistence ---------------------------------------------------------
    def _save(self) -> None:
        with self._lock:
            try:
                self.tasks_path.write_text(
                    json.dumps({k: v.to_dict() for k, v in self._tasks.items()}, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                logger.warning(f"Away tasks save failed: {e}")

    def _load(self) -> None:
        try:
            if self.tasks_path.exists():
                data = json.loads(self.tasks_path.read_text(encoding="utf-8"))
                self._tasks = {k: AwayTask.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Away tasks load failed: {e}")

    # -- task API ---------------------------------------------------------
    def submit(self, kind: str, brief: str) -> AwayTask:
        if kind not in ("research", "digest", "notify"):
            raise ValueError(f"unknown task kind: {kind}")
        with self._lock:
            task = AwayTask(
                id=uuid.uuid4().hex[:12],
                kind=kind,
                brief=brief.strip(),
            )
            self._tasks[task.id] = task
            self._save()
        logger.info(f"Away task queued [{task.kind}]: {task.brief}")
        return task

    def list_tasks(self, limit: int = 50) -> List[AwayTask]:
        return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)[:limit]

    def get_task(self, task_id: str) -> Optional[AwayTask]:
        return self._tasks.get(task_id)

    # -- runner -------------------------------------------------------------
    def run_pending(self) -> List[AwayTask]:
        """Run every pending task now (synchronous). Returns completed tasks."""
        done: List[AwayTask] = []
        pending = [t for t in self._tasks.values() if t.status == "pending"]
        for task in pending:
            self.run_task(task.id)
            done.append(task)
        return done

    def run_task(self, task_id: str) -> AwayTask:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(task_id)
        task.status = "running"
        task.started_at = time.time()
        self._save()
        try:
            if task.kind == "research":
                self._run_research(task)
            elif task.kind == "digest":
                self._run_digest(task)
            elif task.kind == "notify":
                self._run_notify(task)
            task.status = "done"
            task.finished_at = time.time()
        except Exception as e:
            logger.exception(f"Away task {task.id} failed")
            task.status = "error"
            task.error = str(e)
            task.finished_at = time.time()
        self._save()
        return task

    def _run_research(self, task: AwayTask) -> None:
        if self.research_agent is None:
            raise RuntimeError("research agent not available")
        report = self.research_agent.research(task.brief)
        task.result = report.to_dict()
        # build + save + push report
        if self.reporter is not None:
            rep = self.reporter.build_research_report(report)
            task.result["report_path"] = str(rep.path)
            self._push_report(rep.summary, str(rep.path))

    def _run_digest(self, task: AwayTask) -> None:
        if self.digest_fn is None:
            memory_summary = self._default_digest()
        else:
            memory_summary = self.digest_fn(task.brief)
        if self.reporter is not None:
            rep = self.reporter.build_digest(memory_summary, label=task.brief or "periodic")
            task.result = {"summary": rep.summary, "report_path": str(rep.path)}
            self._push_report(rep.summary, str(rep.path))

    def _run_notify(self, task: AwayTask) -> None:
        res = self._send(f"⏰ Reminder: {task.brief}")
        task.result = {"sent": res.ok, "channel": res.channel}

    def _default_digest(self) -> str:
        return (
            "OMNI was monitoring while you were away. "
            "Enable session-memory digests for a fuller recap."
        )

    # -- messaging -----------------------------------------------------------
    def _send(self, text: str):
        if self.messenger is None:
            from omni_v2.away.messenger import MessengerRouter
            self.messenger = MessengerRouter()
        return self.messenger.send_text(text)

    def _push_report(self, summary: str, path: str = "") -> None:
        if self.messenger is None:
            from omni_v2.away.messenger import MessengerRouter
            self.messenger = MessengerRouter()
        try:
            out = self.messenger.send_report(summary, path=path)
            logger.info(f"Away report pushed via {self.messenger.channel}: ok={out.ok}")
        except Exception as e:
            logger.warning(f"Away report push failed: {e}")

    # -- lifecycle ---------------------------------------------------------
    def away_start(self) -> Dict[str, Any]:
        self._active = True
        return {"active": True, "queued_tasks": len([t for t in self._tasks.values() if t.status == "pending"])}

    def away_stop(self) -> Dict[str, Any]:
        self._active = False
        return {"active": False}

    @property
    def active(self) -> bool:
        return self._active

    def stats(self) -> Dict[str, Any]:
        counts = {}
        for t in self._tasks.values():
            counts[t.status] = counts.get(t.status, 0) + 1
        return {
            "active": self._active,
            "tasks_total": len(self._tasks),
            "tasks_by_status": counts,
            "tasks_path": str(self.tasks_path),
        }


_instance = None
_lock = threading.Lock()


def get_away_agent(**kwargs) -> AwayAgent:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = AwayAgent(**kwargs)
    return _instance
