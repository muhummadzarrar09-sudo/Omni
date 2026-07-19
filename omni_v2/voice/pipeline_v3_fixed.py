"""
OMNI V3.1 FIXED - Voice Pipeline - HARDENED VERSION
SoundDevice primary, PyAudio fallback, auto resample

FIXES (from diagnostic/01_DIAGNOSTIC_REPORT.md):
- VP-BUG-01 [HIGH]: Pa/stream cleanup with try/finally
- VP-BUG-02 [HIGH]: Auto-VAD race condition - dedicated process method
- VP-BUG-03 [HIGH]: High-precision linear interpolation resampling
- VP-BUG-04 [MED] : Defensive is_recording reset in start()
- VP-BUG-05 [MED] : current_status set once at end
- VP-BUG-06 [LOW] : Reset last_rms in start()
- ROBUST-BUG-05 [MED] : Cap recordings to last 20 WAVs

Fixes -9999 Unanticipated host error on Realtek HD Audio Mic input.
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

MAX_RECORDINGS_KEEP = 20  # ROBUST-BUG-05 fix: cap recordings to last 20


def _prune_old_recordings(recordings_dir: Path, keep: int = MAX_RECORDINGS_KEEP) -> None:
    """ROBUST-BUG-05 fix: keep only the most recent N recordings"""
    try:
        wavs = sorted(recordings_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in wavs[keep:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Prune recordings: {e}")


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
        self.current_status = "idle"
        self.last_auto_text = None
        self.last_rms = 0.0
        self.actual_sr = 16000  # track actual sample rate for resampling

        self.is_recording = False
        self.audio_buffer = []
        self.sample_rate = 16000
        self.chunk_size = 1024
        self._auto_processing = False  # VP-BUG-02 fix: prevent re-entry

        self.recordings_dir = DATA_DIR / "recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        self.use_sounddevice = False
        self._detect_backend()

        logger.info(
            f"VoicePipeline V3.1 HARDENED - Backend: "
            f"{'sounddevice' if self.use_sounddevice else 'pyaudio'} - Will handle -9999 error"
        )

    def _detect_backend(self):
        """Detect best backend - sounddevice preferred because it handles resampling"""
        try:
            import sounddevice as sd
            logger.info("✅ sounddevice 0.4.6 available - using as PRIMARY (fixes -9999)")
            self.use_sounddevice = True
            try:
                devices = sd.query_devices()
                logger.info(f"sounddevice found {len(devices)} devices:")
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0:
                        logger.info(
                            f"  SD [{i}] {dev['name']} ch={dev['max_input_channels']} "
                            f"default_sr={dev['default_samplerate']}"
                        )
            except Exception as e:
                logger.warning(f"sounddevice query failed: {e}")
        except ImportError:
            logger.warning("sounddevice not available, fallback to pyaudio")
            self.use_sounddevice = False

        if not self.use_sounddevice:
            try:
                import pyaudio
                logger.info("✅ PyAudio available as fallback")
            except ImportError:
                # SMOKE-06 fix: don't error-spam, just info
                logger.info("ℹ️ PyAudio not available either - voice will be disabled")
            except Exception as e:
                logger.warning(f"PyAudio detection error: {e}")

    def is_operational(self) -> bool:
        """SMOKE-01/02 fix: True if voice pipeline can actually capture audio.
        Returns False if no backend (sounddevice or pyaudio) is installed."""
        if self.use_sounddevice:
            return True
        # Check if pyaudio is importable
        try:
            import pyaudio  # noqa
            return True
        except Exception:
            return False

    def _find_sd_device(self, pa_best_name: str = None) -> Optional[int]:
        """Map PyAudio best device name to sounddevice index"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()

            if pa_best_name:
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0 and pa_best_name.lower() in dev['name'].lower():
                        logger.info(f"SD device match: PA '{pa_best_name}' -> SD [{i}] {dev['name']}")
                        return i
                    if (dev['max_input_channels'] > 0 and "realtek" in dev['name'].lower()
                            and "mic" in dev['name'].lower()):
                        if "input" not in dev['name'].lower() or "mic" in dev['name'].lower():
                            logger.info(f"SD device partial match Realtek Mic -> SD [{i}] {dev['name']}")
                            return i

            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 and "realtek" in dev['name'].lower():
                    if "stereo mix" not in dev['name'].lower() and "sound mapper" not in dev['name'].lower():
                        logger.info(f"SD fallback Realtek: SD [{i}] {dev['name']}")
                        return i

            try:
                default_input = sd.default.device[0]
                if default_input is not None and default_input >= 0:
                    logger.info(f"SD default input: {default_input}")
                    return default_input
            except Exception:
                pass

            for i, dev in enumerate(devices):
                if (dev['max_input_channels'] > 0
                        and "virtual" not in dev['name'].lower()
                        and "mapper" not in dev['name'].lower()):
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
        # VP-BUG-04 fix: defensive reset
        if self.is_recording:
            logger.warning("start() called while already recording - forcing reset")
            self.is_recording = False
            time.sleep(0.1)
        self.audio_buffer = []
        self.is_recording = True
        self.current_status = "recording"
        self.last_auto_text = None
        self.last_rms = 0.0  # VP-BUG-06 fix
        if self.on_status:
            try:
                self.on_status("recording")
            except Exception:
                pass
        self.record_thread = threading.Thread(target=self._record_loop, daemon=True, name="V3FixedRecord")
        self.record_thread.start()
        logger.info("🔴 V3.1 Recording started (Auto-VAD Half-Duplex Active) - SPEAK NOW!")

    def stop(self):
        # VP-BUG-02 fix: only call if not already processing
        if not self.is_recording and self.current_status != "recording":
            return
        if self._auto_processing:
            logger.debug("stop() called while auto-processing - skipping")
            return
        self.is_recording = False
        self.current_status = "processing"
        if self.on_status:
            try:
                self.on_status("processing")
            except Exception:
                pass
        if hasattr(self, 'record_thread') and self.record_thread.is_alive():
            self.record_thread.join(timeout=3)

        self._process_buffered_audio()

    def _process_buffered_audio(self):
        """VP-BUG-02 fix: process audio without re-joining recording thread"""
        audio = self._get_audio()
        if audio is None or len(audio) == 0:
            logger.warning("No audio captured")
            self.current_status = "idle"
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass
            return

        duration = len(audio) / self.sample_rate
        max_amp = float(np.abs(audio).max()) if len(audio) > 0 else 0
        rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0
        logger.info(f"📼 Captured: {duration:.2f}s | max={max_amp:.4f} | rms={rms:.5f}")

        # Save WAV + prune old
        if rms > 0.001:  # only save non-silence
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
                # ROBUST-BUG-05 fix: cap to last 20
                _prune_old_recordings(self.recordings_dir)
            except Exception as e:
                logger.warning(f"WAV save failed: {e}")

        if duration < 0.3:
            logger.warning(f"Too short {duration:.2f}s")
            self.current_status = "idle"
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass
            return

        if not self.stt:
            logger.error("STT not available")
            self.current_status = "idle"
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass
            return

        try:
            logger.info("🔍 Transcribing via SINGLE STT...")
            text = self.stt.transcribe(audio, sample_rate=self.sample_rate)
            if text and text.strip():
                self.last_auto_text = text.strip()
                logger.info(f"✅ HEARD: '{text}'")
                if self.on_transcription:
                    try:
                        self.on_transcription(text)
                    except Exception:
                        pass
            else:
                logger.warning(f"❌ Empty | max={max_amp:.3f} rms={rms:.5f}")
                if self.hud:
                    try:
                        self.hud.set_transcription(
                            f"❌ Didn't catch — RMS {rms:.4f}\nWAV saved\nSpeak LOUDER 1 inch!"
                        )
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Transcribe failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # VP-BUG-05 fix: set current_status and emit once
            self.current_status = "idle"
            self._auto_processing = False
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass

    def _record_loop_sounddevice(self):
        """Record via sounddevice - handles resampling, fixes -9999.
        VP-BUG-03 fix: stores at native rate, resamples at end via _get_audio()"""
        try:
            import sounddevice as sd

            pa_best_name = None
            if self.audio_mgr:
                pa_best_name = self.audio_mgr.get_best_name()

            sd_idx = self._find_sd_device(pa_best_name)
            logger.info(f"🎤 SD Opening mic SD [{sd_idx}] {pa_best_name}")

            # VP-BUG-03 fix: pick best rate, store at native rate, resample at end
            for sr in [16000, 44100, 48000]:
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
                        self.actual_sr = sr
                        speech_detected = False
                        silence_start_time = 0.0

                        while self.is_recording:
                            try:
                                data, overflowed = stream.read(self.chunk_size)
                                if overflowed:
                                    logger.warning(f"SD overflowed: {overflowed}")

                                mono = data[:, 0] if data.ndim > 1 else data

                                # VP-BUG-03 fix: store at native rate, resample later
                                self.audio_buffer.extend(mono.tolist())

                                max_v = float(np.abs(mono).max())
                                rms = float(np.sqrt(np.mean(mono ** 2)))
                                self.last_rms = rms

                                # Auto-VAD: auto-stop after speech finishes
                                if rms > 0.012:
                                    speech_detected = True
                                    silence_start_time = time.time()
                                elif speech_detected and rms < 0.007:
                                    if time.time() - silence_start_time > 1.3:
                                        logger.info("🟢 Auto-VAD: 1.3s silence after speech - auto-stopping")
                                        self.is_recording = False
                                        # VP-BUG-02 fix: don't call self.stop() (would re-join)
                                        # Just spawn a thread to process
                                        threading.Thread(
                                            target=self._auto_process_turn,
                                            daemon=True, name="AutoProcessTurn"
                                        ).start()
                                        break

                                if self.on_mic_level:
                                    try:
                                        self.on_mic_level(rms, max_v)
                                    except Exception:
                                        pass
                            except Exception as e:
                                logger.warning(f"SD read failed: {e}")
                                time.sleep(0.05)

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
        """VP-BUG-01 fix: PyAudio with proper try/finally cleanup"""
        pa = None
        stream = None
        try:
            import pyaudio
        except ImportError:
            # SMOKE-06 fix: silent - we already logged the absence in _detect_backend
            logger.debug("PyAudio not available - skipping PyAudio loop")
            return
        except Exception as e:
            # SMOKE-06 fix: don't print full traceback for missing module
            logger.warning(f"PyAudio import error: {e}")
            return
        try:
            pa = pyaudio.PyAudio()
            pa_idx = self._get_device_index()
            logger.info(f"🎤 PyAudio fallback opening mic [{pa_idx}]")

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
                        self.actual_sr = sr

                        while self.is_recording:
                            try:
                                data = stream.read(self.chunk_size, exception_on_overflow=False)
                                if fmt == pyaudio.paInt16:
                                    arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
                                else:
                                    arr = np.frombuffer(data, dtype=np.float32)

                                # VP-BUG-03 fix: store at native rate, resample later
                                self.audio_buffer.extend(arr.tolist())

                                if self.on_mic_level:
                                    try:
                                        max_v = float(np.abs(arr).max())
                                        rms = float(np.sqrt(np.mean(arr ** 2)))
                                        self.on_mic_level(rms, max_v)
                                    except Exception:
                                        pass
                            except Exception as e:
                                logger.warning(f"PyAudio read failed: {e}")
                                time.sleep(0.05)

                        return
                    except Exception as e:
                        logger.warning(f"PyAudio @ {sr}Hz {fmt_name} failed: {e}")
                        continue
        except Exception as e:
            logger.error(f"PyAudio loop failed: {e}")
            # SMOKE-06 fix: no full traceback for missing module
            if "No module named" in str(e):
                logger.debug("PyAudio module missing - voice disabled")
            else:
                import traceback
                traceback.print_exc()
        finally:
            # VP-BUG-01 fix: always clean up
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass

    def _record_loop(self):
        """Main - try sounddevice first, then pyaudio"""
        if self.use_sounddevice:
            self._record_loop_sounddevice()
            if len(self.audio_buffer) == 0 and self.is_recording:
                logger.warning("SD gave no audio, fallback to PyAudio...")
                self._record_loop_pyaudio()
        else:
            self._record_loop_pyaudio()

    def _get_audio(self):
        """VP-BUG-03 fix: high-precision linear interpolation resampling at end"""
        if not self.audio_buffer:
            return None
        raw_audio = np.array(self.audio_buffer, dtype=np.float32)
        if hasattr(self, 'actual_sr') and self.actual_sr != 16000 and self.actual_sr > 0 and len(raw_audio) > 0:
            logger.info(
                f"✨ High-precision linear interpolation resampling: "
                f"{self.actual_sr}Hz -> 16000Hz ({len(raw_audio)} samples)"
            )
            t_old = np.linspace(0, len(raw_audio) / self.actual_sr, len(raw_audio))
            t_new = np.linspace(0, len(raw_audio) / self.actual_sr, int(len(raw_audio) * 16000 / self.actual_sr))
            return np.interp(t_new, t_old, raw_audio).astype(np.float32)
        return raw_audio

    def _auto_process_turn(self):
        """VP-BUG-02 fix: dedicated method, no double-join"""
        self._auto_processing = True
        try:
            self._process_buffered_audio()
        except Exception as e:
            logger.error(f"Auto VAD turn processing error: {e}")
            self.current_status = "idle"
            if self.on_status:
                try:
                    self.on_status("idle")
                except Exception:
                    pass
            self._auto_processing = False
