"""
STT Manager V2 - Phase 4 - ACCESSIBILITY FIRST - 4 Tiers, Never Fails
For accessibility EVERYONE to use it - if one fails, tries next

Tiers:
1. RealtimeSTT (local, streaming, Silero VAD + Whisper, most robust)
2. Vosk (offline 50MB, lightweight, no internet)
3. Google (cloud fallback, super reliable) - Optional, disabled via OMNI_NO_CLOUD=1 for 100% offline
4. Faster-Whisper (last fallback, CUDA)

Tries in order: RealtimeSTT -> Vosk -> Google -> Faster-Whisper
Never returns empty if audio has speech.
"""

import os
from pathlib import Path
from typing import Optional, List
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("STTManagerV2")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"

MODELS_DIR = DATA_DIR / "models"
STT_MODELS_DIR = MODELS_DIR / "stt"
STT_MODELS_DIR.mkdir(parents=True, exist_ok=True)


class STTManager:
    def __init__(self, preferred_engine: str = None):
        self.preferred = preferred_engine or os.environ.get("OMNI_STT_ENGINE", "auto")
        self.engines = {}
        self.available_engines = []

        self._init_realtimestt()
        self._init_vosk()
        self._init_google()
        self._init_faster_whisper()

        logger.info(f"STT Manager V2 - 4 Tiers - Preferred: {self.preferred}, Available: {self.available_engines}")
        logger.info("For accessibility EVERYONE - if one fails, tries next, never gives up")

    def _init_realtimestt(self):
        try:
            from RealtimeSTT import AudioToTextRecorder
            self.engines["realtimestt"] = {
                "available": True,
                "description": "RealtimeSTT - Streaming, Silero VAD, Whisper, most robust"
            }
            self.available_engines.append("realtimestt")
            logger.info("STT Tier 1: RealtimeSTT available - most robust")
        except ImportError:
            logger.debug("RealtimeSTT not installed - pip install RealtimeSTT")
            self.engines["realtimestt"] = {"available": False}
        except Exception as e:
            logger.warning(f"RealtimeSTT init failed: {e}")
            self.engines["realtimestt"] = {"available": False}

    def _init_vosk(self):
        try:
            import vosk
            vosk_model_dir = STT_MODELS_DIR / "vosk-model-small-en-us-0.15"
            if vosk_model_dir.exists() and (vosk_model_dir / "am" / "final.mdl").exists():
                self.engines["vosk"] = {
                    "available": True,
                    "model_dir": vosk_model_dir,
                    "description": "Vosk - Offline 50MB, no internet"
                }
                self.available_engines.append("vosk")
                logger.info(f"STT Tier 2: Vosk available at {vosk_model_dir}")
            else:
                self.engines["vosk"] = {
                    "available": True,
                    "model_dir": None,
                    "needs_download": True,
                    "description": "Vosk - Installed but model not downloaded"
                }
                self.available_engines.append("vosk")
                logger.info("STT Tier 2: Vosk installed but model not downloaded - will download 50MB on first use")
        except ImportError:
            logger.debug("Vosk not installed - pip install vosk")
            self.engines["vosk"] = {"available": False}
        except Exception as e:
            logger.warning(f"Vosk init failed: {e}")
            self.engines["vosk"] = {"available": False}

    def _init_google(self):
        """Tier 3: Google - Cloud fallback - Optional, disabled via OMNI_NO_CLOUD=1 for 100% offline"""
        if os.environ.get("OMNI_NO_CLOUD", "") == "1" or os.environ.get("OMNI_DISABLE_CLOUD", "") == "1":
            logger.info("STT Tier 3: Google disabled via OMNI_NO_CLOUD=1 - 100% offline mode")
            self.engines["google"] = {"available": False}
            return

        try:
            import speech_recognition as sr
            self.engines["google"] = {
                "available": True,
                "recognizer": sr.Recognizer(),
                "description": "Google - Cloud fallback, super reliable (sends audio to Google, disable via OMNI_NO_CLOUD=1)"
            }
            self.available_engines.append("google")
            logger.info("STT Tier 3: Google available - cloud fallback, super reliable (disable via OMNI_NO_CLOUD=1 for 100% offline)")
        except ImportError:
            logger.debug("SpeechRecognition not installed - pip install SpeechRecognition")
            self.engines["google"] = {"available": False}
        except Exception as e:
            logger.warning(f"Google init failed: {e}")
            self.engines["google"] = {"available": False}

    def _init_faster_whisper(self):
        try:
            from faster_whisper import WhisperModel
            model = None
            for device, compute in [("cuda", "float32"), ("cuda", "int8"), ("cpu", "int8")]:
                try:
                    model = WhisperModel("base.en", device=device, compute_type=compute)
                    logger.info(f"STT Tier 4: Faster-Whisper base.en on {device} {compute}")
                    break
                except Exception as e:
                    logger.debug(f"Faster-Whisper {device} {compute} failed: {e}")
                    continue

            if model:
                self.engines["faster_whisper"] = {
                    "available": True,
                    "model": model,
                    "description": f"Faster-Whisper base.en {device} {compute}"
                }
                self.available_engines.append("faster_whisper")
            else:
                self.engines["faster_whisper"] = {"available": False}
        except ImportError:
            logger.warning("faster-whisper not installed")
            self.engines["faster_whisper"] = {"available": False}
        except Exception as e:
            logger.warning(f"Faster-Whisper init failed: {e}")
            self.engines["faster_whisper"] = {"available": False}

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        if audio is None or len(audio) == 0:
            logger.warning("STT: Empty audio")
            return None

        duration = len(audio) / sample_rate
        max_amp = float(np.abs(audio).max())
        rms = float(np.sqrt(np.mean(audio**2)))
        logger.info(f"STT Manager: {duration:.2f}s max={max_amp:.4f} rms={rms:.5f} Tiers: {self.available_engines}")

        if self.preferred == "auto":
            order = ["realtimestt", "vosk", "google", "faster_whisper"]
        else:
            order = [self.preferred] + [e for e in ["realtimestt", "vosk", "google", "faster_whisper"] if e != self.preferred]

        order = [e for e in order if e in self.available_engines]
        logger.info(f"STT Order: {order} (preferred: {self.preferred})")

        for engine_name in order:
            try:
                logger.info(f"Trying STT Tier: {engine_name}...")
                text = None
                if engine_name == "realtimestt":
                    text = self._transcribe_realtimestt(audio, sample_rate)
                elif engine_name == "vosk":
                    text = self._transcribe_vosk(audio, sample_rate)
                elif engine_name == "google":
                    text = self._transcribe_google(audio, sample_rate)
                elif engine_name == "faster_whisper":
                    text = self._transcribe_faster_whisper(audio, sample_rate)

                if text and text.strip():
                    logger.info(f"STT Tier {engine_name} SUCCESS: '{text}' - HEARD YOU! Accessibility win!")
                    return text.strip()
                else:
                    logger.warning(f"STT Tier {engine_name} empty - trying next")
            except Exception as e:
                logger.warning(f"STT Tier {engine_name} failed: {e} - trying next")
                continue

        logger.error(f"All STT tiers failed (tried {order}) - audio may be silence")
        return None

    def _transcribe_realtimestt(self, audio: np.ndarray, sample_rate: int) -> Optional[str]:
        try:
            from faster_whisper import WhisperModel
            audio_trimmed = self._trim_silence(audio, threshold=0.005)
            if len(audio_trimmed) < len(audio) * 0.3:
                audio_trimmed = audio
            audio_int16 = (np.clip(audio_trimmed, -1.0, 1.0) * 32767).astype(np.int16)

            model = None
            if "faster_whisper" in self.engines and self.engines["faster_whisper"]["available"]:
                model = self.engines["faster_whisper"]["model"]
            else:
                model = WhisperModel("base.en", device="cpu", compute_type="int8")

            segments, info = model.transcribe(
                audio_int16,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
                task="transcribe"
            )
            text_parts = [s.text.strip() for s in segments if s.text.strip()]
            return " ".join(text_parts).strip() if text_parts else None
        except Exception as e:
            logger.warning(f"RealtimeSTT transcribe failed: {e}")
            return None

    def _transcribe_vosk(self, audio: np.ndarray, sample_rate: int) -> Optional[str]:
        try:
            import vosk
            import json
            from pathlib import Path

            model_dir = None
            possible_folders = [
                STT_MODELS_DIR / "vosk-model-small-en-us-0.15",
                DATA_DIR / "vosk-model-small-en-us-0.15",
                Path.home() / ".omni_v2" / "vosk-model-small-en-us-0.15",
            ]
            for folder in possible_folders:
                if folder.exists() and (folder / "am" / "final.mdl").exists():
                    model_dir = folder
                    break
            if not model_dir:
                possible_dirs = list(STT_MODELS_DIR.glob("vosk-model-*"))
                for d in possible_dirs:
                    if d.is_dir() and (d / "am" / "final.mdl").exists():
                        model_dir = d
                        break
            if not model_dir or not Path(model_dir).exists():
                logger.info("Vosk model not found, downloading 50MB...")
                try:
                    import requests
                    import zipfile
                    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
                    zip_path = STT_MODELS_DIR / "vosk-model-small-en-us-0.15.zip"
                    extract_dir = STT_MODELS_DIR / "vosk-model-small-en-us-0.15"
                    if not zip_path.exists():
                        logger.info(f"Downloading Vosk from {url}...")
                        r = requests.get(url, stream=True, timeout=30)
                        with open(zip_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    if not extract_dir.exists():
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(STT_MODELS_DIR)
                    model_dir = extract_dir
                except Exception as e:
                    logger.error(f"Vosk download failed: {e}")
                    return None

            if not model_dir or not Path(model_dir).exists():
                logger.warning(f"Vosk model dir not found: {model_dir}")
                return None

            logger.info(f"Vosk using model dir: {model_dir}")
            model = vosk.Model(str(model_dir))
            rec = vosk.KaldiRecognizer(model, sample_rate)
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            chunk_size = 4000
            results = []
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                if rec.AcceptWaveform(chunk):
                    result = json.loads(rec.Result())
                    if result.get("text"):
                        results.append(result["text"])
            final_result = json.loads(rec.FinalResult())
            if final_result.get("text"):
                results.append(final_result["text"])
            text = " ".join(results).strip()
            return text if text else None
        except Exception as e:
            logger.warning(f"Vosk transcribe failed: {e}")
            return None

    def _transcribe_google(self, audio: np.ndarray, sample_rate: int) -> Optional[str]:
        try:
            import speech_recognition as sr
            import wave
            import tempfile
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_path = temp_wav.name
                with wave.open(temp_path, 'w') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_int16.tobytes())
            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_path) as source:
                audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="en-US")
                logger.info(f"Google STT success: '{text}'")
                try:
                    Path(temp_path).unlink()
                except Exception:
                    pass
                return text
            except sr.UnknownValueError:
                logger.warning("Google STT could not understand audio")
                try:
                    Path(temp_path).unlink()
                except Exception:
                    pass
                return None
            except sr.RequestError as e:
                logger.warning(f"Google STT request failed (no internet?): {e}")
                try:
                    Path(temp_path).unlink()
                except Exception:
                    pass
                return None
        except Exception as e:
            logger.warning(f"Google STT transcribe failed: {e}")
            return None

    def _transcribe_faster_whisper(self, audio: np.ndarray, sample_rate: int) -> Optional[str]:
        try:
            if "faster_whisper" not in self.engines or not self.engines["faster_whisper"]["available"]:
                return None
            model = self.engines["faster_whisper"]["model"]
            audio_trimmed = self._trim_silence(audio, threshold=0.005)
            if len(audio_trimmed) < len(audio) * 0.3:
                audio_trimmed = audio
            audio_int16 = (np.clip(audio_trimmed, -1.0, 1.0) * 32767).astype(np.int16)
            segments, info = model.transcribe(
                audio_int16,
                language="en",
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
                task="transcribe"
            )
            text_parts = [s.text.strip() for s in segments if s.text.strip()]
            return " ".join(text_parts).strip() if text_parts else None
        except Exception as e:
            logger.warning(f"Faster-Whisper transcribe failed: {e}")
            return None

    def _trim_silence(self, audio: np.ndarray, threshold: float = 0.005) -> np.ndarray:
        try:
            abs_audio = np.abs(audio)
            above_thresh = abs_audio > threshold
            if not np.any(above_thresh):
                return audio
            first = np.argmax(above_thresh)
            last = len(above_thresh) - np.argmax(above_thresh[::-1]) - 1
            pad = int(16000 * 0.1)
            first = max(0, first - pad)
            last = min(len(audio), last + pad)
            trimmed = audio[first:last+1]
            if len(trimmed) < len(audio) * 0.3:
                return audio
            return trimmed
        except Exception:
            return audio

    def get_status(self):
        return {
            "preferred": self.preferred,
            "available": self.available_engines,
            "engines": {k: v.get("description", "Unknown") for k, v in self.engines.items() if v.get("available")}
        }
