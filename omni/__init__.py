"""Public Python API for the experimental OMNI personal assistant.

The package exposes selected implementation objects lazily so package metadata
and lightweight CLI commands remain usable without installing every optional
capability profile. Importing a lazy object can still require its declared
``core``, ``voice``, ``vision``, or ``desktop`` dependencies.

OMNI is a pre-alpha personal build. Import availability is not a claim that a
capability is stable or release-qualified; the machine-readable capability
matrix under ``quality/`` is the source of truth in the repository.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("omni-agi")
except PackageNotFoundError:  # Source checkout before installation.
    __version__ = "3.2.0"

__author__ = "Zarrar + Agent"


def __getattr__(name):
    """
    Lazy attribute access so importing `omni` doesn't require `omni_v2` to
    be on sys.path. This is what makes the installed `omni` CLI work even
    when the package is loaded from outside the project directory.
    """
    _LAZY_MAP = {
        # name           -> (module_path,                  attribute)
        "Brain":            ("omni_v2.llm.brain",           "Brain"),
        "BrainResponse":    ("omni_v2.llm.brain",           "BrainResponse"),
        "get_brain":         ("omni_v2.llm.brain",           "get_brain"),
        "PlannerAgent":      ("omni_v2.agents.planner",      "PlannerAgent"),
        "ExecutorAgent":     ("omni_v2.agents.executor",     "ExecutorAgent"),
        "MonitorAgent":      ("omni_v2.agents.monitor",      "MonitorAgent"),
        "EvaluatorAgent":    ("omni_v2.agents.evaluator",    "EvaluatorAgent"),
        "MemoryAgent":       ("omni_v2.agents.memory",       "MemoryAgent"),
        "ProactiveAgent":    ("omni_v2.agents.proactive",    "ProactiveAgent"),
        "CommandRegistry":   ("omni_v2.core",                "CommandRegistry"),
        "PluginManager":     ("omni_v2.core",                "PluginManager"),
        "CommandResult":     ("omni_v2.core",                "CommandResult"),
        "CommandPlugin":     ("omni_v2.core",                "CommandPlugin"),
        "CommandMetadata":   ("omni_v2.core",                "CommandMetadata"),
        "get_simple_stt":    ("omni_v2.voice.stt_simple",    "get_simple_stt"),
        "get_simple_tts":    ("omni_v2.voice.tts_simple",    "get_simple_tts"),
        "VoicePipelineV3Fixed": ("omni_v2.voice.pipeline_v3_fixed", "VoicePipelineV3Fixed"),
        "get_audio_v3":      ("omni_v2.voice.audio_device_v3", "get_audio_v3"),
    }
    if name in _LAZY_MAP:
        import importlib
        module_path, attr = _LAZY_MAP[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr)
        globals()[name] = value  # cache so next access is fast
        return value
    raise AttributeError(f"module 'omni' has no attribute {name!r}")


__all__ = [
    "Brain",
    "BrainResponse",
    "CommandMetadata",
    "CommandPlugin",
    "CommandRegistry",
    "CommandResult",
    "EvaluatorAgent",
    "ExecutorAgent",
    "MemoryAgent",
    "MonitorAgent",
    "PlannerAgent",
    "PluginManager",
    "ProactiveAgent",
    "VoicePipelineV3Fixed",
    "get_audio_v3",
    "get_brain",
    "get_simple_stt",
    "get_simple_tts",
]

