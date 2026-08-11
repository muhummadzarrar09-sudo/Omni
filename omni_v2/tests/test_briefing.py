"""
Tests for the Morning Briefing agent (Phase 11).
Run: python -m pytest omni_v2/tests/test_briefing.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_brief_")))

from omni_v2.briefing.briefing import MorningBriefing
from omni_v2.brain.goals import GoalStack
from omni_v2.brain.identity import IdentityCore


class FakeReflector:
    def __init__(self, summary="Worked on the auth refactor."):
        self.summary = summary
    def episodes(self, n=3):
        from omni_v2.brain.reflect import Episode
        return [Episode(ts=1, day="2026-01-01", summary=self.summary, activity={})]


class FakeResearch:
    def __init__(self):
        self.last = None
    def research(self, topic):
        self.last = topic
        from omni_v2.away.research import ResearchReport, ResearchFinding
        r = ResearchReport(topic=topic)
        r.findings.append(ResearchFinding(query=topic, url="https://e.com/a", title="First result", snippet="Facts about topic."))
        r.status = "done"
        return r


class FakeReporter:
    def __init__(self, tmp):
        self.reports_dir = Path(tmp) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    def save_report(self, title, markdown):
        from omni_v2.away.reporter import Report
        path = self.reports_dir / "briefing.md"
        path.write_text(markdown, encoding="utf-8")
        return Report(title=title, markdown=markdown, summary="", path=path)


class FakeMessenger:
    def __init__(self):
        self.sent = []
        self.channel = "fake"
    def send_text(self, text):
        self.sent.append(text)
        from omni_v2.away.messenger import OutboundMessage
        return OutboundMessage(text=text, channel="fake", ok=True)


def _setup(tmp):
    goals = GoalStack(goals_path=Path(tmp) / "goals.json")
    goals.create_goal("build a habit tracker", title="build a habit tracker")
    ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
    ic.update_user(name="Zarrar")
    reporter = FakeReporter(tmp)
    messenger = FakeMessenger()
    b = MorningBriefing(goals=goals, reflector=FakeReflector(), research=FakeResearch(),
                        reporter=reporter, messenger=messenger, identity=ic)
    return b, goals, messenger


def test_build_greets_by_name():
    with tempfile.TemporaryDirectory() as tmp:
        b, _, _ = _setup(tmp)
        data = b.build()
        assert "Zarrar" in data["greeting"]
        assert data["user_name"] == "Zarrar"


def test_build_includes_goals():
    with tempfile.TemporaryDirectory() as tmp:
        b, goals, _ = _setup(tmp)
        data = b.build()
        assert len(data["goals"]) == 1
        assert "habit tracker" in data["goals"][0]["title"]


def test_build_includes_recap():
    with tempfile.TemporaryDirectory() as tmp:
        b, _, _ = _setup(tmp)
        data = b.build()
        assert data["recap"]
        assert "auth refactor" in data["recap"]


def test_build_with_research():
    with tempfile.TemporaryDirectory() as tmp:
        b, _, _ = _setup(tmp)
        data = b.build(research_topic="quantum computing")
        assert data["findings"]
        assert "Research" in data["markdown"]


def test_deliver_saves_and_pushes():
    with tempfile.TemporaryDirectory() as tmp:
        b, _, messenger = _setup(tmp)
        res = b.deliver(research_topic="solar energy", save_report=True, push=True)
        assert res["saved_path"]
        assert res["pushed"] is True
        assert messenger.sent, "should have pushed"


def test_markdown_structure():
    with tempfile.TemporaryDirectory() as tmp:
        b, _, _ = _setup(tmp)
        md = b.build().get("markdown", "")
        assert md.startswith("#")
        assert "Good morning" in md


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
