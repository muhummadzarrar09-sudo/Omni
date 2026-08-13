# Native Windows 11 B02 install/lifecycle/uninstall qualification.
# Prefer scripts/qualify_b02.ps1, which invokes this verifier in an exact,
# isolated worktree and aggregates the required Arm64/x64 evidence matrix.

[CmdletBinding()]
param(
    [switch]$KeepInstalled,
    [string]$PythonPath,
    [string]$LockPath,
    [string]$ResolutionPath,
    [string]$EvidenceDirectory,
    [string]$QualificationDataPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "`n=== $Name ==="
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

function Get-NormalizedMachine {
    param([string]$Machine)
    switch ($Machine.ToLowerInvariant()) {
        { $_ -in @("amd64", "x86_64") } { return "x86_64" }
        { $_ -in @("arm64", "aarch64") } { return "arm64" }
        default { return $Machine.ToLowerInvariant() }
    }
}

Assert-True ($env:OS -eq "Windows_NT") "This qualification must run on Windows."
& git diff --quiet HEAD "--"
Assert-True ($LASTEXITCODE -eq 0) "Qualification requires tracked source files to match the exact HEAD commit."

. (Join-Path $PSScriptRoot "windows_platform.ps1")
$windowsPlatform = Assert-OmniWindows11
$architectureSlug = Get-OmniWindowsArchitectureSlug $windowsPlatform
$expectedPythonMachines = @(Get-OmniPythonMachineNames $windowsPlatform)
$evidencePrefix = "windows-$architectureSlug-install-qualification"

if (-not $EvidenceDirectory) {
    $EvidenceDirectory = Join-Path $root "quality\evidence\B02\native\windows-$architectureSlug"
}
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
$EvidenceDirectory = (Resolve-Path -LiteralPath $EvidenceDirectory).Path
$transcriptPath = Join-Path $EvidenceDirectory "$evidencePrefix.log"
$evidencePath = Join-Path $EvidenceDirectory "$evidencePrefix.json"
$transcriptStarted = $false

if (-not $LockPath) {
    $LockPath = Join-Path $root "requirements\locks\cpython-3.11-windows-$architectureSlug\core.txt"
}
if (-not $ResolutionPath) {
    $ResolutionPath = Join-Path $root "quality\evidence\B02\cpython-3.11-windows-$architectureSlug-profile-resolution.json"
}
$LockPath = (Resolve-Path -LiteralPath $LockPath -ErrorAction Stop).Path
$ResolutionPath = (Resolve-Path -LiteralPath $ResolutionPath -ErrorAction Stop).Path

$originalDataDir = $env:OMNI_DATA_DIR
$originalApiToken = $env:OMNI_API_TOKEN
if (-not $QualificationDataPath) {
    $QualificationDataPath = Join-Path ([IO.Path]::GetTempPath()) "omni-b02-$architectureSlug-data-$PID"
}
Assert-True (-not (Test-Path -LiteralPath $QualificationDataPath)) "Qualification data directory already exists: $QualificationDataPath"
$env:OMNI_DATA_DIR = $QualificationDataPath
$env:OMNI_API_TOKEN = "b02-$architectureSlug-$([Guid]::NewGuid().ToString('N'))"
$recordedProcesses = @{}
$recordedProcessObservations = 0
$qualificationError = $null
$cleanupErrors = [System.Collections.Generic.List[string]]::new()

function Register-OwnedProcesses {
    param([Parameter(Mandatory = $true)]$LifecycleResult)

    foreach ($service in @($LifecycleResult.services)) {
        if ($null -eq $service.pid) { continue }
        $pidValue = [int]$service.pid
        try {
            $process = Get-Process -Id $pidValue -ErrorAction Stop
            $startTimeUtcTicks = $process.StartTime.ToUniversalTime().Ticks
            $executable = [string]$process.Path
            $identityKey = "$pidValue`:$startTimeUtcTicks`:$executable"
            if (-not $recordedProcesses.ContainsKey($identityKey)) {
                $recordedProcesses[$identityKey] = [pscustomobject]@{
                    pid = $pidValue
                    start_time_utc_ticks = $startTimeUtcTicks
                    executable = $executable
                }
            }
            $script:recordedProcessObservations += 1
        } catch {
            throw "Could not record owned $($service.name) process identity for PID ${pidValue}: $($_.Exception.Message)"
        }
    }
}

function Test-RecordedProcessIdentity {
    param([Parameter(Mandatory = $true)]$Identity)

    try {
        $process = Get-Process -Id ([int]$Identity.pid) -ErrorAction Stop
    } catch {
        return $false
    }
    try {
        return (
            $process.StartTime.ToUniversalTime().Ticks -eq [long]$Identity.start_time_utc_ticks -and
            [string]$process.Path -eq [string]$Identity.executable
        )
    } catch {
        return $false
    }
}

function Remove-GeneratedPath {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Label)

    if (-not (Test-Path -LiteralPath $Path)) { return }
    $lastError = $null
    for ($attempt = 1; $attempt -le 3; $attempt += 1) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            if (-not (Test-Path -LiteralPath $Path)) { return }
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Milliseconds (250 * $attempt)
    }
    $suffix = if ($lastError) { ": $lastError" } else { "" }
    [void]$cleanupErrors.Add("$Label remains at $Path$suffix")
}

try {
    Start-Transcript -Path $transcriptPath -Force | Out-Null
    $transcriptStarted = $true

    $resolution = (Get-Content -Raw -Path $ResolutionPath) | ConvertFrom-Json
    Assert-True ($resolution.status -eq "pass") "Native Windows resolver evidence does not report pass."
    Assert-True ($resolution.python.implementation -eq "CPython" -and $resolution.python.version.StartsWith("3.11.")) "Resolver evidence was not generated by CPython 3.11."
    $resolutionMachine = if ($resolution.platform.normalized_machine) {
        [string]$resolution.platform.normalized_machine
    } else {
        Get-NormalizedMachine ([string]$resolution.platform.machine)
    }
    Assert-True ($resolution.platform.system -eq "Windows" -and $resolutionMachine -eq $architectureSlug) "Resolver evidence architecture does not match native Windows $architectureSlug."
    if ($resolution.platform.windows_os_machine) {
        Assert-True ([string]$resolution.platform.windows_os_machine -eq $architectureSlug) "Resolver evidence was produced under architecture emulation."
    }
    Assert-True ([int]$resolution.platform.pointer_bits -eq 64) "Resolver evidence was not generated by a 64-bit CPython interpreter."
    Assert-True ([int]$resolution.platform.windows_build -ge 22000) "Resolver evidence predates Windows 11 build 22000."
    Assert-True ([int]$resolution.platform.windows_product_type -eq 1) "Resolver evidence was not generated on a Windows workstation product."
    Assert-True ($resolution.third_party_build_isolation -eq $false) "Resolver evidence did not disable third-party build isolation."
    Assert-True ([string]$resolution.source_build_contract -eq "quality/windows-native-build-contract.json") "Resolver evidence omitted the native source-build contract."
    $buildLockPath = Join-Path (Split-Path -Parent $LockPath) "build.txt"
    Assert-True (Test-Path -LiteralPath $buildLockPath -PathType Leaf) "Resolver lock set omits the exact build lock."
    foreach ($profile in @("core", "voice", "vision", "desktop", "dev", "all")) {
        Assert-True ($resolution.profiles.$profile.status -eq "pass") "Resolver evidence does not contain a passing $profile profile."
    }
    if ($architectureSlug -eq "arm64") {
        Assert-True ($resolution.arm64_capability_contract.status -eq "pass") "Resolver evidence did not enforce the Windows Arm64 capability contract."
    }
    Assert-True (-not (Test-Path "$root\.venv")) "Qualification requires a clean worktree without .venv."
    Assert-True (-not (Test-Path "$root\frontend_next\node_modules")) "Qualification requires a clean worktree without node_modules."
    Assert-True (-not (Test-Path "$root\frontend_next\.next")) "Qualification requires a clean worktree without a frontend build."

    $installArguments = @("-Core", "-LockPath", $LockPath, "-ResolutionPath", $ResolutionPath)
    if ($PythonPath) { $installArguments += @("-PythonPath", $PythonPath) }
    Invoke-Step "First clean install" { & "$root\scripts\install.ps1" @installArguments }
    $python = "$root\.venv\Scripts\python.exe"
    Assert-True (Test-Path $python) "First install did not create the managed environment."
    Assert-True (Test-Path "$root\frontend_next\.next\BUILD_ID") "First install did not create a frontend build."

    $config = (& $python -m omni_v2.core.runtime_cli --json config show | Out-String) | ConvertFrom-Json
    $configPath = [string]$config.config_path
    Assert-True (Test-Path $configPath) "Canonical config was not initialized."
    Assert-True ($config.secrets.api_token_configured -eq $true) "Qualification API authentication secret was not projected into runtime configuration."
    $configBefore = (Get-FileHash -Algorithm SHA256 $configPath).Hash
    $pythonMetadata = ((& $python -c "import json, platform, sys; print(json.dumps({'implementation': platform.python_implementation(), 'version': platform.python_version(), 'architecture': platform.machine(), 'executable': sys.executable}))" | Out-String) | ConvertFrom-Json)
    Assert-True ($pythonMetadata.implementation -eq "CPython" -and $pythonMetadata.version.StartsWith("3.11.") -and $pythonMetadata.architecture.ToLowerInvariant() -in $expectedPythonMachines) "Managed interpreter is not native CPython 3.11 $($windowsPlatform.Architecture)."
    $nodeVersion = (& node --version).Trim()
    $nodeArchitecture = (& node -p "process.arch").Trim().ToLowerInvariant()
    if ($nodeArchitecture -eq "x64") { $nodeArchitecture = "x86_64" }
    Assert-True ($nodeArchitecture -eq $architectureSlug) "Node.js process architecture $nodeArchitecture does not match native Windows $architectureSlug."
    $corepackCommand = Get-Command corepack -ErrorAction Stop
    $corepackVersion = (& $corepackCommand.Source --version).Trim()
    $npmVersion = (& $corepackCommand.Source "npm@12.0.2" --version).Trim()
    Assert-True ($LASTEXITCODE -eq 0 -and $npmVersion -eq "12.0.2") "Corepack did not resolve exact npm 12.0.2 during qualification."
    $commitSha = (& git rev-parse HEAD).Trim()

    Invoke-Step "Managed start before second install" { & "$root\scripts\start.ps1" -NoBrowser }
    $beforeReinstall = (& $python -m omni_v2.core.runtime_cli --json status | Out-String) | ConvertFrom-Json
    Assert-True $beforeReinstall.ok "Status did not verify the generation before reinstall."
    Assert-True (@($beforeReinstall.services).Count -eq 2) "Full startup did not own backend and frontend."
    Register-OwnedProcesses $beforeReinstall
    $preinstallPids = @($beforeReinstall.services | ForEach-Object { [int]$_.pid })

    Invoke-Step "Authenticated backend readiness" {
        $headers = @{ Authorization = "Bearer $($env:OMNI_API_TOKEN)" }
        $ticket = Invoke-RestMethod -Method Post -Uri "$($config.backend_url)/api/auth/websocket-ticket" -Headers $headers -TimeoutSec 15
        Assert-True ([bool]$ticket.ticket) "Authenticated readiness did not issue a WebSocket ticket."
        $frontendResponse = Invoke-WebRequest -UseBasicParsing -Uri $config.frontend_url -TimeoutSec 15
        Assert-True ([int]$frontendResponse.StatusCode -eq 200) "Frontend readiness did not return HTTP 200."
    }

    Invoke-Step "Idempotent second install while running" { & "$root\scripts\install.ps1" @installArguments }
    Assert-True ((Get-FileHash -Algorithm SHA256 $configPath).Hash -eq $configBefore) "Second install overwrote canonical configuration."
    foreach ($pidValue in $preinstallPids) {
        Assert-True (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) "Second install left old PID $pidValue running."
    }
    Assert-True (-not (Test-Path ([string]$config.runtime_state_path))) "Second install left stale runtime state."

    Invoke-Step "Managed start after second install" { & "$root\scripts\start.ps1" -NoBrowser }
    $first = (& $python -m omni_v2.core.runtime_cli --json status | Out-String) | ConvertFrom-Json
    Assert-True $first.ok "Status did not verify the post-install generation."
    Assert-True (@($first.services).Count -eq 2) "Full startup did not own backend and frontend."
    Register-OwnedProcesses $first
    $firstPids = @($first.services | ForEach-Object { [int]$_.pid })

    Invoke-Step "Idempotent second managed start" { & "$root\scripts\start.ps1" -NoBrowser }
    $idempotent = (& $python -m omni_v2.core.runtime_cli --json status | Out-String) | ConvertFrom-Json
    Assert-True $idempotent.ok "Second managed start did not preserve a ready generation."
    Register-OwnedProcesses $idempotent
    $idempotentPids = @($idempotent.services | ForEach-Object { [int]$_.pid })
    Assert-True (-not (@($firstPids | Where-Object { $idempotentPids -notcontains $_ }))) "Second managed start replaced an already healthy PID."
    Assert-True (-not (@($idempotentPids | Where-Object { $firstPids -notcontains $_ }))) "Second managed start changed the healthy process set."

    Invoke-Step "Managed restart" { & "$root\scripts\start.ps1" -Restart -NoBrowser }
    $second = (& $python -m omni_v2.core.runtime_cli --json status | Out-String) | ConvertFrom-Json
    Assert-True $second.ok "Status did not verify the restarted generation."
    Register-OwnedProcesses $second
    $secondPids = @($second.services | ForEach-Object { [int]$_.pid })
    Assert-True (-not (@($firstPids | Where-Object { $secondPids -contains $_ }))) "Restart reused an old PID."
    foreach ($pidValue in $firstPids) {
        Assert-True (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) "Old PID $pidValue survived restart."
    }

    Invoke-Step "Managed stop" { & $python -m omni_v2.core.runtime_cli stop }
    foreach ($pidValue in $secondPids) {
        Assert-True (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) "PID $pidValue survived stop."
    }
    Assert-True (-not (Test-Path ([string]$config.runtime_state_path))) "Runtime state survived stop."

    Invoke-Step "Safe uninstall with data preservation" { & "$root\scripts\uninstall.ps1" -Confirm:$false }
    Assert-True (-not (Test-Path "$root\.venv")) "Uninstall left .venv behind."
    Assert-True (-not (Test-Path "$root\frontend_next\node_modules")) "Uninstall left node_modules behind."
    Assert-True (-not (Test-Path "$root\frontend_next\.next")) "Uninstall left the frontend build behind."
    Assert-True (Test-Path $configPath) "Default uninstall deleted canonical user data."
    Assert-True ((Get-FileHash -Algorithm SHA256 $configPath).Hash -eq $configBefore) "Uninstall changed preserved configuration."

    Invoke-Step "Explicit user-data uninstall" { & "$root\scripts\uninstall.ps1" -RemoveUserData -Confirm:$false }
    Assert-True (-not (Test-Path $QualificationDataPath)) "Explicit user-data uninstall left canonical data behind."
    Assert-True (Test-Path "$root\pyproject.toml") "Uninstall damaged the source checkout."
    Invoke-Step "Idempotent second uninstall" { & "$root\scripts\uninstall.ps1" -RemoveUserData -Confirm:$false }
    Assert-True (-not (Test-Path $QualificationDataPath)) "Second uninstall recreated or retained canonical data."

    if ($KeepInstalled) {
        if ($null -eq $originalDataDir) {
            Remove-Item Env:OMNI_DATA_DIR -ErrorAction SilentlyContinue
        } else {
            $env:OMNI_DATA_DIR = $originalDataDir
        }
        if ($null -eq $originalApiToken) {
            Remove-Item Env:OMNI_API_TOKEN -ErrorAction SilentlyContinue
        } else {
            $env:OMNI_API_TOKEN = $originalApiToken
        }
        Invoke-Step "Restore installation with the operator's normal data path" { & "$root\scripts\install.ps1" @installArguments }
    }

    Assert-True ($recordedProcessObservations -eq 8) "Lifecycle did not record exactly two services across all four status observations."
    Assert-True ($recordedProcesses.Count -eq 6) "Lifecycle did not prove exactly three distinct two-service process generations."

    $evidence = [ordered]@{
        schema_version = 2
        batch = "B02"
        status = "pass"
        commit_sha = $commitSha
        completed_at_utc = [DateTime]::UtcNow.ToString("o")
        platform = [ordered]@{
            os = "Windows"
            caption = $windowsPlatform.Caption
            version = $windowsPlatform.Version
            build = $windowsPlatform.Build
            product_type = $windowsPlatform.ProductType
            architecture = $windowsPlatform.Architecture
            architecture_slug = $architectureSlug
            qualification_role = if ($architectureSlug -eq "arm64") { "primary-target-equivalent" } else { "secondary-hardware-independent" }
        }
        tools = [ordered]@{
            python = $pythonMetadata
            node = [ordered]@{ version = $nodeVersion; architecture = $nodeArchitecture }
            corepack = $corepackVersion
            npm = $npmVersion
            powershell = $PSVersionTable.PSVersion.ToString()
        }
        artifacts = [ordered]@{
            core_lock = [IO.Path]::GetFileName($LockPath)
            core_lock_sha256 = (Get-FileHash -Algorithm SHA256 $LockPath).Hash.ToLowerInvariant()
            build_lock = [IO.Path]::GetFileName($buildLockPath)
            build_lock_sha256 = (Get-FileHash -Algorithm SHA256 $buildLockPath).Hash.ToLowerInvariant()
            resolver_evidence = [IO.Path]::GetFileName($ResolutionPath)
            resolver_evidence_sha256 = (Get-FileHash -Algorithm SHA256 $ResolutionPath).Hash.ToLowerInvariant()
            transcript = [IO.Path]::GetFileName($transcriptPath)
        }
        assertions = @(
            "native all-profile dependency resolution with exact hashed core and build locks",
            "native Visual Studio compiler/linker/SDK preflight before source installation",
            "fresh isolated-worktree installation",
            "canonical configuration initialization with environment-only API secret",
            "managed backend and frontend readiness plus authenticated ticket issuance",
            "second install while running stops owned PIDs and preserves configuration",
            "second start preserves an already healthy generation",
            "restart replaces owned PIDs",
            "stop removes owned process tree and state",
            "default uninstall removes generated assets and preserves user data",
            "explicit user-data uninstall removes only validated canonical data",
            "second uninstall is idempotent and leaves the source checkout intact"
        )
        qualification_data_removed = $true
        cleanup_passed = $false
        recorded_process_count = $recordedProcesses.Count
        recorded_process_observations = $recordedProcessObservations
        restored_installation = [bool]$KeepInstalled
    }
    $evidencePath = Join-Path $EvidenceDirectory "$evidencePrefix.json"
    $evidence | ConvertTo-Json -Depth 7 | Set-Content -Path $evidencePath -Encoding UTF8

} catch {
    $qualificationError = $_
    Write-Host "`nQualification failed: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    # Cleanup is a qualification invariant, including when an earlier assertion
    # fails. Always target the isolated data root before attempting managed stop.
    $env:OMNI_DATA_DIR = $QualificationDataPath
    $runtimePython = Join-Path $root ".venv\Scripts\python.exe"
    $runtimeStatePath = Join-Path $QualificationDataPath "run\runtime.json"
    if ((Test-Path -LiteralPath $runtimeStatePath) -or $recordedProcesses.Count -gt 0) {
        if (Test-Path -LiteralPath $runtimePython -PathType Leaf) {
            try {
                & $runtimePython -m omni_v2.core.runtime_cli --json stop | Out-Host
                if ($LASTEXITCODE -ne 0) {
                    [void]$cleanupErrors.Add("managed runtime stop failed with exit code $LASTEXITCODE")
                }
            } catch {
                [void]$cleanupErrors.Add("managed runtime stop raised an error: $($_.Exception.Message)")
            }
        } elseif (Test-Path -LiteralPath $runtimeStatePath) {
            [void]$cleanupErrors.Add("runtime state exists but the managed Python interpreter is absent")
        }
    }

    # A failed stop must not strand a process whose exact PID/start-time/path
    # identity was observed from managed lifecycle status.
    foreach ($identity in @($recordedProcesses.Values)) {
        if (Test-RecordedProcessIdentity $identity) {
            try {
                Stop-Process -Id ([int]$identity.pid) -Force -ErrorAction Stop
                Wait-Process -Id ([int]$identity.pid) -Timeout 10 -ErrorAction SilentlyContinue
            } catch {
                [void]$cleanupErrors.Add("could not force-stop recorded PID $($identity.pid): $($_.Exception.Message)")
            }
        }
        if (Test-RecordedProcessIdentity $identity) {
            [void]$cleanupErrors.Add("recorded PID $($identity.pid) survived cleanup")
        }
    }

    if (-not $KeepInstalled -or $null -ne $qualificationError) {
        Remove-GeneratedPath (Join-Path $root ".venv") "generated Python environment"
        Remove-GeneratedPath (Join-Path $root "frontend_next\node_modules") "generated frontend dependency tree"
        Remove-GeneratedPath (Join-Path $root "frontend_next\.next") "generated frontend build"
        Remove-GeneratedPath (Join-Path $root "frontend_next\out") "generated frontend export"
    }
    Remove-GeneratedPath $QualificationDataPath "isolated qualification data"
    if (Test-Path -LiteralPath $runtimeStatePath) {
        [void]$cleanupErrors.Add("managed runtime state survived cleanup: $runtimeStatePath")
    }

    if ($null -eq $originalDataDir) {
        Remove-Item Env:OMNI_DATA_DIR -ErrorAction SilentlyContinue
    } else {
        $env:OMNI_DATA_DIR = $originalDataDir
    }
    if ($null -eq $originalApiToken) {
        Remove-Item Env:OMNI_API_TOKEN -ErrorAction SilentlyContinue
    } else {
        $env:OMNI_API_TOKEN = $originalApiToken
    }
    if ($null -ne $qualificationError -or $cleanupErrors.Count -gt 0) {
        Remove-Item -LiteralPath $evidencePath -Force -ErrorAction SilentlyContinue
    }
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}

if ($cleanupErrors.Count -gt 0) {
    $primaryDetail = if ($null -ne $qualificationError) { " Primary failure: $($qualificationError.Exception.Message)" } else { "" }
    throw "Qualification cleanup failed: $($cleanupErrors -join ';').$primaryDetail"
}
if ($null -ne $qualificationError) {
    throw $qualificationError
}
$completedEvidence = (Get-Content -Raw -LiteralPath $evidencePath) | ConvertFrom-Json
$completedEvidence.cleanup_passed = $true
$completedEvidence | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $evidencePath -Encoding UTF8
Write-Host "`nB02 Windows $architectureSlug install/start/stop/restart/second-install/uninstall qualification: PASS"
Write-Host "Evidence: $evidencePath"
