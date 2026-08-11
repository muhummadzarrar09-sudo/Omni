"""
OMNI AWAY STACK - one-call wiring of the whole away-mode feature set.

`build_away_stack()` returns a dict with a live KnowledgeBase, AwayAgent,
ResearchAgent, Reporter, Messenger and a `context_provider` callable that the
Brain uses to inject hybrid RAG+CAG memory into every prompt.

This is the integration point for the FastAPI backend and the CLI.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Callable

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("AwayContext")


def build_away_stack(knowledge_base=None, reporter=None, messenger=None,
                     digest_fn: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    """Construct the full away-mode component set (shared instances)."""
    from omni_v2.away.knowledge_base import KnowledgeBase
    from omni_v2.away.research import ResearchAgent
    from omni_v2.away.reporter import Reporter
    from omni_v2.away.away_agent import AwayAgent
    from omni_v2.away.messenger import MessengerRouter
    from omni_v2.memory.hybrid_memory import get_hybrid_memory
    from omni_v2.brain.identity import IdentityCore
    from omni_v2.brain.goals import GoalStack
    from omni_v2.brain.metacog import Metacog
    from omni_v2.brain.reflect import Reflector
    from omni_v2.harness.harness import ContinualHarness
    from omni_v2.harness.verifier import SkillVerificationLoop
    from omni_v2.memory.session_memory import SessionMemoryStore

    kb = knowledge_base or KnowledgeBase()
    rep = reporter or Reporter()
    research = ResearchAgent(knowledge_base=kb)
    messenger_obj = messenger if messenger is not None else MessengerRouter()
    agent = AwayAgent(
        knowledge_base=kb,
        reporter=rep,
        research_agent=research,
        messenger=messenger_obj,
        digest_fn=digest_fn,
    )
    memory = kb.memory or get_hybrid_memory()
    identity = IdentityCore()
    metacog = Metacog()
    harness = ContinualHarness()
    # Auto skill verification: when the harness creates/refines a skill, run it
    # through the verification loop (tester) and roll back on failure.
    skill_verifier = SkillVerificationLoop(harness=harness)
    harness.post_skill_hook = skill_verifier.hook

    def _auto_refine_goal(goal, success: bool) -> None:
        """Auto post-goal flow: distill the finished goal into the Continual
        Harness (skills/memory/lessons). Runs in a thread."""
        try:
            verdicts = []
            try:
                for rec in metacog.history(20):
                    v = rec.get("verdict", {})
                    if v.get("suggested_fix"):
                        verdicts.append(v)
            except Exception:
                pass
            committed = harness.refine_from_trajectory(goal, verdicts=verdicts,
                                                       success=success,
                                                       repeated=False)
            logger.info(f"post-goal: auto-refined {goal.id} -> {committed}")
        except Exception as e:
            logger.warning(f"post-goal auto-refine failed: {e}")

    goals = GoalStack(notifier=messenger_obj.send_text,
                      post_goal_hook=_auto_refine_goal)
    try:
        session_store = SessionMemoryStore()
    except Exception:
        session_store = None
    reflector = Reflector(session_memory=session_store, hybrid_memory=memory,
                          identity=identity)

    def context_provider(question: str) -> str:
        """Inject hybrid RAG+CAG context for a user query (used by Brain)."""
        try:
            return memory.build_context(question)
        except Exception as e:
            logger.debug(f"context_provider error: {e}")
            return ""

    return {
        "knowledge_base": kb,
        "memory": memory,
        "reporter": rep,
        "research_agent": research,
        "messenger": messenger_obj,
        "away_agent": agent,
        "context_provider": context_provider,
        "identity": identity,
        "goals": goals,
        "metacog": metacog,
        "reflector": reflector,
        "harness": harness,
        "skill_verifier": skill_verifier,
        "mcp_bridge": None,   # lazy-built by consumers that can supply plugin_manager
        "voice_loop": None,   # lazy-built by consumers that can supply components
        "guardian": None,
    }
