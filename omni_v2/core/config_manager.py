"""Config Manager V2 - With memory and LLM settings"""
import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ConfigV2")

@dataclass
class OMNISettings:
    # Voice
    ptt_key: str = "v"
    wakeword_enabled: bool = True
    wakeword_name: str = "hey omni"
    # STT
    whisper_model: str = "base.en"
    whisper_device: str = "cuda"
    # TTS
    tts_enabled: bool = True
    tts_voice: str = "af_sarah"
    tts_speed: float = 1.0
    # LLM
    llm_provider: str = "ollama"  # ollama, openai, anthropic, local
    llm_model: str = "llama3.1:8b"
    llm_tier: str = "auto"  # fast, brain, deep, local, auto
    # Memory
    memory_enabled: bool = True
    memory_db_path: str = "~/.omni_v2/memory.db"
    vector_db_path: str = "~/.omni_v2/vector.db"
    context_turns: int = 5
    # System
    browser_port: int = 9222
    debug_mode: bool = False
    demo_mode: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OMNISettings':
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ConfigManager:
    DEFAULT_CONFIG_PATH = Path.home() / ".omni_v2" / "config.json"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.settings = OMNISettings()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            logger.info(f"ConfigManager V2 at {self.config_path}")
        except Exception:
            pass
    
    def load(self) -> OMNISettings:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self.settings = OMNISettings.from_dict(data)
                logger.info("V2 Settings loaded")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
                self.settings = OMNISettings()
        return self.settings
    
    def save(self, settings: Optional[OMNISettings] = None) -> bool:
        if settings:
            self.settings = settings
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.settings.to_dict(), f, indent=2)
            logger.info("V2 Settings saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self.settings, key, default)
    
    def set(self, key: str, value: Any) -> None:
        setattr(self.settings, key, value)
    
    def update(self, updates: Dict[str, Any]) -> None:
        for key, value in updates.items():
            self.set(key, value)
