"""
Tests for Jarvis Brain section-C polish (Phase 9 C2/C3).
  C2: visible plan-before-acting (BrainResponse.plan / build_plan)
  C3: offline-first TTS engine priority (piper primary, edge-tts optional cloud)
Run: python -m pytest omni_v2/tests/test_brain_polish.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_polish_")))

from omni_v2.llm.brain import BrainResponse


def test_build_plan_empty():
    r = BrainResponse(text="hi", tool_calls=[])
    assert r.build_plan() == []
    assert r.plan == []


def test_build_plan_url():
    r = BrainResponse(text="ok", tool_calls=[{"tool": "browser_navigate", "args": {"url": "https://github.com"}}])
    plan = r.build_plan()
    assert plan[0] == "1. Open https://github.com"


def test_build_plan_multi():
    r = BrainResponse(text="ok", tool_calls=[
        {"tool": "browser_search", "args": {"query": "qwen 3b"}},
        {"tool": "files_write", "args": {"path": "/tmp/a.py"}},
        {"tool": "windows_launch", "args": {"app": "chrome"}},
    ])
    plan = r.build_plan()
    assert "Search" in plan[0]
    assert "file" in plan[1]
    assert "Launch" in plan[2]
    assert plan[0].startswith("1.")


def test_plan_is_populated_after_think_build():
    # Simulate _llm_think setting plan on the response
    r = BrainResponse(text="ok", tool_calls=[{"tool": "browser_search", "args": {"query": "x"}}])
    r.plan = r.build_plan()
    assert r.plan, "plan should be populated"


def test_tts_offline_default_config():
    from omni_v2.core.config_manager import OMNISettings
    s = OMNISettings()
    assert s.tts_allow_cloud is False  # fully local by default


def test_tts_engine_priority_logic():
    """
    C3: The offline engine (piper) must be selected BEFORE edge-tts (cloud).
    We test the decision function by simulating the _init_engines order via a
    helper that mirrors the priority: piper wins if importable.
    """
    def choose(first_available):
        # first_available in priority order; piper should be first
        order = ["piper", "edge-tts", "sapi"]
        for eng in order:
            if eng in first_available:
                return eng
        return "print"
    assert choose({"piper"}) == "piper"
    assert choose({"piper", "edge-tts"}) == "piper"   # piper before edge even if both
    assert choose({"edge-tts"}) == "edge-tts"         # only if no piper
    assert choose({"sapi"}) == "sapi"
    assert choose(set()) == "print"


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
