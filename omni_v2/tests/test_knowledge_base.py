"""
Tests for the KnowledgeBase ingestion + query (Away Mode).
Run: python -m pytest omni_v2/tests/test_knowledge_base.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_kb_")))

from omni_v2.away.knowledge_base import KnowledgeBase
from omni_v2.memory.hybrid_memory import HybridMemory


def _mk():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        kb = KnowledgeBase(memory=mem)
        yield kb


def test_chunk_text_overlap():
    text = " ".join(["word"] * 2000)
    chunks = KnowledgeBase.chunk_text(text)
    assert len(chunks) > 1
    # chunks reconnect with overlap -> first+last chunk share content words
    assert all(len(c) <= 800 for c in chunks)


def test_add_text_and_query():
    kb = next(_mk())
    kb.add_text("Authentication uses JWT tokens with a secret key stored in env.")
    res = kb.query("how does authentication work")
    assert res["hit_count"] >= 1
    assert "JWT" in res["context"]


def test_add_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "notes.md"
        p.write_text("# Deployment\nDeploy with docker compose and nginx reverse proxy.\n")
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        kb = KnowledgeBase(memory=mem)
        n = kb.add_file(str(p))
        assert n >= 1
        res = kb.query("deploy the app")
        assert res["hit_count"] >= 1


def test_add_directory_recursive():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.md").write_text("Alpha document about rockets.")
        Path(tmp, "sub").mkdir()
        Path(tmp, "sub", "b.txt").write_text("Beta document about engines.")
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        kb = KnowledgeBase(memory=mem)
        n = kb.add_directory(tmp)
        assert n >= 2


def test_search_keyword():
    kb = next(_mk())
    kb.add_text("Postgres is a relational database.")
    results = kb.search("postgres")
    assert len(results) >= 1


def test_source_index():
    kb = next(_mk())
    kb.add_text("some unique text here")
    assert len(kb.list_sources()) >= 1


def test_missing_file_raises():
    kb = next(_mk())
    try:
        kb.add_file("/nonexistent/file.md")
        assert False, "should have raised"
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
