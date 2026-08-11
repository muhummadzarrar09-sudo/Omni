"""
OMNI RECURRING SCHEDULER (Phase 15, #1) — OMNI acts on a schedule.

Ties OMNI's actions (morning briefing, guardian, digests, notify, research, away
tasks) to real cron/interval schedules so it works automatically on a schedule —
not just on demand. Wraps the existing OmniScheduler with a richer job model.

Design (headless-testable):
  - RecurringJob: {name, schedule(cron or interval), action, action_args, enabled}.
  - RecurringScheduler:
      * add_cron / add_interval -> registers into the underlying OmniScheduler.
      * on_fire(action, args) -> runs the action via a pluggable runner
        (reuse make_runner + a briefing/guardian runner).
      * list / remove / status.
  - Fully local; the underlying scheduler persists jobs across restarts.

Usage:
    omni schedule add briefing --cron "0 8 * * *"   # 8am daily briefing
    omni schedule add guardian  --interval 3600      # hourly guardian scan
    omni schedule list / remove <name>
"""
from __future__ import annotations
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("RecurringScheduler")

from omni_v2.core.paths import DATA_DIR

SCHEDULES_PATH = DATA_DIR / "brain" / "recurring.json"


class RecurringJob:
    """A scheduled recurring OMNI action."""

    def __init__(self, name: str, schedule_type: str, schedule_value: str,
                 action: str, action_args: Dict[str, Any] = None,
                 enabled: bool = True):
        self.name = name
        self.schedule_type = schedule_type    # cron | interval
        self.schedule_value = schedule_value  # cron expr or interval seconds
        self.action = action                  # briefing | guardian | digest | notify | research | away
        self.action_args = action_args or {}
        self.enabled = enabled
        self.last_run: Optional[float] = None
        self.run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "schedule_type": self.schedule_type,
                "schedule_value": self.schedule_value, "action": self.action,
                "action_args": self.action_args, "enabled": self.enabled,
                "last_run": self.last_run, "run_count": self.run_count}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RecurringJob":
        j = RecurringJob(d["name"], d["schedule_type"], d["schedule_value"],
                         d["action"], d.get("action_args", {}), d.get("enabled", True))
        j.last_run = d.get("last_run")
        j.run_count = d.get("run_count", 0)
        return j


class RecurringScheduler:
    """Manages recurring jobs and wires them to the underlying OmniScheduler."""

    def __init__(self, scheduler=None, runner: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
                 jobs_path: Optional[Path] = None):
        self.scheduler = scheduler            # underlying OmniScheduler
        self.runner = runner                  # runner(action, args) -> result
        self.jobs_path = Path(jobs_path) if jobs_path else SCHEDULES_PATH
        self.jobs_path.parent.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, RecurringJob] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.jobs_path.exists():
                data = json.loads(self.jobs_path.read_text(encoding="utf-8"))
                self._jobs = {k: RecurringJob.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"recurring load failed: {e}")

    def _save(self) -> None:
        try:
            self.jobs_path.write_text(
                json.dumps({k: v.to_dict() for k, v in self._jobs.items()}, indent=2),
                encoding="utf-8")
        except Exception as e:
            logger.warning(f"recurring save failed: {e}")

    # -- CRUD ----------------------------------------------------------------
    def add_cron(self, name: str, cron_expr: str, action: str,
                 action_args: Dict[str, Any] = None) -> RecurringJob:
        job = RecurringJob(name, "cron", cron_expr, action, action_args)
        self._jobs[name] = job
        self._register_in_scheduler(job)
        self._save()
        logger.info(f"⏰ scheduled '{name}' cron '{cron_expr}' -> {action}")
        return job

    def add_interval(self, name: str, seconds: int, action: str,
                     action_args: Dict[str, Any] = None) -> RecurringJob:
        job = RecurringJob(name, "interval", str(seconds), action, action_args)
        self._jobs[name] = job
        self._register_in_scheduler(job)
        self._save()
        logger.info(f"⏰ scheduled '{name}' every {seconds}s -> {action}")
        return job

    def _register_in_scheduler(self, job: RecurringJob) -> None:
        if self.scheduler is None:
            return
        try:
            if job.schedule_type == "cron":
                self.scheduler.add_cron(job.name, f"__recurring__{job.name}", job.schedule_value,
                                        task_id=job.name)
            else:
                self.scheduler.add_interval(job.name, f"__recurring__{job.name}",
                                            seconds=int(job.schedule_value),
                                            task_id=job.name)
        except Exception as e:
            logger.warning(f"register schedule '{job.name}' failed: {e}")

    def remove(self, name: str) -> bool:
        if name in self._jobs:
            del self._jobs[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[RecurringJob]:
        return self._jobs.get(name)

    def list(self) -> List[RecurringJob]:
        return list(self._jobs.values())

    # -- execution ------------------------------------------------------------
    def fire(self, name: str) -> Dict[str, Any]:
        """Fire a job now (manually or by the underlying scheduler)."""
        job = self._jobs.get(name)
        if job is None or not job.enabled:
            return {"ok": False, "detail": f"no enabled job '{name}'"}
        result = None
        if self.runner is not None:
            try:
                result = self.runner(job.action, job.action_args)
            except Exception as e:
                logger.warning(f"recurring runner failed: {e}")
                result = {"ok": False, "error": str(e)}
        job.last_run = time.time()
        job.run_count += 1
        self._save()
        logger.info(f"⏰ fired recurring job '{name}' ({job.action})")
        return {"ok": True, "name": name, "action": job.action, "result": result}

    def stats(self) -> Dict[str, Any]:
        by = {}
        for j in self._jobs.values():
            by[j.action] = by.get(j.action, 0) + 1
        return {"jobs": len(self._jobs), "by_action": by,
                "path": str(self.jobs_path)}


def make_scheduler_runner(controller=None) -> Callable[[str, Dict[str, Any]], Any]:
    """Build a runner that maps recurring actions to DesktopController ops."""
    if controller is None:
        from omni_v2.away.desktop import DesktopController
        controller = DesktopController()

    def _run(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if action == "briefing":
            res = controller.wake_run(speak=False, push=True)
            return {"ok": res.get("ok", False), "greeting": res.get("greeting", "")}
        if action == "guardian":
            return controller.guardian_run_once()
        if action == "digest":
            if controller.away:
                t = controller.away.submit("digest", "scheduled")
                return {"ok": True, "task_id": t.id}
            return {"ok": False}
        if action == "notify":
            return controller.send_message(args.get("text", args.get("message", "OMNI scheduled")))
        if action == "research":
            return controller.away_submit("research", args.get("topic", args.get("brief", "")))
        if action == "away":
            return controller.away_submit(args.get("kind", "notify"),
                                          args.get("brief", args.get("text", "")))
        return {"ok": False, "error": f"unknown action {action}"}
    return _run


def get_recurring_scheduler(**kwargs) -> RecurringScheduler:
    return RecurringScheduler(**kwargs)
