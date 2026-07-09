# OMNI Setup Script - Install dependencies on Windows

Write-Host "OMNI Setup" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Install Python 3.10+ from python.org" -ForegroundColor Red
    exit 1
}

# Python version check
$versionMatch = python --version 2>&1 | Select-String "Python 3.(1[0-9]|[2-9][0-9])"
if (-not $versionMatch) {
    Write-Host "WARNING: Python 3.10+ recommended for best compatibility" -ForegroundColor Yellow
}

# Run the main install from requirements.txt
Write-Host ""
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
Write-Host "(This may take a few minutes on first run)" -ForegroundColor Yellow

pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Some packages failed to install." -ForegroundColor Red
    Write-Host "Try running as Administrator: Right-click PowerShell → Run as Administrator" -ForegroundColor Yellow
    Write-Host "Then re-run: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. (Optional) Launch Chrome with CDP: .\scripts\launch-chrome.ps1"
Write-Host "  2. Run OMNI: python omni.py"
Write-Host "  3. Press CapsLock to speak"
Write-Host ""
Write-Host "For GPU acceleration (Whisper CUDA):" -ForegroundColor Yellow
Write-Host "  Install Visual C++ Redistributable:" -ForegroundColor Yellow
Write-Host "  https://aka.ms/vs/17/release/vc_redist.x64.exe" -ForegroundColor Yellow