# ==============================================================================
# 🤖 OMNI V3 - CINEMATIC HALF-DUPLEX AGI HERMES LAUNCHER (PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# Check inner folder structure if needed
if (Test-Path "$ProjectRoot\Omni\omni.py") {
    Write-Host "[INFO] Detected inner Omni directory. Entering Omni\..." -ForegroundColor Cyan
    Set-Location "$ProjectRoot\Omni"
    $ProjectRoot = "$ProjectRoot\Omni"
}

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  🤖 OMNI V3 - CINEMATIC HALF-DUPLEX AGI HERMES LAUNCHER" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "[INFO] Working Directory: $(Get-Location)" -ForegroundColor Green

# 1. Verify python in virtualenv
$PythonExe = "$(Get-Location)\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment python.exe not found at $PythonExe" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv && .venv\Scripts\activate && pip install -r backend_fastapi\requirements.txt" -ForegroundColor Yellow
    exit 1
}

# 2. Check and install node_modules if missing
if (-not (Test-Path "$(Get-Location)\frontend_next\node_modules")) {
    Write-Host "[INFO] Installing Next.js node_modules in frontend_next..." -ForegroundColor Yellow
    Push-Location "$(Get-Location)\frontend_next"
    npm install
    Pop-Location
}

Write-Host "`n[1/2] Spawning FastAPI Brain Backend on Port 8765..." -ForegroundColor Green
# Use python -m uvicorn to completely bypass the Windows .exe launcher WinError!
$BackendPath = "$(Get-Location)\backend_fastapi"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k `"cd /d `"$BackendPath`" && ..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8765`"" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "[2/2] Opening web browser & starting Next.js on Port 3000..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Set-Location "$(Get-Location)\frontend_next"
npm run dev
