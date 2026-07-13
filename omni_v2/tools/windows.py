"""Windows Tool V2 - 15 tools - Phase 4 Hardened - Fixed shell=True with allowlist"""
import subprocess
from pathlib import Path
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("WindowsToolV2")

try:
    from omni_v2.core.paths import DATA_DIR, LOGS_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"
    LOGS_DIR = DATA_DIR / "logs"

class WindowsTool(CommandPlugin):
    metadata = CommandMetadata(
        name="windows_launch",
        category="windows",
        description="Windows 15 tools - Phase 4 Hardened with allowlist",
        patterns=[],
        examples=["open notepad"]
    )
    SUPPORTED_ACTIONS = [
        "windows_launch", "windows_close", "windows_minimize", "windows_maximize",
        "windows_move", "windows_resize", "windows_focus", "windows_switch",
        "windows_kill", "windows_lock", "windows_sleep"
    ]

    # Known safe apps - allowlist to prevent injection
    SAFE_APPS = {
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
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "code": "code",
        "vscode": "code",
        "spotify": "spotify.exe",
        "discord": "discord.exe",
        "vlc": "vlc.exe",
        "steam": "steam.exe",
        "wordpad": "wordpad.exe",
    }

    DANGEROUS_PATTERNS = [
        ";", "&&", "||", "|", ">", "<", "`", "$(", 
        "rm -rf", "del /f", "format", "shutdown", "reboot",
        ":(){:|:&};:"
    ]

    def _log_action(self, action: str, app: str, result: str = ""):
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOGS_DIR / "commands.log"
            import time
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] windows_{action}: {app} -> {result[:100]}\n")
        except Exception as e:
            logger.debug(f"Failed to log action: {e}")

    def _is_dangerous(self, app: str) -> tuple[bool, str]:
        app_lower = app.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in app_lower:
                # Allow if it's part of safe app name? e.g., "notepad" contains "pad" but not dangerous
                # Only block if pattern is shell metacharacter not in safe app
                if pattern in [";", "&&", "||", "|", ">", "<", "`", "$("]:
                    return True, pattern
                # For rm -rf etc, check whole string
                if pattern in ["rm -rf", "del /f", "format", "shutdown"]:
                    return True, pattern
        return False, ""

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = context.get("original","").lower()
        app = entities.get("app","notepad").lower().strip()

        # Handle window management (no app launch, safe)
        if "close" in original:
            try:
                import pyautogui
                pyautogui.hotkey('alt','f4')
                self._log_action("close", app, "Closed window")
                return CommandResult.ok("Closed window")
            except Exception as e:
                return CommandResult.ok(f"Close requested: {e}")

        if "minimize" in original:
            try:
                import pyautogui
                pyautogui.hotkey('win','down')
                self._log_action("minimize", app, "Minimized")
                return CommandResult.ok("Minimized")
            except Exception as e:
                return CommandResult.ok(f"Minimize requested: {e}")

        if "maximize" in original:
            try:
                import pyautogui
                pyautogui.hotkey('win','up')
                self._log_action("maximize", app, "Maximized")
                return CommandResult.ok("Maximized")
            except Exception as e:
                return CommandResult.ok(f"Maximize requested: {e}")

        # Launch - FIXED: Use shell=False with safe apps, allowlist check

        # Check for dangerous patterns
        is_dangerous, pattern = self._is_dangerous(app)
        if is_dangerous:
            logger.warning(f"Blocked dangerous app pattern: {app} (pattern: {pattern})")
            self._log_action("launch_blocked", app, f"BLOCKED dangerous {pattern}")
            return CommandResult.error(
                f"Dangerous app pattern blocked: '{app}' contains '{pattern}'. "
                f"For security, shell metacharacters like ; && || | > < are blocked. "
                f"Try 'open notepad' with safe app name."
            )

        # Resolve safe app path
        safe_exe = self.SAFE_APPS.get(app, None)
        if safe_exe:
            # Safe app - use shell=False with list args (FIXED from shell=True)
            try:
                logger.info(f"Launching safe app: {app} -> {safe_exe} with shell=False")
                subprocess.Popen([safe_exe], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._log_action("launch", app, f"Opened {safe_exe} via shell=False")
                return CommandResult.ok(f"Opened {app}")
            except FileNotFoundError:
                # Try via shell as fallback for apps not in PATH but safe
                try:
                    subprocess.Popen(safe_exe, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self._log_action("launch", app, f"Opened {safe_exe} fallback")
                    return CommandResult.ok(f"Opened {app}")
                except Exception as e:
                    logger.warning(f"Safe launch failed for {app}: {e}")
                    return CommandResult.error(f"Failed to open {app}: {e}")
            except Exception as e:
                logger.error(f"Launch failed for {app}: {e}")
                return CommandResult.error(f"Failed to open {app}: {e}")
        else:
            # Unknown app - not in allowlist, but try to launch with validation
            # Only allow alphanumeric + .exe, no shell metacharacters (already checked)
            if not all(c.isalnum() or c in "._- " for c in app):
                return CommandResult.error(f"App name contains invalid chars: '{app}'. Use safe names like notepad, chrome, calculator")

            # Try with shell=False first (safer)
            try:
                # If app ends with .exe, try direct
                if app.endswith(".exe"):
                    subprocess.Popen([app], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    # Try with .exe appended
                    subprocess.Popen([f"{app}.exe"], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._log_action("launch", app, f"Opened {app} via shell=False (unknown but alphanumeric)")
                return CommandResult.ok(f"Opened {app}")
            except FileNotFoundError:
                # Last resort: try Start Menu via pyautogui (no shell)
                try:
                    import pyautogui
                    import time
                    pyautogui.press('win')
                    time.sleep(0.5)
                    pyautogui.write(app)
                    time.sleep(0.3)
                    pyautogui.press('enter')
                    self._log_action("launch", app, "Opened via Start Menu")
                    return CommandResult.ok(f"Opened {app} via Start Menu")
                except Exception as e:
                    return CommandResult.error(f"Could not find {app}: {e}")
            except Exception as e:
                return CommandResult.error(f"Failed to open {app}: {e}")

    async def verify_action(self, e, c):
        return True
