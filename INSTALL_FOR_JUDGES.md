# OMNI V3 - Installation Guide for Judges (Portable - No D:/Omni Hardcode)

**This works wherever you clone it - C:\Users\Judge\Downloads\Omni, /home/judge/Omni, /tmp/Omni, etc.**

All paths are now relative to file location using `Path(__file__).resolve().parent.parent` - NOT hardcoded D:/Omni.

## Quick Start (2 minutes)

```bash
# 1. Clone (anywhere)
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni  # Or wherever you cloned, e.g., C:\Users\Judge\Downloads\Omni

# 2. Create venv (Python 3.10, 3.11, 3.12 all work)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
# source .venv/bin/activate

# 3. Install PyTorch for 1050 Ti (optional, brain works without it via regex fallback)
pip install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121

# 4. Install rest (NO PyAudio - it fails on Python 3.12, we use sounddevice only)
pip install -r requirements-final-no-pyaudio.txt
# If that file not found, use:
# pip install psutil sounddevice==0.4.6 faster-whisper pyttsx3 loguru mss pyautogui pillow requests

# 5. Test mic (should show RMS >0.01 even without PyAudio, uses sounddevice)
python -m omni_v2.voice.test_mic_fixed
# Expected: SD [x] Realtek... RMS 0.014 LOUD → ✅ Mic works, -9999 fixed via sounddevice

# 6. Run Web UI - Neomorphism Soft UI (REAL CSS double shadow, PyQt can't do this)
python -m omni_v2.web_server_fixed
# OR
python -m omni_v2.web_server

# Opens http://localhost:8765/ in isolated Chrome profile (data/chrome_profile/OMNI-Profile)
# Profile has NO email signed in - privacy by design - works for judges anywhere
# No 404 - root / now serves UI directly, fixed from D:\ bug
```

## What Changed for Portability

### OLD BUG (404 loop):
```python
THIS_FILE = Path(__file__).resolve()  # D:\Omni\omni_v2\web_server.py
OMNI_ROOT = THIS_FILE.parent.parent.parent  # D:\  <- BUG! parent.parent.parent = D:\
WEB_UI_FILE = OMNI_ROOT / "omni_v2" / "web_ui" / "index.html"  # D:\omni_v2\... -> 404!
# When judges clone to C:\Users\Judge\Downloads\Omni, it becomes C:\ -> 404
```

### NEW FIX (portable):
```python
THIS_FILE = Path(__file__).resolve()  # e.g., C:\Users\Judge\Downloads\Omni\omni_v2\web_server_fixed.py
OMNI_ROOT = THIS_FILE.parent.parent  # C:\Users\Judge\Downloads\Omni <- CORRECT! Works anywhere
WEB_UI_FILE = OMNI_ROOT / "omni_v2" / "web_ui" / "index.html"  # C:\Users\Judge\...\index.html -> 200 OK
```

Same fix for browser profile isolation:
```python
# OLD: Path.cwd() / "data" / "chrome_profile"  # Depends on where you run python from
# NEW: OMNI_ROOT = Path(__file__).resolve().parent.parent.parent
#      profile_dir = OMNI_ROOT / "data" / "chrome_profile"  # Always repo_root/data/..., portable
```

### Other Portable Fixes:
- **No PyAudio**: PyAudio 0.2.13 fails on Python 3.12 with `pkgutil.ImpImporter` error. We use `sounddevice==0.4.6` only, which handles resampling and fixes `[Errno -9999]`.
- **No hardcoded D:/Omni**: All `data/` paths are relative to repo root via `__file__` resolution.
- **Web UI at root /**: Old version served UI at `/omni_v2/web_ui/index.html` and required correct chdir. New version serves UI at `/` directly, no chdir needed, no 404.

## Test on Any Path

This was tested on:
- `D:\Omni` (your path) -> works, RMS 0.3918 LOUD
- `/home/user/omni_repo` (Linux sandbox) -> works, WEB_UI_FILE exists
- Should work on: `C:\Users\Judge\Desktop\Omni`, `/tmp/judge/Omni`, etc.

## Troubleshooting for Judges

**If mic test shows RMS 0.0000:**
- Windows: Win+R -> mmsys.cpl -> Recording -> Realtek Mic -> Properties -> Advanced -> Uncheck "Allow exclusive control" -> Levels 100 + Boost 20dB
- Then `python -m omni_v2.voice.test_mic_fixed` should show RMS >0.01

**If web UI shows 404:**
- Make sure you run `python -m omni_v2.web_server_fixed` from repo root (where `omni_v2/` folder is)
- Open http://localhost:8765/ directly, not /omni_v2/web_ui/index.html (though both work now)
- Check log: `[Path Fix] OMNI_ROOT: C:\...\Omni` should be your clone path, not D:\

**If torch fails:**
- Optional - brain works with regex fallback: `OMNI_NO_TORCH=1`
- Or install CPU version: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`

## Demo for Judges (No Mic Needed)

Web UI has 3 demo buttons that work offline without mic - perfect for judging:
- ♿ Accessibility: High contrast, screen reader
- 🔗 Chain + Self-Heal: Shows Planner->Executor->Monitor->Evaluator re-planning when Chrome not found -> Edge fallback
- 🏪 Shop Guardian: Weather + news -> risk -> PO PDF + Urdu WhatsApp

Click them, watch agent logs, see self-healing.

## Architecture: Why Neomorphism Wins UX

- PyQt neomorphism is fake - manual painting
- Web CSS neomorphism is real: `box-shadow: 12px 12px 24px rgba(0,0,0,0.55), -8px -8px 20px rgba(255,255,255,0.055)` - soft extruded plastic
- Three.js 1800 particles orb in center with state colors
- Profile isolation privacy-first - opens GitHub without email leak

Enjoy!

- Muhammad Zarrar | Rawalpindi | GTX 1050 Ti 4GB
