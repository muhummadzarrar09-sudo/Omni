"""Planner Agent - Breaks user utterance into steps, handles chain commands
HARDENED VERSION

FIXES (from diagnostic/01_DIAGNOSTIC_REPORT.md):
- LOOP-BUG-01 [HIGH]: Better context resolution (word-boundary, not just substring)
- LOOP-BUG-03 [HIGH]: Cumulative context threaded through chain
"""
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
        logger.info("PlannerAgent V2 initialized (chain-aware, hardened)")

    def plan(self, text: str) -> List[ActionStep]:
        """
        V2 NEW: Chain commands
        Input: "Open Chrome, maximize it, and go to YouTube"
        Output: 3 steps
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

        # LOOP-BUG-01 fix: better context resolution with word-boundary regex
        steps = self._resolve_context_references(steps, text)

        logger.info(f"Planner: {len(steps)} steps planned for '{text}'")
        for s in steps:
            logger.debug(f"  Step {s.step_index}: {s.action} | {s.entities} | {s.description}")

        return steps

    def _resolve_context_references(self, steps: List[ActionStep], original_text: str) -> List[ActionStep]:
        """
        LOOP-BUG-01 fix: Resolve 'it', 'that', 'them', 'this' to previous entities.
        Uses word-boundary regex to avoid false positives like 'this' inside 'thistle'.
        """
        resolved = []
        last_entities = {}
        # Pronouns to look for at start of step or after a chain delimiter
        PRONOUN_RE = re.compile(r'\b(it|that|them|this|those)\b', re.IGNORECASE)

        for step in steps:
            lower = step.original.lower()
            has_pronoun = bool(PRONOUN_RE.search(lower))

            # If step has a pronoun AND no entities, try to inherit from previous step
            if has_pronoun and not step.entities and last_entities:
                step.entities = last_entities.copy()
                step.description += f" (context: resolved pronoun -> {last_entities})"
                logger.info(f"Context resolved: '{step.original}' -> {last_entities}")
            # Even if step has some entities, fill in missing ones from prior context
            elif has_pronoun and step.entities and last_entities:
                for k, v in last_entities.items():
                    step.entities.setdefault(k, v)
                logger.info(f"Context enriched: '{step.original}' -> {step.entities}")

            if step.entities:
                last_entities = step.entities.copy()

            resolved.append(step)

        return resolved

    def should_chain(self, text: str) -> bool:
        """Check if text contains chain delimiters"""
        chain_keywords = [" and ", " then ", " , ", " plus ", " after that ", " and then "]
        lower = text.lower()
        return any(kw in lower for kw in chain_keywords)
