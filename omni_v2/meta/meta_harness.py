"""
OMNI META-HARNESS (Phase 16, #2) — the self-improvement OUTER loop.

The Prime-Agent / AlphaEvolve idea applied: OMNI not only refines skills from
experience (inner harness), but also IMPROVES ITS OWN HARNESS over time.

The loop per iteration:
  1. MINE: read failure traces (action journal failures / metacog verdicts /
     benchmark results) and cluster them into weakness patterns.
  2. PROPOSE: generate candidate harness edits (add a lesson / refine a skill /
     adjust a prompt / add a guardrail) from the patterns.
  3. VALIDATE: run a benchmark regression on the candidate; compare the outcome
     to the baseline.
  4. COMMIT/REJECT: keep the edit only if it improves (or holds) the metric;
     otherwise roll back. Every edit is snapshotted.

All logic is headless-testable: the miner, proposer, and validator are pluggable
(no model needed); tests use fakes.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("MetaHarness")


@dataclass
class WeaknessPattern:
    """A mined failure pattern from traces."""
    kind: str                 # tool_error | repeated | regression | unknown
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    frequency: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HarnessEdit:
    """A proposed change to the harness."""
    target: str               # skill:<name> | lesson:<name> | memory:<name> | prompt
    kind: str                 # create | refine | guardrail
    content: str
    applied: bool = False
    kept: bool = False
    improvement: Optional[float] = None
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetaHarness:
    """Mines failures, proposes harness edits, validates via regression, keeps only improvements."""

    def __init__(
        self,
        harness=None,               # ContinualHarness (optional) to apply edits to
        miner: Optional[Callable[[], List[WeaknessPattern]]] = None,
        proposer: Optional[Callable[[List[WeaknessPattern]], List[HarnessEdit]]] = None,
        validator: Optional[Callable[[HarnessEdit], float]] = None,
        baseline_score: float = 0.0,
        improvement_threshold: float = 0.0,
    ):
        self.harness = harness
        self.miner = miner or (lambda: [])
        self.proposer = proposer or (lambda pats: [])
        self.validator = validator or (lambda edit: 0.0)
        self.baseline_score = baseline_score
        self.improvement_threshold = improvement_threshold
        self._history: List[HarnessEdit] = []

    # -- step 1: mine -------------------------------------------------------
    def mine(self) -> List[WeaknessPattern]:
        patterns = self.miner()
        # merge by (kind) and count
        merged: Dict[str, WeaknessPattern] = {}
        for p in patterns:
            if p.kind in merged:
                merged[p.kind].frequency += 1
                merged[p.kind].evidence.extend(p.evidence)
            else:
                merged[p.kind] = p
        return list(merged.values())

    # -- step 2: propose ----------------------------------------------------
    def propose(self, patterns: List[WeaknessPattern]) -> List[HarnessEdit]:
        return self.proposer(patterns)

    # -- step 3: validate ---------------------------------------------------
    def _validate(self, edit: HarnessEdit) -> float:
        try:
            return float(self.validator(edit) or 0.0)
        except Exception as e:
            logger.warning(f"meta validator error: {e}")
            return -1.0

    # -- step 4: commit/reject ----------------------------------------------
    def _apply(self, edit: HarnessEdit) -> None:
        if self.harness is None:
            return
        try:
            if edit.target.startswith("skill:"):
                name = edit.target.split(":", 1)[1]
                self.harness.add("skill", name, edit.content)
            elif edit.target.startswith("lesson:"):
                name = edit.target.split(":", 1)[1]
                self.harness.add("lesson", name, edit.content)
            elif edit.target.startswith("memory:"):
                name = edit.target.split(":", 1)[1]
                self.harness.add("memory", name, edit.content)
        except Exception as e:
            logger.warning(f"meta apply failed: {e}")

    def _rollback(self, edit: HarnessEdit) -> None:
        # snapshot rollback via the harness (prior version preserved on add)
        if self.harness is not None and edit.target.startswith(("skill:", "lesson:", "memory:")):
            kind, name = edit.target.split(":", 1)
            self.harness.rollback(kind, name)

    # -- one full iteration --------------------------------------------------
    def improve(self, apply: bool = True) -> Dict[str, Any]:
        """Run one self-improvement iteration. Returns what was done."""
        patterns = self.mine()
        edits = self.propose(patterns)
        committed = []
        rejected = []
        for edit in edits:
            score = self._validate(edit)
            delta = score - self.baseline_score
            edit.improvement = delta
            if delta >= self.improvement_threshold:
                if apply:
                    self._apply(edit)
                    edit.applied = True
                edit.kept = True
                committed.append(edit)
            else:
                if apply and edit.applied:
                    self._rollback(edit)
                rejected.append(edit)
            self._history.append(edit)
        return {
            "patterns": [p.to_dict() for p in patterns],
            "proposed": len(edits),
            "committed": [e.to_dict() for e in committed],
            "rejected": [e.to_dict() for e in rejected],
        }

    def history(self, n: int = 30) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._history[-n:][::-1]]

    def stats(self) -> Dict[str, Any]:
        kept = sum(1 for e in self._history if e.kept)
        return {"iterations_edits": len(self._history), "kept": kept,
                "rejected": len(self._history) - kept}


def get_meta_harness(**kwargs) -> MetaHarness:
    return MetaHarness(**kwargs)
