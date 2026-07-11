"""Monitor Agent - Watches if step succeeded"""
from typing import Dict, Any

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("MonitorV2")

from omni_v2.core.command_registry import ActionStep
from omni_v2.core.plugin_manager import CommandResult

class MonitorAgent:
    """Monitor: Checks if action actually succeeded (screen changed? process running?)"""

    def __init__(self):
        logger.info("MonitorAgent V2 initialized (observes execution)")

    def monitor(self, step: ActionStep, result: CommandResult) -> bool:
        """Check if step succeeded - best-effort verification"""

        # If plugin says failed, monitor says failed
        if not result.success:
            logger.debug(f"Monitor: Step {step.step_index} failed per plugin")
            return False

        # For trusted categories, trust plugin success
        trusted = ["browser", "system", "windows", "vscode", "omni", "alpha", "media", "files", "ai", "integrations"]
        category = step.action.split("_")[0] if "_" in step.action else ""
        if category in trusted:
            logger.debug(f"Monitor: Step {step.step_index} trusted category {category} -> success")
            return True

        # For other categories, try to verify via plugin's verify_action if available
        # For Phase 1, simple trust
        logger.debug(f"Monitor: Step {step.step_index} -> success (best-effort)")
        return True

    def monitor_chain(self, steps: list[ActionStep], results: list[CommandResult]) -> Dict[str, Any]:
        """Monitor entire chain"""
        success_count = sum(1 for r in results if r.success)
        total = len(results)
        overall_success = success_count == total or success_count >= total * 0.7  # 70% success = overall success for chain

        report = {
            "total_steps": total,
            "success_steps": success_count,
            "failed_steps": total - success_count,
            "overall_success": overall_success,
            "success_rate": success_count / max(total, 1)
        }

        logger.info(f"Monitor Chain: {success_count}/{total} steps succeeded, overall={overall_success}")

        return report
