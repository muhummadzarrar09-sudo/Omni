"""
OMNI BACKUP & RESTORE (Phase 15, #4) — export/import the whole OMNI state.

Creates a portable archive of OMNI's data (brain state, harness, knowledge base,
goals, identity, vault meta, config, schedules, automations, journal, calendar,
contacts) so you can back it up or move it to another machine (e.g. the DGX).

Design:
  - `create_backup(dest)`: copies all relevant data/ subdirs into a timestamped
    folder (or a .zip archive). Excludes models (huge) by default.
  - `restore_backup(src)`: restores the archived state back into data/.
  - Safe: never touches models, never overwrites unless asked.
  - Headless-testable (works on the local data dir).

Usage:
    omni backup create --out ~/omni-backup   # folder backup
    omni backup create --zip ~/omni-backup.zip
    omni backup restore ~/omni-backup
    omni backup list
"""
from __future__ import annotations
import json
import time
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Backup")

from omni_v2.core.paths import DATA_DIR

# subdirs/files to back up (excludes models/ which are huge + redownloadable)
BACKUP_INCLUDES = [
    "brain", "kb", "sources.json", "config.json", "personal", "reports",
    "messenger", "skills", "away", "scheduler", "security", "profiles",
    "personality", "onboarding", "stats", "vision", "notifications",
]
# files we never back up
EXCLUDE_FILES = {"owner_model.xml", "vault_key"}


class BackupManager:
    """Creates and restores portable OMNI state archives."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR

    # -- discovery ---------------------------------------------------------
    def _snapshot_dirs(self) -> List[Path]:
        out = []
        for name in BACKUP_INCLUDES:
            p = self.data_dir / name
            if p.exists():
                out.append(p)
        return out

    # -- create ------------------------------------------------------------
    def create(self, out: Optional[str] = None, as_zip: bool = False) -> Dict[str, Any]:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        if out:
            dest = Path(out)
        elif as_zip:
            dest = self.data_dir.parent / f"omni_backup_{stamp}.zip"
        else:
            dest = self.data_dir.parent / f"omni_backup_{stamp}"

        if as_zip:
            count = self._create_zip(dest)
            return {"ok": True, "path": str(dest), "items": count, "zip": True}
        return self._create_folder(dest)

    def _create_folder(self, dest: Path) -> Dict[str, Any]:
        dest.mkdir(parents=True, exist_ok=True)
        count = 0
        for src in self._snapshot_dirs():
            target = dest / src.name
            if src.is_dir():
                shutil.copytree(src, target, dirs_exist_ok=True,
                                ignore=self._ignore_fn)
            else:
                shutil.copy2(src, target)
            count += 1
        # write a manifest
        (dest / "manifest.json").write_text(json.dumps({
            "created_at": time.time(), "items": count, "version": "omni-v3",
        }), encoding="utf-8")
        logger.info(f"📦 backup created at {dest} ({count} items)")
        return {"ok": True, "path": str(dest), "items": count + 1, "zip": False}

    def _create_zip(self, dest: Path) -> int:
        count = 0
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for src in self._snapshot_dirs():
                if src.is_dir():
                    for f in src.rglob("*"):
                        if f.is_file() and f.name not in EXCLUDE_FILES:
                            zf.write(f, f"{src.name}/{f.relative_to(src)}")
                            count += 1
                else:
                    zf.write(src, src.name)
                    count += 1
            zf.writestr("manifest.json", json.dumps({
                "created_at": time.time(), "items": count, "version": "omni-v3"}))
        logger.info(f"📦 zip backup created at {dest} ({count} files)")
        return count

    def _ignore_fn(self, dir, names):
        return [n for n in names if n in EXCLUDE_FILES]

    # -- restore -----------------------------------------------------------
    def restore(self, src: str, overwrite: bool = True) -> Dict[str, Any]:
        src_path = Path(src)
        if not src_path.exists():
            return {"ok": False, "detail": f"backup not found: {src}"}
        count = 0
        if src_path.is_dir():
            for item in src_path.iterdir():
                if item.name == "manifest.json":
                    continue
                target = self.data_dir / item.name
                if item.is_dir():
                    if target.exists() and not overwrite:
                        continue
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
                count += 1
        elif src_path.suffix == ".zip":
            with zipfile.ZipFile(src_path) as zf:
                for name in zf.namelist():
                    if name == "manifest.json":
                        continue
                    zf.extract(name, self.data_dir)
                    count += 1
        return {"ok": True, "restored_items": count, "from": str(src_path)}

    # -- introspection -------------------------------------------------------
    def list_backups(self, search_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        base = Path(search_dir) if search_dir else self.data_dir.parent
        out = []
        for p in sorted(base.glob("omni_backup*")):
            size = sum(f.stat().st_size for f in p.rglob("*")) if p.is_dir() else p.stat().st_size
            out.append({"name": p.name, "path": str(p), "size_bytes": size,
                        "is_dir": p.is_dir()})
        return out

    def stats(self) -> Dict[str, Any]:
        return {"data_dir": str(self.data_dir),
                "snapshot_items": len(self._snapshot_dirs())}


def get_backup(**kwargs) -> BackupManager:
    return BackupManager(**kwargs)
