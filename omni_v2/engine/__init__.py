"""
OMNI ENGINE (Phase 16, #1) — the agentic tool-calling runtime.

OpenHarness-style QueryEngine: brain + tool registry + permission gate + hooks +
cost metering + compaction in one loop. Headless-testable.
"""
from omni_v2.engine.query_engine import QueryEngine, Tool, TurnResult, get_query_engine

__all__ = ["QueryEngine", "Tool", "TurnResult", "get_query_engine"]
