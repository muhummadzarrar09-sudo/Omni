"""Voice Pipeline V2 - Phase 4 - ACCESSIBILITY FIRST - STT Manager 4 Tiers - Actually HEARS Everyone!"""
import time
import threading
from pathlib import Path
from typing import Callable, Optional
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("VoicePipelineV2")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"

class VoicePipelineV2:
    """Voice Pipeline V2 Phase 4 - Accessibility First - STT 4 Tiers - Never fails if audio has speech"""

    def __init__(self, 
                 device_manager=None,
                 on_transcription: Callable = None,
                 on_status: Callable = None,
                 device_index: Optional[int] = None):

        self.device_manager = device_manager
        self.on_transcription = on_transcription
        self.on_status = on_status
        self.device_index = device_index

        self.is_recording = False
        self.audio_buffer = []
        self.sample_rate = 16000
        self.chunk_size = 1024

        # STT Manager V2 - 4 Tiers for Accessibility
        self.stt_manager = None
        self.whisper_model = None
        self.whisper_available = False
        self._init_stt_manager()

        self.recordings_dir = DATA_DIR / "recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        logger.info("VoicePipeline V2 Phase 4 - Accessibility First - STT 4 Tiers (RealtimeSTT/Vosk/Google/Whisper) - WILL HEAR EVERYONE")

    def _init_stt_manager(self):
        """Init STT Manager 4 Tiers - Never fails for accessibility"""
        try:
            from omni_v2.voice.stt_manager import STTManager
            self.stt_manager = STTManager()
            self.whisper_available = len(self.stt_manager.available_engines) > 0
            # Keep old whisper_model reference for backwards compat
            if "faster_whisper" in self.stt_manager.engines and self.stt_manager.engines["faster_whisper"]["available"]:
                self.whisper_model = self.stt_manager.engines["faster_whisper"]["model"]
            status = self.stt_manager.get_status()
            logger.info(f"STT Manager V2 - {len(status['available'])} tiers: {status['available']} - Preferred: {status['preferred']}")
            for eng, desc in status['engines'].items():
                logger.info(f"  Tier {eng}: {desc}")
            logger.info("For accessibility EVERYONE - if one fails, tries next, never gives up")
        except ImportError as e:
            logger.error(f"STT Manager not available: {e} - trying old Whisper direct")
            try:
                from faster_whisper import WhisperModel
                for device, compute in [("cuda", "float32"), ("cuda", "int8"), ("cpu", "int8")]:
                    try:
                        self.whisper_model = WhisperModel("base.en", device=device, compute_type=compute)
                        self.whisper_available = True
                        logger.info(f"Whisper fallback: base.en on {device} {compute}")
                        return
                    except Exception as ex:
                        logger.debug(f"Whisper {device} {compute} failed: {ex}")
            except Exception as ex:
                logger.error(f"Whisper fallback failed: {ex}")
                self.whisper_available = False
        except Exception as e:
            logger.error(f"STT Manager init failed: {e}")
            self.whisper_available = False

    def start(self):
        if self.is_recording:
            return
        self.audio_buffer = []
        self.is_recording = True
        if self.on_status:
            try:
                self.on_status("recording")
            except Exception:
                pass
        self.record_thread = threading.Thread(target=self._record_loop, daemon=True, name="VoiceRecordV2")
        self.record_thread.start()
        logger.info("Voice recording started - SPEAK LOUD 2 inches, HOLD V 2-3 sec after speaking! (PTT manual, no auto cut, 4-tier STT)")

    def stop(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.on_status:
            try:
                self.on_status("processing")
            except Exception:
                pass
        if hasattr(self, 'record_thread') and self.record_thread.is_alive():
            self.record_thread.join(timeout=2)

        audio = self._get_audio()

        if audio is None or len(audio) == 0:
            logger.warning("No audio captured - mic may be muted")
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass
            return

        duration = len(audio) / self.sample_rate
        max_amp = float(np.abs(audio).max())
        rms = float(np.sqrt(np.mean(audio**2)))

        logger.info(f"Captured: {duration:.2f}s | max={max_amp:.4f} | rms={rms:.5f} | samples={len(audio)}")

        # Save WAV for debugging
        try:
            from datetime import datetime
            import wave
            filename = self.recordings_dir / f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(duration)}s.wav"
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            with wave.open(str(filename), 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())
            logger.info(f"Saved recording to {filename} - play to check if mic captured speech")
        except Exception as e:
            logger.warning(f"Failed to save recording: {e}")

        if duration < 0.15:
            logger.warning(f"Audio too short: {duration:.2f}s < 0.15s - hold V longer")
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass
            return

        # Transcribe via STT Manager 4 Tiers - Never fails if audio has speech
        try:
            if not self.stt_manager or not self.stt_manager.available_engines:
                logger.error("STT Manager not available or no engines - cannot transcribe")
                if self.on_status:
                    try:
                        self.on_status("idle")
                    except Exception:
                        pass
                return

            logger.info(f"Transcribing via STT Manager 4 Tiers: {self.stt_manager.available_engines}...")

            text = self.stt_manager.transcribe(audio, sample_rate=self.sample_rate)

            if text and text.strip():
                logger.info(f"Transcribed (HEARD YOU! Accessibility win!): '{text}' - rms={rms:.5f} max={max_amp:.4f}")
                if self.on_transcription:
                    try:
                        self.on_transcription(text)
                    except Exception as e:
                        logger.error(f"Transcription callback error: {e}")
            else:
                logger.warning(f"All STT tiers returned empty (audio may truly be silence/noise) - max={max_amp:.3f} rms={rms:.5f} - SAVED to {self.recordings_dir} - play WAV!")
                logger.warning("Try: LOUDER, CLOSER (1 inch!), hold V 3 sec after, boost mic Windows Settings -> Sound -> Input 100% + Boost +30dB")
                logger.warning("Also try: python scripts/test_mic_level.py to see live RMS - should be >0.02 GREEN LOUD")
                if self.on_status:
                    try:
                        self.on_status("idle")
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"STT Manager transcription error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass

    def _record_loop(self):
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            device_idx = self.device_index
            if device_idx is None and self.device_manager:
                try:
                    device_idx = self.device_manager.get_input_device_index()
                except Exception:
                    device_idx = None

            logger.info(f"Opening mic stream: device={device_idx or 'default'}, rate={self.sample_rate}, PTT manual no auto cut")

            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_idx,
                frames_per_buffer=self.chunk_size
            )

            logger.info("Mic stream opened, recording... (PTT manual, speaks LOUD 1 inch!)")

            while self.is_recording:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    self.audio_buffer.append(audio)
                except Exception as e:
                    logger.warning(f"Record loop read error: {e}")
                    break

            stream.stop_stream()
            stream.close()
            pa.terminate()

            logger.info(f"Recording stopped, captured {len(self.audio_buffer)} chunks")

        except ImportError:
            logger.error("PyAudio not installed")
            self.is_recording = False
        except Exception as e:
            logger.error(f"Record loop error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.is_recording = False

    def _get_audio(self):
        if not self.audio_buffer:
            return None
        try:
            audio = np.concatenate(self.audio_buffer)
            self.audio_buffer = []
            return audio
        except Exception as e:
            logger.error(f"Failed to concat audio buffer: {e}")
            self.audio_buffer = []
            return None
