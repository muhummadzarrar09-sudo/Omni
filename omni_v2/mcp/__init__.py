"""
OMNI MCP BRIDGE (Phase 13) — connect OMNI to the Model Context Protocol
ecosystem (6,000+ MCP servers/tools).

Lets OMNI register MCP server tools as native OMNI plugins, so the brain can
call them like any built-in tool. Fully pluggable and headless-testable: the
bridge imports the `mcp` Python SDK lazily, and a `FakeMCP` provider is used in
tests. On real hardware, `pip install mcp` then `omni mcp add <server>`.
"""
from omni_v2.mcp.bridge import (
    MCPBridge, MCPToolPlugin, get_mcp_bridge,
)

__all__ = ["MCPBridge", "MCPToolPlugin", "get_mcp_bridge"]
