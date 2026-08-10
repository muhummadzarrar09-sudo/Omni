"""
OMNI DESKTOP CONTROLLER - headless logic behind the desktop app.

Wraps the whole away-mode + security feature set into a single object the
customtkinter GUI (`omni_desktop.py`) calls. Being headless makes it fully
unit-testable without a display / camera / GUI toolkit.

Methods are grouped by tab:
  - status / messenger / reports
  - knowledge base
  - research
  - away tasks
  - security (enroll, arm, disarm, snapshot, intruder events, manual lock)

The messenger is wired into the guard's pre-lock alert automatically when it's
not a pure 'file' provider, so a suspected intruder triggers a phone alert.
"""
from __future__ import annotations
import time
import threading
from typing import Any, Dict, List, Optional, Callable

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("DesktopController")

try:
    from omni_v2.away.context import build_away_stack
except Exception:  # pragma: no cover
    build_away_stack = None

try:
    from omni_v2.away.messenger import load_away_config, save_away_config, FileMessenger
except Exception:  # pragma: no cover
    load_away_config = save_away_config = None

try:
    from omni_v2.security.face_auth import FaceAuth
except Exception:  # pragma: no cover
    FaceAuth = None

try:
    from omni_v2.security.lockdown import LockdownController, MachineLocker
except Exception:  # pragma: no cover
    LockdownController = None
    MachineLocker = None

try:
    from omni_v2.security.guard_monitor import GuardMonitor
except Exception:  # pragma: no cover
    GuardMonitor = None


class DesktopController:
    """One object that powers the entire desktop app."""

    def __init__(self, away_stack: Optional[Dict[str, Any]] = None,
                 on_status_change: Optional[Callable[[str], None]] = None):
        if away_stack is None and build_away_stack is not None:
            away_stack = build_away_stack()
        self.stack = away_stack or {}
        self.away = self.stack.get("away_agent")
        self.kb = self.stack.get("knowledge_base")
        self.reporter = self.stack.get("reporter")
        self.research = self.stack.get("research_agent")
        self.messenger = self.stack.get("messenger")
        self.memory = self.stack.get("memory")
        self.identity = self.stack.get("identity")
        if self.identity is None:
            try:
                from omni_v2.brain.identity import IdentityCore
                self.identity = IdentityCore()
            except Exception:
                self.identity = None
        self.goals = self.stack.get("goals")
        if self.goals is None:
            try:
                from omni_v2.brain.goals import GoalStack
                self.goals = GoalStack()
            except Exception:
                self.goals = None
        self.metacog = self.stack.get("metacog")
        if self.metacog is None:
            try:
                from omni_v2.brain.metacog import Metacog
                self.metacog = Metacog()
            except Exception:
                self.metacog = None
        self.reflector = self.stack.get("reflector")
        if self.reflector is None:
            try:
                from omni_v2.brain.reflect import Reflector
                from omni_v2.memory.session_memory import SessionMemoryStore
                from omni_v2.memory.hybrid_memory import get_hybrid_memory
                self.reflector = Reflector(session_memory=SessionMemoryStore(),
                                           hybrid_memory=get_hybrid_memory())
            except Exception:
                self.reflector = None
        self.on_status_change = on_status_change

        # -- security ----------------------------------------------------
        self.face_auth = FaceAuth() if FaceAuth else None
        self.locker = MachineLocker() if MachineLocker else None
        self.lockdown = LockdownController(
            locker=self.locker, notify_fn=self._notify,
        ) if LockdownController else None
        self.guard = GuardMonitor(
            face_auth=self.face_auth,
            lockdown=self.lockdown,
            on_intruder=self._on_intruder,
            cancel_callback=lambda: self._cancel_requested.get("cancel", False),
        ) if (GuardMonitor and self.face_auth and self.lockdown) else None
        self._cancel_requested: Dict[str, bool] = {"cancel": False}
        self._intruder_hook: Optional[Callable[[Dict[str, Any]], None]] = None

    # -- status / config -------------------------------------------------
    def status(self) -> Dict[str, Any]:
        out = {"ts": time.time()}
        if self.away:
            out["away"] = self.away.stats()
        if self.kb:
            out["kb"] = self.kb.stats()
        if self.messenger:
            out["messenger"] = getattr(self.messenger, "channel", "unknown")
        if self.reporter:
            out["reports_recent"] = self.reporter.list_recent(n=5)
        if self.face_auth:
            out["security"] = self.face_auth.stats()
            out["security"]["backend"] = self.face_auth.backend
            out["security"]["backend_label"] = (
                "OpenCV LBPH (trained, local)" if self.face_auth.backend == "lbph" else
                "dlib deep embeddings (if installed)" if self.face_auth.backend == "deep" else
                "gradient descriptor (fallback)")
        if self.guard:
            out["security"]["guard"] = self.guard.stats()
        from omni_v2.brain.identity import IdentityCore
        try:
            out["identity"] = IdentityCore().stats()
        except Exception:
            pass
        if self.goals:
            out["goals"] = self.goals.stats()
        if self.metacog:
            out["metacog"] = self.metacog.stats()
        if self.reflector:
            out["reflector"] = self.reflector.stats()
        return out

    def messenger_config(self) -> Dict[str, Any]:
        return load_away_config() if load_away_config else {}

    def save_config(self, cfg: Dict[str, Any]) -> None:
        if save_away_config:
            save_away_config(cfg)

    def send_message(self, text: str) -> Dict[str, Any]:
        if self.messenger is None:
            return {"ok": False, "detail": "messenger unavailable"}
        res = self.messenger.send_text(text)
        return {"ok": res.ok, "detail": res.detail, "channel": res.channel}

    # -- knowledge base --------------------------------------------------
    def kb_add(self, target: str) -> Dict[str, Any]:
        from pathlib import Path
        if self.kb is None:
            return {"ok": False, "detail": "KB unavailable"}
        try:
            if "://" in target:
                n = self.kb.add_url(target)
            else:
                n = self.kb.add_file(target)
            return {"ok": True, "chunks": n, "detail": f"ingested {n} chunk(s)"}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def kb_query(self, question: str, k: int = 4) -> Dict[str, Any]:
        if self.kb is None:
            return {"ok": False, "detail": "KB unavailable"}
        return self.kb.query(question, k=k)

    # -- research ----------------------------------------------------------
    def run_research(self, topic: str) -> Dict[str, Any]:
        if self.research is None or self.reporter is None:
            return {"ok": False, "detail": "research/reporter unavailable"}
        try:
            report = self.research.research(topic)
            rep = self.reporter.build_research_report(report)
            return {"ok": True, "markdown": report.to_markdown(),
                    "path": str(rep.path), "findings": len(report.findings)}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    # -- away tasks ----------------------------------------------------------
    def away_submit(self, kind: str, brief: str) -> Dict[str, Any]:
        if self.away is None:
            return {"ok": False, "detail": "away agent unavailable"}
        try:
            t = self.away.submit(kind, brief)
            return {"ok": True, "task": t.to_dict()}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def away_list(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.away.list_tasks(20)] if self.away else []

    def away_run_pending(self) -> List[Dict[str, Any]]:
        if self.away is None:
            return []
        done = self.away.run_pending()
        return [t.to_dict() for t in done]

    def away_start_stop(self, start: bool) -> Dict[str, Any]:
        if self.away is None:
            return {"ok": False}
        if start:
            return {"ok": True, **self.away.away_start()}
        return {"ok": True, **self.away.away_stop()}

    # -- goals (Jarvis Brain Step 3) -------------------------------------------
    def goal_create(self, intent: str, title: str = "") -> Dict[str, Any]:
        if self.goals is None:
            return {"ok": False, "detail": "goals unavailable"}
        try:
            g = self.goals.create_goal(intent, title=title)
            return {"ok": True, "goal": g.to_dict()}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def goal_list(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self.goals.list_goals(20)] if self.goals else []

    def goal_begin(self, goal_id: str) -> Dict[str, Any]:
        if self.goals is None:
            return {"ok": False, "detail": "unavailable"}
        s = self.goals.begin_step(goal_id)
        return {"ok": s is not None, "step": s.to_dict() if s else None}

    def goal_complete_step(self, goal_id: str, result: Dict[str, Any] = None) -> Dict[str, Any]:
        if self.goals is None:
            return {"ok": False}
        g = self.goals.complete_step(goal_id, result)
        return {"ok": True, "goal": g.to_dict()}

    def goal_fail(self, goal_id: str, error: str = "", fix: str = "") -> Dict[str, Any]:
        if self.goals is None:
            return {"ok": False}
        g = self.goals.fail_step(goal_id, error=error, suggested_fix=fix)
        return {"ok": True, "goal": g.to_dict()}

    def goal_abandon(self, goal_id: str) -> Dict[str, Any]:
        if self.goals is None:
            return {"ok": False}
        g = self.goals.abandon(goal_id)
        return {"ok": True, "goal": g.to_dict()}

    # -- metacognition (Jarvis Brain Step 4) -----------------------------------
    def metacog_decide(self, succeeded: bool, message: str = "",
                       error: str = "") -> Dict[str, Any]:
        if self.metacog is None:
            return {"ok": False, "detail": "metacog unavailable"}
        v = self.metacog.decide(succeeded, message=message, error=error)
        return {"ok": True, "verdict": v.to_dict()}

    def metacog_apply_to_goal(self, goal_id: str, verdict: Dict[str, Any]) -> Dict[str, Any]:
        from omni_v2.brain.metacog import Verdict
        if self.metacog is None or self.goals is None:
            return {"ok": False, "detail": "metacog/goals unavailable"}
        v = Verdict.from_dict(verdict)
        g = self.metacog.apply_to_goal(self.goals, goal_id, v)
        return {"ok": True, "goal": g.to_dict() if g else None}

    def metacog_history(self) -> list:
        return self.metacog.history(20) if self.metacog else []

    # -- episodic reflection & patterns (Jarvis Brain Step 5) -------------------
    def reflect_today(self) -> Dict[str, Any]:
        if self.reflector is None:
            return {"ok": False, "detail": "reflector unavailable"}
        try:
            ep = self.reflector.reflect_today()
            return {"ok": True, "episode": ep.to_dict()}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def detect_patterns(self, days: int = 7) -> Dict[str, Any]:
        if self.reflector is None:
            return {"ok": False, "patterns": []}
        return {"ok": True, "patterns": self.reflector.detect_patterns(days)}

    def reflector_episodes(self) -> list:
        return [e.to_dict() for e in self.reflector.episodes(20)] if self.reflector else []

    # -- security -------------------------------------------------------------
    def enroll_owner(self) -> Dict[str, Any]:
        """Capture several camera frames (multi-sample) and enroll the owner."""
        if self.face_auth is None:
            return {"ok": False, "detail": "face_auth unavailable"}
        try:
            res = self.face_auth.enroll_from_camera(frames=6, delay=0.25)
            return {"ok": True, "detail": f"enrolled (backend={res['backend']}, samples={res['samples']})"}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def guard_arm(self) -> Dict[str, Any]:
        if self.guard is None:
            return {"ok": False, "detail": "guard unavailable"}
        ok = self.guard.arm()
        return {"ok": ok, "detail": "armed" if ok else "cannot arm (enroll owner / camera?)"}

    def guard_disarm(self) -> Dict[str, Any]:
        if self.guard:
            self.guard.disarm()
        return {"ok": True, "detail": "disarmed"}

    def guard_snapshot(self) -> Dict[str, Any]:
        return self.guard.snapshot() if self.guard else {"verdict": "unavailable"}

    def set_intruder_hook(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        self._intruder_hook = fn

    def _on_intruder(self, event: Dict[str, Any]) -> None:
        self._cancel_requested["cancel"] = False  # reset per event
        if self._intruder_hook:
            try:
                self._intruder_hook(event)
            except Exception as e:
                logger.warning(f"intruder hook error: {e}")
        logger.warning(f"Security: intruder event -> {event}")

    def cancel_lockdown(self) -> None:
        self._cancel_requested["cancel"] = True

    def manual_lock(self) -> Dict[str, Any]:
        if self.lockdown is None:
            return {"ok": False, "detail": "lockdown unavailable"}
        ev = self.lockdown.lock_with_countdown(reason="manual lock from OMNI app", block=False)
        return {"ok": True, "detail": f"lock in {ev['countdown']}s"}

    def lock_history(self) -> list:
        return self.lockdown.history() if self.lockdown else []

    def intruder_events(self) -> list:
        return self.guard.events() if self.guard else []

    # -- internal notify (guard pre-lock alert) -------------------------------
    def _notify(self, text: str) -> None:
        if self.messenger is not None and getattr(self.messenger, "channel", "file") != "file" and not isinstance(self.messenger, FileMessenger):
            try:
                self.messenger.send_text(text)
            except Exception as e:
                logger.warning(f"guard alert send failed: {e}")


def get_desktop_controller(**kwargs) -> DesktopController:
    return DesktopController(**kwargs)
