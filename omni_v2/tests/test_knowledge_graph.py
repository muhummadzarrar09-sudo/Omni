"""
Tests for the Knowledge Graph (Phase 11).
Run: python -m pytest omni_v2/tests/test_knowledge_graph.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_kg_")))

from omni_v2.graph.knowledge_graph import KnowledgeGraphBuilder
from omni_v2.memory.hybrid_memory import HybridMemory


class FakeSession:
    def __init__(self, sessions):
        self.sessions = sessions
    def recall_sessions(self, days=7):
        return self.sessions


def test_build_from_memory():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        mem.remember("Authentication uses JWT with a secret. Deploy with docker and nginx.")
        mem.remember("Solar panels convert sunlight to electricity for homes.")
        g = KnowledgeGraphBuilder(memory=mem).build()
        assert g["nodes"], "should have nodes"
        assert g["edges"], "should have edges"
        assert g["stats"]["nodes"] > 0


def test_build_from_sessions():
    sessions = [{
        "commands": ["open browser and search for machine learning", "read file main.py"],
        "tool_calls": ["browser_search", "files_read", "browser_search"],
    }]
    g = KnowledgeGraphBuilder(session_memory=FakeSession(sessions)).build()
    kinds = {n["kind"] for n in g["nodes"]}
    assert "command" in kinds
    assert "tool" in kinds


def test_tools_cooccurrence():
    sessions = [{"commands": ["x"], "tool_calls": ["browser_search", "files_write", "browser_search"]}]
    g = KnowledgeGraphBuilder(session_memory=FakeSession(sessions)).build()
    tool_nodes = [n for n in g["nodes"] if n["kind"] == "tool"]
    assert len(tool_nodes) >= 2


def test_extract_files():
    text = "see C:/Users/x/main.py and ./src/utils.md"
    files = KnowledgeGraphBuilder._extract_files(text)
    assert any("main.py" in f for f in files)


def test_extract_topics():
    t = KnowledgeGraphBuilder._extract_topics("The machine learning model training and deployment")
    assert "machine" in t
    assert "the" not in t


def test_hash_and_add():
    g = KnowledgeGraphBuilder()
    nodes = {}
    nid = g._add_node(nodes, "Python", "topic")
    assert nid == "topic:python"
    g._add_node(nodes, "Python", "topic")
    assert nodes[nid]["weight"] == 2


def test_to_json():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        mem.remember("some topic about databases and indexes")
        path = Path(tmp) / "graph.json"
        js = KnowledgeGraphBuilder(memory=mem).to_json(path)
        import json
        assert json.loads(js)["nodes"]
        assert path.exists()


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        mem.remember("something to index")
        st = KnowledgeGraphBuilder(memory=mem).stats()
        assert st["nodes"] > 0


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
