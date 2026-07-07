# OMNI Setup Script - Install dependencies

Write-Host "OMNI Setup - Installing dependencies..." -ForegroundColor Cyan

# Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Create venv (optional)
$v = Read-Host "Create virtual environment? (y/n)"
if ($v -eq "y") {
    python -m venv .venv
    .\.venv\Scripts\activate
    Write-Host "Virtual environment created" -ForegroundColor Green
}

# Upgrade pip
python -m pip install --upgrade pip

# Install PyQt5
Write-Host "Installing PyQt5..." -ForegroundColor Yellow
pip install PyQt5==5.15.10

# Install voice
pip install faster-whisper==1.0.3
pip install silero-vad==0.3.0

# Install audio
pip install PyAudio
pip install numpy>=1.24.0

# Install TTS
pip install kokoro-tts

# Install automation
pip install pyautogui pyperclip
pip install websocket-client

# Install utilities
pip install keyboard psutil loguru

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run: .\scripts\launch-chrome.ps1"
Write-Host "  2. Run: python omni.py"
