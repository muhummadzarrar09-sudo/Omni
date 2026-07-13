"""
Audio Device Manager V2 - Fixed for Realtek Mic + No Sound Mapper
"""

import platform
import threading
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("AudioDeviceV2")

@dataclass
class AudioDevice:
    index: int
    name: str
    is_input: bool
    max_channels: int
    default_sample_rate: float
    is_default: bool = False

@dataclass
class AudioSystemStatus:
    system: str
    pyaudio_available: bool
    default_input_device: Optional[AudioDevice] = None
    all_input_devices: list[AudioDevice] = field(default_factory=list)
    current_input_index: Optional[int] = None
    current_probe_status: str = "not_probe"
    last_error: Optional[str] = None
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024

    @property
    def device_count(self):
        return len(self.all_input_devices)

    def summary(self):
        lines = [
            f"System: {self.system}",
            f"PyAudio: {'available' if self.pyaudio_available else 'not'}",
            f"Mics found: {self.device_count}",
            f"Default mic: {self.default_input_device.name if self.default_input_device else 'None'}",
            f"Probe status: {self.current_probe_status}",
        ]
        if self.last_error:
            lines.append(f"Last error: {self.last_error}")
        return "\n".join(lines)

class AudioDeviceManager:
    _instance = None

    def __init__(self, preferred_device_index: Optional[int] = None):
        AudioDeviceManager._instance = self
        self._pyaudio = None
        self._status = AudioSystemStatus(system=platform.system().lower(), pyaudio_available=False)
        self._preferred_index = preferred_device_index
        self._probe_lock = threading.Lock()
        self._init_pyaudio()
        self._detect_devices()
        self._probe_default_device()

    @staticmethod
    def get_instance():
        return AudioDeviceManager._instance

    def _init_pyaudio(self):
        try:
            import pyaudio
            self._pyaudio = pyaudio
            self._status.pyaudio_available = True
        except ImportError:
            self._status.last_error = "PyAudio not installed"
        except Exception as e:
            self._status.last_error = f"PyAudio init failed: {e}"

    def _is_virtual_device(self, name: str) -> bool:
        lower = name.lower()
        virtual_keywords = ["sound mapper", "primary sound capture", "stereo mix", "what u hear", "wave out", "microsoft sound mapper"]
        return any(kw in lower for kw in virtual_keywords)

    def _find_best_microphone(self, devices):
        if not devices:
            return None
        real_mics = [d for d in devices if not self._is_virtual_device(d.name)]
        if not real_mics:
            real_mics = devices

        def score_mic(d):
            score = 0
            name_lower = d.name.lower()
            if "realtek" in name_lower:
                score += 100
            if "microphone" in name_lower and "stereo mix" not in name_lower:
                score += 50
            if "hd audio" in name_lower:
                score += 20
            if d.default_sample_rate >= 48000:
                score += 10
            if d.is_default:
                score += 5
            score -= d.index
            return score

        real_mics.sort(key=score_mic, reverse=True)
        if real_mics:
            logger.info(f"Best mic: [{real_mics[0].index}] {real_mics[0].name} (score {score_mic(real_mics[0])})")
            return real_mics[0]
        return None

    def _detect_devices(self):
        if self._pyaudio is None:
            return
        try:
            pa = self._pyaudio.PyAudio()
            device_count = pa.get_device_count()
            try:
                default_input_index = pa.get_default_input_device()
            except Exception:
                default_input_index = -1

            input_devices = []
            for i in range(device_count):
                try:
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        device = AudioDevice(
                            index=i,
                            name=info['name'][:60],
                            is_input=True,
                            max_channels=info['maxInputChannels'],
                            default_sample_rate=info['defaultSampleRate'],
                            is_default=(i == default_input_index),
                        )
                        input_devices.append(device)
                except Exception:
                    continue

            pa.terminate()
            self._status.all_input_devices = input_devices

            real_default = None
            for d in input_devices:
                if d.is_default and not self._is_virtual_device(d.name):
                    real_default = d
                    break

            if real_default:
                self._status.default_input_device = real_default
            else:
                best = self._find_best_microphone(input_devices)
                self._status.default_input_device = best
                if best:
                    logger.info(f"System default virtual/None, using best real mic: [{best.index}] {best.name}")

            if input_devices:
                logger.info(f"Found {len(input_devices)} input device(s)")
            else:
                self._status.last_error = "No microphone input devices found"

        except Exception as e:
            self._status.last_error = f"Device detection failed: {e}"

    def _probe_default_device(self):
        target_index = self._preferred_index
        candidates = []

        if target_index is not None:
            candidates.append(target_index)

        if self._status.default_input_device:
            if self._status.default_input_device.index not in candidates:
                candidates.append(self._status.default_input_device.index)

        best = self._find_best_microphone(self._status.all_input_devices)
        if best and best.index not in candidates:
            candidates.append(best.index)

        for d in self._status.all_input_devices:
            if not self._is_virtual_device(d.name) and d.index not in candidates:
                candidates.append(d.index)

        for d in self._status.all_input_devices:
            if d.index not in candidates:
                candidates.append(d.index)

        if not candidates:
            self._status.current_probe_status = "failed"
            self._status.last_error = "No device to probe"
            return

        for idx in candidates:
            logger.info(f"Trying mic [{idx}] as recording device...")
            ok, error = self._probe_device(idx)
            if ok:
                self._status.current_input_index = idx
                self._status.current_probe_status = "ok"
                self._status.last_error = None
                logger.info(f"Mic [{idx}] probe OK - using this device")
                return
            else:
                logger.warning(f"Mic [{idx}] probe failed: {error}")

        self._status.current_input_index = candidates[0] if candidates else None
        self._status.current_probe_status = "failed"
        self._status.last_error = "All microphones failed probe"

    def _probe_device(self, device_index: int):
        if self._pyaudio is None:
            return False, "PyAudio not initialized"
        with self._probe_lock:
            probe = None
            try:
                probe = self._pyaudio.PyAudio()
                stream = probe.open(
                    format=self._pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=512,
                    start=True,
                )
                import time
                time.sleep(0.5)
                data = stream.read(512, exception_on_overflow=False)
                import numpy as np
                audio = np.frombuffer(data, dtype=np.int16)
                max_val = np.abs(audio).max()
                stream.stop_stream()
                stream.close()
                probe.terminate()
                return True, None
            except Exception as e:
                if probe:
                    try:
                        probe.terminate()
                    except Exception:
                        pass
                return False, str(e)

    def get_status(self):
        return self._status

    def get_input_device_index(self):
        return self._status.current_input_index

    def get_pyaudio(self):
        return self._pyaudio
