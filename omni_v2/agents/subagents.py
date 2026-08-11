"""
OMNI SUB-AGENT DELEGATION (Phase 13, #4) — RLM-style "sub-agents as calls".

The Prime-Agent idea applied to OMNI: a goal's steps can run as PARALLEL
sub-agents that each do one focused piece and REPORT BACK COMPACTLY — the
parent stays small and focused, results are aggregated, and nothing bloats the
main context.

Design:
  - SubAgentSpec: describes one delegated unit (name, brief, handler).
  - SubAgentDelegator: runs a batch of specs in parallel (thread pool),
    collects each result, and produces a COMPACT aggregated summary.
  - Handlers are pluggable callables: brief -> result (str/dict). Tests use
    fakes; real handlers wrap the away-queue (research/digest/notify), tools, or
    the brain.
  - `delegate_goal`: given a GoalStack goal, runs each pending step as a
    sub-agent (using a step handler), then completes those steps and returns a
    compact report — the RLM "decompose -> spawn sub-calls -> synthesize" loop.

Fully local, headless-testable with fake handlers.
"""
from __future__ import annotations
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SubAgents")


@dataclass
class SubAgentResult:
    name: str
    ok: bool
    summary: str              # compact report back to the parent
    detail: Optional[Dict[str, Any]] = None
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SubAgentDelegator:
    """Runs parallel sub-agents and aggregates compact results."""

    def __init__(self, max_workers: int = 3, handler: Optional[Callable[[str, str], Any]] = None):
        self.max_workers = max_workers
        # handler(brief) -> result; default returns a simple ack
        self.handler = handler or (lambda brief: {"ok": True, "summary": f"handled: {brief[:60]}"})
        self._results: List[SubAgentResult] = []

    def spawn(self, name: str, brief: str) -> SubAgentResult:
        """Run one sub-agent synchronously."""
        try:
            raw = self.handler(brief)
            if isinstance(raw, dict):
                summary = raw.get("summary", raw.get("result", raw.get("message", str(raw))))
                detail = raw
                ok = raw.get("ok", raw.get("success", True))
            else:
                summary = str(raw)[:300]
                detail = None
                ok = True
            res = SubAgentResult(name=name, ok=bool(ok), summary=str(summary)[:500], detail=detail)
        except Exception as e:
            res = SubAgentResult(name=name, ok=False, summary=f"error: {e}")
        self._results.append(res)
        return res

    def spawn_many(self, specs: List[Dict[str, str]]) -> List[SubAgentResult]:
        """
        Run a batch of sub-agent specs [{name, brief}] in parallel.
        Returns results in the same order as specs.
        """
        ordered: Dict[str, SubAgentResult] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(specs)))) as ex:
            future_to_key = {}
            for spec in specs:
                name = spec.get("name", "sub")
                brief = spec.get("brief", "")
                key = name or brief
                future_to_key[ex.submit(self.spawn, name, brief)] = key
            for fut in as_completed(future_to_key):
                key = future_to_key[fut]
                try:
                    ordered[key] = fut.result()
                except Exception as e:
                    ordered[key] = SubAgentResult(name=key, ok=False, summary=f"error: {e}")
        return [ordered.get((s.get("name") or s.get("brief")), SubAgentResult(name="?", ok=False, summary="missing"))
                for s in specs]

    def aggregate(self, results: List[SubAgentResult]) -> Dict[str, Any]:
        """Produce a COMPACT aggregated summary for the parent context."""
        ok = sum(1 for r in results if r.ok)
        lines = [f"[sub-agents] {ok}/{len(results)} succeeded:"]
        for r in results:
            mark = "✓" if r.ok else "✗"
            lines.append(f"  {mark} {r.name}: {r.summary[:120]}")
        return {
            "ok_count": ok,
            "total": len(results),
            "summary": "\n".join(lines),
            "all_ok": ok == len(results),
        }

    def delegate_goal(self, goal, goals_stack=None, step_handler: Optional[Callable[[str], Any]] = None) -> Dict[str, Any]:
        """
        RLM-style: run each pending goal step as a parallel sub-agent, complete
        the steps on the goal stack, and return a compact report.
        """
        if goal is None:
            return {"ok": False, "summary": "no goal"}
        steps = getattr(goal, "steps", [])
        handler = step_handler or self.handler
        specs = [{"name": f"step{i+1}", "brief": s.desc} for i, s in enumerate(steps)]
        results = self.spawn_many(specs) if specs else []
        agg = self.aggregate(results)

        # complete steps on the goal stack if provided
        if goals_stack is not None:
            try:
                for _ in range(len(steps) * 2):
                    s = goals_stack.begin_step(goal.id)
                    if s is None:
                        break
                    goals_stack.complete_step(goal.id, result={"sub_agent": True})
            except Exception as e:
                logger.warning(f"delegate_goal complete failed: {e}")
        return {**agg, "goal_id": getattr(goal, "id", None)}

    def history(self, n: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._results[-n:][::-1]]

    def stats(self) -> Dict[str, Any]:
        ok = sum(1 for r in self._results if r.ok)
        return {"spawned": len(self._results), "succeeded": ok,
                "failed": len(self._results) - ok, "max_workers": self.max_workers}


def get_subagent_delegator(**kwargs) -> SubAgentDelegator:
    return SubAgentDelegator(**kwargs)
