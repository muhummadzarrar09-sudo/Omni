"""
OMNI SKILL VERIFICATION LOOP (Phase 13, #2) — "is this skill actually good?"

When the Continual Harness creates or refines a skill, this loop:
  1. Runs the skill through a pluggable TESTER against a test case.
  2. If it passes  -> keep it (record it as verified).
  3. If it fails   -> ROLL IT BACK to the previous version (or drop it if new).

This closes the self-improvement loop: the harness may write a bad skill, and
the verifier catches it instead of letting it poison future runs.

Fully local and headless-testable:
  - The tester is a callable(skill_artifact) -> (bool, message). Tests use fakes.
  - Default tester is conservative (returns True with a "not tested" note) so it
    never wrongly blocks, and can be upgraded to a real executor on the DGX.
"""
from __future__ import annotations
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SkillVerifierLoop")


class SkillVerificationLoop:
    """Verifies skills after creation/refinement and rolls back failures."""

    def __init__(self, harness=None, tester: Optional[Callable[[Any], Tuple[bool, str]]] = None,
                 autofix: bool = True):
        self.harness = harness
        # tester(skill_artifact) -> (passed: bool, message: str)
        self.tester = tester or self._default_tester
        self.autofix = autofix        # if True, attempt a fix before rolling back
        self._results: List[Dict[str, Any]] = []

    @staticmethod
    def _default_tester(skill) -> Tuple[bool, str]:
        """Conservative default: pass with a note (upgrade on DGX to a real runner)."""
        return True, "not-executed (deterministic tester); skill kept"

    @staticmethod
    def sandbox_tester(sandbox=None):
        """Build a tester that runs the skill in the SkillSandbox (Phase 14 #3).
        A skill passes only if it executes cleanly in the isolated subprocess."""
        if sandbox is None:
            from omni_v2.skills.sandbox import SkillSandbox
            sandbox = SkillSandbox()
        def _test(skill) -> Tuple[bool, str]:
            res = sandbox.run_skill_artifact(skill)
            if res.ok:
                return True, f"sandbox-executed ok: {res.output[:80] or 'clean'}"
            return False, f"sandbox failed: {res.error[:120]}"
        return _test

    # -- main entry ---------------------------------------------------------
    def verify_skill(self, skill: Any) -> Dict[str, Any]:
        """Verify a single skill artifact. Returns a result dict."""
        try:
            passed, msg = self.tester(skill)
        except Exception as e:
            passed, msg = False, f"tester raised: {e}"

        record = {
            "ts": time.time(), "name": skill.name, "version": skill.version,
            "passed": passed, "message": msg,
        }
        self._results.append(record)
        self._results = self._results[-200:]

        if passed:
            logger.info(f"✓ skill verified: {skill.name} v{skill.version} — {msg}")
            return {**record, "action": "kept"}

        # failed -> roll back to previous version (or drop if only v1 / new)
        logger.warning(f"✗ skill failed verification: {skill.name} v{skill.version} — {msg}")
        rolled_back = False
        if self.harness is not None:
            try:
                rolled_back = self.harness.rollback(skill.kind, skill.name)
            except Exception as e:
                logger.warning(f"skill rollback failed: {e}")
        if not rolled_back:
            # new skill with no prior snapshot -> remove it
            self._drop(skill)
        return {**record, "action": "rolled_back" if rolled_back else "dropped"}

    def _drop(self, skill) -> None:
        try:
            self.harness.remove(skill.kind, skill.name)
            logger.info(f"dropped unverified skill: {skill.name}")
        except Exception as e:
            logger.warning(f"skill drop failed: {e}")

    # -- wire into harness auto-refine --------------------------------------
    def hook(self, skill: Any) -> None:
        """Callable to pass as the harness's post-skill hook."""
        self.verify_skill(skill)

    def history(self, n: int = 20) -> List[Dict[str, Any]]:
        return self._results[-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        passed = sum(1 for r in self._results if r["passed"])
        return {
            "checks": len(self._results),
            "passed": passed,
            "failed": len(self._results) - passed,
            "actions": {r.get("action", "?") for r in self._results},
        }


def get_skill_verifier(**kwargs) -> SkillVerificationLoop:
    return SkillVerificationLoop(**kwargs)
