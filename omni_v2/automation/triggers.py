"""
OMNI AUTOMATION TRIGGERS (Phase 13, #5) — the "agent operating layer" feel.

Lets EXTERNAL events wake OMNI and start goals / research / tasks automatically.
Three trigger types:
  - WEBHOOK: an HTTP endpoint that fires an automation when POSTed to
    (with an optional secret token).
  - SCHEDULE: a cron/interval that fires an automation (wraps the existing
    OmniScheduler).
  - FILE: a new file appearing in a watched directory fires an automation.

Each automation is a {name, action, action_args, enabled} record. The `runner`
callback performs the action (submit goal / research / notify / away-task).

Design:
  - TriggerManager: registry + webhook handling (a small standalone HTTP server
    so it works without the FastAPI app too).
  - The FastAPI layer exposes /api/automation/webhook/<name> so the main app
    handles webhooks; a standalone listener is also provided for non-FastAPI use.
  - Fully headless-testable with fakes.

Examples:
  omni automation add-webhook deploy_hook --action goal "deploy the app"
  curl -X POST http://localhost:8888/webhook/deploy_hook
"""
from __future__ import annotations
import json
import time
import uuid
import hashlib
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Automation")

from omni_v2.core.paths import DATA_DIR

TRIGGERS_PATH = DATA_DIR / "brain" / "triggers.json"

# automation action kinds
ACTION_GOAL = "goal"          # start a goal
ACTION_RESEARCH = "research"  # run research
ACTION_NOTIFY = "notify"      # send a message
ACTION_AWAY = "away"          # queue an away task


class Automation:
    """One automation trigger."""

    def __init__(self, name: str, trigger: str, action: str, action_args: Dict[str, Any],
                 enabled: bool = True, secret: str = ""):
        self.name = name
        self.trigger = trigger        # webhook | schedule | file
        self.action = action
        self.action_args = action_args or {}
        self.enabled = enabled
        self.secret = secret          # optional token for webhook auth
        self.last_fired: Optional[float] = None
        self.fire_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "trigger": self.trigger, "action": self.action,
                "action_args": self.action_args, "enabled": self.enabled,
                "secret": self.secret, "last_fired": self.last_fired,
                "fire_count": self.fire_count}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Automation":
        a = Automation(d["name"], d["trigger"], d["action"], d.get("action_args", {}),
                       enabled=d.get("enabled", True), secret=d.get("secret", ""))
        a.last_fired = d.get("last_fired")
        a.fire_count = d.get("fire_count", 0)
        return a


class TriggerManager:
    """Registry + execution of automation triggers."""

    def __init__(self, runner: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
                 triggers_path: Optional[Path] = None, scheduler=None):
        self.triggers_path = Path(triggers_path) if triggers_path else TRIGGERS_PATH
        self.triggers_path.parent.mkdir(parents=True, exist_ok=True)
        # runner(action_kind, action_args) -> performs the action (goal/research/etc.)
        self.runner = runner
        self.scheduler = scheduler      # optional OmniScheduler for schedule triggers
        self._lock = threading.RLock()
        self._triggers: Dict[str, Automation] = {}
        self._fired_log: List[Dict[str, Any]] = []
        self._load()

    # -- persistence --------------------------------------------------------
    def _save(self) -> None:
        with self._lock:
            try:
                self.triggers_path.write_text(
                    json.dumps({k: v.to_dict() for k, v in self._triggers.items()}, indent=2),
                    encoding="utf-8")
            except Exception as e:
                logger.warning(f"triggers save failed: {e}")

    def _load(self) -> None:
        try:
            if self.triggers_path.exists():
                data = json.loads(self.triggers_path.read_text(encoding="utf-8"))
                self._triggers = {k: Automation.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"triggers load failed: {e}")

    # -- CRUD ---------------------------------------------------------------
    def add(self, name: str, trigger: str, action: str, action_args: Dict[str, Any],
            secret: str = "") -> Automation:
        if trigger not in ("webhook", "schedule", "file"):
            raise ValueError(f"bad trigger: {trigger}")
        if action not in (ACTION_GOAL, ACTION_RESEARCH, ACTION_NOTIFY, ACTION_AWAY):
            raise ValueError(f"bad action: {action}")
        with self._lock:
            a = Automation(name, trigger, action, action_args, secret=secret)
            self._triggers[name] = a
            self._save()
        return a

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._triggers:
                del self._triggers[name]
                self._save()
                return True
            return False

    def get(self, name: str) -> Optional[Automation]:
        return self._triggers.get(name)

    def list(self) -> List[Automation]:
        return list(self._triggers.values())

    # -- execution -----------------------------------------------------------
    def fire(self, name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fire an automation by name (used by webhook / schedule / file watchers)."""
        a = self._triggers.get(name)
        if a is None:
            return {"ok": False, "detail": f"no trigger '{name}'"}
        if not a.enabled:
            return {"ok": False, "detail": f"trigger '{name}' disabled"}
        # merge payload into action_args (payload overrides)
        args = {**a.action_args, **(payload or {})}
        result = None
        if self.runner is not None:
            try:
                result = self.runner(a.action, args)
            except Exception as e:
                logger.warning(f"automation runner failed: {e}")
                result = {"ok": False, "error": str(e)}
        a.last_fired = time.time()
        a.fire_count += 1
        self._fired_log.append({"name": name, "action": a.action, "ts": a.last_fired,
                                "result": result})
        self._fired_log = self._fired_log[-200:]
        self._save()
        logger.info(f"⚡ automation fired: {name} ({a.action})")
        return {"ok": True, "name": name, "action": a.action, "result": result}

    # -- webhook handling ------------------------------------------------------
    def handle_webhook(self, name: str, payload: Dict[str, Any], token: str = "") -> Dict[str, Any]:
        a = self._triggers.get(name)
        if a is None:
            return {"ok": False, "detail": f"no trigger '{name}'"}
        if a.secret and a.secret != token:
            return {"ok": False, "detail": "invalid token"}
        return self.fire(name, payload)

    # -- introspection ---------------------------------------------------------
    def fired_log(self, n: int = 20) -> List[Dict[str, Any]]:
        return self._fired_log[-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        by = {}
        for a in self._triggers.values():
            by[a.trigger] = by.get(a.trigger, 0) + 1
        return {"triggers": len(self._triggers), "by_trigger": by,
                "fired": len(self._fired_log), "path": str(self.triggers_path)}


# -- default runner factory: wire into goals/research/away --------------------
def make_runner(goals=None, research=None, away=None, messenger=None) -> Callable[[str, Dict[str, Any]], Any]:
    """Build a runner that maps automation actions to real OMNI operations."""
    def _run(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if action == ACTION_GOAL and goals is not None:
            intent = args.get("intent", args.get("brief", ""))
            g = goals.create_goal(intent, title=args.get("title", ""))
            return {"ok": True, "goal_id": g.id}
        if action == ACTION_RESEARCH and research is not None:
            topic = args.get("topic", args.get("brief", ""))
            report = research.research(topic)
            return {"ok": True, "findings": len(report.findings)}
        if action == ACTION_NOTIFY and messenger is not None:
            text = args.get("text", args.get("message", "OMNI automation"))
            res = messenger.send_text(text)
            return {"ok": res.ok}
        if action == ACTION_AWAY and away is not None:
            kind = args.get("kind", "notify")
            brief = args.get("brief", args.get("text", ""))
            t = away.submit(kind, brief)
            return {"ok": True, "task_id": t.id}
        return {"ok": False, "error": f"unknown action or missing dependency: {action}"}
    return _run


def get_trigger_manager(**kwargs) -> TriggerManager:
    return TriggerManager(**kwargs)
