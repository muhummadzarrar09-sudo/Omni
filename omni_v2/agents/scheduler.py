"""
OMNI V3 - Scheduler - Proper cron-style task scheduling with APScheduler

Features:
  - Cron expressions ("0 9 * * 1-5" = 9am weekdays)
  - Interval ("every 30 min")
  - One-shot ("in 5 min")
  - Persistent (survives restarts)
  - Misfire handling
  - Timezone-aware
"""
from __future__ import annotations
import json
import time
import uuid
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Scheduler")

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.debug("apscheduler not installed - using simple scheduler")


@dataclass
class ScheduledTask:
    id: str
    name: str
    command: str  # the text command to execute via brain
    trigger_type: str  # "cron" | "interval" | "date"
    trigger_args: Dict[str, Any]  # e.g. {"hour": 9, "minute": 0} for cron
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int = 0


class OmniScheduler:
    """
    The butler who remembers. Cron-style task scheduling.
    Persists to data/scheduler/tasks.json so tasks survive restarts.
    """
    def __init__(self, on_task_due: Optional[Callable[[ScheduledTask], None]] = None):
        self.on_task_due = on_task_due
        self.tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.RLock()
        try:
            from omni_v2.core.paths import DATA_DIR
            self.data_dir = DATA_DIR / "scheduler"
        except Exception:
            self.data_dir = Path.home() / ".omni_v2" / "scheduler"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.data_dir / "tasks.json"
        self._scheduler = None
        self._use_real = APSCHEDULER_AVAILABLE
        if self._use_real:
            try:
                self._scheduler = BackgroundScheduler(daemon=True)
                self._scheduler.start()
                logger.info("✅ OmniScheduler: APScheduler running")
            except Exception as e:
                logger.warning(f"APScheduler failed: {e}, using simple scheduler")
                self._use_real = False
        self._load_tasks()
        if not self._use_real:
            self._start_simple_loop()

    def _load_tasks(self):
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, tdata in data.get("tasks", {}).items():
                        task = ScheduledTask(**tdata)
                        self.tasks[tid] = task
                        if task.enabled:
                            self._schedule_task(task)
        except Exception as e:
            logger.debug(f"Load tasks: {e}")

    def _save_tasks(self):
        try:
            data = {"tasks": {tid: asdict(t) for tid, t in self.tasks.items()}}
            tmp = self.tasks_file.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.tasks_file)
        except Exception as e:
            logger.debug(f"Save tasks: {e}")

    def _validate_task_input(self, name: str, command: str) -> None:
        name = str(name or "").strip()
        command = str(command or "").strip()
        if not name or not command:
            raise ValueError("Task name and command are required")
        if len(name) > 200 or len(command) > 2000:
            raise ValueError("Task name or command is too long")
        if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in command):
            raise ValueError("Task command contains control characters")

    def add_cron(self, name: str, command: str, cron_expr: str, task_id: Optional[str] = None) -> ScheduledTask:
        """Add a cron job. cron_expr is a 5-field cron string (e.g. '0 9 * * 1-5')."""
        self._validate_task_input(name, command)
        if not self._use_real:
            return self._add_simple(name, command, "cron", cron_expr=cron_expr)
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError(f"Cron must have 5 fields, got {len(parts)}")
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1], day=parts[2],
                month=parts[3], day_of_week=parts[4]
            )
            tid = task_id or f"cron_{uuid.uuid4().hex}"
            task = ScheduledTask(
                id=tid, name=name, command=command,
                trigger_type="cron", trigger_args={"cron": cron_expr}
            )
            with self._lock:
                self.tasks[tid] = task
                self._scheduler.add_job(
                    self._fire_task, trigger, id=tid,
                    args=[task], replace_existing=True
                )
                self._save_tasks()
            logger.info(f"📅 Scheduled cron task: {name} ({cron_expr})")
            return task
        except Exception as e:
            logger.error(f"add_cron failed: {e}")
            raise

    def add_interval(self, name: str, command: str, **kwargs) -> ScheduledTask:
        """Add an interval job. kwargs: seconds=60, minutes=30, hours=1, etc."""
        self._validate_task_input(name, command)
        if not kwargs or any(float(v) <= 0 for v in kwargs.values()):
            raise ValueError("Interval must contain positive values")
        if not self._use_real:
            return self._add_simple(name, command, "interval", **kwargs)
        try:
            tid = f"interval_{uuid.uuid4().hex}"
            task = ScheduledTask(
                id=tid, name=name, command=command,
                trigger_type="interval", trigger_args=kwargs
            )
            with self._lock:
                self.tasks[tid] = task
                self._scheduler.add_job(
                    self._fire_task, IntervalTrigger(**kwargs),
                    id=tid, args=[task], replace_existing=True
                )
                self._save_tasks()
            logger.info(f"⏰ Scheduled interval task: {name} ({kwargs})")
            return task
        except Exception as e:
            logger.error(f"add_interval failed: {e}")
            raise

    def add_once(self, name: str, command: str, run_at: datetime) -> ScheduledTask:
        """Add a one-shot job at a specific time."""
        self._validate_task_input(name, command)
        if run_at.tzinfo is None:
            logger.warning("Naive datetime supplied; interpreting in scheduler local timezone")
        if not self._use_real:
            return self._add_simple(name, command, "date", run_at=run_at.isoformat())
        try:
            tid = f"once_{uuid.uuid4().hex}"
            task = ScheduledTask(
                id=tid, name=name, command=command,
                trigger_type="date", trigger_args={"run_at": run_at.isoformat()}
            )
            with self._lock:
                self.tasks[tid] = task
                self._scheduler.add_job(
                    self._fire_task, DateTrigger(run_date=run_at),
                    id=tid, args=[task], replace_existing=True
                )
                self._save_tasks()
            logger.info(f"⏰ Scheduled one-shot: {name} at {run_at}")
            return task
        except Exception as e:
            logger.error(f"add_once failed: {e}")
            raise

    def _fire_task(self, task: ScheduledTask):
        """Called when a task is due."""
        task.last_run = time.time()
        task.run_count += 1
        logger.info(f"🔥 Task firing: {task.name} -> '{task.command}'")
        if self.on_task_due:
            try:
                self.on_task_due(task)
            except Exception as e:
                logger.error(f"on_task_due: {e}")
        if task.trigger_type == "date":
            with self._lock:
                task.enabled = False
                self.tasks.pop(task.id, None)
                if self._use_real and self._scheduler:
                    try:
                        self._scheduler.remove_job(task.id)
                    except Exception:
                        pass
        self._save_tasks()

    def shutdown(self) -> None:
        """Stop scheduler threads and persist current state."""
        with self._lock:
            if self._scheduler:
                try:
                    self._scheduler.shutdown(wait=False)
                except Exception as exc:
                    logger.debug(f"Scheduler shutdown: {exc}")
                self._scheduler = None

    def remove(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self.tasks:
                if self._use_real and self._scheduler:
                    try:
                        self._scheduler.remove_job(task_id)
                    except Exception:
                        pass
                del self.tasks[task_id]
                self._save_tasks()
                return True
        return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {**asdict(t), "id": tid}
                for tid, t in self.tasks.items()
            ]

    def _schedule_task(self, task: ScheduledTask):
        """Re-schedule a loaded task after restart."""
        if not self._use_real:
            return
        try:
            if task.trigger_type == "cron":
                self._scheduler.add_job(
                    self._fire_task, CronTrigger.from_crontab(task.trigger_args["cron"]),
                    id=task.id, args=[task], replace_existing=True
                )
            elif task.trigger_type == "interval":
                self._scheduler.add_job(
                    self._fire_task, IntervalTrigger(**task.trigger_args),
                    id=task.id, args=[task], replace_existing=True
                )
            elif task.trigger_type == "date":
                run_at = datetime.fromisoformat(task.trigger_args["run_at"])
                self._scheduler.add_job(
                    self._fire_task, DateTrigger(run_date=run_at),
                    id=task.id, args=[task], replace_existing=True
                )
        except Exception as e:
            logger.debug(f"Re-schedule {task.id}: {e}")

    def _add_simple(self, name, command, ttype, **kwargs) -> ScheduledTask:
        """Fallback when APScheduler is not available."""
        tid = f"{ttype}_{int(time.time()*1000)}"
        task = ScheduledTask(
            id=tid, name=name, command=command,
            trigger_type=ttype, trigger_args=kwargs
        )
        with self._lock:
            self.tasks[tid] = task
            self._save_tasks()
        return task

    def _start_simple_loop(self):
        """Fallback simple polling loop if APScheduler is missing."""
        def _loop():
            while True:
                time.sleep(30)
                now = time.time()
                with self._lock:
                    for tid, task in list(self.tasks.items()):
                        if not task.enabled:
                            continue
                        # Check if due
                        if task.trigger_type == "interval":
                            seconds = task.trigger_args.get("seconds", 60)
                            if task.last_run is None or (now - task.last_run) >= seconds:
                                self._fire_task(task)
        t = threading.Thread(target=_loop, daemon=True, name="SimpleScheduler")
        t.start()
        logger.info("⏰ OmniScheduler: simple polling loop started (30s tick)")

    def shutdown(self):
        if self._use_real and self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass


_scheduler_instance: Optional[OmniScheduler] = None
_scheduler_lock = threading.Lock()


def get_scheduler(on_task_due: Optional[Callable] = None) -> OmniScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        with _scheduler_lock:
            if _scheduler_instance is None:
                _scheduler_instance = OmniScheduler(on_task_due=on_task_due)
    return _scheduler_instance
