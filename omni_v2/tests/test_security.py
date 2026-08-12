"""
Tests for the local camera security layer (Phase 8) - hardened verifier backends.
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
import pytest

from omni_v2.security.face_auth import (
    FaceAuth, VERDICT_OWNER, VERDICT_UNKNOWN, VERDICT_NO_FACE, VERDICT_UNAVAILABLE,
    GradientVerifier, LBPHVerifier, DeepVerifier,
)
from omni_v2.security.lockdown import LockdownController, MachineLocker
from omni_v2.security.guard_monitor import GuardMonitor


def _synthetic_face(rng, size=120, seed_offset=0):
    """A fake 'face' image (noisy + oval, deterministically keyed by seed)."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = rng.integers(40, 200, size=(size, size, 3))
    cv, cy = size // 2, size // 2
    rr, cc = np.ogrid[:size, :size]
    mask = (rr - cy) ** 2 / (size * 0.22) ** 2 + (cc - cv) ** 2 / (size * 0.16) ** 2 <= 1
    img[mask] = np.clip(img[mask].astype(int) + 60, 0, 255).astype(np.uint8)
    return img


def _owner_crops(n=4, seed=5):
    """Several slightly-varied crops of the same 'person'."""
    return [_synthetic_face(np.random.default_rng(seed + i)) for i in range(n)]


def _intruder_crops(seed=9000):
    # structurally different: bright, low-texture
    img = np.full((120, 120, 3), 245, dtype=np.uint8)
    img[30:90, 30:90] = (8, 8, 8)
    return [img]


# ---------------------------------------------------------------------------
# Gradient backend
# ---------------------------------------------------------------------------
def test_gradient_enroll_and_verify_owner():
    with tempfile.TemporaryDirectory() as tmp:
        fa = FaceAuth(owner_path=Path(tmp) / "owner.json",
                      verifier=GradientVerifier(threshold=0.30))
        res = fa.enroll_crops(_owner_crops())
        assert res["backend"] == "gradient"
        assert res["samples"] == 4
        assert fa.enrolled is True
        v = fa.verify_crops(_owner_crops(seed=5))
        assert v["verdict"] == VERDICT_OWNER


def test_gradient_verify_unknown():
    with tempfile.TemporaryDirectory() as tmp:
        fa = FaceAuth(owner_path=Path(tmp) / "owner.json",
                      verifier=GradientVerifier(threshold=0.30))
        fa.enroll_crops(_owner_crops())
        v = fa.verify_crops(_intruder_crops())
        assert v["verdict"] == VERDICT_UNKNOWN
        assert v["unknown_faces"] >= 1


def test_gradient_multisample_robust():
    # enrolling 4 samples should make a stray odd crop not ruin the model
    with tempfile.TemporaryDirectory() as tmp:
        fa = FaceAuth(owner_path=Path(tmp) / "owner.json",
                      verifier=GradientVerifier(threshold=0.30))
        crops = _owner_crops()[:3] + [np.full((120, 120, 3), 250, dtype=np.uint8)]
        fa.enroll_crops(crops)
        assert fa.enrolled is True


def test_verify_unavailable_when_not_enrolled():
    with tempfile.TemporaryDirectory() as tmp:
        fa = FaceAuth(owner_path=Path(tmp) / "fresh_owner.json",
                      verifier=GradientVerifier())
        v = fa.verify_crops([np.zeros((100, 100, 3), dtype=np.uint8)])
        assert v["verdict"] == VERDICT_UNAVAILABLE


def test_no_face_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        fa = FaceAuth(owner_path=Path(tmp) / "fresh_owner.json",
                      verifier=GradientVerifier())
        fa.enroll_crops(_owner_crops())
        v = fa.verify_crops([])
        assert v["verdict"] == VERDICT_NO_FACE


def test_gradient_persists():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "owner.json"
        fa = FaceAuth(owner_path=path, verifier=GradientVerifier(threshold=0.30))
        fa.enroll_crops(_owner_crops())
        fa2 = FaceAuth(owner_path=path, verifier=GradientVerifier(threshold=0.30))
        assert fa2.enrolled is True
        assert fa2.verify_crops(_owner_crops(seed=5))["verdict"] == VERDICT_OWNER


# ---------------------------------------------------------------------------
# LBPH backend (trained recognizer)
# ---------------------------------------------------------------------------
def _has_lbph() -> bool:
    try:
        import cv2
    except ImportError:
        return False
    return hasattr(cv2, "face")


requires_lbph = pytest.mark.skipif(
    not _has_lbph(), reason="requires optional opencv-contrib cv2.face support"
)


@requires_lbph
def test_lbph_score_separates():
    # LOWER confidence = closer. Same-person should score far lower than an intruder.
    with tempfile.TemporaryDirectory() as tmp:
        v = LBPHVerifier(threshold=1.5)
        v.enroll(_owner_crops(n=4, seed=7))
        same = v.score(_synthetic_face(np.random.default_rng(7), seed_offset=9))
        diff = v.score(_intruder_crops()[0])
        assert same is not None and diff is not None
        assert same < diff


@requires_lbph
def test_lbph_enroll_and_verify():
    with tempfile.TemporaryDirectory() as tmp:
        fa = FaceAuth(owner_path=Path(tmp) / "owner.json", model_path=Path(tmp) / "m.xml",
                      verifier=LBPHVerifier(threshold=1.5))
        res = fa.enroll_crops(_owner_crops(seed=7))
        assert res["backend"] == "lbph"
        assert res["samples"] >= 3
        # same person (tight threshold) -> owner
        v = fa.verify_crops([_synthetic_face(np.random.default_rng(8))])
        assert v["verdict"] == VERDICT_OWNER
        # intruder with tight threshold -> unknown
        v2 = fa.verify_crops(_intruder_crops())
        assert v2["verdict"] == VERDICT_UNKNOWN


@requires_lbph
def test_lbph_model_save_load():
    with tempfile.TemporaryDirectory() as tmp:
        mp = Path(tmp) / "m.xml"
        meta_path = Path(tmp) / "owner.json"
        fa = FaceAuth(owner_path=meta_path, model_path=mp, verifier=LBPHVerifier(threshold=1.5))
        fa.enroll_crops(_owner_crops(seed=7))
        assert mp.exists() and mp.stat().st_size > 0
        fa2 = FaceAuth(owner_path=meta_path, model_path=mp, verifier=LBPHVerifier(threshold=1.5))
        assert fa2.enrolled is True
        v = fa2.verify_crops([_synthetic_face(np.random.default_rng(8))])
        assert v["verdict"] == VERDICT_OWNER


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------
def test_backend_selection_uses_highest_priority_available_backend():
    fa = FaceAuth(owner_path=Path(tempfile.mkdtemp()) / "selection_owner.json")
    if DeepVerifier().available:
        assert fa.backend == "deep"
    elif _has_lbph():
        assert fa.backend == "lbph"
    else:
        assert fa.backend == "gradient"


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
        lc = LockdownController(locker=FakeLocker(), notify_fn=lambda t: alerts.append(t),
                                log_path=Path(tmp) / "lock.json", default_countdown=0.01)
        ev = lc.lock_with_countdown(reason="test", block=True)
        assert ev["alerted"] is True and ev["locked"] is True
        assert len(alerts) == 1 and "test" in alerts[0]


def test_lockdown_records_history():
    with tempfile.TemporaryDirectory() as tmp:
        lc = LockdownController(locker=FakeLocker(), log_path=Path(tmp) / "lock.json", default_countdown=0.0)
        lc.lock_with_countdown(reason="a", block=True)
        lc.lock_with_countdown(reason="b", block=True)
        hist = lc.history()
        assert len(hist) == 2 and hist[0]["reason"] == "b"


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
    gm = GuardMonitor(face_auth=fa, lockdown=ld, interval=0.01, unknown_streak_required=3,
                      on_intruder=lambda e: fired.append(e))
    for _ in range(3):
        gm._check_once()
    assert len(fired) >= 1 and len(ld.events) >= 1


def test_guard_owner_resets_streak():
    fa = FakeFaceAuth([VERDICT_UNKNOWN, VERDICT_OWNER, VERDICT_UNKNOWN, VERDICT_UNKNOWN])
    fired = []
    gm = GuardMonitor(face_auth=fa, lockdown=FakeLockdown(), interval=0.01,
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
    assert gm.stats()["enrolled"] is True


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
