"""
OMNI Intent Mapper - Semantic search with graceful fallback
============================================================

Replaces brittle regex with vector embeddings.
If sentence-transformers not installed or offline, falls back to regex (non-fatal).
"""

from __future__ import annotations

from typing import Optional, Tuple, Dict, List
from loguru import logger
import re

try:
    import numpy as np
except ImportError:
    np = None

try:
    from sentence_transformers import SentenceTransformer, util
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    SentenceTransformer = None
    util = None
    logger.warning("sentence-transformers not installed - semantic matching disabled, using regex fallback. pip install sentence-transformers")

class IntentMapper:
    """Handles semantic matching between user input and command examples."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.58):
        self.model_name = model_name
        self.threshold = threshold
        self.model = None
        self._intent_map: Dict[str, any] = {} # command_id -> mean_vector
        self._command_ids: List[str] = []
        self._fallback_examples: Dict[str, List[str]] = {}  # Store raw examples for fallback fuzzy match
        self._load_model()

    def _load_model(self) -> None:
        """Load lightweight embedding model with offline cache awareness."""
        if not ST_AVAILABLE:
            logger.info("IntentMapper: sentence-transformers unavailable, semantic search disabled (regex will be used)")
            return
        try:
            logger.info(f"Loading Intent Mapper model: {self.model_name} (first run downloads ~80MB, cached thereafter)...")
            # Try loading with local_files_only first to avoid network if cached
            try:
                self.model = SentenceTransformer(self.model_name, device='cpu')
                logger.info("Intent Mapper model loaded from cache ✓ (fast)")
            except Exception:
                # Fallback: allow download
                self.model = SentenceTransformer(self.model_name)
                logger.info("Intent Mapper model downloaded and loaded ✓")
        except Exception as e:
            logger.warning(f"Intent Mapper model load failed: {e}. Continuing with regex-only mode.")
            self.model = None

    def register_command(self, command_id: str, examples: List[str]) -> None:
        """Encode examples for a command and store their average vector + fallback keywords."""
        if not examples:
            return

        # Always store for fallback fuzzy matching
        cleaned = [re.sub(r"[^a-z0-9 ]", " ", ex.lower()).strip() for ex in examples if ex.strip()]
        self._fallback_examples[command_id] = cleaned

        if self.model is None:
            return

        try:
            embeddings = self.model.encode(examples, convert_to_tensor=True, show_progress_bar=False)
            mean_vector = embeddings.mean(dim=0)
            self._intent_map[command_id] = mean_vector
            if command_id not in self._command_ids:
                self._command_ids.append(command_id)
            logger.debug(f"Registered intent for '{command_id}' with {len(examples)} examples")
        except Exception as e:
            logger.debug(f"Intent register failed for {command_id}: {e}")

    def _fallback_match(self, user_input: str) -> Tuple[Optional[str], float]:
        """Simple keyword fuzzy fallback when model not available."""
        user_input = user_input.lower()
        best = None
        best_score = 0.0
        for cmd_id, examples in self._fallback_examples.items():
            for ex in examples:
                # token overlap score
                ex_words = set(ex.split())
                user_words = set(user_input.split())
                if not ex_words or not user_words:
                    continue
                overlap = len(ex_words & user_words) / len(ex_words | user_words)
                # also check substring containment
                if ex in user_input or user_input in ex:
                    overlap = max(overlap, 0.6)
                # keyword boost for important words
                if overlap > best_score:
                    best_score = overlap
                    best = cmd_id
        if best_score >= 0.35:  # lower threshold for fallback
            return best, best_score
        return None, best_score

    def match(self, user_input: str) -> Tuple[Optional[str], float]:
        """Match user input to most similar command - robust edition."""
        if not user_input or not user_input.strip():
            return None, 0.0

        user_input_clean = user_input.lower().strip()

        # If no model, force regex fallback (CRITICAL FIX: previously returned wrong vscode intent)
        if self.model is None or not self._intent_map:
            logger.debug("IntentMapper: no model, using regex fallback (return None)")
            return None, 0.0

        # Semantic path only
        try:
            user_vec = self.model.encode(user_input_clean, convert_to_tensor=True, show_progress_bar=False)
            best_command = None
            max_sim = -1.0
            for cmd_id, cmd_vec in self._intent_map.items():
                sim = util.cos_sim(user_vec, cmd_vec).item()
                if sim > max_sim:
                    max_sim = sim
                    best_command = cmd_id
            if max_sim >= self.threshold:
                return best_command, max_sim
            # Below threshold -> let regex handle it (don't force fallback)
            logger.debug(f"Semantic confidence low {max_sim:.2f} for '{user_input_clean}' - deferring to regex")
            return None, max_sim
        except Exception as e:
            logger.debug(f"Semantic match error: {e}, deferring to regex")
            return None, 0.0

    def set_threshold(self, value: float) -> None:
        self.threshold = max(0.1, min(0.95, float(value)))
        logger.info(f"Intent threshold updated to: {self.threshold}")
