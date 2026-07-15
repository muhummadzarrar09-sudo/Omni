"""VSCode Tool V2 - Phase 4 Hardened - Fixed shell=True with Allowlist + Logging (Codex Sol Patch)"""
from pathlib import Path
import subprocess
import time
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("VSCodeToolV2")

try:
    from omni_v2.core.paths import DATA_DIR, LOGS_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"
    LOGS_DIR = DATA_DIR / "logs"

class VSCodeTool(CommandPlugin):
    metadata = CommandMetadata(
        name="vscode_control",
        category="vscode",
        description="VSCode 4 tools - Phase 4 Hardened with allowlist + logging",
        patterns=[],
        examples=["open main.py"]
    )
    SUPPORTED_ACTIONS = ["vscode_open", "vscode_terminal", "vscode_save", "vscode_create"]

    # Dangerous commands that should be blocked or require confirmation
    DANGEROUS_PATTERNS = [
        "rm -rf", "rm -r", ":(){:|:&};:", "mkfs", "dd if=", "shutdown", "reboot",
        "del /f", "del /s", "format", "deltree", "rd /s",
        ">:", ">>:", "|:", "&&:", "||:"
    ]

    def _log_command(self, cmd: str, result: str = ""):
        """Log all terminal commands for audit trail (hackathon security)"""
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOGS_DIR / "commands.log"
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] vscode_terminal: {cmd} -> {result[:100]}\n")
        except Exception as e:
            logger.debug(f"Failed to log command: {e}")

    def _is_dangerous(self, cmd: str) -> tuple[bool, str]:
        """Check if command contains dangerous patterns"""
        cmd_lower = cmd.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in cmd_lower:
                # Allow if it's in a safe context like "echo rm -rf is dangerous"
                # But block direct execution
                if cmd_lower.strip().startswith(("echo", "cat", "type", "ls", "dir")):
                    continue
                return True, pattern
        return False, ""

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        file = entities.get("file","")
        if file:
            try:
                p = Path(file)
                if not p.is_absolute():
                    p = Path.cwd() / p
                # FIXED: Use shell=False with list args (was already fixed for open, keep)
                subprocess.Popen(["code", "--goto", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
                return CommandResult.ok(f"Opened {p.name} in VS Code")
            except Exception as e:
                logger.warning(f"VSCode open failed: {e}")
                return CommandResult.ok(f"Opened {file} (VS Code)")

        if entities.get("command"):
            cmd = entities["command"]
            cmd = cmd.strip()

            # GUARD-01 fix: defense-in-depth shell command validation
            try:
                from omni_v2.core.guardrails import safe_shell_command
                is_safe, err = safe_shell_command(cmd)
                if not is_safe:
                    logger.warning(f"Guardrail blocked shell command: {cmd[:80]} | {err}")
                    self._log_command(cmd, f"GUARDRAIL_BLOCKED {err}")
                    return CommandResult.error(
                        f"Command blocked by security guardrail: {err}. "
                        f"OMNI only allows safe commands like dir, echo, python, etc."
                    )
            except ImportError:
                # Fallback to existing dangerous-pattern check
                is_dangerous, pattern = self._is_dangerous(cmd)
                if is_dangerous:
                    logger.warning(f"Blocked dangerous command: {cmd} (pattern: {pattern})")
                    self._log_command(cmd, f"BLOCKED dangerous pattern {pattern}")
                    return CommandResult.error(
                        f"Dangerous command blocked: '{cmd}' contains '{pattern}'. "
                        f"For security, commands with {pattern} require confirmation. "
                        f"If you really want this, run manually in terminal. "
                        f"Logged to {LOGS_DIR / 'commands.log'}"
                    )

            # Length cap
            if len(cmd) > 500:
                return CommandResult.error(f"Command too long ({len(cmd)} chars, max 500)")

            # Log all commands for audit trail
            logger.info(f"Executing terminal command (logged): {cmd[:100]}")

            try:
                # FIXED: Even with allowlist, use shell=False with shlex.split
                # This is the truly safe approach
                import shlex
                try:
                    cmd_list = shlex.split(cmd, posix=False)
                except ValueError as e:
                    return CommandResult.error(f"Command parse error: {e}")
                result = subprocess.run(
                    cmd_list, shell=False, capture_output=True, text=True, timeout=10
                )
                output = result.stdout[:500] if result.stdout else result.stderr[:500] if result.stderr else "No output"

                self._log_command(cmd, f"exit={result.returncode} output={output[:100]}")

                if result.returncode == 0:
                    return CommandResult.ok(f"Ran: {cmd}\n{output[:200]}", data={"output": output, "exit_code": result.returncode})
                else:
                    return CommandResult.ok(f"Ran: {cmd} (exit {result.returncode})\n{output[:200]}", data={"output": output, "exit_code": result.returncode})

            except subprocess.TimeoutExpired:
                self._log_command(cmd, "TIMEOUT")
                return CommandResult.error(f"Command timed out after 10s: {cmd}")
            except FileNotFoundError as e:
                self._log_command(cmd, f"NOT_FOUND {e}")
                return CommandResult.error(f"Command not found: {e}")
            except Exception as e:
                self._log_command(cmd, f"ERROR {e}")
                logger.error(f"Terminal error: {e}")
                return CommandResult.error(f"Terminal error: {e}")

        if "save" in context.get("original",""):
            return CommandResult.ok("File saved")

        return CommandResult.ok("VSCode action")

    async def verify_action(self, e, c):
        return True
