"""Legacy application preferences layered beneath canonical runtime configuration.

Runtime paths, models, devices, offline/cloud policy, and ports belong to
:mod:`omni_v2.core.config`. This compatibility manager stores only UI/feature
preferences in ``settings.json`` and projects canonical values into the legacy
``OMNISettings`` view so old callers cannot create a competing authority.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from omni_v2.core.config import (
    DEFAULT_BROWSER_DEBUG_PORT,
    DEFAULT_STT_DEVICE,
    DEFAULT_STT_MODEL,
    DEFAULT_TTS_VOICE,
    RuntimeConfig,
    load_config,
)

try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger("ConfigV2")


@dataclass
class OMNISettings:
    # Legacy feature/UI preferences.
    ptt_key: str = "v"
    wakeword_enabled: bool = True
    wakeword_name: str = "hey omni"
    wakeword_engine: str = "openwakeword"
    stt_engine: str = "auto"
    tts_enabled: bool = True
    tts_speed: float = 1.0
    llm_provider: str = "ollama"
    memory_enabled: bool = True
    context_turns: int = 5
    debug_mode: bool = False
    demo_mode: bool = False
    pii_logging: bool = False
    log_commands: bool = True

    # Canonical runtime projections. Defaults preserve direct-construction
    # compatibility; ConfigManager.load() replaces these from RuntimeConfig.
    whisper_model: str = DEFAULT_STT_MODEL
    whisper_device: str = DEFAULT_STT_DEVICE
    no_cloud: bool = False
    tts_voice: str = DEFAULT_TTS_VOICE
    tts_allow_cloud: bool = False
    llm_model: str = "llama3.1:8b"
    llm_tier: str = "auto"
    memory_db_path: str = ""
    vector_db_path: str = ""
    browser_port: int = DEFAULT_BROWSER_DEBUG_PORT

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OMNISettings:
        valid_fields = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in valid_fields})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_CANONICAL_FIELDS = {
    "stt_engine",
    "whisper_model",
    "whisper_device",
    "no_cloud",
    "tts_voice",
    "tts_allow_cloud",
    "llm_model",
    "llm_tier",
    "memory_db_path",
    "vector_db_path",
    "browser_port",
}


class ConfigManager:
    """Compatibility facade for non-runtime settings.

    New code should use :func:`load_config` directly. Canonical fields exposed
    here are read-only projections; ``set`` rejects attempts to mutate them.
    """

    def __init__(self, config_path: Path | None = None):
        self.runtime = load_config()
        self.config_path = config_path or (self.runtime.data_dir / "settings.json")
        self.settings = self._apply_runtime(OMNISettings(), self.runtime)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Legacy preferences at {self.config_path}; runtime config at {self.runtime.config_path}")

    @staticmethod
    def _apply_runtime(settings: OMNISettings, runtime: RuntimeConfig) -> OMNISettings:
        settings.stt_engine = runtime.stt_engine
        settings.whisper_model = runtime.stt_model
        settings.whisper_device = runtime.stt_device
        settings.no_cloud = runtime.offline
        settings.tts_voice = runtime.tts_voice
        settings.tts_allow_cloud = runtime.tts_allow_cloud
        settings.llm_model = str(runtime.fast_model_path)
        settings.llm_tier = "fast"
        settings.memory_db_path = str(runtime.memory_db_path)
        settings.vector_db_path = str(runtime.vector_db_path)
        settings.browser_port = runtime.browser_debug_port
        return settings

    def load(self) -> OMNISettings:
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise TypeError("settings document must be a JSON object")
                self.settings = OMNISettings.from_dict(data)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                logger.warning(f"Failed to load legacy preferences: {exc}")
                self.settings = OMNISettings()
        self.runtime = load_config()
        self.settings = self._apply_runtime(self.settings, self.runtime)
        return self.settings

    def save(self, settings: OMNISettings | None = None) -> bool:
        if settings:
            self.settings = settings
        document = {
            key: value
            for key, value in self.settings.to_dict().items()
            if key not in _CANONICAL_FIELDS
        }
        temporary = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
        try:
            temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.config_path)
            logger.info(f"Legacy preferences saved to {self.config_path}")
            return True
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            logger.error(f"Failed to save legacy preferences: {exc}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self.settings, key, default)

    def set(self, key: str, value: Any) -> None:
        if key in _CANONICAL_FIELDS:
            raise ValueError(f"{key} is owned by canonical runtime configuration")
        if key not in self.settings.__dataclass_fields__:
            raise KeyError(f"Unknown OMNI setting: {key}")
        setattr(self.settings, key, value)

    def update(self, updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            self.set(key, value)
