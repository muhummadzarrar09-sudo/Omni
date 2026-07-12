"""Wake Word V2 - Phase 3 Started - Hey OMNI continuous"""
from typing import Callable, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("WakeWordV2")

class WakeWordDetector:
    """Wake word 'Hey OMNI' via pvporcupine or openwakeword - offline, 5% CPU"""

    def __init__(self, keyword: str = "hey omni", sensitivity: float = 0.7):
        self.keyword = keyword.lower()
        self.sensitivity = sensitivity
        self.detector = None
        self.backend = None
        self._init_detector()
        logger.info(f"WakeWordDetector V2 - Keyword: '{keyword}', Backend: {self.backend}")

    def _init_detector(self):
        # Try pvporcupine first (needs access key, but has free tier)
        try:
            import pvporcupine
            # Try to create with hey google as proxy (since custom hey omni needs key)
            # For demo, use "hey google" or "jarvis" if available
            try:
                # This will fail without access key, but we try
                self.detector = pvporcupine.create(
                    keywords=["hey google"],
                    sensitivities=[self.sensitivity]
                )
                self.backend = "pvporcupine"
                logger.info("Wake word: pvporcupine (hey google as proxy for hey omni)")
                return
            except Exception as e:
                logger.debug(f"pvporcupine create failed (needs access key): {e}")
        except ImportError:
            logger.debug("pvporcupine not installed")

        # Try openwakeword (free, no key, uses ONNX)
        try:
            import openwakeword
            from openwakeword.model import Model
            self.detector = Model(wakeword_models=["hey_jarvis"])
            self.backend = "openwakeword"
            logger.info("Wake word: openwakeword (hey_jarvis as proxy for hey omni) - free, offline")
            return
        except ImportError:
            logger.debug("openwakeword not installed - pip install openwakeword")
        except Exception as e:
            logger.debug(f"openwakeword init failed: {e}")

        # Fallback: no wake word, use PTT only
        self.backend = None
        logger.warning("No wake word engine - using PTT V toggle only. Install: pip install pvporcupine openwakeword")

    def listen_for_wake_word(self, callback: Callable[[], None], stop_event=None):
        """Continuous listening loop - calls callback when wake word detected"""
        if not self.backend:
            logger.warning("No wake word backend - cannot listen")
            return

        try:
            import pyaudio
            pa = pyaudio.PyAudio()

            if self.backend == "pvporcupine":
                import struct
                stream = pa.open(
                    rate=self.detector.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=self.detector.frame_length
                )

                logger.info(f"Listening for wake word '{self.keyword}' via {self.backend}... (say Hey Google as proxy)")

                while True:
                    if stop_event and stop_event.is_set():
                        break
                    pcm = stream.read(self.detector.frame_length)
                    pcm = struct.unpack_from("h" * self.detector.frame_length, pcm)
                    keyword_index = self.detector.process(pcm)
                    if keyword_index >= 0:
                        logger.info(f"Wake word detected! '{self.keyword}'")
                        callback()

            elif self.backend == "openwakeword":
                # Openwakeword uses 16kHz, 1280 frame
                import numpy as np
                stream = pa.open(
                    rate=16000,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=1280
                )

                logger.info(f"Listening for wake word '{self.keyword}' via {self.backend}...")

                while True:
                    if stop_event and stop_event.is_set():
                        break
                    data = stream.read(1280, exception_on_overflow=False)
                    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                    # openwakeword prediction
                    prediction = self.detector.predict(audio)
                    for mdl, score in prediction.items():
                        if score > 0.5:
                            logger.info(f"Wake word '{mdl}' detected with score {score}")
                            callback()
                            # Debounce
                            import time
                            time.sleep(2)

        except Exception as e:
            logger.error(f"Wake word listening failed: {e}")
        finally:
            try:
                stream.stop_stream()
                stream.close()
                pa.terminate()
            except Exception:
                pass

    def is_available(self) -> bool:
        return self.backend is not None

if __name__ == "__main__":
    def on_wake():
        print("Hey OMNI detected! Starting command...")

    detector = WakeWordDetector()
    if detector.is_available():
        print(f"Testing wake word via {detector.backend} - say Hey Google / Hey Jarvis")
        detector.listen_for_wake_word(on_wake)
    else:
        print("No wake word backend - install pvporcupine or openwakeword")
