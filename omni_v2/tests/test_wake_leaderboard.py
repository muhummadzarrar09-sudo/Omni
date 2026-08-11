"""
Tests for the Wake Routine (Phase 14 #7) and Harness Leaderboard (Phase 14 #8b).
Run: python -m pytest omni_v2/tests/test_wake_leaderboard.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_wake_")))

from omni_v2.wake.wake_routine import WakeRoutine
from omni_v2.brain.identity import IdentityCore
from omni_v2.personal.calendar_contacts import CalendarParser
from omni_v2.leaderboard.leaderboard import Leaderboard


# --- Wake routine fakes ---------------------------------------------------
class FakeIdentity:
    def __init__(self, name):
        self.user = type("U", (), {"name": name})()


class FakeCalendar:
    def events_today(self):
        return [{"summary": "Team Standup", "start": "2026-08-11T10:00:00"}]


class FakeBriefing:
    def __init__(self, goals):
        self.goals = goals
    def build(self, research_topic=""):
        return {"markdown": "## Morning\n- item"}


class FakeGoals:
    def active_goals(self):
        return [{"title": "build app"}]


class FakeTTS:
    def __init__(self):
        self.spoken = []
    def speak(self, text):
        self.spoken.append(text)
        return True


class FakeMessenger:
    def __init__(self):
        self.sent = []
        self.channel = "fake"
    def send_text(self, text):
        self.sent.append(text)
        from omni_v2.away.messenger import OutboundMessage
        return OutboundMessage(text=text, channel="fake", ok=True)


class FakeGuardian:
    def __init__(self):
        self.running = False
        self.started = False
    def start(self):
        self.started = True
        self.running = True
        return True


def _wake(name="Zarrar", with_tts=True, with_guardian=True):
    ic = FakeIdentity(name)
    cal = FakeCalendar()
    b = FakeBriefing(goals=FakeGoals())
    tts = FakeTTS() if with_tts else None
    msg = FakeMessenger()
    g = FakeGuardian() if with_guardian else None
    w = WakeRoutine(identity=ic, calendar=cal, briefing=b, tts=tts,
                    messenger=msg, guardian=g)
    return w, tts, msg, g


def test_greeting_by_name():
    w, _, _, _ = _wake("Zarrar")
    greeting = w.build_greeting()
    assert "Zarrar" in greeting
    assert "Good" in greeting


def test_greeting_includes_event():
    w, _, _, _ = _wake()
    greeting = w.build_greeting()
    assert "Team Standup" in greeting


def test_run_speaks_and_pushes():
    w, tts, msg, _ = _wake()
    res = w.run(speak=True, push=True)
    assert res["spoken"] is True
    assert res["pushed"] is True
    assert tts.spoken
    assert msg.sent


def test_run_warms_guardian():
    w, _, _, g = _wake()
    w.run(speak=False, push=False)
    assert g.started is True


def test_no_name_greeting():
    w, _, _, _ = _wake("")
    greeting = w.build_greeting()
    assert "Good" in greeting
    assert "Zarrar" not in greeting


def test_status():
    w, _, _, _ = _wake()
    st = w.status()
    assert st["has_identity"] is True
    assert st["user_name"] == "Zarrar"


# --- Leaderboard -----------------------------------------------------------
def test_record_and_score():
    with tempfile.TemporaryDirectory() as tmp:
        lb = Leaderboard(path=Path(tmp) / "lb.json")
        lb.record_skill_use("skill_deploy", ok=True)
        lb.record_skill_use("skill_deploy", ok=True)
        lb.record_skill_use("skill_buggy", ok=False)
        rep = lb.report("skill")
        assert rep["total"] == 2
        # skill_deploy (2 ok) in keep; skill_buggy (fail) in refine
        keep_names = [e["name"] for e in rep["keep"]]
        refine_names = [e["name"] for e in rep["refine"]]
        assert "skill_deploy" in keep_names
        assert "skill_buggy" in refine_names


def test_automation_record():
    with tempfile.TemporaryDirectory() as tmp:
        lb = Leaderboard(path=Path(tmp) / "lb.json")
        lb.record_automation_fire("deploy_hook", ok=True)
        lb.record_automation_fire("deploy_hook", ok=True)
        rep = lb.report("automation")
        assert rep["total"] == 1
        assert rep["keep"][0]["name"] == "deploy_hook"


def test_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "lb.json"
        l1 = Leaderboard(path=p)
        l1.record_skill_use("skill_x", ok=True)
        l2 = Leaderboard(path=p)
        assert l2.entries()[0]["uses"] == 1


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        lb = Leaderboard(path=Path(tmp) / "lb.json")
        lb.record_skill_use("s", ok=True)
        assert lb.stats()["entries"] == 1


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
