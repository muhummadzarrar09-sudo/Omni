"""
Test Multi-Orchestrator Refinement Loop (Phase 6.2)
Run: python -m omni_v2.tests.test_hermes_refinement
"""

import asyncio
import sys
import time
from pathlib import Path

# Windows console UTF-8
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass

# Ensure repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from omni_v2.agents import ExecutorAgent, MonitorAgent, EvaluatorAgent
from omni_v2.core.command_registry import ActionStep
from omni_v2.core.plugin_manager import PluginManager, CommandResult, CommandPlugin, CommandMetadata

class MockFailingChromeTool(CommandPlugin):
    metadata = CommandMetadata(
        name="windows_launch",
        category="windows",
        description="Launch windows apps",
        patterns=[],
        examples=[]
    )
    SUPPORTED_ACTIONS = ["windows_launch"]
    
    async def execute(self, entities: dict, context: dict) -> CommandResult:
        app = entities.get("app", "")
        if app == "chrome":
            # Simulate real Errno 2 failure when chrome is not installed
            return CommandResult.error("[Errno 2] No such file or directory: 'chrome.exe'")
        elif app == "msedge":
            return CommandResult.ok("✅ Successfully launched Microsoft Edge (self-healed fallback for chrome)")
        return CommandResult.ok(f"Launched {app}")
    
    async def verify_action(self, e, c):
        return True

def test_hermes_refinement():
    print("="*65)
    print("  OMNI V3 - PHASE 6.2: HERMES MULTI-ORCHESTRATOR REFINEMENT LOOP")
    print("="*65)
    
    pm = PluginManager()
    pm.register(MockFailingChromeTool())
    
    executor = ExecutorAgent(pm)
    monitor = MonitorAgent()
    evaluator = EvaluatorAgent()
    
    # 1. Test failure diagnosis capture
    step1 = ActionStep(action="windows_launch", entities={"app": "chrome"}, original="open chrome", description="Step 1: open chrome", step_index=1)
    res_fail = asyncio.run(executor.execute_step(step1))
    print(f"\n1. Initial Step Execution -> success={res_fail.success} | msg={res_fail.message}")
    assert not res_fail.success, "Expected chrome launch to fail"
    
    diag = monitor.capture_failure_context(step1, res_fail)
    print(f"2. Monitor Diagnosis -> missing_app={diag['is_missing_app']} | errno={diag['errno_code']} | can_retry={diag['can_retry']}")
    assert diag["is_missing_app"] and diag["errno_code"] == 2 and diag["can_retry"], "Monitor did not diagnose Errno 2 correctly"
    
    # 2. Test Evaluator re-planning
    refined = evaluator.replan("open chrome", step1, diag)
    print(f"3. Evaluator Re-Plan -> {len(refined)} steps | new_action={refined[0].action} | new_app={refined[0].entities['app']}")
    assert len(refined) == 1 and refined[0].entities["app"] == "msedge", "Evaluator did not re-plan to msedge"
    
    # 3. Test full closed-loop self-healing execution
    print("\n4. Running execute_step_with_retry (Closed-Loop Self-Healing)...")
    t0 = time.perf_counter()
    res_recovered = asyncio.run(executor.execute_step_with_retry(step1, max_retries=3, evaluator=evaluator, monitor=monitor))
    lat_heal = (time.perf_counter() - t0) * 1000.0
    
    print(f"   -> Recovered Success: {res_recovered.success} | Latency: {lat_heal:.2f} ms")
    print(f"   -> Final Message: {res_recovered.message}")
    assert res_recovered.success, "execute_step_with_retry did not recover"
    assert "Microsoft Edge" in res_recovered.message, "Recovered step did not execute msedge"
    
    # 4. Test unknown plugin self-repair
    step_unknown = ActionStep(action="unknown", entities={"text": "what is the meaning of life?"}, original="what is the meaning of life?", description="Step 1: unknown", step_index=1)
    refined_unknown = evaluator.replan("what is the meaning of life?", step_unknown, {"error_message": "Plugin not found for action 'unknown'"})
    print(f"\n5. Unknown Plugin Re-Plan -> action={refined_unknown[0].action} | entities={refined_unknown[0].entities}")
    assert refined_unknown[0].action == "ai_chat" or refined_unknown[0].action.startswith("custom_"), f"Did not route unknown action properly, got {refined_unknown[0].action}"
    
    print("\n✅ PHASE 6.2 HERMES REFINEMENT LOOP: 100% PASSED (Autonomous Self-Healing Achieved)")
    print("="*65)

if __name__ == "__main__":
    test_hermes_refinement()
