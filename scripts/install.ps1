# OMNI primary-platform source-checkout installer.
#
# B02 targets Windows 11 x64. This installer is not B01 evidence: B01's exact
# dependency lock remains CPython 3.11/Linux x86_64. See
# docs/TROUBLESHOOTING.md for the qualification boundary and recovery steps.

[CmdletBinding()]
param(
    [Alias("Minimal")]
    [switch]$Core,
    [switch]$All
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

if ($Core -and $All) {
    throw "Choose either -Core or -All, not both."
}
$profile = if ($All) { "all" } else { "core" }
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

. (Join-Path $PSScriptRoot "windows_platform.ps1")
$windowsPlatform = Assert-OmniWindows11X64
Write-Host "Primary platform: $($windowsPlatform.Caption) build $($windowsPlatform.Build) $($windowsPlatform.Architecture)"

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$python = if ($pythonCommand) { $pythonCommand.Source } else { $null }
$pythonPrefix = @()
if ($python) {
    & $python -c "import platform, sys; raise SystemExit(0 if platform.python_implementation() == 'CPython' and sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32 and platform.machine().lower() in {'amd64', 'x86_64'} else 1)"
}
if (-not $python -or $LASTEXITCODE -ne 0) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $launcher) {
        throw "CPython 3.11 x64 was not found. Install it from python.org and enable the py launcher."
    }
    $python = $launcher.Source
    $pythonPrefix = @("-3.11")
    & $python @pythonPrefix -c "import platform, sys; raise SystemExit(0 if platform.python_implementation() == 'CPython' and sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32 and platform.machine().lower() in {'amd64', 'x86_64'} else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "The py launcher does not provide CPython 3.11 x64."
    }
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    if (Test-Path (Join-Path $root ".venv")) {
        throw ".venv exists but is incomplete. Remove it after preserving anything intentional, then retry."
    }
    Write-Host "Creating isolated CPython 3.11 environment..."
    & $python @pythonPrefix -m venv (Join-Path $root ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv." }
}
& $venvPython -c "import platform, sys; raise SystemExit(0 if platform.python_implementation() == 'CPython' and sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32 and platform.machine().lower() in {'amd64', 'x86_64'} else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Existing .venv is not CPython 3.11 x64. Remove it explicitly and rerun the installer."
}

# A second install safely stops a runtime before replacing environment files.
# Do not use find_spec here: the checkout itself is importable from the current
# directory even in a brand-new environment whose runtime dependencies are not
# installed yet.
& $venvPython -c "import importlib.metadata as m; raise SystemExit(0 if any(d.metadata.get('Name', '').lower() == 'omni-agi' for d in m.distributions()) else 1)"
if ($LASTEXITCODE -eq 0) {
    & $venvPython -m omni_v2.core.runtime_cli --json stop | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "The existing owned runtime could not be stopped safely. Run status and inspect its state before retrying."
    }
}

Write-Host "Installing OMNI profile '$profile' from this checkout..."
$lockPath = Join-Path $root "requirements\locks\cpython-3.11-windows-x86_64\$profile.txt"
if (Test-Path $lockPath) {
    Write-Host "Using native Windows hashed lock: $lockPath"
    Invoke-Checked $venvPython -m pip install --require-hashes -r $lockPath
    # Native Windows locks include the exact pyproject build backend. Disable
    # build isolation so local-source installation cannot resolve hidden build
    # dependencies from the network.
    Invoke-Checked $venvPython -m pip install --no-build-isolation --no-deps .
} else {
    # Truthful fallback until native Windows resolution is generated and
    # committed by scripts/resolve_profiles.py on Windows 11 x64.
    Write-Warning "Native Windows lock is absent; dependencies and build tools are index-resolved. This is not B01 evidence or a reproducible Windows qualification."
    Invoke-Checked $venvPython -m pip install ".[${profile}]"
}
Invoke-Checked $venvPython -m pip check
Invoke-Checked $venvPython -m omni_v2.core.runtime_cli --json config init | Out-Null

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$corepackCommand = Get-Command corepack -ErrorAction SilentlyContinue
if (-not $nodeCommand -or -not $corepackCommand) {
    throw "Node.js 22.22.2+ (major 22) with Corepack is required for the OMNI interface."
}
$nodeVersionText = (& $nodeCommand.Source --version).TrimStart("v")
try { $nodeVersion = [version]$nodeVersionText } catch { throw "Could not parse Node.js version '$nodeVersionText'." }
if ($nodeVersion.Major -ne 22 -or $nodeVersion -lt [version]"22.22.2") {
    throw "Node.js >=22.22.2,<23 is required; found $nodeVersionText."
}
$npmVersion = (& $corepackCommand.Source "npm@12.0.2" --version).Trim()
if ($LASTEXITCODE -ne 0 -or $npmVersion -ne "12.0.2") {
    throw "Corepack could not provide npm 12.0.2 required by frontend_next/package.json."
}

$configJson = (& $venvPython -m omni_v2.core.runtime_cli --json config show | Out-String)
if ($LASTEXITCODE -ne 0) { throw "Could not resolve canonical runtime configuration." }
$config = $configJson | ConvertFrom-Json
$env:OMNI_BACKEND_URL = $config.backend_url
$env:OMNI_BACKEND_HOST = $config.backend_host
$env:OMNI_BACKEND_PORT = [string]$config.backend_port
$env:OMNI_FRONTEND_HOST = $config.frontend_host
$env:OMNI_FRONTEND_PORT = [string]$config.frontend_port

Write-Host "Installing exact frontend lock and creating a production build..."
Push-Location (Join-Path $root "frontend_next")
try {
    Invoke-Checked $corepackCommand.Source npm@12.0.2 ci
    Invoke-Checked $corepackCommand.Source npm@12.0.2 run build
} finally {
    Pop-Location
}

Write-Host "Running primary-platform preflight..."
Invoke-Checked $venvPython -m omni_v2.core.runtime_cli preflight --primary --frontend --root $root

Write-Host ""
Write-Host "OMNI installation is ready."
Write-Host "Start:     .\start.bat"
Write-Host "Stop:      .\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli stop"
Write-Host "Uninstall: powershell -File scripts\uninstall.ps1"
Write-Host "Config:    $($config.config_path)"
Write-Host "Missing models and optional hardware are reported as warnings, not hidden or auto-downloaded."
