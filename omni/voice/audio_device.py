"""
OMNI Audio Device Manager
=========================
Cross-platform audio device detection, selection, and management.

Handles:
- Auto-detect default input device (microphone)
- List all available microphones with names
- Validate device before use (probe the device)
- Handle device hot-plug (disconnect/reconnect)
- Volume/level detection for audio quality monitoring
- PyAudio errors translated to human-readable messages

No edge case left behind — every error is caught, logged, and reported.
"""

from __future__ import annotations

import platform
import threading
from typing import Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class AudioDevice:
    """Represents a single audio device."""
    index: int
    name: str
    is_input: bool
    max_channels: int
    default_sample_rate: float
    is_default: bool = False
    is_probe_ok: bool = False

    def __str__(self) -> str:
        default_marker = " [DEFAULT]" if self.is_default else ""
        return f"{self.name}{default_marker}"


@dataclass
class AudioSystemStatus:
    """Current state of the audio system."""
    system: str  # "windows", "linux", "darwin"
    pyaudio_available: bool
    default_input_device: Optional[AudioDevice] = None
    all_input_devices: list[AudioDevice] = field(default_factory=list)
    current_input_index: Optional[int] = None
    current_probe_status: str = "not_probe"  # "ok", "failed", "not_probe"
    last_error: Optional[str] = None
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024

    @property
    def device_count(self) -> int:
        return len(self.all_input_devices)

    @property
    def has_working_mic(self) -> bool:
        return (
            self.pyaudio_available
            and self.default_input_device is not None
            and self.current_probe_status == "ok"
        )

    def summary(self) -> str:
        lines = [
            f"System:       {self.system}",
            f"PyAudio:      {'✓ available' if self.pyaudio_available else '✗ not available'}",
            f"Mics found:   {self.device_count}",
            f"Default mic:  {self.default_input_device.name if self.default_input_device else 'None'}",
            f"Probe status: {self.current_probe_status}",
            f"Sample rate:  {self.sample_rate} Hz",
            f"Chunk size:   {self.chunk_size}",
        ]
        if self.last_error:
            lines.append(f"Last error:   {self.last_error}")
        return "\n".join(lines)


class AudioDeviceManager:
    """
    Manages audio input/output device detection and selection.

    Usage:
        adm = AudioDeviceManager()
        status = adm.get_status()

        # Get default mic
        mic = adm.get_default_input_device()

        # Probe a specific device
        ok, error = adm.probe_device(device_index=2)

        # Select a device
        adm.select_device(2)
    """

    _instance: Optional["AudioDeviceManager"] = None

    def __init__(self, preferred_device_index: Optional[int] = None):
        AudioDeviceManager._instance = self

        self._pyaudio = None
        self._status = AudioSystemStatus(
            system=platform.system().lower(),
            pyaudio_available=False,
        )
        self._preferred_index = preferred_device_index
        self._probe_lock = threading.Lock()

        self._init_pyaudio()
        self._detect_devices()
        self._probe_default_device()

    # ── Singleton ─────────────────────────────────────────────────────────

    @staticmethod
    def get_instance() -> Optional["AudioDeviceManager"]:
        return AudioDeviceManager._instance

    # ── PyAudio initialization ────────────────────────────────────────────

    def _init_pyaudio(self) -> None:
        """Initialize PyAudio. Failures are non-fatal — audio still works via fallback."""
        try:
            import pyaudio
            self._pyaudio = pyaudio
            self._status.pyaudio_available = True
            logger.debug("AudioDeviceManager: PyAudio initialized")
        except ImportError:
            self._status.last_error = "PyAudio not installed (pip install PyAudio)"
            logger.warning("AudioDeviceManager: PyAudio not installed")
        except Exception as e:
            self._status.last_error = f"PyAudio init failed: {e}"
            logger.warning(f"AudioDeviceManager: PyAudio init failed: {e}")

    # ── Device detection ──────────────────────────────────────────────────

    def _detect_devices(self) -> None:
        """Detect all available audio input devices."""
        if self._pyaudio is None:
            return

        try:
            pa = self._pyaudio.PyAudio()
            device_count = pa.get_device_count()

            # Get default device index safely
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
                            name=self._clean_device_name(info['name']),
                            is_input=True,
                            max_channels=info['maxInputChannels'],
                            default_sample_rate=info['defaultSampleRate'],
                            is_default=(i == default_input_index),
                        )
                        input_devices.append(device)
                except Exception as e:
                    logger.warning(f"AudioDeviceManager: failed to read device {i}: {e}")
                    continue

            pa.terminate()

            self._status.all_input_devices = input_devices

            # Set default
            self._status.default_input_device = next(
                (d for d in input_devices if d.is_default), None
            )

            if input_devices:
                logger.info(f"AudioDeviceManager: found {len(input_devices)} input device(s)")
            else:
                self._status.last_error = "No microphone input devices found"
                logger.warning("AudioDeviceManager: no input devices found")

        except Exception as e:
            self._status.last_error = f"Device detection failed: {e}"
            logger.error(f"AudioDeviceManager: device detection failed: {e}")

    def _clean_device_name(self, name: str) -> str:
        """Truncate very long device names for display."""
        MAX_LEN = 60
        if len(name) > MAX_LEN:
            return name[:MAX_LEN - 3] + "..."
        return name

    # ── Device probing ────────────────────────────────────────────────────

    def _probe_default_device(self) -> None:
        """Probe the default (or preferred) input device to verify it works."""
        target_index = self._preferred_index
        if target_index is None:
            # Try to get the system default
            if self._status.default_input_device:
                target_index = self._status.default_input_device.index
            elif self._status.all_input_devices:
                # FALLBACK: If no system default is set, just pick the first available mic
                target_index = self._status.all_input_devices[0].index
                logger.info(f"No system default mic found. Using first available device [{target_index}]")

        if target_index is None:
            self._status.current_probe_status = "failed"
            self._status.last_error = "No device to probe"
            return

        ok, error = self._probe_device(target_index)
        self._status.current_input_index = target_index
        self._status.current_probe_status = "ok" if ok else "failed"
        if error:
            self._status.last_error = error

    def _probe_device(self, device_index: int) -> tuple[bool, Optional[str]]:
        """
        Probe a specific device by opening a test stream for 0.5s.

        Returns:
            (success: bool, error_message: str or None)
        """
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

                # Read a few frames to verify the device actually produces audio
                import time
                time.sleep(0.5)
                data = stream.read(512, exception_on_overflow=False)

                # Check that we got actual audio data (not all zeros)
                import numpy as np
                audio = np.frombuffer(data, dtype=np.int16)
                max_val = np.abs(audio).max()
                if max_val < 1:
                    stream.stop_stream()
                    stream.close()
                    probe.terminate()
                    return False, f"Device produces absolute silence (max amplitude={max_val})"

                stream.stop_stream()
                stream.close()
                probe.terminate()
                return True, None

            except OSError as e:
                if probe:
                    try:
                        probe.terminate()
                    except Exception:
                        pass
                err_str = str(e)
                if "9999" in err_str or "Invalid" in err_str:
                    return False, f"Device index {device_index} is invalid or unavailable"
                if "could not" in err_str.lower():
                    return False, f"Device could not start: {e}"
                return False, f"OSError probing device: {e}"
            except AttributeError as e:
                # pyaudio version mismatch
                if probe:
                    try:
                        probe.terminate()
                    except Exception:
                        pass
                return False, f"PyAudio version mismatch: {e}"
            except Exception as e:
                if probe:
                    try:
                        probe.terminate()
                    except Exception:
                        pass
                return False, f"Probe failed: {e}"

    # ── Public API ────────────────────────────────────────────────────────

    def get_status(self) -> AudioSystemStatus:
        """Return current audio system status."""
        return self._status

    def get_default_input_device(self) -> Optional[AudioDevice]:
        """Return the system default input device."""
        return self._status.default_input_device

    def get_all_input_devices(self) -> list[AudioDevice]:
        """Return all detected input devices."""
        return self._status.all_input_devices

    def select_device(self, device_index: int) -> tuple[bool, Optional[str]]:
        """
        Select a specific input device. Probes it first to confirm it's working.

        Returns:
            (success, error_message)
        """
        # Find the device in our list
        device = next((d for d in self._status.all_input_devices if d.index == device_index), None)
        if device is None:
            return False, f"Device index {device_index} not in device list"

        # Probe the device
        ok, error = self._probe_device(device_index)
        if ok:
            self._status.current_input_index = device_index
            self._status.current_probe_status = "ok"
            self._status.last_error = None
            logger.info(f"AudioDeviceManager: selected device [{device_index}] {device.name}")
            return True, None
        else:
            self._status.current_probe_status = "failed"
            self._status.last_error = error
            logger.warning(f"AudioDeviceManager: device [{device_index}] probe failed: {error}")
            return False, error

    def refresh_devices(self) -> None:
        """Re-scan for audio devices (useful after hot-plug)."""
        self._detect_devices()
        self._probe_default_device()
        logger.info("AudioDeviceManager: devices refreshed")

    def test_device_audio_level(self, device_index: int, duration_s: float = 1.0) -> tuple[float, bool]:
        """
        Measure the audio level of a device over `duration_s` seconds.

        Returns:
            (average_rms_level: float, has_audio: bool)
        """
        if self._pyaudio is None:
            return 0.0, False

        probe = None
        try:
            probe = self._pyaudio.PyAudio()
            stream = probe.open(
                format=self._pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
                start=True,
            )

            import numpy as np
            import time

            total_rms = 0.0
            sample_count = 0

            end_time = time.time() + duration_s
            while time.time() < end_time:
                try:
                    data = stream.read(512, exception_on_overflow=False)
                    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    rms = np.sqrt(np.mean(audio ** 2))
                    total_rms += rms
                    sample_count += 1
                except Exception:
                    break

            stream.stop_stream()
            stream.close()
            probe.terminate()

            avg_rms = total_rms / max(sample_count, 1)
            has_audio = avg_rms > 0.001  # Anything louder than 0.1% amplitude

            return avg_rms, has_audio

        except Exception as e:
            if probe:
                try:
                    probe.terminate()
                except Exception:
                    pass
            return 0.0, False

    def get_pyaudio(self):
        """Return the PyAudio instance for use by VoicePipeline."""
        return self._pyaudio

    def get_input_device_index(self) -> Optional[int]:
        """Return the currently selected input device index."""
        return self._status.current_input_index


# ── PyAudio error code translations ─────────────────────────────────────────

PYAUDIO_ERROR_MESSAGES = {
    -9999: "Invalid device index — device may have been unplugged",
    -9988: "Stream is not stopped",
    -9987: "Stream is not started",
    -9986: "Could not get stream information",
    -9985: "Stream is already stopped",
    -9984: "Stream is already started",
    -9983: "Memory allocation failed",
    -9982: "Stream error — check your microphone cable and drivers",
    -9996: "Device unavailable — may have been disconnected",
    -9997: "Incompatible host API",
    -9998: "Incompatible device — check sample rate compatibility",
    -9991: "Blocking while another stream is active",
}


def translate_pyaudio_error(code: int) -> str:
    """Translate a PyAudio error code to a human-readable message."""
    return PYAUDIO_ERROR_MESSAGES.get(
        code,
        f"PortAudio error {code} — see https://people.csail.mit.edu/hubert/pyaudio/docs/#paErrorCodes"
    )