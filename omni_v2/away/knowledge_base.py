"""
OMNI KNOWLEDGE BASE - a file/url/folder corpus backed by HybridMemory.

Lets OMNI learn a knowledge base locally:
  omni kb add some_document.txt
  omni kb add https://somepage.example/article
  omni kb add ./docs                     # whole folder
  omni kb query "how do I deploy the api"
  omni kb search "authentication"

Every chunk added goes through HybridMemory so it gets BOTH:
  - a long-term RAG embedding (deep recall later)
  - a short-term CAG hot-cache entry (fast recall now)
Fully offline. No API. Files stay in data/kb/.
"""
from __future__ import annotations
import json
import re
import hashlib
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KnowledgeBase")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

try:
    from omni_v2.memory.hybrid_memory import HybridMemory, get_hybrid_memory
except Exception:  # pragma: no cover - fallback for standalone import
    from omni_v2.memory.hybrid_memory import HybridMemory, get_hybrid_memory

# Readable text extensions we ingest by default
TEXT_EXTS = {
    ".txt", ".md", ".rst", ".json", ".py", ".js", ".ts", ".html", ".htm",
    ".csv", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".sh", ".bat",
    ".sql", ".log",
}

CHUNK_SIZE = 700      # chars per chunk
CHUNK_OVERLAP = 120   # overlap between chunks to keep context continuity


class KnowledgeBase:
    """Ingest documents/folders/URLs into the hybrid memory and query them."""

    def __init__(self, memory: Optional[HybridMemory] = None):
        self.memory = memory or get_hybrid_memory()
        self.source_index_path = DATA_DIR / "kb" / "sources.json"
        self.source_index_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._sources: Dict[str, Dict[str, Any]] = self._load_sources()

    # -- chunking ----------------------------------------------------------
    @staticmethod
    def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
        """Split text into overlapping chunks at paragraph/word boundaries."""
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) <= size:
            return [text] if text else []
        chunks: List[str] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(start + size, n)
            # prefer a sentence boundary near the end of the chunk
            if end < n:
                cut = text.rfind(". ", start + size // 2, end)
                if cut != -1:
                    end = cut + 1
            chunks.append(text[start:end].strip())
            if end >= n:
                break
            start = max(end - overlap, start + 1)
        return [c for c in chunks if c]

    # -- ingestion -----------------------------------------------------------
    def add_text(self, text: str, source: str = "paste", title: str = "") -> int:
        """Ingest raw text (chunked) into hybrid memory. Returns chunk count."""
        chunks = self.chunk_text(text)
        added = 0
        for i, c in enumerate(chunks, 1):
            self.memory.remember(
                text=c,
                kind="document",
                source=source,
                title=f"{title or source} #{i}",
                importance=0.6,
                hot=True,
            )
            added += 1
        self._record_source(source, title=title, n_chunks=added)
        logger.info(f"KB: ingested {added} chunk(s) from {source}")
        return added

    def add_file(self, path: str, title: str = "") -> int:
        """Read and ingest a local file (or any readable text)."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"file not found: {p}")
        if p.is_dir():
            return self.add_directory(str(p), title=title)
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ValueError(f"cannot read {p}: {e}") from e
        if not raw.strip():
            logger.warning(f"KB: {p} is empty, skipping")
            return 0
        return self.add_text(raw, source=str(p), title=title or p.name)

    def add_directory(self, folder: str, title: str = "", recursive: bool = True) -> int:
        """Ingest every readable text file in a folder (recursive by default)."""
        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError(f"folder not found: {folder_path}")
        files = sorted(
            (folder_path.rglob("*") if recursive else folder_path.glob("*"))
        )
        total = 0
        for f in files:
            if not f.is_file():
                continue
            if f.suffix.lower() not in TEXT_EXTS:
                continue
            if any(part.startswith(".") for part in f.parts):
                continue  # skip hidden dirs
            try:
                total += self.add_file(str(f), title=title)
            except Exception as e:
                logger.warning(f"KB: skipped {f}: {e}")
        logger.info(f"KB: ingested {total} chunks from folder {folder}")
        return total

    def add_url(self, url: str, title: str = "") -> int:
        """Fetch and ingest a web page (offline-safe: urllib, strips HTML)."""
        from urllib.request import Request, urlopen
        req = Request(url, headers={"User-Agent": "Omni-Local-KB/1.0"})
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            raise ValueError(f"cannot fetch {url}: {e}") from e
        text = _html_to_text(raw)
        if not text.strip():
            raise ValueError(f"no readable text at {url}")
        return self.add_text(text, source=url, title=title or url)

    # -- query -------------------------------------------------------------
    def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """Ask the knowledge base. Returns fused RAG+CAG context + raw hits."""
        hits = self.memory.retrieve(question, k=k)
        return {
            "question": question,
            "context": self.memory.build_context(question, k=k),
            "hits": [h.to_dict() for h in hits],
            "hit_count": len(hits),
        }

    def search(self, term: str, k: int = 10) -> List[Dict[str, Any]]:
        """Simple keyword search across stored items (for CLI `kb search`)."""
        tl = term.lower()
        results = []
        for it in self.memory._items.values():  # noqa: SLF001 - intentional internal read
            if tl in it.text.lower() or tl in it.title.lower():
                results.append(it.to_dict())
        return results[:k]

    # -- sources index -------------------------------------------------------
    def _load_sources(self) -> Dict[str, Dict[str, Any]]:
        try:
            if self.source_index_path.exists():
                with open(self.source_index_path) as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _record_source(self, source: str, title: str = "", n_chunks: int = 0) -> None:
        with self._lock:
            key = hashlib.sha256(source.encode()).hexdigest()[:12]
            prev = self._sources.get(key, {"source": source, "n_chunks": 0})
            prev["source"] = source
            prev["title"] = title or prev.get("title", "")
            prev["n_chunks"] = prev.get("n_chunks", 0) + n_chunks
            self._sources[key] = prev
            try:
                with open(self.source_index_path, "w") as f:
                    json.dump(self._sources, f, indent=2)
            except Exception as e:
                logger.warning(f"KB: source index save failed: {e}")

    def list_sources(self) -> List[Dict[str, Any]]:
        return list(self._sources.values())

    def stats(self) -> Dict[str, Any]:
        return {
            "memory": self.memory.stats(),
            "sources": len(self._sources),
        }


def _html_to_text(html: str) -> str:
    """Crude but dependency-free HTML -> plain text."""
    # strip scripts/styles
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    # drop tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_knowledge_base(memory: Optional[HybridMemory] = None) -> KnowledgeBase:
    return KnowledgeBase(memory=memory)
