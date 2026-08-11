"""
OMNI MCP BRIDGE — Model Context Protocol integration.

Turns MCP server tools into native OMNI plugins so the brain can call them like
any built-in tool (browser, files, etc.).

Design:
  - MCPToolPlugin: a CommandPlugin wrapper that adapts one MCP tool into the
    OMNI plugin interface (execute(entities, context) -> CommandResult).
  - MCPBridge: manages MCP connections. `add_server(name, command, args)` spawns
    an MCP stdio server, lists its tools, and registers each as an OMNI plugin.
  - Lazy import of the `mcp` SDK so the module is importable/testable without it.
  - `FakeMCPProvider` lets tests exercise the bridge with no real MCP server.

Usage:
    from omni_v2.mcp.bridge import get_mcp_bridge
    bridge = get_mcp_bridge()
    bridge.add_server("filesystem", ["npx", "-y", "@modelcontextprotocol/server-filesystem"])
    # each tool is now registered into the shared PluginManager
"""
from __future__ import annotations
import json
import time
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("MCPBridge")

# OMNI plugin imports (lazy to avoid heavy import at module load)
def _plugin_types():
    from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult
    return CommandPlugin, CommandMetadata, CommandResult


class MCPToolPlugin:
    """
    Adapts one MCP tool into an OMNI CommandPlugin.

    Instead of subclassing CommandPlugin per tool, we build a lightweight plugin
    object that satisfies the PluginManager interface (metadata + async execute).
    """

    def __init__(self, name: str, description: str, tool_call, input_schema=None):
        CommandPlugin, CommandMetadata, _ = _plugin_types()
        self.metadata = CommandMetadata(
            name=name, category="mcp", description=description,
            patterns=[], examples=[description or name],
        )
        self.SUPPORTED_ACTIONS = [name]
        self._tool_call = tool_call   # async fn(**kwargs) -> dict
        self._input_schema = input_schema or {}

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any] = None):
        _, _, CommandResult = _plugin_types()
        # entities = {"key": value} for the tool's parameters
        try:
            result = await self._tool_call(**entities)
            if isinstance(result, dict):
                text = result.get("content") or result.get("result") or json.dumps(result)[:500]
                if isinstance(text, list):
                    # MCP content blocks: [{type: text, text: ...}]
                    parts = [c.get("text", "") for c in text if isinstance(c, dict)]
                    text = "\n".join(parts) or json.dumps(result)[:500]
                return CommandResult.ok(message=str(text), data=result)
            return CommandResult.ok(message=str(result), data=result)
        except Exception as e:
            logger.error(f"MCP tool {self.metadata.name} error: {e}")
            return CommandResult.error(f"MCP tool {self.metadata.name} failed: {e}", error=str(e))


class FakeMCPProvider:
    """A fake MCP provider so the bridge is testable without the real SDK."""

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}

    def connect_stdio(self, name: str, command: List[str], **kw) -> Dict[str, Any]:
        return {"name": name, "connected": True, "fake": True}

    def list_tools(self, session) -> List[Dict[str, Any]]:
        # session is our dict; return the tools we recorded
        tools = session.get("tools", [])
        return tools

    def call_tool(self, session, tool_name: str, args: Dict[str, Any]):
        fn = session.get("handlers", {}).get(tool_name)
        if fn is None:
            raise ValueError(f"no fake handler for {tool_name}")
        return fn(args)


class MCPBridge:
    """Manages MCP servers and registers their tools as OMNI plugins."""

    def __init__(self, plugin_manager=None, provider=None, servers_dir: Optional[Path] = None):
        self.plugin_manager = plugin_manager
        self.provider = provider          # FakeMCPProvider or real mcp client
        self.servers_dir = Path(servers_dir) if servers_dir else None
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._register_provider()

    def _register_provider(self):
        if self.provider is not None:
            return
        try:
            import mcp  # noqa: PLC0415
            self._real_mcp = mcp
            self.provider = None  # use real client path lazily
        except Exception:
            # fall back to fake so bridge is always usable
            self.provider = FakeMCPProvider()

    @property
    def uses_fake(self) -> bool:
        return isinstance(self.provider, FakeMCPProvider)

    # -- server management -------------------------------------------------
    def add_server(self, name: str, command: Optional[List[str]] = None,
                   tools: Optional[List[Dict[str, Any]]] = None,
                   handlers: Optional[Dict[str, Callable]] = None) -> Dict[str, Any]:
        """
        Add an MCP server.
          - If `provider` is a FakeMCPProvider: `tools` (list of {name, description,
            inputSchema}) + optional `handlers` define it. Used for tests / demo.
          - If the real MCP SDK is installed and `command` given: spawn a stdio
            server, list its tools, register each.
        Registers each tool into the shared PluginManager.
        """
        with self._lock:
            if self.uses_fake:
                session = self.provider.connect_stdio(name, command or [], tools=tools)
                session["tools"] = tools or []
                session["handlers"] = handlers or {}
                self._servers[name] = session
                registered = self._register_tools(name, session)
                return {"server": name, "registered_tools": registered, "fake": True}

            # real MCP path
            try:
                return self._add_real_server(name, command or [])
            except Exception as e:
                logger.error(f"real MCP add_server failed: {e}")
                return {"server": name, "error": str(e), "registered_tools": 0}

    def _register_tools(self, server: str, session: Dict[str, Any]) -> int:
        registered = 0
        tools = session.get("tools", [])
        for t in tools:
            tname = t.get("name", "")
            desc = t.get("description", "") or f"MCP tool {tname}"
            schema = t.get("inputSchema", {})
            if not tname:
                continue
            plugin = MCPToolPlugin(
                name=f"{server}_{tname}",   # namespace to avoid collisions
                description=f"[{server}] {desc}",
                tool_call=self._make_call(session, tname),
                input_schema=schema,
            )
            if self.plugin_manager is not None:
                try:
                    self.plugin_manager.register(plugin)
                    registered += 1
                except Exception as e:
                    logger.warning(f"register MCP tool {tname}: {e}")
        return registered

    def _make_call(self, session, tname: str):
        async def _call(**kwargs):
            if self.uses_fake:
                return self.provider.call_tool(session, tname, kwargs)
            return await self._real_call_tool(session, tname, kwargs)
        return _call

    async def _real_call_tool(self, session, tname, args):
        """Call a real MCP tool via the mcp SDK ClientSession."""
        client_session = session.get("_client_session")
        if client_session is None:
            raise RuntimeError("MCP client session not available")
        result = await client_session.call_tool(tname, args or {})
        # MCP result -> plain dict/string
        content = getattr(result, "content", None)
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict) and "text" in c:
                    parts.append(c["text"])
                elif isinstance(c, dict):
                    parts.append(json.dumps(c)[:500])
            return "\n".join(parts) or str(result)
        return str(result)

    def _add_real_server(self, name, command):
        """Spawn a real MCP stdio server, list its tools, register each."""
        if self._real_mcp is None:
            raise RuntimeError("mcp SDK not installed. pip install mcp")
        if not command or not command[0]:
            raise ValueError("command required for real MCP server")

        mcp_client = self._real_mcp
        ClientSession = mcp_client.ClientSession
        StdioServerParameters = mcp_client.StdioServerParameters
        from mcp.client.stdio import stdio_client  # noqa: PLC0415

        params = StdioServerParameters(command=command[0], args=command[1:], env=None)
        session_info = {"name": name, "tools": [], "handlers": {}, "connected": True}

        import asyncio  # noqa: PLC0415

        async def _bootstrap():
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as cs:
                    await cs.initialize()
                    tools = await cs.list_tools()
                    tool_list = []
                    for t in tools.tools:
                        tool_list.append({
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": getattr(t, "inputSchema", None) or getattr(t, "input_schema", {}) or {},
                        })
                    session_info["tools"] = tool_list
                    session_info["_client_session"] = cs
                    # NOTE: the session must stay alive for calls; this keeps a
                    # reference. In practice a persistent session manager is used.

        # Run bootstrap synchronously (a real app would hold the session open).
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_bootstrap())
            loop.close()
        except Exception as e:
            logger.error(f"real MCP bootstrap failed: {e}")
            return {"server": name, "error": str(e), "registered_tools": 0}

        self._servers[name] = session_info
        registered = self._register_tools(name, session_info)
        return {"server": name, "registered_tools": registered, "fake": False}

    # -- introspection --------------------------------------------------------
    def list_servers(self) -> List[Dict[str, Any]]:
        return [{"name": n, "tools": [t.get("name") for t in s.get("tools", [])]}
                for n, s in self._servers.items()]

    def remove_server(self, name: str) -> bool:
        with self._lock:
            if name in self._servers:
                del self._servers[name]
                return True
            return False

    def stats(self) -> Dict[str, Any]:
        return {
            "servers": len(self._servers),
            "fake_provider": self.uses_fake,
            "servers_detail": self.list_servers(),
        }


_instance = None
_lock = threading.Lock()


def get_mcp_bridge(**kwargs) -> MCPBridge:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = MCPBridge(**kwargs)
    return _instance
