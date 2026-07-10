"""
OMNI CUDA Diagnostic — Run this on your Windows PC
Paste the output into the chat if something fails.
"""
import sys, subprocess, os

print("=" * 60)
print("  OMNI CUDA + VAD DIAGNOSTIC")
print("=" * 60)
print(f"\nPython: {sys.version}")
print(f"Executable: {sys.executable}\n")

# 1. Visual C++ Redistributable check
print("--- Visual C++ Redistributable ---")
vc_paths = [
    r"C:\Windows\System32\vcruntime140.dll",
    r"C:\Windows\System32\vcruntime140_1.dll",
    r"C:\Windows\SysWOW64\vcruntime140.dll",
]
for p in vc_paths:
    if os.path.exists(p):
        print(f"  ✓ Found: {p}")
    else:
        print(f"  ✗ MISSING: {p}")

# 2. PyTorch + CUDA
print("\n--- PyTorch + CUDA ---")
try:
    import torch
    print(f"  PyTorch: {torch.__version__}")
    print(f"  CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA version: {torch.version.cuda}")
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        props = torch.cuda.get_device_properties(0)
        print(f"  GPU memory: {props.total_memory / 1e9:.1f} GB")
        # Test tensor on GPU
        try:
            t = torch.tensor([1.0]).cuda()
            print(f"  GPU tensor test: ✓ PASSED")
        except Exception as e:
            print(f"  GPU tensor test: ✗ FAILED - {e}")
    else:
        print("  CUDA not available — trying to init...")
        try:
            torch.cuda.init()
        except Exception as e:
            print(f"  CUDA init error: {e}")
except ImportError:
    print("  ✗ PyTorch NOT installed")
    print("  → Run: pip install torch --index-url https://download.pytorch.org/whl/cu121")
except Exception as e:
    print(f"  ✗ PyTorch error: {e}")

# 3. Test c10.dll directly
print("\n--- Torch DLL Loading ---")
try:
    import ctypes
    dll_paths = [
        r"C:\Users\M.Zarrar\AppData\Local\Programs\Python\Python312\Lib\site-packages\torch\lib\c10.dll",
    ]
    for dll in dll_paths:
        if os.path.exists(dll):
            try:
                ctypes.CDLL(dll)
                print(f"  ✓ c10.dll loads OK: {dll}")
            except Exception as e:
                print(f"  ✗ c10.dll FAILED to load: {e}")
        else:
            print(f"  ✗ c10.dll not found: {dll}")
except Exception as e:
    print(f"  DLL check error: {e}")

# 4. faster-whisper
print("\n--- faster-whisper ---")
try:
    import faster_whisper
    print(f"  faster-whisper: {faster_whisper.__version__}")
    # Try loading model on CUDA
    try:
        model = faster_whisper.WhisperModel("base.en", device="cuda", compute_type="float16")
        print(f"  ✓ Whisper CUDA model loaded: base.en")
        del model
    except Exception as e:
        print(f"  ✗ Whisper CUDA failed: {e}")
        # Try CPU fallback
        try:
            model = faster_whisper.WhisperModel("base.en", device="cpu", compute_type="int8")
            print(f"  ✓ Whisper CPU fallback works: base.en (int8)")
            del model
        except Exception as e2:
            print(f"  ✗ Whisper CPU also failed: {e2}")
except ImportError:
    print("  ✗ faster-whisper NOT installed")
except Exception as e:
    print(f"  Error: {e}")

# 5. TTS — Kokoro-ONNX (FIX: check the correct package name)
print("\n--- Kokoro TTS ---")
try:
    # FIX: The correct package is 'kokoro-onnx' which imports as 'kokoro_onnx'
    from kokoro_onnx import Kokoro
    print("  kokoro-onnx: ✓ installed (correct package)")
    try:
        # Check model files exist
        from omni.tts.kokoro_tts import KokoroTTS
        tts = KokoroTTS()
        model_ok, voices_ok = tts.model_files_present
        engine = tts.engine_type
        print(f"  Engine type: {engine}")
        print(f"  Model file:  {'✓ present' if model_ok else '✗ missing'}")
        print(f"  Voices file: {'✓ present' if voices_ok else '✗ missing'}")
        if engine == 'kokoro-onnx':
            print(f"  ✓ Kokoro-ONNX is ACTIVE — high quality TTS")
        elif engine == 'pyttsx3':
            print(f"  ⚠ Kokoro-ONNX inactive — Windows SAPI fallback active")
            print(f"  → Download model files: python scripts/download_models.py --kokoro")
        else:
            print(f"  ⚠ No TTS engine active")
    except ImportError:
        print("  ⚠ Could not import KokoroTTS (omni package not in path)")
        print("  → Run this script from the project root: python scripts/cuda_check.py")
except ImportError:
    print("  kokoro-onnx: ✗ NOT installed")
    print("  → Run: pip install kokoro-onnx")
    print("  → Then: python scripts/download_models.py --kokoro")
except Exception as e:
    print(f"  Error: {e}")

# 6. Silero VAD
print("\n--- Silero VAD ---")
try:
    import torch
    torch.set_num_threads(1)
    vad_model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        trust_repo=True
    )
    # Check if torchaudio is available (for best VAD accuracy)
    try:
        import torchaudio
        print(f"  Silero VAD: ✓ loaded via torch.hub")
        print(f"  Torchaudio: ✓ {torchaudio.__version__} — VAD accuracy is OPTIMAL")
    except ImportError:
        print(f"  Silero VAD: ✓ loaded via torch.hub")
        print(f"  Torchaudio: ✗ not installed — VAD runs on CPU (acceptable)")
        print(f"  → Install torchaudio for optimal VAD: pip install torchaudio --index-url https://download.pytorch.org/whl/cu121")
except Exception as e:
    print(f"  Silero VAD: ✗ failed — {e}")
    print("  → Energy-based fallback will be used")

# 7. PyAudio
print("\n--- PyAudio ---")
try:
    import pyaudio
    p = pyaudio.PyAudio()
    # FIX: get_version() doesn't exist in PyAudio 0.2.14 — just print 'OK'
    print(f"  PyAudio: ✓ (installed, version unknown but working)")
    # List input devices
    mic_count = 0
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            print(f"  MIC {i}: {dev['name']} ({dev['defaultSampleRate']} Hz)")
            mic_count += 1
    if mic_count == 0:
        print(f"  ⚠ No input devices found — check Windows Sound settings")
    print(f"  Total input devices: {mic_count}")
    p.terminate()
except ImportError:
    print("  ✗ PyAudio NOT installed")
    print("  → Run: pip install PyAudio")
except Exception as e:
    print(f"  PyAudio error: {e}")
    print(f"  (This is non-fatal — voice capture may still work)")

print("\n" + "=" * 60)
print("  RECOMMENDATIONS:")
print("=" * 60)
print("""
If CUDA is NOT available:
  1. Install Visual C++ Redistributable:
     https://aka.ms/vs/17/release/vc_redist.x64.exe
     
  2. Reinstall PyTorch with CUDA:
     pip uninstall torch
     pip install torch --index-url https://download.pytorch.org/whl/cu121

If c10.dll fails to load:
  → The VC++ Redistributable is the fix.
  → Your installed version may be outdated or broken.
  → Download and install from the link above (run as Admin).

If Whisper still fails on CUDA:
  → The app automatically falls back to CPU+int8.
  → CPU works fine — just slightly slower.
  → For GTX 1050 Ti: CPU+int8 is still very usable.

If Kokoro TTS is not active:
  → Run: python scripts/download_models.py --kokoro
  → This downloads ~82MB of TTS model files.

For BEST performance on your GTX 1050 Ti:
  → Install VC++ Redistributable (link above)
  → Then: pip install torchaudio --index-url https://download.pytorch.org/whl/cu121
  → Then: python scripts/download_models.py --kokoro
  → Then re-run: python omni.py
""")