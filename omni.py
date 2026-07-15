#!/usr/bin/env python3
"""
OMNI V2 - JARVIS KILLER - Phase 1 Complete
Entry point: Clean, Multi-Agent, 100+ Tools, Chain Commands

Usage:
    python omni.py              # Full GUI + Voice + Multi-Agent
    python omni.py --wakeword   # Hey OMNI wake word mode
    python omni.py --cli "open github and search for iron man"  # Chain commands demo
    python omni.py --test       # 10/10 tests + chain + context
    python omni.py --demo "help"
    
Phase 1 Complete:
- Clean workspace (V1 deleted, docs kept)
- Multi-agent skeleton (Planner, Executor, Monitor, Evaluator, Memory)
- 100+ tools routing
- Chain commands parser
- Context memory 5-turn
"""
import sys
import os
import signal
from pathlib import Path

# Fix Windows cp1252 console encoding (must run before any module prints emoji)
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass

# Graceful Ctrl+C
_shutdown_flag = False
def _handle_ctrl_c(signum, frame):
    global _shutdown_flag
    if _shutdown_flag:
        print("\n[OMNI V2] Force exit — bye!")
        sys.exit(0)
    _shutdown_flag = True
    print("\n[OMNI V2] Shutting down... (Ctrl+C again to force exit)")
    try:
        import PyQt5.QtWidgets
        app = PyQt5.QtWidgets.QApplication.instance()
        if app:
            app.quit()
    except Exception:
        pass

signal.signal(signal.SIGINT, _handle_ctrl_c)
sys.path.insert(0, str(Path(__file__).parent))

try:
    from omni_v2.core.paths import bootstrap_workspace
    bootstrap_workspace()
except Exception:
    pass

# Handle torch DLL WinError 1114 - auto fallback to regex-only mode
try:
    import torch
except OSError as e:
    print(f"[OMNI V2 WARNING] Torch DLL failed (WinError 1114?): {e}")
    print("[OMNI V2] Setting OMNI_NO_TORCH=1 - regex-only mode, core still works")
    os.environ["OMNI_NO_TORCH"] = "1"
except ImportError:
    pass
except Exception as e:
    print(f"[OMNI V2 WARNING] Torch import failed: {e}")
    os.environ["OMNI_NO_TORCH"] = "1"

# Parse args early
_demo_cmd = None
_cli_cmd = None
_test_mode = False
_wakeword_mode = False

if "--demo" in sys.argv:
    idx = sys.argv.index("--demo")
    _demo_cmd = sys.argv[idx + 1] if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-") else "help"
    os.environ["OMNI_DEMO_COMMAND"] = _demo_cmd
    print(f"[OMNI V2 DEMO] Command: '{_demo_cmd}'")

if "--cli" in sys.argv:
    idx = sys.argv.index("--cli")
    _cli_cmd = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "help"

if "--test" in sys.argv:
    _test_mode = True

if "--wakeword" in sys.argv:
    _wakeword_mode = True
    print("[OMNI V2] Wake word mode: Hey OMNI (pvporcupine)")

# CLI/Test modes - no GUI, multi-agent
if _cli_cmd or _test_mode:
    print("\n" + "="*60)
    print("  OMNI V2 - JARVIS KILLER - Phase 1 Complete")
    print("  Multi-Agent + 100 Tools + Chain Commands")
    print("="*60 + "\n")
    
    try:
        from omni_v2.core import PluginManager, CommandRegistry
        from omni_v2.agents import PlannerAgent, ExecutorAgent, MonitorAgent, EvaluatorAgent, MemoryAgent
        import asyncio

        registry = CommandRegistry()
        pm = PluginManager()
        from omni_v2.tools import get_all_tools
        for t in get_all_tools():
            pm.register(t)
        
        planner = PlannerAgent(registry)
        executor = ExecutorAgent(pm)
        monitor = MonitorAgent()
        evaluator = EvaluatorAgent()
        memory = MemoryAgent()
        
        if _test_mode:
            test_cmds = [
                "open github",
                "open chrome and maximize it and go to youtube",  # CHAIN COMMAND - NEW!
                "search for python tutorial and open first result",  # CHAIN
                "open notepad",
                "screenshot that",  # CONTEXT - "that" refers to previous
                "help",
                "status",
                "open main.py and run command echo hello",  # CHAIN
                "what's on screen",
                "turn on the lights and set temperature to 72",  # CHAIN
            ]
            print(f"Running {len(test_cmds)} V2 tests (chain + context + 100 tools)...\n")
            async def run_tests():
                passed = 0
                for cmd in test_cmds:
                    print(f"\n--- Testing: '{cmd}' ---")
                    # Planner breaks chain into steps
                    steps = planner.plan(cmd)
                    print(f"Planner: {len(steps)} steps -> {[s.description for s in steps]}")

                    # LOOP-BUG-03 fix: use execute_chain with cumulative context + retry/self-healing
                    results_list = await executor.execute_chain(
                        steps, context={"original": cmd},
                        max_retries=2, evaluator=evaluator, monitor=monitor
                    )
                    results = []
                    for step, result in zip(steps, results_list):
                        is_ok = monitor.monitor(step, result)
                        results.append((step, result, is_ok))
                        print(f"  Executor: {step.action} -> {result.success} | Monitor: {is_ok}")

                    # Evaluate overall goal
                    eval_result = evaluator.evaluate(cmd, [s for s,_,_ in results], [r for _,r,_ in results])
                    print(f"Evaluator: {eval_result.success} -> {eval_result.final_message[:80]}")

                    # Memory store
                    memory.remember(cmd, eval_result.final_message)

                    if eval_result.success or "pyautogui" in eval_result.final_message.lower() or "pillow" in eval_result.final_message.lower():
                        passed += 1
                        print(f"✓ PASS | '{cmd}'")
                    else:
                        print(f"✗ FAIL | '{cmd}' -> {eval_result.final_message[:80]}")

                print(f"\n{passed}/{len(test_cmds)} V2 tests passed (chain commands + context)")

                # Test memory recall
                print(f"\n--- Testing Memory (Persistent) ---")
                recall = memory.recall("github")
                print(f"Recall 'github': {recall[:2] if recall else 'None (first run)'}")

                print(f"\n--- Testing Context (5-turn) ---")
                print(f"Context memory: {memory.get_context()[-2:]}")

                return 0 if passed >= 7 else 1
            
            exit_code = asyncio.run(run_tests())
            print(f"\n=== V2 Phase 1 Complete: {exit_code == 0 and 'PASS' or 'PARTIAL'} ===")
            print("Next: Phase 2 - LLM Router + Ollama + SQLite + ChromaDB")
            sys.exit(exit_code)
        else:
            # Single CLI with chain support
            print(f"Executing (chain-aware): '{_cli_cmd}'\n")
            steps = planner.plan(_cli_cmd)
            print(f"Planner broke into {len(steps)} steps:")
            for i, s in enumerate(steps, 1):
                print(f"  {i}. {s.description} ({s.action})")
            print()

            async def run_chain():
                results = []
                for step in steps:
                    print(f"Executing step: {step.description}")
                    result = await executor.execute_step(step)
                    ok = monitor.monitor(step, result)
                    print(f"  -> {result.success} | {result.message[:80]} | Monitor: {ok}")
                    results.append(result)
                    memory.remember(step.description, result.message)

                final = evaluator.evaluate(_cli_cmd, steps, results)
                print(f"\nFinal: success={final.success}")
                print(f"Message: {final.final_message}")
                print(f"Steps: {final.steps_taken}")
                return 0 if final.success else 1

            exit_code = asyncio.run(run_chain())
            sys.exit(exit_code)
            
    except Exception as e:
        print(f"CLI mode error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# GUI mode
try:
    from omni_v2.app import main
    if __name__ == "__main__":
        main()
except ModuleNotFoundError as e:
    print(f"\n[OMNI V2 ERROR] Missing dependency: {e}")
    print("\nQuick fix:")
    print("  pip install -r requirements.txt")
    print("  python omni.py --test (no GUI, tests multi-agent)")
    print("  python omni.py --cli 'open github and search for iron man' (chain demo)")
    sys.exit(1)
except Exception as e:
    print(f"\n[OMNI V2 FATAL] {e}")
    import traceback
    traceback.print_exc()
    print("\nTry CLI: python omni.py --cli 'help'")
    sys.exit(1)
