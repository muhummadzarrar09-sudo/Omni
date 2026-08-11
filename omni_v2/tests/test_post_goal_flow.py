"""
Tests for the auto post-goal flow (Phase 12.1): goal completion auto-refines
into the Continual Harness.
Run: python -m pytest omni_v2/tests/test_post_goal_flow.py -q
"""
import sys
import os
from pathlib import Path
import tempfile
import time

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_postgoal_")))

from omni_v2.brain.goals import GoalStack
from omni_v2.harness.harness import ContinualHarness


def test_complete_goal_auto_refines():
    """Completing a goal fires the post_goal_hook which distills into the harness."""
    with tempfile.TemporaryDirectory() as tmp:
        harness = ContinualHarness(harness_dir=Path(tmp) / "harness")
        hook_calls = []

        def hook(goal, success):
            hook_calls.append((goal.id, success))
            # simulate what build_away_stack does
            harness.refine_from_trajectory(goal, success=success, repeated=True)

        gs = GoalStack(goals_path=Path(tmp) / "goals.json",
                       decomposer=lambda i: ["s1", "s2"],
                       post_goal_hook=hook)
        g = gs.create_goal("build a habit tracker")
        # complete all steps
        for _ in range(5):
            s = gs.begin_step(g.id)
            if s is None:
                break
            gs.complete_step(g.id)
        # give the background thread a moment
        time.sleep(0.3)
        assert hook_calls, "post_goal_hook should have fired"
        assert hook_calls[0][1] is True  # success=True
        # harness should have distilled something
        assert harness.list("skill") or harness.list("memory") or harness.list("lesson")


def test_fail_goal_auto_refines_failure():
    """A failed goal fires the hook with success=False and distills a lesson."""
    with tempfile.TemporaryDirectory() as tmp:
        harness = ContinualHarness(harness_dir=Path(tmp) / "harness")
        hook_calls = []

        def hook(goal, success):
            hook_calls.append((goal.id, success))
            harness.refine_from_trajectory(goal, success=success)

        gs = GoalStack(goals_path=Path(tmp) / "goals.json",
                       decomposer=lambda i: ["do thing"],
                       post_goal_hook=hook)
        g = gs.create_goal("deploy the service")
        gs.begin_step(g.id)
        gs.fail_step(g.id, error="port in use")
        time.sleep(0.3)
        assert hook_calls
        assert hook_calls[0][1] is False  # success=False
        assert harness.list("lesson"), "a failure should produce a lesson"


def test_no_hook_no_crash():
    """GoalStack without a post_goal_hook still works fine."""
    with tempfile.TemporaryDirectory() as tmp:
        gs = GoalStack(goals_path=Path(tmp) / "goals.json", decomposer=lambda i: ["s1"])
        g = gs.create_goal("something")
        gs.begin_step(g.id)
        gs.complete_step(g.id)
        assert gs.get_goal(g.id).status == "done"


def test_build_away_stack_wires_auto_refine():
    """build_away_stack wires the post_goal_hook to auto-refine into the harness."""
    from omni_v2.away.context import build_away_stack
    with tempfile.TemporaryDirectory() as tmp:
        stack = build_away_stack()
        gs = stack["goals"]
        harness = stack["harness"]
        assert gs.post_goal_hook is not None, "auto-refine hook should be wired"
        g = gs.create_goal("research a topic and summarize it")
        for _ in range(8):
            s = gs.begin_step(g.id)
            if s is None:
                break
            gs.complete_step(g.id)
        time.sleep(0.5)
        # harness should have refined at least memory/lesson for the completed goal
        assert harness.stats()["artifacts"] >= 1


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
