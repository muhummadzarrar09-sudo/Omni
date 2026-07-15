"""Evaluator Agent - Checks overall goal achieved, learns from failures, re-plans (Phase 6.2)"""
import json
from typing import List, Dict, Any, Optional
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
    """Evaluator: Checks if goal achieved, learns from failures, re-plans via GGUF/Rule matrix"""

    def __init__(self, gguf_model: Optional[Any] = None):
        self.max_retries = 3
        self.gguf_model = gguf_model
        logger.info("EvaluatorAgent V2 Phase 6.2 initialized (self-refinement loop)")

    def evaluate(self, goal: str, steps: List[ActionStep], results: List[CommandResult]) -> ExecutionResult:
        """Evaluate if overall goal achieved"""
        steps_taken = [s.description for s in steps]
        observations = []

        success_count = sum(1 for r in results if r.success)
        total = len(results)
        messages = [r.message for r in results if r.message]

        if total == 0:
            return ExecutionResult(
                success=False,
                final_message="No steps executed - could not understand goal",
                steps_taken=steps_taken,
                observations=["No steps planned"]
            )

        if total == 1:
            overall_success = results[0].success
        else:
            overall_success = success_count >= total * 0.6  # 60% for chain

        if overall_success:
            final_msg = " | ".join(messages[:3])
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
        lower_msg = result.final_message.lower()
        if any(k in lower_msg for k in ["not found", "unknown", "no such file", "errno 2", "failed to open"]):
            return True
        return False

    def construct_repair_prompt(self, original_goal: str, failed_step: ActionStep, error_context: Dict[str, Any]) -> str:
        """Phase 6.2: Construct GGUF repair prompt for self-correction"""
        payload = {
            "goal": original_goal,
            "failed_action": failed_step.action,
            "failed_entities": failed_step.entities,
            "error_observed": error_context.get("error_message", "Unknown error"),
            "instruction": "Refine the step using fallback applications, alternative tools, or corrected parameters. Return ONLY JSON: {\"action\": \"new_action\", \"entities\": {...}}"
        }
        return json.dumps(payload)

    def replan(self, original_goal: str, failed_step: ActionStep, error_context: Dict[str, Any] = None) -> List[ActionStep]:
        """Phase 6.2: Re-plan failed step using GGUF brain or high-speed rule matrix"""
        error_context = error_context or {}
        logger.info(f"Evaluator: Re-planning for step '{failed_step.action}' | error={error_context.get('error_message', '')[:60]}")

        # 1. Check GGUF neural repair if loaded
        if self.gguf_model and hasattr(self.gguf_model, "generate"):
            try:
                prompt = self.construct_repair_prompt(original_goal, failed_step, error_context)
                response = self.gguf_model.generate(prompt, max_tokens=150)
                # Parse json from response
                if "{" in response and "}" in response:
                    json_str = response[response.find("{"):response.rfind("}")+1]
                    parsed = json.loads(json_str)
                    new_act = parsed.get("action")
                    new_ent = parsed.get("entities", {})
                    if new_act and new_act != failed_step.action:
                        logger.info(f"🧠 GGUF Refined: {failed_step.action} -> {new_act} | {new_ent}")
                        return [ActionStep(
                            action=new_act,
                            entities=new_ent,
                            original=original_goal,
                            description=f"Refined Step: {new_act} (via GGUF self-repair)",
                            step_index=failed_step.step_index
                        )]
            except Exception as e:
                logger.debug(f"GGUF neural repair fallback: {e}")

        # 2. High-speed Rule Matrix (Deterministic self-healing for common OS/browser missing errors)
        err_lower = str(error_context.get("error_message", "")).lower()
        act = failed_step.action
        ent = failed_step.entities.copy() if failed_step.entities else {}

        # Rule A: Windows launch chrome -> fallback to msedge or browser_navigate
        if act == "windows_launch" and ent.get("app") == "chrome" and ("not found" in err_lower or "errno 2" in err_lower):
            logger.info("🔧 Self-repair Rule A triggered: chrome missing -> trying msedge fallback")
            return [ActionStep(
                action="windows_launch",
                entities={"app": "msedge"},
                original=original_goal,
                description=f"Refined Step: windows_launch msedge (chrome not found fallback)",
                step_index=failed_step.step_index
            )]

        # Rule B: Windows launch notepad -> fallback to vscode or echo
        if act == "windows_launch" and ent.get("app") == "notepad" and ("not found" in err_lower or "errno 2" in err_lower):
            logger.info("🔧 Self-repair Rule B triggered: notepad missing -> trying vscode_open fallback")
            return [ActionStep(
                action="vscode_open",
                entities={"file": "notes.txt"},
                original=original_goal,
                description=f"Refined Step: vscode_open notes.txt (notepad not found fallback)",
                step_index=failed_step.step_index
            )]

        # Rule C: Unknown plugin -> check if we can synthesize a custom skill via SkillMakerAgent (Phase 6.3), else fallback to ai_chat
        if "plugin not found" in err_lower or act == "unknown":
            try:
                from omni_v2.skills import get_skill_maker, get_skill_registry
                maker = get_skill_maker(self.gguf_model)
                saved_path, synth_msg = maker.synthesize_skill(original_goal or failed_step.action)
                if saved_path and saved_path.exists():
                    reg = get_skill_registry()
                    new_skill = reg.load_skill_file(saved_path)
                    if new_skill and new_skill.metadata and new_skill.metadata.name:
                        logger.info(f"🧬 Phase 6.3 Synthesized & Registered Custom Skill: {new_skill.metadata.name}")
                        return [ActionStep(
                            action=new_skill.metadata.name,
                            entities=failed_step.entities or {},
                            original=original_goal,
                            description=f"Refined Step: {new_skill.metadata.name} (via Phase 6.3 SkillMakerAgent)",
                            step_index=failed_step.step_index
                        )]
            except Exception as e:
                logger.debug(f"Phase 6.3 dynamic skill synthesis fallback: {e}")

            logger.info("🔧 Self-repair Rule C triggered: unknown plugin -> routing to ai_chat universal engine")
            return [ActionStep(
                action="ai_chat",
                entities={"text": original_goal or "help"},
                original=original_goal,
                description=f"Refined Step: ai_chat universal routing ({act} fallback)",
                step_index=failed_step.step_index
            )]

        return []
