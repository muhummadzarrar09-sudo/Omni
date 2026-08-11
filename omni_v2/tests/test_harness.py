"""
Tests for the Continual Harness (Phase 12) - self-refining skills/memory/lessons.
Run: python -m pytest omni_v2/tests/test_harness.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_harness_")))

from omni_v2.harness.harness import ContinualHarness, HarnessArtifact
from omni_v2.brain.goals import Goal, GoalStack


def _harness(tmp, **kw):
    return ContinualHarness(harness_dir=Path(tmp) / "harness", **kw)


def _goal(tmp, intent="build a habit tracker", status="done", history=None):
    gs = GoalStack(goals_path=Path(tmp) / "goals.json")
    g = gs.create_goal(intent, title=intent)
    g.status = status
    g.history = history or [{"ts": 1, "msg": "step done"}]
    return g


def test_add_and_get_artifact():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        a = h.add("skill", "skill_deploy", "1. build\n2. ship")
        assert h.get("skill", "skill_deploy").content == "1. build\n2. ship"
        assert a.version == 1


def test_add_increments_version_and_snapshots():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        h.add("skill", "skill_deploy", "v1 content")
        a2 = h.add("skill", "skill_deploy", "v2 content")
        assert a2.version == 2
        # snapshot preserved
        snaps = list((Path(tmp) / "harness" / "snapshots" / "skill:skill_deploy").glob("v*.json"))
        assert len(snaps) == 1


def test_rollback_restores_previous():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        h.add("skill", "skill_deploy", "v1 content")
        h.add("skill", "skill_deploy", "v2 content")
        assert h.rollback("skill", "skill_deploy") is True
        assert h.get("skill", "skill_deploy").content == "v1 content"


def test_list_filters_by_kind():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        h.add("skill", "s1", "x")
        h.add("memory", "m1", "y")
        assert len(h.list("skill")) == 1
        assert len(h.list()) == 2


def test_build_context_filters_by_topic():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        h.add("skill", "skill_deploy", "deploy with docker")
        h.add("memory", "mem_user", "user prefers python")
        ctx = h.build_context("deploy")
        assert "docker" in ctx
        assert "python" not in ctx  # unrelated filtered out


def test_refine_success_repeated_creates_skill():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        g = _goal(tmp, "build a habit tracker", status="done")
        res = h.refine_from_trajectory(g, repeated=True)
        assert res["skills"], "should create a skill on repeated success"
        assert res["memory"]
        assert res["lessons"]


def test_refine_failure_adds_lesson_and_improves_skill():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        g = _goal(tmp, "deploy the service", status="blocked")
        # first create a skill, then a failure with metacog fix improves it
        h.add("skill", "skill_deploy_the_service", "original procedure")
        verdicts = [{"suggested_fix": "use port 8080 instead", "cause": "tool_error"}]
        res = h.refine_from_trajectory(g, verdicts=verdicts, success=False)
        assert res["lessons"]
        art = h.get("skill", "skill_deploy_the_service")
        assert art is not None and "8080" in art.content


def test_harness_persists_across_reload():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "harness"
        h = ContinualHarness(harness_dir=d)
        h.add("memory", "mem_hello", "hello world")
        h2 = ContinualHarness(harness_dir=d)
        assert h2.get("memory", "mem_hello").content == "hello world"


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        h.add("skill", "s1", "x")
        h.add("memory", "m1", "y")
        st = h.stats()
        assert st["artifacts"] == 2
        assert st["by_kind"]["skill"] == 1
        assert st["has_distiller"] is False


def test_artifact_roundtrip():
    a = HarnessArtifact(kind="skill", name="s", content="c", version=3,
                        evidence=["e1"])
    a2 = HarnessArtifact.from_dict(a.to_dict())
    assert a2.version == 3
    assert a2.evidence == ["e1"]


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
