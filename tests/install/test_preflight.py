from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from omni_v2.core import preflight
from omni_v2.core.config import load_config
from omni_v2.core.preflight import run_preflight, write_json_report


def _free_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def _configured_environment(tmp_path: Path) -> dict[str, str]:
    ports: set[int] = set()
    while len(ports) < 3:
        ports.add(_free_port())
    backend, frontend, discovery = ports
    browser = tmp_path / "browser"
    browser.write_text("test executable marker", encoding="utf-8")
    model = tmp_path / "models" / "fast.gguf"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"valid-model-placeholder")
    return {
        "OMNI_DATA_DIR": str(tmp_path),
        "OMNI_BACKEND_PORT": str(backend),
        "OMNI_FRONTEND_PORT": str(frontend),
        "OMNI_DISCOVERY_PORT": str(discovery),
        "OMNI_MODEL_PATH": str(model),
        "OMNI_BROWSER_PATH": str(browser),
    }


def _mock_windows_platform(
    monkeypatch: pytest.MonkeyPatch,
    *,
    build: int,
    product_type: int | None,
    machine: str = "AMD64",
) -> None:
    monkeypatch.setattr(preflight.platform, "system", lambda: "Windows")
    monkeypatch.setattr(preflight.platform, "machine", lambda: machine)
    monkeypatch.setattr(preflight.platform, "release", lambda: "11")
    monkeypatch.setattr(preflight, "_windows_version", lambda: (build, product_type))


def test_primary_platform_accepts_windows_11_x64_workstation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_windows_platform(monkeypatch, build=26100, product_type=1)

    result = preflight._platform_check(require_primary=True)

    assert result.status == "pass"
    assert result.summary == "Windows 11 x64 workstation detected"
    assert "product type 1" in result.detail


def test_primary_platform_rejects_windows_server_despite_qualifying_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_windows_platform(monkeypatch, build=26100, product_type=3)

    result = preflight._platform_check(require_primary=True)

    assert result.status == "fail"
    assert "Windows Server" in result.summary
    assert "product type 3" in result.detail


def test_primary_platform_fails_when_windows_product_type_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_windows_platform(monkeypatch, build=26100, product_type=None)

    result = preflight._platform_check(require_primary=True)

    assert result.status == "fail"
    assert "could not be verified" in result.summary
    assert "build number alone" in result.detail


def test_preflight_reports_structured_results_and_persists_redacted_diagnostics(
    tmp_path: Path,
) -> None:
    environment = _configured_environment(tmp_path)
    environment["OMNI_API_TOKEN"] = "diagnostics-must-not-leak-this"
    config = load_config(environment=environment)
    repository = tmp_path / "checkout"
    (repository / "frontend_next" / ".next").mkdir(parents=True)
    (repository / "frontend_next" / "package.json").write_text("{}", encoding="utf-8")
    (repository / "frontend_next" / ".next" / "BUILD_ID").write_text("build", encoding="utf-8")
    next_cli = repository / "frontend_next" / "node_modules" / "next" / "dist" / "bin" / "next"
    next_cli.parent.mkdir(parents=True)
    next_cli.write_text("test executable marker", encoding="utf-8")
    (repository / "frontend_next" / "server.js").write_text(
        "test server marker", encoding="utf-8"
    )

    result = run_preflight(
        config=config,
        repository_root=repository,
        require_frontend=True,
    )

    assert result.ok is True
    assert result.counts["fail"] == 0
    assert result.counts["pass"] >= 10
    assert any(check.code == "model.fast" and check.status == "pass" for check in result.checks)
    assert any(check.code == "frontend.build" and check.status == "pass" for check in result.checks)
    diagnostics_path = tmp_path / "diagnostics.json"
    write_json_report(result, diagnostics_path)
    persisted = diagnostics_path.read_text(encoding="utf-8")
    assert "diagnostics-must-not-leak-this" not in persisted
    assert json.loads(persisted)["configuration"]["secrets"]["api_token_configured"] is True


def test_preflight_warns_truthfully_when_configured_model_is_missing(
    tmp_path: Path,
) -> None:
    environment = _configured_environment(tmp_path)
    Path(environment["OMNI_MODEL_PATH"]).unlink()
    result = run_preflight(
        config=load_config(environment=environment),
        repository_root=tmp_path,
    )

    check = next(item for item in result.checks if item.code == "model.fast")
    assert result.ok is True
    assert check.status == "warn"
    assert check.remediation is not None
    assert "OMNI_MODEL_PATH" in check.remediation


def test_preflight_detects_an_unowned_port_without_mutating_it(tmp_path: Path) -> None:
    environment = _configured_environment(tmp_path)
    with socket.socket() as occupied:
        occupied.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        environment["OMNI_BACKEND_PORT"] = str(occupied.getsockname()[1])
        result = run_preflight(
            config=load_config(environment=environment),
            repository_root=tmp_path,
        )
        occupied.settimeout(0.1)
        probe = socket.create_connection(occupied.getsockname(), timeout=0.1)
        probe.close()

    check = next(item for item in result.checks if item.code == "port.backend")
    assert result.ok is True
    assert check.status == "warn"
    assert "already in use" in check.summary
