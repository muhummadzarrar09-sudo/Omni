"""
Tests for the Jarvis Brain Goal Stack (Phase 9, Step 3).
Run: python -m pytest omni_v2/tests/test_goals.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_goals_")))

from omni_v2.brain.goals import GoalStack, Goal, ST_ACTIVE, ST_DONE, ST_BLOCKED, ST_ABANDONED


def _stack(tmp, decomposer=None, notifier=None):
    return GoalStack(goals_path=Path(tmp) / "goals.json",
                     decomposer=decomposer, notifier=notifier)


def test_create_goal_deterministic_plan():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp)
        g = gs.create_goal("build a habit tracker")
        assert g.steps, "should have steps"
        assert g.status in (ST_ACTIVE, "pending")
        assert g.progress == 0.0


def test_create_goal_with_custom_decomposer():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp, decomposer=lambda intent: ["step a", "step b", "step c"])
        g = gs.create_goal("anything")
        assert [s.desc for s in g.steps] == ["step a", "step b", "step c"]


def test_begin_and_complete_steps_updates_progress():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp, decomposer=lambda i: ["s1", "s2"])
        g = gs.create_goal("task")
        s1 = gs.begin_step(g.id)
        assert s1 is not None and s1.desc == "s1"
        gs.complete_step(g.id)
        assert gs.get_goal(g.id).progress == 0.5
        s2 = gs.begin_step(g.id)
        assert s2.desc == "s2"
        gs.complete_step(g.id)
        g = gs.get_goal(g.id)
        assert g.status == ST_DONE
        assert g.progress == 1.0


def test_fail_step_replans_with_fix():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp, decomposer=lambda i: ["do thing"])
        g = gs.create_goal("task")
        gs.begin_step(g.id)
        g = gs.fail_step(g.id, error="boom", suggested_fix="try again differently")
        assert g.steps[0].status == "failed"
        assert g.status == ST_BLOCKED
        assert any(s.desc == "try again differently" for s in g.steps)


def test_retry_failed():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp, decomposer=lambda i: ["do thing"])
        g = gs.create_goal("task")
        gs.begin_step(g.id)
        gs.fail_step(g.id, error="x")
        g = gs.retry_failed(g.id)
        assert g.steps[0].status == "pending"
        assert g.status == ST_ACTIVE


def test_goal_persists_across_reload():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "goals.json"
        gs = GoalStack(goals_path=path)
        g = gs.create_goal("build a habit tracker")
        gs.begin_step(g.id)
        gs.complete_step(g.id)
        gs2 = GoalStack(goals_path=path)
        g2 = gs2.get_goal(g.id)
        assert g2 is not None
        assert 0 < g2.progress < 1.0  # 1 of N steps done


def test_follow_up_notifies_on_complete():
    with tempfile.TemporaryDirectory() as tmp:
        sent = []
        gs = _stack(tmp, decomposer=lambda i: ["s1"], notifier=lambda t: sent.append(t))
        g = gs.create_goal("task")
        gs.schedule_follow_up(g.id, fu_type="report", message="Task done!")
        gs.begin_step(g.id)
        gs.complete_step(g.id)
        assert sent, "follow-up should be sent on completion"
        assert "Task done!" in sent


def test_abandon():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp, decomposer=lambda i: ["s1"])
        g = gs.create_goal("task")
        g = gs.abandon(g.id)
        assert g.status == ST_ABANDONED


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp, decomposer=lambda i: ["s1"])
        gs.create_goal("a")
        gs.create_goal("b")
        st = gs.stats()
        assert st["goals_total"] == 2


def test_next_step_respects_dependencies():
    with tempfile.TemporaryDirectory() as tmp:
        gs = _stack(tmp)
        g = gs.create_goal("task", steps=["s1", "s2", "s3"])
        # add dependency: s3 depends on s2
        g.steps[2].depends_on = [1]
        gs._save()
        first = gs.next_step(g.id)
        assert first.desc == "s1"
        gs.begin_step(g.id)
        gs.complete_step(g.id)
        second = gs.next_step(g.id)
        assert second.desc == "s2"


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
