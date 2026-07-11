"""VSCode Plugin - Code editing via voice"""
import subprocess
import time
from pathlib import Path
from typing import Dict, Any
from loguru import logger

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class VSCodePlugin(CommandPlugin):
    """VSCode automation - open files, run terminal commands, save, create"""

    metadata = CommandMetadata(
        name="vscode_control",
        category="vscode",
        description="Control VS Code via voice (open files, terminal, save)",
        patterns=[],
        examples=["open main.py", "run command echo hello", "save file", "create file utils.py"]
    )

    SUPPORTED_ACTIONS = [
        "vscode_open",
        "vscode_terminal",
        "vscode_save",
        "vscode_create",
    ]

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = (context.get("original") or "").lower()
        action = context.get("action") or original

        # Determine which sub-action
        # Use entities keys + original text keywords
        if "file" in entities or "open" in original or entities.get("file"):
            file_name = entities.get("file", "").strip()
            if file_name:
                return await self._open_file(file_name)
            # if action is create
            if "create" in original or "new" in original:
                # try to extract filename from original if not in entities
                # fallback parsing: create file X.py
                import re
                m = re.search(r"create\s+(?:new\s+)?file\s+(\S+)", original)
                if m:
                    return await self._create_file(m.group(1))
                return CommandResult.error("No filename specified to create")

        if "command" in entities:
            return await self._run_terminal(entities["command"])

        if "save" in original:
            return await self._save_file()

        if "create" in original:
            # try to get file from entities or original
            file_name = entities.get("file", "")
            if file_name:
                return await self._create_file(file_name)
            import re
            m = re.search(r"(?:create|new)\s+(?:file\s+)?(\S+\.\w+)", original)
            if m:
                return await self._create_file(m.group(1))
            return CommandResult.error("No filename for create")

        # Fallback: if we have a file entity, open it
        if entities.get("file"):
            return await self._open_file(entities["file"])

        return CommandResult.error("VSCode command unclear. Try 'open main.py' or 'save'")

    async def _open_file(self, file_path: str) -> CommandResult:
        try:
            path = Path(file_path)
            # If relative and not exists, try current working directory search?
            # Try code CLI
            try:
                subprocess.Popen(["code", "--goto", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"VSCode opened: {file_path}")
                return CommandResult.ok(f"Opened {file_path} in VS Code")
            except FileNotFoundError:
                # VSCode CLI not in PATH, try with pyautogui? Try start file
                subprocess.Popen(str(path), shell=True)
                return CommandResult.ok(f"Opened {file_path} (system default)")
        except Exception as e:
            logger.error(f"VSCode open error: {e}")
            return CommandResult.error(f"Failed to open {file_path}: {e}")

    async def _run_terminal(self, command: str) -> CommandResult:
        try:
            # Run via VSCode terminal if possible? For now, run in shell and focus VSCode
            # Attempt to use 'code' integrated terminal is not trivial, so we execute via subprocess
            # and also send keystrokes to VSCode if it's focused
            logger.info(f"Running terminal command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout or result.stderr or "Command completed"
            # Trim output to 500 chars for TTS
            trimmed = output[:500]
            return CommandResult.ok(f"Ran: {command}\n{trimmed}" if trimmed else f"Ran: {command}", data={"output": output})
        except subprocess.TimeoutExpired:
            return CommandResult.error(f"Command timed out: {command}")
        except Exception as e:
            logger.error(f"Terminal error: {e}")
            return CommandResult.error(f"Terminal error: {e}")

    async def _save_file(self) -> CommandResult:
        try:
            import pyautogui
            pyautogui.hotkey('ctrl', 's')
            logger.info("VSCode save triggered")
            return CommandResult.ok("File saved")
        except ImportError:
            return CommandResult.error("pyautogui not installed for save")
        except Exception as e:
            return CommandResult.error(f"Save failed: {e}")

    async def _create_file(self, file_path: str) -> CommandResult:
        try:
            p = Path(file_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.touch()
                logger.info(f"Created file: {file_path}")
            # Open in VSCode
            try:
                subprocess.Popen(["code", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                pass
            return CommandResult.ok(f"Created {file_path}")
        except Exception as e:
            logger.error(f"Create file error: {e}")
            return CommandResult.error(f"Failed to create {file_path}: {e}")

    async def verify_action(self, entities: Dict[str, Any], context: Dict[str, Any]) -> bool:
        # For file open/create, verify file exists
        file_name = entities.get("file")
        if file_name:
            p = Path(file_name)
            # If we tried to create, it should exist
            if "create" in (context.get("original") or "").lower():
                return p.exists()
            # For open, we trust success if file path looks valid
            return True
        return True
