"""
OMNI V3 - STT SIMPLE - ONE ENGINE THAT WORKS
No 4 tiers, no Vosk, no Google. Just faster-whisper base.en INT8 single engine.
Designed for GTX 1050 Ti 4GB - Actually HEARS.
"""
import os
from pathlib import Path
from typing import Optional
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("STTSimpleV3")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"
    DATA_DIR = Path.cwd() / "data"

class SimpleSTT:
    """One engine, reliable, no fighting"""
    
    def __init__(self, model_size: str = "base.en"):
        self.model = None
        self.device = "cpu"
        self.compute_type = "int8"
        self.model_size = model_size
        self.recordings_dir = DATA_DIR / "recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self._init_model()
    
    def _init_model(self):
        """Init once, CUDA INT8 first, then CPU INT8"""
        try:
            from faster_whisper import WhisperModel
            
            # Try CUDA INT8 first - perfect for 1050 Ti
            for device, compute in [("cuda", "int8"), ("cpu", "int8"), ("cpu", "int8_float32")]:
                try:
                    logger.info(f"STT V3 - Trying {self.model_size} on {device} {compute}...")
                    self.model = WhisperModel(self.model_size, device=device, compute_type=compute)
                    self.device = device
                    self.compute_type = compute
                    logger.info(f"✅ STT V3 READY: {self.model_size} on {device} {compute} - SINGLE ENGINE, WILL HEAR")
                    return
                except Exception as e:
                    logger.warning(f"STT {device} {compute} failed: {e}")
                    continue
            
            logger.error("STT V3 - All devices failed!")
            self.model = None
            
        except ImportError as e:
            logger.error(f"faster-whisper not installed: {e} - pip install faster-whisper==1.0.3")
            self.model = None
        except Exception as e:
            logger.error(f"STT V3 init failed: {e}")
            self.model = None
    
    def _trim_silence(self, audio: np.ndarray, threshold: float = 0.005, pad_ms: int = 200, sample_rate: int = 16000) -> np.ndarray:
        """Light trim, keep pad - don't cut aggressive like before"""
        if len(audio) == 0:
            return audio
        
        # Find first sample above threshold
        abs_audio = np.abs(audio)
        above = np.where(abs_audio > threshold)[0]
        
        if len(above) == 0:
            return audio  # All silence, return original
        
        start = max(0, above[0] - int(sample_rate * pad_ms / 1000))
        end = min(len(audio), above[-1] + int(sample_rate * pad_ms / 1000) + 1)
        
        trimmed = audio[start:end]
        logger.debug(f"Trim: {len(audio)} -> {len(trimmed)} samples ({len(audio)/sample_rate:.2f}s -> {len(trimmed)/sample_rate:.2f}s)")
        return trimmed
    
    def _is_hallucination(self, text: str) -> bool:
        """Filter Whisper hallucinations when audio is silence/noise"""
        text_lower = text.lower().strip()
        hallucinations = [
            "i don't think i'm going to do that",
            "thank you",
            "thanks",
            "you",
            "the",
            "",
            "  ",
        ]
        # If text too short and is exactly hallucination
        if text_lower in hallucinations and len(text) < 15:
            return True
        # If text is repeated single word many times
        if len(set(text_lower.split())) == 1 and len(text_lower.split()) > 3:
            return True
        return False
    
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """Transcribe - single engine, reliable"""
        if self.model is None:
            logger.error("STT model not loaded")
            return None
        
        if audio is None or len(audio) == 0:
            logger.warning("No audio")
            return None
        
        duration = len(audio) / sample_rate
        max_amp = float(np.abs(audio).max()) if len(audio) > 0 else 0
        rms = float(np.sqrt(np.mean(audio**2))) if len(audio) > 0 else 0
        
        logger.info(f"🎤 Transcribe: {duration:.2f}s | max={max_amp:.4f} | rms={rms:.5f} | device={self.device}")
        
        # Save WAV for debug BEFORE processing
        try:
            from datetime import datetime
            import wave
            filename = self.recordings_dir / f"v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{duration:.1f}s_rms{rms:.4f}.wav"
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            with wave.open(str(filename), 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
            logger.info(f"💾 Saved WAV: {filename} - play it to verify mic captured")
        except Exception as e:
            logger.warning(f"Failed to save WAV: {e}")
        
        # Duration check - permissive
        if duration < 0.3:
            logger.warning(f"Audio too short: {duration:.2f}s < 0.3s - hold V longer!")
            return None
        
        # RMS check - very permissive for accessibility
        if rms < 0.0008:
            logger.warning(f"Audio too quiet: rms={rms:.5f} < 0.0008 - speak LOUDER, CLOSER (1 inch!), mic boost 100%+30dB")
            # Still try anyway, don't block
        
        try:
            # Trim lightly
            trimmed = self._trim_silence(audio, threshold=0.005, pad_ms=200, sample_rate=sample_rate)
            
            # Single engine transcribe - GREEDY beam_size=1 = robust for noisy, no hallucination
            logger.info(f"🔍 Whisper {self.model_size} transcribing... lang=en beam=1 (greedy) vad_filter=False")
            segments, info = self.model.transcribe(
                trimmed,
                language="en",
                beam_size=1,  # Greedy - most robust, not beam 5
                vad_filter=False,  # We have manual PTT, don't auto filter silence
                task="transcribe",
                condition_on_previous_text=False,  # Prevent hallucination from previous
                no_speech_threshold=0.4,  # Slightly higher, less hallucination
                log_prob_threshold=-1.0,
                compression_ratio_threshold=2.4,
            )
            
            text_parts = []
            for seg in segments:
                txt = seg.text.strip()
                if txt:
                    text_parts.append(txt)
            
            full_text = " ".join(text_parts).strip()
            
            if not full_text:
                logger.warning(f"❌ Whisper returned empty | max={max_amp:.3f} rms={rms:.5f} | WAV saved, play it!")
                logger.warning("Try: LOUDER, CLOSER, boost mic 100%+30dB, hold V 1sec before/after")
                return None
            
            if self._is_hallucination(full_text):
                logger.warning(f"⚠️ Hallucination filtered: '{full_text}' - likely silence/noise")
                return None
            
            logger.info(f"✅ HEARD YOU! '{full_text}' | rms={rms:.5f} max={max_amp:.4f} | device={self.device}")
            return full_text
            
        except Exception as e:
            logger.error(f"Transcribe failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def get_status(self):
        return {
            "model": self.model_size,
            "device": self.device,
            "compute": self.compute_type,
            "available": self.model is not None,
            "recordings_dir": str(self.recordings_dir)
        }

# Singleton for V3
_simple_stt_instance = None

def get_simple_stt():
    global _simple_stt_instance
    if _simple_stt_instance is None:
        _simple_stt_instance = SimpleSTT()
    return _simple_stt_instance
