from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from scripts.resolve_profiles import (
    _parse_exact_hashed_lock,
    _parse_exact_hashed_lock_records,
    _validate_arm64_capability_markers,
    _validate_arm64_capability_selection,
)

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_PROFILES = {"core", "voice", "vision", "desktop", "dev", "all"}
FIRST_PARTY = {"omni", "omni_v2", "backend_fastapi", "__future__"}


def _metadata() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _profile_names(requirements: list[str]) -> set[str]:
    return {canonicalize_name(Requirement(value).name) for value in requirements}


def _third_party_imports() -> set[str]:
    imports: set[str] = set()
    for root_name in ("omni", "omni_v2", "backend_fastapi"):
        for path in (ROOT / root_name).rglob("*.py"):
            if "tests" in path.parts or "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    top_level = name.split(".", 1)[0]
                    if top_level not in sys.stdlib_module_names and top_level not in FIRST_PARTY:
                        imports.add(top_level)
    return imports


def test_supported_python_and_profile_set_are_exact() -> None:
    metadata = _metadata()
    project = metadata["project"]
    assert project["requires-python"] == ">=3.11,<3.12"
    assert project["dependencies"] == []
    assert set(project["optional-dependencies"]) == EXPECTED_PROFILES
    assert metadata["tool"]["ruff"]["target-version"] == "py311"


def test_build_backend_excludes_vulnerable_and_unreviewed_setuptools_versions() -> None:
    requirements = [Requirement(value) for value in _metadata()["build-system"]["requires"]]
    setuptools = next(
        requirement
        for requirement in requirements
        if canonicalize_name(requirement.name) == "setuptools"
    )

    assert not setuptools.specifier.contains("82.0.1")
    assert setuptools.specifier.contains("83.0.0")
    assert setuptools.specifier.contains("84.0.0")
    assert not setuptools.specifier.contains("85.0.0")


def test_all_contains_every_runtime_profile_and_dev_contains_core() -> None:
    profiles = _metadata()["project"]["optional-dependencies"]
    normalized = {name: _profile_names(values) for name, values in profiles.items()}
    runtime_union = normalized["core"] | normalized["voice"] | normalized["vision"] | normalized["desktop"]
    assert runtime_union <= normalized["all"]
    assert normalized["core"] <= normalized["dev"]


def test_every_production_third_party_import_is_mapped_and_declared() -> None:
    profile_authority = json.loads((ROOT / "quality/dependency-profiles.json").read_text())
    import_map = profile_authority["import_map"]
    discovered = _third_party_imports()
    assert discovered == set(import_map), (
        f"import/profile drift: missing map={sorted(discovered - set(import_map))}; "
        f"stale map={sorted(set(import_map) - discovered)}"
    )

    profiles = _metadata()["project"]["optional-dependencies"]
    normalized = {name: _profile_names(values) for name, values in profiles.items()}
    for module, record in import_map.items():
        distribution = canonicalize_name(record["distribution"])
        for profile in record["profiles"]:
            assert profile in EXPECTED_PROFILES, f"{module}: unknown profile {profile}"
            assert distribution in normalized[profile], (
                f"{module}: {record['distribution']} is absent from profile {profile}"
            )


def test_requirement_compatibility_files_delegate_to_pyproject() -> None:
    root_requirements = (ROOT / "requirements.txt").read_text()
    backend_requirements = (ROOT / "backend_fastapi/requirements.txt").read_text()
    assert re.search(r"(?m)^\.\[all\]$", root_requirements)
    assert re.search(r"(?m)^\.\[core\]$", backend_requirements)
    assert "-e " not in root_requirements
    assert "-e " not in backend_requirements
    for impossible in ("numpy>=2.5.1", "opencv-python>=5.0.0.93"):
        assert impossible not in root_requirements
        assert impossible not in backend_requirements
        assert impossible not in (ROOT / "pyproject.toml").read_text()


def test_checkout_installers_use_real_profiles_without_editable_installs() -> None:
    installer_paths = (
        ROOT / "Makefile",
        ROOT / "install.bat",
        ROOT / "scripts/install.sh",
        ROOT / "scripts/install.ps1",
        ROOT / "scripts/setup_hardware.sh",
    )
    installers = {path: path.read_text() for path in installer_paths}
    combined = "\n".join(installers.values())
    makefile = installers[ROOT / "Makefile"]

    assert "-e " not in combined
    assert ".[brain]" not in combined
    assert 'install ".[core]"' in makefile
    assert 'install ".[all]"' in makefile
    assert 'install ".[dev]"' in makefile
    assert all("TROUBLESHOOTING.md" in source for source in installers.values())
    assert "not B01" in combined or "NOT a B01" in combined
    assert "scripts\\install.ps1" in installers[ROOT / "install.bat"]
    assert all(
        "sys.version_info[:2] == (3, 11)" in source
        for path, source in installers.items()
        if path.name not in {"Makefile", "install.bat"}
    )


def test_windows_native_build_contract_and_architecture_locks_are_exact() -> None:
    contract = json.loads(
        (ROOT / "quality/windows-native-build-contract.json").read_text(encoding="utf-8")
    )
    assert contract["schema_version"] == 1
    assert contract["build_isolation"] is False
    assert contract["runtime_install_build_isolation"] is False
    assert contract["wheel_only_build_bootstrap"] is True

    expected_build = {
        canonicalize_name(name): version for name, version in contract["build_lock"].items()
    }
    assert expected_build["setuptools"] == "84.0.0"
    assert expected_build["pip"] == "26.2.1"
    assert expected_build["cmake"] == "4.4.2"
    assert expected_build["ninja"] == "1.13.0"
    assert contract["build_tool_cli"] == {
        "cmake": "cmake version 4.4.2",
        "ninja": "1.13.0.git.kitware.jobserver-pipe-1",
    }
    for architecture in ("x86_64", "arm64"):
        lock = (
            ROOT
            / "requirements/locks"
            / f"cpython-3.11-windows-{architecture}"
            / "build.txt"
        )
        assert _parse_exact_hashed_lock(lock) == expected_build
        lock_records = _parse_exact_hashed_lock_records(lock)
        assert {name: record["sha256"] for name, record in lock_records.items()} == {
            canonicalize_name(name): sha256
            for name, sha256 in contract["build_artifact_sha256"][architecture].items()
        }
        assert set(lock_records) == set(contract["build_artifact_sha256"][architecture])
        assert all(
            re.fullmatch(r"[a-f0-9]{64}", sha256)
            for sha256 in contract["build_artifact_sha256"][architecture].values()
        )
        visual_studio = contract["visual_studio"]["architectures"][architecture]
        expected_host = "Hostx64\\x64" if architecture == "x86_64" else "Hostarm64\\arm64"
        assert visual_studio["compiler_path_fragment"] == f"{expected_host}\\cl.exe"
        assert visual_studio["linker_path_fragment"] == f"{expected_host}\\link.exe"

        records = contract["source_distributions"][architecture]
        keys = [(canonicalize_name(record["name"]), record["version"]) for record in records]
        assert len(keys) == len(set(keys))
        for record in records:
            assert re.fullmatch(r"[a-f0-9]{64}", record["sha256"])
            assert record["filename"].endswith((".tar.gz", ".zip"))
            assert record["kind"] in {"native", "pure_python"}
            assert set(map(canonicalize_name, record["declared_build_requirements"])) <= set(
                map(canonicalize_name, record["controlled_tools"])
            )
            assert set(map(canonicalize_name, record["controlled_tools"])) <= set(
                expected_build
            )

    x64_sources = {
        (canonicalize_name(record["name"]), record["version"])
        for record in contract["source_distributions"]["x86_64"]
    }
    arm64_sources = {
        (canonicalize_name(record["name"]), record["version"])
        for record in contract["source_distributions"]["arm64"]
    }
    assert len(x64_sources) == 12
    assert len(arm64_sources) == 9
    assert ("dlib", "20.0.1") in x64_sources
    assert ("dlib", "20.0.1") not in arm64_sources
    assert ("llama-cpp-python", "0.3.34") in x64_sources & arm64_sources


def test_windows_arm64_capability_contract_is_enforced_by_markers() -> None:
    metadata = _metadata()
    contract = json.loads(
        (ROOT / "quality/windows-arm64-capabilities.json").read_text(encoding="utf-8")
    )
    _validate_arm64_capability_markers(metadata, contract)

    profiles = metadata["project"]["optional-dependencies"]
    all_requirements = [Requirement(value) for value in profiles["all"]]
    all_names = {canonicalize_name(requirement.name) for requirement in all_requirements}
    assert set(map(canonicalize_name, contract["required_python_distributions"])) <= all_names
    excluded = {
        canonicalize_name(record["distribution"]) for record in contract["marker_exclusions"]
    }
    assert len(excluded) == 10
    assert excluded <= all_names

    results = {
        "all": {
            "packages": [
                {"name": name} for name in contract["required_python_distributions"]
            ]
        }
    }
    evidence = _validate_arm64_capability_selection(results, contract)
    assert evidence["status"] == "pass"
    assert evidence["selected_exclusions"] == []
    results["all"]["packages"].append({"name": "chromadb"})
    with pytest.raises(RuntimeError, match="selected excluded distributions"):
        _validate_arm64_capability_selection(results, contract)

    arm_cryptography = [
        requirement
        for requirement in all_requirements
        if canonicalize_name(requirement.name) == "cryptography"
        and requirement.marker
        and requirement.marker.evaluate(
            {"platform_system": "Windows", "platform_machine": "ARM64"}
        )
    ]
    assert len(arm_cryptography) == 1
    assert arm_cryptography[0].specifier.contains("46.0.3")
    assert not arm_cryptography[0].specifier.contains("46.0.4")


def test_package_discovery_covers_runtime_roots_and_excludes_source_tests() -> None:
    setuptools = _metadata()["tool"]["setuptools"]
    discovery = setuptools["packages"]["find"]
    assert discovery["namespaces"] is False
    assert set(discovery["include"]) >= {
        "omni",
        "omni.*",
        "omni_v2",
        "omni_v2.*",
        "backend_fastapi",
        "backend_fastapi.*",
    }
    assert "omni_v2.tests" in discovery["exclude"]
    assert set(setuptools["package-data"]["omni_v2"]) == {"ui/*.html", "web_ui/*.html"}
