#!/usr/bin/env python3
"""Verify OMNI wheel/sdist contents against the source tree.

The check is intentionally independent of setuptools' manifest bookkeeping. It
computes the runtime file set from the checkout, then requires the wheel and
sdist to contain that complete set. It also rejects source tests, local state,
models, secrets, caches, and unrelated applications from distributable payloads.
"""

from __future__ import annotations

import argparse
import email
import json
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = ("omni", "omni_v2", "backend_fastapi")
REQUIRED_EXTRAS = {"core", "voice", "vision", "desktop", "dev", "all"}
REQUIRED_SDIST_SUPPORT = {
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "pyproject.toml",
    "scripts/check_package_contents.py",
    "tests/package/test_artifact_install.py",
    "tests/package/test_package_metadata.py",
}
FORBIDDEN_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    "__pycache__",
    "archive",
    "data",
    "frontend",
    "frontend_next",
    "logs",
    "mobile",
    "models",
    "node_modules",
    "quality",
}
FORBIDDEN_SUFFIXES = (".db", ".gguf", ".pyc", ".pyo", ".sqlite", ".sqlite3")


def _runtime_files() -> set[str]:
    expected: set[str] = set()
    for root_name in RUNTIME_ROOTS:
        root = ROOT / root_name
        for path in root.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith("omni_v2/tests/"):
                continue
            if path.suffix == ".py" or relative in {
                "omni_v2/ui/orb_threejs.html",
                "omni_v2/web_ui/index.html",
            }:
                expected.add(relative)
    return expected


def _forbidden_payload(names: Iterable[str], *, sdist_prefix: str = "") -> list[str]:
    bad: list[str] = []
    for original in names:
        name = original
        if sdist_prefix and name.startswith(sdist_prefix):
            name = name[len(sdist_prefix) :]
        path = PurePosixPath(name)
        lowered = name.lower()
        if (
            any(part.lower() in FORBIDDEN_PARTS for part in path.parts)
            or lowered.endswith(FORBIDDEN_SUFFIXES)
            or path.name == ".env"
            or path.name.startswith(".env.")
        ):
            bad.append(original)
    return sorted(bad)


def _wheel_metadata(archive: zipfile.ZipFile, names: set[str]) -> list[str]:
    errors: list[str] = []
    metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
    if len(metadata_names) != 1:
        return [f"wheel must contain exactly one METADATA file; found {metadata_names}"]
    metadata = email.message_from_bytes(archive.read(metadata_names[0]))
    if metadata.get("Name") != "omni-agi":
        errors.append(f"wheel project name is {metadata.get('Name')!r}, expected 'omni-agi'")
    requires_python = metadata.get("Requires-Python", "")
    if {item.strip() for item in requires_python.split(",")} != {">=3.11", "<3.12"}:
        errors.append(
            f"wheel Requires-Python is {requires_python!r}, expected bounds >=3.11 and <3.12"
        )
    extras = set(metadata.get_all("Provides-Extra", []))
    if extras != REQUIRED_EXTRAS:
        errors.append(f"wheel extras are {sorted(extras)}, expected {sorted(REQUIRED_EXTRAS)}")
    return errors


def check_wheel(path: Path, expected: set[str]) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        missing = sorted(expected - names)
        leaked_tests = sorted(name for name in names if name.startswith("omni_v2/tests/"))
        allowed_roots = set(RUNTIME_ROOTS)
        unexpected_payload = sorted(
            name
            for name in names
            if name.split("/", 1)[0] not in allowed_roots
            and ".dist-info/" not in name
        )
        errors = _wheel_metadata(archive, names)
    forbidden = _forbidden_payload(names)
    if missing:
        errors.append(f"wheel is missing {len(missing)} runtime files: {missing}")
    if leaked_tests:
        errors.append(f"wheel contains source tests: {leaked_tests}")
    if unexpected_payload:
        errors.append(f"wheel contains unexpected top-level payload: {unexpected_payload}")
    if forbidden:
        errors.append(f"wheel contains forbidden local/runtime data: {forbidden}")
    return {
        "artifact": str(path),
        "kind": "wheel",
        "members": len(names),
        "runtime_files_required": len(expected),
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def check_sdist(path: Path, expected: set[str]) -> dict[str, object]:
    with tarfile.open(path, "r:gz") as archive:
        names = {member.name for member in archive.getmembers() if member.isfile()}
    roots = {name.split("/", 1)[0] for name in names}
    errors: list[str] = []
    if len(roots) != 1:
        errors.append(f"sdist must have one root directory; found {sorted(roots)}")
        prefix = ""
    else:
        prefix = next(iter(roots)) + "/"
    stripped = {name[len(prefix) :] for name in names if name.startswith(prefix)}
    missing_runtime = sorted(expected - stripped)
    missing_support = sorted(REQUIRED_SDIST_SUPPORT - stripped)
    leaked_tests = sorted(name for name in stripped if name.startswith("omni_v2/tests/"))
    forbidden = _forbidden_payload(names, sdist_prefix=prefix)
    if missing_runtime:
        errors.append(f"sdist is missing {len(missing_runtime)} runtime files: {missing_runtime}")
    if missing_support:
        errors.append(f"sdist is missing reproducibility files: {missing_support}")
    if leaked_tests:
        errors.append(f"sdist contains excluded omni_v2 source tests: {leaked_tests}")
    if forbidden:
        errors.append(f"sdist contains forbidden local/runtime data: {forbidden}")
    return {
        "artifact": str(path),
        "kind": "sdist",
        "members": len(names),
        "runtime_files_required": len(expected),
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    wheels = sorted(path for path in args.artifacts if path.suffix == ".whl")
    sdists = sorted(path for path in args.artifacts if path.name.endswith(".tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        parser.error(
            f"expected exactly one wheel and one .tar.gz sdist; got {len(wheels)} wheel(s) "
            f"and {len(sdists)} sdist(s)"
        )

    expected = _runtime_files()
    results = [check_wheel(wheels[0], expected), check_sdist(sdists[0], expected)]
    payload = {
        "schema_version": 1,
        "status": "pass" if all(item["status"] == "pass" for item in results) else "fail",
        "runtime_files_required": len(expected),
        "artifacts": results,
    }
    if args.as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in results:
            print(
                f"{item['status'].upper()}: {item['kind']} {item['artifact']} "
                f"({item['members']} members; {item['runtime_files_required']} runtime files required)"
            )
            for error in item["errors"]:
                print(f"  - {error}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
