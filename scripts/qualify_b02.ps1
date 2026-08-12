# Unattended B02 native-Windows qualification and fail-closed matrix verdict.
#
# Default: qualify this native lane from an isolated detached worktree, preserve
# evidence outside it, then evaluate the complete Arm64/x64 matrix.
# -LaneOnly is for CI matrix jobs. -AggregateOnly evaluates downloaded lanes.

[CmdletBinding()]
param(
    [string]$CommitSha,
    [string]$EvidenceRoot,
    [string]$PythonPath,
    [switch]$LaneOnly,
    [switch]$AggregateOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0
$sourceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $sourceRoot

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Get-FileSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Invoke-NativeStep {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "`n=== $Name ==="
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

function Invoke-NativeJsonStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )
    Write-Host "`n=== $Name ==="
    $output = (& $FilePath @Arguments | Out-String)
    $exitCode = $LASTEXITCODE
    $output | Set-Content -LiteralPath $OutputPath -Encoding UTF8
    Write-Host "Captured JSON: $OutputPath"
    if ($exitCode -ne 0) { throw "$Name failed with exit code $exitCode" }
    try {
        $null = $output | ConvertFrom-Json
    } catch {
        throw "$Name did not emit valid JSON: $($_.Exception.Message)"
    }
}

function Write-JsonFile {
    param([Parameter(Mandatory = $true)]$Value, [Parameter(Mandatory = $true)][string]$Path)
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $Value | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Resolve-ExactCommit {
    param([string]$Requested)
    $candidate = if ($Requested) { $Requested } else { (& git rev-parse HEAD).Trim() }
    & git cat-file -e "$candidate^{commit}" 2>$null
    Assert-True ($LASTEXITCODE -eq 0) "Commit does not identify a local Git commit: $candidate"
    $resolved = (& git rev-parse "$candidate^{commit}").Trim()
    Assert-True ($LASTEXITCODE -eq 0 -and $resolved -match "^[0-9a-f]{40}$") "Could not resolve exact commit: $candidate"
    return $resolved
}

function Test-ObjectProperty {
    param($Value, [string]$Name)
    return $null -ne $Value -and $null -ne $Value.PSObject.Properties[$Name]
}

function Test-LaneArtifacts {
    param($Lane, [string]$LaneJsonPath, [string]$ExpectedCommit)

    $errors = [System.Collections.Generic.List[string]]::new()
    $laneDirectory = Split-Path -Parent $LaneJsonPath
    $architecture = [string]$Lane.platform.architecture_slug
    $profiles = @("core", "voice", "vision", "desktop", "dev", "all")
    $requiredChecks = @(
        "detached_exact_commit",
        "all_profile_resolution",
        "repeatable_exact_hashed_locks",
        "isolated_exact_dev_install_pip_check_and_audits",
        "isolated_exact_all_install_pip_check",
        "configured_python_suite_configuration_governance_ruff_compile",
        "wheel_sdist_package_tests_contents_and_metadata",
        "frontend_ci_install_script_tree_audit_proxy_lint_build",
        "native_install_lifecycle_uninstall",
        "tracked_source_unchanged"
    )

    if ([int]$Lane.schema_version -ne 2) { [void]$errors.Add("lane schema_version is not 2") }
    if ($Lane.batch -ne "B02") { [void]$errors.Add("lane batch is not B02") }
    if ($Lane.status -ne "pass") { [void]$errors.Add("lane status is not pass") }
    if ($Lane.commit_sha -ne $ExpectedCommit) { [void]$errors.Add("lane commit does not match $ExpectedCommit") }
    if ($architecture -notin @("arm64", "x86_64")) {
        [void]$errors.Add("lane architecture is not native Arm64 or x64")
    }
    if ([int]$Lane.platform.windows_build -lt 22000 -or [int]$Lane.platform.windows_product_type -ne 1) {
        [void]$errors.Add("lane is not Windows 11 workstation evidence")
    }
    $expectedRole = if ($architecture -eq "arm64") { "primary-target-equivalent" } else { "secondary-hardware-independent" }
    if ([string]$Lane.platform.qualification_role -ne $expectedRole) {
        [void]$errors.Add("lane qualification role is invalid")
    }
    if ([string]$Lane.platform.powershell_process_architecture -ne $architecture) {
        [void]$errors.Add("PowerShell process architecture does not match the native lane")
    }
    if ([string]$Lane.tools.python_implementation -ne "CPython" -or -not ([string]$Lane.tools.python_version).StartsWith("3.11.")) {
        [void]$errors.Add("lane did not use CPython 3.11")
    }
    $pythonMachine = ([string]$Lane.tools.python_machine).ToLowerInvariant()
    if ($pythonMachine -eq "amd64") { $pythonMachine = "x86_64" }
    if ($pythonMachine -eq "aarch64") { $pythonMachine = "arm64" }
    if ($pythonMachine -ne $architecture) {
        [void]$errors.Add("Python architecture does not match the native lane")
    }
    if ([string]$Lane.tools.node_architecture -ne $architecture) {
        [void]$errors.Add("Node.js architecture does not match the native lane")
    }
    try {
        $nodeVersion = [version](([string]$Lane.tools.node_version).TrimStart("v"))
        if ($nodeVersion.Major -ne 22 -or $nodeVersion -lt [version]"22.22.2") {
            [void]$errors.Add("Node.js is outside >=22.22.2,<23")
        }
    } catch {
        [void]$errors.Add("Node.js version cannot be parsed")
    }
    if ([string]$Lane.tools.npm_version -ne "12.0.2") {
        [void]$errors.Add("lane did not use exact npm 12.0.2")
    }
    if (-not [bool]$Lane.cleanup_passed) { [void]$errors.Add("lane cleanup did not pass") }

    $actualChecks = @($Lane.checks_passed | ForEach-Object { [string]$_ })
    foreach ($requiredCheck in $requiredChecks) {
        if ($actualChecks -notcontains $requiredCheck) { [void]$errors.Add("missing passing check: $requiredCheck") }
    }
    if ($actualChecks.Count -ne $requiredChecks.Count -or @($actualChecks | Select-Object -Unique).Count -ne $actualChecks.Count) {
        [void]$errors.Add("passing-check set is incomplete, duplicated, or unexpected")
    }

    $packagePaths = @($Lane.package_artifacts | ForEach-Object { [string]$_ })
    if ($packagePaths.Count -ne 2) {
        [void]$errors.Add("lane must preserve exactly one wheel and one source distribution")
    } else {
        if (@($packagePaths | Where-Object { $_ -match "^packages/omni_agi-[0-9.]+-py3-none-any[.]whl$" }).Count -ne 1) {
            [void]$errors.Add("lane package artifacts omit the expected wheel")
        }
        if (@($packagePaths | Where-Object { $_ -match "^packages/omni_agi-[0-9.]+[.]tar[.]gz$" }).Count -ne 1) {
            [void]$errors.Add("lane package artifacts omit the expected source distribution")
        }
    }

    $expectedArtifactPaths = [System.Collections.Generic.List[string]]::new()
    [void]$expectedArtifactPaths.Add("cpython-3.11-windows-$architecture-profile-resolution.json")
    foreach ($profile in $profiles) {
        [void]$expectedArtifactPaths.Add("locks/cpython-3.11-windows-$architecture/$profile.txt")
    }
    foreach ($path in @(
        "python-vulnerability-audit.json",
        "python-license-inventory.json",
        "frontend-install-scripts.json",
        "frontend-dependency-tree.json",
        "frontend-vulnerability-audit.json",
        "windows-$architecture-install-qualification.json",
        "windows-$architecture-install-qualification.log",
        "windows-$architecture-qualification.log"
    )) {
        [void]$expectedArtifactPaths.Add($path)
    }
    foreach ($path in $packagePaths) { [void]$expectedArtifactPaths.Add($path) }

    $artifactByPath = @{}
    foreach ($artifact in @($Lane.artifacts)) {
        $relative = ([string]$artifact.path).Replace("\", "/")
        if ($artifactByPath.ContainsKey($relative)) {
            [void]$errors.Add("duplicate artifact entry: $relative")
            continue
        }
        $artifactByPath[$relative] = $artifact
        if ($expectedArtifactPaths -notcontains $relative) {
            [void]$errors.Add("unexpected artifact entry: $relative")
            continue
        }
        $full = [IO.Path]::GetFullPath((Join-Path $laneDirectory $relative.Replace("/", "\")))
        $lanePrefix = [IO.Path]::GetFullPath($laneDirectory).TrimEnd("\") + "\"
        if (-not $full.StartsWith($lanePrefix, [StringComparison]::OrdinalIgnoreCase)) {
            [void]$errors.Add("artifact escapes lane directory: $relative")
        } elseif (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            [void]$errors.Add("missing artifact: $relative")
        } elseif ([string]$artifact.sha256 -notmatch "^[0-9a-f]{64}$") {
            [void]$errors.Add("artifact digest is malformed: $relative")
        } elseif ((Get-FileSha256 $full) -ne [string]$artifact.sha256) {
            [void]$errors.Add("artifact digest mismatch: $relative")
        }
    }
    foreach ($expectedPath in $expectedArtifactPaths) {
        if (-not $artifactByPath.ContainsKey($expectedPath)) { [void]$errors.Add("artifact entry is absent: $expectedPath") }
    }
    if ($artifactByPath.Count -ne $expectedArtifactPaths.Count) {
        [void]$errors.Add("artifact manifest cardinality is invalid")
    }

    foreach ($profile in $profiles) {
        $lockRelative = "locks/cpython-3.11-windows-$architecture/$profile.txt"
        if (-not (Test-ObjectProperty $Lane.repeated_lock_sha256 $profile)) {
            [void]$errors.Add("repeated-lock digest is absent for $profile")
        } elseif ($artifactByPath.ContainsKey($lockRelative)) {
            $repeatedDigest = [string]$Lane.repeated_lock_sha256.PSObject.Properties[$profile].Value
            if ($repeatedDigest -ne [string]$artifactByPath[$lockRelative].sha256) {
                [void]$errors.Add("repeated-lock digest does not match artifact for $profile")
            }
        }
    }

    $lifecycleRelative = "windows-$architecture-install-qualification.json"
    $lifecyclePath = Join-Path $laneDirectory $lifecycleRelative
    if (Test-Path -LiteralPath $lifecyclePath -PathType Leaf) {
        try {
            $lifecycle = (Get-Content -Raw -LiteralPath $lifecyclePath) | ConvertFrom-Json
            if ([int]$lifecycle.schema_version -ne 2 -or $lifecycle.status -ne "pass" -or $lifecycle.commit_sha -ne $ExpectedCommit) {
                [void]$errors.Add("lifecycle evidence schema, status, or commit is invalid")
            }
            if ([string]$lifecycle.platform.architecture_slug -ne $architecture) {
                [void]$errors.Add("lifecycle architecture does not match lane architecture")
            }
            if ([int]$lifecycle.platform.build -lt 22000 -or [int]$lifecycle.platform.product_type -ne 1) {
                [void]$errors.Add("lifecycle did not run on a Windows 11 workstation")
            }
            $lifecyclePythonMachine = ([string]$lifecycle.tools.python.architecture).ToLowerInvariant()
            if ($lifecyclePythonMachine -eq "amd64") { $lifecyclePythonMachine = "x86_64" }
            if ($lifecyclePythonMachine -eq "aarch64") { $lifecyclePythonMachine = "arm64" }
            if ($lifecyclePythonMachine -ne $architecture -or [string]$lifecycle.tools.npm -ne "12.0.2") {
                [void]$errors.Add("lifecycle toolchain architecture or npm identity is invalid")
            }
            if ([string]$lifecycle.artifacts.core_lock_sha256 -ne [string]$Lane.core_lock_sha256) {
                [void]$errors.Add("lifecycle core-lock digest does not match lane evidence")
            }
            $resolutionRelative = "cpython-3.11-windows-$architecture-profile-resolution.json"
            if ($artifactByPath.ContainsKey($resolutionRelative) -and [string]$lifecycle.artifacts.resolver_evidence_sha256 -ne [string]$artifactByPath[$resolutionRelative].sha256) {
                [void]$errors.Add("lifecycle resolver digest does not match lane evidence")
            }
            if (-not [bool]$lifecycle.qualification_data_removed) {
                [void]$errors.Add("lifecycle did not remove isolated qualification data")
            }
        } catch {
            [void]$errors.Add("lifecycle evidence cannot be parsed: $($_.Exception.Message)")
        }
    } else {
        [void]$errors.Add("lifecycle evidence is absent")
    }

    $resolutionPath = Join-Path $laneDirectory "cpython-3.11-windows-$architecture-profile-resolution.json"
    if (Test-Path -LiteralPath $resolutionPath -PathType Leaf) {
        try {
            $resolution = (Get-Content -Raw -LiteralPath $resolutionPath) | ConvertFrom-Json
            if ([int]$resolution.schema_version -ne 1 -or $resolution.status -ne "pass") {
                [void]$errors.Add("resolver evidence schema or status is invalid")
            }
            if (
                [string]$resolution.python.implementation -ne "CPython" -or
                -not ([string]$resolution.python.version).StartsWith("3.11.") -or
                -not [bool]$resolution.build_system_requirements_included
            ) {
                [void]$errors.Add("resolver interpreter or local-build contract is invalid")
            }
            if ([string]$resolution.platform.system -ne "Windows" -or [string]$resolution.platform.normalized_machine -ne $architecture) {
                [void]$errors.Add("resolver evidence platform does not match the lane")
            }
            if (
                [string]$resolution.platform.windows_os_machine -ne $architecture -or
                [int]$resolution.platform.pointer_bits -ne 64 -or
                [int]$resolution.platform.windows_product_type -ne 1 -or
                [int]$resolution.platform.windows_build -lt 22000
            ) {
                [void]$errors.Add("resolver evidence was not generated by native 64-bit Python on Windows 11 workstation")
            }
            foreach ($profile in $profiles) {
                if ($resolution.profiles.PSObject.Properties[$profile].Value.status -ne "pass") {
                    [void]$errors.Add("resolver profile is not pass: $profile")
                }
            }
        } catch {
            [void]$errors.Add("resolver evidence cannot be parsed: $($_.Exception.Message)")
        }
    }

    try {
        $installScripts = (Get-Content -Raw -LiteralPath (Join-Path $laneDirectory "frontend-install-scripts.json")) | ConvertFrom-Json
        if (-not (Test-ObjectProperty $installScripts "allowScripts") -or @($installScripts.allowScripts).Count -ne 0) {
            [void]$errors.Add("frontend has unreviewed install scripts")
        }
    } catch {
        [void]$errors.Add("frontend install-script evidence cannot be parsed: $($_.Exception.Message)")
    }
    try {
        $dependencyTree = (Get-Content -Raw -LiteralPath (Join-Path $laneDirectory "frontend-dependency-tree.json")) | ConvertFrom-Json
        if (Test-ObjectProperty $dependencyTree "problems") {
            if (@($dependencyTree.problems).Count -ne 0) { [void]$errors.Add("frontend dependency tree reports problems") }
        }
        if (-not (Test-ObjectProperty $dependencyTree "dependencies")) { [void]$errors.Add("frontend dependency tree is empty") }
    } catch {
        [void]$errors.Add("frontend dependency-tree evidence cannot be parsed: $($_.Exception.Message)")
    }
    try {
        $frontendAudit = (Get-Content -Raw -LiteralPath (Join-Path $laneDirectory "frontend-vulnerability-audit.json")) | ConvertFrom-Json
        if (
            -not (Test-ObjectProperty $frontendAudit "metadata") -or
            -not (Test-ObjectProperty $frontendAudit "vulnerabilities") -or
            [int]$frontendAudit.metadata.dependencies.total -le 0 -or
            [int]$frontendAudit.metadata.vulnerabilities.total -ne 0 -or
            @($frontendAudit.vulnerabilities.PSObject.Properties).Count -ne 0
        ) {
            [void]$errors.Add("frontend vulnerability audit is malformed or not clean")
        }
    } catch {
        [void]$errors.Add("frontend vulnerability evidence cannot be parsed: $($_.Exception.Message)")
    }
    $devLockPath = Join-Path $laneDirectory "locks\cpython-3.11-windows-$architecture\dev.txt"
    $expectedDevNames = @()
    if (Test-Path -LiteralPath $devLockPath -PathType Leaf) {
        $expectedDevNames = @(
            Get-Content -LiteralPath $devLockPath |
                ForEach-Object {
                    if ($_ -match "^([A-Za-z0-9_.-]+)==") {
                        ([string]$Matches[1]).ToLowerInvariant() -replace "[-_.]+", "-"
                    }
                }
        )
    }
    $expectedDevDistributions = $expectedDevNames.Count
    try {
        $pythonAudit = (Get-Content -Raw -LiteralPath (Join-Path $laneDirectory "python-vulnerability-audit.json")) | ConvertFrom-Json
        if (-not (Test-ObjectProperty $pythonAudit "dependencies") -or -not (Test-ObjectProperty $pythonAudit "fixes")) {
            [void]$errors.Add("Python vulnerability audit schema is incomplete")
        } else {
            $auditedDependencies = @($pythonAudit.dependencies)
            $auditedNames = @(
                $auditedDependencies |
                    ForEach-Object { (([string]$_.name).ToLowerInvariant() -replace "[-_.]+", "-") }
            )
            # pip-audit intentionally omits the packaging toolchain it uses to
            # inspect requirements. Account for that fixed boundary explicitly;
            # every other exact dev-lock distribution must appear exactly once.
            $auditToolingOmissions = @("packaging", "pip", "setuptools")
            $expectedAuditedNames = @($expectedDevNames | Where-Object { $_ -notin $auditToolingOmissions })
            if (@($auditToolingOmissions | Where-Object { $_ -notin $expectedDevNames }).Count -ne 0) {
                [void]$errors.Add("Python vulnerability audit tooling-omission contract no longer matches the exact dev lock")
            }
            $missingAuditNames = @($expectedAuditedNames | Where-Object { $_ -notin $auditedNames })
            $unexpectedAuditNames = @($auditedNames | Where-Object { $_ -notin $expectedAuditedNames })
            if (
                $expectedDevDistributions -le 0 -or
                $auditedNames.Count -ne $expectedAuditedNames.Count -or
                $missingAuditNames.Count -ne 0 -or
                $unexpectedAuditNames.Count -ne 0
            ) {
                [void]$errors.Add("Python vulnerability audit coverage does not match the exact dev lock minus explicit audit-tooling omissions")
            }
            if (@($auditedNames | Where-Object { -not $_ }).Count -ne 0 -or @($auditedNames | Select-Object -Unique).Count -ne $auditedNames.Count) {
                [void]$errors.Add("Python vulnerability audit has missing or duplicate distributions")
            }
            foreach ($dependency in $auditedDependencies) {
                if (-not (Test-ObjectProperty $dependency "vulns")) {
                    [void]$errors.Add("Python vulnerability audit dependency schema is incomplete")
                } elseif (@($dependency.vulns).Count -ne 0) {
                    [void]$errors.Add("Python vulnerability audit reports a finding")
                }
            }
            if (@($pythonAudit.fixes).Count -ne 0) { [void]$errors.Add("Python vulnerability audit reports pending fixes") }
        }
    } catch {
        [void]$errors.Add("Python vulnerability evidence cannot be parsed: $($_.Exception.Message)")
    }
    try {
        $licenseInventory = (Get-Content -Raw -LiteralPath (Join-Path $laneDirectory "python-license-inventory.json")) | ConvertFrom-Json
        if (
            $licenseInventory.status -ne "pass" -or
            [int]$licenseInventory.expected_distribution_count -ne $expectedDevDistributions -or
            [int]$licenseInventory.inventoried_distribution_count -ne $expectedDevDistributions -or
            @($licenseInventory.missing).Count -ne 0 -or
            @($licenseInventory.version_mismatches).Count -ne 0 -or
            @($licenseInventory.unknown_licenses).Count -ne 0
        ) {
            [void]$errors.Add("Python license inventory is incomplete or does not match the exact dev lock")
        }
    } catch {
        [void]$errors.Add("Python license evidence cannot be parsed: $($_.Exception.Message)")
    }

    return @($errors)
}

function Invoke-MatrixAggregate {
    param([string]$Root, [string]$ExpectedCommit)

    $laneFiles = @(Get-ChildItem -LiteralPath $Root -Recurse -File -Filter "windows-*-lane.json" -ErrorAction SilentlyContinue)
    $valid = @{}
    $evaluated = [System.Collections.Generic.List[object]]::new()
    foreach ($file in $laneFiles) {
        try {
            $lane = (Get-Content -Raw -LiteralPath $file.FullName) | ConvertFrom-Json
            $errors = @(Test-LaneArtifacts $lane $file.FullName $ExpectedCommit)
            $entry = [ordered]@{
                path = $file.FullName
                architecture = [string]$lane.platform.architecture_slug
                commit_sha = [string]$lane.commit_sha
                status = if ($errors.Count -eq 0) { "pass" } else { "invalid" }
                errors = $errors
            }
            [void]$evaluated.Add($entry)
            if ($errors.Count -eq 0) {
                $architecture = [string]$lane.platform.architecture_slug
                if ($valid.ContainsKey($architecture)) {
                    $valid[$architecture] = "ambiguous"
                } else {
                    $valid[$architecture] = $file.FullName
                }
            }
        } catch {
            [void]$evaluated.Add([ordered]@{
                path = $file.FullName
                architecture = $null
                commit_sha = $null
                status = "invalid"
                errors = @("lane evidence cannot be parsed: $($_.Exception.Message)")
            })
        }
    }

    $missing = [System.Collections.Generic.List[string]]::new()
    foreach ($required in @("arm64", "x86_64")) {
        if (-not $valid.ContainsKey($required)) {
            [void]$missing.Add($required)
        } elseif ($valid[$required] -eq "ambiguous") {
            [void]$missing.Add("$required (multiple valid lanes; aggregation is ambiguous)")
        }
    }
    # A valid pair cannot launder additional malformed, wrong-commit, failed, or
    # otherwise invalid lane files present in the evidence root. Every discovered
    # lane attestation must validate, and duplicate valid architectures remain
    # ambiguous through the missing/ambiguous check above.
    $invalidEvidence = @($evaluated | Where-Object { $_.status -ne "pass" })
    $passed = $missing.Count -eq 0 -and $invalidEvidence.Count -eq 0
    $verdict = [ordered]@{
        schema_version = 2
        batch = "B02"
        status = if ($passed) { "pass" } else { "blocked" }
        commit_sha = $ExpectedCommit
        evaluated_at_utc = [DateTime]::UtcNow.ToString("o")
        required_native_lanes = @("windows-arm64", "windows-x86_64")
        missing_or_ambiguous_lanes = @($missing)
        invalid_lane_evidence_count = $invalidEvidence.Count
        lanes = @($evaluated)
        b03_unlocked = $passed
        nonclaims = if ($passed) { @() } else { @(
            "B02 is not closed.",
            "B03 remains locked.",
            "A single native lane cannot qualify the amended Windows platform matrix."
        ) }
    }
    $verdictPath = Join-Path $Root "b02-aggregate-verdict.json"
    Write-JsonFile $verdict $verdictPath
    Write-Host "Aggregate evidence: $verdictPath"
    if ($passed) {
        Write-Host ("ALL SYSTEMS GO {0} B03 UNLOCKED" -f [char]0x2014)
        return $true
    }
    Write-Host "B02 BLOCKED - B03 REMAINS LOCKED"
    if ($missing.Count -gt 0) {
        Write-Host "Missing or ambiguous native lane(s): $($missing -join ', ')"
    }
    if ($invalidEvidence.Count -gt 0) {
        Write-Host "Invalid lane evidence file(s): $($invalidEvidence.Count)"
    }
    return $false
}

if ($LaneOnly -and $AggregateOnly) {
    throw "Choose either -LaneOnly or -AggregateOnly, not both."
}
$CommitSha = Resolve-ExactCommit $CommitSha
$sourceCommit = (& git rev-parse HEAD).Trim()
Assert-True ($LASTEXITCODE -eq 0 -and $sourceCommit -eq $CommitSha) "Qualification authority must be checked out at the exact commit under test ($CommitSha); found $sourceCommit."
& git diff --quiet HEAD "--"
Assert-True ($LASTEXITCODE -eq 0) "Qualification authority has tracked changes; commit them before evaluating a lane or aggregate verdict."
if (-not $EvidenceRoot) {
    $EvidenceRoot = Join-Path $sourceRoot "quality\evidence\B02\native"
}
New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
$EvidenceRoot = (Resolve-Path -LiteralPath $EvidenceRoot).Path

if ($AggregateOnly) {
    $matrixPassed = Invoke-MatrixAggregate $EvidenceRoot $CommitSha
    if (-not $matrixPassed) { exit 2 }
    exit 0
}

Assert-True ($env:OS -eq "Windows_NT") "B02 native lane qualification must run on Windows 11."
. (Join-Path $PSScriptRoot "windows_platform.ps1")
# Resolve the architecture before enforcing the workstation/build gate so even a
# rejected hosted Windows Server diagnostic can preserve a fail-closed lane log
# and JSON instead of disappearing before evidence initialization.
$windowsPlatform = Get-OmniWindowsPlatform
$architectureSlug = Get-OmniWindowsArchitectureSlug $windowsPlatform
$expectedPythonMachines = @(Get-OmniPythonMachineNames $windowsPlatform)
$powerShellProcessArchitecture = [System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString().ToLowerInvariant()
if ($powerShellProcessArchitecture -eq "x64") { $powerShellProcessArchitecture = "x86_64" }
Assert-True ($powerShellProcessArchitecture -eq $architectureSlug) "Qualification PowerShell must be native $architectureSlug; found $powerShellProcessArchitecture."

$laneDirectory = Join-Path $EvidenceRoot "windows-$architectureSlug"
if (Test-Path -LiteralPath $laneDirectory) {
    Remove-Item -LiteralPath $laneDirectory -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $laneDirectory | Out-Null
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) "omni-b02-$architectureSlug-$PID-$([Guid]::NewGuid().ToString('N'))"
$worktree = Join-Path $tempRoot "source"
$devVenv = Join-Path $tempRoot "dev-venv"
$allVenv = Join-Path $tempRoot "all-venv"
$repeatRoot = Join-Path $tempRoot "repeat-resolution"
$qualificationData = Join-Path $tempRoot "qualification-data"
$packageDirectory = Join-Path $worktree "dist"
$packageEvidenceDirectory = Join-Path $laneDirectory "packages"
$laneJsonPath = Join-Path $laneDirectory "windows-$architectureSlug-lane.json"
$transcriptPath = Join-Path $laneDirectory "windows-$architectureSlug-qualification.log"
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

$worktreeAdded = $false
$lanePassed = $false
$cleanupPassed = $true
$failureMessage = $null
$transcriptStarted = $false
$checks = [System.Collections.Generic.List[string]]::new()
$profileHashes = [ordered]@{}
$packageEvidencePaths = [System.Collections.Generic.List[string]]::new()
$resolutionPath = Join-Path $laneDirectory "cpython-3.11-windows-$architectureSlug-profile-resolution.json"
$lockDirectory = Join-Path $laneDirectory "locks\cpython-3.11-windows-$architectureSlug"
$lifecycleEvidenceName = "windows-$architectureSlug-install-qualification.json"
$lifecycleEvidencePath = Join-Path $laneDirectory $lifecycleEvidenceName
$pythonAuditPath = Join-Path $laneDirectory "python-vulnerability-audit.json"
$licenseInventoryPath = Join-Path $laneDirectory "python-license-inventory.json"
$frontendInstallScriptsPath = Join-Path $laneDirectory "frontend-install-scripts.json"
$frontendTreePath = Join-Path $laneDirectory "frontend-dependency-tree.json"
$frontendAuditPath = Join-Path $laneDirectory "frontend-vulnerability-audit.json"
$selectedPython = $null
$pythonImplementation = $null
$pythonVersion = $null
$pythonMachine = $null
$nodeVersion = $null
$nodeArchitecture = $null
$npmVersion = $null
$powerShellExecutable = (Get-Process -Id $PID).Path

try {
    Start-Transcript -Path $transcriptPath -Force | Out-Null
    $transcriptStarted = $true

    # Re-query through the shared assertion after evidence capture is active.
    # This rejects standard windows-latest server images while retaining the
    # diagnostic artifact that explains why they cannot replace the x64 laptop.
    $windowsPlatform = Assert-OmniWindows11

    & git diff --quiet HEAD "--"
    Assert-True ($LASTEXITCODE -eq 0) "The invoking checkout has tracked changes. Commit them before exact-commit qualification."

    if ($PythonPath) {
        $selectedPython = (Resolve-Path -LiteralPath $PythonPath -ErrorAction Stop).Path
    } else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        $selectedPython = if ($pythonCommand) { $pythonCommand.Source } else { $null }
        if (-not $selectedPython) {
            $launcher = Get-Command py -ErrorAction SilentlyContinue
            Assert-True ($null -ne $launcher) "Native CPython 3.11 was not found on PATH and the py launcher is absent."
            $selectedPython = (& $launcher.Source -3.11 -c "import sys; print(sys.executable)").Trim()
            Assert-True ($LASTEXITCODE -eq 0) "The py launcher does not expose CPython 3.11."
        }
    }
    $pythonProbe = ((& $selectedPython -c "import json, platform, struct; print(json.dumps({'implementation': platform.python_implementation(), 'version': platform.python_version(), 'machine': platform.machine().lower(), 'bits': struct.calcsize('P') * 8}))" | Out-String) | ConvertFrom-Json)
    Assert-True ($LASTEXITCODE -eq 0) "Could not inspect selected Python: $selectedPython"
    $pythonImplementation = [string]$pythonProbe.implementation
    $pythonVersion = [string]$pythonProbe.version
    $pythonMachine = [string]$pythonProbe.machine
    Assert-True ($pythonImplementation -eq "CPython" -and $pythonVersion.StartsWith("3.11.") -and [int]$pythonProbe.bits -eq 64 -and $pythonMachine -in $expectedPythonMachines) "Selected Python is not native 64-bit CPython 3.11 $($windowsPlatform.Architecture)."

    $nodeCommand = Get-Command node -ErrorAction Stop
    $nodeVersion = (& $nodeCommand.Source --version).Trim()
    $nodeArchitecture = (& $nodeCommand.Source -p "process.arch").Trim().ToLowerInvariant()
    if ($nodeArchitecture -eq "x64") { $nodeArchitecture = "x86_64" }
    Assert-True ($LASTEXITCODE -eq 0 -and $nodeArchitecture -eq $architectureSlug) "Node.js must be native $architectureSlug; found $nodeArchitecture."
    $parsedNodeVersion = [version]$nodeVersion.TrimStart("v")
    Assert-True ($parsedNodeVersion.Major -eq 22 -and $parsedNodeVersion -ge [version]"22.22.2") "Node.js >=22.22.2,<23 is required; found $nodeVersion."
    $corepackCommand = Get-Command corepack -ErrorAction Stop
    $npmVersion = (& $corepackCommand.Source "npm@12.0.2" --version).Trim()
    Assert-True ($LASTEXITCODE -eq 0 -and $npmVersion -eq "12.0.2") "Corepack could not provide exact npm 12.0.2."

    Invoke-NativeStep "Create detached worktree at exact commit $CommitSha" {
        & git worktree add --detach $worktree $CommitSha
    }
    $worktreeAdded = $true
    $worktreeCommit = (& git -C $worktree rev-parse HEAD).Trim()
    Assert-True ($worktreeCommit -eq $CommitSha) "Detached worktree commit drifted."
    [void]$checks.Add("detached_exact_commit")

    $resolver = Join-Path $worktree "scripts\resolve_profiles.py"
    Invoke-NativeStep "Resolve all six native dependency profiles" {
        & $selectedPython $resolver --output $resolutionPath --lock-dir $lockDirectory
    }
    [void]$checks.Add("all_profile_resolution")

    $repeatOutput = Join-Path $repeatRoot "profile-resolution.json"
    $repeatLocks = Join-Path $repeatRoot "locks"
    Invoke-NativeStep "Repeat native dependency resolution" {
        & $selectedPython $resolver --output $repeatOutput --lock-dir $repeatLocks
    }
    $firstResolution = (Get-Content -Raw -LiteralPath $resolutionPath) | ConvertFrom-Json
    $repeatResolution = (Get-Content -Raw -LiteralPath $repeatOutput) | ConvertFrom-Json
    Assert-True (($firstResolution.profiles | ConvertTo-Json -Depth 10 -Compress) -eq ($repeatResolution.profiles | ConvertTo-Json -Depth 10 -Compress)) "Repeated resolver package graph drifted."
    foreach ($profile in @("core", "voice", "vision", "desktop", "dev", "all")) {
        $firstLock = Join-Path $lockDirectory "$profile.txt"
        $secondLock = Join-Path $repeatLocks "$profile.txt"
        Assert-True ((Get-FileSha256 $firstLock) -eq (Get-FileSha256 $secondLock)) "Repeated $profile lock bytes drifted."
        $profileHashes[$profile] = Get-FileSha256 $firstLock
    }
    [void]$checks.Add("repeatable_exact_hashed_locks")

    Invoke-NativeStep "Create isolated dev environment" { & $selectedPython -m venv $devVenv }
    $devPython = Join-Path $devVenv "Scripts\python.exe"
    $devLock = Join-Path $lockDirectory "dev.txt"
    Invoke-NativeStep "Install exact native dev lock" {
        & $devPython -m pip install --disable-pip-version-check --require-hashes -r $devLock
    }
    Invoke-NativeStep "Install exact local source without dependency resolution" {
        & $devPython -m pip install --disable-pip-version-check --no-build-isolation --no-deps $worktree
    }
    Invoke-NativeStep "Check installed dependency consistency" { & $devPython -m pip check }
    Invoke-NativeJsonStep "Audit exact native Python dev lock" $devPython @(
        "-m", "pip_audit", "--require-hashes", "-r", $devLock, "--format", "json"
    ) $pythonAuditPath
    Invoke-NativeStep "Inventory exact native Python dev-lock licenses" {
        & $devPython (Join-Path $worktree "scripts\audit_python_licenses.py") $devLock --output $licenseInventoryPath | Out-Null
    }
    [void]$checks.Add("isolated_exact_dev_install_pip_check_and_audits")

    Invoke-NativeStep "Create isolated all-runtime environment" { & $selectedPython -m venv $allVenv }
    $allPython = Join-Path $allVenv "Scripts\python.exe"
    $allLock = Join-Path $lockDirectory "all.txt"
    Invoke-NativeStep "Install exact native all-runtime lock" {
        & $allPython -m pip install --disable-pip-version-check --require-hashes -r $allLock
    }
    Invoke-NativeStep "Install exact local source in all-runtime environment without dependency resolution" {
        & $allPython -m pip install --disable-pip-version-check --no-build-isolation --no-deps $worktree
    }
    Invoke-NativeStep "Check installed all-runtime dependency consistency" { & $allPython -m pip check }
    $allSitePackages = (& $allPython -c "import sysconfig; print(sysconfig.get_paths()['purelib'])").Trim()
    Assert-True ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $allSitePackages -PathType Container)) "Could not locate the exact all-runtime environment's site-packages directory."
    [void]$checks.Add("isolated_exact_all_install_pip_check")

    Invoke-NativeStep "Run B02 install and lifecycle Python tests" {
        Push-Location $worktree
        try { & $devPython -m pytest -q (Join-Path $worktree "tests\install") }
        finally { Pop-Location }
    }
    Invoke-NativeStep "Run configured OMNI Python tests against exact all-runtime dependencies" {
        $oldPythonPath = $env:PYTHONPATH
        try {
            $env:PYTHONPATH = if ($null -eq $oldPythonPath) {
                $allSitePackages
            } else {
                "$allSitePackages$([IO.Path]::PathSeparator)$oldPythonPath"
            }
            Push-Location $worktree
            try { & $devPython -m pytest -q (Join-Path $worktree "omni_v2\tests") }
            finally { Pop-Location }
        } finally {
            if ($null -eq $oldPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $oldPythonPath }
        }
    }
    Invoke-NativeStep "Run centralized configuration contract" {
        Push-Location $worktree
        try { & $devPython (Join-Path $worktree "scripts\verify_config_contract.py") }
        finally { Pop-Location }
    }
    Invoke-NativeStep "Check governed authority and generated-document consistency" {
        Push-Location $worktree
        try { & $devPython (Join-Path $worktree "scripts\quality_baseline.py") check }
        finally { Pop-Location }
    }
    Invoke-NativeStep "Run adversarial governance validator self-test" {
        Push-Location $worktree
        try { & $devPython (Join-Path $worktree "scripts\quality_baseline_selftest.py") }
        finally { Pop-Location }
    }
    Invoke-NativeStep "Run fatal Ruff gate" {
        Push-Location $worktree
        try { & $devPython -m ruff check --select "E9,F63,F7,F82" omni backend_fastapi omni_v2 scripts tests }
        finally { Pop-Location }
    }
    Invoke-NativeStep "Compile Python source and test surfaces" {
        & $devPython -m compileall -q (Join-Path $worktree "omni") (Join-Path $worktree "omni_v2") (Join-Path $worktree "backend_fastapi") (Join-Path $worktree "tests") (Join-Path $worktree "scripts")
    }
    [void]$checks.Add("configured_python_suite_configuration_governance_ruff_compile")

    New-Item -ItemType Directory -Force -Path $packageDirectory | Out-Null
    Invoke-NativeStep "Build wheel and source distribution without an isolated dependency resolution" {
        Push-Location $worktree
        try { & $devPython -m build --no-isolation --outdir $packageDirectory }
        finally { Pop-Location }
    }
    $packageArtifacts = @(Get-ChildItem -LiteralPath $packageDirectory -File)
    Assert-True ($packageArtifacts.Count -eq 2) "Package build must emit exactly one wheel and one source distribution."
    Assert-True (@($packageArtifacts | Where-Object { $_.Name -like "*.whl" }).Count -eq 1) "Package build did not emit exactly one wheel."
    Assert-True (@($packageArtifacts | Where-Object { $_.Name -like "*.tar.gz" }).Count -eq 1) "Package build did not emit exactly one source distribution."
    Invoke-NativeStep "Run package tests against built artifacts and the exact build backend" {
        $oldExactBuildLock = $env:OMNI_EXACT_BUILD_LOCK
        try {
            $env:OMNI_EXACT_BUILD_LOCK = $devLock
            Push-Location $worktree
            try { & $devPython -m pytest -q (Join-Path $worktree "tests\package") }
            finally { Pop-Location }
        } finally {
            if ($null -eq $oldExactBuildLock) { Remove-Item Env:OMNI_EXACT_BUILD_LOCK -ErrorAction SilentlyContinue } else { $env:OMNI_EXACT_BUILD_LOCK = $oldExactBuildLock }
        }
    }
    Invoke-NativeStep "Check package contents" {
        & $devPython (Join-Path $worktree "scripts\check_package_contents.py") @($packageArtifacts.FullName)
    }
    Invoke-NativeStep "Check package metadata" {
        & $devPython -m twine check @($packageArtifacts.FullName)
    }
    New-Item -ItemType Directory -Force -Path $packageEvidenceDirectory | Out-Null
    foreach ($packageArtifact in $packageArtifacts) {
        Copy-Item -LiteralPath $packageArtifact.FullName -Destination $packageEvidenceDirectory
        [void]$packageEvidencePaths.Add("packages/$($packageArtifact.Name)")
    }
    [void]$checks.Add("wheel_sdist_package_tests_contents_and_metadata")

    $frontend = Join-Path $worktree "frontend_next"
    Push-Location $frontend
    try {
        Invoke-NativeStep "Install exact frontend lock" { & $corepackCommand.Source "npm@12.0.2" ci }
        Invoke-NativeJsonStep "Inspect unreviewed frontend install scripts" $corepackCommand.Source @(
            "npm@12.0.2", "install-scripts", "ls", "--json"
        ) $frontendInstallScriptsPath
        $installScripts = (Get-Content -Raw -LiteralPath $frontendInstallScriptsPath) | ConvertFrom-Json
        Assert-True ((Test-ObjectProperty $installScripts "allowScripts") -and @($installScripts.allowScripts).Count -eq 0) "npm reports unreviewed install scripts."
        Invoke-NativeJsonStep "Validate complete frontend dependency tree" $corepackCommand.Source @(
            "npm@12.0.2", "ls", "--all", "--json"
        ) $frontendTreePath
        Invoke-NativeJsonStep "Audit exact frontend lock" $corepackCommand.Source @(
            "npm@12.0.2", "audit", "--audit-level=low", "--json"
        ) $frontendAuditPath
        Invoke-NativeStep "Run frontend proxy tests" { & $corepackCommand.Source "npm@12.0.2" run "test:proxy" }
        Invoke-NativeStep "Run frontend lint" { & $corepackCommand.Source "npm@12.0.2" run lint }
        $oldBackendUrl = $env:OMNI_BACKEND_URL
        try {
            $env:OMNI_BACKEND_URL = "http://127.0.0.1:8765"
            Invoke-NativeStep "Build frontend production bundle" { & $corepackCommand.Source "npm@12.0.2" run build }
        } finally {
            if ($null -eq $oldBackendUrl) { Remove-Item Env:OMNI_BACKEND_URL -ErrorAction SilentlyContinue } else { $env:OMNI_BACKEND_URL = $oldBackendUrl }
        }
    } finally {
        Pop-Location
    }
    [void]$checks.Add("frontend_ci_install_script_tree_audit_proxy_lint_build")

    Remove-Item -LiteralPath (Join-Path $frontend "node_modules") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $frontend ".next") -Recurse -Force -ErrorAction SilentlyContinue
    $verifierArguments = @(
        "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $worktree "scripts\verify_windows_install.ps1"),
        "-PythonPath", $selectedPython,
        "-LockPath", (Join-Path $lockDirectory "core.txt"),
        "-ResolutionPath", $resolutionPath,
        "-EvidenceDirectory", $laneDirectory,
        "-QualificationDataPath", $qualificationData
    )
    Invoke-NativeStep "Run full install/start/readiness/restart/stop/uninstall lifecycle" {
        & $powerShellExecutable @verifierArguments
    }
    Assert-True (Test-Path -LiteralPath $lifecycleEvidencePath -PathType Leaf) "Lifecycle verifier did not emit passing evidence."
    [void]$checks.Add("native_install_lifecycle_uninstall")

    & git -C $worktree diff --quiet HEAD "--"
    Assert-True ($LASTEXITCODE -eq 0) "Qualification modified tracked source in the detached worktree."
    [void]$checks.Add("tracked_source_unchanged")
    $lanePassed = $true
} catch {
    $failureMessage = $_.Exception.Message
    Write-Error "B02 Windows $architectureSlug lane failed: $failureMessage" -ErrorAction Continue
} finally {
    try {
        $managedPython = Join-Path $worktree ".venv\Scripts\python.exe"
        if (Test-Path -LiteralPath $managedPython) {
            & $managedPython -m omni_v2.core.runtime_cli stop 2>$null | Out-Null
        }
        $statePath = Join-Path $qualificationData "run\runtime.json"
        if (Test-Path -LiteralPath $statePath) {
            try {
                $state = (Get-Content -Raw -LiteralPath $statePath) | ConvertFrom-Json
                foreach ($service in @($state.services)) {
                    if ($service.pid) { & taskkill.exe /PID ([string]$service.pid) /T /F 2>$null | Out-Null }
                }
            } catch { }
        }
        foreach ($process in @(Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue)) {
            $name = ([string]$process.Name).ToLowerInvariant()
            $commandLine = [string]$process.CommandLine
            if (
                [int]$process.ProcessId -ne $PID -and
                $name -in @("node.exe", "python.exe", "pythonw.exe") -and
                $commandLine -and
                (
                    $commandLine.IndexOf($worktree, [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                    $commandLine.IndexOf($qualificationData, [StringComparison]::OrdinalIgnoreCase) -ge 0
                )
            ) {
                & taskkill.exe /PID ([string]$process.ProcessId) /T /F 2>$null | Out-Null
            }
        }
        foreach ($generated in @(
            (Join-Path $worktree ".venv"),
            (Join-Path $worktree "frontend_next\node_modules"),
            (Join-Path $worktree "frontend_next\.next"),
            $qualificationData
        )) {
            if (Test-Path -LiteralPath $generated) { Remove-Item -LiteralPath $generated -Recurse -Force }
        }
        if ($worktreeAdded) {
            & git worktree remove --force $worktree 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git worktree remove failed with exit code $LASTEXITCODE" }
        }
        & git worktree prune
        if ($LASTEXITCODE -ne 0) { throw "git worktree prune failed with exit code $LASTEXITCODE" }
        if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
    } catch {
        $cleanupPassed = $false
        $cleanupFailure = $_.Exception.Message
        if ($failureMessage) { $failureMessage = "$failureMessage; cleanup failed: $cleanupFailure" } else { $failureMessage = "cleanup failed: $cleanupFailure" }
        Write-Error $cleanupFailure -ErrorAction Continue
    }
    if ($transcriptStarted) {
        try {
            Stop-Transcript | Out-Null
        } catch {
            $cleanupPassed = $false
            if ($failureMessage) { $failureMessage = "$failureMessage; transcript finalization failed: $($_.Exception.Message)" } else { $failureMessage = "transcript finalization failed: $($_.Exception.Message)" }
        }
    }
}

$artifacts = [System.Collections.Generic.List[object]]::new()
foreach ($artifactPath in @(
    $resolutionPath,
    $pythonAuditPath,
    $licenseInventoryPath,
    $frontendInstallScriptsPath,
    $frontendTreePath,
    $frontendAuditPath,
    $lifecycleEvidencePath,
    (Join-Path $laneDirectory "windows-$architectureSlug-install-qualification.log"),
    $transcriptPath
)) {
    if (Test-Path -LiteralPath $artifactPath -PathType Leaf) {
        $relativePath = $artifactPath.Substring($laneDirectory.Length).TrimStart("\").Replace("\", "/")
        [void]$artifacts.Add([ordered]@{ path = $relativePath; sha256 = Get-FileSha256 $artifactPath })
    }
}
if (Test-Path -LiteralPath $lockDirectory) {
    foreach ($profile in @("core", "voice", "vision", "desktop", "dev", "all")) {
        $lockPath = Join-Path $lockDirectory "$profile.txt"
        if (Test-Path -LiteralPath $lockPath -PathType Leaf) {
            [void]$artifacts.Add([ordered]@{ path = "locks/cpython-3.11-windows-$architectureSlug/$profile.txt"; sha256 = Get-FileSha256 $lockPath })
        }
    }
}
foreach ($packageRelative in $packageEvidencePaths) {
    $packagePath = Join-Path $laneDirectory $packageRelative.Replace("/", "\")
    if (Test-Path -LiteralPath $packagePath -PathType Leaf) {
        [void]$artifacts.Add([ordered]@{ path = $packageRelative; sha256 = Get-FileSha256 $packagePath })
    }
}
$laneStatus = if ($lanePassed -and $cleanupPassed) { "pass" } else { "fail" }
$laneEvidence = [ordered]@{
    schema_version = 2
    batch = "B02"
    status = $laneStatus
    commit_sha = $CommitSha
    completed_at_utc = [DateTime]::UtcNow.ToString("o")
    platform = [ordered]@{
        caption = $windowsPlatform.Caption
        version = $windowsPlatform.Version
        windows_build = $windowsPlatform.Build
        windows_product_type = $windowsPlatform.ProductType
        architecture = $windowsPlatform.Architecture
        architecture_slug = $architectureSlug
        powershell_process_architecture = $powerShellProcessArchitecture
        qualification_role = if ($architectureSlug -eq "arm64") { "primary-target-equivalent" } else { "secondary-hardware-independent" }
    }
    tools = [ordered]@{
        python_implementation = $pythonImplementation
        python_version = $pythonVersion
        python_machine = $pythonMachine
        node_version = $nodeVersion
        node_architecture = $nodeArchitecture
        npm_version = $npmVersion
        powershell_version = $PSVersionTable.PSVersion.ToString()
    }
    checks_passed = @($checks)
    repeated_lock_sha256 = $profileHashes
    core_lock_sha256 = if ($profileHashes.Contains("core")) { $profileHashes["core"] } else { $null }
    lifecycle_evidence = $lifecycleEvidenceName
    package_artifacts = @($packageEvidencePaths)
    artifacts = @($artifacts)
    cleanup_passed = $cleanupPassed
    failure = $failureMessage
}
Write-JsonFile $laneEvidence $laneJsonPath
Write-Host "Lane evidence: $laneJsonPath"

if ($laneStatus -ne "pass") {
    Write-Host "B02 BLOCKED - B03 REMAINS LOCKED"
    exit 1
}
Write-Host "B02 Windows $architectureSlug lane: PASS"
if ($LaneOnly) {
    Write-Host "Lane-only mode: matrix verdict intentionally deferred; B03 remains locked."
    exit 0
}
$matrixPassed = Invoke-MatrixAggregate $EvidenceRoot $CommitSha
if (-not $matrixPassed) { exit 2 }
exit 0
