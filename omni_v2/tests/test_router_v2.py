"""
Tests for the DGX-ready LLM Router V2 (Phase 13, #6).
Run: python -m pytest omni_v2/tests/test_router_v2.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_router_")))

from omni_v2.llm.router_v2 import LLMRouterV2, Decision


def test_capability_estimation():
    assert LLMRouterV2.estimate_required_capability("open the browser") == 1
    assert LLMRouterV2.estimate_required_capability("what is the weather") >= 2
    assert LLMRouterV2.estimate_required_capability("design the architecture for a service") == 3
    assert LLMRouterV2.estimate_required_capability("prove this theorem formally") == 4


def test_select_cheapest_capable():
    r = LLMRouterV2(available_models=["qwen2.5-1.5b", "qwen2.5-3b"])
    # trivial task -> fast tier, cheapest model (1.5b)
    dec = r.select("open the browser")
    assert dec.tier == "fast"
    assert dec.model == "qwen2.5-1.5b"
    # hard task -> deep tier
    dec2 = r.select("design the architecture for a scalable service")
    assert dec2.tier in ("deep", "reasoning", "brain")
    assert dec2.required_cap == 3


def test_select_respects_available_models():
    # only 1.5b available -> even hard tasks must use it (local fallback)
    r = LLMRouterV2(available_models=["qwen2.5-1.5b"])
    dec = r.select("prove this theorem formally")
    assert dec.model == "qwen2.5-1.5b"
    assert dec.tier in ("local", "fast", "brain")


def test_select_no_available_goes_local():
    r = LLMRouterV2(available_models=["nonexistent"])
    dec = r.select("anything")
    assert dec.tier == "local"
    assert "fallback" in dec.reason


def test_estimate_tokens():
    assert LLMRouterV2.estimate_tokens("hello world") == 2  # 11 chars //4 = 2
    assert LLMRouterV2.estimate_tokens("") == 1


def test_complete_without_resolver():
    r = LLMRouterV2(available_models=["qwen2.5-1.5b", "qwen2.5-3b"])
    dec, result = r.complete("open the browser")
    assert result is None  # no resolver
    assert dec.tier == "fast"


def test_complete_with_resolver():
    calls = []
    def resolver(tier, model):
        calls.append((tier, model))
        return f"ran {model}"
    r = LLMRouterV2(available_models=["qwen2.5-1.5b", "qwen2.5-3b"], resolver=resolver)
    dec, result = r.complete("open the browser")
    assert result == "ran qwen2.5-1.5b"
    assert calls[0] == ("fast", "qwen2.5-1.5b")


def test_dgx_uses_big_models():
    # On DGX all models available -> hard task picks a big capable one
    r = LLMRouterV2()  # all models assumed available
    dec = r.select("design the architecture for a distributed system")
    assert dec.model in ("qwen2.5-14b", "qwen2.5-72b", "deepseek-r1-70b")


def test_stats():
    r = LLMRouterV2(available_models=["qwen2.5-1.5b"])
    st = r.stats()
    assert "tiers" in st
    assert st["available_models"] == ["qwen2.5-1.5b"]
    assert st["has_resolver"] is False


def test_decision_roundtrip():
    d = Decision("fast", "qwen2.5-1.5b", 1, "cheap", 10)
    dd = d.to_dict()
    assert dd["tier"] == "fast"
    assert dd["model"] == "qwen2.5-1.5b"


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
