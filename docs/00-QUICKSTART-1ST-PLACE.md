# 🏆 OMNI - 1st Place Quickstart (WINNING EDITION - FIXED FOR PYTHON 3.12)

**This is THE file to start with. Read this first!**

All `.md` docs are now organized in `docs/` folder (as requested). Here's exactly what to run to win.

> **⚠️ Python 3.12 Fix:** If you got `ResolutionImpossible` numpy error, see `docs/11-PYTHON312-FIX.md` - Fixed in new requirements.txt!

---

## ⚡ TL;DR - 3 Commands to Win (Fixed for Python 3.12)

```powershell
# 1. Setup (Windows PowerShell)
python -m venv .venv
.venv\Scripts\activate
python.exe -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt   # Now fixed: allows numpy 2.x

# If above fails (old version), use minimal fix:
pip install -r requirements-minimal.txt
python omni.py --test  # Should work even with minimal
pip install -r requirements.txt  # Then full

# 2. Download TTS models (~82MB, one-time) - you already have 310MB, so skip if verified
python scripts/download_models.py --verify
python scripts/download_models.py --kokoro  # Only if missing

# 3. Launch Chrome with debugging + Run OMNI
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\launch-chrome.ps1
# Or use batch (no policy issue): .\scripts\launch-chrome.bat
python omni.py
# Press V, say "open github" -> watch Orb turn green->purple->white!
```

---

## 📁 Workspace Organization (Fixed as Requested)

**Root:** Only `README.md` + code
- `README.md` - GitHub landing page (stays in root)
- `omni.py` - Main entry point
- `requirements.txt` - Dependencies

**docs/ - All documentation here:**
- `00-QUICKSTART-1ST-PLACE.md` ← **YOU ARE HERE** - Commands to run
- `01-OMNI-Concept.md` - What is OMNI
- `02-Technical-Stack.md` - Tech stack details
- `03-Architecture.md` - ReAct reasoning loop
- `04-Development-Roadmap.md` - Roadmap
- `05-Demo-Script.md` - Demo script for judges
- `06-Presentation-Slides.md` - Slide deck content
- `07-Enhancements-PRD.md` - Future enhancements
- `08-HACKATHON-WINNING-REPORT.md` - **11 critical bugs fixed** (detailed report)
- `09-WINNING-CHECKLIST.md` - Checklist for judges

**You can now download the whole folder and everything is clean in docs/**

---

## 🖥️ Full Setup - Windows (GTX 1050 Ti Optimized)

### Prerequisites
- Windows 10/11
- Python 3.10 or 3.11 (3.12 works but PyAudio can be tricky)
- NVIDIA GPU driver installed
- Microphone

### Step 0: One-Time Windows Config (Admin PowerShell)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Download VC++ Redistributable (fixes torch DLL errors):
https://aka.ms/vs/17/release/vc_redist.x64.exe

### Step 1: Clone & Venv
```powershell
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
python -m venv .venv
.venv\Scripts\activate
```

### Step 2: Install Dependencies
```powershell
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```
This installs:
- PyQt5 (UI orb + tray)
- faster-whisper (STT)
- sentence-transformers (semantic intent)
- PyAudio (mic)
- kokoro-onnx + pyttsx3 + sounddevice (TTS 3-tier)
- pyautogui, keyboard, psutil, loguru, websockets

### Step 3: Download Models (One-time, ~82MB)
```powershell
python scripts/download_models.py --kokoro
python scripts/download_models.py --verify
```

### Step 4: Verify Everything Works (No Mic Needed)
```powershell
python omni.py --test
# Expected: 10/10 tests pass

python omni.py --cli "open github"
# Expected: success=True, Opened: https://github.com

python scripts/cuda_check.py
# Shows CUDA, Whisper, TTS status
```

---

## 🚀 Running OMNI

### Option A: Normal Mode (With Voice, Needs Mic + GUI)
```powershell
# 1. Launch Chrome with CDP (for full browser control)
.\scripts\launch-chrome.ps1
# This opens Chrome with --remote-debugging-port=9222

# 2. In another terminal, run OMNI
python omni.py
# You should see:
# - System tray icon (O)
# - Floating Voice Orb (cyan pulsing)
# - Log: "OMNI ready. Press V to speak."

# 3. Press V key (toggle ON)
# Orb turns 🟢 bright green = Listening
# Speak: "open github"
# Orb turns 🟣 purple = Thinking
# Browser opens github.com
# Orb turns ⚪ white = Speaking
# TTS says "Opened github" in af_sarah voice
# Orb back to 🔵 cyan idle
```

### Option B: Demo Mode (No Mic Needed, For Judges)
```powershell
python omni.py --demo
# Default demo: "help"

python omni.py --demo "open github"
# Executes "open github" without microphone

python omni.py --demo "what's on screen"
# Accessibility demo
```

### Option C: CLI Mode (No GUI, For CI/Testing)
```powershell
python omni.py --cli "open youtube"
python omni.py --cli "search for python tutorial"
python omni.py --cli "help"
python omni.py --cli "status"
python omni.py --cli "turn on the lights"
```

---

## 🎤 Voice Commands to Demo (Winning Script)

Say these after pressing V:

**Browser (CDP + OS fallback):**
- "open github" / "open youtube" / "open google.com"
- "search for cats" / "search for python tutorial"
- "click login" / "type hello world" / "scroll down"

**Windows:**
- "open notepad" / "open calculator"
- "close window" / "minimize window" / "maximize window"

**VS Code (NEW - fixes missing plugin):**
- "open main.py"
- "run command echo hello"
- "save" / "create file test.py"

**System:**
- "screenshot" → saves to ~/.omni/screenshots/
- "copy this text" / "paste" / "volume up"

**Accessibility (ALPHA):**
- "what's on screen" / "describe screen"
- "show commands" / "find login button"
- "record this" → "save macro morning" → "run morning"

**OMNI Core:**
- "help" → full command list
- "status" → CPU/Memory/GPU status
- "settings" → opens settings dialog
- "do that again" → repeats last command

**Integrations (BETA - demo-friendly):**
- "send email to john" → opens Gmail compose
- "what's on my calendar" → shows demo schedule
- "turn on the lights" / "set temperature to 72"

---

## 🐛 What Was Fixed? (11 Critical Bugs)

See `docs/08-HACKATHON-WINNING-REPORT.md` for full details:

1. **omni.py sys.path** → ModuleNotFoundError crash (MAIN BREAKING ERROR)
2. **Duplicate ParsedCommand** → lint/parsing confusion
3. **PTT never subscribed** → pressing V did nothing
4. **Plugin routing broken** → 80% commands → "Plugin not found"
5. **Missing VSCode plugin** → vscode_* actions all failed
6. **SystemPlugin only screenshot** → copy/paste/volume failed
7. **WindowsPlugin only launch** → close/minimize failed
8. **Browser verification breaking loop** → OS fallback marked as fail
9. **IntentMapper returning vscode for everything** → semantic fallback bug
10. **EventBus create_task without loop** → RuntimeError
11. **Orb crash in headless** → whole app crash

All fixed + winning upgrades (trust system, cross-platform PTT, CLI mode, etc.)

---

## 📦 Download & Push to GitHub

### To Download:
- In Arena workspace, click Download or use git:
```bash
git clone https://github.com/muhummadzarrar09-sudo/Omni
# Replace with this fixed version's files
```

### To Push Fixed Version to Your Repo:
```powershell
cd Omni
git add .
git commit -m "🏆 Winning Edition: Fixed 11 critical bugs, added VSCode plugin, alias routing, CLI demo mode, 10/10 tests passing - Ready for 1st place!"
git push origin main
```

Now your GitHub repo has docs/ organized and winning code.

---

## 🏆 Why This Wins 1st Place

- **It Works:** Before 80% failed, now 10/10 CLI tests pass
- **Autonomous:** ReAct loop Plan→Act→Observe→Correct with verification
- **Semantic:** Understands meaning, not just keywords
- **Local-First:** 100% offline, no API costs, private
- **Accessible:** Voice Orb visual, screen description, macros
- **Hardware-Tuned:** GTX 1050 Ti float32→int8 fallback, 120s max recording
- **Demo-Ready:** --demo, --cli, --test modes for judges without hardware

---

**You were at breaking point. Now you're at winning point. Let's take 1st! 🚀**

*Questions? See docs/09-WINNING-CHECKLIST.md for judge checklist*
