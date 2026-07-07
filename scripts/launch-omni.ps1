# OMNI Launcher Script

$ErrorActionPreference = "Stop"

# Activate venv if exists
$venvPath = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $venvPath (Join-Path $PSScriptRoot "..\omni.py")
} else {
    python (Join-Path $PSScriptRoot "..\omni.py")
}
