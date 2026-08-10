"""
Tests for the Away Agent task queue + runner.
Run: python -m pytest omni_v2/tests/test_away_agent.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_kb_")))

from omni_v2.away.away_agent import AwayAgent, AwayTask
from omni_v2.away.knowledge_base import KnowledgeBase
from omni_v2.memory.hybrid_memory import HybridMemory
from omni_v2.away.research import ResearchAgent, ResearchFinding


class FakeMessenger:
    def __init__(self):
        self.channel = "fake"
        self.sent = []
    def send_text(self, text):
        self.sent.append(text)
        from omni_v2.away.messenger import OutboundMessage
        return OutboundMessage(text=text, channel="fake", ok=True)
    def send_report(self, summary, path=""):
        self.sent.append(summary)
        from omni_v2.away.messenger import OutboundMessage
        return OutboundMessage(text=summary, channel="fake", ok=True)
    def poll_commands(self):
        return []


def _agent(tmp):
    mem = HybridMemory(persist_dir=Path(tmp) / "kb")
    kb = KnowledgeBase(memory=mem)
    research = ResearchAgent(
        search_fn=lambda q: [ResearchFinding(query=q, url="https://e.com", title="t", snippet="facts about " + q)],
        knowledge_base=kb,
    )
    return AwayAgent(
        knowledge_base=kb,
        research_agent=research,
        messenger=FakeMessenger(),
        tasks_path=Path(tmp) / "tasks.json",
    )


def test_submit_and_list():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        t = a.submit("research", "quantum computing")
        assert t.kind == "research"
        assert t.status == "pending"
        assert a.get_task(t.id).brief == "quantum computing"
        assert len(a.list_tasks()) == 1


def test_run_research_task():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        t = a.submit("research", "black holes")
        done = a.run_task(t.id)
        assert done.status == "done"
        assert done.result is not None
        assert "report_path" in done.result
        # findings got pushed
        assert len(a.messenger.sent) >= 1


def test_run_digest_task():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        t = a.submit("digest", "daily")
        done = a.run_task(t.id)
        assert done.status == "done"
        assert "report_path" in done.result


def test_run_notify_task():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        t = a.submit("notify", "call mom")
        done = a.run_task(t.id)
        assert done.status == "done"
        assert done.result["sent"] is True


def test_run_pending_all():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        a.submit("notify", "one")
        a.submit("notify", "two")
        done = a.run_pending()
        assert len(done) == 2


def test_invalid_kind():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        try:
            a.submit("bogus", "x")
            assert False
        except ValueError:
            pass


def test_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        a.submit("notify", "persisted task")
        a2 = AwayAgent(tasks_path=Path(tmp) / "tasks.json")
        assert any(t.brief == "persisted task" for t in a2.list_tasks())


def test_away_start_stop():
    with tempfile.TemporaryDirectory() as tmp:
        a = _agent(tmp)
        assert a.away_start()["active"] is True
        assert a.active is True
        assert a.away_stop()["active"] is False


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
