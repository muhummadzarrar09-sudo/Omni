"""
OMNI Voice Pipeline - Complete Voice Recognition System
Handles: Audio Capture → VAD → Whisper STT → Command Execution
"""

import numpy as np
import threading
import queue
from typing import Optional, Callable
from loguru import logger

from omni.core.event_bus import EventBus, EventType


class VoicePipeline:
    """
    Complete voice processing pipeline:
    PTT Press → VAD Detection → Audio Buffer → Whisper → Command
    """
    
    def __init__(
        self,
        event_bus: EventBus = None,
        on_transcription: Callable[[str], None] = None,
        on_status: Callable[[str], None] = None
    ):
        self.event_bus = event_bus or EventBus()
        self.on_transcription = on_transcription
        self.on_status = on_status
        
        # Components
        self.audio_buffer = []
        self.is_recording = False
        self.recording_thread = None
        self.audio_stream = None
        self.audio_interface = None
        
        # VAD
        self.vad_model = None
        self._load_vad()
        
        # State
        self.sample_rate = 16000
        self.speech_threshold = 0.5
        
        logger.info("VoicePipeline initialized")
    
    def _load_vad(self) -> None:
        """Load Silero VAD model — falls back to energy-based if torch fails."""
        try:
            import torch
            torch.set_num_threads(1)

            self.vad_model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                trust_repo=True
            )
            self.get_speech_ts = utils[0]
            logger.info("Silero VAD loaded")

        except Exception as e:
            logger.warning(
                f"VAD not loaded ({e}). Using energy-based speech detection. "
                "If you see torch DLL errors, install Visual C++ Redistributable "
                "or update your GPU drivers."
            )
            self.vad_model = None
    
    def start(self) -> None:
        """Start the voice pipeline"""
        if self.recording_thread and self.recording_thread.is_alive():
            return
        
        self.audio_buffer = []
        self.is_recording = True
        
        self.recording_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="VoiceCapture"
        )
        self.recording_thread.start()
        logger.info("Voice capture started")
    
    def stop(self) -> None:
        """Stop the voice pipeline"""
        self.is_recording = False
        
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        if self.audio_interface:
            self.audio_interface.terminate()
        
        logger.info("Voice capture stopped")
    
    def _capture_loop(self) -> None:
        """Main audio capture loop"""
        try:
            import pyaudio
            
            self.audio_interface = pyaudio.PyAudio()
            self.audio_stream = self.audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            
            self.audio_stream.start_stream()
            
            # Keep thread alive
            while self.is_recording:
                import time
                time.sleep(0.1)
                
        except ImportError:
            logger.error("PyAudio not installed")
        except Exception as e:
            logger.error(f"Audio capture error: {e}")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio stream callback"""
        if status:
            logger.warning(f"Audio status: {status}")
        
        # Convert to numpy
        audio_np = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # VAD check
        is_speech = self._detect_speech(audio_np)
        
        if is_speech:
            self.audio_buffer.append(audio_np)
            if self.on_status:
                self.on_status("recording")
        elif self.audio_buffer:
            # Check for silence end
            if self._check_silence():
                self._end_recording()
        
        return (in_data, pyaudio.paContinue)
    
    def _detect_speech(self, audio_chunk: np.ndarray) -> bool:
        """Detect if audio contains speech"""
        if self.vad_model is not None:
            try:
                speech_prob = self.vad_model(audio_chunk, self.sample_rate).item()
                return speech_prob > self.speech_threshold
            except:
                pass
        
        # Fallback: Energy-based
        energy = np.abs(audio_chunk).mean()
        return energy > 0.02
    
    def _check_silence(self) -> bool:
        """Check if recording should end"""
        if len(self.audio_buffer) < 10:
            return False
        
        # Check last ~0.3 seconds
        recent = np.concatenate(self.audio_buffer[-5:])
        energy = np.abs(recent).mean()
        return energy < 0.01
    
    def _end_recording(self) -> None:
        """End recording and trigger transcription"""
        if not self.audio_buffer:
            return
        
        # Get audio
        audio = np.concatenate(self.audio_buffer)
        self.audio_buffer = []
        
        if self.on_status:
            self.on_status("processing")
        
        # Send to transcription
        if self.on_transcription:
            self.on_transcription(audio)
        
        if self.on_status:
            self.on_status("idle")
    
    def get_audio(self) -> np.ndarray:
        """Get current audio buffer"""
        if not self.audio_buffer:
            return np.array([])
        
        audio = np.concatenate(self.audio_buffer)
        self.audio_buffer = []
        return audio


class WhisperSTT:
    """Speech-to-text using faster-whisper"""
    
    def __init__(self, model_name: str = "base.en", device: str = "cuda"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self._loaded = False
        self._load_model()
    
    def _load_model(self) -> None:
        """Load Whisper model — auto-falls back to CPU if CUDA fails."""
        # Try CUDA first if requested
        if self.device == "cuda":
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    self.model_name,
                    device="cuda",
                    compute_type="float16"
                )
                self._loaded = True
                logger.info(f"Whisper loaded: {self.model_name} on CUDA")
                return
            except Exception as e:
                logger.warning(f"Whisper CUDA failed ({e}), falling back to CPU...")
        
        # Fallback: CPU with int8 (works on any hardware, no GPU needed)
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8"
            )
            self._loaded = True
            logger.info(f"Whisper loaded: {self.model_name} on CPU (int8)")
        except ImportError:
            logger.error("faster-whisper not installed — run: pip install faster-whisper")
        except Exception as e:
            logger.error(
                f"Whisper load error: {e}\n"
                "If you see torch DLL errors, install the Visual C++ Redistributable "
                "from: https://aka.ms/vs/17/release/vc_redist.x64.exe"
            )
    
    def transcribe(self, audio: np.ndarray, language: str = "en") -> Optional[str]:
        """Transcribe audio to text"""
        if not self._loaded:
            return None
        
        if len(audio) == 0:
            return None
        
        try:
            import torch
            
            if not isinstance(audio, torch.Tensor):
                audio_tensor = torch.from_numpy(audio).float()
            else:
                audio_tensor = audio
            
            segments, info = self.model.transcribe(
                audio_tensor,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300)
            )
            
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            result = " ".join(text_parts)
            logger.info(f"Transcribed: '{result}'")
            
            return result.strip() if result else None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def is_loaded(self) -> bool:
        return self._loaded