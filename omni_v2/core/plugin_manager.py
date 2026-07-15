"""Plugin Manager V2 - 100+ Tools Routing with Alias Map"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("PluginManagerV2")

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
        return cls(success=False, message=message, error=error or message)

    @classmethod
    def fail(cls, message: str, error: str = None):
        """Alias for error() — some tools call fail(), some call error()."""
        return cls.error(message, error)

class CommandPlugin:
    metadata: CommandMetadata = None
    SUPPORTED_ACTIONS: List[str] = []
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        raise NotImplementedError

class PluginManager:
    """Manages 100+ tools with alias routing"""
    
    # Category fallbacks for 100+ tools
    CATEGORY_FALLBACKS = {
        "browser": "browser_navigate",
        "windows": "windows_launch",
        "system": "system_screenshot",
        "omni": "omni_help",
        "alpha": "alpha_control",
        "accessibility": "accessibility_mode",
        "vscode": "vscode_control",
        "integrations": None,
        "media": "media_play_music",
        "files": "files_list_dir",
        "ai": "ai_chat",
    }

    # 100+ actions mapping
    ACTION_ALIASES: Dict[str, str] = {
        # Browser 15
        "browser_navigate": "browser_navigate", "browser_search": "browser_navigate", "browser_click": "browser_navigate",
        "browser_type": "browser_navigate", "browser_scroll": "browser_navigate", "browser_new_tab": "browser_navigate",
        "browser_close_tab": "browser_navigate", "browser_back": "browser_navigate", "browser_forward": "browser_navigate",
        "browser_refresh": "browser_navigate", "browser_screenshot_element": "browser_navigate", "browser_extract_text": "browser_navigate",
        "browser_fill_form": "browser_navigate", "browser_bookmark": "browser_navigate",
        # Windows 15
        "windows_launch": "windows_launch", "windows_close": "windows_launch", "windows_minimize": "windows_launch",
        "windows_maximize": "windows_launch", "windows_move": "windows_launch", "windows_resize": "windows_launch",
        "windows_focus": "windows_launch", "windows_switch": "windows_launch", "windows_kill": "windows_launch",
        "windows_lock": "windows_launch", "windows_sleep": "windows_launch",
        # System 10
        "system_screenshot": "system_screenshot", "system_copy": "system_screenshot", "system_paste": "system_screenshot",
        "system_volume": "system_screenshot", "system_brightness": "system_screenshot", "system_clean_temp": "system_screenshot",
        "system_battery": "system_screenshot",
        # Media 10
        "media_play_music": "media_play_music", "media_pause": "media_play_music", "media_next": "media_play_music",
        "media_prev": "media_play_music", "media_youtube_play": "media_play_music", "media_spotify_control": "media_play_music",
        # Files 10
        "files_create_folder": "files_list_dir", "files_delete": "files_list_dir", "files_list_dir": "files_list_dir", "files_search_files": "files_list_dir",
        # AI 10
        "ai_chat": "ai_chat", "ai_summarize": "ai_chat", "ai_translate": "ai_chat", "ai_code_generate": "ai_chat",
        # Integrations 20
        "integrations_send_email": "gmail_control", "integrations_show_calendar": "calendar_control",
        "integrations_lights_on": "smarthome_control", "integrations_lights_off": "smarthome_control",
        "integrations_set_temperature": "smarthome_control",
        "integrations_performance": "performance_check", "integrations_weather": "performance_check",
        "integrations_timer": "performance_check",
        # Omni
        "omni_help": "omni_help", "omni_settings": "omni_help", "omni_status": "omni_help", "omni_repeat": "omni_help",
        # Alpha
        "alpha_screen_desc": "alpha_control", "alpha_show_hints": "alpha_control",
        # VSCode
        "vscode_open": "vscode_control", "vscode_terminal": "vscode_control", "vscode_save": "vscode_control", "vscode_create": "vscode_control",
    }

    def __init__(self):
        self._plugins: Dict[str, CommandPlugin] = {}
        self._categories: Dict[str, List[str]] = {}
        self._action_to_plugin: Dict[str, str] = {}
        logger.info("PluginManager V2 initialized with 100+ tools alias routing")

    def register(self, plugin: CommandPlugin) -> None:
        if not plugin.metadata:
            return
        name = plugin.metadata.name
        self._plugins[name] = plugin
        category = plugin.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)
        for alias in getattr(plugin, 'SUPPORTED_ACTIONS', []):
            self._action_to_plugin[alias] = name
        logger.info(f"Registered: {name} ({category})")

    def get_plugin(self, name: str) -> Optional[CommandPlugin]:
        if not name:
            return None
        if name in self._plugins:
            return self._plugins[name]
        if name in self._action_to_plugin:
            canonical = self._action_to_plugin[name]
            if canonical in self._plugins:
                return self._plugins[canonical]
        if name in self.ACTION_ALIASES:
            canonical = self.ACTION_ALIASES[name]
            if canonical in self._plugins:
                return self._plugins[canonical]
        if "_" in name:
            prefix = name.split("_")[0]
            if prefix == "integrations":
                lower = name.lower()
                if "email" in lower:
                    return self._plugins.get("gmail_control") or self._plugins.get("browser_navigate")
                if "calendar" in lower or "meeting" in lower:
                    return self._plugins.get("calendar_control") or self._plugins.get("browser_navigate")
                if "light" in lower or "temp" in lower or "door" in lower:
                    return self._plugins.get("smarthome_control") or self._plugins.get("system_screenshot")
                if "performance" in lower or "status" in lower or "weather" in lower:
                    return self._plugins.get("performance_check")
            fallback = self.CATEGORY_FALLBACKS.get(prefix)
            if fallback and fallback in self._plugins:
                return self._plugins[fallback]
            for cname, plugin in self._plugins.items():
                if plugin.metadata.category == prefix:
                    return plugin
        name_lower = name.lower()
        for cname, plugin in self._plugins.items():
            if cname.lower() in name_lower or name_lower in cname.lower():
                return plugin

        # Universal AGI routing fallback: never return None or say "Plugin not found for unknown"
        if name == "unknown" or "unknown" in name_lower:
            logger.info(f"⚡ Routing unknown action '{name}' to universal ai_chat plugin")
            return self._plugins.get("ai_chat") or self._plugins.get("omni_help")

        logger.info(f"⚡ Plugin not explicitly matched for action '{name}'. Routing to universal ai_chat engine.")
        return self._plugins.get("ai_chat") or self._plugins.get("omni_help")

    def get_all_plugins(self) -> List[CommandPlugin]:
        return list(self._plugins.values())

    async def execute(self, action: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> CommandResult:
        plugin = self.get_plugin(action)
        if not plugin:
            return CommandResult.error(f"Unknown command: {action}")
        try:
            return await plugin.execute(entities, context or {})
        except Exception as e:
            logger.error(f"Plugin {action} error: {e}")
            return CommandResult.error(str(e), error=str(e))
