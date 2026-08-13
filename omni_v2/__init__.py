"""Principal implementation package for the experimental OMNI personal build.

Capability status is governed by ``quality/capabilities.json`` in the source
repository; module availability alone does not mean a capability is stable.
"""

from omni import __version__

__author__ = "OMNI contributors"

__all__ = [
    "CommandRegistry",
    "EvaluatorAgent",
    "ExecutorAgent",
    "MemoryAgent",
    "MonitorAgent",
    "PlannerAgent",
    "PluginManager",
    "__version__",
]
