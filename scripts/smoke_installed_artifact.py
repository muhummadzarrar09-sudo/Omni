#!/usr/bin/env python3
"""Install the exact wheel with core dependencies and smoke it off-checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {command}\n"
            f"stdout tail:\n{result.stdout[-4000:]}\nstderr tail:\n{result.stderr[-4000:]}"
        )
    return result


def _installed_tree_snapshot(site_packages: Path) -> dict[str, str]:
    """Hash every installed OMNI payload file to detect runtime mutations."""
    roots = [
        site_packages / "omni",
        site_packages / "omni_v2",
        site_packages / "backend_fastapi",
        *site_packages.glob("omni_agi-*.dist-info"),
    ]
    if any(not root.is_dir() for root in roots[:3]) or len(roots) != 4:
        raise RuntimeError(f"could not identify one complete OMNI installation in {site_packages}")
    snapshot: dict[str, str] = {}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(site_packages).as_posix()
                snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not snapshot:
        raise RuntimeError(f"installed OMNI package tree is empty: {site_packages}")
    return snapshot


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument(
        "--lock",
        type=Path,
        default=ROOT / "requirements/locks/cpython-3.11-linux-x86_64/core.txt",
        help="exact hashed core-profile lock",
    )
    parser.add_argument("--timeout", type=int, default=60, help="backend startup timeout in seconds")
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    lock = args.lock.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error(f"wheel not found: {wheel}")
    if not lock.is_file():
        parser.error(f"core lock not found: {lock}")

    with tempfile.TemporaryDirectory(prefix="omni-b01-installed-") as temporary:
        work = Path(temporary)
        environment = work / "venv"
        clean_cwd = work / "work"
        clean_cwd.mkdir()
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        if os.name == "nt":
            python = environment / "Scripts/python.exe"
            omni = environment / "Scripts/omni.exe"
        else:
            python = environment / "bin/python"
            omni = environment / "bin/omni"

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        data_root = work / "data"
        env["OMNI_DATA_DIR"] = str(data_root)
        dependency_install = _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--require-hashes",
                "-r",
                str(lock),
            ],
            clean_cwd,
            env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                wheel.as_uri(),
            ],
            clean_cwd,
            env,
        )
        site_probe = _run(
            [
                str(python),
                "-I",
                "-c",
                "import site; print(site.getsitepackages()[0])",
            ],
            clean_cwd,
            env,
            timeout=30,
        )
        site_packages = Path(site_probe.stdout.strip()).resolve()
        package_tree_before = _installed_tree_snapshot(site_packages)

        _run([str(omni), "--help"], clean_cwd, env, timeout=30)
        install_help = _run([str(omni), "install"], clean_cwd, env, timeout=30)
        if "omni-agi[core]" not in install_help.stdout:
            raise RuntimeError("installed CLI did not render canonical profile guidance")
        engine_info = _run([str(omni), "engine", "info"], clean_cwd, env, timeout=30)
        if "QueryEngine" not in engine_info.stdout:
            raise RuntimeError("installed CLI did not dispatch a lightweight subcommand")
        import_probe = _run(
            [
                str(python),
                "-I",
                "-c",
                (
                    "import importlib.metadata,importlib.resources,json,pathlib,omni,omni_v2,backend_fastapi;"
                    "from omni_v2.core.paths import DATA_DIR;"
                    "version=importlib.metadata.version('omni-agi');"
                    "assert omni.__version__ == version and omni_v2.__version__ == version;"
                    "root=importlib.resources.files('omni_v2');"
                    "ui=root.joinpath('ui/orb_threejs.html');"
                    "web=root.joinpath('web_ui/index.html');"
                    "assert ui.is_file() and web.is_file();"
                    "print(json.dumps({'paths':[str(pathlib.Path(x.__file__).resolve()) "
                    "for x in (omni,omni_v2,backend_fastapi)],'resources':[ui.name,web.name],"
                    "'version':version,'data_root':str(DATA_DIR.resolve())}))"
                ),
            ],
            clean_cwd,
            env,
            timeout=30,
        )
        import_result = json.loads(import_probe.stdout)
        import_paths = import_result["paths"]
        if any(str(ROOT) in path for path in import_paths):
            raise RuntimeError(f"source-checkout import leaked into smoke test: {import_paths}")
        if Path(import_result["data_root"]) != data_root.resolve():
            raise RuntimeError(f"installed runtime ignored OMNI_DATA_DIR: {import_result['data_root']}")

        port = _free_port()
        server = subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "backend_fastapi.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            cwd=clean_cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        payload: dict[str, object] | None = None
        deadline = time.monotonic() + args.timeout
        try:
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    output = server.stdout.read() if server.stdout else ""
                    raise RuntimeError(f"backend exited before smoke request ({server.returncode}):\n{output[-6000:]}")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                        payload = json.loads(response.read())
                    break
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                    time.sleep(0.25)
            if payload is None:
                raise RuntimeError(f"backend did not answer within {args.timeout} seconds")
            if payload.get("status") != "ok":
                raise RuntimeError(f"unexpected backend health payload: {payload}")
            if payload.get("version") != import_result["version"]:
                raise RuntimeError(
                    "backend/package version mismatch: "
                    f"{payload.get('version')} != {import_result['version']}"
                )
            recordings_dir = Path(str(payload.get("stt", {}).get("recordings_dir", "")))
            if recordings_dir != data_root / "recordings":
                raise RuntimeError(
                    f"installed backend used non-user-data recording path: {recordings_dir}"
                )
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

        unexpected_cwd_entries = sorted(path.name for path in clean_cwd.iterdir())
        if unexpected_cwd_entries:
            raise RuntimeError(
                "installed runtime wrote into its working directory instead of OMNI_DATA_DIR: "
                f"{unexpected_cwd_entries}"
            )

        package_tree_after = _installed_tree_snapshot(site_packages)
        if package_tree_after != package_tree_before:
            added = sorted(package_tree_after.keys() - package_tree_before.keys())
            removed = sorted(package_tree_before.keys() - package_tree_after.keys())
            changed = sorted(
                path
                for path in package_tree_before.keys() & package_tree_after.keys()
                if package_tree_before[path] != package_tree_after[path]
            )
            raise RuntimeError(
                "installed runtime mutated its package tree: "
                f"added={added}, removed={removed}, changed={changed}"
            )

        result = {
            "schema_version": 1,
            "status": "pass",
            "wheel": wheel.name,
            "profile": "core",
            "lock": lock.name,
            "hashed_lock_install": "pass",
            "working_directory_outside_checkout": True,
            "cli_help": "pass",
            "cli_install_guidance": "pass",
            "cli_engine_info": "pass",
            "imports": import_paths,
            "version": import_result["version"],
            "package_resources": import_result["resources"],
            "data_root": import_result["data_root"],
            "working_directory_entries": unexpected_cwd_entries,
            "installed_package_tree": str(site_packages),
            "installed_package_file_count": len(package_tree_after),
            "installed_package_tree_immutable": True,
            "backend_health": payload,
            "dependency_install_completed": "Successfully installed" in dependency_install.stdout,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
