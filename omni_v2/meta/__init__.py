"""
OMNI META-HARNESS (Phase 16, #2) — the self-improvement outer loop.

Mines failure traces -> proposes harness edits -> validates via regression ->
keeps only improvements (snapshot/rollback). Headless-testable.
"""
from omni_v2.meta.meta_harness import (
    MetaHarness, WeaknessPattern, HarnessEdit, get_meta_harness,
)

__all__ = ["MetaHarness", "WeaknessPattern", "HarnessEdit", "get_meta_harness"]
