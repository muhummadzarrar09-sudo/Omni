# OMNI source-checkout convenience installer for Windows.
#
# This script resolves declared dependency ranges from package indexes. It is
# not B01 qualification evidence. B01 qualifies CPython 3.11 on Linux x86_64;
# see docs/TROUBLESHOOTING.md for the exact hash-lock + local-wheel workflow.

[CmdletBinding()]
param(
    [Alias("Minimal")]
    [switch]$Core,
    [switch]$All
)

$ErrorActionPreference = "Stop"
if ($Core -and $All) {
    throw "Choose either -Core or -All, not both."
}
$profile = if ($Core) { "core" } else { "all" }
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) {
    throw "CPython 3.11 was not found."
}
$python = $pythonCommand.Source
& $python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    $found = & $python -VV
    throw "OMNI requires CPython >=3.11,<3.12; found $found."
}

if (-not $env:VIRTUAL_ENV) {
    if (-not (Test-Path .venv)) {
        & $python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create .venv." }
    }
    . .\.venv\Scripts\Activate.ps1
    $python = "python"
}

Write-Host "OMNI source install: profile=$profile (index-resolved; not B01 evidence)"
Write-Host "For the qualified workflow, see docs/TROUBLESHOOTING.md."
& $python -m pip install ".[${profile}]"
if ($LASTEXITCODE -ne 0) { throw "OMNI source installation failed." }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw "The installed environment has broken requirements." }

Write-Host "Installed OMNI from this checkout with the '$profile' profile."
Write-Host "Run: omni --help"
