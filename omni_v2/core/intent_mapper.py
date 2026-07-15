"""
Intent Mapper V2 - Phase 6.1 Fast AF Semantic Router
Integrates FastAFStore Tier 1 (<1.5ms lookup) + optional SentenceTransformers
"""
from __future__ import annotations
from typing import Optional, Tuple, Dict, List
import re
import os
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("IntentMapperV2")

try:
    import numpy as np
except ImportError:
    np = None

try:
    from omni_v2.memory.fast_af_store import get_fast_af_store
except ImportError:
    get_fast_af_store = None

ST_AVAILABLE = False
SentenceTransformer = None
util = None
_IMPORT_ERROR_MSG = ""

if os.environ.get("OMNI_NO_TORCH", "") == "1":
    ST_AVAILABLE = False
    _IMPORT_ERROR_MSG = "Disabled via OMNI_NO_TORCH"
else:
    try:
        from sentence_transformers import SentenceTransformer, util
        ST_AVAILABLE = True
    except ImportError as e:
        ST_AVAILABLE = False
        _IMPORT_ERROR_MSG = str(e)
    except OSError as e:
        ST_AVAILABLE = False
        _IMPORT_ERROR_MSG = str(e)
    except Exception as e:
        ST_AVAILABLE = False
        _IMPORT_ERROR_MSG = str(e)

class IntentMapper:
    """Fast AF Semantic Router + Intent Mapper V2"""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.58):
        self.model_name = model_name
        self.threshold = threshold
        self.model = None
        self._intent_map: Dict[str, any] = {}
        self._command_ids: List[str] = []
        self._fallback_examples: Dict[str, List[str]] = {}
        self.fast_af = get_fast_af_store() if get_fast_af_store else None
        self._load_model()

    def _load_model(self) -> None:
        if not ST_AVAILABLE:
            logger.info(f"IntentMapper V2: ST not available, using Fast AF DB + regex")
            return
        try:
            logger.info(f"Loading Intent Mapper V2 model: {self.model_name}")
            try:
                self.model = SentenceTransformer(self.model_name, device='cpu')
                logger.info("Intent Mapper V2 loaded from cache ✓")
            except Exception:
                self.model = SentenceTransformer(self.model_name)
                logger.info("Intent Mapper V2 downloaded ✓")
        except Exception as e:
            logger.warning(f"Intent Mapper V2 load failed: {e}")
            self.model = None

    def register_command(self, command_id: str, examples: List[str]) -> None:
        if not examples:
            return
        cleaned = [re.sub(r"[^a-z0-9 ]", " ", ex.lower()).strip() for ex in examples if ex.strip()]
        self._fallback_examples[command_id] = cleaned
        
        # Register right into Fast AF DB Tier 1 (<1ms)
        if self.fast_af:
            try:
                self.fast_af.remember_skill(command_id, "command_intent", command_id, [], cleaned, persist=False)
            except Exception as e:
                logger.debug(f"FastAF register error: {e}")

        if self.model is None:
            return
        try:
            embeddings = self.model.encode(examples, convert_to_tensor=True, show_progress_bar=False)
            mean_vector = embeddings.mean(dim=0)
            self._intent_map[command_id] = mean_vector
            if command_id not in self._command_ids:
                self._command_ids.append(command_id)
        except Exception as e:
            logger.debug(f"Intent register failed {command_id}: {e}")

    def match(self, user_input: str) -> Tuple[Optional[str], float]:
        if not user_input or not user_input.strip():
            return None, 0.0
        user_input_clean = user_input.lower().strip()
        
        # Step 1: Sub-millisecond Tier 1 check via FastAFStore (<1.5 ms)
        if self.fast_af:
            try:
                matches, lookup_ms = self.fast_af.semantic_lookup(user_input_clean, threshold=min(0.42, self.threshold), top_k=1)
                if matches and matches[0]["score"] >= min(0.45, self.threshold):
                    logger.debug(f"⚡ FastAF match ({lookup_ms:.2f}ms): {matches[0]['name']} | score={matches[0]['score']:.2f}")
                    return matches[0]["name"], matches[0]["score"]
            except Exception as e:
                logger.debug(f"FastAF match error: {e}")

        # Step 2: SentenceTransformers check if loaded
        if self.model is None or not self._intent_map:
            return None, 0.0
        try:
            user_vec = self.model.encode(user_input_clean, convert_to_tensor=True, show_progress_bar=False)
            best_command = None
            max_sim = -1.0
            for cmd_id, cmd_vec in self._intent_map.items():
                try:
                    sim = util.cos_sim(user_vec, cmd_vec).item()
                except Exception:
                    continue
                if sim > max_sim:
                    max_sim = sim
                    best_command = cmd_id
            if max_sim >= self.threshold:
                return best_command, max_sim
            return None, max_sim
        except Exception as e:
            logger.debug(f"Semantic match error: {e}")
            return None, 0.0
