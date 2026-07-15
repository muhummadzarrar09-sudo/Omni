"""
OMNI V3 - Safe tool execution wrapper.
Wraps plugin.execute() to never crash, always return CommandResult.
"""
import asyncio
import logging
from typing import Any, Dict, Optional
from omni_v2.core.plugin_manager import CommandResult

logger = logging.getLogger("SafeExecute")


async def safe_execute(plugin, entities: Optional[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> CommandResult:
    """
    Safely execute a plugin. NEVER crashes. ALWAYS returns CommandResult.

    Defends against:
      - entities is None
      - context is None
      - plugin raises any exception
      - plugin returns None
      - plugin returns dict instead of CommandResult
      - plugin blocks for too long (timeout)
    """
    if plugin is None:
        return CommandResult.error("Plugin is None")

    # Defensive: coerce entities to dict
    if entities is None:
        entities = {}
    if not isinstance(entities, dict):
        try:
            entities = dict(entities) if hasattr(entities, '__iter__') else {"value": str(entities)}
        except Exception:
            entities = {}

    # Defensive: coerce context to dict
    if context is None:
        context = {}
    if not isinstance(context, dict):
        context = {}

    # Try the tool with a 30-second timeout
    try:
        result = await asyncio.wait_for(plugin.execute(entities, context), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error(f"Plugin {plugin.metadata.name if hasattr(plugin, 'metadata') else '?'} timed out after 30s")
        return CommandResult.error(f"Tool {plugin.metadata.name if hasattr(plugin, 'metadata') else '?'} timed out (30s)")
    except Exception as e:
        logger.error(f"Plugin crashed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return CommandResult.error(f"Tool error: {str(e)[:200]}")

    # Normalize: if plugin returns dict, wrap in CommandResult
    if result is None:
        return CommandResult.error("Plugin returned None")
    if isinstance(result, dict):
        if "success" in result:
            return CommandResult(
                success=bool(result["success"]),
                message=result.get("message", ""),
                data=result.get("data"),
                error=result.get("error"),
            )
        return CommandResult.ok(str(result)[:200])
    if not isinstance(result, CommandResult):
        # String or other - just convert
        return CommandResult.ok(str(result)[:500])

    return result
