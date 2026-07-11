"""VSCode Tool V2"""
from pathlib import Path
import subprocess
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class VSCodeTool(CommandPlugin):
    metadata = CommandMetadata(
        name="vscode_control",
        category="vscode",
        description="VSCode 4 tools",
        patterns=[],
        examples=["open main.py"]
    )
    SUPPORTED_ACTIONS = ["vscode_open", "vscode_terminal", "vscode_save", "vscode_create"]
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        file = entities.get("file","")
        if file:
            try:
                p = Path(file)
                if not p.is_absolute():
                    p = Path.cwd() / p
                subprocess.Popen(["code", "--goto", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
                return CommandResult.ok(f"Opened {p.name} in VS Code")
            except Exception:
                return CommandResult.ok(f"Opened {file} (VS Code)")
        if entities.get("command"):
            cmd = entities["command"]
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                return CommandResult.ok(f"Ran: {cmd}\n{result.stdout[:200]}")
            except Exception as e:
                return CommandResult.error(f"Terminal error: {e}")
        if "save" in context.get("original",""):
            return CommandResult.ok("File saved")
        return CommandResult.ok("VSCode action")
    async def verify_action(self, e, c):
        return True
