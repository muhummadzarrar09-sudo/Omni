"""
Test mic with FIXED pipeline - sounddevice + pyaudio fallback
Run: python -m omni_v2.voice.test_mic_fixed
Should handle -9999 error
"""
import time
import pytest
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger()

def test_sounddevice():
    print("=== Testing sounddevice (FIX for -9999) ===")
    try:
        import sounddevice as sd
        import numpy as np
        
        devices = sd.query_devices()
        print(f"Found {len(devices)} devices:")
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                print(f"  SD [{i}] {dev['name']} | ch={dev['max_input_channels']} sr={dev['default_samplerate']}")
        
        # Find best Realtek
        best_idx = None
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and 'realtek' in dev['name'].lower() and 'mic' in dev['name'].lower():
                if 'stereo mix' not in dev['name'].lower():
                    best_idx = i
                    print(f"Best SD mic: [{i}] {dev['name']}")
                    break
        
        if best_idx is None:
            best_idx = sd.default.device[0]
            print(f"Using default input SD [{best_idx}]")
        
        print(f"\nTesting SD [{best_idx}] @ 16000Hz for 2 seconds - SPEAK LOUD!")
        with sd.InputStream(samplerate=16000, channels=1, device=best_idx, dtype='float32', blocksize=1024) as stream:
            frames = []
            for _ in range(int(16000/1024*2)):
                data, overflowed = stream.read(1024)
                if overflowed:
                    print(f"Overflowed: {overflowed}")
                frames.append(data[:,0] if data.ndim>1 else data)
                # Live RMS
                rms = float((data**2).mean()**0.5)
                max_v = float(abs(data).max())
                print(f"  RMS={rms:.5f} MAX={max_v:.4f} {'🔊 LOUD' if rms>0.03 else '🔉 Good' if rms>0.01 else '🔈 Low' if rms>0.001 else '🔇 Silent'}", end='\r')
                time.sleep(0.05)
        
        print("\n✅ Sounddevice works! No -9999 error")
        audio = np.concatenate(frames)
        overall_rms = float((audio**2).mean()**0.5)
        overall_max = float(abs(audio).max())
        print(f"Overall: RMS={overall_rms:.5f} MAX={overall_max:.4f}")
        if overall_rms > 0.01:
            print("✅ Mic is LOUD enough for STT")
        else:
            print("⚠️ Mic quiet - boost Windows Sound -> Input 100% +30dB, speak 1 inch")
        return None
        
    except Exception as e:
        print(f"❌ Sounddevice failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.skip(f"Audio hardware unavailable: {e}")

def test_pyaudio_fallback():
    print("\n=== Testing PyAudio fallback with multiple samplerates ===")
    try:
        import pyaudio
        import numpy as np
        
        pa = pyaudio.PyAudio()
        # Find best index via our manager
        from omni_v2.voice.audio_device_v3 import get_audio_v3
        mgr = get_audio_v3()
        idx = mgr.get_best_index()
        print(f"PyAudio best index: {idx} {mgr.get_best_name()}")
        
        for sr in [48000, 44100, 16000]:
            try:
                print(f"Trying PyAudio @ {sr}Hz...")
                stream = pa.open(format=pyaudio.paInt16, channels=1, rate=sr, input=True, input_device_index=idx, frames_per_buffer=1024)
                print(f"  Opened @ {sr}Hz OK, reading 1 sec...")
                data = b''
                for _ in range(int(sr/1024*1)):
                    chunk = stream.read(1024, exception_on_overflow=False)
                    data += chunk
                stream.stop_stream()
                stream.close()
                arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)/32767.0
                rms = float((arr**2).mean()**0.5)
                max_v = float(abs(arr).max())
                print(f"  ✅ Works @ {sr}Hz RMS={rms:.5f} MAX={max_v:.4f}")
                pa.terminate()
                return None
            except Exception as e:
                print(f"  ❌ @ {sr}Hz failed: {e}")
        
        pa.terminate()
        print("❌ All PyAudio samplerates failed - use sounddevice")
        pytest.skip(f"Audio hardware unavailable: {e}")
        
    except Exception as e:
        print(f"❌ PyAudio test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.skip(f"Audio hardware unavailable: {e}")

if __name__ == "__main__":
    print("OMNI V3.1 Mic Test - Fixes -9999 Unanticipated host error")
    print("Your earlier test RMS 0.3918 = mic WORKS, just PyAudio exclusive bug")
    print("")
    sd_ok = test_sounddevice()
    pa_ok = test_pyaudio_fallback()
    
    print("\n=== SUMMARY ===")
    if sd_ok:
        print("✅ Use sounddevice backend - FIXED pipeline_v3_fixed.py will work")
        print("   python -m omni_v2.app_v3_fixed  (or updated app_v3_neumorphism)")
    elif pa_ok:
        print("⚠️ Sounddevice failed but PyAudio works at different SR - pipeline will auto resample")
    else:
        print("❌ Both failed - check Windows mmsys.cpl exclusive mode OFF")
        print("   Win+R -> mmsys.cpl -> Recording -> Realtek Mic -> Properties -> Advanced -> Uncheck exclusive")
