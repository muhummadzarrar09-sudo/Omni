"""
OMNI V3 - Multi-modal Vision (Phase 4A: "It Sees")

Drag a screenshot, PDF, or image into OMNI → it explains what's there.
"OMNI, what does this say?" → reads the text.
"OMNI, summarize this PDF" → does it.
"OMNI, what's in this image?" → describes it.

Uses local vision models (no cloud):
  - Moondream2 (1.9B) for image understanding
  - Tesseract for OCR (text extraction)
  - PIL for image preprocessing
  - pdfplumber for PDF text extraction
"""
from __future__ import annotations
import io
import base64
import threading
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("MultimodalVision")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass
class VisionResult:
    """Result of a vision operation."""
    success: bool
    file_type: str  # "image" | "pdf" | "screenshot"
    description: str = ""
    extracted_text: str = ""
    objects_detected: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    model_used: str = ""
    error: str = ""


class MultimodalVision:
    """
    Local multi-modal vision. No cloud.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.uploads_dir = DATA_DIR / "vision" / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._moondream = None
        self._tesseract = None
        self._pdfplumber = None
        self._lock_obj = threading.RLock()
        self._initialized = True
        self._check_dependencies()
        logger.info(f"👁️ MultimodalVision initialized (uploads: {self.uploads_dir})")

    def _check_dependencies(self):
        """Check which vision dependencies are available."""
        # Moondream2
        try:
            from transformers import AutoModelForCausalLM
            from transformers import AutoProcessor
            # Don't load yet, just check
            self._moondream = "available"
            logger.info("✅ transformers available (Moondream2 ready)")
        except ImportError:
            logger.debug("transformers not installed - image description limited")
        # Tesseract
        try:
            import pytesseract
            # Check if tesseract binary is installed
            try:
                pytesseract.get_tesseract_version()
                self._tesseract = "available"
                logger.info("✅ pytesseract + tesseract binary available")
            except Exception as e:
                logger.debug(f"tesseract binary not found: {e}")
        except ImportError:
            logger.debug("pytesseract not installed")
        # PDF
        try:
            import pdfplumber
            self._pdfplumber = "available"
            logger.info("✅ pdfplumber available")
        except ImportError:
            logger.debug("pdfplumber not installed")

    def process_file(self, file_path: str, query: str = "Describe this") -> VisionResult:
        """
        Process a file (image, PDF, or screenshot) and respond to a query.

        Args:
            file_path: Path to the file
            query: What the user wants to know (default: "Describe this")

        Returns:
            VisionResult with description, text, objects, etc.
        """
        t0 = time.time()
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return VisionResult(
                success=False, file_type="unknown",
                error=f"File not found: {file_path}"
            )
        suffix = path.suffix.lower()
        if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            return self._process_image(path, query, t0)
        elif suffix == ".pdf":
            return self._process_pdf(path, query, t0)
        elif suffix in (".txt", ".md", ".log"):
            return self._process_text(path, query, t0)
        else:
            return VisionResult(
                success=False, file_type=suffix.lstrip("."),
                error=f"Unsupported file type: {suffix}"
            )

    def process_bytes(self, data: bytes, filename: str, query: str = "Describe this") -> VisionResult:
        """Process file data from bytes (e.g. upload)."""
        t0 = time.time()
        # Save to uploads dir
        safe_name = filename.replace("/", "_").replace("\\", "_")
        upload_path = self.uploads_dir / f"{int(time.time()*1000)}_{safe_name}"
        try:
            upload_path.write_bytes(data)
        except Exception as e:
            return VisionResult(
                success=False, file_type="unknown",
                error=f"Failed to save: {e}"
            )
        result = self.process_file(str(upload_path), query)
        return result

    def process_screenshot(self, query: str = "What's on my screen?") -> VisionResult:
        """Capture and analyze the current screen."""
        t0 = time.time()
        try:
            import mss
            with mss.mss() as sct:
                # Capture primary monitor
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                # Save
                path = self.uploads_dir / f"screen_{int(time.time()*1000)}.png"
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                img.save(str(path))
            return self._process_image(path, query, t0, file_type="screenshot")
        except ImportError:
            return VisionResult(
                success=False, file_type="screenshot",
                error="mss not installed. Run: pip install mss"
            )
        except Exception as e:
            return VisionResult(
                success=False, file_type="screenshot",
                error=f"Screenshot failed: {e}"
            )

    def _process_image(self, path: Path, query: str, t0: float, file_type: str = "image") -> VisionResult:
        """Process an image file."""
        result = VisionResult(success=True, file_type=file_type)
        # Try OCR first (fast, deterministic)
        if self._tesseract:
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(path)
                text = pytesseract.image_to_string(img)
                result.extracted_text = text.strip()
                if result.extracted_text:
                    result.metadata["ocr_chars"] = len(result.extracted_text)
                    result.model_used = "tesseract"
            except Exception as e:
                logger.debug(f"OCR: {e}")
        # Try Moondream2 for description
        if self._moondream:
            try:
                from PIL import Image
                img = Image.open(path)
                description = self._describe_with_moondream(img, query)
                if description:
                    result.description = description
                    if not result.model_used:
                        result.model_used = "moondream2"
                    else:
                        result.model_used = f"{result.model_used}+moondream2"
            except Exception as e:
                logger.debug(f"Moondream: {e}")
        # Fallback: just metadata
        if not result.description and not result.extracted_text:
            try:
                from PIL import Image
                img = Image.open(path)
                result.description = f"Image: {path.name} ({img.size[0]}x{img.size[1]} {img.mode})"
                result.metadata["size"] = img.size
                result.metadata["mode"] = img.mode
                result.model_used = "metadata"
            except Exception as e:
                result.error = f"Failed to read image: {e}"
                result.success = False
        result.duration_ms = (time.time() - t0) * 1000
        return result

    def _describe_with_moondream(self, image, query: str) -> str:
        """Use Moondream2 to describe the image."""
        try:
            from transformers import AutoModelForCausalLM, AutoProcessor
            from PIL import Image
            # Lazy load (heavy)
            if not hasattr(self, '_md_model'):
                self._md_model = None
            if self._md_model is None:
                logger.info("Loading Moondream2 (one-time, ~1GB)...")
                self._md_model_id = "vikhyatk/moondream2"
                self._md_model = AutoModelForCausalLM.from_pretrained(
                    self._md_model_id,
                    trust_remote_code=True,
                    torch_dtype="auto",
                ).to("cpu")  # CPU for compatibility
                self._md_processor = AutoProcessor.from_pretrained(
                    self._md_model_id, trust_remote_code=True
                )
            # Encode image
            enc_image = self._md_model.encode_image(image)
            # Generate
            result = self._md_model.answer_question(
                enc_image, query, self._md_processor
            )
            return result
        except Exception as e:
            logger.debug(f"Moondream2: {e}")
            return ""

    def _process_pdf(self, path: Path, query: str, t0: float) -> VisionResult:
        """Process a PDF file."""
        result = VisionResult(success=True, file_type="pdf")
        if self._pdfplumber:
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    pages_text = []
                    metadata = {"pages": len(pdf.pages)}
                    for i, page in enumerate(pdf.pages[:50]):  # cap at 50 pages
                        text = page.extract_text() or ""
                        if text.strip():
                            pages_text.append(f"--- Page {i+1} ---\n{text}")
                    result.extracted_text = "\n\n".join(pages_text)
                    result.metadata = metadata
                    result.model_used = "pdfplumber"
            except Exception as e:
                result.error = f"PDF parse: {e}"
                result.success = False
        else:
            # Fallback: try raw bytes
            try:
                raw = path.read_bytes()
                result.extracted_text = raw.decode("utf-8", errors="replace")[:50000]
                result.model_used = "raw"
            except Exception as e:
                result.error = f"PDF read: {e}"
                result.success = False
        # Generate a summary
        if result.extracted_text and query:
            summary = self._summarize_text(result.extracted_text, query)
            if summary:
                result.description = summary
        result.duration_ms = (time.time() - t0) * 1000
        return result

    def _process_text(self, path: Path, query: str, t0: float) -> VisionResult:
        """Process a text file."""
        result = VisionResult(success=True, file_type="text")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            result.extracted_text = text[:50000]
            result.metadata = {"chars": len(text), "lines": text.count("\n")}
            result.model_used = "raw"
        except Exception as e:
            result.error = f"Text read: {e}"
            result.success = False
        if result.extracted_text and query:
            summary = self._summarize_text(result.extracted_text, query)
            if summary:
                result.description = summary
        result.duration_ms = (time.time() - t0) * 1000
        return result

    def _summarize_text(self, text: str, query: str) -> str:
        """Summarize text using brain if available, else truncate."""
        # Cap text for processing
        if len(text) > 8000:
            text = text[:8000] + "..."
        try:
            from omni_v2.llm.brain import get_brain
            brain = get_brain()
            if brain and brain.model_loaded:
                prompt = f'Based on this content, answer: "{query}"\n\nContent:\n{text}\n\nAnswer:'
                resp = brain.think(prompt, stream=False)
                if resp.text:
                    return resp.text[:1000]
        except Exception as e:
            logger.debug(f"Brain summarize: {e}")
        # Fallback: return first 500 chars
        return f"({len(text)} chars) {text[:500]}..."

    def get_status(self) -> Dict[str, Any]:
        return {
            "moondream2": bool(self._moondream),
            "tesseract": bool(self._tesseract),
            "pdfplumber": bool(self._pdfplumber),
            "uploads_dir": str(self.uploads_dir),
            "uploads_count": len(list(self.uploads_dir.glob("*"))) if self.uploads_dir.exists() else 0,
        }


def get_vision() -> MultimodalVision:
    return MultimodalVision()
