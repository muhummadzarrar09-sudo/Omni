"""Central filesystem paths for OMNI runtime data.

Packaged code can live in a read-only environment (for example, system
``site-packages``), so runtime state must never default beside the source. The
``OMNI_DATA_DIR`` environment variable is the explicit override; otherwise the
platform's per-user data location is used.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def get_project_root() -> Path:
    """Return the source-checkout or installed-package container.

    This compatibility path is suitable only for locating bundled/read-only
    resources. Runtime state belongs under :func:`get_data_dir`.
    """

    return Path(__file__).resolve().parent.parent.parent


def _default_data_dir(environment: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environment is None else environment
    if os.name == "nt":
        base = Path(env.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "OMNI"
    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Application Support" / "OMNI"
    base = Path(env.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "omni"


def sys_platform() -> str:
    """Small wrapper kept separate to make platform path behavior testable."""

    import sys

    return sys.platform


def get_data_dir(
    *,
    create: bool = True,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Return OMNI's writable user-data directory.

    ``OMNI_DATA_DIR`` is intentionally allowed to point outside the home
    directory: operators may use another drive, an encrypted mount, or a test
    sandbox. The caller controls that location and its permissions. Passing an
    explicit environment keeps configuration-contract tests deterministic.
    """

    env = os.environ if environment is None else environment
    configured = env.get("OMNI_DATA_DIR")
    data_dir = (
        Path(configured).expanduser().resolve()
        if configured
        else _default_data_dir(env).expanduser().resolve()
    )
    if create:
        data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_omni_v2_data_dir() -> Path:
    """Compatibility alias for the canonical OMNI data directory."""

    return get_data_dir()


# Constants are resolved without creating anything at import time. Individual
# services create only the directories they actually need.
PROJECT_ROOT = get_project_root()
DATA_DIR = get_data_dir(create=False)
CONFIG_PATH = DATA_DIR / "config.json"
MEMORY_DB_PATH = DATA_DIR / "memory.db"
VECTOR_DB_PATH = DATA_DIR / "chroma"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
LOGS_DIR = DATA_DIR / "logs"
VECTOR_FALLBACK_PATH = DATA_DIR / "vector_fallback.json"
MEMORY_JSON_PATH = DATA_DIR / "memory.json"


def migrate_old_data() -> None:
    """Copy legacy ``~/.omni_v2`` data into the canonical location once."""

    import shutil

    old_home = Path.home() / ".omni_v2"
    new_data = get_data_dir()
    if not old_home.exists() or old_home.resolve() == new_data.resolve():
        return
    if (new_data / "memory.db").exists() and (new_data / "chroma").exists():
        return

    try:
        for filename in ("memory.db", "memory.json"):
            source = old_home / filename
            destination = new_data / filename
            if source.exists() and not destination.exists():
                shutil.copy2(source, destination)

        source_chroma = old_home / "chroma"
        destination_chroma = new_data / "chroma"
        if source_chroma.exists() and not destination_chroma.exists():
            shutil.copytree(source_chroma, destination_chroma)

        source_screenshots = old_home / "screenshots"
        if source_screenshots.exists():
            destination_screenshots = new_data / "screenshots"
            destination_screenshots.mkdir(exist_ok=True)
            for source in source_screenshots.iterdir():
                destination = destination_screenshots / source.name
                if source.is_file() and not destination.exists():
                    shutil.copy2(source, destination)
    except OSError as exc:
        print(f"[OMNI V2] Legacy data migration failed: {exc}")


def bootstrap_workspace() -> None:
    """Explicitly prepare writable runtime directories and migrate old data."""

    get_data_dir()
    for path in (VECTOR_DB_PATH, SCREENSHOTS_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)
    migrate_old_data()
