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
    [string]$ResolutionPath,
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

function Get-ExactHashedLockRecords {
    param([Parameter(Mandatory = $true)][string]$Path)

    $records = @{}
    $lineNumber = 0
    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $lineNumber += 1
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) { continue }
        if ($line -notmatch "^([A-Za-z0-9_.-]+)==([^\s]+)\s+--hash=sha256:([a-f0-9]{64})$") {
            throw "Invalid exact hashed lock entry at ${Path}:$lineNumber"
        }
        $name = ([string]$Matches[1]).ToLowerInvariant() -replace "[-_.]+", "-"
        if ($records.ContainsKey($name)) { throw "Duplicate exact lock distribution: $name" }
        $records[$name] = [pscustomobject]@{ version = [string]$Matches[2]; sha256 = [string]$Matches[3] }
    }
    if ($records.Count -eq 0) { throw "Exact hashed lock is empty: $Path" }
    return $records
}

function Assert-ExactInstalledEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][hashtable]$BuildRecords,
        [Parameter(Mandatory = $true)][hashtable]$RuntimeRecords,
        [Parameter(Mandatory = $true)][string]$ProjectVersion
    )

    $expected = @{}
    foreach ($authority in @($BuildRecords, $RuntimeRecords)) {
        foreach ($entry in $authority.GetEnumerator()) {
            $name = [string]$entry.Key
            $version = [string]$entry.Value.version
            if ($expected.ContainsKey($name) -and $expected[$name] -ne $version) {
                throw "Exact build and runtime locks conflict for ${name}: $($expected[$name]) and $version."
            }
            $expected[$name] = $version
        }
    }
    $expected["omni-agi"] = $ProjectVersion

    $inventoryText = (& $Python -m pip list --format json --disable-pip-version-check | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "Could not inventory the managed environment." }
    $inventory = $inventoryText | ConvertFrom-Json
    $installed = @{}
    foreach ($distribution in @($inventory)) {
        $name = ([string]$distribution.name).ToLowerInvariant() -replace "[-_.]+", "-"
        if ($installed.ContainsKey($name)) { throw "Managed environment contains duplicate distribution: $name" }
        $installed[$name] = [string]$distribution.version
    }
    $missing = @($expected.Keys | Where-Object { -not $installed.ContainsKey($_) })
    $unexpected = @($installed.Keys | Where-Object { -not $expected.ContainsKey($_) })
    $mismatched = @($expected.Keys | Where-Object { $installed.ContainsKey($_) -and $installed[$_] -ne $expected[$_] })
    if ($missing.Count -ne 0 -or $unexpected.Count -ne 0 -or $mismatched.Count -ne 0) {
        throw "Managed distributions differ from the exact authority (missing=$($missing -join ','), unexpected=$($unexpected -join ','), mismatched=$($mismatched -join ',')). Remove .venv and retry."
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

if ($LockPath) {
    $resolvedLockPath = (Resolve-Path -LiteralPath $LockPath -ErrorAction Stop).Path
    $resolvedBuildLockPath = Join-Path (Split-Path -Parent $resolvedLockPath) "build.txt"
} else {
    $lockRoot = Join-Path $root "requirements\locks\cpython-3.11-windows-$architectureSlug"
    $resolvedLockPath = Join-Path $lockRoot "$profile.txt"
    $resolvedBuildLockPath = Join-Path $lockRoot "build.txt"
}
if (-not (Test-Path -LiteralPath $resolvedBuildLockPath -PathType Leaf)) {
    throw "Exact wheel-only native build lock is absent: $resolvedBuildLockPath"
}
$resolvedResolutionPath = if ($ResolutionPath) {
    (Resolve-Path -LiteralPath $ResolutionPath -ErrorAction Stop).Path
} else {
    $null
}

# Prove the native compiler/linker/SDK before any dependency metadata
# preparation. This rejects x64 tools and outputs on Arm64 (and vice versa).
. (Join-Path $PSScriptRoot "windows_build_tools.ps1")
$buildContract = Get-OmniBuildContract
$buildRecords = Get-ExactHashedLockRecords $resolvedBuildLockPath
$expectedBuildRecords = @{}
$contractBuildHashes = $buildContract.build_artifact_sha256.$architectureSlug
foreach ($property in $buildContract.build_lock.PSObject.Properties) {
    $name = $property.Name.ToLowerInvariant()
    $hashProperty = $contractBuildHashes.PSObject.Properties[$name]
    if (-not $hashProperty) {
        throw "Native build contract has no $architectureSlug artifact hash for $name."
    }
    $expectedBuildRecords[$name] = [pscustomobject]@{
        version = [string]$property.Value
        sha256 = [string]$hashProperty.Value
    }
}
if (
    $buildRecords.Count -ne $expectedBuildRecords.Count -or
    @($expectedBuildRecords.Keys | Where-Object {
        -not $buildRecords.ContainsKey($_) -or
        [string]$buildRecords[$_].version -ne [string]$expectedBuildRecords[$_].version -or
        [string]$buildRecords[$_].sha256 -ne [string]$expectedBuildRecords[$_].sha256
    }).Count -ne 0
) {
    throw "Exact build lock versions or artifact hashes do not match quality/windows-native-build-contract.json."
}
Write-Host "Validating native Visual Studio 2022 compiler, linker, and Windows SDK..."
$nativeBuildTools = Enter-OmniWindowsNativeBuildEnvironment -ArchitectureSlug $architectureSlug
Write-Host "Native toolchain: $($nativeBuildTools.compiler) -> PE $($nativeBuildTools.pe_machine)"

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
Write-Host "Bootstrapping exact wheel-only build authority: $resolvedBuildLockPath"
Invoke-Checked $venvPython -m pip install --disable-pip-version-check --no-cache-dir "--only-binary=:all:" --no-deps --require-hashes -r $resolvedBuildLockPath
Invoke-Checked $venvPython -m pip check
# --no-build-isolation does not activate the invoking virtual environment for
# backend subprocesses. Put its exact Scripts directory first so setup.py,
# CMake backends, and compiler probes cannot select an ambient CMake or Ninja.
$venvScripts = Split-Path -Parent $venvPython
$env:PATH = "$venvScripts;$env:PATH"
$cmakeVersion = ((& (Join-Path $venvScripts "cmake.exe") --version | Select-Object -First 1) | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $cmakeVersion -ne [string]$buildContract.build_tool_cli.cmake) {
    throw "The installed CMake CLI identity does not match the native build contract: '$cmakeVersion'."
}
$ninjaVersion = ((& (Join-Path $venvScripts "ninja.exe") --version) | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $ninjaVersion -ne [string]$buildContract.build_tool_cli.ninja) {
    throw "The installed Ninja CLI identity does not match the native build contract: '$ninjaVersion'."
}
$runtimeRecords = $null
if (Test-Path -LiteralPath $resolvedLockPath -PathType Leaf) {
    $runtimeRecords = Get-ExactHashedLockRecords $resolvedLockPath
    if ($resolvedResolutionPath) {
        $resolution = (Get-Content -Raw -LiteralPath $resolvedResolutionPath) | ConvertFrom-Json
        if (
            $resolution.status -ne "pass" -or
            [string]$resolution.platform.system -ne "Windows" -or
            [string]$resolution.platform.normalized_machine -ne $architectureSlug -or
            $resolution.third_party_build_isolation -ne $false -or
            [string]$resolution.source_build_contract -ne "quality/windows-native-build-contract.json" -or
            $resolution.profiles.$profile.status -ne "pass"
        ) {
            throw "Resolver evidence does not authorize this native Windows $architectureSlug $profile installation."
        }
        $resolvedRecords = @{}
        foreach ($package in @($resolution.profiles.$profile.packages)) {
            $name = ([string]$package.name).ToLowerInvariant() -replace "[-_.]+", "-"
            if ($name -eq "omni-agi") { continue }
            $resolvedRecords[$name] = [pscustomobject]@{ version = [string]$package.version; sha256 = [string]$package.sha256 }
        }
        if (
            $runtimeRecords.Count -ne $resolvedRecords.Count -or
            @($resolvedRecords.Keys | Where-Object {
                -not $runtimeRecords.ContainsKey($_) -or
                [string]$runtimeRecords[$_].version -ne [string]$resolvedRecords[$_].version -or
                [string]$runtimeRecords[$_].sha256 -ne [string]$resolvedRecords[$_].sha256
            }).Count -ne 0
        ) {
            throw "Runtime lock bytes do not match the supplied resolver artifact evidence."
        }
        $approvedSources = @{}
        foreach ($record in @($buildContract.source_distributions.$architectureSlug)) {
            $name = ([string]$record.name).ToLowerInvariant() -replace "[-_.]+", "-"
            $approvedSources["$name==$([string]$record.version)"] = $record
        }
        foreach ($package in @($resolution.profiles.$profile.packages | Where-Object { [string]$_.artifact_kind -eq "sdist" })) {
            $name = ([string]$package.name).ToLowerInvariant() -replace "[-_.]+", "-"
            $key = "$name==$([string]$package.version)"
            if (
                -not $approvedSources.ContainsKey($key) -or
                [string]$package.sha256 -ne [string]$approvedSources[$key].sha256
            ) {
                throw "Resolver evidence selected an unapproved native source artifact: $key"
            }
        }
    } else {
        Write-Warning "No -ResolutionPath was supplied; this exact-lock installation is not B02 qualification evidence."
    }
    Write-Host "Using native Windows hashed lock: $resolvedLockPath"
    Invoke-Checked $venvPython -m pip install --disable-pip-version-check --no-cache-dir --no-build-isolation --require-hashes -r $resolvedLockPath
    # Every third-party source distribution must build with the preinstalled
    # authority above. PEP 517 isolation and pip's local wheel cache are both
    # forbidden because either can hide undeclared build inputs.
    Invoke-Checked $venvPython -m pip install --disable-pip-version-check --no-cache-dir --no-build-isolation --no-deps .
} else {
    # Truthful fallback for ordinary development installation only. The B02
    # qualification driver always supplies a native exact runtime lock and
    # never enters this branch. The build authority remains exact even here.
    Write-Warning "Native Windows $architectureSlug runtime lock is absent; runtime dependencies are index-resolved. This is not reproducible Windows qualification evidence."
    Invoke-Checked $venvPython -m pip install --disable-pip-version-check --no-cache-dir --no-build-isolation ".[${profile}]"
}
Invoke-Checked $venvPython -m pip check
if ($null -ne $runtimeRecords) {
    $projectVersion = ((& $venvPython -c "import pathlib, sys, tomllib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))['project']['version'])" (Join-Path $root "pyproject.toml")) | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $projectVersion) {
        throw "Could not identify the expected OMNI project version."
    }
    Assert-ExactInstalledEnvironment -Python $venvPython -BuildRecords $buildRecords -RuntimeRecords $runtimeRecords -ProjectVersion $projectVersion
}
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
