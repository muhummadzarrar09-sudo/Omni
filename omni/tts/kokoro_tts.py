"""Kokoro TTS - Local text-to-speech"""
import threading
from typing import Optional, Callable
from loguru import logger

class KokoroTTS:
    """Text-to-Speech using Kokoro TTS."""
    
    VOICES = {
        "af_sarah": "American female, friendly",
        "af_bella": "American female, professional",
        "am_michael": "American male, neutral",
    }
    
    def __init__(self, voice: str = "af_sarah", speed: float = 1.0):
        self.voice = voice
        self.speed = speed
        self.kokoro = None
        self.is_speaking = False
        self._load_model()
    
    def _load_model(self) -> None:
        try:
            from kokoro import Kokoro
            self.kokoro = Kokoro(device="cuda")
            logger.info("Kokoro TTS loaded")
        except ImportError:
            logger.warning("Kokoro TTS not installed")
        except Exception as e:
            logger.error(f"Failed to load Kokoro: {e}")
    
    def speak(self, text: str, callback: Optional[Callable] = None) -> None:
        if not self.kokoro:
            return
        if self.is_speaking:
            self.stop()
        self.is_speaking = True
        thread = threading.Thread(target=self._speak_async, args=(text, callback), daemon=True)
        thread.start()
    
    def _speak_async(self, text: str, callback: Optional[Callable]) -> None:
        try:
            audio = self.kokoro.generate(text, voice=self.voice, speed=self.speed)
            if audio is not None:
                import numpy as np
                try:
                    import sounddevice as sd
                    sd.play(audio, samplerate=24000)
                    sd.wait()
                except ImportError:
                    try:
                        import simpleaudio as sa
                        if audio.dtype != np.int16:
                            audio = (audio * 32767).astype(np.int16)
                        play_obj = sa.play_buffer(audio, 1, 2, 24000)
                        play_obj.wait()
                    except: pass
            self.is_speaking = False
            if callback:
                callback()
        except Exception as e:
            logger.error(f"Speech error: {e}")
            self.is_speaking = False
    
    def stop(self) -> None:
        if self.is_speaking:
            try:
                import sounddevice as sd
                sd.stop()
            except: pass
            self.is_speaking = False
