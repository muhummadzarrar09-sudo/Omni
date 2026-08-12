from __future__ import annotations

from pathlib import Path

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
    assert "--no-build-isolation" in installer
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
    assert "build_system_requirements_included -eq $true" in verifier
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
    assert "Repeat native dependency resolution" in qualifier
    assert "Install exact native dev lock" in qualifier
    assert "Install exact native all-runtime lock" in qualifier
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


def test_profile_resolver_reads_pip_report_as_utf8(tmp_path: Path) -> None:
    report = tmp_path / "pip-report.json"
    metadata = "right quote \N{RIGHT DOUBLE QUOTATION MARK}"
    report.write_bytes(f'{{"metadata": "{metadata}"}}'.encode("utf-8"))

    assert _read_utf8_json(report) == {"metadata": metadata}


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
