"""
OMNI FACE AUTH - local camera-based user verification (Phase 8 security).

Purpose: confirm "is it me at the laptop?" when OMNI is in away/guard mode.

Fully local & offline:
  - Camera capture via OpenCV (VideoCapture).
  - Face detection via OpenCV's bundled Haar cascade (no model download).
  - Identity via a lightweight, deterministic descriptor (resize + gradient
    magnitude + color histogram of the face crop), compared with cosine
    distance against an enrolled "owner" descriptor. No cloud, no API.

Design notes / honest limits:
  - This is a *basic local* biometric check, NOT military-grade (no neural
    face-embedding model). It is good enough to catch "someone else is at the
    machine" in most conditions, but lighting/angle/occlusion affect it. For
    real high-stakes biometrics you'd swap in a trained embedding model — the
    interface (`verify(frame)` -> verdict) is designed so you can.
  - All heavy imports (cv2, numpy) are lazy so the module is importable and
    unit-testable even where OpenCV is missing.

Storage: data/security/owner.json holds the enrolled owner descriptor + a
tolerance threshold chosen at enrollment time.
"""
from __future__ import annotations
import json
import math
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("FaceAuth")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

SECURITY_DIR = DATA_DIR / "security"
OWNER_PATH = SECURITY_DIR / "owner.json"
CASCADE_NAME = "haarcascade_frontalface_default.xml"

# Verdict types
VERDICT_OWNER = "owner"
VERDICT_UNKNOWN = "unknown"
VERDICT_NO_FACE = "no_face"
VERDICT_UNAVAILABLE = "unavailable"


def _lazy_cv():
    import cv2  # noqa: PLC0415 - lazy import, optional dependency
    return cv2


class FaceAuth:
    """Enroll an owner and verify camera frames against that identity."""

    def __init__(self, owner_path: Optional[Path] = None, threshold: float = 0.30):
        self.owner_path = Path(owner_path) if owner_path else OWNER_PATH
        self.threshold = threshold
        self._lock = threading.RLock()
        self._owner_desc: Optional[Dict[str, Any]] = None
        self._cascade = None
        self._camera = None
        self._load_owner()

    # -- descriptor ---------------------------------------------------------
    @staticmethod
    def _descriptor(crop_bgr: Any) -> Optional[Dict[str, Any]]:
        """Compute a compact descriptor for a face crop (BGR array)."""
        try:
            cv2 = _lazy_cv()
            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (48, 48))
            # gradient magnitudes capture structure
            gx = cv2.Sobel(resized, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(resized, cv2.CV_32F, 0, 1, ksize=3)
            mag = cv2.magnitude(gx, gy).flatten()
            # color histogram (HSV hue) adds robustness to lighting
            hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
            desc = list(mag.astype(float) / (mag.max() + 1e-6)) + list(hist / (hist.sum() + 1e-6))
            # normalize the whole vector
            norm = math.sqrt(sum(v * v for v in desc)) or 1.0
            return {"vec": [float(v) / norm for v in desc], "n": len(desc)}
        except Exception as e:
            logger.warning(f"FaceAuth descriptor failed: {e}")
            return None

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    @staticmethod
    def _distance(a: List[float], b: List[float]) -> float:
        # 1 - cosine, in [0,2]
        return 1.0 - FaceAuth._cosine(a, b)

    # -- camera / detection --------------------------------------------------
    def _get_cascade(self):
        if self._cascade is None:
            cv2 = _lazy_cv()
            p = Path(cv2.data.haarcascades) / CASCADE_NAME
            if not p.exists():
                raise RuntimeError(f"Haar cascade not found: {p}")
            self._cascade = cv2.CascadeClassifier(str(p))
        return self._cascade

    def open_camera(self, index: int = 0) -> bool:
        cv2 = _lazy_cv()
        try:
            self._camera = cv2.VideoCapture(index)
            return self._camera.isOpened()
        except Exception as e:
            logger.warning(f"Camera open failed: {e}")
            return False

    def close_camera(self) -> None:
        if self._camera is not None:
            try:
                self._camera.release()
            except Exception:
                pass
            self._camera = None

    def capture_frame(self) -> Optional[Any]:
        """Grab the latest camera frame (BGR ndarray) or None."""
        if self._camera is None:
            if not self.open_camera():
                return None
        ok, frame = self._camera.read()
        if not ok or frame is None:
            return None
        return frame

    def detect_faces(self, frame: Any) -> List[Tuple[int, int, int, int]]:
        cv2 = _lazy_cv()
        cascade = self._get_cascade()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

    def _face_crops(self, frame: Any) -> List[Any]:
        crops = []
        for (x, y, w, h) in self.detect_faces(frame):
            try:
                crops.append(frame[y:y + h, x:x + w])
            except Exception:
                continue
        return crops

    # -- enrollment ------------------------------------------------------------
    def enroll(self, frame: Any) -> Dict[str, Any]:
        """Enroll the owner from a single frame (takes the largest face)."""
        crops = self._face_crops(frame)
        if not crops:
            raise ValueError("no face detected in frame; cannot enroll")
        largest = max(crops, key=lambda c: c.shape[0] * c.shape[1])
        desc = self._descriptor(largest)
        if desc is None:
            raise ValueError("could not build face descriptor")
        with self._lock:
            self._owner_desc = {
                "vec": desc["vec"],
                "n": desc["n"],
                "threshold": self.threshold,
                "enrolled_at": time.time(),
            }
            self._save()
        return {"enrolled": True, "faces": len(crops)}

    def _load_owner(self) -> None:
        try:
            if self.owner_path.exists():
                self._owner_desc = json.loads(self.owner_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"FaceAuth owner load failed: {e}")
            self._owner_desc = None

    def _save(self) -> None:
        SECURITY_DIR.mkdir(parents=True, exist_ok=True)
        if self._owner_desc is None:
            return
        self.owner_path.write_text(json.dumps(self._owner_desc), encoding="utf-8")

    @property
    def enrolled(self) -> bool:
        return self._owner_desc is not None

    # -- verification ----------------------------------------------------------
    def verify(self, frame: Any) -> Dict[str, Any]:
        """Verdict on a single frame. Returns {verdict, faces, distance, ...}."""
        if not self.enrolled:
            return {"verdict": VERDICT_UNAVAILABLE, "faces": 0, "reason": "not_enrolled"}
        try:
            crops = self._face_crops(frame)
        except Exception as e:
            return {"verdict": VERDICT_UNAVAILABLE, "faces": 0, "reason": str(e)}
        if not crops:
            return {"verdict": VERDICT_NO_FACE, "faces": 0}
        # classify each face; any non-owner face -> UNKNOWN (intruder)
        unknown = 0
        owner_matches = 0
        distances = []
        for crop in crops:
            desc = self._descriptor(crop)
            if desc is None:
                continue
            d = self._distance(desc["vec"], self._owner_desc["vec"])
            distances.append(d)
            if d <= self._owner_desc.get("threshold", self.threshold):
                owner_matches += 1
            else:
                unknown += 1
        faces = len(crops)
        if unknown > 0:
            verdict = VERDICT_UNKNOWN
        else:
            verdict = VERDICT_OWNER
        return {
            "verdict": verdict,
            "faces": faces,
            "owner_matches": owner_matches,
            "unknown_faces": unknown,
            "distances": [round(d, 4) for d in distances],
            "threshold": self._owner_desc.get("threshold", self.threshold),
        }

    def stats(self) -> Dict[str, Any]:
        return {
            "enrolled": self.enrolled,
            "owner_path": str(self.owner_path),
            "threshold": self.threshold,
        }


def get_face_auth(**kwargs) -> FaceAuth:
    return FaceAuth(**kwargs)
