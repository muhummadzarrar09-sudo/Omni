"""
OMNI V3 - Wake Word V3 - Always-on "Hey OMNI" detection
Works WITHOUT external ML models. Uses:
  - sounddevice (already installed)
  - Energy-based VAD (voice activity detection)
  - Whisper-tiny to transcribe short clips and check for "hey omni"
  - Falls back to a simple energy threshold if Whisper is unavailable

Three backends in priority order:
  1. openwakeword (best accuracy, requires pip install openwakeword)
  2. whisper-tiny pseudo-wake (always works, ~100ms latency)
  3. Energy-only "say anything loud" mode (always works, ~0ms latency)
"""
from __future__ import annotations
import threading
import time
import queue
from pathlib import Path
from typing import Callable, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("WakeWordV3")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


# === Backend 1: openwakeword (if installed) ===
class OpenWakeWordBackend:
    def __init__(self):
        self.model = None
        self.backend_name = "openwakeword"
        try:
            from openwakeword.model import Model
            self.model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            logger.info("WakeWord V3: openwakeword backend loaded (say 'hey jarvis' or 'alexa')")
        except Exception as e:
            logger.debug(f"openwakeword init failed: {e}")
            self.model = None
            self.backend_name = None

    def is_available(self):
        return self.model is not None

    def predict(self, audio_int16) -> bool:
        try:
            import numpy as np
            audio = np.frombuffer(audio_int16, dtype=np.int16).astype(np.float32) / 32768.0
            pred = self.model.predict(audio)
            for mdl, score in pred.items():
                if score > 0.3:
                    return True
        except Exception as e:
            logger.debug(f"openwakeword predict: {e}")
        return False


# === Backend 2: Whisper-tiny pseudo-wake ===
class WhisperWakeBackend:
    """
    Continuously records 2-second windows, transcribes with tiny.en,
    fires callback if transcription contains 'hey omni' or similar.
    Slightly more CPU but always works.
    """
    SIMILAR_PHRASES = [
        "hey omni", "hey omeny", "hey on me", "hey oni", "hey amy",
        "hey homie", "hey on the", "hey only", "a omni", "hey, only",
        "hey, omni", "hey ommy", "hey money", "hey honestly",
        "omni", "hey ome", "he omni", "hey om", "hey o",
    ]

    def __init__(self):
        self.backend_name = "whisper-tiny"
        self.model = None
        self.sample_rate = 16000
        try:
            from faster_whisper import WhisperModel
            # tiny.en is the fastest, runs on CPU fine
            self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            logger.info("WakeWord V3: Whisper-tiny backend loaded (detects 'hey omni')")
        except Exception as e:
            logger.warning(f"Whisper wake backend init failed: {e}")
            self.model = None
            self.backend_name = None

    def is_available(self):
        return self.model is not None

    def predict(self, audio_int16) -> bool:
        if not self.model:
            return False
        try:
            import numpy as np
            audio = np.frombuffer(audio_int16, dtype=np.int16).astype(np.float32) / 32768.0
            # Transcribe
            segments, _ = self.model.transcribe(
                audio,
                language="en",
                without_timestamps=True,
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(seg.text for seg in segments).lower().strip()
            if not text:
                return False
            # Check for wake phrase or close variations
            for phrase in self.SIMILAR_PHRASES:
                if phrase in text:
                    logger.info(f"Wake phrase detected: '{text}' (matched '{phrase}')")
                    return True
            # Also check single-word: "omni"
            if "omni" in text and len(text) < 20:
                logger.info(f"Wake word 'omni' detected in: '{text}'")
                return True
        except Exception as e:
            logger.debug(f"Whisper wake predict: {e}")
        return False


# === Backend 3: Energy threshold (always works) ===
class EnergyWakeBackend:
    """
    Detects 'wake' by sustained loud audio above threshold.
    Not a real wake word - fires on any loud sound. Useful as
    last-resort fallback when ML models are unavailable.
    """
    def __init__(self):
        self.backend_name = "energy"
        self.threshold = 0.05  # RMS threshold
        self.min_duration = 0.3  # seconds of sustained sound
        logger.info(f"WakeWord V3: Energy-only backend (any sound above {self.threshold} RMS for {self.min_duration}s)")

    def is_available(self):
        return True

    def predict_buffer(self, audio_int16, sample_rate=16000) -> bool:
        try:
            import numpy as np
            audio = np.frombuffer(audio_int16, dtype=np.int16).astype(np.float32) / 32768.0
            if len(audio) < sample_rate * self.min_duration:
                return False
            # Calculate RMS over the buffer
            rms = float(np.sqrt(np.mean(audio ** 2)))
            return rms > self.threshold
        except Exception as e:
            logger.debug(f"Energy predict: {e}")
        return False


# === Main Wake Word Service ===
class WakeWordServiceV3:
    """
    The butler that listens. Always-on background service.
    Picks the best available backend, runs in a thread,
    fires callback when wake word is heard.
    """
    def __init__(self, on_wake: Callable[[], None], on_command: Optional[Callable[[str], None]] = None):
        self.on_wake = on_wake          # fires when "hey omni" heard
        self.on_command = on_command    # fires with transcribed command
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._command_buffer: list = []  # accumulates post-wake audio

        # Try backends in order
        self.backends = []
        for backend_cls in [OpenWakeWordBackend, WhisperWakeBackend, EnergyWakeBackend]:
            try:
                b = backend_cls()
                if b.is_available():
                    self.backends.append(b)
                    logger.info(f"WakeWord V3: registered backend {b.backend_name}")
            except Exception as e:
                logger.debug(f"Backend {backend_cls.__name__} init failed: {e}")

        if not self.backends:
            logger.warning("WakeWord V3: NO backends available! Service will not function.")
        else:
            logger.info(f"WakeWord V3: {len(self.backends)} backends active, primary: {self.backends[0].backend_name}")

    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, name="WakeWordV3", daemon=True)
        self._thread.start()
        logger.info("🟢 WakeWord V3 service started (always-listening)")

    def stop(self):
        self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("🔴 WakeWord V3 service stopped")

    def _listen_loop(self):
        """Main loop - reads audio in 80ms chunks, runs backends"""
        try:
            import sounddevice as sd
            import numpy as np

            # Use a small block size for low latency
            block_size = 1280  # 80ms at 16kHz
            sample_rate = 16000
            audio_q = queue.Queue()

            def audio_callback(indata, frames, time_info, status):
                if status:
                    pass  # suppress overflow warnings
                audio_q.put(bytes(indata))

            # Open input stream
            with sd.RawInputStream(
                samplerate=sample_rate,
                channels=1,
                dtype='int16',
                blocksize=block_size,
                callback=audio_callback,
            ):
                logger.info("WakeWord V3: mic stream open, listening for 'Hey OMNI'...")
                wake_cooldown_until = 0
                post_wake_audio = []
                in_command_mode = False
                command_mode_start = 0

                while not self._stop_event.is_set():
                    try:
                        chunk = audio_q.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    now = time.time()
                    if now < wake_cooldown_until:
                        continue  # debounce

                    # Try each backend
                    woke = False
                    for backend in self.backends:
                        if hasattr(backend, 'predict'):
                            try:
                                if backend.predict(chunk):
                                    woke = True
                                    break
                            except Exception as e:
                                logger.debug(f"Backend {backend.backend_name} predict error: {e}")
                        elif hasattr(backend, 'predict_buffer'):
                            try:
                                if backend.predict_buffer(chunk, sample_rate):
                                    woke = True
                                    break
                            except Exception as e:
                                logger.debug(f"Backend {backend.backend_name} predict_buffer error: {e}")

                    if woke:
                        logger.info(f"🟢 Wake word detected via {self.backends[0].backend_name}!")
                        wake_cooldown_until = now + 2  # 2s cooldown
                        in_command_mode = True
                        command_mode_start = now
                        post_wake_audio = [chunk]
                        # Notify caller
                        try:
                            self.on_wake()
                        except Exception as e:
                            logger.error(f"on_wake callback error: {e}")

                    elif in_command_mode:
                        post_wake_audio.append(chunk)
                        # Capture 5 seconds of post-wake audio for command transcription
                        if now - command_mode_start > 5.0:
                            # Process the captured command
                            audio_bytes = b"".join(post_wake_audio)
                            command_text = self._transcribe_command(audio_bytes)
                            if command_text:
                                logger.info(f"📝 Post-wake command: '{command_text}'")
                                if self.on_command:
                                    try:
                                        self.on_command(command_text)
                                    except Exception as e:
                                        logger.error(f"on_command callback error: {e}")
                            else:
                                logger.debug("No command transcribed after wake")
                            in_command_mode = False
                            post_wake_audio = []

        except ImportError as e:
            logger.error(f"WakeWord V3: sounddevice not available: {e}")
        except Exception as e:
            logger.error(f"WakeWord V3 listen loop crashed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _transcribe_command(self, audio_bytes: bytes) -> Optional[str]:
        """Transcribe the post-wake audio to text using available STT."""
        try:
            import numpy as np
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            # Try faster_whisper first
            try:
                from faster_whisper import WhisperModel
                # Use small.en or whatever's available
                if not hasattr(self, '_whisper_for_commands'):
                    try:
                        self._whisper_for_commands = WhisperModel("base.en", device="cpu", compute_type="int8")
                    except Exception:
                        self._whisper_for_commands = None
                if self._whisper_for_commands:
                    segments, _ = self._whisper_for_commands.transcribe(
                        audio, language="en", without_timestamps=True, beam_size=1
                    )
                    text = " ".join(seg.text for seg in segments).strip()
                    if text and len(text) > 2:
                        return text
            except ImportError:
                pass
        except Exception as e:
            logger.debug(f"Command transcription: {e}")
        return None

    def is_available(self) -> bool:
        return len(self.backends) > 0

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "available": self.is_available(),
            "backends": [b.backend_name for b in self.backends],
            "primary_backend": self.backends[0].backend_name if self.backends else None,
        }
