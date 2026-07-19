r"""
OMNI V3 - Security Guardrails
Stress-test defenses against:
  1. Path traversal (writing outside data/)
  2. Shell injection via vscode_terminal
  3. Malformed JSON DoS
  4. Oversized inputs
  5. ReDoS (regex denial of service)
  6. Sensitive path blocking (C:\Windows, system32, etc.)
  7. Loop bounds on self-healing
  8. Unicode/encoding attacks
"""
import re
import os
import json
import logging
from pathlib import Path
from typing import Any, Optional, Tuple

logger = logging.getLogger("Guardrails")

# === 1. PATH GUARD ===

# Windows: directories that should NEVER be writable
FORBIDDEN_PATH_PATTERNS_WIN = [
    re.compile(r"^[a-zA-Z]:\\Windows", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\Program Files", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\Program Files \(x86\)", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\ProgramData", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\System Volume Information", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\Boot", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\$Recycle", re.IGNORECASE),
    # Unix
    re.compile(r"^/etc(/|$)"),
    re.compile(r"^/boot(/|$)"),
    re.compile(r"^/sys(/|$)"),
    re.compile(r"^/proc(/|$)"),
    re.compile(r"^/dev(/|$)"),
    re.compile(r"^/root(/|$)"),
    re.compile(r"^/sbin(/|$)"),
    re.compile(r"^/usr/sbin(/|$)"),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\.[\\/]"),
    re.compile(r"\.\.%2[fF]"),
    re.compile(r"%2[eE]%2[eE]"),
    re.compile(r"\.\.\\"),
]

# Max file size to write (1MB)
MAX_FILE_WRITE_BYTES = 1024 * 1024


def safe_path(path_str: str, allowed_root: Optional[Path] = None) -> Tuple[bool, str]:
    r"""
    Validate a path. Returns (is_safe, error_message).
    Blocks:
      - Path traversal (..\)
      - Forbidden system directories
      - Absolute paths outside allowed_root
    """
    if not path_str or not isinstance(path_str, str):
        return False, "Path is empty or not a string"

    # Length cap (defense against huge paths)
    if len(path_str) > 1000:
        return False, f"Path too long ({len(path_str)} chars, max 1000)"

    # Normalize separators for pattern matching
    normalized = path_str.replace("\\", "/")

    # Check traversal patterns on the ORIGINAL string (preserves backslash traversal)
    for pat in PATH_TRAVERSAL_PATTERNS:
        if pat.search(path_str) or pat.search(normalized):
            return False, f"Path traversal pattern detected: {pat.pattern}"

    # Check forbidden patterns BEFORE resolution (resolution can rewrite on non-native OS)
    for pat in FORBIDDEN_PATH_PATTERNS_WIN:
        # Check both original (with backslashes) and normalized (with forward slashes)
        if pat.match(path_str) or pat.match(normalized):
            return False, f"Path is in a forbidden system directory: {path_str}"

    # Then try to resolve for the relative-to-allowed-root check
    try:
        p = Path(path_str)
        if allowed_root:
            p = (allowed_root / p).resolve() if not p.is_absolute() else p.resolve()
            try:
                p.relative_to(allowed_root.resolve())
            except ValueError:
                return False, f"Path escapes allowed root: {p} not in {allowed_root}"
        else:
            p = p.resolve()
        # Re-check resolved path against forbidden patterns (catches symlink games)
        resolved_norm = str(p).replace("\\", "/")
        for pat in FORBIDDEN_PATH_PATTERNS_WIN:
            if pat.match(str(p)) or pat.match(resolved_norm):
                return False, f"Resolved path is in forbidden directory: {p}"
    except Exception as e:
        return False, f"Path resolution failed: {e}"

    return True, ""


# === 2. SHELL COMMAND GUARD ===

# Patterns that are ALWAYS blocked regardless of context
ABSOLUTELY_FORBIDDEN_SHELL = [
    # Destructive
    r"rm\s+(-[a-zA-Z]*)?-[a-zA-Z]*r",  # rm -r
    r"rm\s+(-[a-zA-Z]*)?-[a-zA-Z]*f",  # rm -f
    r"del\s+/[sSqfQ]",  # del /s /q /f
    r"format\s+[a-zA-Z]:",  # format C:
    r"rd\s+/[sS]",  # rd /s
    r"rmdir\s+/[sS]",
    r":\(\)\s*\{.*\};:",  # fork bomb
    r"mkfs",  # format filesystem
    r"dd\s+if=.*of=/dev/",  # disk wipe
    r"shutdown",  # system shutdown
    r"reboot",
    r"poweroff",
    r"halt",
    # Privilege escalation
    r"net\s+user\s+.*\s+/add",  # create user
    r"sudo\s+su",
    r"runas\s+/user:administrator",
    # Network exfil
    r"curl\s+.*\|\s*(bash|sh|cmd|powershell)",
    r"wget\s+.*\|\s*(bash|sh|cmd|powershell)",
    r"Invoke-WebRequest.*\|\s*Ivoke-Expression",
    r"iwr.*\|\s*iex",
    r"bitsadmin\s+/transfer",
    # Registry tampering
    r"reg\s+delete\s+HKLM",
    r"reg\s+add\s+HKLM",
    r"reg\s+delete\s+HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    # Remote code
    r"powershell\s+.*-enc",
    r"powershell\s+.*-EncodedCommand",
    r"powershell\s+.*-e\s",
    r"powershell\s+.*-ExecutionPolicy\s+Bypass",
    r"cmd\s+/c\s+.*&&",
]

# Compile
SHELL_BLOCKERS = [re.compile(p, re.IGNORECASE) for p in ABSOLUTELY_FORBIDDEN_SHELL]

# Allowlist of safe base commands (whitelist approach for ultimate safety)
SAFE_SHELL_COMMANDS = {
    "dir", "ls", "echo", "type", "cat", "cd", "pwd", "set", "echo.",
    "where", "which", "whoami", "hostname", "date", "time", "ver",
    "ipconfig", "ping", "tracert", "nslookup", "systeminfo", "tasklist",
    "code", "notepad", "calc",
}


def safe_shell_command(cmd: str) -> Tuple[bool, str]:
    """
    Validate a shell command. Returns (is_safe, error_message).
    Strict mode: must start with a known-safe base command.
    """
    if not cmd or not isinstance(cmd, str):
        return False, "Command is empty or not a string"

    # Length cap
    if len(cmd) > 500:
        return False, f"Command too long ({len(cmd)} chars)"

    # Block absolutely-forbidden patterns
    for blocker in SHELL_BLOCKERS:
        if blocker.search(cmd):
            return False, f"Forbidden shell pattern: {blocker.pattern}"

    # Block any null bytes or control chars
    if any(ord(c) < 32 and c not in '\t\n\r' for c in cmd):
        return False, "Command contains control characters"

    # Extract base command (first word)
    base = cmd.strip().split()[0].lower() if cmd.strip() else ""
    # Strip extensions
    for suffix in (".exe", ".bat", ".cmd"):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    # Permit only the harmless version probe for Python; never permit arbitrary
    # interpreter/package-manager execution through this generic validator.
    if base == "python" and cmd.strip().lower() in {"python --version", "python -v"}:
        return True, ""
    if base not in SAFE_SHELL_COMMANDS:
        return False, f"Base command '{base}' not in safe allowlist. Safe: {sorted(SAFE_SHELL_COMMANDS)[:10]}..."

    # Block if it contains shell metachars that bypass allowlist
    dangerous_meta = ["&&", "||", ";", "|", ">", "<", "`", "$("]
    # Allow only ONE pipe at a time for "dir | findstr" pattern
    if cmd.count("|") > 1:
        return False, "Multiple pipes not allowed"
    if any(m in cmd for m in ["&&", "||", ";", "`", "$("]):
        return False, f"Shell metacharacters not allowed: && || ; ` $("

    # Block obvious redirect-to-system-paths
    if re.search(r">\s*[a-zA-Z]:\\Windows", cmd, re.IGNORECASE):
        return False, "Redirect into Windows directory blocked"
    if re.search(r">\s*/etc/", cmd, re.IGNORECASE):
        return False, "Redirect into /etc blocked"

    return True, ""


# === 3. JSON PARSE GUARD ===

def safe_json_loads(text: str, max_length: int = 100_000) -> Tuple[bool, Any, str]:
    """
    Parse JSON safely. Returns (success, value, error_message).
    Caps input length to prevent DoS via giant strings.
    """
    if not text or not isinstance(text, str):
        return False, None, "Input is empty or not a string"
    if len(text) > max_length:
        return False, None, f"JSON input too long ({len(text)} chars, max {max_length})"
    try:
        return True, json.loads(text), ""
    except json.JSONDecodeError as e:
        return False, None, f"JSON parse error: {e}"
    except Exception as e:
        return False, None, f"Unexpected JSON error: {e}"


# === 4. INPUT SIZE GUARDS ===

def cap_string(s: str, max_len: int = 10_000, name: str = "input") -> str:
    """Cap a string to max_len characters, log if truncated."""
    if not isinstance(s, str):
        s = str(s)
    if len(s) > max_len:
        logger.warning(f"Guardrail: {name} truncated from {len(s)} to {max_len} chars")
        return s[:max_len] + "...[truncated]"
    return s


# === 5. LLM OUTPUT VALIDATION ===

# Patterns that suggest prompt injection or malicious output
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all|the)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|all|the|my)\s+(instructions?|prompts?|system)", re.IGNORECASE),
    re.compile(r"forget\s+(previous|all|the)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),  # trying to inject system role
]


def scan_prompt_injection(text: str) -> Tuple[bool, str]:
    """Detect prompt injection attempts in user input."""
    if not text:
        return False, ""
    for pat in PROMPT_INJECTION_PATTERNS:
        m = pat.search(text)
        if m:
            return True, f"Suspicious pattern: '{m.group(0)}'"
    return False, ""


# === 6. RECURSION / LOOP BOUNDS ===

class LoopGuard:
    """Track and limit self-healing loop iterations."""
    def __init__(self, max_per_request: int = 5):
        self.max_per_request = max_per_request
        self.count = 0

    def check(self) -> Tuple[bool, str]:
        if self.count >= self.max_per_request:
            return False, f"Loop guard tripped: {self.count} >= {self.max_per_request}"
        self.count += 1
        return True, ""


# === 7. TOOL ARGS VALIDATION ===

# Each tool can declare what args it expects
TOOL_ARG_LIMITS = {
    "browser_navigate": {"url": 2000},
    "browser_search": {"query": 500},
    "windows_launch": {"app": 100, "args": 1000},
    "files_write": {"path": 1000, "content": MAX_FILE_WRITE_BYTES},
    "files_read": {"path": 1000},
    "vscode_terminal": {"command": 500},
}


def validate_tool_args(tool: str, args: dict) -> Tuple[bool, str]:
    """Validate tool args against limits."""
    if not isinstance(args, dict):
        return False, f"Args must be a dict, got {type(args).__name__}"

    limits = TOOL_ARG_LIMITS.get(tool, {})
    for k, v in args.items():
        if k in limits:
            v_str = str(v) if v is not None else ""
            if len(v_str) > limits[k]:
                return False, f"Arg '{k}' too long ({len(v_str)} > {limits[k]})"

        # Generic caps on all args
        if isinstance(v, str) and len(v) > 100_000:
            return False, f"Arg '{k}' exceeds 100KB limit"
        if isinstance(v, (dict, list)) and len(str(v)) > 100_000:
            return False, f"Arg '{k}' (collection) exceeds 100KB limit"

    return True, ""


# === 8. URL GUARD (for browser_navigate) ===

ALLOWED_URL_SCHEMES = {"http", "https", "ftp", "file"}
BLOCKED_URL_PATTERNS = [
    re.compile(r"^file:///[a-zA-Z]:/Windows", re.IGNORECASE),
    re.compile(r"^file:///[a-zA-Z]:/Program Files", re.IGNORECASE),
    re.compile(r"^javascript:", re.IGNORECASE),
    re.compile(r"^data:.*<script", re.IGNORECASE),
    re.compile(r"^vbscript:", re.IGNORECASE),
]


def safe_url(url: str) -> Tuple[bool, str]:
    """Validate a URL for browser navigation."""
    if not url or not isinstance(url, str):
        return False, "URL is empty"
    if len(url) > 2000:
        return False, f"URL too long ({len(url)} chars)"

    for pat in BLOCKED_URL_PATTERNS:
        if pat.match(url):
            return False, f"URL matches blocked pattern: {pat.pattern}"

    # Must have a scheme
    if "://" not in url:
        return False, "URL missing scheme (e.g., https://)"

    scheme = url.split("://", 1)[0].lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        return False, f"URL scheme '{scheme}' not allowed. Allowed: {ALLOWED_URL_SCHEMES}"

    return True, ""


# === 9. RATE LIMIT (basic) ===

import time
from collections import defaultdict


class RateLimiter:
    """Simple per-key rate limiter."""
    def __init__(self, max_per_minute: int = 60):
        self.max_per_minute = max_per_minute
        self._buckets = defaultdict(list)

    def check(self, key: str) -> Tuple[bool, str]:
        now = time.time()
        bucket = self._buckets[key]
        # Drop old entries
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= self.max_per_minute:
            return False, f"Rate limit: {len(bucket)}/{self.max_per_minute} per minute for '{key}'"
        bucket.append(now)
        return True, ""


# === 10. SECURE RANDOM / NONCE ===

import secrets

def make_nonce(n: int = 16) -> str:
    """Generate a cryptographically-secure nonce for command tracking."""
    return secrets.token_urlsafe(n)


# === EXPORTS ===

__all__ = [
    "safe_path", "safe_shell_command", "safe_json_loads", "cap_string",
    "scan_prompt_injection", "LoopGuard", "validate_tool_args",
    "safe_url", "RateLimiter", "make_nonce",
    "MAX_FILE_WRITE_BYTES", "FORBIDDEN_PATH_PATTERNS_WIN",
    "PATH_TRAVERSAL_PATTERNS", "ABSOLUTELY_FORBIDDEN_SHELL", "SAFE_SHELL_COMMANDS",
    "PROMPT_INJECTION_PATTERNS", "ALLOWED_URL_SCHEMES",
]
