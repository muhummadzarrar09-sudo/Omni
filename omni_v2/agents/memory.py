"""Memory Agent V2 - Phase 2 Hardened - Data Inside Project Root (Unanimous)"""
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import deque

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("MemoryV2")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"

try:
    from omni_v2.memory.sqlite_store import SQLiteMemoryStore
    from omni_v2.memory.vector_store import VectorMemoryStore
    NEW_STORES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"New memory stores not available: {e} - using JSON fallback")
    NEW_STORES_AVAILABLE = False
    SQLiteMemoryStore = None
    VectorMemoryStore = None

class MemoryAgent:
    """Memory V2 Phase 2 Hardened: SQLite + ChromaDB inside project/data/ for unanimous portability"""

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = memory_dir or DATA_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.context = deque(maxlen=5)

        self.sqlite_store = None
        self.vector_store = None
        self.use_new_stores = False

        if NEW_STORES_AVAILABLE:
            try:
                self.sqlite_store = SQLiteMemoryStore(self.memory_dir / "memory.db")
                self.vector_store = VectorMemoryStore(self.memory_dir / "chroma")
                self.use_new_stores = True
                logger.info(f"MemoryAgent V2 Phase 2 Hardened: SQLite + ChromaDB in {self.memory_dir} (project data/)")
            except Exception as e:
                logger.warning(f"Failed to init new stores: {e} - using fallback")
                self.use_new_stores = False

        if not self.use_new_stores:
            self.long_term_file = self.memory_dir / "memory.json"
            self.long_term_memory: Dict[str, Any] = {}
            self._load_fallback()
        else:
            self.long_term_file = self.memory_dir / "memory.json"
            self.long_term_memory = {}

        logger.info(f"MemoryAgent V2 Phase 2 Hardened: context=5, new_stores={self.use_new_stores}, dir={self.memory_dir}")

    def _load_fallback(self):
        import json
        if self.long_term_file.exists():
            try:
                with open(self.long_term_file, 'r') as f:
                    self.long_term_memory = json.load(f)
                logger.info(f"Loaded {len(self.long_term_memory)} fallback memories from project data/")
            except Exception as e:
                logger.warning(f"Failed to load fallback memory: {e}")
                self.long_term_memory = {}

    def _save_fallback(self):
        import json
        try:
            with open(self.long_term_file, 'w') as f:
                json.dump(self.long_term_memory, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fallback memory: {e}")

    def remember(self, key: str, value: str):
        self.context.append({
            "key": key,
            "value": value,
            "timestamp": time.time()
        })

        if self.use_new_stores:
            try:
                self.sqlite_store.remember(key, value)
                self.vector_store.add_memory(f"{key}: {value}", {"key": key, "timestamp": time.time()})
                self.sqlite_store.log_interaction(key, value, success=True)
            except Exception as e:
                logger.warning(f"Failed to remember in new stores: {e}")
        else:
            self.long_term_memory[key] = {
                "value": value,
                "timestamp": time.time(),
                "count": self.long_term_memory.get(key, {}).get("count", 0) + 1 if isinstance(self.long_term_memory.get(key), dict) else 1
            }
            self._save_fallback()

        logger.debug(f"Memory V2 remembered: '{key}' in project data/")

    def recall(self, query: str) -> List[str]:
        results = []

        if self.use_new_stores:
            try:
                sqlite_results = self.sqlite_store.recall(query, limit=3)
                for r in sqlite_results:
                    results.append(f"{r['key']}: {r['value']}")

                vector_results = self.vector_store.search(query, n_results=3)
                for r in vector_results:
                    results.append(f"[vector] {r['text']}")

            except Exception as e:
                logger.warning(f"Recall from new stores failed: {e}")

        query_lower = query.lower()
        for item in self.context:
            if query_lower in item["key"].lower() or query_lower in item["value"].lower():
                results.append(f"[context] {item['key']}: {item['value']}")

        if not self.use_new_stores:
            for k, v in self.long_term_memory.items():
                if query_lower in k.lower() or query_lower in str(v).lower():
                    if isinstance(v, dict):
                        results.append(f"{k}: {v.get('value', '')}")
                    else:
                        results.append(f"{k}: {v}")

        logger.debug(f"Memory V2 recall '{query}' -> {len(results)} results from project data/")
        return results[:5]

    def get_context(self) -> List[Dict[str, Any]]:
        return list(self.context)

    def learn_preference(self, text: str):
        lower = text.lower()

        if "prefer" in lower and "voice" in lower:
            if "british" in lower:
                self.remember("tts_voice_preference", "bf_gemma")
                if self.use_new_stores:
                    self.sqlite_store.learn_preference("tts_voice", "bf_gemma", text)
                logger.info("Learned preference: British voice")
            elif "male" in lower:
                self.remember("tts_voice_preference", "am_michael")
                if self.use_new_stores:
                    self.sqlite_store.learn_preference("tts_voice", "am_michael", text)
            elif "female" in lower:
                self.remember("tts_voice_preference", "af_sarah")
                if self.use_new_stores:
                    self.sqlite_store.learn_preference("tts_voice", "af_sarah", text)

        if "chrome is my default" in lower or "use chrome" in lower:
            self.remember("browser_preference", "chrome")
            if self.use_new_stores:
                self.sqlite_store.learn_preference("browser", "chrome", text)

        if "my name is" in lower:
            import re
            m = re.search(r"my name is (\w+)", lower)
            if m:
                name = m.group(1)
                self.remember("user_name", name)
                if self.use_new_stores:
                    self.sqlite_store.learn_preference("user_name", name, text)
                logger.info(f"Learned user name: {name}")

    def get_recent_interactions(self, limit: int = 5) -> List[Dict[str, Any]]:
        if self.use_new_stores:
            try:
                return self.sqlite_store.get_recent_interactions(limit)
            except Exception:
                pass
        return [{"user": item["key"], "assistant": item["value"], "timestamp": item["timestamp"]} for item in list(self.context)[-limit:]]

    def clear_context(self):
        self.context.clear()
        logger.info("Context cleared")

    def clear_long_term(self):
        self.long_term_memory = {}
        self._save_fallback()
        logger.info("Long-term memory cleared")
