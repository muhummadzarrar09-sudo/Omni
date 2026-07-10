"""
OMNI Intent Mapper
==================

This module replaces brittle regex matching with Semantic Intent Mapping.
It uses a lightweight Sentence-Transformer model to turn user speech 
and command examples into vectors, then uses cosine similarity to find 
the most likely intended command.

This allows OMNI to understand "get me to github" as "open github".
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Tuple, Dict, List
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")

class IntentMapper:
    """
    Handles semantic matching between user input and command examples.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.6):
        self.model_name = model_name
        self.threshold = threshold
        self.model = None
        self._intent_map: Dict[str, np.ndarray] = {} # command_id -> mean_vector
        self._command_ids: List[str] = []
        
        self._load_model()

    def _load_model(self) -> None:
        """Load the lightweight embedding model."""
        try:
            logger.info(f"Loading Intent Mapper model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Intent Mapper model loaded successfully ✓")
        except Exception as e:
            logger.error(f"Failed to load Intent Mapper model: {e}")

    def register_command(self, command_id: str, examples: List[str]) -> None:
        """
        Encode examples for a command and store their average vector.
        """
        if self.model is None or not examples:
            return

        try:
            # Encode all examples for this command
            embeddings = self.model.encode(examples, convert_to_tensor=True)
            # Use the mean vector as the 'centroid' for this intent
            mean_vector = embeddings.mean(dim=0)
            
            self._intent_map[command_id] = mean_vector
            if command_id not in self._command_ids:
                self._command_ids.append(command_id)
                
            logger.debug(f"Registered intent for '{command_id}' with {len(examples)} examples")
        except Exception as e:
            logger.error(f"Error registering intent for {command_id}: {e}")

    def match(self, user_input: str) -> Tuple[Optional[str], float]:
        """
        Match user input to the most similar command.
        Returns: (command_id, similarity_score)
        """
        if self.model is None or not self._intent_map:
            return None, 0.0

        try:
            # Encode the user input
            user_vec = self.model.encode(user_input, convert_to_tensor=True)
            
            best_command = None
            max_sim = -1.0
            
            # Compare against all registered intent centroids
            for cmd_id, cmd_vec in self._intent_map.items():
                # Calculate cosine similarity
                sim = util.cos_sim(user_vec, cmd_vec).item()
                
                if sim > max_sim:
                    max_sim = sim
                    best_command = cmd_id
            
            # Return only if it passes the confidence threshold
            if max_sim >= self.threshold:
                return best_command, max_sim
            
            return None, max_sim
            
        except Exception as e:
            logger.error(f"Intent matching error: {e}")
            return None, 0.0

    def set_threshold(self, value: float) -> None:
        """Adjust the matching sensitivity."""
        self.threshold = value
        logger.info(f"Intent threshold updated to: {self.threshold}")
