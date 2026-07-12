"""Screen Capture V2 - Phase 3 Started - Fast mss + OpenCV"""
from pathlib import Path
from typing import Tuple, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ScreenV2")

try:
    from omni_v2.core.paths import SCREENSHOTS_DIR
except ImportError:
    SCREENSHOTS_DIR = Path.home() / ".omni_v2" / "screenshots"

class ScreenCapture:
    """Fast screen capture via mss - Phase 3"""

    def __init__(self):
        self.backend = None
        self._init_backend()
        logger.info(f"ScreenCapture V2 - Backend: {self.backend}")

    def _init_backend(self):
        try:
            import mss
            self.backend = "mss"
            logger.info("Screen capture: mss (fast, 60fps)")
        except ImportError:
            try:
                from PIL import ImageGrab
                self.backend = "pil"
                logger.info("Screen capture: PIL ImageGrab (fallback)")
            except ImportError:
                self.backend = None
                logger.warning("No screen capture backend - pip install mss Pillow")

    def capture(self, monitor: int = 0):
        """Capture full screen"""
        if self.backend == "mss":
            try:
                import mss
                from PIL import Image
                with mss.mss() as sct:
                    mon = sct.monitors[monitor]
                    shot = sct.grab(mon)
                    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    return img
            except Exception as e:
                logger.error(f"mss capture failed: {e}")
        elif self.backend == "pil":
            try:
                from PIL import ImageGrab
                return ImageGrab.grab()
            except Exception as e:
                logger.error(f"PIL capture failed: {e}")
        return None

    def capture_and_save(self, path: Path = None):
        """Capture and save to screenshots dir"""
        img = self.capture()
        if img and path is None:
            from datetime import datetime
            path = SCREENSHOTS_DIR / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if img and path:
            try:
                img.save(str(path))
                logger.info(f"Screenshot saved to {path}")
                return path
            except Exception as e:
                logger.error(f"Save screenshot failed: {e}")
        return None

    def find_template(self, template_path: str) -> Optional[Tuple[int, int]]:
        """Find template image on screen via OpenCV - Phase 3 future"""
        # Phase 3: Mock, Phase 4: Real OpenCV template matching
        logger.info(f"Find template '{template_path}' - Phase 3 mock, Phase 4 OpenCV")
        return None

if __name__ == "__main__":
    cap = ScreenCapture()
    img = cap.capture()
    if img:
        print(f"Captured: {img.size}")
        path = cap.capture_and_save()
        print(f"Saved to: {path}")
    else:
        print("Capture failed")
