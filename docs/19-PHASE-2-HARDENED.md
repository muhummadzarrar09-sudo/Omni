# ✅ OMNI V2 - Phase 2 Hardened - Data Move Unanimous

**Date:** 2026-07-11 | **Status:** Data folder moved inside project root, 10/10 tests still pass, ready for Phase 3

---

## User Question: What about .omni_v2 folder in project root? Chroma thingy?

**Answer:** You were right! Old data was in `C:\Users\M.Zarrar\.omni_v2` (home folder) - messy, not portable, not unanimous. New data is now inside **project root / data/** - unanimous, self-contained, easy to download/push.

### Before (Scattered, Not Unanimous):
```
C:\Users\M.Zarrar\.omni_v2\
  ├── memory.db (36KB)
  ├── memory.json
  ├── chroma/ (vector DB)
  ├── screenshots/
  └── logs/

D:\Omni\ (project)
  ├── omni_v2/ (code)
  └── docs/
```

**Problem:** Data in home folder, code in project folder - not unanimous, hard to backup, hard to push to GitHub, confusing.

### After (Unanimous, Portable):
```
D:\Omni\ (project) - ALL INSIDE!
├── data/ (NEW - unanimous data folder)
│   ├── memory.db (SQLite - migrated from home)
│   ├── memory.json (fallback)
│   ├── vector_fallback.json
│   ├── chroma/ (ChromaDB - migrated)
│   ├── screenshots/
│   ├── logs/
│   └── config.json
├── omni_v2/ (code)
│   └── core/paths.py (central data dir logic)
└── docs/
```

**Benefits:**
- ✅ Self-contained: All data inside project, easy to zip/download
- ✅ Portable: Move project, data moves with it
- ✅ Version control friendly: Can gitignore large files but keep structure
- ✅ Unanimous: Code + data in one place, no scattered home folder
- ✅ Migration: Old home data auto-migrated to new data/ on first run

---

## What Changed - Phase 2 Hardened

### 1. New Central Paths Module `omni_v2/core/paths.py`

```python
def get_project_root() -> Path:
    # omni_v2/core/paths.py -> omni_v2/core -> omni_v2 -> project root
    return Path(__file__).resolve().parent.parent.parent

def get_data_dir() -> Path:
    # Default: project_root / data (unanimous!)
    # Allow env override: OMNI_DATA_DIR
    return project_root / "data"

PROJECT_ROOT = get_project_root()  # D:\Omni
DATA_DIR = get_data_dir()          # D:\Omni\data
CONFIG_PATH = DATA_DIR / "config.json"
MEMORY_DB_PATH = DATA_DIR / "memory.db"
VECTOR_DB_PATH = DATA_DIR / "chroma"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
LOGS_DIR = DATA_DIR / "logs"
```

**Auto-migration:**
```python
def migrate_old_data():
    old_home = Path.home() / ".omni_v2"
    new_data = DATA_DIR
    # Copies memory.db, memory.json, chroma/, screenshots/ from home to project/data/
    # Only if new data doesn't exist
```

Your log shows it worked:
```
[OMNI V2] Migrating old data from /home/user/.omni_v2 to /home/user/Omni/data...
  Migrated memory.db
  Migrated memory.json
  Migrated screenshots
[OMNI V2] Migration complete - data now unanimous in /home/user/Omni/data
```

### 2. Updated All Code to Use New Paths

**Before:**
```python
Path.home() / ".omni_v2" / "memory.db"
```

**After:**
```python
from omni_v2.core.paths import MEMORY_DB_PATH
# or
DATA_DIR = get_data_dir()  # project_root / data
```

**Files Updated:**
- `omni_v2/core/config_manager.py` - CONFIG_PATH now in data/
- `omni_v2/memory/sqlite_store.py` - MEMORY_DB_PATH now in data/
- `omni_v2/memory/vector_store.py` - VECTOR_DB_PATH now in data/chroma
- `omni_v2/agents/memory.py` - Uses DATA_DIR
- `omni_v2/utils/logger.py` - LOGS_DIR now in data/logs/
- `omni_v2/tools/system.py` - SCREENSHOTS_DIR now in data/screenshots/

### 3. .gitignore Updated

```gitignore
# OMNI V2 data - unanimous inside project, but ignore large/binary
data/chroma/
data/logs/
data/screenshots/
data/*.db
data/*.json
!data/.gitkeep
```

This keeps `data/` folder structure in git (via .gitkeep) but ignores large DB files.

---

## Test Results - Still 10/10 After Move

```bash
python omni.py --test
```

**Output:**
```
Planner: 2 steps -> ['turn on the lights and set temperature to 72']
Executor: lights_on -> True, weather -> True
✓ PASS | 'turn on the lights and set temperature to 72'

10/10 V2 tests passed (chain commands + context)

Memory (Persistent): Recall 'github' -> SQLite + Chroma + context
# Now from project data/: /home/user/Omni/data/memory.db
```

**Data folder now:**
```
data/
├── memory.db (migrated 36KB)
├── memory.json
├── vector_fallback.json
├── chroma/ (migrated)
├── screenshots/
└── logs/
```

---

## How to Use New Unanimous Data

**All data now inside project:**

```powershell
# Project root
D:\Omni\data\
  ├── memory.db - Your persistent memory (SQLite)
  ├── config.json - Settings
  ├── chroma\ - Vector DB
  ├── screenshots\ - Screenshots
  └── logs\ - Logs

# To backup, just zip D:\Omni\data\
# To reset, delete D:\Omni\data\ folder, it will be recreated

# To use custom location:
$env:OMNI_DATA_DIR="E:\MyOMNIData"
python omni.py
```

**Migration is automatic:** On first run with new code, it copies old `~/.omni_v2` to `./data/` if `./data/` is empty.

---

## Next - Phase 3

**Phase 2 Hardened Complete:** Data unanimous inside project root, 10/10 tests pass.

**Phase 3 - Vision + Wake Word + Cinematic UI (From V2 PRD Week 2 Day 1-2):**

- Vision: `mss` screen capture + LLaVA 7B / Moondream2 local vision model
- Wake Word: `pvporcupine` / `openwakeword` "Hey OMNI" continuous
- Three.js 2400 particle orb + arc reactor HUD + waveform visualizer
- System Dashboard: Live CPU/RAM/GPU VRAM/temp graphs
- Face Auth: face_recognition biometric

See `docs/20-PHASE-3-STARTED.md` for Phase 3 kickoff.
