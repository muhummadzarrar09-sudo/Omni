"""
STT Manager V2 - HARDENED - 3 Tiers, Never Fails
For accessibility EVERYONE - if one fails, tries next

Tiers (3, not 4 - RealtimeSTT is just a wrapper around faster_whisper):
1. Faster-Whisper (local, base.en INT8, primary)
2. Vosk (offline 50MB, lightweight, no internet)
3. Google (cloud fallback, super reliable) - Optional, disabled via OMNI_NO_CLOUD=1

FIXES (from diagnostic/01_DIAGNOSTIC_REPORT.md):
- STT-BUG-04 [MED] : Removed misleading 4-tier claim, accurate 3-tier
- STT-BUG-05 [MED] : Vosk download uses timeouts + progress + size limits
- STT-BUG-06 [MED] : Google temp WAV cleanup in finally block
"""

import os
from pathlib import Path
from typing import Optional
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
        # Diagnostics
        self.init_status = "pending"
        self.last_error = None

        self._init_faster_whisper()  # Tier 1 - primary local
        self._init_vosk()            # Tier 2 - offline
        self._init_google()          # Tier 3 - cloud fallback

        logger.info(
            f"STT Manager V2 - 3 Tiers - Preferred: {self.preferred}, "
            f"Available: {self.available_engines}"
        )
        logger.info("For accessibility EVERYONE - if one fails, tries next, never gives up")

    def _init_faster_whisper(self):
        """Tier 1: Faster-Whisper (local, base.en INT8) - PRIMARY"""
        try:
            from faster_whisper import WhisperModel
            model = None
            active_device = "cpu"
            active_compute = "int8"
            for device, compute in [
                ("cuda", "int8"),
                ("cuda", "float16"),
                ("cpu", "int8"),
                ("cpu", "int8_float16"),
                ("cpu", "float32"),
            ]:
                try:
                    model = WhisperModel("base.en", device=device, compute_type=compute)
                    active_device = device
                    active_compute = compute
                    logger.info(f"STT Tier 1: Faster-Whisper base.en on {device} {compute}")
                    break
                except Exception as e:
                    logger.debug(f"Faster-Whisper {device} {compute} failed: {e}")
                    continue

            if model:
                self.engines["faster_whisper"] = {
                    "available": True,
                    "model": model,
                    "description": f"Faster-Whisper base.en {active_device} {active_compute} (Tier 1 primary)",
                }
                self.available_engines.append("faster_whisper")
            else:
                self.engines["faster_whisper"] = {"available": False}
        except ImportError:
            self.engines["faster_whisper"] = {"available": False}
            logger.debug("faster-whisper not installed")
        except Exception as e:
            self.engines["faster_whisper"] = {"available": False}
            logger.warning(f"Faster-Whisper init failed: {e}")

    def _init_vosk(self):
        """Tier 2: Vosk (offline 50MB)"""
        try:
            import vosk
            vosk_model_dir = STT_MODELS_DIR / "vosk-model-small-en-us-0.15"
            if vosk_model_dir.exists() and (vosk_model_dir / "am" / "final.mdl").exists():
                self.engines["vosk"] = {
                    "available": True,
                    "model_dir": vosk_model_dir,
                    "description": "Vosk - Offline 50MB, no internet (Tier 2)",
                }
                self.available_engines.append("vosk")
                logger.info(f"STT Tier 2: Vosk available at {vosk_model_dir}")
            else:
                self.engines["vosk"] = {
                    "available": True,
                    "model_dir": None,
                    "needs_download": True,
                    "description": "Vosk - Installed but model not downloaded (Tier 2)",
                }
                self.available_engines.append("vosk")
                logger.info("STT Tier 2: Vosk installed but model not downloaded - will download 50MB on first use")
        except ImportError:
            self.engines["vosk"] = {"available": False}
            logger.debug("Vosk not installed - pip install vosk")
        except Exception as e:
            self.engines["vosk"] = {"available": False}
            logger.warning(f"Vosk init failed: {e}")

    def _init_google(self):
        """Tier 3: Google - Cloud fallback - Optional, disabled via OMNI_NO_CLOUD=1"""
        if os.environ.get("OMNI_NO_CLOUD", "") == "1" or os.environ.get("OMNI_DISABLE_CLOUD", "") == "1":
            logger.info("STT Tier 3: Google disabled via OMNI_NO_CLOUD=1 - 100% offline mode")
            self.engines["google"] = {"available": False}
            return

        try:
            import speech_recognition as sr
            self.engines["google"] = {
                "available": True,
                "recognizer": sr.Recognizer(),
                "description": "Google - Cloud fallback, super reliable (Tier 3, disable via OMNI_NO_CLOUD=1)",
            }
            self.available_engines.append("google")
            logger.info("STT Tier 3: Google available - cloud fallback, super reliable")
        except ImportError:
            self.engines["google"] = {"available": False}
            logger.debug("SpeechRecognition not installed - pip install SpeechRecognition")
        except Exception as e:
            self.engines["google"] = {"available": False}
            logger.warning(f"Google init failed: {e}")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        if audio is None or len(audio) == 0:
            logger.warning("STT: Empty audio")
            return None

        duration = len(audio) / sample_rate
        max_amp = float(np.abs(audio).max())
        rms = float(np.sqrt(np.mean(audio ** 2)))
        logger.info(
            f"STT Manager: {duration:.2f}s max={max_amp:.4f} rms={rms:.5f} Tiers: {self.available_engines}"
        )

        # Order: prefer local (faster_whisper) first, then offline (vosk), then cloud (google)
        if self.preferred == "auto":
            order = ["faster_whisper", "vosk", "google"]
        else:
            order = [self.preferred] + [
                e for e in ["faster_whisper", "vosk", "google"] if e != self.preferred
            ]

        order = [e for e in order if e in self.available_engines]
        logger.info(f"STT Order: {order} (preferred: {self.preferred})")

        for engine_name in order:
            try:
                logger.info(f"Trying STT Tier: {engine_name}...")
                text = None
                if engine_name == "faster_whisper":
                    text = self._transcribe_faster_whisper(audio, sample_rate)
                elif engine_name == "vosk":
                    text = self._transcribe_vosk(audio, sample_rate)
                elif engine_name == "google":
                    text = self._transcribe_google(audio, sample_rate)

                if text and text.strip():
                    logger.info(
                        f"STT Tier {engine_name} SUCCESS: '{text}' - HEARD YOU! Accessibility win!"
                    )
                    return text.strip()
                else:
                    logger.warning(f"STT Tier {engine_name} empty - trying next")
            except Exception as e:
                logger.warning(f"STT Tier {engine_name} failed: {e} - trying next")
                continue

        logger.error(f"All STT tiers failed (tried {order}) - audio may be silence")
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
                task="transcribe",
            )
            text_parts = [s.text.strip() for s in segments if s.text.strip()]
            return " ".join(text_parts).strip() if text_parts else None
        except Exception as e:
            logger.warning(f"Faster-Whisper transcribe failed: {e}")
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
                # STT-BUG-05 fix: robust download with timeouts
                logger.info("Vosk model not found, downloading 50MB...")
                try:
                    import requests
                    import zipfile
                    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
                    zip_path = STT_MODELS_DIR / "vosk-model-small-en-us-0.15.zip"
                    extract_dir = STT_MODELS_DIR / "vosk-model-small-en-us-0.15"
                    if not zip_path.exists():
                        logger.info(f"Downloading Vosk from {url}...")
                        # STT-BUG-05: explicit connect/read timeouts, content-length aware
                        r = requests.get(url, stream=True, timeout=(5, 30))
                        total = int(r.headers.get("content-length", 0))
                        downloaded = 0
                        with open(zip_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total and downloaded % (1024 * 1024) < 8192:
                                    pct = (downloaded / total) * 100
                                    logger.info(f"  Vosk download: {pct:.0f}% ({downloaded//1024}KB / {total//1024}KB)")
                        # Validate size
                        if zip_path.exists() and zip_path.stat().st_size < 1_000_000:
                            raise Exception(f"Vosk zip too small: {zip_path.stat().st_size} bytes - download truncated")
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
                chunk = audio_bytes[i:i + chunk_size]
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
        # STT-BUG-06 fix: ensure temp WAV is always cleaned up
        temp_path = None
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
                return text
            except sr.UnknownValueError:
                logger.warning("Google STT could not understand audio")
                return None
            except sr.RequestError as e:
                logger.warning(f"Google STT request failed (no internet?): {e}")
                return None
        except Exception as e:
            logger.warning(f"Google STT transcribe failed: {e}")
            return None
        finally:
            # STT-BUG-06 fix: always clean up temp file
            if temp_path is not None:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass

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
            trimmed = audio[first:last + 1]
            if len(trimmed) < len(audio) * 0.3:
                return audio
            return trimmed
        except Exception:
            return audio

    def get_status(self):
        return {
            "preferred": self.preferred,
            "available": self.available_engines,
            "engines": {k: v.get("description", "Unknown") for k, v in self.engines.items() if v.get("available")},
        }
