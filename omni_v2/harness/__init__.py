"""
OMNI CONTINUAL HARNESS (Phase 12) — the self-refining "grows with you" loop.

A durable, versioned store of skills / memory / lessons that OMNI refines from
its own goal trajectories (Prime-Agent-style Continual Harness). Snapshots are
rollback-able; the base prompt is never touched. Headless-testable, no model
required for the plumbing.
"""
from omni_v2.harness.harness import ContinualHarness, get_harness, HarnessArtifact
from omni_v2.harness.verifier import SkillVerificationLoop, get_skill_verifier

__all__ = [
    "ContinualHarness", "get_harness", "HarnessArtifact",
    "SkillVerificationLoop", "get_skill_verifier",
]
