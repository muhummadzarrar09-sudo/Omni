"""Windows Plugin - Windows GUI automation"""
import subprocess
import time
from typing import Dict, Any
from loguru import logger
from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class WindowsPlugin(CommandPlugin):
    """Windows GUI automation plugin"""
    
    metadata = CommandMetadata(
        name="windows_launch",
        category="windows",
        description="Control Windows applications via voice",
        patterns=[r"open\s+(?:the\s+)?(?P<app>\w+)", r"launch\s+(?:the\s+)?(?P<app>\w+)"],
        examples=["open notepad", "launch calculator"]
    )
    
    APP_PATHS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
    }
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        app = entities.get("app", "").lower()
        if not app:
            return CommandResult.error("No app name specified")
        
        try:
            path = self.APP_PATHS.get(app, f"{app}.exe")
            subprocess.Popen(path)
            time.sleep(0.5)
            logger.info(f"Launched: {app}")
            return CommandResult.ok(f"Opened {app}")
        except FileNotFoundError:
            return CommandResult.error(f"Could not find {app}")
        except Exception as e:
            logger.error(f"Launch error: {e}")
            return CommandResult.error(f"Failed to open {app}")
