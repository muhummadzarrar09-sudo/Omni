from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_windows_primary_paths_require_workstation_product_type() -> None:
    platform_helper = (ROOT / "scripts" / "windows_platform.ps1").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts" / "start.ps1").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts" / "verify_windows_install.ps1").read_text(encoding="utf-8")
    resolver = (ROOT / "scripts" / "resolve_profiles.py").read_text(encoding="utf-8")

    assert "Win32_OperatingSystem" in platform_helper
    assert "$operatingSystem.BuildNumber" in platform_helper
    assert "$platform.ProductType -ne 1" in platform_helper
    assert "Windows Server" in platform_helper
    assert 'windows_platform.ps1")' in installer
    assert "Assert-OmniWindows11X64" in installer
    assert "--require-hashes" in installer
    assert "--no-build-isolation" in installer
    assert 'windows_platform.ps1")' in launcher
    assert "Assert-OmniWindows11X64" in launcher
    assert '"preflight", "--primary"' in launcher
    assert '$needsRecovery' in launcher
    assert '"unhealthy", "unverified"' in launcher
    assert 'windows_platform.ps1")' in verifier
    assert "Assert-OmniWindows11X64" in verifier
    assert "windows_product_type -eq 1" in verifier
    assert "windows_build -ge 22000" in verifier
    assert "pointer_bits -eq 64" in verifier
    assert "build_system_requirements_included -eq $true" in verifier
    assert "_windows_product_type() != 1" in resolver
    assert "windows_build is None or windows_build < 22000" in resolver
    assert "_is_windows_x64()" in resolver
    assert '"windows_product_type": _windows_product_type()' in resolver
    assert '"windows_build": _windows_build()' in resolver
    assert '"pointer_bits": _pointer_bits()' in resolver
    assert "Idempotent second managed start" in verifier


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
