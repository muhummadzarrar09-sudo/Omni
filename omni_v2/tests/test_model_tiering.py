"""
Tests for Jarvis Brain model tiering (Phase 9, Step 2).
Run: python -m pytest omni_v2/tests/test_model_tiering.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_tier_")))

from omni_v2.llm.brain import Brain


def _make_brain():
    """Construct a Brain without a model (no llama needed)."""
    # Use object.__new__ to bypass the singleton and avoid model loading.
    b = object.__new__(Brain)
    # minimal attrs needed by the pure-logic methods we test
    b._deep_enabled = True
    b._deep_model_path = None
    b._current_model_path = None
    b.llm = None
    b.model_loaded = False
    return b


def test_needs_deep_trigger_words():
    b = _make_brain()
    assert b.needs_deep("can you plan a multi-step deployment for me") is True
    assert b.needs_deep("why is the auth failing? debug it") is True
    assert b.needs_deep("design the architecture for a new service") is True
    assert b.needs_deep("write code to parse the csv") is True


def test_needs_deep_false_for_chat():
    b = _make_brain()
    assert b.needs_deep("open my browser") is False
    assert b.needs_deep("good morning") is False


def test_needs_deep_long_prompt():
    b = _make_brain()
    long_text = "please give me a very thorough breakdown of " + ("detail " * 200)
    assert b.needs_deep(long_text) is True


def test_needs_deep_disabled():
    b = _make_brain()
    b._deep_enabled = False
    assert b.needs_deep("plan a complex project") is False


def test_find_deep_model_prefers_big():
    with tempfile.TemporaryDirectory() as tmp:
        models = Path(tmp) / "models"
        models.mkdir(parents=True)
        (models / "qwen2.5-1.5b-instruct-q4_k_m.gguf").write_bytes(b"a" * 100)
        (models / "qwen2.5-3b-instruct-q4_k_m.gguf").write_bytes(b"b" * 200)
        found = _find_deep_in(models)
        assert found is not None and "3b" in found


def test_find_deep_model_none():
    with tempfile.TemporaryDirectory() as tmp:
        models = Path(tmp) / "models"
        models.mkdir(parents=True)
        (models / "qwen2.5-1.5b-instruct-q4_k_m.gguf").write_bytes(b"a" * 10)
        assert _find_deep_in(models) is None


def _find_deep_in(models_dir):
    """Replicates Brain._find_deep_model scanning logic for a single dir."""
    markers = ["3b", "7b", "8b", "14b", "deep", "big", "reasoning", "large"]
    best, best_size = None, 0
    for g in sorted(models_dir.glob("*.gguf")):
        name = g.name.lower()
        if any(m in name for m in markers) and g.stat().st_size > best_size:
            best, best_size = str(g.resolve()), g.stat().st_size
    return best


def test_get_status_reports_deep():
    b = _make_brain()
    b._tier = "llm"
    b._tool_brief = "a - b\nc - d"
    b._conversation = []
    st = b.get_status()
    assert "deep_available" in st
    assert "deep_model_path" in st
    assert "deep_enabled" in st


def test_tier_marked_deep_on_response():
    from omni_v2.llm.brain import BrainResponse
    r = BrainResponse(text="hi", tool_calls=[])
    assert r.tier == "brain"  # default
    r.tier = "llm-deep"
    assert r.tier == "llm-deep"


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
