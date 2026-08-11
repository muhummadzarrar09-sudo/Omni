"""
Tests for Sub-Agent Delegation (Phase 13, #4) - RLM-style parallel sub-agents.
Run: python -m pytest omni_v2/tests/test_subagents.py -q
"""
import sys
import os
import time
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_subagent_")))

from omni_v2.agents.subagents import SubAgentDelegator, SubAgentResult
from omni_v2.brain.goals import GoalStack


def _handler(brief):
    time.sleep(0.05)
    return {"ok": True, "summary": f"done: {brief}"}


def test_spawn_single():
    d = SubAgentDelegator(handler=_handler)
    r = d.spawn("sub1", "do something")
    assert r.ok is True
    assert "do something" in r.summary


def test_spawn_many_parallel():
    d = SubAgentDelegator(handler=_handler, max_workers=3)
    specs = [{"name": "a", "brief": "task a"}, {"name": "b", "brief": "task b"}, {"name": "c", "brief": "task c"}]
    t0 = time.time()
    results = d.spawn_many(specs)
    elapsed = time.time() - t0
    assert len(results) == 3
    # ran in parallel (3 x 0.05s should be ~0.05-0.1, not 0.15)
    assert elapsed < 0.2, f"expected parallel, took {elapsed:.2f}s"
    assert all(r.ok for r in results)


def test_spawn_error_handled():
    def bad(brief):
        raise ValueError("sub-agent blew up")
    d = SubAgentDelegator(handler=bad)
    r = d.spawn("bad", "x")
    assert r.ok is False
    assert "blew up" in r.summary


def test_aggregate():
    d = SubAgentDelegator(handler=_handler)
    results = [d.spawn("a", "x"), d.spawn("b", "y")]
    agg = d.aggregate(results)
    assert agg["ok_count"] == 2
    assert agg["all_ok"] is True
    assert "sub-agents" in agg["summary"]


def test_aggregate_reports_failures():
    d = SubAgentDelegator(handler=lambda b: {"ok": False, "summary": "failed"})
    results = [d.spawn("a", "x")]
    agg = d.aggregate(results)
    assert agg["ok_count"] == 0
    assert agg["all_ok"] is False


def test_delegate_goal_completes_steps():
    with tempfile.TemporaryDirectory() as tmp:
        gs = GoalStack(goals_path=Path(tmp) / "goals.json", decomposer=lambda i: ["s1", "s2", "s3"])
        g = gs.create_goal("build a thing")
        d = SubAgentDelegator(handler=_handler)
        report = d.delegate_goal(gs.get_goal(g.id), goals_stack=gs)
        assert report["ok_count"] == 3
        assert report["all_ok"] is True
        assert gs.get_goal(g.id).status == "done"
        assert gs.get_goal(g.id).progress == 1.0


def test_delegate_goal_empty_steps():
    d = SubAgentDelegator(handler=_handler)
    report = d.delegate_goal(None)
    assert report["ok"] is False


def test_stats_and_history():
    d = SubAgentDelegator(handler=_handler)
    d.spawn("a", "x")
    d.spawn("b", "y")
    assert d.stats()["spawned"] == 2
    assert len(d.history()) == 2


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
