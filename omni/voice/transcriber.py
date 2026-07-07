"""Whisper Transcriber - Speech-to-Text"""
import numpy as np
from typing import Optional
from loguru import logger

class WhisperTranscriber:
    """Speech-to-text using faster-whisper."""
    
    def __init__(self, model_name: str = "base.en", device: str = "cuda"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self._loaded = False
        self._load_model()
    
    def _load_model(self) -> None:
        try:
            from faster_whisper import WhisperModel
            compute_type = "float16" if self.device == "cuda" else "int8"
            self.model = WhisperModel(self.model_name, device=self.device, compute_type=compute_type)
            self._loaded = True
            logger.info(f"Whisper model loaded: {self.model_name}")
        except ImportError:
            logger.error("faster-whisper not installed")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
    
    def transcribe(self, audio: np.ndarray, language: str = "en") -> Optional[str]:
        if not self._loaded or self.model is None:
            return None
        if len(audio) == 0:
            return None
        try:
            import torch
            audio_tensor = torch.from_numpy(audio).float() if not isinstance(audio, torch.Tensor) else audio
            segments, _ = self.model.transcribe(audio_tensor, language=language, beam_size=5, vad_filter=True)
            text_parts = [segment.text.strip() for segment in segments]
            result = " ".join(text_parts)
            logger.info(f"Transcribed: '{result}'")
            return result.strip() if result else None
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def is_loaded(self) -> bool:
        return self._loaded
