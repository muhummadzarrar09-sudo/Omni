"""
Skill Registry - Phase 6.3 Dynamic Skill Loader & Fast AF DB Indexer
Loads synthesized python skill files and registers them into PluginManager & FastAFStore.
"""
import time
import importlib.util
import inspect
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SkillRegistry")

from omni_v2.core.plugin_manager import PluginManager, CommandPlugin
try:
    from omni_v2.memory.fast_af_store import get_fast_af_store
except ImportError:
    get_fast_af_store = None

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.cwd() / "data"

SKILLS_DIR = DATA_DIR / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

class SkillRegistry:
    """Manages loading, registering, and indexing dynamic custom skills"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SkillRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, plugin_manager: Optional[PluginManager] = None):
        if self._initialized and self.plugin_manager:
            return
        self._lock = threading.RLock()
        self.plugin_manager = plugin_manager or PluginManager()
        self.fast_af = get_fast_af_store() if get_fast_af_store else None
        self.loaded_skills: Dict[str, CommandPlugin] = {}
        self._initialized = True
        logger.info("SkillRegistry Phase 6.3 initialized (dynamic skill loader + re-entrant lock)")

    def load_all_skills(self) -> int:
        """Load all custom_*.py skills from data/skills/ into PluginManager + FastAFStore"""
        t0 = time.perf_counter()
        if not SKILLS_DIR.exists():
            return 0

        count = 0
        for py_file in SKILLS_DIR.glob("custom_*.py"):
            if py_file.is_file():
                if self.load_skill_file(py_file):
                    count += 1

        lat_ms = (time.perf_counter() - t0) * 1000.0
        logger.info(f"🧬 Loaded & indexed {count} custom skills from {SKILLS_DIR} ({lat_ms:.2f}ms)")
        return count

    def load_skill_file(self, file_path: Path) -> Optional[CommandPlugin]:
        """Load a single custom skill python file dynamically with thread safety"""
        with self._lock:
            if not file_path.exists() or not file_path.is_file():
                logger.error(f"Skill file {file_path} does not exist")
                return None

            module_name = file_path.stem
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(file_path))
                if not spec or not spec.loader:
                    return None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find CommandPlugin subclass
                for attr_name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, CommandPlugin) and obj is not CommandPlugin:
                        skill_instance = obj()
                        meta = getattr(skill_instance, "metadata", None)
                        if meta and meta.name:
                            # 1. Register into PluginManager
                            self.plugin_manager.register(skill_instance)
                            self.loaded_skills[meta.name] = skill_instance

                            # 2. Register into Fast AF DB Tier 1 (<1ms)
                            if self.fast_af:
                                self.fast_af.remember_skill(
                                    name=meta.name,
                                    category=meta.category or "custom_skill",
                                    description=meta.description or "Dynamic custom skill",
                                    patterns=meta.patterns or [meta.name],
                                    examples=meta.examples or [meta.description],
                                    persist=True
                                )
                            logger.info(f"✨ Skill '{meta.name}' loaded and registered from {file_path.name}")
                            return skill_instance
            except Exception as e:
                logger.error(f"Failed to load skill file {file_path}: {e}")

            return None

def get_skill_registry(plugin_manager: Optional[PluginManager] = None) -> SkillRegistry:
    return SkillRegistry(plugin_manager)
