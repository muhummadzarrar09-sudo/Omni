"""Face Auth V2 - Phase 3 - Biometric Security"""
import os
from pathlib import Path
from typing import Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("FaceAuthV2")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"

class FaceAuth:
    """Face recognition biometric - local, privacy-first"""

    def __init__(self):
        self.face_db_dir = DATA_DIR / "faces"
        self.face_db_dir.mkdir(parents=True, exist_ok=True)
        self.face_recognition_available = False
        self._init_face_recognition()
        logger.info(f"FaceAuth V2 - DB: {self.face_db_dir}, Available: {self.face_recognition_available}")

    def _init_face_recognition(self):
        try:
            import face_recognition
            self.face_recognition_available = True
            logger.info("Face recognition available - biometric security enabled")
        except ImportError:
            logger.warning("face_recognition not installed - pip install face_recognition (needs dlib) - using mock")
            self.face_recognition_available = False
        except Exception as e:
            logger.warning(f"Face recognition init failed: {e} - using mock")
            self.face_recognition_available = False

    def enroll(self, name: str, image_path: Optional[Path] = None) -> bool:
        """Enroll a face - capture from webcam or use image"""
        if not self.face_recognition_available:
            # Mock enroll
            mock_file = self.face_db_dir / f"{name}.txt"
            mock_file.write_text(f"Mock face data for {name}")
            logger.info(f"Mock enrolled face for {name}")
            return True

        try:
            # Real face recognition
            import face_recognition
            import cv2

            if image_path and Path(image_path).exists():
                image = face_recognition.load_image_file(str(image_path))
            else:
                # Capture from webcam
                cap = cv2.VideoCapture(0)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    logger.error("Failed to capture from webcam")
                    return False
                # Convert BGR to RGB
                image = frame[:, :, ::-1]

            encodings = face_recognition.face_encodings(image)
            if not encodings:
                logger.warning("No face found in image")
                return False

            # Save encoding
            import pickle
            encoding_file = self.face_db_dir / f"{name}.pkl"
            with open(encoding_file, 'wb') as f:
                pickle.dump(encodings[0], f)

            logger.info(f"Enrolled face for {name} -> {encoding_file}")
            return True

        except Exception as e:
            logger.error(f"Face enroll failed: {e}")
            return False

    def recognize(self, image_path: Optional[Path] = None) -> Optional[str]:
        """Recognize face - returns name or None"""
        if not self.face_recognition_available:
            # Mock - check if any enrolled faces exist
            faces = list(self.face_db_dir.glob("*.txt")) + list(self.face_db_dir.glob("*.pkl"))
            if faces:
                # Return first mock face name
                name = faces[0].stem
                logger.info(f"Mock recognized: {name}")
                return name
            return None

        try:
            import face_recognition
            import cv2
            import pickle

            # Load unknown image
            if image_path and Path(image_path).exists():
                unknown_image = face_recognition.load_image_file(str(image_path))
            else:
                cap = cv2.VideoCapture(0)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    return None
                unknown_image = frame[:, :, ::-1]

            unknown_encodings = face_recognition.face_encodings(unknown_image)
            if not unknown_encodings:
                return None

            unknown_encoding = unknown_encodings[0]

            # Compare with known faces
            for encoding_file in self.face_db_dir.glob("*.pkl"):
                try:
                    with open(encoding_file, 'rb') as f:
                        known_encoding = pickle.load(f)

                    results = face_recognition.compare_faces([known_encoding], unknown_encoding, tolerance=0.6)
                    if results[0]:
                        name = encoding_file.stem
                        logger.info(f"Recognized: {name}")
                        return name
                except Exception as e:
                    logger.debug(f"Compare failed for {encoding_file}: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"Face recognize failed: {e}")
            return None

    def list_enrolled(self):
        return [f.stem for f in self.face_db_dir.glob("*.pkl")] + [f.stem for f in self.face_db_dir.glob("*.txt")]

if __name__ == "__main__":
    auth = FaceAuth()
    print(f"Enrolled faces: {auth.list_enrolled()}")
    print("Testing recognition (mock if no face_recognition)...")
    name = auth.recognize()
    print(f"Recognized: {name}")
