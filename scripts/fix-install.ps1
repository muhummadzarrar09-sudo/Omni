# OMNI - Fix Install Script for Python 3.12 (Winning Edition)
# This script fixes the numpy<2.0 vs kokoro-onnx>=0.4.0 conflict

Write-Host "OMNI Fix Install - Python 3.12 Compatibility" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Ensure we're in venv
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating .venv..." -ForegroundColor Yellow
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        . .\.venv\Scripts\Activate.ps1
    }
}

Write-Host ""
Write-Host "Step 1: Installing core deps (loguru, numpy, psutil) - This makes CLI work" -ForegroundColor Cyan
pip install loguru numpy psutil packaging --upgrade

Write-Host ""
Write-Host "Step 2: Testing CLI mode (should work now)" -ForegroundColor Cyan
python omni.py --cli "help"

Write-Host ""
Write-Host "Step 3: Installing PyQt5 (UI)" -ForegroundColor Cyan
pip install PyQt5 PyQt5-sip PyQt5-Qt5 --upgrade

Write-Host ""
Write-Host "Step 4: Installing ONNX runtime (numpy 2.x compatible)" -ForegroundColor Cyan
pip install "onnxruntime>=1.18.0" --upgrade

Write-Host ""
Write-Host "Step 5: Installing Kokoro TTS (needs numpy 2.x)" -ForegroundColor Cyan
pip install "kokoro-onnx>=0.4.0" --upgrade
pip install pyttsx3 sounddevice --upgrade

Write-Host ""
Write-Host "Step 6: Installing Whisper + torch (CPU version, fast)" -ForegroundColor Cyan
pip install faster-whisper sentence-transformers --upgrade
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 --upgrade
# If CUDA version fails, fallback to CPU:
# pip install torch torchaudio --upgrade

Write-Host ""
Write-Host "Step 7: Installing automation libs" -ForegroundColor Cyan
pip install pyautogui pyperclip keyboard websocket-client websockets colorlog coloredlogs --upgrade
pip install comtypes --upgrade
# PyAudio - may need pipwin on Python 3.12
try {
    pip install PyAudio --upgrade
} catch {
    Write-Host "PyAudio pip failed, trying pipwin..." -ForegroundColor Yellow
    pip install pipwin
    pipwin install pyaudio
}

Write-Host ""
Write-Host "Step 8: Verifying install" -ForegroundColor Cyan
python omni.py --test
python scripts/cuda_check.py

Write-Host ""
Write-Host "Setup complete! Next:" -ForegroundColor Green
Write-Host "  1. .\scripts\launch-chrome.ps1 (in new terminal, still need Bypass policy)" -ForegroundColor Cyan
Write-Host "  2. python omni.py" -ForegroundColor Cyan
Write-Host "  3. Or without mic: python omni.py --cli 'open github'" -ForegroundColor Cyan
