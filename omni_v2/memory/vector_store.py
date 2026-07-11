"""Vector Store V2 - Phase 2 - ChromaDB + Fallback"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("VectorStore")

class VectorMemoryStore:
    """Vector store for semantic memory - ChromaDB if available, JSON fallback"""

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or (Path.home() / ".omni_v2" / "chroma")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.chroma_available = False
        self.collection = None
        self.fallback_memory: List[Dict[str, Any]] = []
        self.fallback_file = self.persist_dir.parent / "vector_fallback.json"
        
        self._init_chroma()
        self._load_fallback()

    def _init_chroma(self):
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = client.get_or_create_collection(
                name="omni_v2_memories",
                metadata={"hnsw:space": "cosine"}
            )
            self.chroma_available = True
            logger.info(f"ChromaDB initialized at {self.persist_dir} - vector search enabled")
        except ImportError:
            logger.warning("ChromaDB not installed - using JSON fallback. pip install chromadb")
            self.chroma_available = False
        except Exception as e:
            logger.warning(f"ChromaDB init failed: {e} - using JSON fallback")
            self.chroma_available = False

    def _load_fallback(self):
        if self.fallback_file.exists():
            try:
                with open(self.fallback_file, 'r') as f:
                    self.fallback_memory = json.load(f)
                logger.info(f"Loaded {len(self.fallback_memory)} fallback vector memories")
            except Exception as e:
                logger.warning(f"Failed to load fallback vector memory: {e}")
                self.fallback_memory = []

    def _save_fallback(self):
        try:
            with open(self.fallback_file, 'w') as f:
                json.dump(self.fallback_memory, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fallback vector memory: {e}")

    def add_memory(self, text: str, metadata: Dict[str, Any] = None):
        metadata = metadata or {}
        timestamp = time.time()
        
        if self.chroma_available and self.collection:
            try:
                # ChromaDB needs unique id
                doc_id = f"mem_{int(timestamp*1000)}_{hash(text) % 10000}"
                self.collection.add(
                    documents=[text],
                    metadatas=[{**metadata, "timestamp": timestamp}],
                    ids=[doc_id]
                )
                logger.debug(f"Chroma added: {text[:50]}")
                return
            except Exception as e:
                logger.warning(f"Chroma add failed: {e}, using fallback")

        # Fallback: simple list
        self.fallback_memory.append({
            "text": text,
            "metadata": metadata,
            "timestamp": timestamp
        })
        # Keep only last 100
        if len(self.fallback_memory) > 100:
            self.fallback_memory = self.fallback_memory[-100:]
        self._save_fallback()
        logger.debug(f"Fallback vector added: {text[:50]}")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        if self.chroma_available and self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                # Chroma returns dict with documents, metadatas, distances
                docs = results.get('documents', [[]])[0]
                metas = results.get('metadatas', [[]])[0]
                distances = results.get('distances', [[]])[0]

                formatted = []
                for i in range(len(docs)):
                    formatted.append({
                        "text": docs[i],
                        "metadata": metas[i] if i < len(metas) else {},
                        "distance": distances[i] if i < len(distances) else 0.0,
                        "source": "chroma"
                    })
                logger.debug(f"Chroma search '{query}' -> {len(formatted)} results")
                return formatted
            except Exception as e:
                logger.warning(f"Chroma search failed: {e}, using fallback")

        # Fallback: keyword search
        query_lower = query.lower()
        results = []
        for mem in self.fallback_memory:
            text_lower = mem["text"].lower()
            # Simple keyword overlap score
            if query_lower in text_lower:
                score = 0.8
            else:
                # Jaccard similarity of words
                q_words = set(query_lower.split())
                t_words = set(text_lower.split())
                if q_words and t_words:
                    score = len(q_words & t_words) / len(q_words | t_words)
                else:
                    score = 0.0

            if score > 0.2:
                results.append({
                    "text": mem["text"],
                    "metadata": mem["metadata"],
                    "distance": 1.0 - score,
                    "source": "fallback",
                    "score": score
                })

        # Sort by score descending
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:n_results]

    def get_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        if self.chroma_available:
            # Chroma doesn't have easy "recent" query, use fallback list
            pass

        # Fallback: return last n from fallback_memory
        recent = sorted(self.fallback_memory, key=lambda x: x.get("timestamp", 0), reverse=True)[:n]
        return [{"text": r["text"], "metadata": r["metadata"]} for r in recent]
