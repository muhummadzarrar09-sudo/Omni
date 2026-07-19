"""
OMNI V3 - User Profile Store (Phase 1A: It Remembers You)

Persistent JSON profile of the user. OMNI uses this to:
  - Greet by name (AIM #2)
  - Personalize responses
  - Track behavioral patterns
  - Remember preferences across sessions

Storage: data/profiles/user.json (portable, human-readable, git-friendly)
"""
from __future__ import annotations
import json
import time
import threading
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("UserProfile")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path(__file__).resolve().parents[2] / "data"


SCHEMA_VERSION = 2


@dataclass
class UserProfile:
    """Persistent user profile for personalization."""

    # Identity
    name: str = ""
    pronouns: str = ""
    timezone: str = "UTC"
    location: str = ""

    # Schedule
    work_start_hour: int = 9
    work_end_hour: int = 17
    work_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    lunch_hour: int = 13

    # Preferences
    favorite_voice: str = "jarvis"
    formality: str = "casual"
    theme: str = "dark"
    wake_word_sensitivity: float = 0.5
    proactive_frequency: str = "normal"

    # Personal
    hobbies: List[str] = field(default_factory=list)
    favorite_music: str = "lo-fi"
    pet_names: Dict[str, str] = field(default_factory=dict)
    family: Dict[str, str] = field(default_factory=dict)
    birthday: str = ""

    # Projects
    current_projects: List[Dict[str, str]] = field(default_factory=list)
    active_apps: List[str] = field(default_factory=list)

    # Behavioral patterns (learned)
    avg_daily_commands: int = 0
    most_used_tools: Dict[str, int] = field(default_factory=dict)
    peak_hours: List[int] = field(default_factory=list)
    longest_session_min: int = 0
    total_commands: int = 0

    # Meta
    created_at: float = 0.0
    updated_at: float = 0.0
    version: int = SCHEMA_VERSION

    # Defensive: prevent crashes on unknown fields when reading older files
    def __setattr__(self, name: str, value: Any) -> None:
        # Coerce lists/dicts to avoid surprises from JSON
        if name == "hobbies" and not isinstance(value, list):
            value = list(value) if value else []
        elif name == "work_days" and not isinstance(value, list):
            value = list(value) if value else [0, 1, 2, 3, 4]
        elif name in ("pet_names", "family", "most_used_tools") and not isinstance(value, dict):
            value = dict(value) if value else {}
        elif name in ("current_projects", "active_apps", "peak_hours") and not isinstance(value, list):
            value = list(value) if value else []
        super().__setattr__(name, value)


class UserProfileStore:
    """
    Thread-safe, persistent user profile.
    Singleton. Atomic file writes (no partial corruption).
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

    def __init__(self, profile_dir: Optional[Path] = None):
        if self._initialized:
            return
        self.profile_dir = profile_dir or (DATA_DIR / "profiles")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.profile_dir / "user.json"
        self._data_lock = threading.RLock()
        self._profile: UserProfile = UserProfile()
        self._load()
        self._initialized = True
        logger.info(f"👤 UserProfile loaded from {self.profile_file}")

    def _load(self):
        """Load profile from JSON, with corruption recovery."""
        with self._data_lock:
            if not self.profile_file.exists():
                # First run - create default
                self._profile = UserProfile(
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                self._save()
                logger.info("👤 Created default user profile")
                return
            try:
                raw = json.loads(self.profile_file.read_text(encoding="utf-8"))
                # Filter out unknown fields (forward compat)
                known = {f.name for f in UserProfile.__dataclass_fields__.values()}
                filtered = {k: v for k, v in raw.items() if k in known}
                self._profile = UserProfile(**filtered)
                # Migrate if needed
                if self._profile.version < SCHEMA_VERSION:
                    logger.info(f"👤 Migrating profile v{self._profile.version} -> v{SCHEMA_VERSION}")
                    self._profile.version = SCHEMA_VERSION
                    self._save()
            except json.JSONDecodeError as e:
                logger.error(f"👤 Profile JSON corrupted: {e} - backing up & resetting")
                # Backup corrupted file, start fresh
                backup = self.profile_file.with_suffix(".corrupted.json")
                try:
                    backup.write_text(self.profile_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
                self._profile = UserProfile(created_at=time.time(), updated_at=time.time())
                self._save()
            except Exception as e:
                logger.error(f"👤 Profile load failed: {e}")
                self._profile = UserProfile(created_at=time.time(), updated_at=time.time())

    def _save(self):
        """Atomic write: write to temp file, then rename."""
        with self._data_lock:
            self._profile.updated_at = time.time()
            try:
                # Write to temp file in same dir (atomic rename)
                fd, tmp_path = tempfile.mkstemp(
                    dir=str(self.profile_dir),
                    prefix=".user_",
                    suffix=".json.tmp",
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(asdict(self._profile), f, indent=2, ensure_ascii=False)
                        f.flush()
                        os.fsync(f.fileno())
                    # Atomic rename
                    os.replace(tmp_path, self.profile_file)
                except Exception:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                    raise
            except Exception as e:
                logger.error(f"👤 Profile save failed: {e}")

    # ===== GET =====

    def get(self, key: str, default: Any = None) -> Any:
        """Get a field value."""
        with self._data_lock:
            return getattr(self._profile, key, default)

    def get_all(self) -> Dict[str, Any]:
        """Get full profile as dict."""
        with self._data_lock:
            return asdict(self._profile)

    def is_empty(self) -> bool:
        """Returns True if profile has no name set yet (first-time user)."""
        with self._data_lock:
            return not self._profile.name

    def greeting_name(self) -> str:
        """Return the name to use in greetings, or empty string if not set."""
        return self.get("name", "")

    # ===== SET =====

    def set(self, key: str, value: Any) -> bool:
        """Set a single field. Returns True if successful."""
        if not hasattr(self._profile, key):
            logger.warning(f"👤 Unknown profile field: {key}")
            return False
        try:
            with self._data_lock:
                setattr(self._profile, key, value)
                self._save()
            return True
        except Exception as e:
            logger.error(f"👤 set({key}) failed: {e}")
            return False

    def set_many(self, **kwargs) -> Dict[str, bool]:
        """Set multiple fields as one atomic update."""
        results = {}
        with self._data_lock:
            valid = True
            for k in kwargs:
                if not hasattr(self._profile, k):
                    results[k] = False
                    valid = False
            if not valid:
                for k in kwargs:
                    results.setdefault(k, False)
                return results
            try:
                for k, v in kwargs.items():
                    setattr(self._profile, k, v)
                    results[k] = True
                self._save()
            except Exception as exc:
                logger.error(f"set_many failed: {exc}")
                return {k: False for k in kwargs}
        return results

    def forget(self, key: str) -> bool:
        """Reset a field to its default value."""
        defaults = UserProfile()
        if not hasattr(defaults, key):
            return False
        default_value = getattr(defaults, key)
        # Handle mutable defaults from field(default_factory=...)
        from dataclasses import fields, MISSING
        for f in fields(defaults):
            if f.name == key:
                if f.default_factory is not MISSING:
                    default_value = f.default_factory()
                break
        return self.set(key, default_value)

    def reset_all(self) -> bool:
        """Reset entire profile to defaults. DESTRUCTIVE."""
        with self._data_lock:
            self._profile = UserProfile(created_at=time.time(), updated_at=time.time())
            self._save()
            logger.warning("👤 User profile reset to defaults")
            return True

    # ===== BEHAVIORAL LEARNING =====

    def record_command(self, command: str) -> None:
        """Record that a command was issued. Used to compute behavioral stats."""
        with self._data_lock:
            self._profile.total_commands += 1
            # Update rolling 7-day command count (simplified)
            self._profile.avg_daily_commands = int(self._profile.total_commands / 7) if self._profile.total_commands > 0 else 0
            # Save every 10 commands to reduce IO
            if self._profile.total_commands % 10 == 0:
                self._save()

    def record_tool_usage(self, tool: str) -> None:
        """Record a tool call for most-used tracking."""
        with self._data_lock:
            self._profile.most_used_tools[tool] = self._profile.most_used_tools.get(tool, 0) + 1
            if sum(self._profile.most_used_tools.values()) % 25 == 0:
                self._save()

    def record_session_duration(self, duration_min: int) -> None:
        """Record how long a session lasted. Updates longest_session_min."""
        with self._data_lock:
            if duration_min > self._profile.longest_session_min:
                self._profile.longest_session_min = duration_min
                self._save()

    def record_peak_hour(self, hour: int) -> None:
        """Track hours when user is most active."""
        with self._data_lock:
            if hour not in self._profile.peak_hours:
                self._profile.peak_hours.append(hour)
                self._profile.peak_hours.sort()
                if len(self._profile.peak_hours) > 24:
                    self._profile.peak_hours = self._profile.peak_hours[-24:]
                self._save()

    def get_top_tools(self, n: int = 5) -> List[tuple]:
        """Return the N most-used tools as [(tool, count), ...]."""
        with self._data_lock:
            tools = self._profile.most_used_tools.items()
            return sorted(tools, key=lambda x: -x[1])[:n]

    # ===== STATS =====

    def get_stats(self) -> Dict[str, Any]:
        """Return user-facing stats for the UI."""
        with self._data_lock:
            return {
                "name": self._profile.name,
                "total_commands": self._profile.total_commands,
                "avg_daily_commands": self._profile.avg_daily_commands,
                "longest_session_min": self._profile.longest_session_min,
                "peak_hours": self._profile.peak_hours,
                "top_tools": self.get_top_tools(5),
                "active_projects": [p.get("name", "?") for p in self._profile.current_projects],
                "member_since": self._profile.created_at,
                "days_using_omni": int((time.time() - self._profile.created_at) / 86400) if self._profile.created_at > 0 else 0,
            }


def get_user_profile() -> UserProfileStore:
    """Get the singleton UserProfileStore."""
    return UserProfileStore()
