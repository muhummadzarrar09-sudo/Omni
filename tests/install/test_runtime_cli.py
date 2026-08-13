from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_cli(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["OMNI_DATA_DIR"] = str(tmp_path)
    return subprocess.run(
        [sys.executable, "-m", "omni_v2.core.runtime_cli", *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_help_exposes_managed_configuration_and_lifecycle_commands(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--help")

    assert result.returncode == 0
    for command in ("config", "preflight", "start", "stop", "status", "restart"):
        assert command in result.stdout


def test_config_init_and_show_are_machine_readable_and_idempotent(tmp_path: Path) -> None:
    first = _run_cli(tmp_path, "--json", "config", "init")
    second = _run_cli(tmp_path, "--json", "config", "init")
    shown = _run_cli(tmp_path, "--json", "config", "show")

    assert first.returncode == second.returncode == shown.returncode == 0
    assert json.loads(first.stdout)["created"] is True
    assert json.loads(second.stdout)["created"] is False
    public = json.loads(shown.stdout)
    assert public["data_dir"] == str(tmp_path.resolve())
    assert "api_token" not in public
    assert public["secrets"]["api_token_configured"] is False


def test_status_is_structured_even_when_runtime_is_stopped(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--json", "status")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["ok"] is False
    assert {service["status"] for service in payload["services"]} == {"stopped"}


def test_non_primary_preflight_succeeds_with_truthful_optional_warnings(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--json", "preflight", "--root", str(Path.cwd()))
    report = json.loads(result.stdout)

    assert result.returncode == 0
    assert report["ok"] is True
    assert report["counts"]["fail"] == 0
    assert report["counts"]["warn"] >= 1
    assert (tmp_path / "diagnostics" / "preflight.json").is_file()
