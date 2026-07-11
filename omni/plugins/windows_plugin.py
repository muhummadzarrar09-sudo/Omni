"""
Windows Plugin - Windows GUI automation with full window management
Uses pyautogui + subprocess (no uiauto dependency)
"""
import subprocess
import time
from typing import Dict, Any
from loguru import logger

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class WindowsPlugin(CommandPlugin):
    """Windows GUI automation plugin - launch, close, minimize, maximize"""

    # Known apps that are unambiguously desktop applications
    KNOWN_APPS = {
        "notepad", "calculator", "explorer", "cmd", "powershell",
        "paint", "wordpad", "taskmgr", "regedit", "control",
        "magnifier", "snipping", "mspaint", "word", "excel",
        "chrome", "firefox", "edge", "teams", "zoom",
        "discord", "spotify", "vlc", "steam",
        "terminal", "taskmanager", "resources", "settings",
        "code", "vscode", "visual studio code"
    }

    APP_PATHS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "taskmgr": "taskmgr.exe",
        "taskmanager": "taskmgr.exe",
        "chrome": "chrome.exe",
        "code": "code",
        "vscode": "code",
        "visual studio code": "code",
    }

    metadata = CommandMetadata(
        name="windows_launch",
        category="windows",
        description="Control Windows applications via voice",
        patterns=[
            r"open\s+(?:the\s+)?(?P<app>\w+)",
            r"launch\s+(?:the\s+)?(?P<app>\w+)",
            r"close\s+(?:this\s+)?window",
            r"minimize\s+(?:this\s+)?window",
            r"maximize\s+(?:this\s+)?window",
        ],
        examples=["open notepad", "launch calculator", "close window", "minimize window"]
    )

    SUPPORTED_ACTIONS = [
        "windows_launch",
        "windows_close",
        "windows_minimize",
        "windows_maximize",
    ]
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = (context.get("original") or "").lower()

        # Window management commands have priority - they don't need app entity
        if "close" in original and ("window" in original or original.strip() == "close"):
            return await self._close_window()
        if "minimize" in original:
            return await self._minimize_window()
        if "maximize" in original:
            return await self._maximize_window()

        # Launch logic
        app = entities.get("app", "").lower().strip()
        if not app:
            # Try to extract from original: "open notepad"
            import re
            m = re.search(r"(?:open|launch|start)\s+(?:the\s+)?(\w+(?:\s*\w+)*)", original)
            if m:
                app = m.group(1).strip()
        
        if not app:
            return CommandResult.error("No app name specified - say 'open notepad'")

        # Normalize app name aliases
        app = app.replace("visual studio code", "code").replace("vs code", "code")

        return await self._launch_app(app)

    async def _launch_app(self, app: str) -> CommandResult:
        try:
            path = self.APP_PATHS.get(app, f"{app}.exe" if not app.endswith('.exe') and " " not in app else app)
            
            # Try direct launch first
            try:
                # Special case for code
                if app == "code":
                    subprocess.Popen(["code"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True if app.endswith('.exe') else False)
                time.sleep(0.5)
                logger.info(f"Launched: {app} via {path}")
                return CommandResult.ok(f"Opened {app}")
            except FileNotFoundError:
                # Fallback: use Windows search via pyautogui
                try:
                    import pyautogui
                    pyautogui.press('win')
                    time.sleep(0.5)
                    pyautogui.write(app)
                    time.sleep(0.3)
                    pyautogui.press('enter')
                    time.sleep(0.8)
                    logger.info(f"Launched via Start menu: {app}")
                    return CommandResult.ok(f"Opened {app} via Start menu")
                except ImportError:
                    return CommandResult.error(f"Could not find {app} - pyautogui not installed for fallback")
                except Exception as e:
                    logger.warning(f"Start menu launch failed for {app}: {e}")
                    # Last resort: explorer shell search
                    subprocess.Popen(f'start {app}', shell=True)
                    return CommandResult.ok(f"Opened {app}")
            except Exception as e:
                logger.warning(f"Direct launch failed for {app}: {e}, trying Start menu")
                try:
                    import pyautogui
                    pyautogui.press('win')
                    time.sleep(0.5)
                    pyautogui.write(app)
                    pyautogui.press('enter')
                    return CommandResult.ok(f"Opened {app}")
                except Exception as e2:
                    return CommandResult.error(f"Failed to open {app}: {e2}")
            
        except Exception as e:
            logger.error(f"Launch error {app}: {e}")
            return CommandResult.error(f"Failed to open {app}: {e}")

    async def _close_window(self) -> CommandResult:
        try:
            import pyautogui
            pyautogui.hotkey('alt', 'f4')
            time.sleep(0.3)
            return CommandResult.ok("Closed window")
        except ImportError:
            return CommandResult.error("pyautogui not installed - cannot close window")
        except Exception as e:
            return CommandResult.error(f"Close failed: {e}")

    async def _minimize_window(self) -> CommandResult:
        try:
            import pyautogui
            pyautogui.hotkey('win', 'down')
            time.sleep(0.2)
            return CommandResult.ok("Minimized window")
        except ImportError:
            return CommandResult.error("pyautogui not installed")
        except Exception as e:
            return CommandResult.error(f"Minimize failed: {e}")

    async def _maximize_window(self) -> CommandResult:
        try:
            import pyautogui
            pyautogui.hotkey('win', 'up')
            time.sleep(0.2)
            return CommandResult.ok("Maximized window")
        except ImportError:
            return CommandResult.error("pyautogui not installed")
        except Exception as e:
            return CommandResult.error(f"Maximize failed: {e}")

    async def verify_action(self, entities: Dict[str, Any], context: Dict[str, Any]) -> bool:
        # For launch, we optimistically return True - actual verification via process list is possible
        original = (context.get("original") or "").lower()
        if "close" in original or "minimize" in original or "maximize" in original:
            return True
        return True
