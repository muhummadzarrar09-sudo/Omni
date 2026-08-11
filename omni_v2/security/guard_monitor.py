"""
OMNI GUARD MONITOR - background camera watchdog (Phase 8 security).

When armed, it periodically samples the camera and verifies the person at the
machine against the enrolled owner. On an "unknown" verdict it:
   1. raises a local `on_intruder` callback / stores an event,
   2. (via the LockdownController) sends a pre-lock alert, runs a countdown,
      then locks the machine.

Fully local & offline (OpenCV + messenger). The `on_intruder` hook is what the
desktop app / CLI use to notify before lockdown.

It is intentionally conservative and debounced: it requires N consecutive
unknown verdicts before acting, to avoid false positives from a momentary
glance away. The owner can cancel during the countdown.
"""
from __future__ import annotations
import time
import threading
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("GuardMonitor")

try:
    from omni_v2.security.face_auth import FaceAuth, VERDICT_UNKNOWN, VERDICT_NO_FACE, VERDICT_UNAVAILABLE
except Exception:  # pragma: no cover
    FaceAuth = None
    VERDICT_UNKNOWN = "unknown"
    VERDICT_NO_FACE = "no_face"
    VERDICT_UNAVAILABLE = "unavailable"

try:
    from omni_v2.security.lockdown import LockdownController
except Exception:  # pragma: no cover
    LockdownController = None


class GuardMonitor:
    """Background camera-based intruder watchdog."""

    def __init__(
        self,
        face_auth: Optional[FaceAuth] = None,
        lockdown: Optional[LockdownController] = None,
        interval: float = 2.0,
        unknown_streak_required: int = 3,
        on_intruder: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_callback: Optional[Callable[[], bool]] = None,
        camera_index: int = 0,
    ):
        self.face_auth = face_auth or (FaceAuth() if FaceAuth else None)
        self.lockdown = lockdown or (LockdownController() if LockdownController else None)
        self.interval = interval
        self.unknown_streak_required = unknown_streak_required
        self.on_intruder = on_intruder          # notified on confirmed intruder
        self.cancel_callback = cancel_callback  # called during countdown; True=cancel
        self.camera_index = camera_index

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._armed = False
        self._lock = threading.RLock()
        self._unknown_streak = 0
        self._events: List[Dict[str, Any]] = []

    # -- control -----------------------------------------------------------
    def arm(self) -> bool:
        """Start the watchdog. Returns True if the camera opened."""
        if self.face_auth is None:
            logger.warning("Guard monitor cannot arm (face_auth unavailable)")
            return False
        if not self.face_auth.enrolled:
            logger.warning("Guard monitor cannot arm (owner not enrolled)")
            return False
        if not self.face_auth.open_camera(self.camera_index):
            logger.warning("Guard monitor cannot arm (no camera)")
            return False
        self._stop.clear()
        self._armed = True
        self._unknown_streak = 0
        self._thread = threading.Thread(target=self._loop, daemon=True, name="omni-guard")
        self._thread.start()
        logger.info("Guard monitor armed")
        return True

    def disarm(self) -> None:
        self._armed = False
        self._stop.set()
        if self.face_auth is not None:
            self.face_auth.close_camera()

    @property
    def armed(self) -> bool:
        return self._armed

    def snapshot(self) -> Dict[str, Any]:
        """Single-shot verify (used by tests / manual check). Returns verdict."""
        if self.face_auth is None:
            return {"verdict": VERDICT_UNAVAILABLE}
        frame = self.face_auth.capture_frame()
        if frame is None:
            return {"verdict": VERDICT_UNAVAILABLE, "reason": "no_camera_frame"}
        return self.face_auth.verify(frame)

    # -- main loop ---------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._check_once()
            except Exception as e:
                logger.warning(f"Guard check error: {e}")
            self._stop.wait(self.interval)

    def _check_once(self) -> None:
        res = self.snapshot()
        verdict = res.get("verdict", VERDICT_UNAVAILABLE)
        if verdict == VERDICT_UNKNOWN:
            self._unknown_streak += 1
            if self._unknown_streak >= self.unknown_streak_required:
                self._unknown_streak = 0  # reset so it re-triggers on continued intruder
                self._handle_intruder(res)
        elif verdict == VERDICT_NO_FACE:
            # no face is NOT an intruder by itself (owner may be away) — keep
            # a small streak but don't escalate on it.
            pass
        else:
            # owner or unavailable -> reset streak
            self._unknown_streak = 0

    def _handle_intruder(self, res: Dict[str, Any]) -> None:
        event = {
            "ts": time.time(),
            "verdict": VERDICT_UNKNOWN,
            "faces": res.get("faces", 0),
            "unknown_faces": res.get("unknown_faces", 0),
            "distances": res.get("distances", []),
        }
        self._events.append(event)
        self._events = self._events[-100:]

        # 1) local callback (desktop app shows alert / can auto-cancel)
        if self.on_intruder is not None:
            try:
                self.on_intruder(event)
            except Exception as e:
                logger.warning(f"on_intruder callback error: {e}")

        # 2) countdown with cancel opportunity -> lock
        if self.lockdown is not None:
            # expose a cancel closure to the callback during countdown
            if self.cancel_callback is not None:
                # give the UI a way to cancel: cancel_callback() returns True to abort
                import threading as _t
                lock_res = {}
                def _maybe_run():
                    # poll cancel during the countdown is handled inside lockdown's sleep;
                    # simplest: check cancel BEFORE arming the lock, and after sleep
                    if self.cancel_callback() is True:
                        lock_res["cancelled"] = True
                        return
                    ld = self.lockdown.lock_with_countdown(reason="unrecognized person at machine", block=True)
                    lock_res.update(ld)
                _t.Thread(target=_maybe_run, daemon=True, name="omni-intruder-lock").start()
            else:
                self.lockdown.lock_with_countdown(
                    reason="unrecognized person at machine", block=False)
        logger.warning("Guard: intruder detected -> alert + lockdown")

    def events(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._events[-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        return {
            "armed": self._armed,
            "unknown_streak": self._unknown_streak,
            "events_total": len(self._events),
            "enrolled": bool(self.face_auth and self.face_auth.enrolled),
            "interval": self.interval,
            "streak_required": self.unknown_streak_required,
        }


def get_guard_monitor(**kwargs) -> GuardMonitor:
    return GuardMonitor(**kwargs)
