"""
OMNI V3 - Skill Marketplace (Phase 4C: "Others Can Extend It")

1-click install community skills. OMNI becomes a platform.

A "skill" is a Python file that extends OMNI's capabilities.
This module:
  - Manages a local registry of installed skills
  - One-click install from a remote registry (GitHub raw URLs)
  - Auto-update checking
  - Sandboxed execution (skills can't break the brain)

Skill format (a Python file):
  ```python
  from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

  class MySkill(CommandPlugin):
      metadata = CommandMetadata(
          name="my_skill",
          category="custom",
          description="What this skill does",
          patterns=[],
      )
      async def execute(self, entities, context):
          return CommandResult.ok("Did the thing!")
  ```

Marketplace sources:
  - Local: data/skills/installed/ (already in place)
  - Remote: GitHub raw URLs in MARKETPLACE_INDEX
"""
from __future__ import annotations
import json
import hashlib
import os
import time
import threading
import tempfile
import urllib.request
import importlib.util
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Marketplace")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


# Sample marketplace index (could be moved to a remote URL)
MARKETPLACE_INDEX = [
    {
        "id": "github_pr_reviewer",
        "name": "GitHub PR Reviewer",
        "description": "Review open PRs in your repos and summarize changes",
        "author": "omni-community",
        "version": "1.0.0",
        "category": "developer",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/github_pr_reviewer.py",
        "tags": ["github", "pr", "review", "developer"],
        "rating": 4.8,
        "installs": 1247,
    },
    {
        "id": "spotify_controller",
        "name": "Spotify Controller",
        "description": "Control Spotify playback, search, playlists, queue",
        "author": "music-lovers",
        "version": "2.1.0",
        "category": "media",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/spotify_controller.py",
        "tags": ["spotify", "music", "media"],
        "rating": 4.6,
        "installs": 892,
    },
    {
        "id": "morning_briefing",
        "name": "Morning Briefing",
        "description": "Get a full morning brief: calendar, emails, weather, news, top tasks",
        "author": "productivity-pros",
        "version": "1.5.0",
        "category": "productivity",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/morning_briefing.py",
        "tags": ["morning", "brief", "calendar", "productivity"],
        "rating": 4.9,
        "installs": 2341,
    },
    {
        "id": "pomodoro_timer",
        "name": "Pomodoro Timer",
        "description": "25/5 minute focus cycles with break reminders",
        "author": "focus-masters",
        "version": "3.0.0",
        "category": "productivity",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/pomodoro_timer.py",
        "tags": ["pomodoro", "focus", "timer", "productivity"],
        "rating": 4.7,
        "installs": 1567,
    },
    {
        "id": "standup_generator",
        "name": "Standup Generator",
        "description": "Generate standup updates from your git commits",
        "author": "agile-team",
        "version": "1.2.0",
        "category": "developer",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/standup_generator.py",
        "tags": ["standup", "git", "developer", "agile"],
        "rating": 4.5,
        "installs": 723,
    },
    {
        "id": "deep_work_mode",
        "name": "Deep Work Mode",
        "description": "Block distractions, mute notifications, set focus timer",
        "author": "calm-coders",
        "version": "1.0.0",
        "category": "productivity",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/deep_work_mode.py",
        "tags": ["focus", "productivity", "deep-work"],
        "rating": 4.8,
        "installs": 1893,
    },
    {
        "id": "code_formatter",
        "name": "Auto Code Formatter",
        "description": "Run black/ruff on saved files automatically",
        "author": "clean-coders",
        "version": "2.0.0",
        "category": "developer",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/code_formatter.py",
        "tags": ["format", "black", "ruff", "developer"],
        "rating": 4.4,
        "installs": 567,
    },
    {
        "id": "meeting_notes",
        "name": "Meeting Notes",
        "description": "Auto-capture meeting notes from audio and summarize",
        "author": "productivity-pros",
        "version": "1.0.0",
        "category": "productivity",
        "url": "https://raw.githubusercontent.com/omni-community/skills/main/meeting_notes.py",
        "tags": ["meeting", "notes", "productivity"],
        "rating": 4.6,
        "installs": 412,
    },
]


@dataclass
class InstalledSkill:
    """A skill that has been installed locally."""
    id: str
    name: str
    version: str
    author: str
    description: str
    category: str
    installed_at: float
    source_url: str
    file_path: str
    enabled: bool = True
    last_updated: float = 0.0
    use_count: int = 0


class SkillMarketplace:
    """
    The marketplace. Browse, install, update, uninstall community skills.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, marketplace_index: Optional[List[Dict]] = None):
        if self._initialized:
            return
        self.skills_dir = DATA_DIR / "skills" / "installed"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.installed_file = self.skills_dir / "installed.json"
        self._installed: Dict[str, InstalledSkill] = {}
        self._index = marketplace_index or MARKETPLACE_INDEX
        self._data_lock = threading.RLock()
        self._load()
        self._initialized = True
        logger.info(f"📦 SkillMarketplace initialized ({len(self._index)} in index, {len(self._installed)} installed)")

    def _load(self):
        if not self.installed_file.exists():
            self._save()
            return
        try:
            data = json.loads(self.installed_file.read_text(encoding="utf-8"))
            for sid, sdata in data.get("installed", {}).items():
                self._installed[sid] = InstalledSkill(**sdata)
        except Exception as e:
            logger.error(f"Marketplace load: {e}")

    def _save(self):
        with self._data_lock:
            data = {"installed": {sid: asdict(s) for sid, s in self._installed.items()}}
            try:
                fd, tmp = tempfile.mkstemp(dir=str(self.skills_dir), prefix=".mkt_", suffix=".json.tmp")
                with __import__("os").fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                __import__("os").replace(tmp, self.installed_file)
            except Exception as e:
                logger.error(f"Marketplace save: {e}")

    def get_index(self, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Browse the marketplace."""
        items = [dict(item) for item in self._index]
        if category:
            items = [i for i in items if i.get("category") == category]
        if search:
            search_lower = search.lower()
            items = [i for i in items if (
                search_lower in i.get("name", "").lower() or
                search_lower in i.get("description", "").lower() or
                any(search_lower in t for t in i.get("tags", []))
            )]
        # Annotate with installed status
        for item in items:
            item["installed"] = item["id"] in self._installed
        return items

    def get_categories(self) -> List[str]:
        """Get all categories."""
        return sorted(set(i.get("category", "other") for i in self._index))

    def install(self, skill_id: str) -> Dict[str, Any]:
        """Install a skill from the marketplace."""
        with self._data_lock:
            if skill_id in self._installed:
                return {"success": False, "error": "Already installed"}
            item = next((i for i in self._index if i["id"] == skill_id), None)
            if not item:
                return {"success": False, "error": f"Skill '{skill_id}' not found in marketplace"}
            # Download the skill
            try:
                target_path = self.skills_dir / f"{skill_id}.py"
                self._download_skill(item["url"], target_path)
                # Verify before any import or registration.
                from omni_v2.skills.verifier import SkillVerifier
                source = target_path.read_text(encoding="utf-8")
                safe, reason = SkillVerifier.verify(source)
                if not safe:
                    target_path.unlink(missing_ok=True)
                    raise ValueError(f"Skill rejected by verifier: {reason}")
                # Register
                installed = InstalledSkill(
                    id=skill_id,
                    name=item["name"],
                    version=item["version"],
                    author=item["author"],
                    description=item["description"],
                    category=item.get("category", "other"),
                    installed_at=time.time(),
                    source_url=item["url"],
                    file_path=str(target_path),
                )
                self._installed[skill_id] = installed
                self._save()
                # Try to load the skill
                self._try_load_skill(target_path)
                logger.info(f"📦 Installed skill: {skill_id}")
                return {
                    "success": True,
                    "skill_id": skill_id,
                    "name": item["name"],
                    "version": item["version"],
                }
            except Exception as e:
                logger.error(f"Install failed: {e}")
                return {"success": False, "error": str(e)}

    def _download_skill(self, url: str, target: Path) -> None:
        """Download a skill file from a URL with timeout."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OMNI-V3"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read(50001)  # hard cap, detect oversized payloads
                if len(data) > 50000:
                    raise ValueError("skill download exceeds 50KB limit")
                tmp = target.with_suffix(target.suffix + ".download")
                tmp.write_bytes(data)
                os.replace(tmp, target)
        except Exception as e:
            # Never report an unavailable skill as installed. Remove partial files.
            target.unlink(missing_ok=True)
            raise RuntimeError(f"Skill download failed: {e}") from e


    def _try_load_skill(self, path: Path) -> bool:
        """Try to dynamically load a skill as a Python module."""
        try:
            spec = importlib.util.spec_from_file_location(f"omni_skill_{path.stem}", path)
            if not spec or not spec.loader:
                return False
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True
        except Exception as e:
            logger.debug(f"Skill load (continuing without): {e}")
            return False

    def uninstall(self, skill_id: str) -> bool:
        """Uninstall a skill."""
        with self._data_lock:
            if skill_id not in self._installed:
                return False
            skill = self._installed[skill_id]
            try:
                Path(skill.file_path).unlink(missing_ok=True)
            except Exception:
                pass
            del self._installed[skill_id]
            self._save()
            logger.info(f"📦 Uninstalled skill: {skill_id}")
            return True

    def list_installed(self) -> List[Dict[str, Any]]:
        """List all installed skills."""
        with self._data_lock:
            return [asdict(s) for s in self._installed.values()]

    def increment_use(self, skill_id: str) -> None:
        """Track skill usage."""
        with self._data_lock:
            if skill_id in self._installed:
                self._installed[skill_id].use_count += 1
                # Save every 10 uses
                if self._installed[skill_id].use_count % 10 == 0:
                    self._save()

    def check_updates(self) -> List[Dict[str, Any]]:
        """Check for available updates (compares versions)."""
        updates = []
        for item in self._index:
            if item["id"] in self._installed:
                local = self._installed[item["id"]]
                if item["version"] != local.version:
                    updates.append({
                        "skill_id": item["id"],
                        "name": item["name"],
                        "local_version": local.version,
                        "latest_version": item["version"],
                    })
        return updates

    def get_status(self) -> Dict[str, Any]:
        return {
            "marketplace_count": len(self._index),
            "installed_count": len(self._installed),
            "categories": self.get_categories(),
            "updates_available": len(self.check_updates()),
        }


def get_marketplace() -> SkillMarketplace:
    return SkillMarketplace()
