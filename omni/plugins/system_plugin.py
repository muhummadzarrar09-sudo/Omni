"""System Plugin - System-level commands"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class SystemPlugin(CommandPlugin):
    """System-level command plugin"""
    
    metadata = CommandMetadata(
        name="system_screenshot",
        category="system",
        description="System commands like screenshot",
        patterns=[r"(?:take\s+)?(?:a\s+)?screenshot"],
        examples=["screenshot"]
    )
    
    def __init__(self):
        super().__init__()
        self.screenshot_dir = Path.home() / ".omni" / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        try:
            import pyautogui
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = self.screenshot_dir / filename
            pyautogui.screenshot(str(filepath))
            logger.info(f"Screenshot saved: {filepath}")
            return CommandResult.ok(f"Screenshot saved", data={"path": str(filepath)})
        except ImportError:
            return CommandResult.error("pyautogui not installed")
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return CommandResult.error("Screenshot failed")
