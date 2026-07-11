"""SQLite Store V2 - Phase 2 - Persistent Memory"""
import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SQLiteStore")

class SQLiteMemoryStore:
    """Persistent memory via SQLite - stores facts, preferences, interactions"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (Path.home() / ".omni_v2" / "memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()
        logger.info(f"SQLiteMemoryStore V2 at {self.db_path}")

    def _init_db(self):
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    count INTEGER DEFAULT 1,
                    created_at REAL DEFAULT (strftime('%s','now')),
                    updated_at REAL DEFAULT (strftime('%s','now'))
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_text TEXT NOT NULL,
                    assistant_text TEXT NOT NULL,
                    success BOOLEAN DEFAULT 1,
                    timestamp REAL DEFAULT (strftime('%s','now'))
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pref_key TEXT UNIQUE NOT NULL,
                    pref_value TEXT NOT NULL,
                    learned_from TEXT,
                    updated_at REAL DEFAULT (strftime('%s','now'))
                )
            """)
            self.conn.commit()
            logger.info("SQLite DB initialized with memories, interactions, preferences tables")
        except Exception as e:
            logger.error(f"SQLite init failed: {e}")

    def remember(self, key: str, value: str, category: str = "general"):
        try:
            # Upsert
            existing = self.conn.execute("SELECT count FROM memories WHERE key = ?", (key,)).fetchone()
            if existing:
                self.conn.execute(
                    "UPDATE memories SET value = ?, count = count + 1, updated_at = strftime('%s','now'), category = ? WHERE key = ?",
                    (value, category, key)
                )
            else:
                self.conn.execute(
                    "INSERT INTO memories (key, value, category) VALUES (?, ?, ?)",
                    (key, value, category)
                )
            self.conn.commit()
            logger.debug(f"SQLite remembered: {key}")
        except Exception as e:
            logger.error(f"SQLite remember failed: {e}")

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            # Simple keyword search - Phase 2, Phase 3 will use vector search
            like_query = f"%{query}%"
            rows = self.conn.execute(
                "SELECT key, value, category, count FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (like_query, like_query, limit)
            ).fetchall()
            results = [{"key": r[0], "value": r[1], "category": r[2], "count": r[3]} for r in rows]
            logger.debug(f"SQLite recall '{query}' -> {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"SQLite recall failed: {e}")
            return []

    def log_interaction(self, user_text: str, assistant_text: str, success: bool = True):
        try:
            self.conn.execute(
                "INSERT INTO interactions (user_text, assistant_text, success) VALUES (?, ?, ?)",
                (user_text, assistant_text, success)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"SQLite log interaction failed: {e}")

    def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            rows = self.conn.execute(
                "SELECT user_text, assistant_text, timestamp FROM interactions ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [{"user": r[0], "assistant": r[1], "timestamp": r[2]} for r in rows]
        except Exception as e:
            logger.error(f"SQLite get recent failed: {e}")
            return []

    def learn_preference(self, pref_key: str, pref_value: str, learned_from: str = ""):
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO preferences (pref_key, pref_value, learned_from, updated_at) VALUES (?, ?, ?, strftime('%s','now'))",
                (pref_key, pref_value, learned_from)
            )
            self.conn.commit()
            logger.info(f"Learned preference: {pref_key} = {pref_value}")
        except Exception as e:
            logger.error(f"Learn preference failed: {e}")

    def get_preference(self, pref_key: str) -> Optional[str]:
        try:
            row = self.conn.execute("SELECT pref_value FROM preferences WHERE pref_key = ?", (pref_key,)).fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Get preference failed: {e}")
            return None

    def get_all_preferences(self) -> Dict[str, str]:
        try:
            rows = self.conn.execute("SELECT pref_key, pref_value FROM preferences").fetchall()
            return {r[0]: r[1] for r in rows}
        except Exception as e:
            logger.error(f"Get all preferences failed: {e}")
            return {}
