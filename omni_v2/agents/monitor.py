"""Monitor Agent - Watches execution & captures failure context
HARDENED VERSION

FIXES (from diagnostic/01_DIAGNOSTIC_REPORT.md):
- LOOP-BUG-04 [HIGH]: Inspect result.message for known failure substrings
"""
import time
from typing import Dict, Any, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("MonitorV2")

from omni_v2.core.command_registry import ActionStep
from omni_v2.core.plugin_manager import CommandResult

try:
    from omni_v2.memory.fast_af_store import get_fast_af_store
except ImportError:
    get_fast_af_store = None

# Substrings that strongly indicate a failed action even if result.success is True
# (defensive: some plugins return success=True for partial completion)
FAILURE_INDICATORS = [
    "errno", "winerror", "permission denied", "not found",
    "no such file", "failed to", "could not", "denied",
    "missing", "unauthorized", "blocked", "exception",
    "error:", "error ", "traceback", "stack trace"
]


class MonitorAgent:
    """Monitor: Checks if action succeeded and extracts deep failure diagnostics"""

    def __init__(self):
        self.fast_af = get_fast_af_store() if get_fast_af_store else None
        logger.info("MonitorAgent V2 Phase 6.2 initialized (observes & diagnoses, hardened)")

    def monitor(self, step: ActionStep, result: CommandResult) -> bool:
        """
        Check if step succeeded - best-effort verification + FastAF telemetry.
        LOOP-BUG-04 fix: actually inspect result.message for known failure patterns.
        """
        t0 = time.perf_counter()

        if not result.success:
            logger.debug(
                f"Monitor: Step {step.step_index} ({step.action}) failed -> {result.message[:100]}"
            )
            if self.fast_af:
                try:
                    self.fast_af.log_execution(
                        step.action, False,
                        (time.perf_counter() - t0) * 1000.0,
                        result.message
                    )
                except Exception:
                    pass
            return False

        # LOOP-BUG-04 fix: inspect result.message for failure indicators
        msg_lower = (result.message or "").lower()
        for indicator in FAILURE_INDICATORS:
            if indicator in msg_lower:
                logger.warning(
                    f"Monitor: Step {step.step_index} reports success but message contains '{indicator}' "
                    f"- treating as failure. msg={result.message[:100]}"
                )
                if self.fast_af:
                    try:
                        self.fast_af.log_execution(
                            step.action, False,
                            (time.perf_counter() - t0) * 1000.0,
                            f"False success: {result.message[:80]}"
                        )
                    except Exception:
                        pass
                return False

        # Real success path
        trusted = ["browser", "system", "windows", "vscode", "omni", "alpha", "media", "files", "ai", "integrations"]
        category = step.action.split("_")[0] if "_" in step.action else ""
        if category in trusted:
            logger.debug(f"Monitor: Step {step.step_index} trusted category {category} -> success")
        else:
            logger.debug(f"Monitor: Step {step.step_index} -> success (best-effort)")

        if self.fast_af:
            try:
                self.fast_af.log_execution(
                    step.action, True,
                    (time.perf_counter() - t0) * 1000.0,
                    result.message
                )
            except Exception:
                pass

        return True

    def capture_failure_context(self, step: ActionStep, result: CommandResult) -> Dict[str, Any]:
        """Phase 6.2: Extract structured failure context for Evaluator / GGUF refinement"""
        error_msg = result.message or "Unknown error"

        is_missing_app = any(k in error_msg.lower() for k in [
            "no such file", "not found", "errno 2", "winerror 2",
            "cannot find", "could not find", "no such file or directory"
        ])
        is_unknown_plugin = "plugin not found" in error_msg.lower() or "no plugin for" in error_msg.lower()
        is_permission_err = any(k in error_msg.lower() for k in [
            "permission denied", "errno 13", "winerror 5", "access denied"
        ])

        errno_code = None
        if "errno " in error_msg.lower():
            try:
                errno_code = int(error_msg.lower().split("errno ")[1].split("]")[0].split(":")[0].strip())
            except Exception:
                pass
        if errno_code is None and "winerror " in error_msg.lower():
            try:
                errno_code = int(error_msg.lower().split("winerror ")[1].split("]")[0].strip().split()[0])
            except Exception:
                pass

        context = {
            "failed_step": step.action,
            "step_index": step.step_index,
            "entities": step.entities,
            "original_goal": step.original,
            "error_message": error_msg,
            "errno_code": errno_code,
            "is_missing_app": is_missing_app,
            "is_unknown_plugin": is_unknown_plugin,
            "is_permission_err": is_permission_err,
            "can_retry": not is_permission_err,
            "timestamp": time.time()
        }

        logger.info(
            f"🔍 Monitor diagnosed failure: {step.action} | missing_app={is_missing_app} | "
            f"can_retry={context['can_retry']}"
        )
        return context

    def monitor_chain(self, steps: list, results: list) -> Dict[str, Any]:
        """Monitor entire chain"""
        success_count = sum(1 for r in results if r.success)
        total = len(results)
        # Use Monitor's stricter check per-step
        verified_results = []
        for step, result in zip(steps, results):
            verified_results.append(self.monitor(step, result))
        true_success_count = sum(1 for v in verified_results if v)
        overall_success = true_success_count == total or true_success_count >= total * 0.7

        report = {
            "total_steps": total,
            "success_steps": true_success_count,
            "failed_steps": total - true_success_count,
            "overall_success": overall_success,
            "success_rate": true_success_count / max(total, 1)
        }

        logger.info(
            f"Monitor Chain: {true_success_count}/{total} steps succeeded, overall={overall_success}"
        )
        return report
