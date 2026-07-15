"""
OMNI V3 - TTS SIMPLE - ONE ENGINE THAT WORKS - HARDENED
Kokoro af_sarah preferred, SAPI5 fallback, print-as-last-resort.
NEVER silently fails - always produces SOME audible output.

FIXES (from diagnostic/01_DIAGNOSTIC_REPORT.md):
- TTS-BUG-01 [HIGH]: Always log final engine state + last_error
- TTS-BUG-02 [HIGH]: SAPI engine thread-safe via single instance + lock
- TTS-BUG-03 [MED] : Sentence-boundary cut, 800 char limit
- TTS-BUG-04 [MED] : stop_speaking() interrupt
- TTS-BUG-05 [LOW] : Safe no-op when engine is None
"""
from pathlib import Path
from typing import Optional
import threading
import re

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
    """One engine, reliable, ALWAYS speaks something"""

    def __init__(self):
        self.engine_type = None
        self.kokoro_model = None
        self.sapi_engine = None
        self._lock = threading.Lock()
        self._stop_flag = False
        # Diagnostics
        self.init_status = "pending"
        self.last_error = None
        self.spoken_count = 0
        self._init_tts()

    def _init_tts(self):
        """Try Kokoro first, fallback SAPI5, then print fallback"""
        # Try Kokoro
        try:
            try:
                import espeakng_loader
                espeakng_loader.setup()
            except Exception as e:
                logger.debug(f"espeakng-loader setup skipped: {e}")

            from kokoro_onnx import Kokoro

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
                self.init_status = "kokoro_loaded"
                logger.info(f"✅ TTS V3 READY: Kokoro af_sarah - {model_file}")
                return
            else:
                logger.warning(f"Kokoro model not found. Searched: {model_paths}")

        except ImportError as e:
            self.last_error = f"kokoro_onnx not installed: {e}"
            logger.debug(f"kokoro_onnx not installed: {e}")
        except Exception as e:
            self.last_error = f"Kokoro init failed: {e}"
            logger.warning(f"Kokoro init failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        # Fallback SAPI5 - always works on Windows
        try:
            import pyttsx3
            import pythoncom

            # COM initialize on this thread (TTS-BUG-02 fix)
            try:
                pythoncom.CoInitialize()
            except Exception:
                pass

            self.sapi_engine = pyttsx3.init()
            # Set voice - prefer female English
            voices = self.sapi_engine.getProperty('voices')
            if voices:
                for v in voices:
                    name_l = v.name.lower()
                    if any(k in name_l for k in ['zira', 'sarah', 'hazel', 'female', 'eva']):
                        self.sapi_engine.setProperty('voice', v.id)
                        break
            self.sapi_engine.setProperty('rate', 185)
            self.engine_type = "sapi"
            self.init_status = "sapi_loaded"
            logger.info(f"✅ TTS V3 READY: SAPI5 fallback - {self.sapi_engine.getProperty('voice')}")

        except ImportError as e:
            self.last_error = f"pyttsx3 not installed: {e}"
            logger.error(f"pyttsx3 not installed: {e} - pip install pyttsx3")
        except Exception as e:
            self.last_error = f"SAPI5 init failed: {e}"
            logger.error(f"TTS V3 - SAPI5 init failed! {e}")
            import traceback
            logger.debug(traceback.format_exc())

        if self.engine_type is None:
            self.init_status = "no_engine_print_only"
            logger.warning("⚠️ TTS: No engine available - will print to console as fallback")

    def _truncate_at_sentence(self, text: str, max_len: int = 800) -> str:
        """Cut at sentence boundary, not mid-word (TTS-BUG-03 fix)"""
        if len(text) <= max_len:
            return text
        # Try to find last sentence boundary within limit
        truncated = text[:max_len]
        # Look for sentence end in last 100 chars
        m = list(re.finditer(r'[.!?]\s', truncated))
        if m:
            cut = m[-1].end()
            if cut > max_len * 0.5:  # don't cut too short
                return truncated[:cut].strip()
        # Otherwise, cut at last space
        last_space = truncated.rfind(' ')
        if last_space > max_len * 0.5:
            return truncated[:last_space].strip() + "..."
        return truncated + "..."

    def speak(self, text: str, blocking: bool = True):
        """Speak text - ALWAYS produces output"""
        if not text or not text.strip():
            logger.warning("TTS: Empty text, skip")
            return

        text = self._truncate_at_sentence(text.strip(), max_len=800)

        with self._lock:
            self._stop_flag = False
            try:
                if self.engine_type == "kokoro":
                    logger.info(f"🔊 Speaking via Kokoro: '{text[:80]}...'")
                    try:
                        import sounddevice as sd
                        audio, sample_rate = self.kokoro_model.create(
                            text, voice="af_sarah", speed=1.0, lang="en-us"
                        )
                        sd.play(audio, samplerate=sample_rate)
                        if blocking:
                            sd.wait()
                        self.spoken_count += 1
                        logger.info(f"✅ Kokoro speak done: {len(audio)/sample_rate:.2f}s")
                        return
                    except Exception as e:
                        logger.warning(f"Kokoro play failed: {e}, fallback to SAPI")
                        # Fall through to SAPI in same lock
                        self.engine_type = "sapi"
                        self._init_sapi_if_needed()

                if self.engine_type == "sapi":
                    logger.info(f"🔊 Speaking via SAPI5: '{text[:80]}...'")
                    try:
                        # TTS-BUG-02 fix: COM init on this thread
                        try:
                            import pythoncom
                            pythoncom.CoInitialize()
                        except Exception:
                            pass
                        # Use the existing engine (not init a new one)
                        if self.sapi_engine is None:
                            self._init_sapi_if_needed()
                        if self.sapi_engine is not None:
                            self.sapi_engine.say(text)
                            if blocking:
                                self.sapi_engine.runAndWait()
                            self.spoken_count += 1
                            logger.info(f"✅ SAPI5 speak done")
                            return
                    except Exception as e:
                        logger.warning(f"SAPI speak failed: {e}, falling through to print")

            except Exception as e:
                logger.error(f"TTS speak error: {e}")

            # TTS-BUG-05 fix: print fallback when no engine works
            print(f"[OMNI SAYS]: {text}")
            self.spoken_count += 1

    def _init_sapi_if_needed(self):
        """Lazy-init SAPI engine on demand"""
        if self.sapi_engine is not None:
            return
        try:
            import pyttsx3
            self.sapi_engine = pyttsx3.init()
            voices = self.sapi_engine.getProperty('voices')
            if voices:
                for v in voices:
                    if any(k in v.name.lower() for k in ['zira', 'sarah', 'hazel', 'female']):
                        self.sapi_engine.setProperty('voice', v.id)
                        break
            self.sapi_engine.setProperty('rate', 185)
            self.engine_type = "sapi"
        except Exception as e:
            logger.error(f"Lazy SAPI init failed: {e}")
            self.sapi_engine = None

    def speak_async(self, text: str):
        """Non-blocking speak in background thread"""
        thread = threading.Thread(target=self.speak, args=(text, True), daemon=True)
        thread.start()
        return thread

    def stop_speaking(self):
        """TTS-BUG-04 fix: Interrupt any ongoing TTS"""
        self._stop_flag = True
        if self.sapi_engine is not None:
            try:
                self.sapi_engine.stop()
            except Exception:
                pass
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        logger.info("🛑 TTS interrupted")

    def get_status(self):
        return {
            "engine": self.engine_type,
            "kokoro_available": self.kokoro_model is not None,
            "sapi_available": self.sapi_engine is not None,
            "init_status": self.init_status,
            "last_error": self.last_error,
            "spoken_count": self.spoken_count,
        }


# Singleton
_simple_tts_instance = None
_tts_lock = threading.Lock()


def get_simple_tts():
    global _simple_tts_instance
    if _simple_tts_instance is None:
        with _tts_lock:
            if _simple_tts_instance is None:
                _simple_tts_instance = SimpleTTS()
    return _simple_tts_instance
