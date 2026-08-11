"""
OMNI SELF-IMPROVEMENT BENCHMARK (Phase 14, #2).

Measures whether OMNI gets faster/cheaper on repeated task types as the Continual
Harness accumulates skills. Headless-testable.
"""
from omni_v2.benchmark.benchmark import (
    BenchmarkCase, BenchmarkResult, BenchmarkRunner, get_benchmark_runner,
)

__all__ = ["BenchmarkCase", "BenchmarkResult", "BenchmarkRunner", "get_benchmark_runner"]
