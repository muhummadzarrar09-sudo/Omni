"""
OMNI V3 - Wake Word V4 - THE BEST OF THE BEST

Uses openWakeWord with custom-trained or pre-trained "Hey Jarvis" / "Alexa" / "Hey Mycroft" models.
Sub-100ms latency, runs on CPU via ONNX Runtime, no cloud needed.

Backend priority:
  1. openWakeWord (free, ONNX, 100% offline, <100ms)
  2. Porcupine (best accuracy, requires Picovoice API key)
  3. Whisper-tiny (always works if faster-whisper is installed)
  4. Energy threshold (always works, least accurate)
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
    logger = logging.getLogger("WakeWordBest")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# === Backend 1: openWakeWord (best free option) ===
class OpenWakeWordBest:
    def __init__(self):
        self.model = None
        self.backend_name = "openwakeword"
        self.model_name = "hey_jarvis"
        try:
            from openwakeword.model import Model
            # Pre-trained models: hey_jarvis, alexa, hey_mycroft, hey_rhodora, hey_siri
            # For "Hey OMNI", "hey_jarvis" is the closest sound
            self.model = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx"
            )
            logger.info("WakeWord Best: openWakeWord loaded (hey_jarvis as proxy for 'Hey OMNI')")
        except ImportError:
            logger.debug("openwakeword not installed - pip install openwakeword")
            self.model = None
            self.backend_name = None
        except Exception as e:
            logger.warning(f"openwakeword init failed: {e}")
            self.model = None
            self.backend_name = None

    def is_available(self):
        return self.model is not None

    def predict(self, audio_int16) -> bool:
        try:
            import numpy as np
            audio = np.frombuffer(audio_int16, dtype=np.int16).astype(np.float32) / 32768.0
            pred = self.model.predict(audio)
            for mdl_name, score in pred.items():
                if score > 0.3:  # sensitivity threshold
                    logger.info(f"openWakeWord detected '{mdl_name}' with score {score:.2f}")
                    return True
        except Exception as e:
            logger.debug(f"openWakeWord predict: {e}")
        return False


# === Backend 2: Picovoice Porcupine (best accuracy) ===
class PorcupineWakeBackend:
    def __init__(self):
        self.detector = None
        self.backend_name = "porcupine"
        try:
            import pvporcupine
            import os
            access_key = os.environ.get("PICOVOICE_ACCESS_KEY")
            if access_key:
                self.detector = pvporcupine.create(
                    access_key=access_key,
                    keywords=["jarvis"],
                    sensitivities=[0.5]
                )
                logger.info("WakeWord Best: Porcupine loaded (jarvis keyword)")
            else:
                logger.debug("Porcupine: no PICOVOICE_ACCESS_KEY set, skipping")
                self.detector = None
                self.backend_name = None
        except ImportError:
            logger.debug("pvporcupine not installed")
            self.detector = None
            self.backend_name = None
        except Exception as e:
            logger.warning(f"Porcupine init failed: {e}")
            self.detector = None
            self.backend_name = None

    def is_available(self):
        return self.detector is not None

    def predict(self, audio_int16) -> bool:
        try:
            import struct
            pcm = struct.unpack_from(f"h{len(audio_int16)//2}", audio_int16)
            result = self.detector.process(pcm)
            return result >= 0
        except Exception as e:
            logger.debug(f"Porcupine predict: {e}")
        return False


# === Backend 3: Whisper-tiny (always works) ===
class WhisperWakeBackend:
    SIMILAR = [
        "hey omni", "hey ome", "hey omeny", "hey oni", "hey amy",
        "hey homie", "hey on the", "hey only", "hey money", "hey honestly",
        "hey ommy", "hey o", "he omni", "hey om", "a omni",
        "hey, omni", "hey, only", "omni",
    ]
    def __init__(self):
        self.backend_name = "whisper-tiny"
        self.model = None
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            logger.info("WakeWord Best: Whisper-tiny loaded")
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
            segments, _ = self.model.transcribe(
                audio, language="en", without_timestamps=True,
                beam_size=1, vad_filter=True
            )
            text = " ".join(seg.text for seg in segments).lower().strip()
            if not text:
                return False
            for phrase in self.SIMILAR:
                if phrase in text:
                    return True
            if "omni" in text and len(text) < 25:
                return True
        except Exception as e:
            logger.debug(f"Whisper wake predict: {e}")
        return False


# === Backend 4: Energy (always works, no ML) ===
class EnergyWakeBackend:
    def __init__(self):
        self.backend_name = "energy"
        self.threshold = 0.05
        self.min_duration_sec = 0.3
        logger.info(f"WakeWord Best: Energy-only backend (any sound above {self.threshold} RMS)")

    def is_available(self):
        return True

    def predict_buffer(self, audio_int16, sample_rate=16000) -> bool:
        try:
            import numpy as np
            audio = np.frombuffer(audio_int16, dtype=np.int16).astype(np.float32) / 32768.0
            if len(audio) < sample_rate * self.min_duration_sec:
                return False
            rms = float(np.sqrt(np.mean(audio ** 2)))
            return rms > self.threshold
        except Exception:
            return False


class WakeWordServiceBest:
    """The BEST wake word service. Multi-backend. Always-on."""

    def __init__(self, on_wake: Callable[[], None], on_command: Optional[Callable[[str], None]] = None):
        self.on_wake = on_wake
        self.on_command = on_command
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Try backends in priority order
        self.backends = []
        for cls in [OpenWakeWordBest, PorcupineWakeBackend, WhisperWakeBackend, EnergyWakeBackend]:
            try:
                b = cls()
                if b.is_available():
                    self.backends.append(b)
                    logger.info(f"Registered backend: {b.backend_name}")
            except Exception as e:
                logger.debug(f"Backend {cls.__name__} failed: {e}")

        if not self.backends:
            logger.warning("WakeWord Best: NO backends available")
        else:
            logger.info(f"WakeWord Best: {len(self.backends)} backends | primary={self.backends[0].backend_name}")

    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, name="WakeWordBest", daemon=True)
        self._thread.start()
        logger.info("🟢 WakeWord Best service started")

    def stop(self):
        self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("🔴 WakeWord Best service stopped")

    def _listen_loop(self):
        try:
            import sounddevice as sd

            block_size = 1280  # 80ms at 16kHz
            sample_rate = 16000
            audio_q: queue.Queue = queue.Queue()

            def audio_callback(indata, frames, time_info, status):
                audio_q.put(bytes(indata))

            with sd.RawInputStream(
                samplerate=sample_rate,
                channels=1,
                dtype='int16',
                blocksize=block_size,
                callback=audio_callback,
            ):
                logger.info("🎤 Listening for 'Hey OMNI' (always-on)...")
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
                        continue
                    woke = False
                    for backend in self.backends:
                        if hasattr(backend, 'predict'):
                            try:
                                if backend.predict(chunk):
                                    woke = True
                                    break
                            except Exception as e:
                                logger.debug(f"{backend.backend_name} predict: {e}")
                        elif hasattr(backend, 'predict_buffer'):
                            try:
                                if backend.predict_buffer(chunk, sample_rate):
                                    woke = True
                                    break
                            except Exception as e:
                                logger.debug(f"{backend.backend_name} predict_buffer: {e}")
                    if woke:
                        logger.info(f"🟢 Wake word detected ({self.backends[0].backend_name})!")
                        wake_cooldown_until = now + 2
                        in_command_mode = True
                        command_mode_start = now
                        post_wake_audio = [chunk]
                        try:
                            self.on_wake()
                        except Exception as e:
                            logger.error(f"on_wake: {e}")
                    elif in_command_mode:
                        post_wake_audio.append(chunk)
                        if now - command_mode_start > 5.0:
                            audio_bytes = b"".join(post_wake_audio)
                            text = self._transcribe_command(audio_bytes)
                            if text:
                                logger.info(f"📝 Command: '{text}'")
                                if self.on_command:
                                    try:
                                        self.on_command(text)
                                    except Exception as e:
                                        logger.error(f"on_command: {e}")
                            in_command_mode = False
                            post_wake_audio = []
        except ImportError as e:
            logger.error(f"WakeWord Best: sounddevice not available: {e}")
        except Exception as e:
            logger.error(f"WakeWord Best crashed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _transcribe_command(self, audio_bytes: bytes) -> Optional[str]:
        try:
            import numpy as np
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            try:
                from faster_whisper import WhisperModel
                if not hasattr(self, '_whisper'):
                    try:
                        self._whisper = WhisperModel("base.en", device="cpu", compute_type="int8")
                    except Exception:
                        self._whisper = None
                if self._whisper:
                    segments, _ = self._whisper.transcribe(
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
