from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _probe(environment: dict[str, str]) -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json;"
                "from omni_v2.core.paths import DATA_DIR,get_data_dir;"
                "before=DATA_DIR.exists();"
                "created=get_data_dir();"
                "print(json.dumps({'data_dir':str(DATA_DIR),'before':before,"
                "'after':created.is_dir()}))"
            ),
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def test_default_runtime_path_is_per_user_and_created_lazily(tmp_path: Path) -> None:
    xdg_home = tmp_path / "xdg"
    environment = os.environ.copy()
    environment.pop("OMNI_DATA_DIR", None)
    environment["XDG_DATA_HOME"] = str(xdg_home)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    payload = _probe(environment)

    assert Path(str(payload["data_dir"])) == (xdg_home / "omni").resolve()
    assert payload["before"] is False
    assert payload["after"] is True


def test_explicit_runtime_path_override_is_honored(tmp_path: Path) -> None:
    configured = tmp_path / "external-drive" / "omni-state"
    environment = os.environ.copy()
    environment["OMNI_DATA_DIR"] = str(configured)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    payload = _probe(environment)

    assert Path(str(payload["data_dir"])) == configured.resolve()
    assert payload["before"] is False
    assert payload["after"] is True


def test_production_defaults_do_not_target_checkout_data_directories() -> None:
    forbidden = (
        'Path.cwd() / "data"',
        "Path.cwd() / 'data'",
        'Path(__file__).resolve().parents[2] / "data"',
        "Path(__file__).resolve().parents[2] / 'data'",
        "D:/Omni/data/output",
        "sys.path.insert(",
        "sys.path.append(",
    )
    offenders: list[str] = []
    for package in ("omni", "omni_v2", "backend_fastapi"):
        for path in (ROOT / package).rglob("*.py"):
            if "tests" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            for expression in forbidden:
                if expression in source:
                    offenders.append(f"{path.relative_to(ROOT)}: {expression}")
    assert offenders == []


def test_backend_import_outside_checkout_writes_only_to_configured_data_root(
    tmp_path: Path,
) -> None:
    clean_cwd = tmp_path / "work"
    data_root = tmp_path / "state"
    clean_cwd.mkdir()
    environment = os.environ.copy()
    environment["OMNI_DATA_DIR"] = str(data_root)
    environment["PYTHONPATH"] = str(ROOT)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import backend_fastapi.main, json;"
                "from omni_v2.core.paths import DATA_DIR;"
                "print(json.dumps({'data_dir': str(DATA_DIR)}))"
            ),
        ],
        cwd=clean_cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert Path(payload["data_dir"]) == data_root.resolve()
    assert list(clean_cwd.iterdir()) == []
    assert data_root.is_dir()


def test_default_file_write_uses_configured_data_root(tmp_path: Path) -> None:
    clean_cwd = tmp_path / "work"
    data_root = tmp_path / "state"
    clean_cwd.mkdir()
    environment = os.environ.copy()
    environment["OMNI_DATA_DIR"] = str(data_root)
    environment["PYTHONPATH"] = str(ROOT)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import asyncio,json;"
                "from omni_v2.tools.files import FilesTool;"
                "result=asyncio.run(FilesTool().execute("
                "{'action':'write','content':'package-path-check'},"
                "{'original':'write a file'}));"
                "print(json.dumps({'success':result.success,'data':result.data}))"
            ),
        ],
        cwd=clean_cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )

    payload = json.loads(result.stdout)
    target = data_root / "output" / "output.txt"
    assert payload["success"] is True
    assert Path(payload["data"]["path"]) == target.resolve()
    assert target.read_text(encoding="utf-8") == "package-path-check"
    assert list(clean_cwd.iterdir()) == []
