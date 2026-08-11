"""
Tests for the Auto Skill Verification Loop (Phase 13, #2).
Run: python -m pytest omni_v2/tests/test_skill_verify.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_skverify_")))

from omni_v2.harness.verifier import SkillVerificationLoop
from omni_v2.harness.harness import ContinualHarness


def _harness(tmp):
    return ContinualHarness(harness_dir=Path(tmp) / "harness")


def test_skill_passes_is_kept():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        v = SkillVerificationLoop(harness=h, tester=lambda s: (True, "looks good"))
        art = h.add("skill", "skill_good", "procedure")
        res = v.verify_skill(art)
        assert res["passed"] is True
        assert res["action"] == "kept"
        assert h.get("skill", "skill_good") is not None


def test_skill_fails_and_rolls_back():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        v = SkillVerificationLoop(harness=h, tester=lambda s: (False, "broken"))
        # first add a v1, then v2 fails -> roll back to v1
        h.add("skill", "skill_test", "v1 good")
        v2 = h.add("skill", "skill_test", "v2 broken")
        res = v.verify_skill(v2)
        assert res["passed"] is False
        assert res["action"] == "rolled_back"
        assert h.get("skill", "skill_test").content == "v1 good"  # rolled back


def test_new_skill_fails_is_dropped():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        v = SkillVerificationLoop(harness=h, tester=lambda s: (False, "bad"))
        art = h.add("skill", "skill_new", "first attempt")
        res = v.verify_skill(art)
        assert res["action"] == "dropped"
        assert h.get("skill", "skill_new") is None  # removed


def test_auto_hook_on_add():
    """The harness's post_skill_hook auto-runs verification on every skill add."""
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        v = SkillVerificationLoop(harness=h, tester=lambda s: (True, "ok"))
        h.post_skill_hook = v.hook
        h.add("skill", "skill_auto", "procedure")
        # verifier should have a check recorded
        assert v.stats()["checks"] == 1
        assert v.stats()["passed"] == 1


def test_auto_hook_rolls_back_failed_skill():
    """A skill that fails auto-verification gets rolled back via the hook."""
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        # v1 is good (hook not yet set, or passes), v2 fails
        h.add("skill", "skill_x", "v1 good")
        v = SkillVerificationLoop(harness=h, tester=lambda s: (False, "fails"))
        h.post_skill_hook = v.hook
        h.add("skill", "skill_x", "v2 bad")
        assert v.stats()["failed"] == 1
        # v2 rolled back to v1
        assert h.get("skill", "skill_x").content == "v1 good"


def test_default_tester_conservative():
    v = SkillVerificationLoop(harness=None)
    from omni_v2.harness.harness import HarnessArtifact
    art = HarnessArtifact(kind="skill", name="s", content="c")
    res = v.verify_skill(art)
    assert res["passed"] is True  # never wrongly blocks
    assert "not-executed" in res["message"]


def test_history_and_stats():
    with tempfile.TemporaryDirectory() as tmp:
        h = _harness(tmp)
        v = SkillVerificationLoop(harness=h, tester=lambda s: (True, "ok"))
        art = h.add("skill", "skill_h", "c")
        v.verify_skill(art)
        v.verify_skill(art)
        assert len(v.history()) == 2
        st = v.stats()
        assert st["checks"] == 2
        assert st["passed"] == 2


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
