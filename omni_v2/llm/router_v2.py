"""
OMNI LLM ROUTER V2 (Phase 13, #6) — the DGX-ready model router.

A smarter, cost-aware upgrade on top of the existing LLMRouter. Picks the
CHEAPEST capable model per task — OpenSquilla-style — so on the DGX Station
(with many local models in memory) OMNI dispatches each turn to the right tier:
fast (cheap) / balanced / deep (reasoning) / local (offline fallback).

Key ideas (all headless-testable, no model required for the logic):
  - Explicit MODEL SPECS: each tier lists candidate models with a `cost` weight
    (lower = cheaper/faster) and a `capability` (rough reasoning strength).
  - COST-AWARE SELECTION: given an estimated task complexity + available models,
    pick the cheapest tier whose capability is sufficient. Never wastes a big
    model on a trivial task, never under-powers a hard one.
  - HEURISTIC TIERING: same style as the existing router but returns a rich
    Decision object {tier, model, reason, estimated_tokens} for observability.
  - Pluggable resolver: `resolver(tier, model_name) -> callable` that actually
    performs the call (Ollama / llama-cpp / OpenAI). Tests use fakes.

On the 1050 Ti today: fast=brain on the 1.5B, deep on the 3B. On the DGX: the
same router picks from a much larger local pool automatically.
"""
from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("RouterV2")


# Default tier/model specs. cost = relative compute cost (lower = cheaper).
DEFAULT_TIERS: Dict[str, Dict[str, Any]] = {
    "fast": {
        "description": "quick lookups, time, open, trivial commands",
        "capability": 1, "cost": 1, "temperature": 0.2, "max_tokens": 100,
        "models": [
            {"name": "qwen2.5-1.5b", "cost": 1.0, "capability": 1},
            {"name": "qwen2.5-3b", "cost": 1.8, "capability": 2},
        ],
    },
    "brain": {
        "description": "normal conversation, tool calls",
        "capability": 2, "cost": 2, "temperature": 0.5, "max_tokens": 300,
        "models": [
            {"name": "qwen2.5-1.5b", "cost": 1.0, "capability": 1},
            {"name": "qwen2.5-3b", "cost": 1.8, "capability": 2},
            {"name": "qwen2.5-14b", "cost": 5.0, "capability": 3},   # DGX
        ],
    },
    "deep": {
        "description": "hard reasoning, planning, code, analysis",
        "capability": 3, "cost": 4, "temperature": 0.7, "max_tokens": 1000,
        "models": [
            {"name": "qwen2.5-3b", "cost": 1.8, "capability": 2},
            {"name": "qwen2.5-14b", "cost": 5.0, "capability": 3},
            {"name": "qwen2.5-72b", "cost": 12.0, "capability": 4},  # DGX
        ],
    },
    "reasoning": {
        "description": "chain-of-thought, complex math, long planning",
        "capability": 4, "cost": 6, "temperature": 0.6, "max_tokens": 2000,
        "models": [
            {"name": "qwen2.5-14b", "cost": 5.0, "capability": 3},
            {"name": "qwen2.5-72b", "cost": 12.0, "capability": 4},
            {"name": "deepseek-r1-70b", "cost": 15.0, "capability": 5},  # DGX
        ],
    },
    "local": {
        "description": "offline fallback",
        "capability": 2, "cost": 2, "temperature": 0.5, "max_tokens": 300,
        "models": [{"name": "qwen2.5-1.5b", "cost": 1.0, "capability": 1}],
    },
}

# keywords -> required capability (how strong a model this task needs)
_CAPABILITY_KEYWORDS = {
    4: ["complex math", "prove", "formal", "optimize for correctness", "chain of thought"],
    3: ["plan a", "design", "architecture", "debug", "refactor", "analyze",
        "compare", "solve", "root cause", "write code", "strategy", "multi-step"],
    2: ["explain", "how", "why", "summarize", "what is", "create", "build a"],
    1: ["open", "time", "launch", "search", "what time", "play", "who", "when"],
}


class Decision:
    """The router's choice for a task."""
    def __init__(self, tier: str, model: str, required_cap: int, reason: str,
                 estimated_tokens: int = 0):
        self.tier = tier
        self.model = model
        self.required_cap = required_cap
        self.reason = reason
        self.estimated_tokens = estimated_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {"tier": self.tier, "model": self.model,
                "required_cap": self.required_cap, "reason": self.reason,
                "estimated_tokens": self.estimated_tokens}


class LLMRouterV2:
    """Cost-aware multi-tier model router (DGX-ready)."""

    def __init__(self, tiers: Optional[Dict[str, Dict[str, Any]]] = None,
                 available_models: Optional[List[str]] = None,
                 resolver: Optional[Callable[[str, str], Any]] = None):
        self.tiers = tiers or DEFAULT_TIERS
        # available_models = the model names actually loadable on this hardware.
        # None -> assume all are available (DGX). On the 1050 Ti, pass only
        # ["qwen2.5-1.5b","qwen2.5-3b"].
        self.available_models = set(available_models or self._all_model_names())
        # resolver(tier, model_name) -> callable to actually run the model.
        self.resolver = resolver

    def _all_model_names(self) -> List[str]:
        names = []
        for cfg in self.tiers.values():
            for m in cfg.get("models", []):
                names.append(m["name"])
        return names

    # -- capability estimation ---------------------------------------------
    @staticmethod
    def estimate_required_capability(text: str) -> int:
        lower = (text or "").lower()
        # start from highest and check keywords
        for cap in (4, 3, 2, 1):
            for kw in _CAPABILITY_KEYWORDS.get(cap, []):
                if kw in lower:
                    return cap
        # heuristic by length / complexity markers
        if len(lower) > 300 or lower.count(",") > 8 or ";" in lower:
            return 3
        if len(lower) > 120:
            return 2
        return 1

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    # -- selection ----------------------------------------------------------
    def select(self, text: str, preferred_tier: Optional[str] = None) -> Decision:
        """Pick the cheapest capable model for `text`."""
        required = self.estimate_required_capability(text)
        est_tokens = self.estimate_tokens(text)

        # find a tier whose capability >= required
        candidate_tiers = [t for t, cfg in self.tiers.items()
                           if cfg.get("capability", 0) >= required]
        if not candidate_tiers:
            candidate_tiers = list(self.tiers.keys())

        # prefer explicit tier if requested and capable
        if preferred_tier and preferred_tier in self.tiers and \
           self.tiers[preferred_tier].get("capability", 0) >= required:
            tier_name = preferred_tier
        else:
            # cheapest capable tier
            tier_name = min(candidate_tiers, key=lambda t: self.tiers[t].get("cost", 99))

        cfg = self.tiers[tier_name]
        # cheapest available model within that tier that meets capability
        candidates = [m for m in cfg.get("models", [])
                      if m["name"] in self.available_models
                      and m.get("capability", 0) >= required]
        if not candidates:
            # fall back to cheapest available model in tier
            candidates = [m for m in cfg.get("models", [])
                          if m["name"] in self.available_models]
        if not candidates:
            # no available model at all -> local tier, first model
            model = self.tiers["local"]["models"][0]["name"]
            tier_name = "local"
            reason = f"no capable model available for cap={required}; local fallback"
            return Decision(tier_name, model, required, reason, est_tokens)

        model = min(candidates, key=lambda m: m.get("cost", 99))
        reason = f"cap={required} -> cheapest capable in '{tier_name}'"
        return Decision(tier_name, model["name"], required, reason, est_tokens)

    # -- execution ------------------------------------------------------------
    def complete(self, text: str, preferred_tier: Optional[str] = None) -> Any:
        """Select a model and (if a resolver is set) run it. Returns (Decision, result)."""
        dec = self.select(text, preferred_tier)
        if self.resolver is None:
            return dec, None
        return dec, self.resolver(dec.tier, dec.model)

    def stats(self) -> Dict[str, Any]:
        return {
            "tiers": list(self.tiers.keys()),
            "available_models": sorted(self.available_models),
            "has_resolver": self.resolver is not None,
            "tier_count": len(self.tiers),
        }


def get_router_v2(**kwargs) -> LLMRouterV2:
    return LLMRouterV2(**kwargs)
