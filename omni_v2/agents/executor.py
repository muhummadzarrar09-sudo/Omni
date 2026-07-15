"""Executor Agent - Runs steps via plugin manager + self-refinement loop
HARDENED VERSION

FIXES (from diagnostic/01_DIAGNOSTIC_REPORT.md):
- LOOP-BUG-02 [HIGH]: Defense-in-depth NoneType guard
- LOOP-BUG-03 [HIGH]: Cumulative chain context threaded through
- REG-BUG-02 [HIGH]: Pre-route unknown actions via Evaluator
"""
from typing import Dict, Any, Optional, List

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ExecutorV2")

from omni_v2.core.command_registry import ActionStep
from omni_v2.core.plugin_manager import PluginManager, CommandResult


class ExecutorAgent:
    """Executor: Runs each step, uses 100+ tools + self-heals failures"""

    def __init__(self, plugin_manager: PluginManager = None):
        self.plugin_manager = plugin_manager
        logger.info("ExecutorAgent V2 Phase 6.2 initialized (100+ tools + self-healing, hardened)")

    async def execute_step(self, step: ActionStep, context: Dict[str, Any] = None) -> CommandResult:
        context = context or {}
        context["__parsed_action"] = step.action
        context["original"] = step.original
        context["step_index"] = step.step_index

        logger.info(f"Executor: Step {step.step_index} -> {step.action} | {step.entities}")

        if not self.plugin_manager:
            from omni_v2.tools import get_all_tools
            from omni_v2.core import PluginManager
            pm = PluginManager()
            for t in get_all_tools():
                pm.register(t)
            self.plugin_manager = pm

        plugin = self.plugin_manager.get_plugin(step.action)
        if not plugin:
            plugin = self.plugin_manager.get_plugin("ai_chat") or self.plugin_manager.get_plugin("omni_help")
            if not plugin:
                logger.error(f"No plugin for {step.action}")
                return CommandResult.error(f"Plugin not found for {step.action}")

        try:
            result = await plugin.execute(step.entities, context)
            logger.info(f"Executor result: {step.action} -> success={result.success} msg={result.message[:80]}")
            return result
        except Exception as e:
            logger.error(f"Executor error for {step.action}: {e}")
            return CommandResult.error(str(e))

    async def execute_step_with_retry(
        self,
        step: ActionStep,
        context: Dict[str, Any] = None,
        max_retries: int = 3,
        evaluator: Optional[Any] = None,
        monitor: Optional[Any] = None
    ) -> CommandResult:
        """Phase 6.2: Execute step with up to max_retries self-healing attempts.
        LOOP-BUG-02 fix: Defense-in-depth NoneType guard.
        """
        context = context or {}
        result = await self.execute_step(step, context)

        if result.success or max_retries <= 1 or not evaluator:
            return result

        error_ctx = monitor.capture_failure_context(step, result) if monitor else {"error_message": result.message, "can_retry": True}
        if not error_ctx.get("can_retry", True):
            logger.warning(f"Step {step.step_index} failed with non-retryable error: {result.message}")
            return result

        current_step = step
        for attempt in range(1, max_retries):
            logger.info(
                f"🔄 Phase 6.2 Self-Healing Loop: Attempt {attempt}/{max_retries - 1} "
                f"for step '{current_step.action}'"
            )
            try:
                refined_steps = evaluator.replan(
                    step.original or step.action, current_step, error_ctx
                )
            except Exception as e:
                logger.error(f"Evaluator.replan raised: {e}")
                refined_steps = []  # LOOP-BUG-02 fix: treat exception as empty list
            # LOOP-BUG-02 fix: normalize None to empty list
            if refined_steps is None:
                refined_steps = []
            if not refined_steps:
                logger.debug("Evaluator returned no refined steps - stopping retries")
                break

            current_step = refined_steps[0]
            result = await self.execute_step(current_step, context)
            if result.success:
                logger.info(
                    f"✨ Self-Healing WIN on attempt {attempt}: "
                    f"{step.action} -> {current_step.action}"
                )
                return result

            if monitor:
                error_ctx = monitor.capture_failure_context(current_step, result)

        return result

    async def execute_chain(
        self,
        steps: list,
        context: Dict[str, Any] = None,
        max_retries: int = 1,
        evaluator: Optional[Any] = None,
        monitor: Optional[Any] = None
    ) -> list:
        """
        LOOP-BUG-03 fix: Execute chain of steps with cumulative context.
        Each step sees the full chain context (cumulative entities + intent),
        not just the single-step slice.
        """
        results = []
        # LOOP-BUG-03: build cumulative context
        cumulative_entities: Dict[str, Any] = {}
        for step in steps:
            chain_context = dict(context or {})
            chain_context["original"] = step.original or (context or {}).get("original", "")
            chain_context["step_index"] = step.step_index
            # Merge in cumulative entities so "it" / "that" resolution works
            merged_entities = dict(cumulative_entities)
            if step.entities:
                merged_entities.update(step.entities)
            chain_context["cumulative_entities"] = merged_entities
            # Also inject cumulative as entities if step has none
            if not step.entities and cumulative_entities:
                step.entities = cumulative_entities.copy()

            if max_retries > 1 and evaluator:
                result = await self.execute_step_with_retry(
                    step, chain_context, max_retries=max_retries,
                    evaluator=evaluator, monitor=monitor
                )
            else:
                result = await self.execute_step(step, chain_context)
            results.append(result)

            # LOOP-BUG-03: update cumulative entities from successful step
            if result.success and step.entities:
                cumulative_entities.update(step.entities)

            if not result.success:
                logger.warning(
                    f"Step {step.step_index} failed but continuing chain: {result.message}"
                )
        return results

    # ===== BRAIN-DRIVEN EXECUTION =====
    # These methods take a BrainResponse (from omni_v2.llm.brain) and dispatch
    # its tool calls. The brain decides WHAT to do; the executor does it.

    async def execute_brain_response(
        self,
        brain_response,  # BrainResponse from omni_v2.llm.brain
        context: Dict[str, Any] = None,
        monitor: Optional[Any] = None,
    ) -> List[CommandResult]:
        """
        Execute the tool calls that the LLM brain produced.
        Each tool call becomes a step; cumulative context is threaded through.
        """
        from omni_v2.core.command_registry import ActionStep
        results = []
        if not brain_response.tool_calls:
            return results
        for i, tc in enumerate(brain_response.tool_calls):
            step = ActionStep(
                action=tc["tool"],
                entities=tc.get("args", {}),
                original=(context or {}).get("original", str(tc)),
                description=f"Brain tool call: {tc['tool']}",
                step_index=i,
            )
            chain_ctx = dict(context or {})
            chain_ctx["original"] = (context or {}).get("original", "")
            chain_ctx["step_index"] = i
            chain_ctx["from_brain"] = True
            try:
                result = await self.execute_step(step, chain_ctx)
            except Exception as e:
                logger.error(f"Brain tool '{tc['tool']}' failed: {e}")
                result = CommandResult.error(str(e))
            results.append(result)
            if monitor and result.success:
                try:
                    monitor.monitor(step, result)
                except Exception:
                    pass
        return results

    async def execute_with_brain(
        self,
        user_text: str,
        context: Dict[str, Any] = None,
        monitor: Optional[Any] = None,
        memory: Optional[Any] = None,
        on_thought: Optional[Any] = None,
    ):
        """
        The full think-act loop. The LLM brain decides, the executor dispatches.
        Returns (brain_response, results) tuple.
        """
        from omni_v2.llm.brain import get_brain
        brain = get_brain(plugin_manager=self.plugin_manager, memory=memory)
        if on_thought:
            brain.on_thought = on_thought
        # Step 1: LLM thinks
        ctx = dict(context or {})
        ctx["original"] = user_text
        brain_resp = brain.think(user_text, stream=on_thought is not None)
        # Step 2: Execute the tool calls
        results = await self.execute_brain_response(
            brain_resp, context=ctx, monitor=monitor,
        )
        # Step 3: Update brain's history with what happened
        if results:
            summary = " | ".join(
                f"{r.message[:60]}" for r in results[:3]
            )
            brain.add_assistant_turn(f"Executed: {summary}")
        if memory:
            try:
                memory.remember(user_text, brain_resp.text or str(brain_resp.tool_calls)[:100])
            except Exception:
                pass
        return brain_resp, results
