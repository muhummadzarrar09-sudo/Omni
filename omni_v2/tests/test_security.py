"""
Tests for the local camera security layer (Phase 8).
Run: python -m pytest omni_v2/tests/test_security.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_sec_")))

import numpy as np

from omni_v2.security.face_auth import (
    FaceAuth, VERDICT_OWNER, VERDICT_UNKNOWN, VERDICT_NO_FACE, VERDICT_UNAVAILABLE,
)
from omni_v2.security.lockdown import LockdownController, MachineLocker
from omni_v2.security.guard_monitor import GuardMonitor


def _synthetic_face(rng, size=120):
    """A fake 'face' BGR image (noisy, roughly face-shaped region)."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = rng.integers(40, 200, size=(size, size, 3))
    cv, cy = size // 2, size // 2
    rr, cc = np.ogrid[:size, :size]
    mask = (rr - cy) ** 2 / (size * 0.22) ** 2 + (cc - cv) ** 2 / (size * 0.16) ** 2 <= 1
    img[mask] = np.clip(img[mask].astype(int) + 60, 0, 255).astype(np.uint8)
    return img


class CropFaceAuth(FaceAuth):
    """FaceAuth that injects crops directly (bypasses Haar detection for tests)."""
    def __init__(self, crops, **kw):
        super().__init__(**kw)
        self._crops = list(crops)
    def _face_crops(self, frame):
        return self._crops


# ---------------------------------------------------------------------------
# FaceAuth descriptor & distance
# ---------------------------------------------------------------------------
def test_descriptor_consistency():
    rng = np.random.default_rng(42)
    f1 = _synthetic_face(rng)
    fa = FaceAuth(owner_path=Path("/tmp/nonexistent_owner.json"))
    d1 = fa._descriptor(f1)
    d2 = fa._descriptor(f1.copy())
    assert d1 is not None and d2 is not None
    assert fa._distance(d1["vec"], d2["vec"]) < 1e-6  # identical -> distance 0


def test_distance_separates_different_faces():
    fa = FaceAuth(owner_path=Path("/tmp/nonexistent_owner.json"))
    rng = np.random.default_rng(1)
    a = fa._descriptor(_synthetic_face(rng))
    rng2 = np.random.default_rng(999)
    b = fa._descriptor(_synthetic_face(rng2))
    assert a is not None and b is not None
    assert fa._distance(a["vec"], b["vec"]) > 0.01


def test_verify_unavailable_when_not_enrolled():
    fa = FaceAuth(owner_path=Path("/tmp/nonexistent_owner.json"))
    res = fa.verify(np.zeros((100, 100, 3), dtype=np.uint8))
    assert res["verdict"] == VERDICT_UNAVAILABLE


def test_enroll_and_verify_owner():
    with tempfile.TemporaryDirectory() as tmp:
        face = _synthetic_face(np.random.default_rng(5))
        fa = CropFaceAuth([face], owner_path=Path(tmp) / "owner.json")
        res = fa.enroll(None)
        assert res["enrolled"] is True
        assert fa.enrolled is True
        v = fa.verify(None)
        assert v["verdict"] == VERDICT_OWNER


def test_verify_unknown_face():
    with tempfile.TemporaryDirectory() as tmp:
        owner_face = _synthetic_face(np.random.default_rng(5))
        fa = CropFaceAuth([owner_face], owner_path=Path(tmp) / "owner.json")
        fa.enroll(None)
        # A structurally different (low-texture, bright) face -> unknown
        intruder = np.full((120, 120, 3), 240, dtype=np.uint8)
        intruder[30:90, 30:90] = (10, 10, 10)
        fa._crops = [intruder]
        v = fa.verify(None)
        assert v["verdict"] == VERDICT_UNKNOWN
        assert v["unknown_faces"] >= 1


def test_enroll_persists():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "owner.json"
        fa = CropFaceAuth([_synthetic_face(np.random.default_rng(5))], owner_path=path)
        fa.enroll(None)
        fa2 = CropFaceAuth([_synthetic_face(np.random.default_rng(5))], owner_path=path)
        assert fa2.enrolled is True


def test_no_face_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        fa = CropFaceAuth([], owner_path=Path(tmp) / "owner.json")
        fa._owner_desc = {"vec": [0.1, 0.2, 0.3], "n": 3, "threshold": 0.3}
        v = fa.verify(None)
        assert v["verdict"] == VERDICT_NO_FACE


# ---------------------------------------------------------------------------
# Lockdown
# ---------------------------------------------------------------------------
class FakeLocker(MachineLocker):
    def __init__(self):
        self.locked = False
    def lock_now(self):
        self.locked = True
        return True


def test_lockdown_alert_before_lock():
    with tempfile.TemporaryDirectory() as tmp:
        alerts = []
        locker = FakeLocker()
        lc = LockdownController(locker=locker, notify_fn=lambda t: alerts.append(t),
                                log_path=Path(tmp) / "lock.json", default_countdown=0.01)
        ev = lc.lock_with_countdown(reason="test", block=True)
        assert ev["alerted"] is True
        assert ev["locked"] is True
        assert len(alerts) == 1
        assert "test" in alerts[0]


def test_lockdown_records_history():
    with tempfile.TemporaryDirectory() as tmp:
        lc = LockdownController(locker=FakeLocker(), log_path=Path(tmp) / "lock.json",
                                default_countdown=0.0)
        lc.lock_with_countdown(reason="a", block=True)
        lc.lock_with_countdown(reason="b", block=True)
        hist = lc.history()
        assert len(hist) == 2
        assert hist[0]["reason"] == "b"


def test_lockdown_no_notify_ok():
    with tempfile.TemporaryDirectory() as tmp:
        lc = LockdownController(locker=FakeLocker(), notify_fn=None,
                                log_path=Path(tmp) / "lock.json", default_countdown=0.0)
        ev = lc.lock_with_countdown(reason="x", block=True)
        assert ev["locked"] is True


# ---------------------------------------------------------------------------
# Guard monitor (fake face_auth to avoid camera)
# ---------------------------------------------------------------------------
class FakeFaceAuth:
    def __init__(self, verdicts):
        self._verdicts = list(verdicts)
        self.enrolled = True
    def open_camera(self, index=0):
        return True
    def close_camera(self):
        pass
    def capture_frame(self):
        return object()
    def verify(self, frame):
        return {"verdict": self._verdicts.pop(0) if self._verdicts else VERDICT_OWNER,
                "faces": 1, "unknown_faces": 1, "distances": [0.9]}


class FakeLockdown:
    def __init__(self):
        self.events = []
    def lock_with_countdown(self, reason, block=False):
        self.events.append(reason)
        return {"locked": True, "alerted": True, "reason": reason, "status": "locked"}


def test_guard_triggers_on_unknown_streak():
    fa = FakeFaceAuth([VERDICT_UNKNOWN, VERDICT_UNKNOWN, VERDICT_UNKNOWN])
    ld = FakeLockdown()
    fired = []
    gm = GuardMonitor(face_auth=fa, lockdown=ld, interval=0.01,
                      unknown_streak_required=3, on_intruder=lambda e: fired.append(e))
    for _ in range(3):
        gm._check_once()
    assert len(fired) >= 1
    assert len(ld.events) >= 1
    assert "unrecognized" in ld.events[0]


def test_guard_owner_resets_streak():
    fa = FakeFaceAuth([VERDICT_UNKNOWN, VERDICT_OWNER, VERDICT_UNKNOWN, VERDICT_UNKNOWN])
    ld = FakeLockdown()
    fired = []
    gm = GuardMonitor(face_auth=fa, lockdown=ld, interval=0.01,
                      unknown_streak_required=3, on_intruder=lambda e: fired.append(e))
    for _ in range(4):
        gm._check_once()
    assert fired == []


def test_guard_requires_enrolled():
    fa = FakeFaceAuth([VERDICT_UNKNOWN])
    fa.enrolled = False
    gm = GuardMonitor(face_auth=fa)
    assert gm.arm() is False


def test_guard_stats():
    fa = FakeFaceAuth([VERDICT_OWNER])
    gm = GuardMonitor(face_auth=fa, lockdown=FakeLockdown())
    gm._check_once()
    st = gm.stats()
    assert st["enrolled"] is True


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
