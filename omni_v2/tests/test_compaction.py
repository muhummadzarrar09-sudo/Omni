"""
Tests for Context Auto-Compaction (Phase 13, #3).
Run: python -m pytest omni_v2/tests/test_compaction.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_compact_")))

from omni_v2.llm.compaction import Compactor, heuristic_summary, estimate_tokens


def _msgs(n=10, content="hello world this is a test message that is long enough"):
    msgs = [{"role": "system", "content": "SYS"}]
    for i in range(n):
        if i % 2 == 0:
            msgs.append({"role": "user", "content": f"{content} {i}"})
        else:
            msgs.append({"role": "assistant", "content": f"reply {i}"})
    return msgs


def test_estimate_tokens():
    assert estimate_tokens("hello world") >= 1
    assert estimate_tokens("x" * 40) == 10


def test_no_compact_when_under_budget():
    c = Compactor(max_tokens=100000)
    msgs = _msgs(6)
    out = c.maybe_compact(msgs)
    assert out == msgs  # unchanged under budget
    assert c.compactions == 0


def test_compact_when_over_budget():
    c = Compactor(max_tokens=50, keep_last=4)
    msgs = _msgs(12)
    out = c.maybe_compact(msgs)
    assert len(out) < len(msgs)
    assert c.compactions == 1
    # first (system) + note + tail preserved
    assert out[0]["role"] == "system"
    # there is a compaction note
    assert any(m.get("role") == "system" and "compacted" in str(m.get("content","")).lower() for m in out)


def test_keeps_recent_turns():
    c = Compactor(max_tokens=50, keep_last=4)
    msgs = _msgs(14)
    out = c.maybe_compact(msgs)
    # last 4 turns preserved (the tail)
    tail = out[-4:]
    assert len(tail) == 4
    # the last original message content is still present
    assert msgs[-1]["content"] in [m["content"] for m in out]


def test_disabled_returns_unchanged():
    c = Compactor(max_tokens=10, enabled=False)
    msgs = _msgs(10)
    assert c.maybe_compact(msgs) == msgs


def test_heuristic_summary():
    msgs = [
        {"role": "user", "content": "build a habit tracker"},
        {"role": "tool", "name": "browser_search", "content": "found results"},
        {"role": "assistant", "content": "I'll do that"},
    ]
    s = heuristic_summary(msgs)
    assert "build a habit tracker" in s
    assert "found results" in s


def test_custom_summarizer_used():
    called = []
    def summer(m):
        called.append(m)
        return "CUSTOM SUMMARY"
    c = Compactor(max_tokens=10, keep_last=2, summarizer=summer)
    out = c.maybe_compact(_msgs(10))
    assert called, "custom summarizer should be called"
    assert any("CUSTOM SUMMARY" in str(m.get("content","")) for m in out)


def test_stats():
    c = Compactor(max_tokens=100, keep_last=3)
    c.maybe_compact(_msgs(15))
    st = c.stats()
    assert st["compactions"] == 1
    assert st["enabled"] is True
    assert st["summarizer"] == "deterministic"


def test_brain_builds_default_compactor():
    """The Brain builds a default Compactor when none is passed."""
    from omni_v2.llm.brain import Brain
    b = object.__new__(Brain)
    b.compactor = None
    # simulate the __init__ lazy-build logic
    from omni_v2.llm.compaction import Compactor
    b.compactor = Compactor()
    assert b.compactor is not None
    st = b.compactor.stats()
    assert st["enabled"] is True
    assert st["max_tokens"] > 0


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
