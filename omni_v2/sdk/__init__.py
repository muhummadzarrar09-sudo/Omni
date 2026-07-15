"""
OMNI V3 - Plugin SDK
Build your own OMNI skill in 50 lines.

Quick start:
  1. Copy examples/hello_skill.py
  2. Modify the execute() method
  3. Save to data/skills/custom/my_skill.py
  4. OMNI auto-loads it

The SDK provides:
  - CommandPlugin base class
  - Helper decorators
  - Context utilities
  - Common patterns

Example skill:
  ```python
  from omni_v2.sdk import skill, command, get_context

  @skill(
      name="my_skill",
      category="custom",
      description="What my skill does",
  )
  class MySkill:
      @command("greet")
      async def greet(self, entities, context):
          name = entities.get("name", "friend")
          return f"Hello, {name}!"
  ```
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


# === Re-export the main plugin primitives ===
from omni_v2.core.plugin_manager import (
    CommandPlugin,
    CommandMetadata,
    CommandResult,
    PluginManager,
)


# === Helper decorators ===

def skill(name: str, category: str = "custom", description: str = "", patterns: Optional[List[str]] = None):
    """
    Decorator to mark a class as an OMNI skill.
    Returns a class decorator that adds metadata.
    """
    def decorator(cls):
        cls.metadata = CommandMetadata(
            name=name,
            category=category,
            description=description or cls.__doc__ or name,
            patterns=patterns or [],
            examples=[],
        )
        # Make it a CommandPlugin
        if not issubclass(cls, CommandPlugin):
            # Wrap in a minimal CommandPlugin
            original_init = cls.__init__ if hasattr(cls, "__init__") else lambda self: None
            original_execute = cls.execute if hasattr(cls, "execute") else lambda self, e, c: None
            class WrappedSkill(CommandPlugin):
                def __init__(self):
                    self._instance = cls()
                async def execute(self, entities, context):
                    result = self._instance.execute(entities, context)
                    if isinstance(result, CommandResult):
                        return result
                    return CommandResult.ok(str(result))
            cls = WrappedSkill
        return cls
    return decorator


def command(name: str, description: str = ""):
    """
    Decorator to mark a method as a command within a skill.
    """
    def decorator(method):
        method._command_name = name
        method._command_description = description
        return method
    return decorator


def get_context(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get the execution context, with sensible defaults."""
    if context is None:
        return {}
    return dict(context)


# === Common utilities ===

def ok(message: str, data: Any = None) -> CommandResult:
    """Quick success result."""
    return CommandResult.ok(message, data)


def fail(message: str, error: Optional[str] = None) -> CommandResult:
    """Quick failure result."""
    return CommandResult.error(message, error)


def reply(text: str) -> CommandResult:
    """Quick conversational reply."""
    return CommandResult.ok(text)


# === Logging helper for skills ===

def log_skill_action(skill_name: str, action: str, result: str = ""):
    """Log a skill action for debugging."""
    import logging
    logger = logging.getLogger(f"Skill.{skill_name}")
    logger.info(f"{action}: {result[:200]}")


# === Example skill template ===

EXAMPLE_SKILL_CODE = '''
"""
My Custom Skill - example for OMNI V3
Save to data/skills/custom/my_skill.py
"""
from omni_v2.sdk import skill, command, ok, fail, reply


@skill(
    name="my_skill",
    category="custom",
    description="An example skill that echoes back what you say",
)
class MySkill:
    """My example skill - replace this with your logic."""

    async def execute(self, entities, context):
        # Get the original command from context
        original = context.get("original", "")
        if not original:
            return fail("No command provided")
        # Simple echo
        return reply(f"You said: {original}")

    # OR with multiple commands:
    # @command("greet")
    # async def greet(self, entities, context):
    #     name = entities.get("name", "friend")
    #     return reply(f"Hello, {name}!")
'''


__all__ = [
    "CommandPlugin",
    "CommandMetadata",
    "CommandResult",
    "PluginManager",
    "skill",
    "command",
    "get_context",
    "ok",
    "fail",
    "reply",
    "log_skill_action",
    "EXAMPLE_SKILL_CODE",
]
