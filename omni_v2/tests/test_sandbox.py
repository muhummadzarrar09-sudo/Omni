"""
Tests for the Skill Sandbox (Phase 14, #3) - run skills in an isolated subprocess.
Run: python -m pytest omni_v2/tests/test_sandbox.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_sandbox_")))

from omni_v2.skills.sandbox import SkillSandbox
from omni_v2.harness.verifier import SkillVerificationLoop
from omni_v2.harness.harness import HarnessArtifact


def test_runs_safe_code():
    s = SkillSandbox(timeout=10)
    res = s.run_skill_code("x = 1 + 1\nprint('result:', x)")
    assert res.ok is True
    assert "result: 2" in res.output


def test_catches_exception():
    s = SkillSandbox(timeout=10)
    res = s.run_skill_code("raise ValueError('boom')")
    assert res.ok is False
    assert "boom" in res.error


def test_blocks_infinite_loop_timeout():
    s = SkillSandbox(timeout=1)
    res = s.run_skill_code("while True:\n    pass")
    assert res.timed_out is True
    assert res.ok is False


def test_blocks_network():
    s = SkillSandbox(timeout=10)
    # network module import should be blocked by monkeypatch
    res = s.run_skill_code("import socket\ns = socket.socket()")
    # socket.socket was replaced -> raises OSError -> not ok
    assert res.ok is False
    assert "network blocked" in res.error


def test_blocks_memory_hog():
    s = SkillSandbox(timeout=10, max_mem_mb=32)
    # allocating huge memory should be killed by RLIMIT_AS or timeout
    res = s.run_skill_code("x = bytearray(1024 * 1024 * 512)")  # 512MB > 32MB limit
    # may be ok=False (memory error) or timed out; either is a blocked outcome
    assert res.ok is False


def test_empty_code():
    s = SkillSandbox(timeout=5)
    res = s.run_skill_code("   ")
    assert res.ok is False


def test_run_skill_artifact_procedural():
    s = SkillSandbox(timeout=10)
    art = HarnessArtifact(kind="skill", name="skill_deploy",
                          content="## Procedure\n1. build\n2. ship")
    res = s.run_skill_artifact(art)
    assert res.ok is True  # procedural (no code) verified


def test_run_skill_artifact_code():
    s = SkillSandbox(timeout=10)
    art = HarnessArtifact(kind="skill", name="skill_calc",
                          content="def run():\n    return 42\nprint('ok')")
    res = s.run_skill_artifact(art)
    assert res.ok is True
    assert "ok" in res.output


def test_sandbox_tester_passes_good_skill():
    tester = SkillVerificationLoop.sandbox_tester()
    art = HarnessArtifact(kind="skill", name="skill_ok", content="print('fine')")
    passed, msg = tester(art)
    assert passed is True
    assert "fine" in msg


def test_sandbox_tester_fails_bad_skill():
    tester = SkillVerificationLoop.sandbox_tester()
    art = HarnessArtifact(kind="skill", name="skill_bad",
                          content="import os\nos.remove('/etc/hostname')")
    passed, msg = tester(art)
    # may fail on sandbox exec (missing file) or network - either way not cleanly passed
    assert passed is False


def test_stats():
    s = SkillSandbox(timeout=5, max_mem_mb=128)
    st = s.stats()
    assert st["timeout_s"] == 5
    assert st["network_blocked"] is True
    assert st["isolated"] is True


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
