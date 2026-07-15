"""Executor Agent - Runs steps via plugin manager + self-refinement loop (Phase 6.2)"""
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
        logger.info("ExecutorAgent V2 Phase 6.2 initialized (100+ tools + self-healing)")

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

    async def execute_step_with_retry(self, step: ActionStep, context: Dict[str, Any] = None, max_retries: int = 3, evaluator: Optional[Any] = None, monitor: Optional[Any] = None) -> CommandResult:
        """Phase 6.2: Execute step with up to max_retries self-healing attempts via Evaluator/Monitor"""
        context = context or {}
        result = await self.execute_step(step, context)
        
        if result.success or max_retries <= 1 or not evaluator:
            return result

        # Check if failure context allows retry
        error_ctx = monitor.capture_failure_context(step, result) if monitor else {"error_message": result.message, "can_retry": True}
        if not error_ctx.get("can_retry", True):
            logger.warning(f"Step {step.step_index} failed with non-retryable error: {result.message}")
            return result

        # Self-healing loop
        current_step = step
        for attempt in range(1, max_retries):
            logger.info(f"🔄 Phase 6.2 Self-Healing Loop: Attempt {attempt}/{max_retries - 1} for step '{current_step.action}'")
            refined_steps = evaluator.replan(step.original or step.action, current_step, error_ctx) or []
            if not refined_steps:
                logger.debug("Evaluator returned no refined steps - stopping retries")
                break

            current_step = refined_steps[0]
            result = await self.execute_step(current_step, context)
            if result.success:
                logger.info(f"✨ Self-Healing WIN on attempt {attempt}: {step.action} -> {current_step.action}")
                return result

            # Update error context for next retry if needed
            if monitor:
                error_ctx = monitor.capture_failure_context(current_step, result)

        return result

    async def execute_chain(self, steps: list[ActionStep], context: Dict[str, Any] = None, max_retries: int = 1, evaluator: Optional[Any] = None, monitor: Optional[Any] = None) -> list[CommandResult]:
        """Execute chain of steps, optionally self-healing each via execute_step_with_retry"""
        results = []
        for step in steps:
            if max_retries > 1 and evaluator:
                result = await self.execute_step_with_retry(step, context, max_retries=max_retries, evaluator=evaluator, monitor=monitor)
            else:
                result = await self.execute_step(step, context)
            results.append(result)
            if not result.success:
                logger.warning(f"Step {step.step_index} failed but continuing chain: {result.message}")
        return results
