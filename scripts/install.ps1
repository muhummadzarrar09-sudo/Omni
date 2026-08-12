# OMNI native Windows source-checkout installer.
#
# B02 targets the Windows 11 Arm64 DGX Station software/control plane and also
# exercises a Windows 11 x64 surrogate path. This installer is not B01 evidence:
# B01's exact dependency lock remains CPython 3.11/Linux x86_64. See
# docs/TROUBLESHOOTING.md for the qualification boundary and recovery steps.

[CmdletBinding()]
param(
    [Alias("Minimal")]
    [switch]$Core,
    [switch]$All,
    [string]$LockPath,
    [string]$PythonPath
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
$windowsPlatform = Assert-OmniWindows11
$architectureSlug = Get-OmniWindowsArchitectureSlug $windowsPlatform
$pythonMachines = @(Get-OmniPythonMachineNames $windowsPlatform)
$pythonMachineLiteral = ($pythonMachines | ForEach-Object { "'$_'" }) -join ", "
$pythonProbe = "import platform, sys; allowed={$pythonMachineLiteral}; raise SystemExit(0 if platform.python_implementation() == 'CPython' and sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32 and platform.machine().lower() in allowed else 1)"
Write-Host "Windows platform: $($windowsPlatform.Caption) build $($windowsPlatform.Build) $($windowsPlatform.Architecture)"

$pythonPrefix = @()
if ($PythonPath) {
    $python = (Resolve-Path -LiteralPath $PythonPath -ErrorAction Stop).Path
    & $python -c $pythonProbe
    if ($LASTEXITCODE -ne 0) {
        throw "-PythonPath must name native CPython 3.11 $($windowsPlatform.Architecture); rejected '$python'."
    }
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $python = if ($pythonCommand) { $pythonCommand.Source } else { $null }
    if ($python) {
        & $python -c $pythonProbe
    }
    if (-not $python -or $LASTEXITCODE -ne 0) {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw "Native CPython 3.11 $($windowsPlatform.Architecture) was not found. Install the matching python.org build and enable the py launcher."
        }
        $python = $launcher.Source
        $pythonPrefix = @("-3.11")
        & $python @pythonPrefix -c $pythonProbe
        if ($LASTEXITCODE -ne 0) {
            throw "The py launcher does not provide native CPython 3.11 $($windowsPlatform.Architecture). Emulated cross-architecture Python does not qualify."
        }
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
& $venvPython -c $pythonProbe
if ($LASTEXITCODE -ne 0) {
    throw "Existing .venv is not native CPython 3.11 $($windowsPlatform.Architecture). Remove it explicitly and rerun the installer."
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
if ($LockPath) {
    $resolvedLockPath = (Resolve-Path -LiteralPath $LockPath -ErrorAction Stop).Path
} else {
    $resolvedLockPath = Join-Path $root "requirements\locks\cpython-3.11-windows-$architectureSlug\$profile.txt"
}
if (Test-Path -LiteralPath $resolvedLockPath) {
    Write-Host "Using native Windows hashed lock: $resolvedLockPath"
    Invoke-Checked $venvPython -m pip install --require-hashes -r $resolvedLockPath
    # Native Windows locks include the exact pyproject build backend. Disable
    # build isolation so local-source installation cannot resolve hidden build
    # dependencies from the network.
    Invoke-Checked $venvPython -m pip install --no-build-isolation --no-deps .
} else {
    # Truthful fallback for ordinary development installation only. The B02
    # qualification driver always supplies a native exact lock and never enters
    # this branch.
    Write-Warning "Native Windows $architectureSlug lock is absent; dependencies and build tools are index-resolved. This is not reproducible Windows qualification evidence."
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

Write-Host "Running native Windows qualification-platform preflight..."
Invoke-Checked $venvPython -m omni_v2.core.runtime_cli preflight --primary --frontend --root $root

Write-Host ""
Write-Host "OMNI installation is ready."
Write-Host "Start:     .\start.bat"
Write-Host "Stop:      .\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli stop"
Write-Host "Uninstall: powershell -File scripts\uninstall.ps1"
Write-Host "Config:    $($config.config_path)"
Write-Host "Missing models and optional hardware are reported as warnings, not hidden or auto-downloaded."
