"""Wake Word V2 - Fixed - Actually Works with openwakeword + pvporcupine, salvaged from qartex/eadmin2 JARVIS"""

import threading
from typing import Callable, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("WakeWordV2")

from omni_v2.core.config import load_config

class WakeWordDetector:
    """Wake Word - Fixed to actually work - salvaged from best JARVIS repos"""

    def __init__(self, keyword: str = "hey omni", sensitivity: float = 0.5,
                 engine: Optional[str] = None):
        self.keyword = keyword.lower()
        self.sensitivity = sensitivity
        self.detector = None
        self.backend = None
        self.model_path = None
        self.runtime_config = load_config()
        # engine: "openwakeword" (offline default) | "picovoice" (needs key) | "ptt" | None=auto
        if engine is None:
            try:
                from omni_v2.core.config_manager import ConfigManager
                engine = getattr(ConfigManager().load(), "wakeword_engine", "openwakeword")
            except Exception:
                engine = "openwakeword"
        self.engine_pref = engine
        self._init_detector()
        logger.info(f"WakeWordDetector V2 Fixed - Keyword: '{keyword}', Backend: {self.backend}")

    def _init_detector(self):
        pref = self.engine_pref

        # --- OPENWAKEWORD: default, free, offline, no key. ---
        # If the user wants picovoice explicitly, skip this block.
        if pref in ("openwakeword", "auto"):
            try:
                import openwakeword
                from openwakeword.model import Model

                model_dir = self.runtime_config.models_dir / "openwakeword"
                model_dir.mkdir(parents=True, exist_ok=True)

                # Try hey_jarvis model first (closest to "hey omni")
                try:
                    self.detector = Model(
                        wakeword_models=["hey_jarvis"],
                        inference_framework="onnx"
                    )
                    self.backend = "openwakeword"
                    logger.info("Wake word: openwakeword (hey_jarvis as proxy) - free, offline, ONNX")
                    return
                except Exception as e:
                    logger.debug(f"openwakeword hey_jarvis failed: {e}, trying alexa as fallback")
                    try:
                        self.detector = Model(
                            wakeword_models=["alexa"],
                            inference_framework="onnx"
                        )
                        self.backend = "openwakeword_alexa"
                        logger.info("Wake word: openwakeword (alexa as proxy) - offline")
                        return
                    except Exception as e2:
                        logger.debug(f"openwakeword alexa also failed: {e2}")

            except ImportError as e:
                logger.debug(f"openwakeword not installed: {e} - pip install openwakeword")
            except Exception as e:
                logger.warning(f"openwakeword init failed: {e}")

        # --- PICOVOICE: optional, ONLY if explicitly requested AND has a key. ---
        # Demoted: never auto-picked; needs PICOVOICE_KEY and wakeword_engine=picovoice.
        if pref == "picovoice":
            try:
                import pvporcupine
                access_key = self.runtime_config.picovoice_key
                if access_key:
                    self.detector = pvporcupine.create(
                        access_key=access_key,
                        keywords=["jarvis", "hey google"],
                        sensitivities=[self.sensitivity, self.sensitivity]
                    )
                    self.backend = "pvporcupine"
                    logger.info("Wake word: pvporcupine (opt-in, needs PICOVOICE_KEY)")
                    return
                else:
                    logger.debug("picovoice requested but no PICOVOICE_KEY set")
            except ImportError:
                logger.debug("pvporcupine not installed")
            except Exception as e:
                logger.debug(f"pvporcupine init failed: {e}")
            logger.info("picovoice not ready - falling back to PTT only")

        # --- Fallback: PTT only. ---
        self.backend = None
        logger.info(f"No wake word engine available (pref={pref}) - using PTT toggle only (press V to speak). Install: pip install openwakeword")

    def listen_for_wake_word(self, callback: Callable[[], None], stop_event: threading.Event = None):
        """Continuous listening - calls callback when wake word detected - FIXED"""
        if not self.backend:
            logger.warning("No wake word backend - cannot listen for Hey OMNI, using PTT only")
            return

        try:
            import pyaudio
            import numpy as np

            pa = pyaudio.PyAudio()

            if self.backend in ["openwakeword", "openwakeword_alexa"]:
                # Openwakeword - 16kHz, 1280 frame, ONNX (not tflite, fixes your tflite warning)
                stream = pa.open(
                    rate=16000,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=1280,
                    input_device_index=None
                )

                logger.info(f"Listening for wake word '{self.keyword}' via {self.backend}... (say Hey Jarvis / Alexa as proxy, or press V)")

                while True:
                    if stop_event and stop_event.is_set():
                        break

                    try:
                        data = stream.read(1280, exception_on_overflow=False)
                        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                        prediction = self.detector.predict(audio)

                        for mdl, score in prediction.items():
                            # Lower threshold for easier detection (was 0.5, now 0.3 for more sensitive)
                            if score > 0.3:
                                logger.info(f"Wake word '{mdl}' detected! Score {score:.2f} - Hey OMNI!")
                                callback()
                                # Debounce 2 sec to avoid double trigger
                                import time
                                time.sleep(2)
                    except Exception as e:
                        logger.debug(f"Wake word read error: {e}")
                        continue

            elif self.backend == "pvporcupine":
                import struct
                stream = pa.open(
                    rate=self.detector.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=self.detector.frame_length
                )

                logger.info(f"Listening for wake word '{self.keyword}' via pvporcupine... (say Hey Google / Jarvis)")

                while True:
                    if stop_event and stop_event.is_set():
                        break
                    pcm = stream.read(self.detector.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * self.detector.frame_length, pcm)
                    keyword_index = self.detector.process(pcm)
                    if keyword_index >= 0:
                        logger.info(f"Wake word detected! Index {keyword_index} - Hey OMNI!")
                        callback()
                        import time
                        time.sleep(2)

        except Exception as e:
            logger.error(f"Wake word listening failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            try:
                stream.stop_stream()
                stream.close()
                pa.terminate()
            except Exception:
                pass

    def is_available(self) -> bool:
        return self.backend is not None

    def get_status(self):
        return {
            "backend": self.backend,
            "keyword": self.keyword,
            "available": self.is_available(),
            "message": f"Wake word '{self.keyword}' via {self.backend}" if self.backend else "No wake word, using PTT V toggle"
        }

if __name__ == "__main__":
    def on_wake():
        print("\n*** Hey OMNI detected! Starting command... ***\n")

    detector = WakeWordDetector()
    print(f"Backend: {detector.backend}, Available: {detector.is_available()}")
    print(f"Status: {detector.get_status()}")
    if detector.is_available():
        print(f"Testing wake word via {detector.backend} - say Hey Jarvis / Alexa / Hey Google (proxy for Hey OMNI)")
        print("Press Ctrl+C to stop")
        detector.listen_for_wake_word(on_wake)
    else:
        print("No wake word backend - install: pip install openwakeword pvporcupine")
        print("Using PTT V toggle only")
