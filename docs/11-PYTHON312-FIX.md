# 🐛 FIX for Python 3.12 - Requirements Install Failed

**Your error:**
```
ERROR: Cannot install -r requirements.txt (line 16), -r requirements.txt (line 23) and numpy<2.0.0...
    onnxruntime 1.17.0 depends on numpy>=1.26.3
    kokoro-onnx 0.5.0 depends on numpy>=2.0.2
```

**Root cause:** Old `requirements.txt` pinned `numpy<2.0.0` but `kokoro-onnx>=0.4.0` needs `numpy>=2.0.2`. Conflict!

**Fixed in new `requirements.txt`:** Now allows `numpy>=1.26.0` (no upper bound) and `onnxruntime>=1.18.0` which supports numpy 2.x.

---

## ✅ QUICK FIX - Run These Now (In Your Broken .venv)

You are in `D:\00000000. Hackathon Projects\Omni` with `.venv` activated but empty because install failed.

**Option 1: Clean Re-install (Recommended - 2 minutes)**

```powershell
# Delete broken venv
deactivate
Remove-Item -Recurse -Force .venv

# Recreate
python -m venv .venv
.venv\Scripts\activate

# Upgrade pip
python.exe -m pip install --upgrade pip wheel setuptools

# Install MINIMAL first (makes CLI work immediately)
pip install -r requirements-minimal.txt

# Test CLI now works!
python omni.py --test
python omni.py --cli "open github"

# Now install full (fixed) requirements
pip install -r requirements.txt

# Verify
python omni.py --test
python scripts/cuda_check.py
```

**Option 2: Use Fix Script (Step-by-step, avoids big resolver)**

```powershell
# In your Omni folder, .venv activated
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\fix-install.ps1
```

This installs in steps so pip resolver doesn't choke.

**Option 3: Manual Step-by-Step (If pip still fails)**

```powershell
pip install loguru numpy psutil packaging --upgrade
python omni.py --test   # Should now work!

pip install PyQt5 --upgrade
pip install "onnxruntime>=1.18.0" --upgrade
pip install "kokoro-onnx>=0.4.0" pyttsx3 sounddevice --upgrade
pip install faster-whisper sentence-transformers --upgrade
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install pyautogui pyperclip keyboard websocket-client websockets --upgrade
pip install PyAudio --upgrade
# If PyAudio fails:
pip install pipwin
pipwin install pyaudio

python omni.py --test
```

---

## 🔧 Execution Policy Fix (launch-chrome.ps1 error)

Your error:
```
File ...\launch-chrome.ps1 is not digitally signed.
```

**Fix:**

```powershell
# Run this BEFORE running .ps1 scripts (each new terminal)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Then
.\scripts\launch-chrome.ps1
```

**Alternative - Use .bat (no policy needed):**
```powershell
.\scripts\launch-chrome.bat
```

Or manually launch Chrome:
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --force-renderer-accessibility
```

---

## 📁 Path With Spaces Issue

Your path: `D:\00000000. Hackathon Projects\Omni` has spaces!

**Good news:** Our fixed scripts handle spaces now.

**But if you still have issues, rename folder to no spaces:**
```powershell
# Recommended: D:\Omni or D:\Hackathon\Omni
```

---

## 🎯 After Fix - What to Run

```powershell
# .venv activated

# 1. Models already downloaded (you have 310MB kokoro file - good!)
python scripts/download_models.py --verify

# 2. Test CLI (no mic, no GUI)
python omni.py --test
# Expected: 10/10 pass (or 7+ on Linux without pyautogui)

# 3. Test single command
python omni.py --cli "open github"
# Expected: success=True, Opened: https://github.com

# 4. Launch Chrome + Full GUI
# Terminal 1:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\launch-chrome.ps1

# Terminal 2:
.venv\Scripts\activate
python omni.py
# Press V, say "open youtube"
```

---

## 📦 Updated Files in This Fix

- `requirements.txt` - Fixed numpy<2.0 conflict → now numpy>=1.26.0 + onnxruntime>=1.18.0
- `requirements-minimal.txt` - NEW, minimal deps for CLI to work
- `scripts/fix-install.ps1` - NEW, step-by-step installer
- `scripts/launch-chrome.bat` - NEW, batch version no policy issue
- `docs/11-PYTHON312-FIX.md` - This file

---

## 💡 Why This Happened

- Python 3.12 + kokoro-onnx 0.5.0 + numpy<2.0 = impossible to resolve
- Previous requirements pinned numpy for old PyAudio compatibility
- New requirements allow numpy 2.x which all modern packages support

Your models (310MB) are already downloaded, so after fixing pip install, you're done!

---

**Run Option 1 commands above and paste the result here if still failing!**
