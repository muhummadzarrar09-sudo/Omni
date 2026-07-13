# 🧙 OMNI V2 - Setup Wizard Plan - People Just Open Wizard Install Libraries and Boom RUN IT

**Date:** 2026-07-12 | **Goal:** After DONE and DUSTED, make Setup Wizard so people just open wizard, install libraries, boom RUN IT

**From User:** "Cause after it is DONE and DUSTED we will have to make the Setup wizard as well so people just open the setup wizard install libraries and boom RUN IT"

---

## Why Setup Wizard?

**Current Setup (Manual, Painful for Non-Technical Users):**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # May fail with numpy<2.0 conflict, need minimal then full
python scripts/download_models.py --kokoro  # 82MB + 50MB Vosk + 4.9GB Llama + 867MB Moondream2
python scripts/test_stt.py --mic
python omni.py --test
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\launch-chrome.bat
python omni.py
# Plus: Boost mic volume 100% + Boost +30dB, allow mic privacy, etc.
```

**Too many steps! Non-technical users will give up. Need wizard: Open, click Next, Next, Run!**

---

## Setup Wizard Design - 6 Steps

### `omni_v2/ui/setup_wizard.py` - PyQt Wizard

**Step 1: Welcome**

```
+---------------------------------------------+
|  OMNI V2 - JARVIS KILLER Setup Wizard       |
|                                             |
|  Welcome to OMNI V2 Setup!                  |
|  This wizard will install OMNI V2           |
|  - Local, Private, GTX 1050 Ti Optimized    |
|  - 100+ Tools, Multi-Agent, Chain Commands  |
|  - Cinematic HUD + Voice Orb                |
|                                             |
|  Requirements:                              |
|  - Windows 10/11                            |
|  - Python 3.10+ (detected: 3.12.10 ✓)      |
|  - 8GB RAM, 4GB VRAM (1050 Ti)             |
|  - Microphone                               |
|                                             |
|  [Next]                                     |
+---------------------------------------------+
```

**Step 2: Python & System Check**

- Check Python version 3.10+ (show detected version, green check or red X)
- Check Windows version
- Check GPU (nvidia-smi for GTX 1050 Ti detection)
- Check RAM, disk space
- Check microphone via PyAudio device list
- If any fail, show fix instructions

**Step 3: Install Dependencies**

```
+---------------------------------------------+
|  Installing Dependencies                     |
|  Progress: [████████░░] 80%                 |
|                                             |
|  - Creating .venv... Done ✓                 |
|  - Upgrading pip... Done ✓                  |
|  - Installing loguru, numpy... Done ✓       |
|  - Installing PyQt5... Done ✓               |
|  - Installing faster-whisper... Done ✓      |
|  - Installing torch CPU... Done ✓           |
|  - Installing kokoro-onnx... Done ✓         |
|  - Installing pyautogui... Done ✓           |
|  - Current: Installing Pillow...            |
|                                             |
|  Log: data/logs/setup.log                   |
|  [Cancel]                                   |
+---------------------------------------------+
```

- Creates .venv
- Upgrades pip, wheel, setuptools
- Installs requirements.txt with fixed version (numpy>=1.26.0, no <2.0 conflict)
- If fails, tries requirements-minimal.txt first, then full
- Shows progress bar, logs to data/logs/setup.log
- Handles pip launcher bug after folder move (recreate venv)

**Step 4: Download Models**

```
+---------------------------------------------+
|  Downloading Models (One-time)              |
|  Progress: [████░░░░░░] 40%                 |
|                                             |
|  - Whisper base.en (75MB)... Done ✓         |
|  - Kokoro ONNX (80MB) + voices (2MB)...     |
|    Downloading kokoro-v1.0.onnx: 45%        |
|  - Vosk small en-us (50MB)... Pending       |
|  - Llama 3.1 8B Q4_K_M (4.9GB)... Optional  |
|    [ ] Download LLM (slow, optional)        |
|  - Moondream2 (867MB)... Optional           |
|    [ ] Download TurboVLM (optional)         |
|                                             |
|  Total: 207MB required, 5.8GB optional      |
|  [Back] [Next] [Skip Optional]              |
+---------------------------------------------+
```

- Downloads via scripts/download_models.py + hf_downloader.py
- Whisper base.en auto-downloaded by faster-whisper on first use (75MB)
- Kokoro: kokoro-v1.0.onnx (80MB) + voices-v1.0.bin (2MB) from GitHub releases
- Vosk: vosk-model-small-en-us-0.15 (50MB) from alphacephei.com
- Optional: Llama 3.1 8B Q4_K_M (4.9GB) + Moondream2 (867MB) for turbo speed
- Progress bars for each
- Checkboxes for optional large models

**Step 5: Test Mic + Speakers + Setup**

```
+---------------------------------------------+
|  Test Hardware                              |
|                                             |
|  Microphone:                                |
|  - Found 7 mics                             |
|  - Best: [1] Microphone (Realtek Audio) ✓  |
|  - [Test Mic Level] -> Live RMS bar         |
|    Speak LOUD, should see GREEN LOUD        |
|    Current: RMS 0.037 GREEN ✓               |
|  - [Boost Mic] -> Opens Windows Sound       |
|    Settings for 100% + Boost +30dB          |
|                                             |
|  Speakers:                                  |
|  - [Test TTS] -> Speaks "Hello from OMNI"   |
|  - Output: Realtek Speakers ✓               |
|                                             |
|  Chrome:                                    |
|  - [Launch Chrome with CDP] -> Opens        |
|    Chrome at http://localhost:9222 ✓        |
|                                             |
|  OMNI Test:                                 |
|  - [Run Tests] -> 10/10 V2 tests passed ✓  |
|                                             |
|  [Back] [Next]                              |
+---------------------------------------------+
```

- Lists mics via AudioDeviceManager, prefers Realtek (not Sound Mapper) - fixed
- Test Mic Level button -> runs test_mic_level.py live RMS
- Boost Mic button -> opens Windows Sound settings
- Test TTS: Speaks via Kokoro
- Launch Chrome with CDP: Runs launch-chrome.bat
- Run Tests: Runs omni.py --test, shows 10/10

**Step 6: Done - Launch OMNI**

```
+---------------------------------------------+
|  OMNI V2 Ready!                             |
|                                             |
|  Setup Complete!                            |
|  - 10/10 tests passed ✓                     |
|  - Mic Realtek selected ✓                   |
|  - TTS Kokoro working ✓                     |
|  - Chrome CDP launched ✓                    |
|                                             |
|  How to Run:                                |
|  - Press V to speak LOUD and CLOSE (2")     |
|  - Or say Hey Jarvis/Alexa (wake word)      |
|  - Or CLI: python omni.py --cli "open       |
|    github and search for iron man"          |
|                                             |
|  [ ] Start with Windows                     |
|  [ ] Create Desktop Shortcut                |
|                                             |
|  [Launch OMNI V2] [Finish]                  |
|                                             |
|  Docs: docs/00-QUICKSTART-1ST-PLACE.md      |
|  GitHub: github.com/muhummadzarrar09-sudo/  |
|          Omni                               |
+---------------------------------------------+
```

- Checkbox Start with Windows (registry HKCU\Software\Microsoft\Windows\CurrentVersion\Run)
- Checkbox Create Desktop Shortcut
- Button Launch OMNI V2 -> runs omni.py
- Button Finish -> closes wizard
- Shows docs and GitHub links

---

## Implementation - Files to Create

**`omni_v2/ui/setup_wizard.py` - Main Wizard:**

```python
from PyQt5.QtWidgets import QWizard, QWizardPage, QLabel, QProgressBar, QPushButton, QCheckBox

class SetupWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OMNI V2 Setup Wizard - JARVIS KILLER")
        self.setWizardStyle(QWizard.ModernStyle)

        self.addPage(WelcomePage())
        self.addPage(SystemCheckPage())
        self.addPage(InstallDepsPage())
        self.addPage(DownloadModelsPage())
        self.addPage(TestHardwarePage())
        self.addPage(FinishPage())

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to OMNI V2")
        self.setSubTitle("Local, Private, GTX 1050 Ti Optimized, 100+ Tools, Multi-Agent")

class SystemCheckPage(QWizardPage):
    def initializePage(self):
        # Check Python, Windows, GPU, RAM, mic
        pass

class InstallDepsPage(QWizardPage):
    def initializePage(self):
        # Create .venv, pip install -r requirements.txt with progress
        pass

class DownloadModelsPage(QWizardPage):
    def initializePage(self):
        # Download Whisper, Kokoro, Vosk, optional Llama + Moondream2
        pass

class TestHardwarePage(QWizardPage):
    def initializePage(self):
        # List mics, test mic level, test TTS, launch Chrome, run tests
        pass

class FinishPage(QWizardPage):
    def initializePage(self):
        # Show 10/10 tests, launch options
        pass
```

**`scripts/setup_wizard.py` - Entry Point:**

```python
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    sys.exit(app.exec_())
```

**`scripts/setup.bat` - One-Click Batch (No PowerShell Policy Issue):**

```batch
@echo off
echo OMNI V2 Setup Wizard - One-Click Installer
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Create venv
echo Creating .venv...
python -m venv .venv
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python.exe -m pip install --upgrade pip wheel setuptools

REM Install deps
echo Installing dependencies...
pip install -r requirements.txt

REM Download models
echo Downloading models...
python scripts/download_models.py --kokoro
python -m omni_v2.llm.hf_downloader --model vosk-model-small-en-us

REM Test
echo Testing...
python omni.py --test

echo.
echo Setup complete! Run:
echo   .venv\Scripts\activate
echo   python omni.py
echo Or double-click setup_wizard.py
pause
```

**For Hackathon Submission - NSIS Installer (Optional, One-Click .exe):**

- Use NSIS (Nullsoft Scriptable Install System) to create `OMNI_V2_Setup.exe`
- Installer does:
  - Checks Python, installs if not found (or bundles Python)
  - Creates .venv, pip install
  - Downloads models
  - Creates Start Menu shortcut, desktop shortcut
  - Registers auto-start
  - Launches OMNI V2

---

## How to Run Setup Wizard (After DONE and DUSTED)

```powershell
# In D:\Omni, after final push

# Method 1: GUI Wizard (new)
python scripts/setup_wizard.py
# Opens wizard with 6 steps, Next Next Finish, boom RUN IT!

# Method 2: Batch One-Click (no PowerShell policy)
.\scripts\setup.bat
# One-click, installs everything, no policy issue

# Method 3: PowerShell (existing)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

**For Non-Technical Users:**

```
1. Download OMNI V2 zip from GitHub Releases
2. Extract to D:\Omni (no spaces, for torch DLL fix)
3. Double-click setup_wizard.py or setup.bat
4. Click Next, Next, Next, Finish
5. Click Launch OMNI V2
6. Press V, say "open github" loud and close
7. Boom, RUN IT!
```

---

## Why Setup Wizard Matters for 1st Place

**Judges are non-technical? Need easy install:**

- V1 setup: Manual pip install, model downloads, mic config, Chrome launch, boost mic, etc. - 10 steps, painful
- V2 with wizard: Open wizard, click Next 6 times, boom RUN IT - 1 step, easy, professional

**For hackathon submission, easy install = more stars, more forks, more wow factor**

**Original PRD Phase 6 Platform & Packaging: One-click installer for Windows - this is it!**

---

- Zarrar + Agent | 2026-07-12 | Setup Wizard Plan - Open Wizard, Install Libraries, Boom RUN IT - After DONE and DUSTED
