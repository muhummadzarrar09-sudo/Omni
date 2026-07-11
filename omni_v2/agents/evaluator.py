"""Evaluator Agent - Checks overall goal achieved, re-plans if needed"""
from typing import List, Dict, Any
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("EvaluatorV2")

from omni_v2.core.command_registry import ActionStep
from omni_v2.core.plugin_manager import CommandResult

@dataclass
class ExecutionResult:
    success: bool
    final_message: str
    steps_taken: List[str]
    observations: List[str]

class EvaluatorAgent:
    """Evaluator: Checks if goal achieved, learns from failures, re-plans"""

    def __init__(self):
        self.max_retries = 2
        logger.info("EvaluatorAgent V2 initialized (re-planning)")

    def evaluate(self, goal: str, steps: List[ActionStep], results: List[CommandResult]) -> ExecutionResult:
        """Evaluate if overall goal achieved"""

        steps_taken = [s.description for s in steps]
        observations = []

        # Count successes
        success_count = sum(1 for r in results if r.success)
        total = len(results)

        # Collect messages
        messages = [r.message for r in results if r.message]

        if total == 0:
            return ExecutionResult(
                success=False,
                final_message="No steps executed - could not understand goal",
                steps_taken=steps_taken,
                observations=["No steps planned"]
            )

        # Overall success: all steps success OR at least one success for single-step goals
        # For chain, 70% success is enough (some steps may fail but overall goal achieved)
        if total == 1:
            overall_success = results[0].success
        else:
            overall_success = success_count >= total * 0.6  # 60% for chain

        if overall_success:
            # Build final message from all results
            final_msg = " | ".join(messages[:3])  # First 3 messages
            if len(messages) > 3:
                final_msg += f" + {len(messages)-3} more"
            if not final_msg:
                final_msg = f"Completed {success_count}/{total} steps for: {goal}"

            observations.append(f"SUCCESS: {success_count}/{total} steps")
            observations.append(f"Goal: {goal}")

            return ExecutionResult(
                success=True,
                final_message=final_msg,
                steps_taken=steps_taken,
                observations=observations
            )
        else:
            # Failure - could re-plan here
            failed_msgs = [r.message for r in results if not r.success]
            final_msg = f"Failed {total-success_count}/{total} steps: " + " | ".join(failed_msgs[:2])

            observations.append(f"FAILED: {success_count}/{total} steps")
            observations.append(f"Failed: {failed_msgs}")

            return ExecutionResult(
                success=False,
                final_message=final_msg,
                steps_taken=steps_taken,
                observations=observations
            )

    def should_replan(self, result: ExecutionResult) -> bool:
        """Should we re-plan and retry?"""
        if result.success:
            return False
        # If failed due to plugin not found, re-plan with alternative
        if "not found" in result.final_message.lower() or "unknown" in result.final_message.lower():
            return True
        return False

    def replan(self, original_goal: str, failed_result: ExecutionResult) -> List[ActionStep]:
        """Re-plan with alternative approach"""
        logger.info(f"Evaluator: Re-planning for '{original_goal}' after failure: {failed_result.final_message}")

        # Simple re-plan: try alternative phrasings or fallbacks
        # For Phase 1, just return empty (no re-plan yet)
        # Phase 2 will implement LLM-based re-planning

        return []
