"""Config Manager - Settings & Configuration Management"""
import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
from loguru import logger

@dataclass
class OMNISettings:
    ptt_key: str = "v"
    whisper_model: str = "base.en"
    whisper_device: str = "cuda"
    tts_enabled: bool = True
    tts_voice: str = "af_sarah"
    tts_speed: float = 1.0
    browser_port: int = 9222
    vscode_port: int = 8765
    debug_mode: bool = False
    demo_mode: bool = False
    demo_command: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OMNISettings':
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ConfigManager:
    """Manages OMNI configuration with persistence."""
    DEFAULT_CONFIG_PATH = Path.home() / ".omni" / "config.json"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.settings = OMNISettings()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"ConfigManager initialized at {self.config_path}")
    
    def load(self) -> OMNISettings:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self.settings = OMNISettings.from_dict(data)
                logger.info("Settings loaded")
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
            logger.info("Settings saved")
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
