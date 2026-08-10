"""
Tests for the Hybrid RAG+CAG memory (Away Mode).
Run: python -m pytest omni_v2/tests/test_hybrid_memory.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_kb_")))

from omni_v2.memory.hybrid_memory import (
    HybridMemory, sparse_embed, cosine_sim, MemoryItem,
)


def _mem(tmp):
    return HybridMemory(persist_dir=Path(tmp) / "kb")


def test_remember_and_retrieve():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mem(tmp)
        m.remember("The OMNI knowledge base uses hybrid RAG and CAG memory.")
        m.remember("Solar panels convert sunlight into electricity.", importance=0.9)
        m.remember("The cat sat on the mat.", importance=0.1)
        hits = m.retrieve("how does solar energy work", k=2)
        assert hits[0].text.startswith("Solar panels")
        assert hits[0].importance == 0.9


def test_importance_boost():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mem(tmp)
        m.remember("low importance fact about zebras", importance=0.1)
        m.remember("high importance fact about zebras stripes", importance=1.0)
        hits = m.retrieve("zebras", k=2)
        assert hits[0].importance == 1.0


def test_short_term_hot_cache():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mem(tmp)
        for i in range(5):
            m.remember(f"recent fact number {i}", hot=True)
        recent = m.recent(n=3)
        assert len(recent) == 3
        # most recent first
        assert "4" in recent[0].text


def test_cag_pinned_context():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mem(tmp)
        m.pin("user_name", "Zarrar")
        m.pin("goal", "finish the away mode")
        ctx = m.pinned_context()
        assert "Zarrar" in ctx
        assert "finish the away mode" in ctx
        m.unpin("user_name")
        assert "Zarrar" not in m.pinned_context()


def test_fused_build_context():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mem(tmp)
        m.pin("role", "local private assistant")
        m.remember("Deep learning uses neural networks with many layers.", importance=0.8)
        ctx = m.build_context("tell me about deep learning")
        assert "PINNED CONTEXT" in ctx
        assert "LONG-TERM MEMORY" in ctx
        assert "SHORT-TERM MEMORY" in ctx or "neural networks" in ctx


def test_persistence_across_reload():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mem(tmp)
        m.remember("persisted fact about the moon")
        m.pin("orbit", "moon orbits earth")
        m2 = _mem(tmp)
        assert m2.retrieve("moon")[0].text.startswith("persisted fact")
        assert "moon orbits earth" in m2.pinned_context()


def test_sparse_embed_and_cosine():
    a = sparse_embed("solar panels energy")
    b = sparse_embed("solar power energy")
    c = sparse_embed("the cat sat")
    assert cosine_sim(a, b) > cosine_sim(a, c)


def test_forget():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mem(tmp)
        it = m.remember("ephemeral note")
        assert m.forget(it.id) is True
        assert m.retrieve("ephemeral") == []


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
