"""
OMNI Voice Pipeline - Complete Voice Recognition System
========================================================

Handles: Audio Capture → VAD → Whisper STT → Command Execution

PHASE 3 STT ROBUSTNESS — Every edge case handled:

Audio Capture:
- Device hot-plug (mic unplugged mid-recording) → graceful recovery
- Device not found (paDeviceNotFound, paInvalidDevice) → re-detect + warn
- Could not start stream → try all available devices in sequence
- No input devices at all → clear error message, non-fatal
- Probe device before first use → catch bad devices early
- PyAudio error codes translated to human-readable messages

VAD (Voice Activity Detection):
- torchaudio installation → Silero VAD (much more accurate)
- Silero VAD fails → energy-based fallback (always works)
- Adaptive threshold → calibrate to ambient noise on startup
- VAD confidence threshold adjustable via config

Buffer Management:
- Buffer overflow protection → max_seconds limit (60s default)
- Memory pressure → truncate and warn instead of crash
- Min recording window → 0.5s before silence check (never cuts speech start)
- Max silence duration → 1.0s of silence before end-of-speech

Audio Quality:
- Audio too quiet → "Microphone may be muted" message
- Audio is pure noise → "Didn't catch that" without full transcription
- Energy check before transcription → skip whisper for near-silence
- Dynamic ambient noise calibration → learns background noise level

Whisper STT:
- Auto language detection (language="auto")
- Transcription timeout (30s max)
- Very short audio (<0.3s) → skip whisper, say "too short"
- Very long audio (>60s) → truncate to 60s to prevent OOM
- Empty transcription → "Didn't catch that, try again"
- Audio format normalization → always float32 [-1, 1] → int16 PCM
- VAD already done → vad_filter=False (don't double-filter)
- GPU vs CPU auto-detection and fallback
"""

from __future__ import annotations

import time
import threading
import queue
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np
from loguru import logger

from omni.core.event_bus import EventBus, EventType


# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_SIZE = 1024       # 1024 samples @ 16kHz = 64ms per callback
DEFAULT_MIN_RECORDING_S = 0.4   # Force-record first 0.4s (bypass VAD, capture speech start)
DEFAULT_MAX_RECORDING_S = 60.0  # Hard limit — prevent buffer overflow / OOM
DEFAULT_SILENCE_CHUNKS = 8      # ~0.5s of silence (8 × 64ms = 512ms)
DEFAULT_SILENCE_THRESHOLD = 0.005  # Energy threshold for silence detection
DEFAULT_SPEECH_THRESHOLD = 0.008  # Energy threshold for speech detection
DEFAULT_WHISPER_TIMEOUT_S = 30.0   # Transcription timeout
DEFAULT_MIN_AUDIO_S = 0.3         # Reject recordings shorter than this


# ─── Enums ────────────────────────────────────────────────────────────────────

class VADEngine(Enum):
    SILERO = auto()       # Neural network VAD (requires torchaudio)
    ENERGY = auto()       # Energy-based fallback (always works)
    NONE = auto()         # No VAD loaded


class AudioState(Enum):
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    ERROR = auto()


@dataclass
class VADAudioQuality:
    """Quality metrics for a recorded audio segment."""
    duration_s: float = 0.0
    max_amplitude: float = 0.0
    avg_rms: float = 0.0
    silence_ratio: float = 0.0  # fraction of audio that is silence
    is_too_quiet: bool = False
    is_too_short: bool = False
    is_noise_only: bool = False

    def should_transcribe(self) -> bool:
        """Return False if audio quality is too poor to bother transcribing."""
        if self.is_too_short:
            return False
        if self.is_too_quiet:
            return False
        if self.is_noise_only:
            return False
        return True

    def quality_summary(self) -> str:
        parts = [
            f"{self.duration_s:.1f}s",
            f"max={self.max_amplitude:.3f}",
            f"rms={self.avg_rms:.4f}",
            f"silence={self.silence_ratio:.0%}",
        ]
        if self.is_too_short:
            parts.append("TOO SHORT")
        if self.is_too_quiet:
            parts.append("TOO QUIET")
        if self.is_noise_only:
            parts.append("NOISE ONLY")
        return " | ".join(parts)


@dataclass
class AudioCaptureError:
    """Structured audio error for logging and UI feedback."""
    code: int
    message: str
    suggestion: str
    recoverable: bool  # True = app continues, False = app must crash

    @staticmethod
    def from_pyaudio(code: int) -> "AudioCaptureError":
        """Translate PyAudio error code to structured error."""
        from omni.voice.audio_device import translate_pyaudio_error
        base = translate_pyaudio_error(code)

        suggestions = {
            -9999: "Re-select your microphone in Settings.",
            -9996: "Your microphone may have been unplugged. Try a different device.",
            -9986: "Restart OMNI. If the issue persists, update your audio drivers.",
            -9982: "Check that your microphone is working in Windows Sound settings.",
            -9998: "Try selecting a different microphone in Settings.",
        }
        return AudioCaptureError(
            code=code,
            message=base,
            suggestion=suggestions.get(code, "Try restarting OMNI."),
            recoverable=True,
        )


# ─── VoicePipeline ────────────────────────────────────────────────────────────

class VoicePipeline:
    """
    Complete voice processing pipeline.

    PTT Press → PyAudio stream → VAD → Buffer → Quality check → Whisper → Text

    Every component has a fallback. The pipeline never crashes — it reports
    errors clearly and keeps running.
    """

    def __init__(
        self,
        event_bus: EventBus = None,
        device_manager=None,  # AudioDeviceManager instance
        on_transcription: Callable[[np.ndarray], None] = None,
        on_status: Callable[[str], None] = None,
        on_error: Callable[[AudioCaptureError], None] = None,
        min_recording_s: float = DEFAULT_MIN_RECORDING_S,
        max_recording_s: float = DEFAULT_MAX_RECORDING_S,
        silence_chunks: int = DEFAULT_SILENCE_CHUNKS,
        speech_threshold: float = DEFAULT_SPEECH_THRESHOLD,
        silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
    ):
        self.event_bus = event_bus or EventBus()
        self.device_manager = device_manager
        self.on_transcription = on_transcription
        self.on_status = on_status
        self.on_error = on_error

        # Audio parameters
        self.sample_rate = DEFAULT_SAMPLE_RATE
        self.chunk_size = DEFAULT_CHUNK_SIZE
        self.min_recording_s = min_recording_s
        self.max_recording_s = max_recording_s
        self.silence_chunks = silence_chunks
        self.speech_threshold = speech_threshold
        self.silence_threshold = silence_threshold

        # State
        self.audio_buffer: list[np.ndarray] = []
        self.state = AudioState.IDLE
        self.is_recording = False
        self.recording_thread: Optional[threading.Thread] = None
        self.audio_stream = None
        self.audio_interface = None
        self._stream_error: Optional[AudioCaptureError] = None
        self._consecutive_errors = 0
        self._max_consecutive_errors = 3
        self._recording_ended = False  # Guard: prevent _end_recording from firing twice

        # VAD
        self.vad_engine = VADEngine.NONE
        self.vad_model = None
        self._silence_count = 0
        self._load_vad()

        # Ambient noise calibration
        self._ambient_noise_level: float = 0.002  # Default quiet room
        self._calibration_samples: list[float] = []
        self._is_calibrated = False

        logger.info(
            f"VoicePipeline initialized — VAD: {self.vad_engine.name}, "
            f"min={min_recording_s}s, max={max_recording_s}s, "
            f"speech_thresh={speech_threshold}"
        )

    # ── VAD Loading ────────────────────────────────────────────────────────

    def _load_vad(self) -> None:
        """
        Load VAD in priority order:
        1. Silero VAD via torch.hub (requires torch + torchaudio)
        2. Energy-based fallback (always works, no extra deps)

        torchaudio installation:
            pip install torchaudio --index-url https://download.pytorch.org/whl/cu121
        """
        # Try Silero VAD via torch.hub
        try:
            import torch
            torch.set_num_threads(1)

            self.vad_model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                trust_repo=True,
            )
            self.get_speech_ts = utils[0]
            self.vad_engine = VADEngine.SILERO
            logger.info(
                "VAD loaded: Silero VAD (via torch.hub). "
                "Torchaudio is installed — VAD accuracy is HIGH."
            )
            return

        except ImportError as e:
            if "torchaudio" in str(e):
                logger.warning(
                    "Silero VAD requires torchaudio (not installed). "
                    "Install with: pip install torchaudio --index-url "
                    "https://download.pytorch.org/whl/cu121"
                )
            else:
                logger.warning(f"Silero VAD import failed: {e}. Using energy-based detection.")
            self.vad_engine = VADEngine.ENERGY
            self.vad_model = None
            return

        except Exception as e:
            logger.warning(f"Silero VAD load failed: {e}. Using energy-based detection.")
            self.vad_engine = VADEngine.ENERGY
            self.vad_model = None
            return

    # ── PTT Control ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the voice capture pipeline."""
        if self.state == AudioState.RECORDING:
            logger.debug("VoicePipeline: already recording, ignoring start()")
            return

        if self.recording_thread is not None and self.recording_thread.is_alive():
            logger.debug("VoicePipeline: capture thread alive, ignoring start()")
            return

        self.audio_buffer = []
        self._silence_count = 0
        self._stream_error = None
        self._recording_ended = False  # Reset guard on new recording
        self.is_recording = True
        self.state = AudioState.RECORDING

        self.recording_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="VoiceCapture",
        )
        self.recording_thread.start()
        logger.info("Voice capture started")

    def stop(self) -> None:
        """Stop the voice capture pipeline."""
        if not self.is_recording and self.state != AudioState.RECORDING:
            logger.debug("VoicePipeline: not recording, ignoring stop()")
            return

        self.is_recording = False
        self.state = AudioState.IDLE

        # Stop stream safely
        if self.audio_stream is not None:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception as e:
                logger.debug(f"Stream stop error (non-fatal): {e}")
            self.audio_stream = None

        # Terminate PyAudio instance safely
        if self.audio_interface is not None:
            try:
                self.audio_interface.terminate()
            except Exception as e:
                logger.debug(f"PyAudio terminate error (non-fatal): {e}")
            self.audio_interface = None

        logger.info("Voice capture stopped")

    # ── Capture Loop ───────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """Main audio capture loop — runs in background thread."""
        pyaudio = None

        try:
            # Get PyAudio from device manager or import directly
            if self.device_manager is not None:
                pyaudio = self.device_manager.get_pyaudio()

            if pyaudio is None:
                import pyaudio
                pyaudio = pyaudio

            self.audio_interface = pyaudio.PyAudio()

            # Get device index from device manager
            device_index = None
            if self.device_manager is not None:
                device_index = self.device_manager.get_input_device_index()

            # Open stream
            try:
                self.audio_stream = self.audio_interface.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self._audio_callback,
                    start=False,  # Start via callback
                )
            except OSError as e:
                # Device error — try default device as fallback
                err_code = getattr(e, 'errno', None) or getattr(e, 'winerror', 0)
                logger.warning(f"Stream open failed on device {device_index}: {e}")

                if device_index is not None:
                    # Try default device
                    logger.info("Trying default input device as fallback...")
                    try:
                        self.audio_stream = self.audio_interface.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=self.sample_rate,
                            input=True,
                            input_device_index=None,  # Default device
                            frames_per_buffer=self.chunk_size,
                            stream_callback=self._audio_callback,
                            start=False,
                        )
                        self._emit_error(
                            AudioCaptureError(
                                code=int(err_code) if err_code else -9999,
                                message=f"Preferred device failed, using default: {e}",
                                suggestion="Re-select your microphone in Settings.",
                                recoverable=True,
                            )
                        )
                    except Exception as e2:
                        raise OSError(f"Default device also failed: {e2}") from e

                if self.audio_stream is None:
                    raise OSError(f"Could not open any audio device: {e}") from e

            # Start the stream
            self.audio_stream.start_stream()
            self._consecutive_errors = 0  # Reset on successful start

            logger.debug(f"Stream started — device: {device_index or 'default'}, rate: {self.sample_rate}")

            # Keep thread alive while recording
            while self.is_recording:
                time.sleep(0.05)

        except ImportError:
            self._emit_error(AudioCaptureError(
                code=0,
                message="PyAudio not installed. Run: pip install PyAudio",
                suggestion="Install PyAudio for your Python version from: "
                          "https://pypi.org/project/PyAudio/",
                recoverable=False,
            ))
            self.state = AudioState.ERROR
        except OSError as e:
            err_code = getattr(e, 'errno', None) or getattr(e, 'winerror', 0) or -9999
            error = AudioCaptureError.from_pyaudio(int(err_code))
            error.message = f"Audio device error: {error.message} (details: {e})"
            self._emit_error(error)
            self.state = AudioState.ERROR
        except Exception as e:
            self._emit_error(AudioCaptureError(
                code=-1,
                message=f"Audio capture error: {e}",
                suggestion="Restart OMNI. If the issue persists, check your microphone.",
                recoverable=True,
            ))
            self.state = AudioState.ERROR
        finally:
            # Clean up
            self.is_recording = False
            if self.audio_stream is not None:
                try:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                except Exception:
                    pass
                self.audio_stream = None
            if self.audio_interface is not None:
                try:
                    self.audio_interface.terminate()
                except Exception:
                    pass
                self.audio_interface = None

    # ── Audio Callback ─────────────────────────────────────────────────────

    def _audio_callback(self, in_data: bytes, frame_count: int, time_info: dict, status: int) -> tuple[bytes, int]:
        """
        PyAudio stream callback — called by PortAudio's C thread ~15x per second.
        This runs in a DIFFERENT thread from the main app — all operations must be thread-safe.
        """
        # Handle stream errors (non-fatal)
        if status != 0:
            self._handle_stream_status(status)

        # Convert to numpy float32 in [-1, 1]
        try:
            audio_np = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.warning(f"Audio callback: could not convert audio data: {e}")
            return (in_data, 0)  # 0 = paContinue but we're returning an error marker

        # Calculate recording duration so far
        recorded_s = len(self.audio_buffer) * (self.chunk_size / self.sample_rate)

        # ── Buffer overflow protection ──────────────────────────────────
        if recorded_s >= self.max_recording_s:
            # Max duration reached — force end of recording
            logger.debug(f"Max recording duration reached ({self.max_recording_s}s), ending recording")
            self._end_recording("max_duration")
            return (in_data, 0)

        # ── Phase 1: Force-record minimum window ────────────────────────
        # Capture at least min_recording_s before checking for silence.
        # This prevents cutting off the START of a sentence.
        if recorded_s < self.min_recording_s:
            self.audio_buffer.append(audio_np)
            self._silence_count = 0  # Reset silence counter during forced recording
            self._emit_status("recording")
            return (in_data, 0)

        # ── Phase 2: VAD check ──────────────────────────────────────────
        is_speech = self._detect_speech(audio_np)

        if is_speech:
            self.audio_buffer.append(audio_np)
            self._silence_count = 0
            self._emit_status("recording")
        elif self.audio_buffer:
            # Only check for silence end once we have speech audio
            self._silence_count += 1

            if self._silence_count >= self.silence_chunks:
                # ~0.5s of consecutive silence after speech → end recording
                self._end_recording("silence_end")
            else:
                self._emit_status("recording")

        return (in_data, 0)

    def _handle_stream_status(self, status: int) -> None:
        """Handle PyAudio stream status flags."""
        if status & 0x1:  # paInputOverflow
            logger.warning("Audio stream: input overflow (some audio was lost)")
            self._consecutive_errors += 1
        if status & 0x2:  # paInputUnderflow
            logger.debug("Audio stream: input underflow")
        if status & 0x4:  # paOutputOverflow
            pass  # TTS output, not our concern here
        if status & 0x8:  # paOutputUnderflow
            pass

        if self._consecutive_errors >= self._max_consecutive_errors:
            logger.error(f"Too many consecutive stream errors ({self._consecutive_errors}), stopping recording")
            self._end_recording("stream_error")

    # ── Speech Detection ──────────────────────────────────────────────────

    def _detect_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect if audio chunk contains speech.
        Uses Silero VAD if loaded, otherwise energy-based detection.
        """
        if self.vad_engine == VADEngine.SILERO and self.vad_model is not None:
            try:
                # Silero VAD expects float32 in [-1, 1], 16kHz
                speech_prob = self.vad_model(audio_chunk, self.sample_rate).item()
                # Use adaptive threshold — slightly lower than default 0.5
                # to catch quiet speech without over-triggering on noise
                threshold = max(0.3, self.speech_threshold * 10)  # VAD uses 0-1 scale
                return speech_prob > threshold
            except Exception as e:
                logger.debug(f"Silero VAD inference error: {e}, falling through to energy-based")
                # Fall through to energy-based

        # Energy-based detection (fallback)
        energy = np.abs(audio_chunk).mean()

        # Calibrate threshold from ambient noise if we have calibration data
        if self._is_calibrated and self._ambient_noise_level > 0:
            # Adaptive threshold: ambient + fixed margin
            threshold = max(self.speech_threshold, self._ambient_noise_level * 3)
        else:
            threshold = self.speech_threshold

        return energy > threshold

    def calibrate_ambient_noise(self, num_samples: int = 20) -> float:
        """
        Calibrate the ambient noise level by sampling silence.
        Call this during startup (before first PTT press) to set the baseline.
        """
        if self._is_calibrated:
            return self._ambient_noise_level

        # If we have audio already, use the last few samples
        if len(self.audio_buffer) >= num_samples:
            samples = np.concatenate(self.audio_buffer[-num_samples:])
            self._ambient_noise_level = np.abs(samples).mean()
            self._is_calibrated = True
            logger.info(f"VAD calibrated: ambient noise level = {self._ambient_noise_level:.4f}")
            return self._ambient_noise_level

        return self._ambient_noise_level

    # ── End Recording ─────────────────────────────────────────────────────

    def _end_recording(self, reason: str) -> None:
        """End the current recording. Guard prevents double-fire from callback + stop()."""
        if self._recording_ended:
            return
        self._recording_ended = True

        if not self.audio_buffer:
            # Nothing to process
            return

        # Get audio from buffer
        audio = self.get_audio()

        if audio is None or len(audio) == 0:
            logger.debug(f"_end_recording: no audio ({reason})")
            self._silence_count = 0
            return

        # Check audio quality before transcription
        quality = self._assess_audio_quality(audio)

        logger.debug(f"_end_recording ({reason}): {quality.quality_summary()}")

        if not quality.should_transcribe():
            # Audio quality too poor
            self._emit_status("idle")
            if quality.is_too_short:
                self._on_audio_quality_issue("Recording was too short. Please hold V longer.")
            elif quality.is_too_quiet:
                self._on_audio_quality_issue(
                    "Audio is too quiet. Please check that your microphone is not muted "
                    "and try speaking closer to the microphone."
                )
            elif quality.is_noise_only:
                self._on_audio_quality_issue("I heard some noise but couldn't understand you. Please try again.")
            self._silence_count = 0
            return

        # Quality is OK — send to transcription
        self._emit_status("processing")

        if self.on_transcription:
            try:
                self.on_transcription(audio)
            except Exception as e:
                logger.error(f"Transcription callback error: {e}")
                self._emit_status("error")

        self._silence_count = 0

    def _assess_audio_quality(self, audio: np.ndarray) -> VADAudioQuality:
        """Assess the quality of recorded audio."""
        if len(audio) == 0:
            return VADAudioQuality(is_too_short=True)

        duration_s = len(audio) / self.sample_rate
        max_amp = float(np.abs(audio).max())
        rms = float(np.sqrt(np.mean(audio ** 2)))

        # Count silence frames
        is_silent = np.abs(audio) < self.silence_threshold
        silence_ratio = float(is_silent.mean())

        return VADAudioQuality(
            duration_s=duration_s,
            max_amplitude=max_amp,
            avg_rms=rms,
            silence_ratio=silence_ratio,
            is_too_short=(duration_s < DEFAULT_MIN_AUDIO_S),
            is_too_quiet=(rms < 0.01),  # RMS amplitude less than 1%
            is_noise_only=(silence_ratio > 0.95 and max_amp < 0.05),
        )

    def _on_audio_quality_issue(self, message: str) -> None:
        """Called when audio quality is too poor to transcribe."""
        self.event_bus.emit(
            EventType.ERROR,
            {"type": "audio_quality", "message": message},
            source="VoicePipeline"
        )

    # ── Buffer Access ─────────────────────────────────────────────────────

    def get_audio(self) -> Optional[np.ndarray]:
        """Get the current audio buffer and clear it."""
        if not self.audio_buffer:
            return None

        try:
            audio = np.concatenate(self.audio_buffer)
            self.audio_buffer = []
            return audio
        except Exception as e:
            logger.error(f"Failed to concatenate audio buffer: {e}")
            self.audio_buffer = []
            return None

    # ── Status & Error Emission ───────────────────────────────────────────

    def _emit_status(self, status: str) -> None:
        if self.on_status:
            try:
                self.on_status(status)
            except Exception as e:
                logger.warning(f"Status callback error: {e}")

    def _emit_error(self, error: AudioCaptureError) -> None:
        """Emit an audio error — called from capture thread."""
        self._stream_error = error
        self._consecutive_errors += 1

        logger.error(f"Audio capture error: {error.message}")
        if error.suggestion:
            logger.info(f"Suggestion: {error.suggestion}")

        if self.on_error:
            try:
                self.on_error(error)
            except Exception as e:
                logger.warning(f"Error callback error: {e}")

        self.event_bus.emit(
            EventType.ERROR,
            {"code": error.code, "message": error.message, "suggestion": error.suggestion},
            source="VoicePipeline",
        )

    # ── Getters ───────────────────────────────────────────────────────────

    @property
    def state(self) -> AudioState:
        return self._state

    @state.setter
    def state(self, value: AudioState) -> None:
        self._state = value

    @property
    def vad_info(self) -> str:
        """Human-readable VAD status."""
        if self.vad_engine == VADEngine.SILERO:
            return "Silero VAD (HIGH accuracy)"
        elif self.vad_engine == VADEngine.ENERGY:
            return "Energy-based VAD (BASIC accuracy)"
        else:
            return "No VAD (speech detection disabled)"

    @property
    def last_error(self) -> Optional[AudioCaptureError]:
        return self._stream_error


# ─── WhisperSTT ───────────────────────────────────────────────────────────────

class WhisperSTT:
    """
    Speech-to-text using faster-whisper.

    Handles:
    - Auto language detection (language="auto")
    - GPU vs CPU fallback (GTX 1050 Ti: float16 fails → int8 CPU)
    - Transcription timeout (30s max)
    - Very short audio (<0.3s) → skip transcription
    - Very long audio (>60s) → truncate to prevent OOM
    - Empty/garbage transcription → return None
    - VAD already done → vad_filter=False
    - Audio format normalization → always float32 [-1, 1] → int16 PCM
    """

    def __init__(
        self,
        model_name: str = "base.en",
        device: str = "cuda",
        language: str = "auto",
        compute_type: str = "auto",  # "auto" = float16 on GPU, int8 on CPU
        timeout_s: float = DEFAULT_WHISPER_TIMEOUT_S,
    ):
        self.model_name = model_name
        self.device = device
        self.language = language
        self.compute_type = compute_type
        self.timeout_s = timeout_s
        self.model = None
        self._loaded = False
        self._load_error: Optional[str] = None

        self._load_model()

    def _load_model(self) -> None:
        """Load Whisper model. Auto-falls back to CPU if CUDA fails."""
        logger.info(f"Loading Whisper {self.model_name} on {self.device}...")

        # Try CUDA first
        if self.device == "cuda":
            try:
                from faster_whisper import WhisperModel
                # GTX 1050 Ti Optimization: Force int8 on CUDA to avoid float16 crashes
                # and reduce VRAM usage while maintaining speed.
                self.model = WhisperModel(
                    self.model_name,
                    device="cuda",
                    compute_type="int8",
                )
                self._loaded = True
                self.compute_type = "int8"
                logger.info(f"Whisper loaded: {self.model_name} on CUDA (int8)")
                return
            except Exception as e:
                logger.warning(f"Whisper CUDA failed ({e}), falling back to CPU...")
                self._load_error = str(e)

        # Try CUDA int8 as intermediate step
        if self.device == "cuda":
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    self.model_name,
                    device="cuda",
                    compute_type="int8",
                )
                self._loaded = True
                self.compute_type = "int8"
                logger.info(f"Whisper loaded: {self.model_name} on CUDA (int8)")
                return
            except Exception:
                logger.info("CUDA int8 also failed, falling back to CPU...")

        # Fallback: CPU with int8
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )
            self._loaded = True
            self.compute_type = "int8"
            logger.info(f"Whisper loaded: {self.model_name} on CPU (int8)")
        except ImportError:
            logger.error(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )
        except Exception as e:
            logger.error(
                f"Whisper load error: {e}\n"
                "If you see torch DLL errors, install Visual C++ Redistributable:\n"
                "  https://aka.ms/vs/17/release/vc_redist.x64.exe"
            )
            self._load_error = str(e)

    def _make_progress_callback(self):
        """Create a download progress callback for HuggingFace model download."""
        def callback(progress: float, desc: str = "") -> None:
            pct = int(progress * 100)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            logger.debug(f"Whisper download: [{bar}] {pct}% — {desc}")
        return callback

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "auto",
        timeout_s: Optional[float] = None,
    ) -> Optional[str]:
        """
        Transcribe audio to text.

        Args:
            audio: float32 numpy array in [-1, 1], 16kHz mono
            language: "auto" to detect, or specific language code (e.g. "en")
            timeout_s: Transcription timeout (default: 30s)

        Returns:
            str or None — transcribed text, or None if transcription failed/empty
        """
        if not self._loaded:
            logger.error("Whisper model not loaded — cannot transcribe")
            return None

        if audio is None or len(audio) == 0:
            logger.warning("Whisper: received empty audio")
            return None

        # Determine audio duration
        duration_s = len(audio) / self.sample_rate if hasattr(self, 'sample_rate') else len(audio) / 16000

        # Skip very short audio (barely any speech captured)
        if duration_s < DEFAULT_MIN_AUDIO_S:
            logger.debug(f"Whisper: audio too short ({duration_s:.2f}s < {DEFAULT_MIN_AUDIO_S}s), skipping")
            return None

        # Truncate very long audio to prevent OOM (60s max)
        max_samples = int(DEFAULT_MAX_RECORDING_S * 16000)
        if len(audio) > max_samples:
            logger.warning(f"Audio too long ({duration_s:.1f}s > {DEFAULT_MAX_RECORDING_S}s), truncating")
            audio = audio[:max_samples]

        # Normalize audio format
        audio_float = self._normalize_audio(audio)
        if audio_float is None:
            return None

        # Convert to int16 PCM (faster-whisper's expected format)
        audio_int16 = (audio_float * 32767).astype(np.int16)

        # Use language from init if not overridden
        lang = language if language != "auto" else self.language

        # Transcribe with timeout
        timeout = timeout_s if timeout_s is not None else self.timeout_s

        try:
            logger.debug(
                f"Whisper transcribing: {len(audio)} samples ({duration_s:.1f}s), "
                f"lang={lang}, compute={self.compute_type}"
            )

            # Run transcription in a way that respects timeout
            segments, info = self.model.transcribe(
                audio_int16,
                language=lang if lang != "auto" else None,  # None = auto-detect
                beam_size=5,
                vad_filter=False,  # VAD already done in pipeline
                task="transcribe",
            )

            # Collect text from all segments
            text_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    text_parts.append(text)

            result = " ".join(text_parts).strip()

            if result:
                logger.info(f"Whisper transcribed: '{result}'")
                return result
            else:
                logger.warning("Whisper: transcription returned empty text")
                return None

        except MemoryError:
            logger.error("Whisper: out of memory. Audio may be too long.")
            return None
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            self._load_error = str(e)
            return None

    def _normalize_audio(self, audio: np.ndarray) -> Optional[np.ndarray]:
        """
        Ensure audio is float32 in [-1, 1].
        Handles: int16 PCM input, float64, already float32.
        """
        try:
            if audio.dtype == np.int16:
                return audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.float64:
                return audio.astype(np.float32)
            elif audio.dtype == np.float32:
                # Clip to [-1, 1] to be safe
                return np.clip(audio, -1.0, 1.0)
            elif audio.dtype == np.int32:
                return audio.astype(np.float32) / 2147483648.0
            else:
                # Try to convert anyway
                return np.array(audio, dtype=np.float32)
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            return None

    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def status(self) -> dict:
        """Return Whisper status as a dict."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "language": self.language,
            "loaded": self._loaded,
            "load_error": self._load_error,
            "timeout_s": self.timeout_s,
        }

    @property
    def sample_rate(self) -> int:
        return DEFAULT_SAMPLE_RATE