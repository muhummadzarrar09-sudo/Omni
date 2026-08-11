"""
OMNI GUARDIAN (Phase 10) — proactive machine watcher.

Watches processes / health / files and surfaces observations + anomalies to the
messenger and UI. Fully local, pluggable checkers, headless-testable.
"""
from omni_v2.guardian.guardian import (
    Guardian, process_checker, health_checker, file_watcher,
)

__all__ = [
    "Guardian", "process_checker", "health_checker", "file_watcher",
]
