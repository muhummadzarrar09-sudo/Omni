"""
Tests for the MCP Bridge (Phase 13).
Run: python -m pytest omni_v2/tests/test_mcp.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_mcp_")))

from omni_v2.mcp.bridge import MCPBridge, FakeMCPProvider, MCPToolPlugin
from omni_v2.core.plugin_manager import PluginManager


def _bridge(tmp=None):
    pm = PluginManager()
    b = MCPBridge(plugin_manager=pm, provider=FakeMCPProvider())
    return b, pm


def test_add_fake_server_registers_tools():
    b, pm = _bridge()
    res = b.add_server(
        "echo",
        tools=[{"name": "echo", "description": "Echo text", "inputSchema": {"text": "str"}}],
        handlers={"echo": lambda a: {"content": [{"type": "text", "text": f"echo:{a.get('text')}"}]}},
    )
    assert res["registered_tools"] == 1
    assert b.uses_fake is True
    # plugin registered under namespaced name
    assert pm.get_plugin("echo_echo") is not None


async def _execute(plugin, entities):
    return await plugin.execute(entities, context={})


def _run(coro):
    import asyncio
    return asyncio.run(coro)


def test_mcp_tool_plugin_executes():
    import asyncio
    b, pm = _bridge()
    b.add_server(
        "calc",
        tools=[{"name": "add", "description": "Add two numbers"}],
        handlers={"add": lambda a: {"result": a.get("a", 0) + a.get("b", 0)}},
    )
    plugin = pm.get_plugin("calc_add")
    assert plugin is not None
    result = _run(_execute(plugin, {"a": 2, "b": 3}))
    assert result.success is True
    assert "5" in result.message


def test_mcp_tool_plugin_error():
    import asyncio
    b, pm = _bridge()
    b.add_server(
        "bad",
        tools=[{"name": "boom", "description": "fails"}],
        handlers={"boom": lambda a: (_ for _ in ()).throw(ValueError("nope"))},
    )
    plugin = pm.get_plugin("bad_boom")
    result = _run(_execute(plugin, {}))
    assert result.success is False
    assert "nope" in result.message


def test_multiple_servers_namespaced():
    b, pm = _bridge()
    b.add_server("srv1", tools=[{"name": "tool", "description": "a"}], handlers={"tool": lambda a: {"ok": 1}})
    b.add_server("srv2", tools=[{"name": "tool", "description": "b"}], handlers={"tool": lambda a: {"ok": 2}})
    assert pm.get_plugin("srv1_tool") is not None
    assert pm.get_plugin("srv2_tool") is not None


def test_list_servers():
    b, _ = _bridge()
    b.add_server("a", tools=[{"name": "t1", "description": ""}], handlers={"t1": lambda a: {}})
    b.add_server("b", tools=[{"name": "t2", "description": ""}], handlers={"t2": lambda a: {}})
    servers = b.list_servers()
    assert len(servers) == 2
    assert {s["name"] for s in servers} == {"a", "b"}


def test_remove_server():
    b, pm = _bridge()
    b.add_server("x", tools=[{"name": "t", "description": ""}], handlers={"t": lambda a: {}})
    assert b.remove_server("x") is True
    assert b.remove_server("nope") is False


def test_stats():
    b, _ = _bridge()
    b.add_server("a", tools=[{"name": "t", "description": ""}], handlers={"t": lambda a: {}})
    st = b.stats()
    assert st["servers"] == 1
    assert st["fake_provider"] is True


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
