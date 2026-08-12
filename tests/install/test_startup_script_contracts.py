from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.resolve_profiles import _read_utf8_json

ROOT = Path(__file__).resolve().parents[2]


def test_windows_primary_paths_require_workstation_product_type() -> None:
    platform_helper = (ROOT / "scripts" / "windows_platform.ps1").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts" / "start.ps1").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts" / "verify_windows_install.ps1").read_text(encoding="utf-8")
    qualifier = (ROOT / "scripts" / "qualify_b02.ps1").read_text(encoding="utf-8")
    resolver = (ROOT / "scripts" / "resolve_profiles.py").read_text(encoding="utf-8")
    workflow = (
        ROOT / "quality" / "evidence" / "B02" / "hosted-windows-qualification.workflow.yml"
    ).read_text(encoding="utf-8")

    assert "Win32_OperatingSystem" in platform_helper
    assert "$operatingSystem.BuildNumber" in platform_helper
    assert "$platform.ProductType -ne 1" in platform_helper
    assert 'platform.Architecture -notin @("X64", "Arm64")' in platform_helper
    assert "Windows Server" in platform_helper
    assert "PROCESSOR_ARCHITEW6432" in platform_helper
    assert "Win32_Processor" in platform_helper
    assert 'GetProperty("OSArchitecture")' in platform_helper
    assert "::OSArchitecture" not in platform_helper
    assert "Get-OmniPowerShellProcessArchitecture" in platform_helper
    assert "::ProcessArchitecture" not in qualifier
    assert 'windows_platform.ps1")' in installer
    assert "Assert-OmniWindows11" in installer
    assert "-PythonPath" in installer
    assert "cpython-3.11-windows-$architectureSlug" in installer
    assert "--require-hashes" in installer
    assert "--only-binary=:all:" in installer
    assert installer.count("--no-cache-dir") >= 3
    assert "--no-build-isolation" in installer
    assert 'windows_build_tools.ps1")' in installer
    assert "Enter-OmniWindowsNativeBuildEnvironment" in installer
    assert "Get-ExactHashedLockRecords" in installer
    assert "Runtime lock bytes do not match" in installer
    assert 'windows_platform.ps1")' in launcher
    assert "Assert-OmniWindows11" in launcher
    assert '"preflight", "--primary"' in launcher
    assert '$needsRecovery' in launcher
    assert '"unhealthy", "unverified"' in launcher
    assert 'windows_platform.ps1")' in verifier
    assert "Assert-OmniWindows11" in verifier
    assert "windows_product_type" in verifier and "-eq 1" in verifier
    assert "windows_build" in verifier and "-ge 22000" in verifier
    assert "pointer_bits" in verifier and "-eq 64" in verifier
    assert "third_party_build_isolation -eq $false" in verifier
    assert "source_build_contract" in verifier
    assert "build_lock_sha256" in verifier
    assert '"-ResolutionPath", $ResolutionPath' in verifier
    assert "Authenticated backend readiness" in verifier
    assert "finally" in verifier
    assert "_windows_product_type() != 1" in resolver
    assert "windows_build is None or windows_build < 22000" in resolver
    assert "_is_supported_windows_native_64bit()" in resolver
    assert "machine == _windows_os_machine()" in resolver
    assert '"windows_product_type": _windows_product_type()' in resolver
    assert '"windows_build": _windows_build()' in resolver
    assert '"pointer_bits": _pointer_bits()' in resolver
    assert 'path.read_text(encoding="utf-8")' in resolver
    assert "Idempotent second managed start" in verifier

    assert "Qualification authority has tracked changes" in qualifier
    assert qualifier.index("Get-Command py") < qualifier.index("Get-Command python")
    assert "git worktree add --detach" in qualifier
    assert 'foreach ($profile in @("core", "voice", "vision", "desktop", "dev", "all"))' in qualifier
    assert "Repeat native dependency resolution without build isolation" in qualifier
    assert "Bootstrap exact wheel-only native build authority" in qualifier
    assert "Install exact native dev lock without cache or build isolation" in qualifier
    assert qualifier.count('"--disable-pip", "--require-hashes"') == 3
    assert "$unexpectedAuditNames = @($auditedNames | Where-Object { $_ -notin $expectedNames })" in qualifier
    assert "Install exact native all-runtime lock without cache or build isolation" in qualifier
    assert "Check installed all-runtime dependency consistency" in qualifier
    assert "Run configured OMNI Python tests against exact all-runtime dependencies" in qualifier
    assert "Build wheel and source distribution without an isolated dependency resolution" in qualifier
    assert "-m build --no-isolation" in qualifier
    assert "OMNI_EXACT_BUILD_LOCK" in qualifier
    assert "Run frontend proxy tests" in qualifier
    assert "Run full install/start/readiness/restart/stop/uninstall lifecycle" in qualifier
    assert 'required_native_lanes = @("windows-arm64", "windows-x86_64")' in qualifier
    assert '$invalidEvidence = @($evaluated | Where-Object { $_.status -ne "pass" })' in qualifier
    assert "$missing.Count -eq 0 -and $invalidEvidence.Count -eq 0" in qualifier
    assert '"ALL SYSTEMS GO {0} B03 UNLOCKED" -f [char]0x2014' in qualifier
    assert "B02 BLOCKED - B03 REMAINS LOCKED" in qualifier
    assert "windows-11-arm" in workflow
    assert "windows-latest" in workflow
    assert "pull_request.head.sha" in workflow
    assert "types: [opened, synchronize, reopened]" in workflow
    assert "-LaneOnly" in workflow
    assert "-AggregateOnly" in workflow


def test_powershell_variables_before_colons_are_delimited() -> None:
    """PowerShell parses ``$Name:`` as a scoped variable, even in strings."""
    scoped_names = {
        "alias",
        "env",
        "function",
        "global",
        "local",
        "private",
        "script",
        "using",
        "variable",
    }
    unsafe_reference = re.compile(r"(?<!`)\$([A-Za-z_][A-Za-z0-9_]*):")
    assert unsafe_reference.search('"$ArchitectureSlug: details"')
    assert not unsafe_reference.search('"${ArchitectureSlug}: details"')
    failures: list[str] = []

    for path in sorted((ROOT / "scripts").glob("*.ps1")):
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for line_number, line in enumerate(lines, 1):
            for match in unsafe_reference.finditer(line):
                if match.group(1).lower() not in scoped_names:
                    failures.append(f"{path.relative_to(ROOT)}:{line_number}: {match.group(0)}")

    assert not failures, "ambiguous PowerShell variable references:\n" + "\n".join(failures)


def test_profile_resolver_reads_pip_report_as_utf8(tmp_path: Path) -> None:
    report = tmp_path / "pip-report.json"
    metadata = "right quote \N{RIGHT DOUBLE QUOTATION MARK}"
    report.write_bytes(f'{{"metadata": "{metadata}"}}'.encode())

    assert _read_utf8_json(report) == {"metadata": metadata}


def test_profile_resolver_rejects_non_object_report(tmp_path: Path) -> None:
    report = tmp_path / "pip-report.json"
    report.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match="expected a JSON object"):
        _read_utf8_json(report)


def test_windows_source_builds_are_native_exact_and_fail_closed() -> None:
    tools = (ROOT / "scripts" / "windows_build_tools.ps1").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    qualifier = (ROOT / "scripts" / "qualify_b02.ps1").read_text(encoding="utf-8")

    assert "vswhere.exe" in tools
    assert '"-requires"' in tools
    assert "installationVersion" in tools
    assert ".Major -ne 17" in tools
    assert 'if ($ArchitectureSlug -eq "arm64") { "arm64" } else { "x64" }' in tools
    assert "compiler_path_fragment" in tools
    assert "linker_path_fragment" in tools
    assert "Get-Command cl.exe" in tools
    assert "Get-Command link.exe" in tools
    assert "Get-FileHash -Algorithm SHA256" in tools
    assert "contract.visual_studio.windows_sdk_version" in tools
    assert '$vcvarsArguments = "$vcvarsArgument $windowsSdkContractVersion"' in tools
    assert "Import-OmniBatchEnvironment -BatchFile $vcvarsall -Arguments $vcvarsArguments" in tools
    assert "[BitConverter]::ToUInt16($bytes, $peOffset + 4)" in tools
    assert "target_machine" in tools
    assert "& $executable" in tools
    assert "dumpbin" not in tools.lower()

    assert qualifier.index("Enter-OmniWindowsNativeBuildEnvironment") < qualifier.index(
        "Resolve all six native dependency profiles"
    )
    assert '"--only-binary=:all:" --no-deps --require-hashes' in qualifier
    assert qualifier.count("--no-cache-dir --no-build-isolation") >= 4
    assert '$env:PATH = "$(Join-Path $buildVenv \'Scripts\');$env:PATH"' in qualifier
    assert '$env:PATH = "$(Join-Path $devVenv \'Scripts\');$env:PATH"' in qualifier
    assert '$env:PATH = "$(Join-Path $allVenv \'Scripts\');$env:PATH"' in qualifier
    assert "locks/cpython-3.11-windows-$architectureSlug/build.txt" in qualifier
    assert "native_build_tools = $nativeBuildTools" in qualifier
    assert "all-vulnerability-audit.json" in qualifier
    assert "build-vulnerability-audit.json" in qualifier

    assert installer.index("Enter-OmniWindowsNativeBuildEnvironment") < installer.index(
        'pip install --disable-pip-version-check'
    )
    assert "quality/windows-native-build-contract.json" in installer
    assert "build_artifact_sha256" in installer
    assert "artifact hashes do not match" in installer
    assert '$env:PATH = "$venvScripts;$env:PATH"' in installer
    assert "buildContract.build_tool_cli.cmake" in installer
    assert "buildContract.build_tool_cli.ninja" in installer
    assert "Assert-ExactInstalledEnvironment" in installer
    assert "Managed distributions differ from the exact authority" in installer
    assert "Resolver evidence selected an unapproved native source artifact" in installer
    assert "_parse_exact_hashed_lock_records" in (ROOT / "scripts" / "resolve_profiles.py").read_text(
        encoding="utf-8"
    )


def test_dlib_declared_requirements_are_not_confused_with_controlled_tools() -> None:
    contract = _read_utf8_json(ROOT / "quality" / "windows-native-build-contract.json")
    x64_sources = {
        (record["name"], record["version"]): record
        for record in contract["source_distributions"]["x86_64"]  # type: ignore[index]
    }
    dlib = x64_sources[("dlib", "20.0.1")]

    # dlib 20.0.1's sdist declares only setuptools>=42 and wheel. Its build
    # implementation additionally imports packaging and invokes CMake; those
    # tools remain exact and controlled without being misreported as declared.
    assert dlib["declared_build_requirements"] == ["setuptools", "wheel"]
    assert dlib["controlled_tools"] == ["setuptools", "wheel", "packaging", "cmake"]
    assert set(dlib["controlled_tools"]) <= set(contract["build_lock"])  # type: ignore[arg-type]
    assert "packaging" not in dlib["declared_build_requirements"]
    assert "cmake" not in dlib["declared_build_requirements"]


def test_windows_qualification_cleanup_is_strict_on_success_and_failure() -> None:
    verifier = (ROOT / "scripts" / "verify_windows_install.ps1").read_text(encoding="utf-8")
    qualifier = (ROOT / "scripts" / "qualify_b02.ps1").read_text(encoding="utf-8")

    assert "Register-OwnedProcesses" in verifier
    assert "start_time_utc_ticks" in verifier
    assert '$identityKey = "$pidValue`:$startTimeUtcTicks`:$executable"' in verifier
    assert "Test-RecordedProcessIdentity" in verifier
    assert "managed runtime stop failed" in verifier
    assert 'Stop-Process -Id ([int]$identity.pid) -Force' in verifier
    assert 'Remove-GeneratedPath (Join-Path $root ".venv")' in verifier
    assert 'Remove-GeneratedPath $QualificationDataPath "isolated qualification data"' in verifier
    assert 'Remove-Item -LiteralPath $evidencePath -Force' in verifier
    assert "$completedEvidence.cleanup_passed = $true" in verifier
    assert verifier.index("if ($cleanupErrors.Count -gt 0)") < verifier.index(
        "install/start/stop/restart/second-install/uninstall qualification: PASS"
    )

    assert "$env:OMNI_DATA_DIR = $qualificationData" in qualifier
    assert "Get-QualificationProcesses" in qualifier
    assert 'taskkill.exe /PID ([string]$process.ProcessId) /T /F' in qualifier
    assert 'Remove-CleanupPath $tempRoot "qualification temporary root"' in qualifier
    assert "detached qualification worktree remains registered" in qualifier
    assert "cleanup invariant failed; path still exists" in qualifier
    assert "$laneStatus = if ($lanePassed -and $cleanupPassed)" in qualifier
    assert "lifecycleEvidence.cleanup_passed" in qualifier
    assert "recorded_process_count -eq 6" in qualifier
    assert "recorded_process_observations -eq 8" in qualifier


def test_installers_use_corepack_managed_exact_npm() -> None:
    windows_installer = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    unix_installer = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts" / "verify_windows_install.ps1").read_text(encoding="utf-8")

    assert "Get-Command corepack" in windows_installer
    assert "npm@12.0.2" in windows_installer
    assert "Get-Command npm" not in windows_installer
    assert "command -v corepack" in unix_installer
    assert 'NPM=("$COREPACK" "npm@12.0.2")' in unix_installer
    assert "command -v npm" not in unix_installer
    assert "npm@12.0.2" in verifier


def test_unix_developer_launcher_recovers_owned_unhealthy_runtime() -> None:
    launcher = (ROOT / "start.sh").read_text(encoding="utf-8")

    assert "{'unhealthy', 'unverified'}" in launcher
    assert "omni_v2.core.runtime_cli restart" in launcher


def test_uninstall_reports_only_confirmed_removals() -> None:
    source = (ROOT / "scripts" / "uninstall.ps1").read_text(encoding="utf-8")

    generated_removal = source.index("Remove-Item -LiteralPath $path -Recurse -Force")
    generated_record = source.index("[void]$removedGenerated.Add($path)")
    data_removal = source.index("Remove-Item -LiteralPath $fullData -Recurse -Force")
    data_record = source.index("$userDataRemoved = $true")

    assert generated_record > generated_removal
    assert data_record > data_removal
    assert "if ($removedGenerated.Count -gt 0)" in source
    assert "No generated installation assets were removed." in source
    assert "if ($userDataRemoved)" in source
    assert "OMNI user data was not removed because deletion was skipped" in source
    assert "Removed generated installation assets and user data" not in source


def test_uninstall_is_explicit_idempotent_and_fail_closed() -> None:
    source = (ROOT / "scripts" / "uninstall.ps1").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts" / "verify_windows_install.ps1").read_text(encoding="utf-8")

    assert 'SupportsShouldProcess = $true, ConfirmImpact = "High"' in source
    assert '[switch]$RemoveUserData' in source
    assert 'Join-Path $root ".venv"' in source
    assert 'Join-Path $root "frontend_next\\node_modules"' in source
    assert 'Join-Path $root "frontend_next\\.next"' in source
    assert "runtime_cli stop" in source
    assert "owned process tree could not be stopped safely" in source
    assert "Managed runtime state exists but .venv is unavailable" in source
    assert "OMNI_DATA_DIR must be an absolute path" in source
    assert "The canonical user-data path is absent or not absolute" in source
    assert "GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)" in source
    assert "GetFolderPath([Environment+SpecialFolder]::UserProfile)" in source
    assert "$insideRepository" in source
    assert "$containsRepository" in source
    assert "$containsHome" in source
    assert "$fullData -eq $driveRoot" in source
    assert "short-name-like or tilde-containing" in source
    assert "Assert-SafeDataTree $path" in source
    assert "Assert-SafeDataTree $fullData" in source
    assert "FileAttributes]::ReparsePoint" in source
    assert "Generated installation asset still exists after removal" in source
    assert "OMNI user data still exists after removal" in source

    assert '"Explicit user-data uninstall"' in verifier
    assert '"Idempotent second uninstall"' in verifier
    assert "-RemoveUserData -Confirm:$false" in verifier
    assert 'Test-Path "$root\\pyproject.toml"' in verifier
    assert 'explicit user-data uninstall removes only validated canonical data' in verifier
    assert 'second uninstall is idempotent and leaves the source checkout intact' in verifier


def test_frontend_routes_never_fabricate_backend_success_or_drop_status() -> None:
    route_files = sorted((ROOT / "frontend_next" / "app" / "api").rglob("route.js"))
    assert route_files

    for route in route_files:
        source = route.read_text(encoding="utf-8")
        assert "mock: true" not in source, route
        assert "FastAPI not running" not in source, route
        assert "backendProxy(" in source or "backendFetch(" in source, route
        if "export function POST(request)" in source:
            assert "sourceRequest: request" in source, route

    catch_all = (ROOT / "frontend_next" / "app" / "api" / "python" / "[...path]" / "route.js").read_text(
        encoding="utf-8"
    )
    assert "sourceRequest: request" in catch_all
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert f"export const {method} = proxy" in catch_all

    backend = (ROOT / "frontend_next" / "backend.js").read_text(encoding="utf-8")
    assert "enforceMutationOrigin(sourceRequest, method)" in backend
    assert "status: response.status" in backend
    assert "status: 503" in backend
    assert "success: true" not in backend
