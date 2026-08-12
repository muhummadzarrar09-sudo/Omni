from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

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
