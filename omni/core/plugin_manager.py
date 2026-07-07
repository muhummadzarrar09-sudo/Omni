"""Plugin Manager - Extensible Command System"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger

@dataclass
class CommandMetadata:
    name: str
    category: str
    description: str
    patterns: List[str]
    examples: List[str] = None

@dataclass
class CommandResult:
    success: bool
    message: str
    data: Any = None
    error: Optional[str] = None
    
    @classmethod
    def ok(cls, message: str, data: Any = None):
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error(cls, message: str, error: str = None):
        return cls(success=False, message=message, error=error)

class CommandPlugin:
    """Base class for command plugins"""
    metadata: CommandMetadata = None
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        raise NotImplementedError

class PluginManager:
    """Manages command plugins with dynamic loading."""
    def __init__(self):
        self._plugins: Dict[str, CommandPlugin] = {}
        self._categories: Dict[str, List[str]] = {}
        logger.info("PluginManager initialized")
    
    def register(self, plugin: CommandPlugin) -> None:
        if not plugin.metadata:
            return
        name = plugin.metadata.name
        self._plugins[name] = plugin
        category = plugin.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)
        logger.info(f"Registered: {name}")
    
    def get_plugin(self, name: str) -> Optional[CommandPlugin]:
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> List[CommandPlugin]:
        return list(self._plugins.values())
    
    async def execute(self, action: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> CommandResult:
        plugin = self.get_plugin(action)
        if not plugin:
            return CommandResult.error(f"Unknown command: {action}")
        try:
            return await plugin.execute(entities, context or {})
        except Exception as e:
            logger.error(f"Plugin error: {e}")
            return CommandResult.error(str(e))
    
    def get_help_text(self) -> str:
        lines = ["Available Commands:", ""]
        for category in self._categories:
            lines.append(f"--- {category.upper()} ---")
            for name in self._categories[category]:
                p = self._plugins.get(name)
                if p and p.metadata:
                    lines.append(f"  {p.metadata.name}: {p.metadata.description}")
        return "\n".join(lines)
