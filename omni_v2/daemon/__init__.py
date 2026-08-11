"""
OMNI DAEMON (Phase 14, #1) — always-on resident agent + auto-start.

AutoStartManager registers OMNI to start on boot (systemd / XDG autostart /
Windows registry). DaemonController keeps the resident services running.
Headless-testable.
"""
from omni_v2.daemon.daemon import (
    AutoStartManager, DaemonController, PlatformBackend,
    LinuxSystemdBackend, LinuxDesktopBackend, get_autostart, get_daemon,
)

__all__ = [
    "AutoStartManager", "DaemonController", "PlatformBackend",
    "LinuxSystemdBackend", "LinuxDesktopBackend", "get_autostart", "get_daemon",
]
