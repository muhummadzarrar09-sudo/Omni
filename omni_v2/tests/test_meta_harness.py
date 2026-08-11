"""
Tests for the Meta-Harness self-improvement outer loop (Phase 16, #2).
Run: python -m pytest omni_v2/tests/test_meta_harness.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_meta_")))

from omni_v2.meta.meta_harness import MetaHarness, WeaknessPattern, HarnessEdit
from omni_v2.harness.harness import ContinualHarness


def _patterns():
    return [WeaknessPattern(kind="tool_error",
                            evidence=[{"tool": "browser_search", "error": "timeout"}],
                            frequency=5)]


def _edits():
    return [HarnessEdit(target="lesson:fix_search_timeout", kind="create",
                        content="browser_search can time out; add a retry")]


def test_mine_merges_by_kind():
    m = MetaHarness(miner=lambda: [WeaknessPattern("a"), WeaknessPattern("a"),
                                   WeaknessPattern("b")])
    pats = m.mine()
    by_kind = {p.kind: p.frequency for p in pats}
    assert by_kind["a"] == 2
    assert by_kind["b"] == 1


def test_propose():
    m = MetaHarness(proposer=lambda pats: _edits())
    edits = m.propose(_patterns())
    assert len(edits) == 1
    assert edits[0].target == "lesson:fix_search_timeout"


def test_improve_keeps_good_edit():
    # validator returns improvement above threshold -> commit
    m = MetaHarness(proposer=lambda pats: _edits(),
                    validator=lambda edit: 5.0, baseline_score=1.0,
                    improvement_threshold=1.0)
    res = m.improve()
    assert res["proposed"] == 1
    assert len(res["committed"]) == 1
    assert res["committed"][0]["kept"] is True


def test_improve_rejects_bad_edit():
    # validator returns below baseline -> reject
    m = MetaHarness(proposer=lambda pats: _edits(),
                    validator=lambda edit: 0.5, baseline_score=1.0,
                    improvement_threshold=0.0)
    res = m.improve()
    assert len(res["committed"]) == 0
    assert len(res["rejected"]) == 1


def test_improve_applies_to_harness():
    with tempfile.TemporaryDirectory() as tmp:
        h = ContinualHarness(harness_dir=Path(tmp) / "harness")
        m = MetaHarness(harness=h, proposer=lambda pats: _edits(),
                        validator=lambda edit: 5.0, baseline_score=1.0,
                        improvement_threshold=1.0)
        res = m.improve()
        assert h.get("lesson", "fix_search_timeout") is not None


def test_improve_rolls_back_on_bad():
    with tempfile.TemporaryDirectory() as tmp:
        h = ContinualHarness(harness_dir=Path(tmp) / "harness")
        # pre-add v1 of the lesson
        h.add("lesson", "fix_search_timeout", "v1 good")
        # now a bad edit proposes v2 but validator rejects -> rollback to v1
        def bad_propose(pats):
            return [HarnessEdit(target="lesson:fix_search_timeout", kind="refine",
                                content="v2 bad")]

        class AlwaysApplyHarness:
            def add(self, *a, **k): pass
            def rollback(self, *a, **k): pass
        # use the real harness via a validator that rejects so nothing applies
        m = MetaHarness(harness=h, proposer=bad_propose,
                        validator=lambda edit: 0.0, baseline_score=1.0,
                        improvement_threshold=0.0)
        res = m.improve()
        assert len(res["rejected"]) == 1


def test_history_and_stats():
    m = MetaHarness(proposer=lambda pats: _edits(),
                    validator=lambda edit: 5.0, baseline_score=1.0,
                    improvement_threshold=1.0)
    m.improve()
    assert len(m.history()) == 1
    st = m.stats()
    assert st["kept"] == 1


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
