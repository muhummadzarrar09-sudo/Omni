"""
Tests for the Jarvis Brain episodic reflection + pattern awareness (Phase 9 Step 5).
Run: python -m pytest omni_v2/tests/test_reflect.py -q
"""
import sys
import os
import time
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_reflect_")))

from omni_v2.brain.reflect import Reflector, Episode
from omni_v2.brain.identity import IdentityCore
from omni_v2.memory.hybrid_memory import HybridMemory


class FakeSession:
    """Emulates SessionMemoryStore.recall_sessions for tests."""
    def __init__(self, sessions):
        self.sessions = sessions
    def recall_sessions(self, days=7):
        return self.sessions


def _fake_session(commands, tool_calls=None):
    return {
        "commands": commands,
        "tool_calls": tool_calls or [],
    }


def _reflector(tmp, session=None, hybrid=None, identity=None, episodes_path=None):
    return Reflector(session_memory=session, hybrid_memory=hybrid, identity=identity,
                     episodes_path=episodes_path or (Path(tmp) / "episodes.json"))


def test_reflect_today_empty():
    with tempfile.TemporaryDirectory() as tmp:
        r = _reflector(tmp, session=FakeSession([]))
        ep = r.reflect_today()
        assert ep.day == time.strftime("%Y-%m-%d")
        assert "No notable activity" in ep.summary


def test_reflect_today_summarizes_commands():
    with tempfile.TemporaryDirectory() as tmp:
        r = _reflector(tmp, session=FakeSession([_fake_session(["open browser", "open browser", "search docs"])]))
        ep = r.reflect_today()
        assert "3 command" in ep.summary
        assert "open browser" in ep.summary


def test_reflect_saves_episode_and_persists():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "episodes.json"
        r = _reflector(tmp, session=FakeSession([_fake_session(["open mail"])]), episodes_path=path)
        r.reflect_today()
        r2 = Reflector(episodes_path=path)
        assert len(r2.episodes()) == 1
        assert r2.episodes()[0].day == time.strftime("%Y-%m-%d")


def test_reflect_stores_in_hybrid_and_identity():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
        r = _reflector(tmp, session=FakeSession([_fake_session(["research quantum"])]),
                       hybrid=mem, identity=ic)
        ep = r.reflect_today()
        # hybrid episodic item stored
        assert mem.retrieve("today activity", k=5), "episodic should be retrievable"
        assert len(ic.reflections) >= 1


def test_detect_repeat_command_pattern():
    with tempfile.TemporaryDirectory() as tmp:
        r = _reflector(tmp, session=FakeSession([_fake_session(["open twitter"] * 5)]))
        pats = r.detect_patterns()
        assert any(p["kind"] == "repeat" for p in pats)


def test_detect_tool_loop():
    with tempfile.TemporaryDirectory() as tmp:
        r = _reflector(tmp, session=FakeSession([_fake_session(["x"] * 10, tool_calls=["browser_search"] * 6)]))
        pats = r.detect_patterns()
        assert any(p["kind"] == "tool_loop" for p in pats)


def test_detect_research_blend():
    with tempfile.TemporaryDirectory() as tmp:
        cmds = ["research X", "search for Y", "what is Z", "find me A", "open browser"]
        r = _reflector(tmp, session=FakeSession([_fake_session(cmds)]))
        pats = r.detect_patterns()
        assert any(p["kind"] == "blend" for p in pats)


def test_proactive_suggestions_filters():
    with tempfile.TemporaryDirectory() as tmp:
        r = _reflector(tmp, session=FakeSession([_fake_session(["open twitter"] * 5)]))
        sug = r.proactive_suggestions()
        assert all(s["severity"] >= 1 for s in sug)
        assert any(s["kind"] == "repeat" for s in sug)


def test_episode_roundtrip():
    e = Episode(ts=1, day="2026-01-01", summary="hi", activity={"commands": 2})
    e2 = Episode.from_dict(e.to_dict())
    assert e2.day == "2026-01-01"
    assert e2.activity["commands"] == 2


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        r = _reflector(tmp, session=FakeSession([_fake_session(["a"])]))
        r.reflect_today()
        st = r.stats()
        assert st["episodes"] == 1


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
