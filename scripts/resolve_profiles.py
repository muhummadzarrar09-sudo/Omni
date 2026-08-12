#!/usr/bin/env python3
"""Resolve every declared B01 profile and emit exact, hashed CPython 3.11 locks."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("core", "voice", "vision", "desktop", "dev", "all")


def _display_path(path: Path) -> str:
    """Return a stable checkout-relative path when possible, else an absolute path."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _windows_product_type() -> int | None:
    if platform.system() != "Windows":
        return None
    get_version = getattr(sys, "getwindowsversion", None)
    if get_version is None:
        return None
    try:
        return int(get_version().product_type)
    except (AttributeError, TypeError, ValueError):
        return None


def _windows_build() -> int | None:
    if platform.system() != "Windows":
        return None
    get_version = getattr(sys, "getwindowsversion", None)
    if get_version is None:
        return None
    try:
        return int(get_version().build)
    except (AttributeError, TypeError, ValueError):
        return None


def _pointer_bits() -> int:
    return struct.calcsize("P") * 8


def _normalized_machine() -> str:
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        return "x86_64"
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    return machine


def _windows_os_machine() -> str | None:
    if platform.system() != "Windows":
        return None
    machine = (
        os.environ.get("PROCESSOR_ARCHITEW6432")
        or os.environ.get("PROCESSOR_ARCHITECTURE")
        or ""
    ).lower()
    if machine in {"amd64", "x86_64"}:
        return "x86_64"
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    return machine or None


def _is_supported_windows_native_64bit() -> bool:
    machine = _normalized_machine()
    return (
        machine in {"x86_64", "arm64"}
        and machine == _windows_os_machine()
        and _pointer_bits() == 64
    )


def _platform_slug() -> str:
    return f"cpython-3.11-{platform.system().lower()}-{_normalized_machine()}"


def _sha256(download_info: dict) -> str | None:
    archive = download_info.get("archive_info") or {}
    hashes = archive.get("hashes") or {}
    if hashes.get("sha256"):
        return str(hashes["sha256"])
    value = archive.get("hash")
    if isinstance(value, str) and value.startswith("sha256="):
        return value.split("=", 1)[1]
    return None


def _read_utf8_json(path: Path) -> dict[str, object]:
    """Read machine-generated JSON without depending on the host locale."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected a JSON object in {path}")
    return value


def _canonicalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _parse_exact_hashed_lock_records(path: Path) -> dict[str, dict[str, str]]:
    packages: dict[str, dict[str, str]] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(
            r"([A-Za-z0-9_.-]+)==([^\s]+)\s+--hash=sha256:([a-f0-9]{64})",
            line,
        )
        if not match:
            raise RuntimeError(f"invalid exact hashed lock entry at {path}:{line_number}")
        name = _canonicalize_name(match.group(1))
        if name in packages:
            raise RuntimeError(f"duplicate build-lock distribution: {name}")
        packages[name] = {"version": match.group(2), "sha256": match.group(3)}
    if not packages:
        raise RuntimeError(f"exact hashed lock is empty: {path}")
    return packages


def _parse_exact_hashed_lock(path: Path) -> dict[str, str]:
    return {
        name: record["version"]
        for name, record in _parse_exact_hashed_lock_records(path).items()
    }


def _validate_windows_build_authority(
    build_lock: Path, contract: dict[str, object], architecture: str
) -> tuple[dict[str, str], dict[tuple[str, str], dict[str, object]]]:
    if (
        contract.get("schema_version") != 1
        or contract.get("build_isolation") is not False
        or contract.get("runtime_install_build_isolation") is not False
        or contract.get("wheel_only_build_bootstrap") is not True
    ):
        raise RuntimeError("native Windows build-contract policy drifted")
    locked_records = _parse_exact_hashed_lock_records(build_lock)
    locked = {name: record["version"] for name, record in locked_records.items()}
    expected = {
        _canonicalize_name(str(name)): str(version)
        for name, version in dict(contract["build_lock"]).items()  # type: ignore[arg-type]
    }
    expected_hashes = {
        _canonicalize_name(str(name)): str(sha256)
        for name, sha256 in dict(contract["build_artifact_sha256"])[architecture].items()  # type: ignore[arg-type,index,union-attr]
    }
    locked_hashes = {name: record["sha256"] for name, record in locked_records.items()}
    if locked != expected or locked_hashes != expected_hashes:
        raise RuntimeError(
            f"build lock does not match quality/windows-native-build-contract.json: "
            f"expected versions {expected} and hashes {expected_hashes}; "
            f"found versions {locked} and hashes {locked_hashes}"
        )
    installed: dict[str, str] = {}
    for name, version in locked.items():
        try:
            installed[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError(
                f"build authority is not installed before resolution: {name}=={version}"
            ) from error
        if installed[name] != version:
            raise RuntimeError(
                f"installed build authority drift for {name}: expected {version}, "
                f"found {installed[name]}"
            )

    source_records = dict(contract["source_distributions"])[architecture]  # type: ignore[arg-type,index]
    allowed: dict[tuple[str, str], dict[str, object]] = {}
    for raw_record in source_records:  # type: ignore[union-attr]
        record = dict(raw_record)
        key = (_canonicalize_name(str(record["name"])), str(record["version"]))
        if key in allowed:
            raise RuntimeError(f"duplicate source-build contract entry: {key}")
        if record.get("kind") not in {"native", "pure_python"}:
            raise RuntimeError(f"source-build contract {key} has invalid build kind")
        if record.get("backend") not in {
            "setuptools.build_meta",
            "setuptools.build_meta:__legacy__",
            "scikit_build_core.build",
        }:
            raise RuntimeError(f"source-build contract {key} has unapproved backend")
        if not re.fullmatch(r"[a-f0-9]{64}", str(record.get("sha256", ""))):
            raise RuntimeError(f"source-build contract {key} has invalid SHA-256")
        if not str(record.get("filename", "")).endswith((".tar.gz", ".zip")):
            raise RuntimeError(f"source-build contract {key} has invalid source filename")
        controlled_tools = {
            _canonicalize_name(str(name)) for name in record["controlled_tools"]  # type: ignore[index]
        }
        declared_tools = {
            _canonicalize_name(str(name))
            for name in record["declared_build_requirements"]  # type: ignore[index]
        }
        missing_tools = controlled_tools - set(locked)
        if missing_tools:
            raise RuntimeError(f"source-build contract {key} has unlocked tools: {missing_tools}")
        if not declared_tools <= controlled_tools:
            raise RuntimeError(
                f"source-build contract {key} does not control declared tools: "
                f"{declared_tools - controlled_tools}"
            )
        allowed[key] = record
    return installed, allowed


def _validate_arm64_capability_markers(
    metadata: dict[str, object], contract: dict[str, object]
) -> None:
    """Prove every disclosed Arm64 exclusion is explicit in every declaration."""
    if (
        contract.get("status") != "reviewed_b02_installation_scope"
        or contract.get("native_only") is not True
        or contract.get("emulation_accepted") is not False
    ):
        raise RuntimeError("Windows Arm64 capability contract status or native policy drifted")

    optional_dependencies = dict(metadata["project"])["optional-dependencies"]  # type: ignore[index]
    declared: dict[str, list[Requirement]] = {}
    for requirements in dict(optional_dependencies).values():  # type: ignore[arg-type]
        for raw_requirement in requirements:  # type: ignore[union-attr]
            requirement = Requirement(str(raw_requirement))
            declared.setdefault(_canonicalize_name(requirement.name), []).append(requirement)

    arm_environment = {"platform_system": "Windows", "platform_machine": "ARM64"}
    x64_environment = {"platform_system": "Windows", "platform_machine": "AMD64"}
    exclusions = {
        _canonicalize_name(str(dict(record)["distribution"]))
        for record in contract["marker_exclusions"]  # type: ignore[index]
    }
    for name in sorted(exclusions):
        requirements = declared.get(name, [])
        if not requirements:
            raise RuntimeError(f"Arm64 capability exclusion is not declared in pyproject.toml: {name}")
        for requirement in requirements:
            marker = requirement.marker
            marker_text = str(marker).lower() if marker is not None else ""
            if "platform_system" not in marker_text or "platform_machine" not in marker_text:
                raise RuntimeError(
                    f"Arm64 capability exclusion lacks an explicit Windows/machine marker: {requirement}"
                )
            if marker.evaluate(arm_environment):
                raise RuntimeError(f"Arm64 capability exclusion remains selectable: {requirement}")
            if not marker.evaluate(x64_environment):
                raise RuntimeError(f"Arm64-only capability exclusion also disables Windows x64: {requirement}")


def _validate_arm64_capability_selection(
    results: dict[str, object], contract: dict[str, object]
) -> dict[str, object]:
    """Prove the all profile contains native paths and no disclosed exclusions."""
    all_profile = dict(results["all"])
    selected = {
        _canonicalize_name(str(dict(package)["name"]))
        for package in all_profile["packages"]  # type: ignore[index]
    }
    excluded = {
        _canonicalize_name(str(dict(record)["distribution"]))
        for record in contract["marker_exclusions"]  # type: ignore[index]
    }
    prohibited = sorted(selected & excluded)
    if prohibited:
        raise RuntimeError(f"Windows Arm64 all profile selected excluded distributions: {prohibited}")
    required = {
        _canonicalize_name(str(name))
        for name in contract["required_python_distributions"]  # type: ignore[index]
    }
    missing = sorted(required - selected)
    if missing:
        raise RuntimeError(f"Windows Arm64 all profile lacks required native paths: {missing}")
    return {
        "status": "pass",
        "contract": "quality/windows-arm64-capabilities.json",
        "required_python_distributions": sorted(required),
        "excluded_python_distributions": sorted(excluded),
        "selected_exclusions": prohibited,
    }


def _artifact_kind(url: str) -> str:
    path = urlsplit(url).path.lower()
    if path.endswith(".whl"):
        return "wheel"
    if path.endswith((".tar.gz", ".tar.bz2", ".tar.xz", ".zip")):
        return "sdist"
    return "unknown"


def _lock_text(profile: str, packages: list[dict[str, object]]) -> str:
    lines = [
        "# Generated by scripts/resolve_profiles.py; do not edit.",
        f"# Profile: {profile}",
        f"# Interpreter: CPython {platform.python_version()}",
        f"# Platform: {platform.system()} {platform.machine()}",
        "# Install the OMNI wheel separately, then install this platform-specific lock with:",
        f"#   python -m pip install --no-deps --require-hashes -r {profile}.txt",
        "",
    ]
    for package in packages:
        if package["name"].lower() == "omni-agi":
            continue
        digest = package.get("sha256")
        if not digest:
            raise RuntimeError(f"resolved package has no SHA-256: {package}")
        lines.append(f"{package['name']}=={package['version']} --hash=sha256:{digest}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT / "quality/evidence/B01/profile-resolution.json"
            if platform.system() == "Linux"
            else ROOT / "quality/evidence/B02" / f"{_platform_slug()}-profile-resolution.json"
        ),
    )
    parser.add_argument(
        "--lock-dir",
        type=Path,
        default=ROOT / "requirements/locks" / _platform_slug(),
    )
    parser.add_argument(
        "--build-lock",
        type=Path,
        help=(
            "preinstalled exact wheel-only build lock; required on Windows and defaults to the "
            "architecture-specific repository lock"
        ),
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=PROFILES,
        default=list(PROFILES),
        help="profile locks to resolve (default: every declared profile)",
    )
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 11) or platform.python_implementation() != "CPython":
        parser.error("profile locks must be generated with CPython 3.11")
    if platform.system() == "Windows":
        windows_build = _windows_build()
        if not _is_supported_windows_native_64bit():
            parser.error(
                "Windows B02 locks must be generated by native 64-bit CPython on Windows X64 or Arm64"
            )
        if _windows_product_type() != 1:
            parser.error(
                "Windows product locks for B02 must be generated on a Windows 11 workstation, not Windows Server"
            )
        if windows_build is None or windows_build < 22000:
            parser.error(
                "Windows product locks for B02 require Windows 11 build 22000 or newer"
            )
    with (ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)
    build_requirements = list(metadata["build-system"]["requires"])
    declared = set(metadata["project"]["optional-dependencies"])
    if declared != set(PROFILES):
        parser.error(f"declared profile drift: expected {PROFILES}, found {sorted(declared)}")

    build_lock: Path | None = None
    installed_build_authority: dict[str, str] = {}
    allowed_source_distributions: dict[tuple[str, str], dict[str, object]] = {}
    arm64_capability_contract: dict[str, object] | None = None
    if platform.system() == "Windows":
        architecture = _normalized_machine()
        build_lock = args.build_lock or (
            ROOT / "requirements" / "locks" / _platform_slug() / "build.txt"
        )
        if not build_lock.is_absolute():
            build_lock = ROOT / build_lock
        if not build_lock.is_file():
            parser.error(f"native Windows build lock is absent: {build_lock}")
        contract = _read_utf8_json(ROOT / "quality" / "windows-native-build-contract.json")
        try:
            installed_build_authority, allowed_source_distributions = (
                _validate_windows_build_authority(build_lock, contract, architecture)
            )
        except (KeyError, RuntimeError, TypeError, ValueError) as error:
            parser.error(str(error))
        if architecture == "arm64":
            arm64_capability_contract = _read_utf8_json(
                ROOT / "quality" / "windows-arm64-capabilities.json"
            )
            try:
                _validate_arm64_capability_markers(metadata, arm64_capability_contract)
            except (KeyError, RuntimeError, TypeError, ValueError) as error:
                parser.error(str(error))

    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="omni-profile-resolution-") as temporary:
        temp = Path(temporary)
        for profile in args.profiles:
            report_path = temp / f"{profile}.json"
            command = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--dry-run",
                "--ignore-installed",
                "--report",
                str(report_path),
                f".[{profile}]",
            ]
            # Third-party metadata preparation must use the already installed,
            # exact build authority. Default PEP 517 isolation would perform a
            # hidden backend dependency resolution before the runtime lock exists.
            if platform.system() == "Windows":
                command.append("--no-build-isolation")
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=1200,
                check=False,
            )
            if completed.returncode:
                print(completed.stdout[-5000:], file=sys.stderr)
                print(completed.stderr[-5000:], file=sys.stderr)
                raise SystemExit(f"profile {profile} failed to resolve")
            # pip writes report JSON as UTF-8. Windows' locale default may be
            # cp1252, which cannot decode all valid package metadata.
            report = _read_utf8_json(report_path)
            packages: list[dict[str, object]] = []
            selected_sources: list[dict[str, object]] = []
            for item in report["install"]:
                artifact_kind = _artifact_kind(str(item["download_info"]["url"]))
                package = {
                    "name": item["metadata"]["name"],
                    "version": item["metadata"]["version"],
                    "requested": bool(item.get("requested", False)),
                    "url": item["download_info"]["url"],
                    "sha256": _sha256(item["download_info"]),
                    "artifact_kind": artifact_kind,
                }
                normalized_name = _canonicalize_name(str(package["name"]))
                if normalized_name != "omni-agi" and not package["sha256"]:
                    raise SystemExit(f"profile {profile} has unhashed dependency: {package}")
                if normalized_name != "omni-agi" and artifact_kind == "unknown":
                    raise SystemExit(f"profile {profile} selected unknown artifact type: {package}")
                if platform.system() == "Windows" and normalized_name != "omni-agi" and artifact_kind == "sdist":
                    key = (normalized_name, str(package["version"]))
                    source_contract = allowed_source_distributions.get(key)
                    if source_contract is None:
                        raise SystemExit(
                            f"profile {profile} selected unreviewed source distribution {key}; "
                            "amend quality/windows-native-build-contract.json before building it"
                        )
                    selected_filename = Path(urlsplit(str(package["url"])).path).name
                    if (
                        package["sha256"] != source_contract["sha256"]
                        or selected_filename != source_contract["filename"]
                    ):
                        raise SystemExit(
                            f"profile {profile} selected source artifact drift for {key}: "
                            f"{selected_filename} sha256={package['sha256']}"
                        )
                    package["source_build_backend"] = source_contract["backend"]
                    package["source_build_kind"] = source_contract["kind"]
                    selected_sources.append(
                        {
                            "name": package["name"],
                            "version": package["version"],
                            "filename": selected_filename,
                            "sha256": package["sha256"],
                            "backend": source_contract["backend"],
                            "kind": source_contract["kind"],
                        }
                    )
                packages.append(package)
            packages.sort(key=lambda value: (str(value["name"]).lower(), str(value["version"])))
            selected_sources.sort(
                key=lambda value: (str(value["name"]).lower(), str(value["version"]))
            )
            results[profile] = {
                "status": "pass",
                "resolved_count": len(packages),
                "selected_source_distributions": selected_sources,
                "packages": packages,
            }
            print(f"PASS {profile}: {len(packages)} distributions")

    if platform.system() == "Windows" and "all" in results:
        all_sources = {
            (_canonicalize_name(str(dict(source)["name"])), str(dict(source)["version"]))
            for source in dict(results["all"])["selected_source_distributions"]  # type: ignore[index]
        }
        if all_sources != set(allowed_source_distributions):
            raise SystemExit(
                "Windows all profile source selection drifted from the architecture contract: "
                f"expected {sorted(allowed_source_distributions)}, found {sorted(all_sources)}"
            )

    arm64_capability_evidence: dict[str, object] | None = None
    if arm64_capability_contract is not None:
        if "all" in results:
            try:
                arm64_capability_evidence = _validate_arm64_capability_selection(
                    results, arm64_capability_contract
                )
            except (KeyError, RuntimeError, TypeError, ValueError) as error:
                parser.error(str(error))
        else:
            arm64_capability_evidence = {
                "status": "not_evaluated",
                "contract": "quality/windows-arm64-capabilities.json",
                "reason": "the all profile was not requested",
            }

    lock_dir = args.lock_dir if args.lock_dir.is_absolute() else ROOT / args.lock_dir
    lock_dir.mkdir(parents=True, exist_ok=True)
    if build_lock is not None:
        destination = lock_dir / "build.txt"
        if build_lock.resolve() != destination.resolve():
            shutil.copyfile(build_lock, destination)
    for profile in args.profiles:
        packages = results[profile]["packages"]  # type: ignore[index]
        (lock_dir / f"{profile}.txt").write_text(_lock_text(profile, packages), encoding="utf-8")

    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "status": "pass",
        "generated_by": "scripts/resolve_profiles.py",
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable": str(Path(sys.executable).resolve()),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "normalized_machine": _normalized_machine(),
            "windows_os_machine": _windows_os_machine(),
            "pointer_bits": _pointer_bits(),
            "windows_build": _windows_build(),
            "windows_product_type": _windows_product_type(),
        },
        "supported_python": metadata["project"]["requires-python"],
        "local_build_system_requirements": build_requirements,
        "third_party_build_isolation": False if platform.system() == "Windows" else None,
        "build_lock": _display_path(build_lock) if build_lock is not None else None,
        "installed_build_authority": installed_build_authority,
        "source_build_contract": (
            "quality/windows-native-build-contract.json"
            if platform.system() == "Windows"
            else None
        ),
        "arm64_capability_contract": arm64_capability_evidence,
        "profiles": results,
        "lock_directory": _display_path(lock_dir),
        "limitation": (
            f"Locks and resolver evidence are CPython 3.11 {platform.system()} "
            f"{platform.machine()} specific; they do not qualify any other platform. "
            "Resolution alone does not prove installation or runtime behavior."
        ),
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {_display_path(output)} and {len(args.profiles)} hashed lock files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
