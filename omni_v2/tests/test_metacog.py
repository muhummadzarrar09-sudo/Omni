"""
Tests for the Jarvis Brain metacognition loop (Phase 9, Step 4).
Run: python -m pytest omni_v2/tests/test_metacog.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_mcog_")))

from omni_v2.brain.metacog import (
    Metacog, Verdict, CAUSE_AMBIGUOUS, CAUSE_TOOL_ERROR, CAUSE_MISSING_CONTEXT,
    ACTION_SUCCEEDED, ACTION_ASK_USER, ACTION_REPLAN_GOAL, ACTION_CHANGE_APPROACH,
    ACTION_RETRY, ACTION_GIVE_UP, ACTION_ESCALATE_DEEP,
)
from omni_v2.brain.goals import GoalStack


def _mcog(tmp, **kw):
    return Metacog(log_path=Path(tmp) / "metacog.json", **kw)


def test_success_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        v = m.decide(True, message="all good")
        assert v.succeeded is True
        assert v.action == ACTION_SUCCEEDED


def test_ambiguous_cause_asks_user():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        v = m.decide(False, message="ambiguous, which one did you mean")
        assert v.cause == CAUSE_AMBIGUOUS
        assert v.action == ACTION_ASK_USER
        assert v.ask_user is not None


def test_missing_context_asks_user():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        v = m.decide(False, message="not enough info to proceed")
        assert v.cause == CAUSE_MISSING_CONTEXT
        assert v.action == ACTION_ASK_USER


def test_tool_error_with_goal_replans():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        v = m.decide(False, message="FileNotFoundError: no such file",
                     goal_has_plan=True)
        assert v.cause == CAUSE_TOOL_ERROR
        assert v.action == ACTION_REPLAN_GOAL
        assert v.suggested_fix


def test_tool_error_no_goal_changes_approach():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        v = m.decide(False, message="FileNotFoundError: no such file",
                     goal_has_plan=False)
        assert v.action == ACTION_CHANGE_APPROACH


def test_hard_problem_escalates_deep():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        v = m.decide(False, message="this is a hard complex reasoning problem",
                     wants_deep=True)
        assert v.action == ACTION_ESCALATE_DEEP


def test_should_ask_confidence_gate():
    m = Metacog(confidence_threshold=0.6)
    assert m.should_ask(confidence=0.3) is True
    assert m.should_ask(confidence=0.9) is False
    assert m.should_ask(confidence=0.9, ambiguity=True) is True


def test_apply_replan_to_goal():
    with tempfile.TemporaryDirectory() as tmp:
        gs = GoalStack(goals_path=Path(tmp) / "goals.json", decomposer=lambda i: ["do thing"])
        g = gs.create_goal("task")
        gs.begin_step(g.id)
        m = Metacog(log_path=Path(tmp) / "mcog.json")
        v = m.decide(False, message="failed, no such file", goal_has_plan=True)
        updated = m.apply_to_goal(gs, g.id, v, do_replan=True)
        # a replan fix step should have been added
        assert updated is not None
        assert len(updated.steps) == 2
        assert updated.steps[0].status == "failed"


def test_apply_ask_user_with_hook():
    with tempfile.TemporaryDirectory() as tmp:
        gs = GoalStack(goals_path=Path(tmp) / "goals.json", decomposer=lambda i: ["do thing"])
        g = gs.create_goal("task")
        gs.begin_step(g.id)
        answers = []
        m = Metacog(log_path=Path(tmp) / "mcog.json",
                    ask_user_fn=lambda q: answers.append(q) or "use the fallback")
        v = m.decide(False, message="ambiguous, which one")
        updated = m.apply_to_goal(gs, g.id, v, do_replan=True)
        assert answers, "should have asked the user"
        assert updated is not None
        assert any("Per user" in s.suggested_fix for s in updated.steps)


def test_retry_action():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        v = m.decide(False, message="failed", wants_deep=False, goal_has_plan=False)
        # cause unknown + no plan -> change approach, not retry
        assert v.action in (ACTION_CHANGE_APPROACH, ACTION_RETRY, ACTION_ASK_USER)


def test_history_and_stats():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mcog(tmp)
        m.decide(True, message="ok")
        m.decide(False, message="ambiguous, which")
        assert len(m.history()) == 2
        st = m.stats()
        assert st["records"] == 2
        assert ACTION_SUCCEEDED in st["actions"]


def test_verdict_roundtrip():
    v = Verdict(succeeded=False, confidence=0.4, cause=CAUSE_TOOL_ERROR,
                action=ACTION_REPLAN_GOAL, message="boom", suggested_fix="fix",
                ask_user=None)
    v2 = Verdict.from_dict(v.to_dict())
    assert v2.succeeded == v.succeeded
    assert v2.cause == v.cause
    assert v2.action == v.action


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
