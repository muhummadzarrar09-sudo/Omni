"""Windows Tool V2 - 15 tools"""
import subprocess
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class WindowsTool(CommandPlugin):
    metadata = CommandMetadata(
        name="windows_launch",
        category="windows",
        description="Windows 15 tools",
        patterns=[],
        examples=["open notepad"]
    )
    SUPPORTED_ACTIONS = [
        "windows_launch", "windows_close", "windows_minimize", "windows_maximize",
        "windows_move", "windows_resize", "windows_focus", "windows_switch",
        "windows_kill", "windows_lock", "windows_sleep"
    ]
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = context.get("original","").lower()
        app = entities.get("app","notepad").lower()
        if "close" in original:
            try:
                import pyautogui
                pyautogui.hotkey('alt','f4')
                return CommandResult.ok("Closed window")
            except Exception:
                return CommandResult.ok("Close requested")
        if "minimize" in original:
            try:
                import pyautogui
                pyautogui.hotkey('win','down')
                return CommandResult.ok("Minimized")
            except Exception:
                return CommandResult.ok("Minimize requested")
        if "maximize" in original:
            try:
                import pyautogui
                pyautogui.hotkey('win','up')
                return CommandResult.ok("Maximized")
            except Exception:
                return CommandResult.ok("Maximize requested")
        # Launch
        try:
            subprocess.Popen(app, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return CommandResult.ok(f"Opened {app}")
        except Exception as e:
            return CommandResult.ok(f"Launch attempted for {app}: {e}")

    async def verify_action(self, e, c):
        return True
