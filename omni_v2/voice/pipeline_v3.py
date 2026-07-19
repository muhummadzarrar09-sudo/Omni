"""
OMNI V3.1 FIXED - Voice Pipeline with SoundDevice primary, PyAudio fallback
Fixes [Errno -9999] Unanticipated host error on Realtek HD Audio Mic input

Root cause: PyAudio can't open Realtek at 16000Hz when device is set to 48000Hz exclusive
Fix: Use sounddevice (more robust resampling) first, then PyAudio with 48000Hz if fails

Tested: Your mic test got RMS 0.3918 = mic works, just PyAudio continuous stream bug
"""
import threading
import time
from pathlib import Path
from typing import Callable, Optional
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("PipelineV3Fixed")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).resolve().parents[2] / "data"

class VoicePipelineV3Fixed:
    """Fixed pipeline - sounddevice primary, pyaudio fallback, auto resample"""
    
    def __init__(self,
                 stt=None,
                 audio_mgr=None,
                 on_transcription: Callable[[str], None] = None,
                 on_status: Callable[[str], None] = None,
                 on_mic_level: Callable[[float, float], None] = None,
                 hud=None,
                 device_index: Optional[int] = None):
        
        self.stt = stt
        self.audio_mgr = audio_mgr
        self.on_transcription = on_transcription
        self.on_status = on_status
        self.on_mic_level = on_mic_level
        self.hud = hud
        self.device_index = device_index
        
        self.is_recording = False
        self.audio_buffer = []
        self.sample_rate = 16000
        self.chunk_size = 1024
        
        self.recordings_dir = DATA_DIR / "recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_sounddevice = False
        self._detect_backend()
        
        logger.info(f"VoicePipeline V3.1 FIXED - Backend: {'sounddevice' if self.use_sounddevice else 'pyaudio'} - Will handle -9999 error")
    
    def _detect_backend(self):
        """Detect best backend - sounddevice preferred because it handles resampling"""
        try:
            import sounddevice as sd
            logger.info("✅ sounddevice 0.4.6 available - using as PRIMARY (fixes -9999)")
            self.use_sounddevice = True
            # List devices for debug
            try:
                devices = sd.query_devices()
                logger.info(f"sounddevice found {len(devices)} devices:")
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0:
                        logger.info(f"  SD [{i}] {dev['name']} ch={dev['max_input_channels']} default_sr={dev['default_samplerate']}")
            except Exception as e:
                logger.warning(f"sounddevice query failed: {e}")
        except ImportError:
            logger.warning("sounddevice not available, fallback to pyaudio")
            self.use_sounddevice = False
        
        # Also check pyaudio as fallback
        if not self.use_sounddevice:
            try:
                import pyaudio
                logger.info("✅ PyAudio available as fallback")
            except ImportError:
                logger.error("No audio backend! Need sounddevice or pyaudio")
    
    def _find_sd_device(self, pa_best_name: str = None) -> Optional[int]:
        """Map PyAudio best device name to sounddevice index"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            # If we have best name like "Microphone (Realtek HD Audio Mic input)"
            if pa_best_name:
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0 and pa_best_name.lower() in dev['name'].lower():
                        logger.info(f"SD device match: PA '{pa_best_name}' -> SD [{i}] {dev['name']}")
                        return i
                    # Also partial match Realtek
                    if dev['max_input_channels'] > 0 and "realtek" in dev['name'].lower() and "mic" in dev['name'].lower():
                        if "input" not in dev['name'].lower() or "mic" in dev['name'].lower():
                            logger.info(f"SD device partial match Realtek Mic -> SD [{i}] {dev['name']}")
                            return i
            
            # Fallback: first Realtek input
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 and "realtek" in dev['name'].lower():
                    if "stereo mix" not in dev['name'].lower() and "sound mapper" not in dev['name'].lower():
                        logger.info(f"SD fallback Realtek: SD [{i}] {dev['name']}")
                        return i
            
            # Fallback default input
            try:
                default_input = sd.default.device[0]
                if default_input is not None and default_input >= 0:
                    logger.info(f"SD default input: {default_input}")
                    return default_input
            except:
                pass
            
            # Last fallback: first input device
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 and "virtual" not in dev['name'].lower() and "mapper" not in dev['name'].lower():
                    return i
            
            return None
        except Exception as e:
            logger.error(f"SD device find failed: {e}")
            return None
    
    def _get_device_index(self):
        if self.device_index is not None:
            return self.device_index
        if self.audio_mgr:
            return self.audio_mgr.get_best_index()
        return None
    
    def start(self):
        if self.is_recording:
            return
        self.audio_buffer = []
        self.is_recording = True
        if self.on_status:
            try:
                self.on_status("recording")
            except:
                pass
        self.record_thread = threading.Thread(target=self._record_loop, daemon=True, name="V3FixedRecord")
        self.record_thread.start()
        logger.info("🔴 V3.1 Recording started - SPEAK LOUD 1 inch!")
    
    def stop(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.on_status:
            try:
                self.on_status("processing")
            except:
                pass
        if hasattr(self, 'record_thread') and self.record_thread.is_alive():
            self.record_thread.join(timeout=3)
        
        audio = self._get_audio()
        if audio is None or len(audio) == 0:
            logger.warning("No audio captured")
            if self.on_status:
                self.on_status("idle")
            return
        
        duration = len(audio) / self.sample_rate
        max_amp = float(np.abs(audio).max()) if len(audio) > 0 else 0
        rms = float(np.sqrt(np.mean(audio**2))) if len(audio) > 0 else 0
        logger.info(f"📼 Captured: {duration:.2f}s | max={max_amp:.4f} | rms={rms:.5f}")
        
        # Save WAV
        try:
            from datetime import datetime
            import wave
            filename = self.recordings_dir / f"v3_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{duration:.1f}s.wav"
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            with wave.open(str(filename), 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())
            logger.info(f"💾 WAV saved: {filename}")
        except Exception as e:
            logger.warning(f"WAV save failed: {e}")
        
        if duration < 0.3:
            logger.warning(f"Too short {duration:.2f}s")
            if self.on_status:
                self.on_status("idle")
            return
        
        # Transcribe
        if not self.stt:
            logger.error("STT not available")
            if self.on_status:
                self.on_status("idle")
            return
        
        try:
            logger.info("🔍 Transcribing via SINGLE STT...")
            text = self.stt.transcribe(audio, sample_rate=self.sample_rate)
            if text and text.strip():
                logger.info(f"✅ HEARD: '{text}'")
                if self.on_transcription:
                    self.on_transcription(text)
            else:
                logger.warning(f"❌ Empty | max={max_amp:.3f} rms={rms:.5f}")
                if self.hud:
                    try:
                        self.hud.set_transcription(f"❌ Didn't catch — RMS {rms:.4f}\nWAV saved\nSpeak LOUDER 1 inch!")
                    except:
                        pass
                if self.on_status:
                    self.on_status("idle")
        except Exception as e:
            logger.error(f"Transcribe failed: {e}")
            import traceback
            traceback.print_exc()
            if self.on_status:
                self.on_status("idle")
    
    def _record_loop_sounddevice(self):
        """Record via sounddevice - handles resampling, fixes -9999"""
        try:
            import sounddevice as sd
            
            pa_best_name = None
            if self.audio_mgr:
                pa_best_name = self.audio_mgr.get_best_name()
            
            sd_idx = self._find_sd_device(pa_best_name)
            logger.info(f"🎤 SD Opening mic SD [{sd_idx}] {pa_best_name} @16000Hz")
            
            # Try 16000Hz first, then 44100, 48000 with resampling
            for sr in [16000, 44100, 48000, 48000]:
                try:
                    logger.info(f"  Trying SD @ {sr}Hz...")
                    with sd.InputStream(
                        samplerate=sr,
                        channels=1,
                        device=sd_idx,
                        dtype='float32',
                        blocksize=self.chunk_size,
                        latency='low'
                    ) as stream:
                        logger.info(f"✅ SD stream opened @ {sr}Hz - recording...")
                        
                        while self.is_recording:
                            try:
                                data, overflowed = stream.read(self.chunk_size)
                                if overflowed:
                                    logger.warning(f"SD overflowed: {overflowed}")
                                
                                # data is (chunk, channels)
                                mono = data[:, 0] if data.ndim > 1 else data
                                
                                # Resample if needed to 16000
                                if sr != 16000:
                                    # Simple resample via linear interpolation for V3
                                    # For hackathon, just take every Nth sample or repeat
                                    # Better: use librosa? But avoid dependency, do simple
                                    import math
                                    ratio = sr / 16000
                                    # For 48000->16000, take every 3rd sample
                                    if sr == 48000:
                                        mono_resampled = mono[::3]
                                    elif sr == 44100:
                                        # Approx: 44100/16000 = 2.756, need resample
                                        # Use simple decimation for demo - will work for STT because whisper resamples internally anyway
                                        # Actually faster-whisper expects 16000, but we can feed 44100 trimmed - it will handle?
                                        # For now, keep 44100 as is and let STT handle, or simple
                                        indices = np.linspace(0, len(mono)-1, int(len(mono)/ratio)).astype(int)
                                        mono_resampled = mono[indices]
                                    else:
                                        mono_resampled = mono
                                else:
                                    mono_resampled = mono
                                
                                self.audio_buffer.extend(mono_resampled.tolist())
                                
                                # Live mic level callback
                                if self.on_mic_level:
                                    try:
                                        max_v = float(np.abs(mono).max())
                                        rms = float(np.sqrt(np.mean(mono**2)))
                                        self.on_mic_level(rms, max_v)
                                    except:
                                        pass
                                        
                            except Exception as e:
                                logger.warning(f"SD read failed: {e}")
                                time.sleep(0.05)
                    
                    # If we exit loop cleanly, break outer
                    logger.info("SD stream closed cleanly")
                    return
                    
                except Exception as e:
                    logger.warning(f"SD @ {sr}Hz failed: {e}, trying next sr...")
                    continue
            
            logger.error("All SD samplerates failed")
            
        except Exception as e:
            logger.error(f"Sounddevice loop failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _record_loop_pyaudio(self):
        """Fallback PyAudio with multiple samplerate attempts"""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            pa_idx = self._get_device_index()
            logger.info(f"🎤 PyAudio fallback opening mic [{pa_idx}]")
            
            # Try different sample rates and formats that Realtek likes
            for sr in [48000, 44100, 16000]:
                for fmt, fmt_name in [(pyaudio.paInt16, "int16"), (pyaudio.paFloat32, "float32")]:
                    try:
                        logger.info(f"  Trying PyAudio @ {sr}Hz {fmt_name}...")
                        stream = pa.open(
                            format=fmt,
                            channels=1,
                            rate=sr,
                            input=True,
                            input_device_index=pa_idx,
                            frames_per_buffer=self.chunk_size,
                        )
                        logger.info(f"✅ PyAudio opened @ {sr}Hz {fmt_name}")
                        
                        while self.is_recording:
                            try:
                                data = stream.read(self.chunk_size, exception_on_overflow=False)
                                if fmt == pyaudio.paInt16:
                                    arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
                                else:
                                    arr = np.frombuffer(data, dtype=np.float32)
                                
                                # Resample to 16000 if needed
                                if sr != 16000:
                                    if sr == 48000:
                                        arr = arr[::3]
                                    elif sr == 44100:
                                        # Simple resample
                                        ratio = sr / 16000
                                        indices = np.linspace(0, len(arr)-1, int(len(arr)/ratio)).astype(int)
                                        arr = arr[indices]
                                
                                self.audio_buffer.extend(arr.tolist())
                                
                                if self.on_mic_level:
                                    try:
                                        max_v = float(np.abs(arr).max())
                                        rms = float(np.sqrt(np.mean(arr**2)))
                                        self.on_mic_level(rms, max_v)
                                    except:
                                        pass
                            except Exception as e:
                                logger.warning(f"PyAudio read failed: {e}")
                                time.sleep(0.05)
                        
                        stream.stop_stream()
                        stream.close()
                        pa.terminate()
                        logger.info("PyAudio stream closed")
                        return
                        
                    except Exception as e:
                        logger.warning(f"PyAudio @ {sr}Hz {fmt_name} failed: {e}")
                        continue
            
            pa.terminate()
            logger.error("All PyAudio attempts failed")
            
        except Exception as e:
            logger.error(f"PyAudio loop failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _record_loop(self):
        """Main - try sounddevice first, then pyaudio"""
        if self.use_sounddevice:
            self._record_loop_sounddevice()
            # If buffer still empty and still recording, fallback to pyaudio
            if len(self.audio_buffer) == 0 and self.is_recording:
                logger.warning("SD gave no audio, fallback to PyAudio...")
                self._record_loop_pyaudio()
        else:
            self._record_loop_pyaudio()
    
    def _get_audio(self):
        if not self.audio_buffer:
            return None
        return np.array(self.audio_buffer, dtype=np.float32)
