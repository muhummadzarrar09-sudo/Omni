"""Kokoro TTS - Local text-to-speech with Windows SAPI fallback"""
import threading
import subprocess
import platform
from typing import Optional, Callable
from loguru import logger


class KokoroTTS:
    """Text-to-Speech using Kokoro TTS, with Windows SAPI fallback."""
    
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
        self._sapi_available = False
        self._load_model()
    
    def _load_model(self) -> None:
        # Try Kokoro first (any failure → SAPI fallback)
        try:
            from kokoro import Kokoro
            self.kokoro = Kokoro(device="cuda")
            logger.info("Kokoro TTS loaded (CUDA)")
        except Exception:
            # Kokoro failed — try CPU
            try:
                from kokoro import Kokoro
                self.kokoro = Kokoro(device="cpu")
                logger.info("Kokoro TTS loaded (CPU)")
            except Exception:
                # Kokoro not available at all — use SAPI
                logger.warning("Kokoro TTS not available, checking Windows SAPI...")
                self._check_sapi()
    
    def _check_sapi(self) -> None:
        """Check if Windows SAPI is available as fallback."""
        if platform.system() == "Windows":
            try:
                import win32com.client
                self._sapi_available = True
                logger.info("Windows SAPI TTS available as fallback")
            except ImportError:
                # pywin32 not installed, try pyttsx3
                try:
                    import pyttsx3
                    self._sapi_available = True
                    self._pyttsx3_engine = pyttsx3.init()
                    logger.info("pyttsx3 TTS engine available")
                except ImportError:
                    logger.warning("No TTS engine available (Kokoro, pywin32, pyttsx3)")
            except Exception:
                pass
    
    def speak(self, text: str, callback: Optional[Callable] = None) -> None:
        if self.is_speaking:
            self.stop()
        self.is_speaking = True
        
        if self.kokoro:
            thread = threading.Thread(
                target=self._speak_kokoro, args=(text, callback), daemon=True
            )
            thread.start()
        elif self._sapi_available:
            thread = threading.Thread(
                target=self._speak_sapi, args=(text, callback), daemon=True
            )
            thread.start()
        else:
            # No TTS at all - just log it
            logger.info(f"TTS (silent): {text}")
            self.is_speaking = False
            if callback:
                callback()
    
    def _speak_kokoro(self, text: str, callback: Optional[Callable]) -> None:
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
                    except Exception:
                        pass  # Audio playback failed silently
            self.is_speaking = False
            if callback:
                callback()
        except Exception as e:
            logger.error(f"Kokoro speech error: {e}")
            self.is_speaking = False
    
    def _speak_sapi(self, text: str, callback: Optional[Callable]) -> None:
        """Speak using Windows SAPI via PowerShell."""
        try:
            if platform.system() == "Windows":
                # Use PowerShell to call SAPI - cross-version compatible
                escaped = text.replace('"', '\\"').replace("'", "''")
                ps_script = f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak("{escaped}")'
                
                proc = subprocess.Popen(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                proc.wait(timeout=30)
            
            self.is_speaking = False
            if callback:
                callback()
        except subprocess.TimeoutExpired:
            logger.warning("SAPI speech timed out")
            self.is_speaking = False
        except Exception as e:
            logger.error(f"SAPI speech error: {e}")
            self.is_speaking = False
    
    def stop(self) -> None:
        if self.is_speaking:
            try:
                import sounddevice as sd
                sd.stop()
            except ImportError:
                try:
                    import simpleaudio as sa
                    sa.stop_all_operations()
                except Exception:
                    pass
            self.is_speaking = False