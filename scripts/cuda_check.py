"""
OMNI CUDA Diagnostic — Run this on your Windows PC
Paste the output into the chat if something fails.
"""
import sys, subprocess

print("=" * 60)
print("  OMNI CUDA + VAD DIAGNOSTIC")
print("=" * 60)
print(f"\nPython: {sys.version}")
print(f"Executable: {sys.executable}\n")

# 1. Visual C++ Redistributable check
print("--- Visual C++ Redistributable ---")
import os
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

# 5. TTS
print("\n--- Kokoro TTS ---")
try:
    from kokoro import Kokoro
    print("  kokoro package: ✓ installed")
    try:
        k = Kokoro(device="cpu")
        print("  Kokoro CPU: ✓ loaded")
        del k
    except Exception as e:
        print(f"  Kokoro CPU error: {e}")
    try:
        k = Kokoro(device="cuda")
        print("  Kokoro CUDA: ✓ loaded")
        del k
    except Exception as e:
        print(f"  Kokoro CUDA error: {e}")
except ImportError:
    print("  kokoro NOT installed")
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
    print("  Silero VAD: ✓ loaded via torch.hub")
except Exception as e:
    print(f"  Silero VAD: ✗ failed — {e}")
    print("  → Energy-based fallback will be used")

# 7. PyAudio
print("\n--- PyAudio ---")
try:
    import pyaudio
    p = pyaudio.PyAudio()
    print(f"  PyAudio: ✓ (version {p.get_version()})")
    # List input devices
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            print(f"  MIC {i}: {dev['name']} ({dev['defaultSampleRate']} Hz)")
    p.terminate()
except ImportError:
    print("  ✗ PyAudio NOT installed")
except Exception as e:
    print(f"  PyAudio error: {e}")

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

For BEST performance on your GTX 1050 Ti:
  → Install VC++ Redistributable (link above)
  → Then: pip install torch --index-url https://download.pytorch.org/whl/cu121
  → Then re-run: python omni.py
""")