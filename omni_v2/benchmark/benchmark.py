"""
OMNI SELF-IMPROVEMENT BENCHMARK (Phase 14, #2) — proves the harness works.

Measures whether OMNI actually gets FASTER and CHEAPER on repeated task types
as the Continual Harness accumulates skills/memory/lessons. This is the
Hermes-style claim ("20+ skills = ~40% faster/cheaper") made measurable.

Design (all headless-testable):
  - BenchmarkCase: one repeated task type {name, briefs, run}.
  - BenchmarkRunner:
      * runs a task case N times;
      * for each run records: wall time, estimated tokens, step count, success,
        and whether the harness had a matching skill at that point;
      * produces a report comparing "early" (fewer skills) vs "late" (more
        skills) runs, and a per-iteration improvement curve.
  - Pluggable executor: run(brief, harness_context) -> {ok, steps, tokens, time}.
    Tests use fakes that get cheaper/faster when a harness skill exists.
  - Optionally wires a real harness (skills grow between runs), so a real run
    demonstrates improvement end-to-end.

The key metric: does the "late" cohort beat the "early" cohort?
"""
from __future__ import annotations
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Benchmark")


class BenchmarkCase:
    """One repeated task type to benchmark."""

    def __init__(self, name: str, briefs: List[str],
                 run: Callable[[str, str], Dict[str, Any]]):
        self.name = name
        self.briefs = briefs or [name]
        # run(brief, harness_context) -> {ok, steps, tokens, time, ...}
        self.run = run


class BenchmarkResult:
    """A single task run's measurement."""

    def __init__(self, case: str, iteration: int, ok: bool, time_s: float,
                 tokens: int, steps: int, skill_present: bool):
        self.case = case
        self.iteration = iteration
        self.ok = ok
        self.time_s = time_s
        self.tokens = tokens
        self.steps = steps
        self.skill_present = skill_present

    def to_dict(self) -> Dict[str, Any]:
        return {"case": self.case, "iteration": self.iteration, "ok": self.ok,
                "time_s": round(self.time_s, 3), "tokens": self.tokens,
                "steps": self.steps, "skill_present": self.skill_present}


class BenchmarkRunner:
    """Runs a task type repeatedly and measures improvement over time."""

    def __init__(self, harness=None, iterations: int = 4):
        self.harness = harness          # optional ContinualHarness (skills grow)
        self.iterations = iterations
        self._results: List[BenchmarkResult] = []

    def _context_for(self, case: str) -> str:
        if self.harness is None:
            return ""
        # does a skill exist for this case? inject its context
        skill_name = f"skill_{case.lower().replace(' ','_')[:40]}"
        art = self.harness.get("skill", skill_name)
        return art.content if art else ""

    def _has_skill(self, case: str) -> bool:
        if self.harness is None:
            return False
        skill_name = f"skill_{case.lower().replace(' ','_')[:40]}"
        return self.harness.get("skill", skill_name) is not None

    def run_case(self, case: BenchmarkCase) -> List[BenchmarkResult]:
        results = []
        for i in range(1, self.iterations + 1):
            brief = case.briefs[(i - 1) % len(case.briefs)]
            ctx = self._context_for(case.name)
            skill = self._has_skill(case.name)
            t0 = time.time()
            raw = case.run(brief, ctx)
            dt = time.time() - t0
            res = BenchmarkResult(
                case=case.name, iteration=i,
                ok=bool(raw.get("ok", True)),
                time_s=raw.get("time", dt),
                tokens=raw.get("tokens", 0),
                steps=raw.get("steps", 0),
                skill_present=skill,
            )
            results.append(res)
            self._results.append(res)
        return results

    # -- reporting ----------------------------------------------------------
    @staticmethod
    def _avg(items: List[BenchmarkResult], key) -> float:
        if not items:
            return 0.0
        return sum(getattr(r, key) for r in items) / len(items)

    def report(self, case_name: str = "") -> Dict[str, Any]:
        """Compare early vs late cohort for the given case (or all)."""
        results = self._results
        if case_name:
            results = [r for r in results if r.case == case_name]

        # split by presence of a harness skill (early = no skill, late = skill)
        early = [r for r in results if not r.skill_present]
        late = [r for r in results if r.skill_present]

        def cohort_summary(items):
            if not items:
                return {"count": 0}
            return {
                "count": len(items),
                "avg_time_s": round(self._avg(items, "time_s"), 3),
                "avg_tokens": round(self._avg(items, "tokens"), 1),
                "avg_steps": round(self._avg(items, "steps"), 1),
                "success_rate": round(sum(1 for r in items if r.ok) / len(items), 2),
            }

        early_s, late_s = cohort_summary(early), cohort_summary(late)

        # improvement = % reduction in time/tokens/steps from early to late
        def pct(a, b):
            if a in (0, None) or not b:
                return None
            return round((a - b) / a * 100, 1)

        return {
            "case": case_name or "all",
            "iterations": len(results),
            "early": early_s,
            "late": late_s,
            "improvement": {
                "time_pct": pct(early_s.get("avg_time_s"), late_s.get("avg_time_s")),
                "tokens_pct": pct(early_s.get("avg_tokens"), late_s.get("avg_tokens")),
                "steps_pct": pct(early_s.get("avg_steps"), late_s.get("avg_steps")),
            },
        }

    def all_results(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._results]


def get_benchmark_runner(**kwargs) -> BenchmarkRunner:
    return BenchmarkRunner(**kwargs)
