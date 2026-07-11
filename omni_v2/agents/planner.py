"""Planner Agent - Breaks user utterance into steps, handles chain commands"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("PlannerV2")

from omni_v2.core.command_registry import ActionStep, CommandRegistry

class PlannerAgent:
    """Planner: Breaks chain commands into actionable steps"""

    def __init__(self, registry: CommandRegistry = None):
        self.registry = registry or CommandRegistry()
        logger.info("PlannerAgent V2 initialized (chain-aware)")

    def plan(self, text: str) -> List[ActionStep]:
        """
        V2 NEW: Chain commands
        Input: "Open Chrome, maximize it, and go to YouTube and play music"
        Output: 4 steps
        """
        text = text.strip()
        if not text:
            return []

        logger.info(f"Planner: Planning goal -> '{text}'")

        # Use registry's chain parser
        try:
            steps = self.registry.parse_chain(text)
        except AttributeError:
            # Fallback if parse_chain not available
            parts = re.split(r'\s+(?:and|then|,|plus|after\s+that)\s+', text, flags=re.IGNORECASE)
            steps = []
            for i, part in enumerate(parts):
                part = part.strip()
                if not part:
                    continue
                parsed = self.registry.parse(part)
                steps.append(ActionStep(
                    action=parsed.action,
                    entities=parsed.entities,
                    original=parsed.original,
                    description=f"Step {i+1}: {parsed.action}",
                    step_index=i
                ))

        # Enhance with context awareness: resolve "it", "that", etc.
        steps = self._resolve_context_references(steps, text)

        logger.info(f"Planner: {len(steps)} steps planned for '{text}'")
        for s in steps:
            logger.debug(f"  Step {s.step_index}: {s.action} | {s.entities} | {s.description}")

        return steps

    def _resolve_context_references(self, steps: List[ActionStep], original_text: str) -> List[ActionStep]:
        """Resolve 'it', 'that', 'them' to previous entities"""
        resolved = []
        last_entities = {}

        for step in steps:
            # If step has "it" or "that" and no entities, use last entities
            lower = step.original.lower()
            has_pronoun = any(pron in lower for pron in [" it", " that", " them", " this"])

            if has_pronoun and not step.entities and last_entities:
                # Copy last entities for context
                step.entities = last_entities.copy()
                step.description += f" (context: resolved 'it' -> {last_entities})"
                logger.info(f"Context resolved: '{step.original}' -> {last_entities}")

            # Update last_entities if this step has entities
            if step.entities:
                last_entities = step.entities.copy()

            resolved.append(step)

        return resolved

    def should_chain(self, text: str) -> bool:
        """Check if text contains chain delimiters"""
        chain_keywords = [" and ", " then ", " , ", " plus ", " after that ", " and then "]
        lower = text.lower()
        return any(kw in lower for kw in chain_keywords)
