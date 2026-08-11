"""
OMNI CONTEXT COMPACTION (Phase 13, #3) — the token/memory efficiency win.

When a conversation grows past a token budget, instead of dumping everything or
silently truncating, we COMPACT: summarize the older middle into a short note
while preserving the original task and the most recent turns. This keeps the
small brain (1.5B/3B) focused and cuts token cost — the same idea the modern
harnesses use (OpenHarness auto-compaction, Anthropic compaction, etc.).

Two summarizers:
  - deterministic: heuristic summary (topics, user asks, tool results) — works
    offline with no model.
  - pluggable `summarizer` callable (supply the deep LLM / DGX model for richer
    prose).

Fully headless-testable with a pure function + a Compactor class.
"""
from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Compaction")


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def heuristic_summary(messages: List[Dict[str, Any]]) -> str:
    """
    Deterministic summary of a list of messages. Extracts the user's asks and
    key tool results, deduped, into a compact note.
    """
    facts: List[str] = []
    seen = set()
    for m in messages:
        role = m.get("role", "")
        content = str(m.get("content", ""))
        name = m.get("name", "")
        if role == "user" and content:
            line = f"user asked: {content.strip()[:120]}"
        elif role == "assistant" and content:
            line = f"omni replied: {content.strip()[:100]}"
        elif role == "tool" and content:
            line = f"{name}: {content.strip()[:80]}"
        else:
            continue
        key = line.lower()
        if key not in seen:
            seen.add(key)
            facts.append(line)
    if not facts:
        return ""
    # keep a bounded set
    return "[compacted] " + " | ".join(facts[-8:])


class Compactor:
    """Compacts a message transcript to stay within a token budget."""

    def __init__(self, max_tokens: int = 1200, keep_last: int = 4,
                 summarizer: Optional[Callable[[List[Dict[str, Any]]], str]] = None,
                 enabled: bool = True):
        self.max_tokens = max_tokens
        self.keep_last = keep_last
        self.summarizer = summarizer or heuristic_summary
        self.enabled = enabled
        self.compactions = 0

    def maybe_compact(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        If the transcript exceeds max_tokens, compact the middle into a system
        note, preserving the first (task) message and the last `keep_last` turns.
        Returns the (possibly compacted) message list.
        """
        if not self.enabled:
            return messages
        total = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
        if total <= self.max_tokens or len(messages) <= self.keep_last + 1:
            return messages

        first = messages[0]
        tail = messages[-self.keep_last:]
        middle = messages[1:-self.keep_last] if self.keep_last else messages[1:]
        if not middle:
            return messages

        summary = self.summarizer(middle)
        if not summary:
            # fall back to a minimal note
            summary = f"[compacted {len(middle)} earlier turns]"

        note = {"role": "system", "content": summary}
        compacted = [first, note] + tail
        self.compactions += 1
        logger.info(f"🧹 compacted {len(messages)} -> {len(compacted)} turns "
                    f"(~{total} tok -> ~{sum(estimate_tokens(str(m.get('content',''))) for m in compacted)} tok)")
        return compacted

    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled, "max_tokens": self.max_tokens,
            "keep_last": self.keep_last, "compactions": self.compactions,
            "summarizer": "deterministic" if self.summarizer is heuristic_summary else "custom",
        }


def get_compactor(**kwargs) -> Compactor:
    return Compactor(**kwargs)
