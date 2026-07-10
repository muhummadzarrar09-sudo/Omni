"""
OMNI Reasoner - The Autonomy Engine
===================================

Implements the Plan -> Act -> Observe -> Correct loop.
Transforms OMNI from a command-executor into a goal-oriented agent.

Current Strategy: Hybrid Reasoning
- Fast Path: Direct execution for simple, high-confidence commands.
- Reasoning Path: Iterative loop for complex tasks or failing actions.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from loguru import logger

from omni.core.command_registry import ParsedCommand

@dataclass
class ActionStep:
    """A single step in a reasoning plan"""
    action: str
    entities: Dict[str, Any]
    description: str
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class ExecutionResult:
    """The outcome of a reasoning loop"""
    success: bool
    final_message: str
    steps_taken: List[str]
    observations: List[str]

class OmniReasoner:
    """
    The brain that manages the autonomy loop.
    """
    
    def __init__(self, plugin_manager, tts=None):
        self.plugin_manager = plugin_manager
        self.tts = tts
        self.max_loop_iterations = 5
        self.base_retry_delay = 1.0 # seconds
        
    async def solve(self, parsed: ParsedCommand, context: Dict[str, Any]) -> ExecutionResult:
        """
        The main entry point for autonomous goal achievement.
        """
        logger.info(f"Reasoner: Solving goal -> '{parsed.original}'")
        
        # 1. Planning Phase
        # For now, we map the parsed command to an initial action step.
        # In future iterations, this can be replaced by an LLM planner.
        plan = [
            ActionStep(
                action=parsed.action,
                entities=parsed.entities,
                description=f"Executing {parsed.action} as requested"
            )
        ]
        
        steps_taken = []
        observations = []
        
        # 2. The Reasoning Loop
        iteration = 0
        while iteration < self.max_loop_iterations:
            iteration += 1
            if not plan:
                break
                
            current_step = plan.pop(0)
            steps_taken.append(current_step.description)
            
            # ACT
            result = await self._execute_step(current_step, context)
            
            # OBSERVE
            # We ask the plugin if the action actually achieved the goal
            is_verified = await self._verify_success(current_step, result, context)
            
            if is_verified:
                observations.append("Verification SUCCESS: Goal state achieved.")
                return ExecutionResult(
                    success=True, 
                    final_message=result.message or "Goal achieved successfully", 
                    steps_taken=steps_taken, 
                    observations=observations
                )
            
            # CORRECT
            observations.append(f"Verification FAILED: {result.message or 'Action did not produce expected result'}")
            
            if current_step.retry_count < current_step.max_retries:
                current_step.retry_count += 1
                # Strategy: Incremental backoff + Action modification
                delay = self.base_retry_delay * current_step.retry_count
                logger.warning(f"Reasoner: Step failed. Retrying in {delay}s (Attempt {current_step.retry_count}/{current_step.max_retries})")
                
                if self.tts:
                    self.tts.speak(f"Still trying to {current_step.action.split('_')[-1]}... please wait.")
                
                await asyncio.sleep(delay)
                plan.insert(0, current_step) # Put it back at the front to try again
            else:
                logger.error(f"Reasoner: Step {current_step.description} failed after max retries.")
                return ExecutionResult(
                    success=False,
                    final_message=f"I tried several times but couldn't complete the action: {result.message}",
                    steps_taken=steps_taken,
                    observations=observations
                )

        return ExecutionResult(
            success=False,
            final_message="I hit a reasoning limit and couldn't find a solution.",
            steps_taken=steps_taken,
            observations=observations
        )

    async def _execute_step(self, step: ActionStep, context: Dict[str, Any]) -> Any:
        """Interface with the plugin manager to perform the actual work."""
        plugin = self.plugin_manager.get_plugin(step.action)
        if not plugin:
            return type('obj', (object,), {'success': False, 'message': 'Plugin not found'})
        
        return await plugin.execute(step.entities, context)

    async def _verify_success(self, step: ActionStep, result: Any, context: Dict[str, Any]) -> bool:
        """
        The 'Observation' phase. Checks if the plugin's action actually worked.
        """
        # 1. If the plugin explicitly failed, verification is False
        if not result.success:
            return False
            
        # 2. Check if the plugin provides a verification method
        # This is the 'Secret Sauce' - plugins must implement 'verify_action'
        plugin = self.plugin_manager.get_plugin(step.action)
        if plugin and hasattr(plugin, 'verify_action'):
            try:
                return await plugin.verify_action(step.entities, context)
            except Exception as e:
                logger.error(f"Verification error for {step.action}: {e}")
                return False
                
        # 3. Fallback: If no verification method exists, we trust the plugin's success return
        return True
