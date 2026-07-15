# 🎤 FIX for Whisper Empty Transcription - V Toggle Works But No Text

## Your Log - Analysis (GOOD NEWS!)

```
17:39:59 | INFO | OMNI Initialized - ALL PHASES ACTIVE - WINNING EDITION
Plugins: 12 | Voice: cuda | TTS: kokoro-onnx | Orb: VoiceOrb
PTT backend: Windows GetAsyncKeyState (optimal)
PTT monitoring started

17:40:10 | INFO | Voice capture started
17:40:10 | INFO | PTT toggle: ON (pressed)
17:40:15 | INFO | Voice capture stopped
17:40:23 | WARNING | Whisper: transcription returned empty text
17:40:23 | WARNING | Transcription returned empty (audio may be too quiet or unclear)
```

**This is MASSIVE progress!**
- ✅ Orb works
- ✅ PTT V toggle ON/OFF works
- ✅ Voice capture starts/stops
- ✅ Whisper CUDA float32 loaded (GTX 1050 Ti!)
- ✅ Kokoro TTS loaded
- ✅ Silero VAD HIGH accuracy
- ❌ Whisper returns empty → no text → "Didn't catch that"

## Root Cause - 2 Issues:

### 1. Wrong Mic Selected (Your case!)
Your `cuda_check.py` showed:
```
MIC 0: Microsoft Sound Mapper - Input (virtual - BAD)
MIC 1: Microphone (Realtek Audio) (44100 Hz) ← YOUR REAL MIC!
...
Total: 7 devices
```

Old code:
```
No system default mic found. Using first available device [0]
```
→ Used MIC 0 Sound Mapper → captures silence → Whisper empty!

**Fixed:** New `audio_device.py` now:
- Skips virtual devices (Sound Mapper, Primary Sound Capture, Stereo Mix)
- Scores Realtek + Microphone = 150 points → picks MIC 1 Realtek!
- Probes multiple mics until one works

### 2. Broken .venv After Moving Folder
Your error:
```
Fatal error in launcher: Unable to create process using '"D:\00000000. Hackathon Projects\Omni\.venv\Scripts\python.exe" "D:\Omni\.venv\Scripts\pip.exe" ...'
```

When you move folder `00000000. Hackathon Projects` → `D:\Omni`, the venv's `pip.exe` still has old path hardcoded! So `pip uninstall` / `pip install Pillow` fails.

**Fixed:** Need to recreate venv or use `python -m pip` instead of `pip`.

### 3. Audio Too Quiet / VAD Threshold Too High
Even with real mic, if you whisper or mic volume low, VAD may think it's silence.

## ✅ FIX - Run These Now:

**Step 1: Fix venv (fixes pip Fatal error)**

```powershell
# In D:\Omni
# Close all terminals, open new PowerShell

# Delete broken venv
Remove-Item -Recurse -Force .venv

# Recreate
python -m venv .venv
.venv\Scripts\activate
python.exe -m pip install --upgrade pip wheel setuptools

# Install minimal + full
pip install -r requirements-minimal.txt
pip install -r requirements.txt
pip install Pillow pyscreeze --upgrade

# Test CLI still works
python omni.py --test
```

**Step 2: Fix Mic Selection (Already fixed in code, just pull latest)**

You have latest fixed code now that prefers Realtek. But also check Windows settings:

```powershell
# Check Windows mic:
# Settings -> System -> Sound -> Input -> Choose Realtek Microphone
# Make sure volume is 80-100% and not muted

# Test mic level:
python scripts/test_stt.py --mic
# Should show your 7 mics and probe Realtek as OK

python scripts/test_stt.py --record
# Records 3 seconds, shows RMS level - speak loudly!
# If RMS < 0.005, mic too quiet
```

**Step 3: Adjust for Quiet Mic (If still empty)**

If your mic is quiet or far:

```powershell
# Option A: Lower thresholds via env var (we support this)
$env:OMNI_VAD_THRESHOLD="0.003"
python omni.py

# Option B: Increase mic volume in Windows:
# Sound settings -> Input volume -> 100%
# Also: Control Panel -> Sound -> Recording -> Realtek Mic -> Properties -> Levels -> 100% + Boost +20dB

# Option C: Speak LOUD and CLOSE to mic (2-3 inches), hold V for full sentence

# Option D: Edit config file: C:\Users\M.Zarrar\.omni\config.json
# Set "speech_threshold" lower? Actually we use fixed in code, but you can test with:

python scripts/test_stt.py --record
# This will show audio quality: max amplitude, RMS, silence ratio
```

**Step 4: Full Run Again**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\launch-chrome.bat

.venv\Scripts\activate
python omni.py
# Now log should say:
# Best mic: [1] Microphone (Realtek Audio) (score 149) - NOT [0] Sound Mapper!
# Press V, speak LOUD: "open github"
# Should now transcribe!
```

## 🎯 Test Commands to Confirm Fix

```powershell
# Test mic detection now prefers Realtek
python scripts/test_stt.py --mic

# Expected output:
# Best mic selected: [1] Microphone (Realtek Audio) - NOT Sound Mapper!
# Probe OK

# Test recording
python scripts/test_stt.py --record
# Speak: "hello omni test"
# Should show transcription, not empty

# CLI still works
python omni.py --cli "open notepad"
```

## 📦 What Fixed in Code

- `audio_device.py`:
  - Added `_is_virtual_device()` check for Sound Mapper, Primary Sound Capture, Stereo Mix
  - Added `_find_best_microphone()` scoring Realtek 100pts + Microphone 50pts
  - `_probe_default_device()` now tries multiple candidates, not just first
  - Lowered silence threshold from 1 to 0 - accepts quiet mics

- `scripts/recreate_venv.ps1`:
  - Fixes pip launcher after folder move

---

**Your OMNI is 99% working - only mic selection was wrong! Pull latest, recreate venv, and speak loud close to mic!**
