"""
OMNI SECURITY - local camera-based guard & lockdown (Phase 8).

Modules:
  face_auth      -> enroll the owner + verify camera frames (local, OpenCV)
  lockdown       -> cross-platform machine lock with pre-lock alert + countdown
  guard_monitor  -> background camera watchdog: detect intruder -> alert -> lock

Fully local: OpenCV face detection, no cloud, no API. The messenger alert is
the only external-facing piece and is optional.
"""
from omni_v2.security.face_auth import FaceAuth, get_face_auth
from omni_v2.security.lockdown import MachineLocker, LockdownController, get_lockdown_controller
from omni_v2.security.guard_monitor import GuardMonitor, get_guard_monitor

__all__ = [
    "FaceAuth", "get_face_auth",
    "MachineLocker", "LockdownController", "get_lockdown_controller",
    "GuardMonitor", "get_guard_monitor",
]
