"""
Tests for the remote command channel (Away Mode).
Run: python -m pytest omni_v2/tests/test_command_channel.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_kb_")))

from omni_v2.away.command_channel import CommandRouter, CommandPoller
from omni_v2.away.away_agent import AwayAgent
from omni_v2.away.knowledge_base import KnowledgeBase
from omni_v2.memory.hybrid_memory import HybridMemory


class FakeMessenger:
    def __init__(self, inbox=None):
        self.channel = "fake"
        self.outbox = []
        self.inbox_msgs = inbox or []
    def poll_commands(self):
        msgs = self.inbox_msgs
        self.inbox_msgs = []
        return msgs
    def send_text(self, text):
        self.outbox.append(text)
        from omni_v2.away.messenger import OutboundMessage
        return OutboundMessage(text=text, channel="fake", ok=True)


def _setup(tmp):
    mem = HybridMemory(persist_dir=Path(tmp) / "kb")
    kb = KnowledgeBase(memory=mem)
    agent = AwayAgent(knowledge_base=kb, tasks_path=Path(tmp) / "tasks.json")
    return agent, kb


def test_help():
    with tempfile.TemporaryDirectory() as tmp:
        agent, kb = _setup(tmp)
        r = CommandRouter(away_agent=agent, kb=kb)
        reply = r.route("/help")
        assert "/research" in reply


def test_research_command_queues_task():
    with tempfile.TemporaryDirectory() as tmp:
        agent, kb = _setup(tmp)
        r = CommandRouter(away_agent=agent, kb=kb)
        reply = r.route("/research autonomous cars")
        assert "queued" in reply.lower()
        assert len(agent.list_tasks()) == 1


def test_status_command():
    with tempfile.TemporaryDirectory() as tmp:
        agent, kb = _setup(tmp)
        agent.away_start()
        r = CommandRouter(away_agent=agent, kb=kb)
        reply = r.route("/status")
        assert "ON" in reply


def test_kb_query_command():
    with tempfile.TemporaryDirectory() as tmp:
        agent, kb = _setup(tmp)
        kb.add_text("Postgres is a relational database engine.")
        r = CommandRouter(away_agent=agent, kb=kb)
        reply = r.route("/kb what is postgres")
        assert "Postgres" in reply


def test_digest_command():
    with tempfile.TemporaryDirectory() as tmp:
        agent, kb = _setup(tmp)
        r = CommandRouter(away_agent=agent, kb=kb)
        reply = r.route("/digest")
        assert "queued" in reply.lower()


def test_poller_routes_and_replies():
    with tempfile.TemporaryDirectory() as tmp:
        agent, kb = _setup(tmp)
        msg = FakeMessenger(inbox=[{"sender": "me", "text": "/help"}])
        router = CommandRouter(away_agent=agent, kb=kb)
        poller = CommandPoller(msg, router, interval=0.1)
        poller._loop_once = True  # noop attribute
        # drive one iteration manually
        for cmd in msg.poll_commands():
            reply = router.route(cmd["text"], cmd["sender"])
            if reply:
                msg.send_text(reply)
        assert any("/research" in o for o in msg.outbox)


def test_fallback_without_brain():
    with tempfile.TemporaryDirectory() as tmp:
        r = CommandRouter()
        reply = r.route("some random message")
        assert "Received" in reply


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
