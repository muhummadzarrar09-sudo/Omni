"""
OMNI V3 - TTS SIMPLE - ONE ENGINE THAT WORKS
Kokoro af_sarah only, fallback SAPI5 only. No gTTS, playsound, pydub fighting.
"""
from pathlib import Path
from typing import Optional
import threading

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("TTSSimpleV3")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.cwd() / "data"

class SimpleTTS:
    """One engine, reliable"""
    
    def __init__(self):
        self.engine_type = None
        self.kokoro_model = None
        self.sapi_engine = None
        self._lock = threading.Lock()
        self._init_tts()
    
    def _init_tts(self):
        """Try Kokoro first, fallback SAPI5"""
        # Try Kokoro
        try:
            # Check if espeak-ng available (needed for Kokoro)
            try:
                import espeakng_loader
                espeakng_loader.setup()
            except Exception as e:
                logger.warning(f"espeakng-loader setup failed: {e} - trying anyway")
            
            from kokoro_onnx import Kokoro
            
            # Look for model files
            model_paths = [
                DATA_DIR / "models" / "kokoro-v0_19.onnx",
                DATA_DIR / "models" / "kokoro-v1.0.onnx",
                Path("data/models/kokoro-v0_19.onnx"),
                Path.cwd() / "data" / "models" / "kokoro-v0_19.onnx",
            ]
            
            voices_paths = [
                DATA_DIR / "models" / "voices.json",
                DATA_DIR / "models" / "voices-v1.0.bin",
                Path("data/models/voices.json"),
            ]
            
            model_file = None
            voices_file = None
            
            for p in model_paths:
                if p.exists():
                    model_file = str(p)
                    break
            
            for p in voices_paths:
                if p.exists():
                    voices_file = str(p)
                    break
            
            if model_file and voices_file:
                logger.info(f"TTS V3 - Trying Kokoro: model={model_file}")
                self.kokoro_model = Kokoro(model_file, voices_file)
                self.engine_type = "kokoro"
                logger.info(f"✅ TTS V3 READY: Kokoro af_sarah - {model_file}")
                return
            else:
                logger.warning(f"Kokoro model not found. Searched: {model_paths}")
                
        except Exception as e:
            logger.warning(f"Kokoro init failed: {e} - fallback SAPI5")
            import traceback
            logger.debug(traceback.format_exc())
        
        # Fallback SAPI5 - always works on Windows
        try:
            import pyttsx3
            self.sapi_engine = pyttsx3.init()
            # Set voice - try female
            voices = self.sapi_engine.getProperty('voices')
            if voices:
                # Prefer female English
                for v in voices:
                    if 'zira' in v.name.lower() or 'female' in v.name.lower():
                        self.sapi_engine.setProperty('voice', v.id)
                        break
            self.sapi_engine.setProperty('rate', 180)
            self.engine_type = "sapi"
            logger.info(f"✅ TTS V3 READY: SAPI5 fallback - {self.sapi_engine.getProperty('voice')}")
            
        except Exception as e:
            logger.error(f"TTS V3 - All engines failed! {e}")
            self.engine_type = None
    
    def speak(self, text: str, blocking: bool = True):
        """Speak text - single engine"""
        if not text or not text.strip():
            logger.warning("TTS: Empty text, skip")
            return
        
        if self.engine_type is None:
            logger.error("TTS no engine available - can't speak")
            print(f"[OMNI TTS]: {text}")  # Fallback print
            return
        
        # Clean text
        text = text.strip()[:500]  # Limit 500 chars for hackathon
        
        with self._lock:
            try:
                if self.engine_type == "kokoro":
                    logger.info(f"🔊 Speaking via Kokoro: '{text[:80]}...'")
                    # Kokoro streaming
                    try:
                        import sounddevice as sd
                        import numpy as np
                        
                        # Generate audio
                        audio, sample_rate = self.kokoro_model.create(text, voice="af_sarah", speed=1.0, lang="en-us")
                        
                        # Play via sounddevice
                        sd.play(audio, samplerate=sample_rate)
                        if blocking:
                            sd.wait()
                        
                        logger.info(f"✅ Kokoro speak done: {len(audio)/sample_rate:.2f}s")
                        
                    except Exception as e:
                        logger.warning(f"Kokoro play failed {e}, fallback to SAPI")
                        # Fallback within
                        if self.sapi_engine is None:
                            import pyttsx3
                            self.sapi_engine = pyttsx3.init()
                        self.sapi_engine.say(text)
                        if blocking:
                            self.sapi_engine.runAndWait()
                
                elif self.engine_type == "sapi":
                    logger.info(f"🔊 Speaking via SAPI5: '{text[:80]}...'")
                    self.sapi_engine.say(text)
                    if blocking:
                        self.sapi_engine.runAndWait()
                    logger.info(f"✅ SAPI5 speak done")
                
            except Exception as e:
                logger.error(f"TTS speak failed: {e}")
                print(f"[OMNI SAYS - TTS FAILED]: {text}")
    
    def speak_async(self, text: str):
        """Non-blocking"""
        thread = threading.Thread(target=self.speak, args=(text, True), daemon=True)
        thread.start()
    
    def get_status(self):
        return {
            "engine": self.engine_type,
            "kokoro_available": self.kokoro_model is not None,
            "sapi_available": self.sapi_engine is not None,
        }

# Singleton
_simple_tts_instance = None

def get_simple_tts():
    global _simple_tts_instance
    if _simple_tts_instance is None:
        _simple_tts_instance = SimpleTTS()
    return _simple_tts_instance
