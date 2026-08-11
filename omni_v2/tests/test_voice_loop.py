"""
Tests for the VoiceLoop (Phase 10) - fully headless with fakes.
Run: python -m pytest omni_v2/tests/test_voice_loop.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_voice_")))

from omni_v2.voice.voice_loop import VoiceLoop
from omni_v2.brain.goals import GoalStack


class FakeWake:
    def __init__(self, trigger=False):
        self.trigger = trigger
        self.calls = 0
    def detect_wake(self):
        self.calls += 1
        return self.trigger


class FakeCapture:
    def __init__(self, audio="audio"):
        self.audio = audio
        self.calls = 0
    def record_turn(self):
        self.calls += 1
        return self.audio


class FakeSTT:
    def __init__(self, text="hello omni"):
        self.text = text
    def transcribe(self, audio):
        return self.text


class FakeBrain:
    def __init__(self):
        self.last = None
    def think(self, text):
        self.last = text
        from omni_v2.llm.brain import BrainResponse
        return BrainResponse(text=f"echo: {text}", tool_calls=[])


class FakeTTS:
    def __init__(self):
        self.spoken = []
    def speak(self, text):
        self.spoken.append(text)
        return True


def test_respond_returns_and_speaks():
    brain = FakeBrain()
    tts = FakeTTS()
    vl = VoiceLoop(stt=FakeSTT(), brain=brain, tts=tts)
    reply = vl.respond("what time is it")
    assert "what time is it" in reply
    assert tts.spoken, "should speak the reply"
    assert brain.last == "what time is it"


def test_respond_empty():
    vl = VoiceLoop(stt=FakeSTT(), brain=FakeBrain(), tts=FakeTTS())
    assert vl.respond("   ") == ""


def test_voice_goal_intent_creates_goal():
    with tempfile.TemporaryDirectory() as tmp:
        goals = GoalStack(goals_path=Path(tmp) / "goals.json")
        tts = FakeTTS()
        vl = VoiceLoop(stt=FakeSTT(), brain=FakeBrain(), tts=tts, goals=goals)
        reply = vl.respond("research solar energy and report back")
        assert "goal" in reply.lower()
        assert len(goals.list_goals()) == 1
        assert tts.spoken


def test_start_requires_components():
    vl = VoiceLoop()  # no components
    assert vl.start() is False
    assert vl.running is False


def test_full_loop_iteration():
    wake = FakeWake(trigger=True)
    cap = FakeCapture()
    brain = FakeBrain()
    tts = FakeTTS()
    vl = VoiceLoop(wake_detector=wake, audio_capture=cap, stt=FakeSTT(),
                   brain=brain, tts=tts)
    vl._iteration()
    assert brain.last == "hello omni"
    assert tts.spoken
    assert vl.stats()["turns"] >= 0


def test_wake_not_triggered_no_action():
    wake = FakeWake(trigger=False)
    brain = FakeBrain()
    vl = VoiceLoop(wake_detector=wake, audio_capture=FakeCapture(),
                   stt=FakeSTT(), brain=brain, tts=FakeTTS())
    vl._iteration()
    assert brain.last is None  # never triggered -> never thought


def test_stats():
    vl = VoiceLoop(stt=FakeSTT(), brain=FakeBrain(), tts=FakeTTS())
    st = vl.stats()
    assert st["has_brain"] is True
    assert st["has_stt"] is True


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
