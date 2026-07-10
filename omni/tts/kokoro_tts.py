"""
OMNI Text-to-Speech Engine
==========================

Three-tier fallback system:
  Tier 1: Kokoro-ONNX (local ONNX model, highest quality)
  Tier 2: pyttsx3 (Windows SAPI, always available on Windows)
  Tier 3: Silent log (last resort, app never crashes)

Every edge case is handled — no unhandled exceptions, no silent failures,
no crashes from missing files, missing packages, bad audio devices, or
long text. The engine always reports its status and falls back gracefully.

Models expected at: omni/models/
  - kokoro-v1.0.onnx   (~80MB, from nazdridoy/kokoro-tts releases)
  - voices-v1.0.bin    (~2MB,  from nazdridoy/kokoro-tts releases)
"""

from __future__ import annotations

import os
import sys
import time
import queue
import threading
import platform
from pathlib import Path
from typing import Optional, Callable

import numpy as np
from loguru import logger


# ─── Voice Catalog ────────────────────────────────────────────────────────────
# All voices available in kokoro-onnx v1.0 from nazdridoy/kokoro-tts releases.
# Format: voice_id -> (category, description)

VOICE_CATALOG: dict[str, tuple[str, str]] = {
    # ── American Female ──────────────────────────────────────────────────────
    "af_sarah":    ("🇺🇸 American Female", "Bright & warm — best for demos"),
    "af_bella":    ("🇺🇸 American Female", "Professional & clear"),
    "af_nicole":   ("🇺🇸 American Female", "Calm & measured"),
    "af_jessica":  ("🇺🇸 American Female", "Upbeat & energetic"),
    "af_heart":    ("🇺🇸 American Female", "Expressive & emotional"),
    "af_nova":     ("🇺🇸 American Female", "Smooth & soothing"),
    "af_sky":      ("🇺🇸 American Female", "Friendly & approachable"),
    "af_kore":     ("🇺🇸 American Female", "Clear & articulate"),
    "af_river":    ("🇺🇸 American Female", "Steady & reliable"),
    "af_aoede":    ("🇺🇸 American Female", "Modern & contemporary"),
    "af_alloy":    ("🇺🇸 American Female", "Neutral & balanced"),
    "af_heart_02": ("🇺🇸 American Female", "Expressive v2"),
    "af_nova_02":  ("🇺🇸 American Female", "Smooth v2"),
    # ── American Male ─────────────────────────────────────────────────────────
    "am_michael":  ("🇺🇸 American Male",   "Deep & steady"),
    "am_patrick":  ("🇺🇸 American Male",   "Warm & friendly"),
    "am_fen":      ("🇺🇸 American Male",   "Soft & gentle"),
    "am_earl":     ("🇺🇸 American Male",   "Rich & commanding"),
    "am_arthur":   ("🇺🇸 American Male",   "Clear & authoritative"),
    "am_liam":     ("🇺🇸 American Male",   "Natural & conversational"),
    "am_ryan":     ("🇺🇸 American Male",   "Calm & relaxed"),
    "am_antonio":  ("🇺🇸 American Male",   "Confident & direct"),
    "am_finley":   ("🇺🇸 American Male",   "Friendly & approachable"),
    "am_toby":     ("🇺🇸 American Male",   "Bright & upbeat"),
    "am_david":    ("🇺🇸 American Male",   "Strong & clear"),
    # ── British Female ───────────────────────────────────────────────────────
    "bf_gemma":    ("🇬🇧 British Female",  "Elegant & refined"),
    "bf_emma":     ("🇬🇧 British Female",  "Warm & natural"),
    "bf_vickie":   ("🇬🇧 British Female",  "Crisp & precise"),
    "bf_emma_low": ("🇬🇧 British Female",  "Warm, lower pitch"),
    "bf_isabelle": ("🇬🇧 British Female",  "Gentle & soft"),
    "bf_lily":     ("🇬🇧 British Female",  "Clear & articulate"),
    # ── British Male ─────────────────────────────────────────────────────────
    "bm_george":   ("🇬🇧 British Male",    "Classic & authoritative"),
    "bm_lewis":    ("🇬🇧 British Male",    "Clear & confident"),
    # ── Half Accent ──────────────────────────────────────────────────────────
    "hf_xiaoming": ("🌏 Half Accent",      "International, Chinese-English"),
    "hm_alex":     ("🌏 Half Accent",      "International, neutral male"),
    # ── Special ─────────────────────────────────────────────────────────────
    "zf_alpha":    ("🎨 Special",          "Experimental"),
    "zm_secondary":("🎨 Special",          "Secondary character"),
}

# Default recommended voices for different use cases
VOICE_DEFAULTS = {
    "demo":        "af_sarah",   # Best for hackathon demos
    "accessibility": "am_michael", # Deeper, clearer for screen reader use
    "british":     "bf_gemma",   # Premium / formal feel
    "male":        "am_patrick", # Warm male voice
}


class AudioBackend:
    """Abstraction layer for audio playback — handles sounddevice + simpleaudio fallback."""

    def __init__(self):
        self._sd_available = False
        self._sa_available = False
        self._check_backends()

    def _check_backends(self) -> None:
        try:
            import sounddevice as _sd
            self._sd_available = True
            logger.debug("AudioBackend: sounddevice available")
        except ImportError:
            logger.debug("AudioBackend: sounddevice not installed")

        if not self._sd_available:
            try:
                import simpleaudio as _sa
                self._sa_available = True
                logger.debug("AudioBackend: simpleaudio available")
            except ImportError:
                logger.debug("AudioBackend: simpleaudio not installed")

    def play(self, audio: np.ndarray, sample_rate: int = 24000) -> bool:
        """
        Play audio array. Returns True on success, False on any failure.
        Never raises — all exceptions are caught and logged.
        """
        if audio is None or len(audio) == 0:
            logger.warning("AudioBackend: empty audio buffer, nothing to play")
            return False

        # Normalise to int16 PCM
        try:
            if audio.dtype == np.float32 or audio.dtype == np.float64:
                audio = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            elif audio.dtype != np.int16:
                audio = audio.astype(np.int16)
        except Exception as e:
            logger.error(f"AudioBackend: failed to normalise audio dtype {audio.dtype}: {e}")
            return False

        # Try sounddevice first
        if self._sd_available:
            try:
                import sounddevice as sd
                sd.play(audio, samplerate=sample_rate)
                sd.wait()  # Block until playback finishes
                return True
            except Exception as e:
                logger.warning(f"AudioBackend: sounddevice playback failed: {e}")
                # Fall through to simpleaudio

        # Try simpleaudio as fallback
        if self._sa_available:
            try:
                import simpleaudio as sa
                play_obj = sa.play_buffer(audio, num_channels=1, bytes_per_sample=2, sample_rate=sample_rate)
                play_obj.wait()
                return True
            except Exception as e:
                logger.warning(f"AudioBackend: simpleaudio playback failed: {e}")
                # Fall through to silent

        # Nothing available — log the text instead
        logger.warning(f"AudioBackend: no playback backend available (sounddevice={self._sd_available}, simpleaudio={self._sa_available})")
        return False

    def stop(self) -> None:
        """Stop any ongoing playback."""
        if self._sd_available:
            try:
                import sounddevice as sd
                sd.stop()
            except Exception:
                pass
        if self._sa_available:
            try:
                import simpleaudio as sa
                sa.stop_all_operations()
            except Exception:
                pass


class KokoroTTS:
    """
    Three-tier TTS engine for OMNI.

    Usage:
        tts = KokoroTTS(voice="af_sarah", speed=1.0)
        tts.speak("Hello world", callback=on_complete)

    Properties:
        is_speaking: bool — True while audio is being generated/playback
        available_voices: dict — catalog of all available voices
        engine_type: str — "kokoro-onnx" | "pyttsx3" | "silent"
        engine_info: str — human-readable status string
    """

    # Class-level instance so settings can inspect it
    _instance: Optional["KokoroTTS"] = None

    def __init__(
        self,
        voice: str = "af_sarah",
        speed: float = 1.0,
        model_dir: Optional[str] = None,
    ):
        # Singleton for settings inspection
        KokoroTTS._instance = self

        # Validate & clamp parameters
        self._voice = self._validate_voice(voice)
        self._speed = self._clamp_speed(speed)

        # Resolve model directory
        if model_dir:
            self._model_dir = Path(model_dir)
        else:
            # Default: omni/models/ (next to omni/ directory)
            omni_dir = Path(__file__).resolve().parent  # omni/tts/
            self._model_dir = omni_dir.parent.parent / "models"  # omni/../models/

        self._model_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.is_speaking = False
        self._callback_fired = False
        self._current_thread: Optional[threading.Thread] = None
        self._audio_backend = AudioBackend()

        # Engine references
        self._kokoro = None       # kokoro-onnx instance
        self._sapi_engine = None  # pyttsx3 engine
        self._sapi_available = False

        # Determine engine type (set after load)
        self._engine_type = "silent"
        self._engine_info = "No TTS engine loaded"

        # Load all engines in priority order
        self._load_tts_engine()

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def available_voices(self) -> dict:
        return VOICE_CATALOG

    @property
    def engine_type(self) -> str:
        return self._engine_type

    @property
    def engine_info(self) -> str:
        return self._engine_info

    @property
    def voice(self) -> str:
        return self._voice

    @voice.setter
    def voice(self, value: str) -> None:
        self._voice = self._validate_voice(value)

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        self._speed = self._clamp_speed(value)
        # Apply to SAPI engine immediately if it's active
        if self._sapi_available and self._sapi_engine is not None:
            try:
                self._sapi_engine.setProperty('rate', int(200 * self._speed))
            except Exception:
                pass

    @property
    def model_dir(self) -> Path:
        return self._model_dir

    @property
    def model_files_present(self) -> tuple[bool, bool]:
        model = self._model_dir / "kokoro-v1.0.onnx"
        voices = self._model_dir / "voices-v1.0.bin"
        return model.exists(), voices.exists()

    # ── Validation helpers ─────────────────────────────────────────────────

    def _validate_voice(self, voice: str) -> str:
        """Return the voice if valid, otherwise return the demo default."""
        if voice in VOICE_CATALOG:
            return voice
        # Try with _02 suffix variants
        for v in VOICE_CATALOG:
            if v.startswith(voice) or voice.startswith(v):
                return v
        logger.warning(f"Voice '{voice}' not in catalog, using 'af_sarah'")
        return "af_sarah"

    def _clamp_speed(self, speed: float) -> float:
        """Clamp speed to the valid range [0.5, 2.0]."""
        if not isinstance(speed, (int, float)):
            return 1.0
        return max(0.5, min(2.0, float(speed)))

    # ── Model file paths ───────────────────────────────────────────────────

    @property
    def _model_path(self) -> Path:
        return self._model_dir / "kokoro-v1.0.onnx"

    @property
    def _voices_path(self) -> Path:
        return self._model_dir / "voices-v1.0.bin"

    # ── Engine loading (three-tier) ────────────────────────────────────────

    def _load_tts_engine(self) -> None:
        """
        Attempt to load engines in priority order.
        Tier 1: Kokoro-ONNX
        Tier 2: pyttsx3 (Windows SAPI)
        Tier 3: Silent (log only)
        """
        # ── Tier 1: Kokoro-ONNX ────────────────────────────────────────────
        self._try_load_kokoro()

        if self._kokoro is not None:
            return  # Kokoro loaded successfully

        # ── Tier 2: pyttsx3 / Windows SAPI ─────────────────────────────────
        self._try_load_sapi()

        if self._sapi_available:
            return  # SAPI loaded successfully

        # ── Tier 3: Silent fallback ─────────────────────────────────────────
        self._engine_type = "silent"
        self._engine_info = (
            "No TTS engine available. "
            f"Model files should be at: {self._model_dir}\n"
            "  - kokoro-v1.0.onnx (download from GitHub releases)\n"
            "  - voices-v1.0.bin  (download from GitHub releases)\n"
            "Run: python scripts/download_models.py"
        )
        logger.warning(f"TTS: all engines failed, operating in SILENT mode. Model dir: {self._model_dir}")

    def _try_load_kokoro(self) -> None:
        """Attempt to load Kokoro-ONNX. Sets self._kokoro on success."""
        # Check files first with detailed messaging
        model_exists = self._model_path.exists()
        voices_exist = self._voices_path.exists()

        if not model_exists:
            logger.warning(f"Kokoro: model file not found — {self._model_path}")
        if not voices_exist:
            logger.warning(f"Kokoro: voices file not found — {self._voices_path}")

        if not (model_exists and voices_exist):
            missing = []
            if not model_exists:
                missing.append(f"  kokoro-v1.0.onnx")
            if not voices_exist:
                missing.append(f"  voices-v1.0.bin")
            logger.info(f"Kokoro: missing model files in {self._model_dir}:\n" + "\n".join(missing))
            return  # Early exit — don't try importing if files are missing

        # Try importing kokoro_onnx
        try:
            from kokoro_onnx import Kokoro
        except ImportError as e:
            logger.warning(f"Kokoro: kokoro-onnx not installed ({e}). Run: pip install kokoro-onnx")
            return

        # Try importing onnxruntime
        try:
            import onnxruntime as ort
        except ImportError as e:
            logger.warning(f"Kokoro: onnxruntime not installed ({e}). Run: pip install onnxruntime")
            return

        # Try instantiating the model
        try:
            providers = []
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers.append("CUDAExecutionProvider")
                logger.info("Kokoro: CUDA available, using GPU acceleration")
            providers.append("CPUExecutionProvider")
            logger.info(f"Kokoro: providers = {providers}")

            self._kokoro = Kokoro(
                str(self._model_path),
                str(self._voices_path),
            )
            self._engine_type = "kokoro-onnx"
            self._engine_info = (
                f"Kokoro-ONNX v1.0 | Voice: {self._voice} | Speed: {self._speed} | "
                f"Models: {self._model_path.name}"
            )
            logger.info(f"TTS: Kokoro-ONNX loaded successfully ✓")
            logger.info(f"      Kokoro speed: {self._speed}x | voice: {self._voice}")

        except FileNotFoundError as e:
            logger.warning(f"Kokoro: model file not found during load: {e}")
        except Exception as e:
            logger.warning(f"Kokoro: failed to instantiate model: {e}")
            # Don't fall through to SAPI here — let the outer caller handle it
            self._kokoro = None

    def _try_load_sapi(self) -> None:
        """Attempt to load Windows SAPI via pyttsx3. Sets self._sapi_available on success."""
        if platform.system() != "Windows":
            logger.info("SAPI: not on Windows, skipping")
            return

        # Try pyttsx3
        try:
            import pyttsx3
        except ImportError:
            logger.warning("SAPI: pyttsx3 not installed. Run: pip install pyttsx3")
            self._sapi_available = False
            return

        try:
            self._sapi_engine = pyttsx3.init()

            # Enumerate available voices
            try:
                voices = self._sapi_engine.getProperty('voices')
                if not voices:
                    logger.warning("SAPI: no voices found on this system")
                    self._sapi_engine = None
                    self._sapi_available = False
                    return

                voice_info = [f"{v.name} ({v.id[:40]}...)" for v in voices[:5]]
                logger.info(f"SAPI: {len(voices)} voices available. Top 5: {voice_info}")

                # Set preferred voice (prefer female, fall back to first)
                selected = None
                for v in voices:
                    if 'female' in v.name.lower() or 'samantha' in v.name.lower() or 'zira' in v.name.lower():
                        selected = v
                        break
                if selected is None and voices:
                    selected = voices[0]

                if selected:
                    self._sapi_engine.setProperty('voice', selected.id)
                    logger.info(f"SAPI: selected voice: {selected.name}")

            except Exception as e:
                logger.warning(f"SAPI: could not enumerate voices: {e}")

            # Set initial rate
            try:
                self._sapi_engine.setProperty('rate', int(200 * self._speed))
            except Exception:
                pass

            self._sapi_available = True
            self._engine_type = "pyttsx3"
            self._engine_info = (
                f"Windows SAPI | Voice: {self._sapi_engine.getProperty('voices')[0].name if self._sapi_engine else 'unknown'} | "
                f"Speed: {self._speed}x"
            )
            logger.info("TTS: Windows SAPI loaded successfully ✓")

        except ImportError:
            logger.warning("SAPI: pyttsx3 import failed")
            self._sapi_available = False
        except Exception as e:
            logger.warning(f"SAPI: failed to initialize: {e}")
            self._sapi_available = False

    # ── Public API ─────────────────────────────────────────────────────────

    def speak(self, text: str, callback: Optional[Callable] = None) -> None:
        """
        Speak `text` asynchronously in a background thread.
        If already speaking, stop current playback first (no queue, no overlap).

        Args:
            text: Text to speak. Empty string is handled gracefully.
            callback: Called when speech completes (always called, even on error).
        """
        # Guard: empty text
        if not text or not text.strip():
            logger.debug("TTS: empty text, skipping")
            if callback:
                callback()
            return

        # Guard: text too long — chunk it to prevent memory issues
        # Kokoro can handle long text but very long strings (500+ chars)
        # can cause OOM on low-RAM systems. Chunk at word boundaries.
        text = text.strip()
        if len(text) > 800:
            logger.debug(f"TTS: text too long ({len(text)} chars), chunking")
            text = self._chunk_text(text)

        # Stop any current speech before starting new
        self.stop()

        # Reset state for new speech
        self.is_speaking = True
        self._callback_fired = False

        # Dispatch to the appropriate engine
        if self._kokoro is not None:
            self._current_thread = threading.Thread(
                target=self._speak_kokoro,
                args=(text, callback),
                daemon=True,
                name="TTS-Kokoro",
            )
        elif self._sapi_available:
            self._current_thread = threading.Thread(
                target=self._speak_sapi,
                args=(text, callback),
                daemon=True,
                name="TTS-SAPI",
            )
        else:
            # Silent fallback — log text and fire callback immediately
            self._log_silent(text, callback)
            return

        self._current_thread.start()

    def stop(self) -> None:
        """
        Stop any current or pending speech.
        Safe to call even when not speaking — idempotent.
        """
        if not self.is_speaking and self._current_thread is None:
            return

        logger.debug(f"TTS: stop() called (engine={self._engine_type})")

        # Stop audio playback
        self._audio_backend.stop()

        # Stop SAPI engine if active
        if self._sapi_available and self._sapi_engine is not None:
            try:
                self._sapi_engine.stop()
            except Exception:
                pass

        # Wait for the thread to finish (with timeout)
        if self._current_thread is not None and self._current_thread.is_alive():
            try:
                self._current_thread.join(timeout=1.0)
            except Exception:
                pass

        self.is_speaking = False
        self._current_thread = None

        # Fire any pending callback with "stopped" indication
        if not self._callback_fired:
            self._callback_fired = True

    def preview_voice(self, voice: str, callback: Optional[Callable] = None) -> None:
        """
        Preview a specific voice by speaking a test sentence.
        Uses the current speed setting.
        """
        descriptions = {
            "af_sarah":    "Hello! I'm Sarah. OMNI is ready to assist you.",
            "am_michael":  "Hello! I'm Michael. OMNI is ready to assist you.",
            "bf_gemma":    "Hello! I'm Gemma. OMNI is ready to assist you.",
            "am_patrick":  "Hello! I'm Patrick. OMNI is ready to assist you.",
        }
        test_sentence = descriptions.get(voice, "Hello! OMNI is ready to assist you.")
        original_voice = self._voice
        self._voice = self._validate_voice(voice)
        self.speak(test_sentence, callback=lambda: setattr(self, '_voice', original_voice) or (callback and callback()))

    def get_status(self) -> dict:
        """Return current TTS engine status as a dict."""
        return {
            "engine_type": self._engine_type,
            "engine_info": self._engine_info,
            "voice": self._voice,
            "speed": self._speed,
            "is_speaking": self.is_speaking,
            "model_dir": str(self._model_dir),
            "model_present": self.model_files_present[0],
            "voices_present": self.model_files_present[1],
            "available_voices_count": len(VOICE_CATALOG),
        }

    # ── Private: text chunking ─────────────────────────────────────────────

    def _chunk_text(self, text: str, max_chars: int = 400) -> str:
        """
        Split long text into sentences or word-bounded chunks.
        Kokoro handles ~400 chars comfortably on 8GB RAM.
        """
        if len(text) <= max_chars:
            return text

        # Try to split on sentence boundaries first
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_chars:
                current = (current + " " + sentence).strip()
            else:
                if current:
                    chunks.append(current)
                # If single sentence is too long, split on words
                if len(sentence) > max_chars:
                    words = sentence.split()
                    for word in words:
                        if len(current) + len(word) + 1 <= max_chars:
                            current = (current + " " + word).strip()
                        else:
                            if current:
                                chunks.append(current)
                            current = word
                else:
                    current = sentence
        if current:
            chunks.append(current)

        # Return just the first chunk for now (full chunking = Phase 3)
        return chunks[0] if chunks else text[:max_chars]

    # ── Private: silent fallback ───────────────────────────────────────────

    def _log_silent(self, text: str, callback: Optional[Callable]) -> None:
        """Called when no TTS engine is available."""
        logger.info(f"TTS [silent]: {text[:100]}{'...' if len(text) > 100 else ''}")
        self.is_speaking = False
        self._callback_fired = True
        if callback:
            try:
                callback()
            except Exception as e:
                logger.warning(f"TTS callback error: {e}")

    # ── Private: Kokoro-ONNX speak ─────────────────────────────────────────

    def _speak_kokoro(self, text: str, callback: Optional[Callable]) -> None:
        """Generate and play audio using Kokoro-ONNX."""
        try:
            # Validate voice is still loaded (could have been changed mid-thread)
            if self._kokoro is None:
                self._log_silent(text, callback)
                return

            # Generate audio
            audio = self._kokoro.generate(text, voice=self._voice, speed=self._speed)

            if audio is None:
                logger.warning("Kokoro: generate() returned None")
                self._log_silent(text, callback)
                return

            # Ensure numpy array
            if not isinstance(audio, np.ndarray):
                try:
                    audio = np.array(audio)
                except Exception as e:
                    logger.error(f"Kokoro: could not convert audio to numpy: {e}")
                    self._log_silent(text, callback)
                    return

            # Determine sample rate (kokoro-onnx outputs 24kHz by default)
            sr = 24000
            if hasattr(audio, 'sr'):
                sr = int(getattr(audio, 'sr', 24000))
            elif len(audio.shape) > 1 and audio.shape[1] > 1:
                sr = getattr(audio, 'sampling_rate', 24000)

            # Play audio
            success = self._audio_backend.play(audio, sr)
            if not success:
                # Playback failed — log as fallback
                self._log_silent(text, callback)
                return

        except MemoryError:
            logger.error("Kokoro: out of memory generating audio. Text may be too long.")
            self._log_silent(text, callback)
        except Exception as e:
            logger.error(f"Kokoro speech error: {e}")
            self._log_silent(text, callback)
        finally:
            self.is_speaking = False
            if not self._callback_fired:
                self._callback_fired = True
                if callback:
                    try:
                        callback()
                    except Exception as e:
                        logger.warning(f"TTS callback error: {e}")

    # ── Private: Windows SAPI speak ────────────────────────────────────────

    def _speak_sapi(self, text: str, callback: Optional[Callable]) -> None:
        """Speak text using Windows SAPI via pyttsx3."""
        engine = None
        try:
            # Get or create SAPI engine
            if self._sapi_engine is not None:
                engine = self._sapi_engine
            else:
                import pyttsx3
                engine = pyttsx3.init()

            # Update rate in case speed changed
            try:
                engine.setProperty('rate', int(200 * self._speed))
            except Exception:
                pass

            # Speak text
            engine.say(text)
            engine.runAndWait()

        except AttributeError:
            # Engine was stopped / invalid
            logger.warning("SAPI: engine became invalid, re-initializing")
            try:
                import pyttsx3
                self._sapi_engine = pyttsx3.init()
                self._sapi_engine.say(text)
                self._sapi_engine.runAndWait()
            except Exception as e2:
                logger.error(f"SAPI re-init failed: {e2}")
        except Exception as e:
            logger.error(f"SAPI speech error: {e}")
            self._log_silent(text, callback)
        finally:
            self.is_speaking = False
            if not self._callback_fired:
                self._callback_fired = True
                if callback:
                    try:
                        callback()
                    except Exception as e:
                        logger.warning(f"TTS callback error: {e}")

    # ── Static helpers ─────────────────────────────────────────────────────

    @staticmethod
    def get_instance() -> Optional["KokoroTTS"]:
        """Return the current TTS instance (for settings inspection)."""
        return KokoroTTS._instance

    @staticmethod
    def get_model_download_url() -> tuple[str, str]:
        """Return the GitHub release URLs for model files."""
        return (
            "https://github.com/nazdridoy/kokoro-tts/releases/tag/v1.0.0",
            "https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/kokoro-v1.0.onnx",
            "https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/voices-v1.0.bin",
        )