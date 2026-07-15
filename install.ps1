# OMNI V3 - One-shot install for Windows (PowerShell)
# Handles the llama-cpp-python prebuilt wheel issue automatically.
#
# Usage:
#   .\install.ps1                  # full install (CPU only, works on any laptop)
#   .\install.ps1 -Cuda cu121      # NVIDIA GPU acceleration
#   .\install.ps1 -Minimal         # just the brain, no voice/UI
#
# After install:
#   omni model download
#   omni test
#   omni start

[CmdletBinding()]
param(
    [string]$Cuda = "",
    [switch]$Minimal
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ====================================================="
Write-Host "   OMNI V3 - Install (Windows)"
Write-Host "  ====================================================="
Write-Host ""

# 1. Find Python
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    $py = (Get-Command py -ErrorAction SilentlyContinue).Source
}
if (-not $py) {
    Write-Host "  ❌ Python 3 not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}
$pyVersion = & $py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "  Python: $py ($pyVersion)"

# 2. Create venv if not in one
if (-not $env:VIRTUAL_ENV) {
    if (-not (Test-Path .venv)) {
        Write-Host "  Creating venv at .venv..."
        & $py -m venv .venv
    }
    Write-Host "  Activated venv: .venv"
    . .\.venv\Scripts\Activate.ps1
    $py = "python"
}

# 3. Upgrade pip
Write-Host "  Upgrading pip..."
& $py -m pip install --upgrade pip wheel setuptools --quiet

# 4. Install llama-cpp-python FIRST with prebuilt wheel
# (this is the package that fails to build from source without MSVC)
Write-Host "  Installing llama-cpp-python (prebuilt wheel)..."
if ($Cuda) {
    Write-Host "    -> CUDA variant: $Cuda"
    & $py -m pip install "llama-cpp-python" `
        --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/$Cuda" `
        --quiet
} else {
    Write-Host "    -> CPU variant (no GPU needed)"
    & $py -m pip install "llama-cpp-python" `
        --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu" `
        --quiet
}

# 5. Install the rest of OMNI
Write-Host "  Installing OMNI V3..."
if ($Minimal) {
    & $py -m pip install -e .[brain] --quiet
} else {
    & $py -m pip install -e .[all] --quiet
}

Write-Host ""
Write-Host "  ====================================================="
Write-Host "  ✅ OMNI V3 installed!"
Write-Host "  ====================================================="
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    omni model download    # fetches 1.1GB Qwen2.5-1.5B GGUF"
Write-Host "    omni test              # runs 4 test suites"
Write-Host "    omni start             # starts backend on :8765"
Write-Host ""
Write-Host "  Or, the old way (no install):"
Write-Host "    python omni.py --test"
Write-Host ""
