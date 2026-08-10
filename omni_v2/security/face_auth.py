"""
OMNI FACE AUTH - local camera-based user verification (Phase 8 security).

Purpose: confirm "is it me at the laptop?" when OMNI is in away/guard mode.

This is the **hardened** version that addresses the "basic biometrics" caveat.
It now uses a pluggable verifier backend, in priority order:

  1. LBPH  (OpenCV contrib, `cv2.face.LBPHFaceRecognizer`)
     A *trained* local recognizer: you enroll several images of your face and
     it learns a model. At verification time it scores the live face against
     that model. Fully offline, no model download. Reliably rejects a clearly
     different person under good lighting/angle. << DEFAULT when available
  2. Gradient + color descriptor (zero-dep fallback)
     The original lightweight descriptor, kept as a graceful fallback when
     OpenCV contrib is unavailable.
  3. Deep embeddings (optional, via `face_recognition`/dlib)
     If dlib is installed you get state-of-the-art accuracy. It auto-activates;
     otherwise OMNI falls back gracefully.

Robustness upgrades (the actual caveat-fixes):
  * MULTI-SAMPLE ENROLLMENT - you enroll several frames; all become the model,
    so a single bad frame can't break your enrollment.
  * Per-backend, calibratable thresholds.
  * LBPH confidence (lower = closer) is used to classify owner vs unknown.
  * The `verify()` interface is unchanged, so the desktop app / CLI / guard
    monitor keep working regardless of which backend is active.

Storage:
  - data/security/owner.json   -> metadata (backend, threshold, enrolled_at, n)
  - data/security/owner_model.xml -> serialized LBPH model (if LBPH backend)
Fully local & offline. All heavy imports are lazy.
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
MODEL_PATH = SECURITY_DIR / "owner_model.xml"
CASCADE_NAME = "haarcascade_frontalface_default.xml"

# Verdict types
VERDICT_OWNER = "owner"
VERDICT_UNKNOWN = "unknown"
VERDICT_NO_FACE = "no_face"
VERDICT_UNAVAILABLE = "unavailable"


def _lazy_cv():
    import cv2  # noqa: PLC0415 - lazy, optional
    return cv2


def _lazy_np():
    import numpy as np  # noqa: PLC0415
    return np


# ---------------------------------------------------------------------------
# Verifier backends
# ---------------------------------------------------------------------------
class BaseVerifier:
    """A verifier scores face crops; LOWER score = closer to owner."""

    name = "base"
    default_threshold = 0.30

    def __init__(self, threshold: Optional[float] = None):
        self.threshold = self.default_threshold if threshold is None else threshold
        self.enrolled = False

    # -- persistence ----------------------------------------------------
    def to_meta(self) -> Dict[str, Any]:
        return {"backend": self.name, "threshold": self.threshold, "enrolled": self.enrolled}

    def load_meta(self, meta: Dict[str, Any]) -> None:
        self.threshold = meta.get("threshold", self.default_threshold)
        self.enrolled = meta.get("enrolled", False)

    # -- interface ------------------------------------------------------
    def enroll(self, crops: List[Any]) -> int:
        raise NotImplementedError

    def score(self, crop: Any) -> Optional[float]:
        raise NotImplementedError

    def save(self, model_path: Path) -> None:
        raise NotImplementedError

    def load(self, model_path: Path, meta: Dict[str, Any]) -> None:
        raise NotImplementedError


class GradientVerifier(BaseVerifier):
    """Fallback: gradient-magnitude + HSV histogram descriptor, cosine distance."""

    name = "gradient"
    default_threshold = 0.30

    def __init__(self, threshold: Optional[float] = None):
        super().__init__(threshold)
        self._ref_vec: Optional[List[float]] = None
        self._ref_n: int = 0

    @staticmethod
    def _descriptor(crop_bgr: Any) -> Optional[Dict[str, Any]]:
        try:
            cv2 = _lazy_cv()
            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (48, 48))
            gx = cv2.Sobel(resized, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(resized, cv2.CV_32F, 0, 1, ksize=3)
            mag = cv2.magnitude(gx, gy).flatten()
            hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
            desc = list(mag.astype(float) / (mag.max() + 1e-6)) + list(hist / (hist.sum() + 1e-6))
            norm = math.sqrt(sum(v * v for v in desc)) or 1.0
            return {"vec": [float(v) / norm for v in desc], "n": len(desc)}
        except Exception:
            return None

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    def enroll(self, crops: List[Any]) -> int:
        # average the descriptors of all samples for robustness
        vecs = []
        for c in crops:
            d = self._descriptor(c)
            if d:
                vecs.append(d["vec"])
        if not vecs:
            raise ValueError("no usable face crop for enrollment")
        n = len(vecs[0])
        avg = [sum(v[i] for v in vecs) / len(vecs) for i in range(n)]
        norm = math.sqrt(sum(x * x for x in avg)) or 1.0
        self._ref_vec = [float(x) / norm for x in avg]
        self._ref_n = len(vecs)
        self.enrolled = True
        return len(vecs)

    def score(self, crop: Any) -> Optional[float]:
        if self._ref_vec is None:
            return None
        d = self._descriptor(crop)
        if d is None:
            return None
        return 1.0 - self._cosine(d["vec"], self._ref_vec)

    def to_meta(self) -> Dict[str, Any]:
        m = super().to_meta()
        m["ref_vec"] = self._ref_vec
        m["samples"] = self._ref_n
        return m

    def load_meta(self, meta: Dict[str, Any]) -> None:
        super().load_meta(meta)
        self._ref_vec = meta.get("ref_vec")
        self._ref_n = meta.get("samples", 0)

    def save(self, model_path: Path) -> None:
        pass  # descriptor lives in owner.json

    def load(self, model_path: Path, meta: Dict[str, Any]) -> None:
        self.load_meta(meta)


class LBPHVerifier(BaseVerifier):
    """Trained local recognizer (OpenCV contrib). LOWER confidence = closer."""

    name = "lbph"
    default_threshold = 80.0

    def __init__(self, threshold: Optional[float] = None):
        super().__init__(threshold)
        self._model = None
        self._n_samples = 0

    def _get_model(self):
        if self._model is None:
            cv2 = _lazy_cv()
            if not hasattr(cv2, "face"):
                raise RuntimeError("cv2.face (opencv-contrib) not available")
            self._model = cv2.face.LBPHFaceRecognizer_create()
        return self._model

    def enroll(self, crops: List[Any]) -> int:
        np = _lazy_np()
        model = self._get_model()
        samples = []
        labels = []
        for c in crops:
            gray = self._to_gray(c)
            if gray is None:
                continue
            samples.append(gray)
            labels.append(0)
        if not samples:
            raise ValueError("no usable face crop for enrollment")
        model.train(samples, np.array(labels))
        self._n_samples = len(samples)
        self.enrolled = True
        return len(samples)

    @staticmethod
    def _to_gray(crop: Any):
        cv2 = _lazy_cv()
        try:
            if crop.ndim == 3:
                return cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            return crop
        except Exception:
            return None

    def score(self, crop: Any) -> Optional[float]:
        if not self.enrolled:
            return None
        try:
            gray = self._to_gray(crop)
            if gray is None:
                return None
            _, conf = self._model.predict(gray)
            return float(conf)
        except Exception:
            return None

    def to_meta(self) -> Dict[str, Any]:
        m = super().to_meta()
        m["samples"] = self._n_samples
        return m

    def load_meta(self, meta: Dict[str, Any]) -> None:
        super().load_meta(meta)
        self._n_samples = meta.get("samples", 0)

    def save(self, model_path: Path) -> None:
        if self._model is not None and self.enrolled:
            model_path.write_bytes(b"")
            self._model.write(str(model_path))

    def load(self, model_path: Path, meta: Dict[str, Any]) -> None:
        try:
            if model_path.exists() and model_path.stat().st_size > 0:
                model = self._get_model()
                model.read(str(model_path))
                self._model = model
                self.enrolled = meta.get("enrolled", False)
                self._n_samples = meta.get("samples", 0)
        except Exception as e:
            logger.warning(f"LBPH model load failed: {e}")


class DeepVerifier(BaseVerifier):
    """
    Optional state-of-the-art backend via `face_recognition` (dlib).
    Auto-selected only if dlib is importable; otherwise gracefully skipped.
    """

    name = "deep"
    default_threshold = 0.50  # typical face_recognition tolerance ~0.6; keep tight

    def __init__(self, threshold: Optional[float] = None):
        super().__init__(threshold)
        self._encodings: List[Any] = []
        self._fr = None

    @property
    def available(self) -> bool:
        if self._fr is None:
            try:
                import face_recognition  # noqa: PLC0415
                self._fr = face_recognition
            except Exception:
                return False
        return True

    def enroll(self, crops: List[Any]) -> int:
        if not self.available:
            raise RuntimeError("dlib/face_recognition not installed")
        encs = []
        for c in crops:
            try:
                locs = self._fr.face_locations(c, model="hog")
                if not locs:
                    continue
                enc = self._fr.face_encodings(c, known_face_locations=locs)
                if enc:
                    encs.append(enc[0])
            except Exception:
                continue
        if not encs:
            raise ValueError("no detectable face in enrollment frames")
        self._encodings = encs
        self.enrolled = True
        return len(encs)

    def score(self, crop: Any) -> Optional[float]:
        if not self.enrolled or not self.available:
            return None
        try:
            locs = self._fr.face_locations(crop, model="hog")
            if not locs:
                return None
            enc = self._fr.face_encodings(crop, known_face_locations=locs)
            if not enc:
                return None
            dists = self._fr.face_distance(self._encodings, enc[0])
            return float(min(dists))
        except Exception:
            return None

    def to_meta(self) -> Dict[str, Any]:
        m = super().to_meta()
        m["samples"] = len(self._encodings)
        return m

    def save(self, model_path: Path) -> None:
        pass  # encodings not persisted (would require pickling numpy); re-enroll

    def load(self, model_path: Path, meta: Dict[str, Any]) -> None:
        # deep encodings aren't persisted; require re-enrollment
        self.enrolled = False


def _pick_verifier() -> BaseVerifier:
    """Select the best available verifier: deep > lbph > gradient."""
    deep = DeepVerifier()
    if deep.available:
        return deep
    try:
        cv2 = _lazy_cv()
        if hasattr(cv2, "face"):
            return LBPHVerifier()
    except Exception:
        pass
    return GradientVerifier()


# ---------------------------------------------------------------------------
# FaceAuth orchestrator
# ---------------------------------------------------------------------------
class FaceAuth:
    """Enroll an owner and verify camera frames against that identity."""

    def __init__(self, owner_path: Optional[Path] = None, model_path: Optional[Path] = None,
                 threshold: Optional[float] = None, verifier: Optional[BaseVerifier] = None):
        self.owner_path = Path(owner_path) if owner_path else OWNER_PATH
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self._lock = threading.RLock()
        self._verifier = verifier if verifier is not None else _pick_verifier()
        if threshold is not None:
            self._verifier.threshold = threshold
        self._cascade = None
        self._camera = None
        self._meta: Dict[str, Any] = {}
        self._load()

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
        """Enroll the owner from a single frame (uses ALL detected faces as samples)."""
        crops = self._face_crops(frame)
        if not crops:
            raise ValueError("no face detected in frame; cannot enroll")
        return self.enroll_crops(crops)

    def enroll_crops(self, crops: List[Any]) -> Dict[str, Any]:
        """Multi-sample enrollment from pre-extracted face crops."""
        with self._lock:
            n = self._verifier.enroll(crops)
            self._meta = self._verifier.to_meta()
            self._meta["enrolled_at"] = time.time()
            self._verifier.save(self.model_path)
            self._save_meta()
            return {"enrolled": True, "backend": self._verifier.name, "samples": n, "faces": len(crops)}

    def enroll_from_camera(self, frames: int = 5, delay: float = 0.2,
                           index: int = 0) -> Dict[str, Any]:
        """Capture `frames` camera frames and enroll the owner from all faces."""
        if not self.open_camera(index):
            raise RuntimeError("no camera found")
        import time as _t
        all_crops: List[Any] = []
        try:
            for _ in range(frames):
                f = self.capture_frame()
                if f is not None:
                    all_crops.extend(self._face_crops(f))
                _t.sleep(delay)
        finally:
            self.close_camera()
        if not all_crops:
            raise ValueError("no face detected across frames; cannot enroll")
        return self.enroll_crops(all_crops)

    def _save_meta(self) -> None:
        SECURITY_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.owner_path.write_text(json.dumps(self._meta, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"owner meta save failed: {e}")

    def _load(self) -> None:
        try:
            if self.owner_path.exists():
                self._meta = json.loads(self.owner_path.read_text(encoding="utf-8"))
                backend = self._meta.get("backend", self._verifier.name)
                if backend != self._verifier.name:
                    # rebuild the correct verifier for the stored backend
                    self._verifier = {"deep": DeepVerifier, "lbph": LBPHVerifier,
                                      "gradient": GradientVerifier}.get(
                        backend, _pick_verifier)()
                self._verifier.load_meta(self._meta)
                self._verifier.load(self.model_path, self._meta)
        except Exception as e:
            logger.warning(f"FaceAuth load failed: {e}")
            self._verifier = _pick_verifier()

    @property
    def enrolled(self) -> bool:
        return self._verifier.enrolled

    @property
    def backend(self) -> str:
        return self._verifier.name

    @property
    def threshold(self) -> float:
        return self._verifier.threshold

    # -- verification ----------------------------------------------------------
    def verify_crops(self, crops: List[Any]) -> Dict[str, Any]:
        """Pure verification against pre-extracted face crops (no camera/Haar)."""
        if not self.enrolled:
            return {"verdict": VERDICT_UNAVAILABLE, "faces": 0, "reason": "not_enrolled"}
        if not crops:
            return {"verdict": VERDICT_NO_FACE, "faces": 0}
        owner_matches = 0
        unknown = 0
        distances = []
        for crop in crops:
            s = self._verifier.score(crop)
            if s is None:
                continue
            distances.append(round(s, 4))
            if s <= self._verifier.threshold:
                owner_matches += 1
            else:
                unknown += 1
        faces = len(crops)
        verdict = VERDICT_UNKNOWN if unknown > 0 else VERDICT_OWNER
        return {
            "verdict": verdict,
            "faces": faces,
            "owner_matches": owner_matches,
            "unknown_faces": unknown,
            "distances": distances,
            "threshold": self._verifier.threshold,
            "backend": self._verifier.name,
        }

    def verify(self, frame: Any) -> Dict[str, Any]:
        """Verdict on a camera frame. Returns {verdict, faces, distance, ...}."""
        if not self.enrolled:
            return {"verdict": VERDICT_UNAVAILABLE, "faces": 0, "reason": "not_enrolled"}
        try:
            crops = self._face_crops(frame)
        except Exception as e:
            return {"verdict": VERDICT_UNAVAILABLE, "faces": 0, "reason": str(e)}
        if not crops:
            return {"verdict": VERDICT_NO_FACE, "faces": 0}
        return self.verify_crops(crops)

    def stats(self) -> Dict[str, Any]:
        return {
            "enrolled": self.enrolled,
            "backend": self.backend,
            "threshold": self.threshold,
            "owner_path": str(self.owner_path),
            "samples": self._meta.get("samples", 0),
        }


def get_face_auth(**kwargs) -> FaceAuth:
    return FaceAuth(**kwargs)
