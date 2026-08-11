"""
OMNI LOCKDOWN - lock the machine & trigger system actions (Phase 8 security).

Provides cross-platform "lock the machine" primitives plus a countdown that
fires an alert (messenger) BEFORE locking, so the owner gets a heads-up.

Locking primitives (best-effort, platform-aware):
  - Windows : LockWorkStation via ctypes (or rundll32 fallback).
  - macOS   : `pmset displaysleepnow` (locks the screen).
  - Linux   : `loginctl lock-session` if available, else `xdg-screensaver lock`.

These are deliberately fail-safe: if none succeed we still record a lock event
and return success=False so the caller can escalate (e.g. close the session,
notify again). The heavy action (`lock_now`) is fully local.
"""
from __future__ import annotations
import os
import subprocess
import time
import platform
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Lockdown")

from omni_v2.core.paths import DATA_DIR

LOCK_LOG = DATA_DIR / "security" / "lockdown.json"


class MachineLocker:
    """Cross-platform machine-lock primitives."""

    @staticmethod
    def is_windows() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def is_macos() -> bool:
        return platform.system() == "Darwin"

    def lock_now(self) -> bool:
        """Lock the machine. Returns True if a lock action was invoked."""
        try:
            if self.is_windows():
                return self._lock_windows()
            if self.is_macos():
                return self._lock_macos()
            return self._lock_linux()
        except Exception as e:
            logger.error(f"Lock now failed: {e}")
            return False

    def _lock_windows(self) -> bool:
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return True
        except Exception:
            try:
                subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
                return True
            except Exception:
                return False

    def _lock_macos(self) -> bool:
        try:
            subprocess.Popen(["pmset", "displaysleepnow"])
            return True
        except Exception:
            return False

    def _lock_linux(self) -> bool:
        for cmd in (
            ["loginctl", "lock-session"],
            ["xdg-screensaver", "lock"],
            ["dm-tool", "lock"],
        ):
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=5)
                if r.returncode == 0:
                    return True
            except Exception:
                continue
        return False


class LockdownController:
    """
    Arms a guard: on a trigger, sends a pre-lock alert, runs a countdown,
    then locks the machine. Records every event to data/security/lockdown.json.
    """

    def __init__(
        self,
        locker: Optional[MachineLocker] = None,
        notify_fn: Optional[Callable[[str], Any]] = None,
        log_path: Optional[Path] = None,
        default_countdown: float = 10.0,
    ):
        self.locker = locker or MachineLocker()
        self.notify_fn = notify_fn
        self.log_path = Path(log_path) if log_path else LOCK_LOG
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_countdown = default_countdown

    def lock_with_countdown(self, reason: str = "suspicious activity",
                            countdown: Optional[float] = None,
                            block: bool = True) -> Dict[str, Any]:
        """
        Notify -> wait `countdown` seconds -> lock.
        If block=False, the countdown+lock run in a background thread.
        Returns event dict.
        """
        delay = self.default_countdown if countdown is None else countdown
        event = {
            "ts": time.time(),
            "reason": reason,
            "countdown": delay,
            "alerted": False,
            "locked": False,
            "status": "arming",
        }
        if block:
            event = self._run(reason, delay)
        else:
            import threading
            threading.Thread(
                target=lambda: self._run(reason, delay),
                daemon=True, name="omni-lockdown",
            ).start()
        return event

    def _run(self, reason: str, delay: float) -> Dict[str, Any]:
        event = {
            "ts": time.time(), "reason": reason, "countdown": delay,
            "alerted": False, "locked": False, "status": "arming",
        }
        # 1) alert BEFORE locking
        if self.notify_fn is not None:
            try:
                self.notify_fn(
                    f"⚠️ OMNI security: {reason}. "
                    f"Locking this machine in {int(delay)}s. "
                    f"If this is you, cancel now."
                )
                event["alerted"] = True
            except Exception as e:
                logger.warning(f"Pre-lock alert failed: {e}")
        # 2) countdown (opportunity to cancel)
        if delay > 0:
            try:
                time.sleep(delay)
            except Exception:
                pass
        # 3) lock
        event["locked"] = self.locker.lock_now()
        event["status"] = "locked" if event["locked"] else "lock_failed"
        self._record(event)
        return event

    def _record(self, event: Dict[str, Any]) -> None:
        try:
            records = []
            if self.log_path.exists():
                import json
                records = json.loads(self.log_path.read_text(encoding="utf-8"))
            records.append(event)
            # keep last 200
            records = records[-200:]
            import json
            self.log_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Lockdown log write failed: {e}")

    def history(self, n: int = 10) -> list:
        try:
            import json
            if self.log_path.exists():
                records = json.loads(self.log_path.read_text(encoding="utf-8"))
                return records[-n:][::-1]
        except Exception:
            pass
        return []


def get_lockdown_controller(**kwargs) -> LockdownController:
    return LockdownController(**kwargs)
