"""
Windows Plugin - Windows GUI automation
Uses pyautogui + subprocess (no uiauto dependency)
"""

import subprocess
import time
from typing import Dict, Any
from loguru import logger

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class WindowsPlugin(CommandPlugin):
    """Windows GUI automation plugin"""
    
    # Known apps that are unambiguously desktop applications
    KNOWN_APPS = {
        "notepad", "calculator", "explorer", "cmd", "powershell",
        "paint", "wordpad", "taskmgr", "regedit", "control",
        "magnifier", "snipping", "mspaint", "word", "excel",
        "chrome", "firefox", "edge", "teams", "zoom",
        "discord", "spotify", "vlc", "steam",
        "terminal", "taskmanager", "resources",
    }

    # Patterns that indicate a desktop app launch (not a URL)
    APP_LAUNCH_PATTERNS = [
        # Explicit launch keywords
        r"launch\s+(?:the\s+)?(?P<app>\w+)",
        # "open" + known app name (unambiguous)
        r"open\s+(?:the\s+)?(?P<app>" + "|".join(KNOWN_APPS) + r")(?:\s+\w+)?",
        # "open" + .exe file
        r"open\s+(?:the\s+)?(?P<app>\w+\.exe)",
    ]

    metadata = CommandMetadata(
        name="windows_launch",
        category="windows",
        description="Control Windows applications via voice",
        patterns=APP_LAUNCH_PATTERNS,
        examples=["open notepad", "launch calculator"]
    )
    
    APP_PATHS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
    }
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute Windows command"""
        app = entities.get("app", "").lower()
        
        if not app:
            return CommandResult.error("No app name specified")
        
        try:
            if app in self.APP_PATHS:
                path = self.APP_PATHS[app]
            else:
                path = f"{app}.exe"
            
            # Try direct launch first
            try:
                subprocess.Popen(path)
            except FileNotFoundError:
                # Fallback: use Win+R dialog
                try:
                    import pyautogui
                    subprocess.Popen("explorer.exe")  # Open start menu
                    time.sleep(0.3)
                    pyautogui.write(app)
                    pyautogui.press('enter')
                except ImportError:
                    return CommandResult.error(f"Could not find {app}")
            
            time.sleep(0.5)
            logger.info(f"Launched: {app}")
            return CommandResult.ok(f"Opened {app}")
            
        except Exception as e:
            logger.error(f"Launch error: {e}")
            return CommandResult.error(f"Failed to open {app}")