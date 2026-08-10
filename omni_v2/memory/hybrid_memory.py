"""
OMNI HYBRID MEMORY - Long-term (RAG) + Short-term fast (CAG) fused.

Design goal (Away Mode / Knowledge Base):
  A knowledge base with BOTH:
    * LONG-TERM memory  -> RAG  (Retrieval-Augmented Generation)
        Persistent, semantic vector store over a large knowledge base.
        At query time we RETRIEVE the top-K relevant chunks and inject them.
    * SHORT/FAST memory  -> CAG (Cache-Augmented Generation)
        A pre-computed, always-injected context cache (pinned facts, ongoing
        tasks, the KB "index") that is in the prompt WITHOUT retrieval ->
        zero retrieval latency, deterministic, always present.

Why the mix:
  - RAG alone is slow (embedding + vector search every turn) and can miss
    tiny but vital facts unless they survive retrieval.
  - CAG alone cannot scale (you cannot dump the whole KB into the context).
  - The mix gives instant short-term answers (CAG hot cache + pinned context)
    AND deep long-term recall (RAG over the full corpus). This is the
    "LONG term / SHORT fast term memory" split.

Fully local: embeddings are computed with a zero-dependency sparse hashing
vectorizer (no model download, no network, no API). An optional real embedder
can be plugged in for better semantics; the default is pure offline TF-hash.

Persistence: everything lands under data/ via omni_v2.core.paths.
"""
from __future__ import annotations
import json
import re
import time
import math
import hashlib
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("HybridMemory")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

# ---------------------------------------------------------------------------
# Sparse hashing vectorizer (offline, deterministic, no deps)
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "i",
    "you", "we", "they", "he", "she", "have", "has", "had", "as", "at",
    "by", "from", "do", "does", "did", "will", "would", "can", "could",
    "should", "about", "into", "over", "not", "no", "yes", "but", "if",
    "then", "than", "so", "too", "very", "just", "also", "how", "what",
}


def _tokens(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def _hash_token(token: str, dim: int = 512) -> int:
    """Deterministic token->index via SHA-256 (no collision table needed)."""
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % dim


def sparse_embed(text: str, dim: int = 512) -> Dict[int, float]:
    """TF-weighted sparse vector as a dict {dim_index: weight}."""
    counts: Dict[str, int] = {}
    for t in _tokens(text):
        counts[t] = counts.get(t, 0) + 1
    vec: Dict[int, float] = {}
    for token, cnt in counts.items():
        idx = _hash_token(token, dim)
        # sqrt(TF) weighting, keeps magnitude stable for short/long text
        vec[idx] = vec.get(idx, 0.0) + (1.0 + math.log(cnt))
    return vec


def _normalize(vec: Dict[int, float]) -> Dict[int, float]:
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in vec.items()}


def cosine_sim(a: Dict[int, float], b: Dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = 0.0
    for k, v in a.items():
        if k in b:
            dot += v * b[k]
    return dot


class OptionalEmbedder:
    """Pluggable real embedder (e.g. sentence-transformers). Default: sparse hashing."""

    def __init__(self, embedder=None, dim: int = 512):
        self._embedder = embedder
        self._dim = dim

    def embed(self, text: str) -> Dict[int, float]:
        if self._embedder is not None:
            try:
                dense = self._embedder.encode(text)
                # project dense -> sparse-ish dict for a unified interface
                return {int(i): float(v) for i, v in enumerate(dense[:self._dim])}
            except Exception as e:
                logger.warning(f"Optional embedder failed ({e}), using sparse hash")
        return sparse_embed(text, self._dim)

    @property
    def dim(self) -> int:
        return self._dim


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------
@dataclass
class MemoryItem:
    """A single unit of stored knowledge (a chunk / fact / event)."""
    id: str
    text: str
    kind: str = "fact"            # fact | event | document | task | source
    source: str = ""              # file path, url, tool name, "user"
    title: str = ""
    importance: float = 0.5       # 0..1 - boosts retrieval & pinning
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MemoryItem":
        return MemoryItem(**d)


# ---------------------------------------------------------------------------
# The hybrid memory engine
# ---------------------------------------------------------------------------
class HybridMemory:
    """
    Long-term RAG store + short-term CAG cache, fused at query time.
    """

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        embedder=None,
        rag_top_k: int = 5,
        hot_cache_size: int = 40,
    ):
        self.persist_dir = Path(persist_dir) if persist_dir else (DATA_DIR / "kb")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.embedder = OptionalEmbedder(embedder)
        self.rag_top_k = rag_top_k
        self.hot_cache_size = hot_cache_size

        # ---- RAG layer: persistent long-term corpus ----
        self._items: Dict[str, MemoryItem] = {}
        self._vectors: Dict[str, Dict[int, float]] = {}  # id -> normalized vec

        # ---- CAG layer: always-injected context cache ----
        # hot_cache: most-recently-seen short-term items (bounded, in-memory)
        self._hot: "list[MemoryItem]" = []
        # pinned: persistent, always-injected context (user facts, KB index, tasks)
        self._pinned: Dict[str, str] = {}

        self._load()

    # -- persistence ------------------------------------------------------
    def _items_path(self) -> Path:
        return self.persist_dir / "longterm.json"

    def _pinned_path(self) -> Path:
        return self.persist_dir / "cag_pinned.json"

    def _save_items(self) -> None:
        try:
            with open(self._items_path(), "w") as f:
                json.dump([it.to_dict() for it in self._items.values()], f, indent=2)
        except Exception as e:
            logger.warning(f"HybridMemory save failed: {e}")

    def _save_pinned(self) -> None:
        try:
            with open(self._pinned_path(), "w") as f:
                json.dump(self._pinned, f, indent=2)
        except Exception as e:
            logger.warning(f"HybridMemory save pinned failed: {e}")

    def _load(self) -> None:
        try:
            if self._items_path().exists():
                with open(self._items_path()) as f:
                    for d in json.load(f):
                        it = MemoryItem.from_dict(d)
                        self._items[it.id] = it
                        self._vectors[it.id] = _normalize(self.embedder.embed(it.text))
        except Exception as e:
            logger.warning(f"HybridMemory load longterm failed: {e}")
        try:
            if self._pinned_path().exists():
                with open(self._pinned_path()) as f:
                    self._pinned = json.load(f)
        except Exception as e:
            logger.warning(f"HybridMemory load pinned failed: {e}")

    # -- RAG layer: write --------------------------------------------------
    def remember(
        self,
        text: str,
        kind: str = "fact",
        source: str = "",
        title: str = "",
        importance: float = 0.5,
        hot: bool = True,
    ) -> MemoryItem:
        """
        Store a piece of knowledge. Goes to BOTH:
          - RAG long-term corpus (persistent, retrievable)
          - CAG hot cache (short-term, fast) if hot=True
        """
        text = text.strip()
        if not text:
            raise ValueError("cannot remember empty text")
        with self._lock:
            item_id = hashlib.sha256((text + source + str(time.time())).encode()).hexdigest()[:16]
            item = MemoryItem(
                id=item_id,
                text=text,
                kind=kind,
                source=source,
                title=title or (text[:48]),
                importance=max(0.0, min(1.0, importance)),
            )
            self._items[item_id] = item
            self._vectors[item_id] = _normalize(self.embedder.embed(text))
            if hot:
                self._push_hot(item)
            self._save_items()
            return item

    def remember_many(self, items: List[Dict[str, Any]]) -> List[MemoryItem]:
        out = []
        with self._lock:
            for it in items:
                out.append(self.remember(hot=False, **it))
            self._save_items()
        return out

    def _push_hot(self, item: MemoryItem) -> None:
        self._hot.insert(0, item)
        if len(self._hot) > self.hot_cache_size:
            self._hot = self._hot[: self.hot_cache_size]

    # -- RAG layer: read ----------------------------------------------------
    def retrieve(self, query: str, k: Optional[int] = None, kind: Optional[str] = None) -> List[MemoryItem]:
        """Long-term semantic retrieval (RAG). Returns ranked items."""
        k = k or self.rag_top_k
        qv = _normalize(self.embedder.embed(query))
        scored: List[Tuple[float, MemoryItem]] = []
        with self._lock:
            for item_id, vec in self._vectors.items():
                item = self._items[item_id]
                if kind and item.kind != kind:
                    continue
                sim = cosine_sim(qv, vec)
                # importance boosts + a small recency boost
                score = sim * (0.6 + 0.4 * item.importance)
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [it for _, it in scored[:k]]
        with self._lock:
            now = time.time()
            for it in results:
                it.access_count += 1
                it.last_access = now
        return results

    # -- CAG layer ---------------------------------------------------------
    def recent(self, n: int = 10) -> List[MemoryItem]:
        """Short-term fast memory: most recent items without retrieval."""
        return list(self._hot[:n])

    def pin(self, key: str, value: str) -> None:
        """Add to the always-injected (CAG) pinned context cache."""
        with self._lock:
            self._pinned[key] = value
            self._save_pinned()

    def unpin(self, key: str) -> bool:
        with self._lock:
            if key in self._pinned:
                del self._pinned[key]
                self._save_pinned()
                return True
            return False

    def pinned_context(self) -> str:
        """The persistent CAG block, injected into EVERY prompt (no retrieval)."""
        if not self._pinned:
            return ""
        lines = ["[OMNI PINNED CONTEXT (always available, no retrieval needed)]"]
        for k, v in self._pinned.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    def forget(self, item_id: str) -> bool:
        with self._lock:
            if item_id in self._items:
                del self._items[item_id]
                del self._vectors[item_id]
                self._save_items()
                return True
            return False

    # -- fusion ------------------------------------------------------------
    def build_context(self, question: str, k: Optional[int] = None) -> str:
        """
        Fuse CAG (pinned + recent) and RAG (retrieved) into one context block
        that the brain can inject before reasoning. This is the heart of the
        LONG + SHORT mix.
        """
        parts: List[str] = []

        pinned = self.pinned_context()
        if pinned:
            parts.append(pinned)

        # RAG: long-term deep recall
        hits = self.retrieve(question, k=k)
        if hits:
            block = ["[OMNI LONG-TERM MEMORY (retrieved via RAG)]"]
            for i, it in enumerate(hits, 1):
                src = f" ({it.source})" if it.source else ""
                block.append(f"{i}. [{it.kind}{src}] {it.text}")
            parts.append("\n".join(block))

        # CAG: short-term fast memory
        recent = self.recent(n=6)
        if recent:
            block = ["[OMNI SHORT-TERM MEMORY (recent, cached)]"]
            for it in recent:
                block.append(f"- {it.text}")
            parts.append("\n".join(block))

        return "\n\n".join(parts)

    # -- stats -----------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "long_term_items": len(self._items),
                "hot_cache_size": len(self._hot),
                "pinned_context_keys": len(self._pinned),
                "persist_dir": str(self.persist_dir),
                "embedder": "sparse_hash" if self.embedder._embedder is None else "external",
            }

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._vectors.clear()
            self._hot.clear()
            self._pinned.clear()
            self._save_items()
            self._save_pinned()


_instance = None
_lock = threading.Lock()


def get_hybrid_memory(**kwargs) -> HybridMemory:
    """Singleton accessor for the app-wide hybrid memory."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = HybridMemory(**kwargs)
    return _instance
