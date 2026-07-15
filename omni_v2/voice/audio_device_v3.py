"""
OMNI V3 - Audio Device Manager FIXED - RealTek Locked, No Virtual Mics
Simple, lists devices, prefers Realtek, mic boost guide, live RMS
"""
from pathlib import Path
from typing import Optional, List, Dict
import platform

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("AudioV3")

class AudioDeviceV3:
    """Clean device manager for V3"""
    
    def __init__(self):
        self.devices: List[Dict] = []
        self.best_device = None
        self._pyaudio = None
        self._scan()
    
    def _is_virtual(self, name: str) -> bool:
        lower = name.lower()
        virtuals = ["sound mapper", "primary sound capture", "stereo mix", "what u hear", "wave out", "microsoft sound mapper", "virtual"]
        return any(k in lower for k in virtuals)
    
    def _score(self, name: str, default_rate: float, is_default: bool, index: int) -> int:
        score = 0
        nl = name.lower()
        if "realtek" in nl: score += 200
        if "microphone" in nl and "stereo mix" not in nl: score += 100
        if "usb" in nl and "microphone" in nl: score += 80
        if "hd audio" in nl: score += 30
        if "array" in nl: score += 10
        if default_rate >= 48000: score += 20
        if default_rate >= 44100: score += 10
        if is_default: score += 5
        # Prefer lower index a bit
        score -= index * 0.1
        if self._is_virtual(name): score -= 500
        return score
    
    def _scan(self):
        try:
            import pyaudio
            self._pyaudio = pyaudio
            pa = pyaudio.PyAudio()

            try:
                default_idx = pa.get_default_input_device_info()['index'] if pa.get_default_input_device_info() else -1
            except Exception:
                default_idx = -1

            # AUDIO-BUG-01 fix: guard against invalid default_idx
            if default_idx < 0:
                default_idx = None
                logger.warning("No default input device reported by system")

            count = pa.get_device_count()
            logger.info(f"🎤 Scanning {count} audio devices...")

            mics = []
            for i in range(count):
                # AUDIO-BUG-01 fix: skip invalid indices
                if i < 0:
                    continue
                try:
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info['name']
                        is_default = (i == default_idx)
                        is_virtual = self._is_virtual(name)
                        score = self._score(name, info['defaultSampleRate'], is_default, i)

                        dev = {
                            "index": i,
                            "name": name,
                            "channels": info['maxInputChannels'],
                            "rate": info['defaultSampleRate'],
                            "is_default": is_default,
                            "is_virtual": is_virtual,
                            "score": score,
                        }
                        mics.append(dev)
                        tag = "🚫 VIRTUAL" if is_virtual else "✅ REAL"
                        logger.info(f"  [{i}] {tag} {name[:50]} | ch={info['maxInputChannels']} rate={info['defaultSampleRate']} default={is_default} score={score:.1f}")
                except Exception as e:
                    continue

            pa.terminate()

            # Sort by score desc
            mics.sort(key=lambda x: x['score'], reverse=True)
            self.devices = mics

            # Best non-virtual
            real_mics = [d for d in mics if not d['is_virtual']]
            if real_mics:
                self.best_device = real_mics[0]
                logger.info(f"🎯 BEST MIC: [{self.best_device['index']}] {self.best_device['name']} score={self.best_device['score']}")
            elif mics:
                self.best_device = mics[0]
                logger.warning(f"⚠️ Only virtual mics found, using [{self.best_device['index']}] {self.best_device['name']}")
            else:
                logger.error("❌ No mics found!")
                self.best_device = None

        except ImportError:
            logger.error("PyAudio not installed - pip install pyaudio")
            self.devices = []
            self.best_device = None
        except Exception as e:
            logger.error(f"Audio scan failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.devices = []
            self.best_device = None
    
    def get_best_index(self) -> Optional[int]:
        return self.best_device['index'] if self.best_device else None
    
    def get_best_name(self) -> str:
        return self.best_device['name'] if self.best_device else "No mic"
    
    def list_devices_for_ui(self) -> List[str]:
        """For QComboBox: ['[0] Realtek... (BEST)', '[1] USB...']"""
        items = []
        for d in self.devices:
            tag = ""
            if d == self.best_device:
                tag = " ⭐ BEST"
            elif d['is_virtual']:
                tag = " (virtual - avoid)"
            items.append(f"[{d['index']}] {d['name'][:40]}{tag}")
        return items
    
    def get_index_from_combo_text(self, combo_text: str) -> Optional[int]:
        """Parse [3] from combo"""
        try:
            import re
            m = re.search(r'\[(\d+)\]', combo_text)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return self.get_best_index()
    
    def test_mic_rms(self, device_index: int = None, duration: float = 1.0) -> dict:
        """Quick RMS test - returns max, rms for UI bar.
        AUDIO-BUG-02 fix: try/finally for stream cleanup"""
        pa = None
        stream = None
        try:
            import pyaudio
            import numpy as np

            idx = device_index if device_index is not None else self.get_best_index()
            if idx is None or idx < 0:
                return {"max": 0, "rms": 0, "error": "No device"}

            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=idx,
                frames_per_buffer=1024,
            )

            import time
            time.sleep(0.1)
            frames = []
            for _ in range(int(16000 / 1024 * duration)):
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)

            audio = b''.join(frames)
            arr = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32767.0
            max_v = float(np.abs(arr).max())
            rms = float(np.sqrt(np.mean(arr**2)))

            return {"max": max_v, "rms": rms, "device": idx}

        except Exception as e:
            return {"max": 0, "rms": 0, "error": str(e)}
        finally:
            # AUDIO-BUG-02 fix: always clean up
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

# Global for V3 UI
_device_v3_instance = None

def get_audio_v3():
    global _device_v3_instance
    if _device_v3_instance is None:
        _device_v3_instance = AudioDeviceV3()
    return _device_v3_instance
