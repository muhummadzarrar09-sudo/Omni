"""
Tests for the QueryEngine agentic runtime (Phase 16, #1).
Run: python -m pytest omni_v2/tests/test_query_engine.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_engine_")))

from omni_v2.engine.query_engine import QueryEngine, Tool


class FakeBrain:
    """Returns a response with a single tool call, then text."""
    def __init__(self, tool, args):
        self._tool = tool
        self._args = args
        self._count = 0
    def think(self, messages, stream=False):
        class R:  # BrainResponse-like
            text = "done"
            tool_calls = []
        r = R()
        if self._count == 0:
            r.tool_calls = [{"tool": self._tool, "args": self._args}]
            self._count += 1
        return r


def _tool(name="echo", run=None, permission="allow"):
    return Tool(name=name, run=run or (lambda **kw: "echoed"), permission=permission)


def test_run_calls_tool():
    called = []
    def echo(**kw):
        called.append(kw)
        return "ok"
    brain = FakeBrain("echo", {"text": "hi"})
    eng = QueryEngine(brain=brain, tools=[_tool("echo", run=echo)])
    res = eng.run("say hi")
    assert res.tool_calls == 1
    assert called == [{"text": "hi"}]
    assert res.tool_errors == 0


def test_permission_denied():
    brain = FakeBrain("secret", {})
    eng = QueryEngine(brain=brain, tools=[_tool("secret", permission="deny")])
    res = eng.run("do secret")
    assert res.tool_calls == 0
    assert res.tool_errors == 1
    assert any(e["type"] == "denied" for e in res.events)


def test_unknown_tool_error():
    brain = FakeBrain("nope", {})
    eng = QueryEngine(brain=brain, tools=[_tool("echo")])
    res = eng.run("x")
    assert res.tool_errors == 1
    assert any(e["type"] == "tool_error" for e in res.events)


def test_approve_hook_gate():
    brain = FakeBrain("api", {})
    eng = QueryEngine(brain=brain, tools=[_tool("api", permission="ask")],
                      approve=lambda tool, args: True)
    res = eng.run("call api")
    assert res.tool_calls == 1


def test_pre_hook_blocks():
    brain = FakeBrain("write", {})
    eng = QueryEngine(brain=brain, tools=[_tool("write")],
                      pre_hook=lambda tool, args: None)  # returns None -> blocked
    res = eng.run("write")
    assert res.tool_calls == 0
    assert any("BLOCKED" in e.get("result", "") for e in res.events)


def test_post_hook_transforms():
    def echo(**kw):
        return "raw"
    brain = FakeBrain("echo", {})
    eng = QueryEngine(brain=brain, tools=[_tool("echo", run=echo)],
                      post_hook=lambda tool, args, result: result.upper())
    res = eng.run("x")
    # result transformed to RAW
    assert any(e["type"] == "tool_call" and "RAW" in e.get("result", "") for e in res.events)


def test_cost_meter():
    brain = FakeBrain("echo", {})
    eng = QueryEngine(brain=brain, tools=[_tool("echo", run=lambda **k: "r", )])
    eng.tools["echo"].cost = 2.5
    eng.run("x")
    assert eng.stats()["total_cost"] == 2.5


def test_no_brain():
    eng = QueryEngine(brain=None, tools=[_tool("echo")])
    res = eng.run("x")
    assert res.ok is False


def test_register_tool():
    eng = QueryEngine(brain=FakeBrain("a", {}))
    eng.register(_tool("a"))
    assert "a" in eng.tools


def test_stats():
    brain = FakeBrain("echo", {})
    eng = QueryEngine(brain=brain, tools=[_tool("echo")])
    eng.run("x")
    st = eng.stats()
    assert st["tools"] == 1
    assert st["total_tokens"] > 0


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
