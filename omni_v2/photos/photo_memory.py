"""
OMNI PHOTO MEMORY (Phase 15, #3) — captions images into the knowledge base.

Makes photos/imagery part of OMNI's long-term memory: for each image it:
  1. Captions it via the vision module (Moondream2 etc.).
  2. Stores the caption as a RAG memory item (kind="image", source=<path>).
  3. Records metadata (path, size, timestamp) so you can ask
     "what did I take pictures of last month?"

Fully local; the captioner is pluggable so tests use a fake. Degrades gracefully
if the vision dependency (Moondream) isn't available.
"""
from __future__ import annotations
import time
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("PhotoMemory")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

PHOTO_INDEX = DATA_DIR / "brain" / "photo_memory.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


class PhotoMemory:
    """Captions images and stores them in the RAG memory + an index."""

    def __init__(self, memory=None, captioner: Optional[Callable[[str], str]] = None,
                 vision=None):
        self.memory = memory          # HybridMemory (optional)
        self.captioner = captioner    # captioner(image_path) -> str
        self.vision = vision          # MultimodalVision (optional)
        self.index_path = PHOTO_INDEX
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index: List[Dict[str, Any]] = []
        self._load_index()

    def _load_index(self) -> None:
        try:
            if self.index_path.exists():
                self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"photo index load failed: {e}")

    def _save_index(self) -> None:
        try:
            self.index_path.write_text(json.dumps(self._index, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"photo index save failed: {e}")

    def _default_captioner(self, image_path: str) -> str:
        if self.vision is not None:
            try:
                res = self.vision.process_file(image_path, query="Describe this image in detail")
                return getattr(res, "text", "") or getattr(res, "description", "") or ""
            except Exception as e:
                logger.warning(f"vision caption failed: {e}")
                return ""
        return ""

    def caption_image(self, image_path: str) -> Dict[str, Any]:
        """Caption one image and store it in memory + index."""
        p = Path(image_path)
        if not p.exists():
            return {"ok": False, "detail": f"no such file: {image_path}"}
        captioner = self.captioner or self._default_captioner
        caption = captioner(str(p))
        if not caption:
            caption = f"(no caption generated for {p.name})"
        entry = {
            "path": str(p), "name": p.name, "caption": caption,
            "ts": time.time(), "size": p.stat().st_size if p.exists() else 0,
        }
        self._index.append(entry)
        self._index = self._index[-2000:]
        self._save_index()
        # store in RAG memory for semantic recall
        if self.memory is not None:
            try:
                self.memory.remember(
                    f"Image '{p.name}': {caption}", kind="image",
                    source=str(p), title=p.name, importance=0.5)
            except Exception as e:
                logger.warning(f"photo memory store failed: {e}")
        return {"ok": True, "entry": entry}

    def caption_directory(self, folder: str, recursive: bool = True,
                          limit: int = 100) -> Dict[str, Any]:
        """Caption all images in a folder."""
        root = Path(folder)
        if not root.exists() or not root.is_dir():
            return {"ok": False, "detail": f"no such folder: {folder}"}
        files = (root.rglob("*") if recursive else root.glob("*"))
        images = [f for f in files if f.is_file() and f.suffix.lower() in IMAGE_EXTS][:limit]
        results = [self.caption_image(str(f)) for f in images]
        ok = sum(1 for r in results if r.get("ok"))
        return {"ok": True, "captioned": ok, "total": len(images)}

    def search(self, term: str) -> List[Dict[str, Any]]:
        """Find images whose caption mentions a term."""
        tl = term.lower()
        return [e for e in self._index if tl in e["caption"].lower()
                or tl in e["name"].lower()]

    def list_recent(self, n: int = 20) -> List[Dict[str, Any]]:
        return self._index[-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        return {"images_indexed": len(self._index), "path": str(self.index_path)}


def get_photo_memory(**kwargs) -> PhotoMemory:
    return PhotoMemory(**kwargs)
