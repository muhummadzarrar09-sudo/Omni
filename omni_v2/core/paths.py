"""
OMNI V2 Paths - Centralized Data Directory (Unanimous, Portable)
All data now inside project root / data/ instead of ~/.omni_v2/
This makes it self-contained, portable, easy to download/push
"""

from pathlib import Path
import os

def get_project_root() -> Path:
    """Get project root - where omni.py and README.md are"""
    # omni_v2/core/paths.py -> omni_v2/core -> omni_v2 -> project root
    current = Path(__file__).resolve()
    # Go up 2 levels: core/ -> omni_v2/ -> project root
    project_root = current.parent.parent.parent
    return project_root

def get_data_dir() -> Path:
    """Get data directory inside project root - unanimous and portable"""
    # Allow env override for custom location
    env_data_dir = os.environ.get("OMNI_DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir).expanduser().resolve()
    
    # Default: project_root / data
    project_root = get_project_root()
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_omni_v2_data_dir() -> Path:
    """Get .omni_v2 equivalent inside data/ - for backwards compat"""
    data_dir = get_data_dir()
    omni_v2_dir = data_dir / ".omni_v2"
    # For unanimous, we actually want data/ to BE the omni_v2 data dir
    # So return data_dir directly for new code, but keep this for migration
    return data_dir

# Central paths
PROJECT_ROOT = get_project_root()
DATA_DIR = get_data_dir()

# Specific data paths
CONFIG_PATH = DATA_DIR / "config.json"
MEMORY_DB_PATH = DATA_DIR / "memory.db"
VECTOR_DB_PATH = DATA_DIR / "chroma"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
LOGS_DIR = DATA_DIR / "logs"
VECTOR_FALLBACK_PATH = DATA_DIR / "vector_fallback.json"
MEMORY_JSON_PATH = DATA_DIR / "memory.json"

# Ensure all exist
for p in [DATA_DIR, VECTOR_DB_PATH, SCREENSHOTS_DIR, LOGS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

def migrate_old_data():
    """Migrate old ~/.omni_v2 data to new ./data/ if needed"""
    old_home = Path.home() / ".omni_v2"
    new_data = DATA_DIR

    if not old_home.exists():
        return

    # Only migrate if new data is empty or doesn't have key files
    if (new_data / "memory.db").exists() and (new_data / "chroma").exists():
        # Already migrated
        return

    print(f"[OMNI V2] Migrating old data from {old_home} to {new_data}...")

    try:
        import shutil
        # Migrate memory.db
        old_db = old_home / "memory.db"
        new_db = new_data / "memory.db"
        if old_db.exists() and not new_db.exists():
            shutil.copy2(old_db, new_db)
            print(f"  Migrated memory.db: {old_db} -> {new_db}")

        # Migrate memory.json
        old_json = old_home / "memory.json"
        new_json = new_data / "memory.json"
        if old_json.exists() and not new_json.exists():
            shutil.copy2(old_json, new_json)
            print(f"  Migrated memory.json")

        # Migrate chroma folder
        old_chroma = old_home / "chroma"
        new_chroma = new_data / "chroma"
        if old_chroma.exists() and not new_chroma.exists():
            shutil.copytree(old_chroma, new_chroma, dirs_exist_ok=True)
            print(f"  Migrated chroma folder")

        # Migrate screenshots
        old_screenshots = old_home / "screenshots"
        new_screenshots = new_data / "screenshots"
        if old_screenshots.exists():
            new_screenshots.mkdir(exist_ok=True)
            for f in old_screenshots.glob("*"):
                if f.is_file():
                    dest = new_screenshots / f.name
                    if not dest.exists():
                        shutil.copy2(f, dest)
            print(f"  Migrated screenshots")

        print(f"[OMNI V2] Migration complete - data now unanimous in {new_data}")
        print(f"[OMNI V2] Old data still at {old_home} (can be deleted manually)")

    except Exception as e:
        print(f"[OMNI V2] Migration failed: {e} - continuing with fresh data")

# Auto-migrate on import
try:
    migrate_old_data()
except Exception as e:
    print(f"[OMNI V2] Auto-migration failed: {e}")
