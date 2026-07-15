# 💻 EXACT COMMANDS TO RUN - Copy Paste

## Windows PowerShell (Recommended)

```powershell
# --- SETUP (One time) ---
# Admin PowerShell first time only:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Download VC++ fix: https://aka.ms/vs/17/release/vc_redist.x64.exe

git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
python scripts/download_models.py --kokoro

# --- VERIFY (No mic needed) ---
python omni.py --test
python omni.py --cli "help"
python scripts/cuda_check.py

# --- RUN (Full GUI + Voice) ---
.\scripts\launch-chrome.ps1
# NEW terminal:
.venv\Scripts\activate
python omni.py
# Press V, say "open github"

# --- DEMO MODES (No mic) ---
python omni.py --demo "open github"
python omni.py --demo "what's on screen"
python omni.py --cli "open youtube"
python omni.py --cli "status"

# --- PUSH TO GITHUB (After verifying) ---
git add .
git commit -m "🏆 Winning Edition - Fixed 11 bugs, 10/10 tests, ready for 1st!"
git push origin main
```

## Linux / macOS (For Testing, limited features)

```bash
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_models.py --kokoro
python omni.py --test
python omni.py --cli "open github"
```

## What Each Script Does

- `scripts/setup.ps1` - Install deps on Windows
- `scripts/launch-chrome.ps1` - Opens Chrome with --remote-debugging-port=9222 (needed for full browser control like click/type)
- `scripts/cuda_check.py` - Diagnostics for GPU, Whisper, TTS, PyAudio
- `scripts/download_models.py --kokoro` - Downloads kokoro-v1.0.onnx (~80MB) + voices-v1.0.bin (~2MB) to ./models/
- `scripts/test_stt.py` --mic --vad --whisper - Test audio pipeline
- `scripts/test_tts.py --kokoro` - Test TTS

## Troubleshooting

**PyAudio fails on Python 3.12:**
```powershell
pip install pipwin
pipwin install pyaudio
# Or use Python 3.11
```

**Torch DLL error (c10.dll):**
- Install https://aka.ms/vs/17/release/vc_redist.x64.exe
- Reinstall torch: pip uninstall torch; pip install torch --index-url https://download.pytorch.org/whl/cu121

**No mic detected:**
- Check Windows Sound Settings -> Input
- Run: python scripts/cuda_check.py
- Try: python omni.py --cli "help" (no mic needed)

**Chrome CDP not connected:**
- That's OK! OS fallback still opens URLs
- For full click/type control: must launch via .\scripts\launch-chrome.ps1

**Orb not showing:**
- Check if PyQt5 installed
- Try CLI mode: python omni.py --cli "open github" (no GUI needed)
