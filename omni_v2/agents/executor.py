"""Executor Agent - Runs steps via plugin manager"""
from typing import Dict, Any

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ExecutorV2")

from omni_v2.core.command_registry import ActionStep
from omni_v2.core.plugin_manager import PluginManager, CommandResult

class ExecutorAgent:
    """Executor: Runs each step, uses 100+ tools"""

    def __init__(self, plugin_manager: PluginManager = None):
        self.plugin_manager = plugin_manager
        logger.info("ExecutorAgent V2 initialized (100+ tools)")

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
            logger.error(f"No plugin for {step.action}")
            return CommandResult.error(f"Plugin not found for {step.action}")

        try:
            result = await plugin.execute(step.entities, context)
            logger.info(f"Executor result: {step.action} -> success={result.success} msg={result.message[:80]}")
            return result
        except Exception as e:
            logger.error(f"Executor error for {step.action}: {e}")
            return CommandResult.error(str(e))

    async def execute_chain(self, steps: list[ActionStep], context: Dict[str, Any] = None) -> list[CommandResult]:
        results = []
        for step in steps:
            result = await self.execute_step(step, context)
            results.append(result)
            # If step fails, continue to next? Or stop? For Phase 1, continue
            if not result.success:
                logger.warning(f"Step {step.step_index} failed but continuing chain: {result.message}")
        return results
