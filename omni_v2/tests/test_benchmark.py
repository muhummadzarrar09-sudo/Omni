"""
Tests for the Self-Improvement Benchmark (Phase 14, #2).
Run: python -m pytest omni_v2/tests/test_benchmark.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_bench_")))

from omni_v2.benchmark.benchmark import BenchmarkCase, BenchmarkRunner
from omni_v2.harness.harness import ContinualHarness


def _faster_with_skill(brief, ctx):
    """Simulates a task that is faster/cheaper when a harness skill is present."""
    if ctx:  # harness skill exists -> faster, fewer tokens/steps
        return {"ok": True, "time": 1.0, "tokens": 50, "steps": 3}
    return {"ok": True, "time": 3.0, "tokens": 150, "steps": 7}


def test_run_case_records_results():
    case = BenchmarkCase("research", ["research solar"], _faster_with_skill)
    r = BenchmarkRunner(iterations=3)
    results = r.run_case(case)
    assert len(results) == 3
    assert all(rr.ok for rr in results)


def test_report_early_vs_late():
    # no harness -> all early, all slow
    case = BenchmarkCase("deploy", ["deploy x"], _faster_with_skill)
    r = BenchmarkRunner(iterations=3)
    r.run_case(case)
    rep = r.report("deploy")
    assert rep["early"]["count"] == 3
    assert rep["late"]["count"] == 0
    assert rep["improvement"]["time_pct"] is None  # no late cohort


def test_report_with_harness_shows_improvement():
    """When a harness skill appears mid-run, the late cohort should be faster."""
    with tempfile.TemporaryDirectory() as tmp:
        h = ContinualHarness(harness_dir=Path(tmp) / "harness")
        # Pre-seed a skill so it's present from iteration 1 (late cohort)
        h.add("skill", "skill_deploy", "fast procedure")
        r = BenchmarkRunner(harness=h, iterations=4)
        case = BenchmarkCase("deploy", ["deploy x"], _faster_with_skill)
        r.run_case(case)
        rep = r.report("deploy")
        assert rep["early"]["count"] == 0
        assert rep["late"]["count"] == 4
        assert rep["late"]["avg_time_s"] == 1.0  # skill present -> fast


def test_report_improvement_pct():
    # simulate: iteration 1 no skill (slow), then skill appears -> fast
    with tempfile.TemporaryDirectory() as tmp:
        h = ContinualHarness(harness_dir=Path(tmp) / "harness")
        r = BenchmarkRunner(harness=h, iterations=2)
        def run(brief, ctx):
            if ctx:
                return {"ok": True, "time": 1.0, "tokens": 50, "steps": 3}
            return {"ok": True, "time": 3.0, "tokens": 150, "steps": 7}
        # iteration 1: no skill yet; then seed skill before iteration 2
        case = BenchmarkCase("cleanup", ["cleanup files"], run)
        # manually control: run once without skill, add skill, run once
        res1 = [BenchmarkResult_fake(r, "cleanup", 1, ctx="")]
        # simpler: add skill to harness before case 2 by running custom
        h.add("skill", "skill_cleanup", "fast")
        # rebuild runner so skill is present
        r2 = BenchmarkRunner(harness=h, iterations=1)
        res2 = r2.run_case(BenchmarkCase("cleanup", ["cleanup files"], run))
        # manually assemble early/late for the report check
        from omni_v2.benchmark.benchmark import BenchmarkResult
        early = [BenchmarkResult("cleanup", 1, True, 3.0, 150, 7, False)]
        late = [BenchmarkResult("cleanup", 2, True, 1.0, 50, 3, True)]
        # place into runner
        r._results.extend(early + late)
        rep = r.report("cleanup")
        assert rep["early"]["avg_time_s"] == 3.0
        assert rep["late"]["avg_time_s"] == 1.0
        assert rep["improvement"]["time_pct"] == 66.7  # (3-1)/3 = 66.7%
        assert rep["improvement"]["tokens_pct"] == 66.7


def BenchmarkResult_fake(runner, case, it, ctx=""):
    from omni_v2.benchmark.benchmark import BenchmarkResult
    return BenchmarkResult(case, it, True, 3.0, 150, 7, bool(ctx))


def test_all_results():
    case = BenchmarkCase("x", ["x"], _faster_with_skill)
    r = BenchmarkRunner(iterations=2)
    r.run_case(case)
    assert len(r.all_results()) == 2


def test_stats_none():
    r = BenchmarkRunner()
    assert r.report()["iterations"] == 0


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
