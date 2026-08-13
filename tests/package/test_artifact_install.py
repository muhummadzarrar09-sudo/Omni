from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"


def _artifacts() -> tuple[Path, Path]:
    wheels = sorted(DIST.glob("*.whl"))
    sdists = sorted(DIST.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        pytest.fail(
            "package tests require exactly one wheel and one sdist in dist/; "
            "run `rm -rf dist build *.egg-info && python -m build` first"
        )
    return wheels[0], sdists[0]


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"command failed ({result.returncode}): {command}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def test_exact_artifacts_pass_content_validator() -> None:
    wheel, sdist = _artifacts()
    result = _run(
        [sys.executable, "scripts/check_package_contents.py", "--json", str(wheel), str(sdist)],
        cwd=ROOT,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["runtime_files_required"] >= 180


@pytest.mark.parametrize("artifact_index", [0, 1], ids=["wheel", "sdist"])
def test_artifact_installs_and_cli_runs_outside_checkout(
    tmp_path: Path, artifact_index: int
) -> None:
    artifact = _artifacts()[artifact_index]
    environment = tmp_path / "environment"
    work = tmp_path / "outside-checkout"
    work.mkdir()
    _run([sys.executable, "-m", "venv", str(environment)], cwd=work)

    if os.name == "nt":
        python = environment / "Scripts/python.exe"
        omni = environment / "Scripts/omni.exe"
    else:
        python = environment / "bin/python"
        omni = environment / "bin/omni"

    isolated_env = os.environ.copy()
    isolated_env.pop("PYTHONPATH", None)
    isolated_env["PYTHONNOUSERSITE"] = "1"
    exact_build_lock = isolated_env.get("OMNI_EXACT_BUILD_LOCK")
    if exact_build_lock:
        lock = Path(exact_build_lock).resolve()
        assert lock.is_file(), f"OMNI_EXACT_BUILD_LOCK is not a file: {lock}"
        locked_names = {
            line.split("==", 1)[0].strip().lower().replace("_", "-")
            for line in lock.read_text(encoding="utf-8").splitlines()
            if "==" in line and not line.lstrip().startswith("#")
        }
        assert {"setuptools", "wheel"} <= locked_names, (
            "exact qualification lock must include the declared PEP 517 backend"
        )
        installer = [
            sys.executable,
            "-m",
            "pip",
            "--python",
            str(python),
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
        ]
        install_options = ["--no-deps"]
        if artifact.name.endswith(".tar.gz"):
            # Install the complete lock without dependency traversal. This
            # includes the backend and its transitive requirements (notably
            # wheel's packaging dependency) while forbidding hidden network
            # resolution and requiring a hash for every installed archive.
            _run(
                installer
                + ["--only-binary=:all:", "--no-deps", "--require-hashes", "-r", str(lock)],
                cwd=work,
                env=isolated_env,
            )
            install_options.append("--no-build-isolation")
        install_command = installer + install_options + [str(artifact)]
    else:
        install_command = [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            str(artifact),
        ]
    _run(install_command, cwd=work, env=isolated_env)
    help_result = _run([str(omni), "--help"], cwd=work, env=isolated_env)
    assert "OMNI" in help_result.stdout

    probe = _run(
        [
            str(python),
            "-I",
            "-c",
            (
                "import json, pathlib, omni, omni_v2, backend_fastapi; "
                "mods=(omni, omni_v2, backend_fastapi); "
                "print(json.dumps([str(pathlib.Path(m.__file__).resolve()) for m in mods]))"
            ),
        ],
        cwd=work,
        env=isolated_env,
    )
    module_paths = json.loads(probe.stdout)
    checkout = str(ROOT.resolve())
    assert all(checkout not in path for path in module_paths)
    assert all(str(environment.resolve()) in path for path in module_paths)
