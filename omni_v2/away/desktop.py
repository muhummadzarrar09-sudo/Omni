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
        self.harness = self.stack.get("harness")
        if self.harness is None:
            try:
                from omni_v2.harness.harness import ContinualHarness
                self.harness = ContinualHarness()
            except Exception:
                self.harness = None
        self.skill_verifier = self.stack.get("skill_verifier")
        if self.skill_verifier is None and self.harness is not None:
            try:
                from omni_v2.harness.verifier import SkillVerificationLoop
                self.skill_verifier = SkillVerificationLoop(harness=self.harness)
                self.harness.post_skill_hook = self.skill_verifier.hook
            except Exception:
                self.skill_verifier = None
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

        # -- voice loop + guardian (Phase 10) --------------------------------
        self.voice_loop = None
        self.guardian = None
        # -- MCP bridge (Phase 13) -------------------------------------------
        self.mcp_bridge = None
        # -- sub-agent delegation (Phase 13 #4) ------------------------------
        self.delegator = None
        # -- automation triggers (Phase 13 #5) -------------------------------
        self.triggers = None
        # -- LLM router v2 (Phase 13 #6) -------------------------------------
        self.router_v2 = None
        # -- benchmark (Phase 14 #2) ------------------------------------------
        self.benchmark = None
        # -- credential vault (Phase 14 #4) -----------------------------------
        self.vault = None
        # -- personal context (Phase 14 #5) -----------------------------------
        self._calendar = None
        self._contacts_store = None
        # -- recurring scheduler (Phase 15 #1) --------------------------------
        self._recurring = None

    def _get_recurring(self):
        if self._recurring is not None:
            return self._recurring
        try:
            from omni_v2.schedule.recurring import RecurringScheduler, make_scheduler_runner
            self._recurring = RecurringScheduler(runner=make_scheduler_runner(self))
        except Exception as e:
            logger.warning(f"recurring build failed: {e}")
            self._recurring = None
        return self._recurring

    def schedule_add_cron(self, name, cron, action, args=None) -> Dict[str, Any]:
        s = self._get_recurring()
        if s is None:
            return {"ok": False, "detail": "scheduler unavailable"}
        try:
            j = s.add_cron(name, cron, action, args or {})
            return {"ok": True, "job": j.to_dict()}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def schedule_add_interval(self, name, seconds, action, args=None) -> Dict[str, Any]:
        s = self._get_recurring()
        if s is None:
            return {"ok": False, "detail": "scheduler unavailable"}
        try:
            j = s.add_interval(name, int(seconds), action, args or {})
            return {"ok": True, "job": j.to_dict()}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def schedule_list(self) -> Dict[str, Any]:
        s = self._get_recurring()
        return {"ok": True, "jobs": [j.to_dict() for j in s.list()] if s else []}

    def schedule_remove(self, name: str) -> Dict[str, Any]:
        s = self._get_recurring()
        return {"ok": bool(s and s.remove(name))}

    def schedule_fire(self, name: str) -> Dict[str, Any]:
        s = self._get_recurring()
        return s.fire(name) if s else {"ok": False, "detail": "unavailable"}

    def schedule_stats(self) -> Dict[str, Any]:
        s = self._get_recurring()
        return s.stats() if s else {"jobs": 0}

    @property
    def calendar(self):
        if self._calendar is None:
            try:
                from omni_v2.personal.calendar_contacts import CalendarParser
                self._calendar = CalendarParser()
            except Exception as e:
                logger.warning(f"calendar build failed: {e}")
                self._calendar = None
        return self._calendar

    @property
    def contacts(self):
        if self._contacts_store is None:
            try:
                from omni_v2.personal.calendar_contacts import ContactStore
                self._contacts_store = ContactStore()
            except Exception as e:
                logger.warning(f"contacts build failed: {e}")
                self._contacts_store = None
        return self._contacts_store

    def calendar_upcoming(self, hours: int = 24) -> Dict[str, Any]:
        cal = self.calendar
        return {"ok": True, "events": cal.upcoming(hours=hours) if cal else []}

    def contacts_lookup(self, name: str) -> Dict[str, Any]:
        cs = self.contacts
        c = cs.lookup(name) if cs else None
        return {"ok": c is not None, "contact": c}

    def kb_query_cited(self, question: str) -> Dict[str, Any]:
        return self.kb.query_with_citations(question) if self.kb else {"hit_count": 0}

    # -- wake routine (Phase 14 #7) -------------------------------------------
    def wake_run(self, speak: bool = True, push: bool = True) -> Dict[str, Any]:
        from omni_v2.wake.wake_routine import WakeRoutine
        from omni_v2.briefing.briefing import MorningBriefing
        from omni_v2.away.messenger import MessengerRouter
        try:
            briefing = MorningBriefing(goals=self.goals, reflector=self.reflector,
                                       reporter=self.reporter, messenger=self.messenger,
                                       identity=self.identity)
        except Exception:
            briefing = None
        w = WakeRoutine(identity=self.identity, calendar=self.calendar,
                        briefing=briefing, tts=None,
                        messenger=self.messenger, guardian=self.guardian)
        return {"ok": True, **w.run(speak=speak, push=push)}

    def wake_status(self) -> Dict[str, Any]:
        from omni_v2.wake.wake_routine import WakeRoutine
        return {"ok": True, **WakeRoutine(identity=self.identity,
                                          calendar=self.calendar).status()}

    # -- harness leaderboard (Phase 14 #8b) -----------------------------------
    def _get_leaderboard(self):
        try:
            from omni_v2.leaderboard.leaderboard import Leaderboard
            return Leaderboard()
        except Exception as e:
            logger.warning(f"leaderboard build failed: {e}")
            return None

    def leaderboard_report(self, kind: str = "") -> Dict[str, Any]:
        lb = self._get_leaderboard()
        return {"ok": True, "report": lb.report(kind) if lb else {"total": 0}}

    def leaderboard_record(self, name: str, kind: str, ok: bool) -> Dict[str, Any]:
        lb = self._get_leaderboard()
        if lb is None:
            return {"ok": False}
        lb.record(name, kind=kind, ok=ok)
        return {"ok": True}

    def _get_vault(self):
        if self.vault is not None:
            return self.vault
        try:
            from omni_v2.vault.vault import CredentialVault
            self.vault = CredentialVault()
        except Exception as e:
            logger.warning(f"vault build failed: {e}")
            self.vault = None
        return self.vault

    def vault_set(self, name: str, value: str, callers: list = None,
                  metadata: str = "") -> Dict[str, Any]:
        v = self._get_vault()
        if v is None:
            return {"ok": False, "detail": "vault unavailable"}
        try:
            return v.set_secret(name, value, callers=callers, metadata=metadata)
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def vault_get(self, name: str, caller: str = "omni") -> Dict[str, Any]:
        v = self._get_vault()
        if v is None:
            return {"ok": False, "detail": "vault unavailable"}
        try:
            return {"ok": True, "name": name, "value": v.get_secret(name, caller)}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def vault_list(self) -> Dict[str, Any]:
        v = self._get_vault()
        return {"ok": True, "secrets": v.list_secrets() if v else []}

    def vault_stats(self) -> Dict[str, Any]:
        v = self._get_vault()
        return v.stats() if v else {"secrets": 0}

    def _get_benchmark(self):
        if self.benchmark is not None:
            return self.benchmark
        try:
            from omni_v2.benchmark.benchmark import BenchmarkRunner
            self.benchmark = BenchmarkRunner(harness=self.harness)
        except Exception as e:
            logger.warning(f"benchmark build failed: {e}")
            self.benchmark = None
        return self.benchmark

    def benchmark_run(self, case: str, briefs: list, iterations: int = 3,
                      executor=None) -> Dict[str, Any]:
        from omni_v2.benchmark.benchmark import BenchmarkCase
        b = self._get_benchmark()
        if b is None:
            return {"ok": False, "detail": "benchmark unavailable"}
        b.iterations = iterations
        if executor is None:
            executor = lambda brief, ctx: {"ok": True, "time": 1.0, "tokens": 60, "steps": 3}
        case_obj = BenchmarkCase(case, briefs, executor)
        b.run_case(case_obj)
        return {"ok": True, "report": b.report(case)}

    def benchmark_report(self, case: str = "") -> Dict[str, Any]:
        b = self._get_benchmark()
        return {"ok": True, "report": b.report(case) if b else {}}

    def benchmark_stats(self) -> Dict[str, Any]:
        b = self._get_benchmark()
        return {"iterations": len(b.all_results()) if b else 0}

    def _get_router_v2(self):
        if self.router_v2 is not None:
            return self.router_v2
        try:
            from omni_v2.llm.router_v2 import LLMRouterV2
            # On this machine, constrain to models we actually have; on the DGX
            # pass more. Default = all available (DGX-ready).
            self.router_v2 = LLMRouterV2()
        except Exception as e:
            logger.warning(f"router_v2 build failed: {e}")
            self.router_v2 = None
        return self.router_v2

    def router_select(self, text: str) -> Dict[str, Any]:
        r = self._get_router_v2()
        if r is None:
            return {"ok": False, "detail": "router unavailable"}
        dec = r.select(text)
        return {"ok": True, "decision": dec.to_dict()}

    def router_stats(self) -> Dict[str, Any]:
        r = self._get_router_v2()
        return r.stats() if r else {"tiers": []}

    def _get_triggers(self):
        if self.triggers is not None:
            return self.triggers
        try:
            from omni_v2.automation.triggers import TriggerManager, make_runner
            self.triggers = TriggerManager(
                runner=make_runner(goals=self.goals, research=self.research,
                                   away=self.away, messenger=self.messenger),
            )
        except Exception as e:
            logger.warning(f"triggers build failed: {e}")
            self.triggers = None
        return self.triggers

    def trigger_add(self, name: str, trigger: str, action: str, action_args: dict,
                    secret: str = "") -> Dict[str, Any]:
        t = self._get_triggers()
        if t is None:
            return {"ok": False, "detail": "triggers unavailable"}
        try:
            a = t.add(name, trigger, action, action_args, secret=secret)
            return {"ok": True, "automation": a.to_dict()}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def trigger_fire(self, name: str, payload: dict = None) -> Dict[str, Any]:
        t = self._get_triggers()
        if t is None:
            return {"ok": False, "detail": "unavailable"}
        return t.fire(name, payload or {})

    def trigger_list(self) -> Dict[str, Any]:
        t = self._get_triggers()
        return {"ok": True, "automations": [a.to_dict() for a in t.list()] if t else []}

    def trigger_stats(self) -> Dict[str, Any]:
        t = self._get_triggers()
        return t.stats() if t else {"triggers": 0}

    def _get_delegator(self):
        if self.delegator is not None:
            return self.delegator
        try:
            from omni_v2.agents.subagents import SubAgentDelegator
            self.delegator = SubAgentDelegator()
        except Exception as e:
            logger.warning(f"delegator build failed: {e}")
            self.delegator = None
        return self.delegator

    def delegate_goal(self, goal_id: str, step_handler=None) -> Dict[str, Any]:
        d = self._get_delegator()
        if d is None or self.goals is None:
            return {"ok": False, "summary": "delegator/goals unavailable"}
        g = self.goals.get_goal(goal_id)
        if g is None:
            return {"ok": False, "summary": f"no goal {goal_id}"}
        if step_handler is None:
            # default: route each step through the away research agent if available
            step_handler = self._default_step_handler
        return d.delegate_goal(g, goals_stack=self.goals, step_handler=step_handler)

    def _default_step_handler(self, brief: str):
        if self.research is not None:
            try:
                report = self.research.research(brief)
                return {"ok": True, "summary": f"{len(report.findings)} finding(s)"}
            except Exception as e:
                return {"ok": False, "summary": str(e)}
        return {"ok": True, "summary": f"handled: {brief[:60]}"}

    def delegator_stats(self) -> Dict[str, Any]:
        return self._get_delegator().stats() if self.delegator else {"spawned": 0}

    def _get_mcp(self):
        if self.mcp_bridge is not None:
            return self.mcp_bridge
        try:
            from omni_v2.core.plugin_manager import PluginManager
            from omni_v2.mcp.bridge import MCPBridge, FakeMCPProvider
            pm = PluginManager()
            # register all built-in tools into this manager so MCP can coexist
            try:
                from omni_v2.tools import get_all_tools
                for t in get_all_tools():
                    try:
                        pm.register(t)
                    except Exception:
                        pass
            except Exception:
                pass
            self.mcp_bridge = MCPBridge(plugin_manager=pm, provider=FakeMCPProvider())
        except Exception as e:
            logger.warning(f"mcp bridge build failed: {e}")
            self.mcp_bridge = None
        return self.mcp_bridge

    def mcp_add_server(self, name: str, tools: list, handlers: dict = None) -> Dict[str, Any]:
        m = self._get_mcp()
        if m is None:
            return {"ok": False, "detail": "mcp unavailable"}
        return {"ok": True, **m.add_server(name, tools=tools, handlers=handlers or {})}

    def mcp_list(self) -> Dict[str, Any]:
        m = self._get_mcp()
        return {"ok": True, "servers": m.list_servers() if m else []}

    def mcp_stats(self) -> Dict[str, Any]:
        m = self._get_mcp()
        return m.stats() if m else {"servers": 0}

    def _get_voice_loop(self):
        """Lazily build the VoiceLoop with real components when available."""
        if self.voice_loop is not None:
            return self.voice_loop
        try:
            from omni_v2.voice.voice_loop import VoiceLoop
            from omni_v2.voice.wake_word import WakeWordDetector
            from omni_v2.voice.stt_simple import SimpleSTT
            from omni_v2.voice.tts_best import TTSBest
            from omni_v2.llm.brain import get_brain
            self.voice_loop = VoiceLoop(
                wake_detector=WakeWordDetector(),
                stt=SimpleSTT(),
                brain=get_brain(),
                tts=TTSBest(),
                goals=self.goals,
                on_transcription=lambda t: logger.info(f"voice heard: {t}"),
            )
        except Exception as e:
            logger.warning(f"voice loop build failed: {e}")
            self.voice_loop = None
        return self.voice_loop

    def _get_guardian(self):
        if self.guardian is not None:
            return self.guardian
        try:
            from omni_v2.guardian.guardian import Guardian, process_checker, health_checker
            self.guardian = Guardian(
                interval=30.0,
                checkers=[process_checker(), health_checker()],
                notify_fn=lambda t: self._notify(t),
            )
        except Exception as e:
            logger.warning(f"guardian build failed: {e}")
            self.guardian = None
        return self.guardian

    def voice_respond(self, text: str) -> Dict[str, Any]:
        vl = self._get_voice_loop()
        if vl is None:
            return {"ok": False, "detail": "voice loop unavailable"}
        try:
            reply = vl.respond(text)
            return {"ok": True, "reply": reply}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def voice_start(self) -> Dict[str, Any]:
        vl = self._get_voice_loop()
        if vl is None:
            return {"ok": False, "detail": "voice loop unavailable"}
        return {"ok": vl.start(), "detail": "started" if vl.running else "could not start"}

    def voice_stop(self) -> Dict[str, Any]:
        if self.voice_loop:
            self.voice_loop.stop()
        return {"ok": True, "detail": "stopped"}

    def voice_stats(self) -> Dict[str, Any]:
        return self.voice_loop.stats() if self.voice_loop else {"running": False}

    def guardian_start(self) -> Dict[str, Any]:
        g = self._get_guardian()
        if g is None:
            return {"ok": False, "detail": "guardian unavailable"}
        return {"ok": g.start(), "detail": "started" if g.running else "no checkers"}

    def guardian_stop(self) -> Dict[str, Any]:
        if self.guardian:
            self.guardian.stop()
        return {"ok": True, "detail": "stopped"}

    def guardian_run_once(self) -> Dict[str, Any]:
        g = self._get_guardian()
        if g is None:
            return {"ok": False, "observations": []}
        return {"ok": True, "observations": g.run_once()}

    def guardian_recent(self) -> list:
        return self.guardian.recent(30) if self.guardian else []

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
        if self.harness:
            out["harness"] = self.harness.stats()
        if self.skill_verifier:
            out["skill_verifier"] = self.skill_verifier.stats()
        if self.mcp_bridge:
            out["mcp"] = self.mcp_bridge.stats()
        if self.delegator:
            out["delegator"] = self.delegator.stats()
        if self.triggers:
            out["automation"] = self.triggers.stats()
        if self.router_v2:
            out["router"] = self.router_v2.stats()
        if self.voice_loop:
            out["voice"] = self.voice_loop.stats()
        if self.guardian:
            out["guardian"] = self.guardian.stats()
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

    # -- continual harness (Phase 12) ------------------------------------------
    def harness_refine_goal(self, goal_id: str, success: bool = None,
                            repeated: bool = False) -> Dict[str, Any]:
        if self.harness is None or self.goals is None:
            return {"ok": False, "detail": "harness/goals unavailable"}
        g = self.goals.get_goal(goal_id)
        if g is None:
            return {"ok": False, "detail": f"no goal {goal_id}"}
        # gather metacog verdicts if available
        verdicts = []
        if self.metacog is not None:
            for rec in self.metacog.history(20):
                v = rec.get("verdict", {})
                if v.get("suggested_fix"):
                    verdicts.append(v)
        committed = self.harness.refine_from_trajectory(g, verdicts=verdicts,
                                                        success=success, repeated=repeated)
        return {"ok": True, "committed": committed}

    def harness_list(self, kind: str = "") -> Dict[str, Any]:
        if self.harness is None:
            return {"ok": False, "artifacts": []}
        arts = self.harness.list(kind or None)
        return {"ok": True, "artifacts": [a.to_dict() for a in arts]}

    def harness_rollback(self, kind: str, name: str) -> Dict[str, Any]:
        if self.harness is None:
            return {"ok": False, "detail": "harness unavailable"}
        ok = self.harness.rollback(kind, name)
        return {"ok": ok, "detail": "rolled back" if ok else "no snapshot"}

    def harness_context(self, topic: str = "") -> str:
        return self.harness.build_context(topic) if self.harness else ""

    def harness_stats(self) -> Dict[str, Any]:
        return self.harness.stats() if self.harness else {"artifacts": 0}

    # -- skill verification loop (Phase 13 #2) -------------------------------
    def skill_verify(self, kind: str = "skill", name: str = "") -> Dict[str, Any]:
        """Run verification on a harness artifact (or all skills if name empty)."""
        if self.skill_verifier is None or self.harness is None:
            return {"ok": False, "detail": "verifier unavailable"}
        if name:
            art = self.harness.get(kind, name)
            if art is None:
                return {"ok": False, "detail": f"no {kind} '{name}'"}
            return {"ok": True, "results": [self.skill_verifier.verify_skill(art)]}
        # verify all skills
        results = [self.skill_verifier.verify_skill(a)
                   for a in self.harness.list("skill")]
        return {"ok": True, "results": results}

    def skill_verify_stats(self) -> Dict[str, Any]:
        return self.skill_verifier.stats() if self.skill_verifier else {"checks": 0}

    def skill_verify_history(self) -> list:
        return self.skill_verifier.history(20) if self.skill_verifier else []

    # -- skill sandbox (Phase 14 #3) ----------------------------------------
    def skill_sandbox_run(self, code: str = "", skill_name: str = "") -> Dict[str, Any]:
        """Run a skill or code in the isolated sandbox."""
        from omni_v2.skills.sandbox import SkillSandbox
        s = SkillSandbox()
        if skill_name and self.harness is not None:
            art = self.harness.get("skill", skill_name)
            if art is None:
                return {"ok": False, "detail": f"no skill '{skill_name}'"}
            res = s.run_skill_artifact(art)
        elif code:
            res = s.run_skill_code(code)
        else:
            return {"ok": False, "detail": "provide code or skill_name"}
        return {"ok": res.ok, "result": res.to_dict()}

    def skill_sandbox_status(self) -> Dict[str, Any]:
        from omni_v2.skills.sandbox import SkillSandbox
        return {"ok": True, "status": SkillSandbox().stats()}

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
