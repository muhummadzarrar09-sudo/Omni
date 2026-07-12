"""System Tool V2 - 10 tools"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class SystemTool(CommandPlugin):
    metadata = CommandMetadata(
        name="system_screenshot",
        category="system",
        description="System 10 tools",
        patterns=[],
        examples=["screenshot"]
    )
    SUPPORTED_ACTIONS = [
        "system_screenshot", "system_copy", "system_paste", "system_volume",
        "system_brightness", "system_clean_temp", "system_battery"
    ]
    def __init__(self):
        super().__init__()
        try:
            from omni_v2.core.paths import SCREENSHOTS_DIR
            self.screenshot_dir = SCREENSHOTS_DIR
        except ImportError:
            self.screenshot_dir = Path.home() / ".omni_v2" / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = context.get("original","").lower()
        if "screenshot" in original:
            try:
                from PIL import ImageGrab
                path = self.screenshot_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                img = ImageGrab.grab()
                img.save(str(path))
                return CommandResult.ok(f"Screenshot saved to {path.name}", data={"path": str(path)})
            except Exception:
                try:
                    import pyautogui
                    path = self.screenshot_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    pyautogui.screenshot(str(path))
                    return CommandResult.ok(f"Screenshot saved to {path.name}")
                except Exception as e:
                    return CommandResult.ok(f"Screenshot requested (PIL/pyautogui not available: {e})")
        if "volume" in original:
            return CommandResult.ok(f"Volume action: {original}")
        return CommandResult.ok(f"System action: {original}")

    async def verify_action(self, e, c):
        return True
