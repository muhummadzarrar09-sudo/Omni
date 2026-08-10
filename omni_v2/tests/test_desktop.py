"""
Tests for the DesktopController (headless logic behind the GUI).
Run: python -m pytest omni_v2/tests/test_desktop.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_desk_")))

from omni_v2.away.desktop import DesktopController
from omni_v2.away.knowledge_base import KnowledgeBase
from omni_v2.away.research import ResearchAgent, ResearchFinding
from omni_v2.away.reporter import Reporter
from omni_v2.away.messenger import FileMessenger
from omni_v2.memory.hybrid_memory import HybridMemory


def _stack(tmp):
    mem = HybridMemory(persist_dir=Path(tmp) / "kb")
    kb = KnowledgeBase(memory=mem)
    research = ResearchAgent(
        search_fn=lambda q: [ResearchFinding(query=q, url="https://e.com", title="t", snippet="facts about " + q)],
        knowledge_base=kb,
    )
    rep = Reporter(reports_dir=Path(tmp) / "reports")
    msg = FileMessenger(outbox=Path(tmp) / "out", inbox=Path(tmp) / "in")
    return {
        "knowledge_base": kb,
        "research_agent": research,
        "reporter": rep,
        "messenger": msg,
    }


def test_controller_status():
    with tempfile.TemporaryDirectory() as tmp:
        c = DesktopController(away_stack=_stack(tmp))
        st = c.status()
        assert "kb" in st
        assert "messenger" in st


def test_controller_kb_add_and_query():
    with tempfile.TemporaryDirectory() as tmp:
        c = DesktopController(away_stack=_stack(tmp))
        with open(Path(tmp) / "n.md", "w") as f:
            f.write("Postgres is a relational database with indexes.")
        r = c.kb_add(str(Path(tmp) / "n.md"))
        assert r["ok"] is True and r["chunks"] >= 1
        q = c.kb_query("what is postgres")
        assert q["hit_count"] >= 1


def test_controller_research():
    with tempfile.TemporaryDirectory() as tmp:
        c = DesktopController(away_stack=_stack(tmp))
        r = c.run_research("black holes")
        assert r["ok"] is True
        assert r["findings"] >= 1
        assert Path(r["path"]).exists()


def test_controller_away_queue():
    with tempfile.TemporaryDirectory() as tmp:
        # away agent not in this stack; use controller without away -> graceful
        c = DesktopController(away_stack=_stack(tmp))
        assert c.away_list() == []


def test_controller_send_message_file():
    with tempfile.TemporaryDirectory() as tmp:
        c = DesktopController(away_stack=_stack(tmp))
        res = c.send_message("hello from desktop")
        assert res["ok"] is True


def test_controller_messenger_config():
    with tempfile.TemporaryDirectory() as tmp:
        c = DesktopController(away_stack=_stack(tmp))
        cfg = c.messenger_config()
        assert "messenger" in cfg


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
