# Managed OMNI launcher for native Windows 11 X64 or Arm64.

[CmdletBinding()]
param(
    [switch]$Restart,
    [switch]$BackendOnly,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
. (Join-Path $PSScriptRoot "windows_platform.ps1")
$null = Assert-OmniWindows11
$python = Join-Path $root ".venv\Scripts\python.exe"
$frontendBuild = Join-Path $root "frontend_next\.next\BUILD_ID"

if (-not (Test-Path $python) -or (-not $BackendOnly -and -not (Test-Path $frontendBuild))) {
    Write-Host "Installation assets are missing; running the idempotent installer..."
    & (Join-Path $root "scripts\install.ps1") -Core
    if ($LASTEXITCODE -ne 0) { throw "Installation failed." }
}

$preflightArguments = @("-m", "omni_v2.core.runtime_cli", "preflight", "--primary", "--root", $root)
if (-not $BackendOnly) { $preflightArguments += "--frontend" }
& $python @preflightArguments
if ($LASTEXITCODE -ne 0) { throw "Primary-platform preflight failed." }

$statusJson = (& $python -m omni_v2.core.runtime_cli --json status | Out-String)
$status = $statusJson | ConvertFrom-Json
$frontendRunning = @($status.services | Where-Object { $_.name -eq "frontend" -and $_.status -eq "running" }).Count -eq 1
$needsRecovery = @($status.services | Where-Object { $_.status -in @("unhealthy", "unverified") }).Count -gt 0
$mustRestart = $Restart -or $needsRecovery -or ($status.ok -and -not $BackendOnly -and -not $frontendRunning)

if ($mustRestart) {
    $arguments = @("-m", "omni_v2.core.runtime_cli", "restart")
    if ($BackendOnly) { $arguments += "--backend-only" }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Managed restart failed." }
} elseif (-not $status.ok) {
    $arguments = @("-m", "omni_v2.core.runtime_cli", "start")
    if ($BackendOnly) { $arguments += "--backend-only" }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Managed startup failed." }
} else {
    Write-Host "OMNI is already running under verified process ownership."
}

$configJson = (& $python -m omni_v2.core.runtime_cli --json config show | Out-String)
if ($LASTEXITCODE -ne 0) { throw "Could not resolve launcher URL." }
$config = $configJson | ConvertFrom-Json
# The public configuration intentionally exposes only base URLs; derive docs.
$url = if ($BackendOnly) { "$($config.backend_url)/docs" } else { $config.frontend_url }
Write-Host "OMNI is ready at $url"
if (-not $NoBrowser) {
    Start-Process $url
}
