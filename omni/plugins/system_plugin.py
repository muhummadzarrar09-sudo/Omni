"""System Plugin - System-level commands (screenshot, copy/paste, volume)"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class SystemPlugin(CommandPlugin):
    """System-level command plugin handling screenshot, copy, paste, volume"""
    
    metadata = CommandMetadata(
        name="system_screenshot",
        category="system",
        description="System commands: screenshot, copy, paste, volume",
        patterns=[
            r"(?:take\s+)?(?:a\s+)?screenshot",
            r"copy\s+(.+)",
            r"paste",
            r"volume\s+(up|down|mute)"
        ],
        examples=["screenshot", "copy hello", "paste", "volume up"]
    )

    SUPPORTED_ACTIONS = [
        "system_screenshot",
        "system_copy",
        "system_paste",
        "system_volume",
        "performance",
        "performance_check",
    ]
    
    def __init__(self):
        super().__init__()
        self.screenshot_dir = Path.home() / ".omni" / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = (context.get("original") or "").lower()
        
        # Route based on action or keywords
        action_hint = context.get("action") if isinstance(context, dict) else ""

        if "screenshot" in original or "capture" in original or entities.get("action") == "screenshot":
            return await self._screenshot()
        
        if "copy" in original or "action" in entities and entities.get("action") == "copy" or "copy" in str(action_hint):
            text = entities.get("text", "")
            if not text:
                # try parse from original: "copy <text>"
                import re
                m = re.search(r"copy\s+(?:the\s+)?(.+)", original)
                if m:
                    text = m.group(1)
            if text:
                return await self._copy(text)
            # copy without text = Ctrl+C
            return await self._copy_hotkey()

        if "paste" in original:
            return await self._paste()

        if "volume" in original:
            vol_action = entities.get("action", "")
            if not vol_action:
                import re
                m = re.search(r"volume\s+(up|down|mute|unmute)", original)
                if m:
                    vol_action = m.group(1)
            if vol_action:
                return await self._volume(vol_action)
            return CommandResult.error("Volume command unclear. Say 'volume up', 'volume down', or 'volume mute'")

        # Fallback - if we reach here with no clear routing, try screenshot as default
        if not original:
            return CommandResult.error("System command unclear")
        return CommandResult.error(f"Unknown system command: {original}")

    async def _screenshot(self) -> CommandResult:
        try:
            import pyautogui
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = self.screenshot_dir / filename
            pyautogui.screenshot(str(filepath))
            logger.info(f"Screenshot saved: {filepath}")
            return CommandResult.ok(f"Screenshot saved to {filepath.name}", data={"path": str(filepath)})
        except ImportError:
            return CommandResult.error("pyautogui not installed - pip install pyautogui")
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return CommandResult.error(f"Screenshot failed: {e}")

    async def _copy(self, text: str) -> CommandResult:
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.info(f"Copied to clipboard: {text[:50]}")
            return CommandResult.ok(f"Copied: {text[:60]}")
        except ImportError:
            try:
                import pyautogui
                # fallback: type and ctrl+C? Actually copy given text by clipboard via windows
                # Use tkinter as fallback
                import tkinter as tk
                r = tk.Tk()
                r.withdraw()
                r.clipboard_clear()
                r.clipboard_append(text)
                r.update()
                r.destroy()
                return CommandResult.ok(f"Copied: {text[:60]}")
            except Exception as e:
                return CommandResult.error(f"Copy failed: {e}")
        except Exception as e:
            return CommandResult.error(f"Copy failed: {e}")

    async def _copy_hotkey(self) -> CommandResult:
        try:
            import pyautogui
            pyautogui.hotkey('ctrl', 'c')
            return CommandResult.ok("Copied selection")
        except Exception as e:
            return CommandResult.error(f"Copy hotkey failed: {e}")

    async def _paste(self) -> CommandResult:
        try:
            import pyautogui
            pyautogui.hotkey('ctrl', 'v')
            return CommandResult.ok("Pasted")
        except ImportError:
            return CommandResult.error("pyautogui not installed")
        except Exception as e:
            return CommandResult.error(f"Paste failed: {e}")

    async def _volume(self, action: str) -> CommandResult:
        action = action.lower()
        try:
            import pyautogui
            if action == "up":
                pyautogui.press('volumeup')
                return CommandResult.ok("Volume up")
            elif action == "down":
                pyautogui.press('volumedown')
                return CommandResult.ok("Volume down")
            elif action in ("mute", "unmute"):
                pyautogui.press('volumemute')
                return CommandResult.ok("Volume mute toggled")
            else:
                return CommandResult.error(f"Unknown volume action: {action}")
        except ImportError:
            # Fallback using nircmd or pycaw? Just report
            return CommandResult.error("pyautogui not installed for volume control")
        except Exception as e:
            return CommandResult.error(f"Volume control failed: {e}")

    async def verify_action(self, entities: Dict[str, Any], context: Dict[str, Any]) -> bool:
        # For system actions, we trust success if no exception
        return True
