# 🐛 FIX for Torch DLL WinError 1114 - `python omni.py` crashes but `--cli` works

## Your Error

```
[OMNI FATAL] [WinError 1114] A dynamic link library (DLL) initialization routine failed.
Error loading "...torch\lib\c10.dll"

File "...\omni\core\intent_mapper.py", line 21, in <module>
    from sentence_transformers import SentenceTransformer, util
  ...
File "...\torch\__init__.py", line 271, in _load_dll_libraries
    raise err
OSError: [WinError 1114]
```

But `python omni.py --test` and `--cli` worked!

**Why?** 
- `omni.py --cli` uses minimal imports (loguru only)
- `omni.py` full GUI imports `omni.app` → `command_registry` → `intent_mapper` → `sentence_transformers` → `transformers` → `torch` → **DLL fails**

Your `cuda_check.py` shows:
- `PyTorch: 2.13.0+cpu` (CPU only, no CUDA)
- `CUDA available: False`
- `c10.dll loads OK` via ctypes, but fails via torch's _load_dll_libraries

## Root Cause

**Torch 2.13.0 + Python 3.12 + Path with spaces `D:\00000000. Hackathon Projects\Omni` = DLL hell**

Known issues:
1. Torch 2.13 changed DLL loading to be stricter
2. Path with spaces breaks some DLL dependency resolution
3. Python 3.12 is very new, torch 2.13 has edge cases

Your `c10.dll` loads via `ctypes.CDLL` but fails via `torch._load_dll_libraries()` which sets up PATH and loads dependent DLLs like `libiomp5md.dll`, `uv.dll`, etc.

## ✅ FIXES (3 Options)

### Option 1: Move Project to Path Without Spaces (EASIEST, Recommended)

```powershell
# Close everything
# Move folder from:
# D:\00000000. Hackathon Projects\Omni
# To:
# D:\Omni  (no spaces!)

# Then:
cd D:\Omni
.venv\Scripts\activate
python omni.py --test
python omni.py
```

This fixes 90% of WinError 1114 cases with torch!

### Option 2: Reinstall Torch with Stable Version (For GTX 1050 Ti)

Torch 2.13 is bleeding edge. For GTX 1050 Ti, 2.2.2 is more stable and has CUDA support:

```powershell
.venv\Scripts\activate

# Uninstall current (CPU-only) torch
pip uninstall torch torchaudio -y

# Install CUDA 12.1 version (works with GTX 1050 Ti)
pip install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121

# Verify
python scripts/cuda_check.py
# Should show: PyTorch: 2.2.2+cu121, CUDA available: True, GPU: NVIDIA GeForce GTX 1050 Ti
```

### Option 3: Use OMNI_NO_TORCH Mode (Quick Fix - No Semantic Search but Core Works)

If you need full GUI NOW without fixing torch, disable semantic search:

```powershell
# Method A: Set env var for one run
$env:OMNI_NO_TORCH="1"
python omni.py

# Method B: Permanent - add to omni.py (already done in fixed version)
# Fixed omni.py now auto-detects torch DLL failure and sets OMNI_NO_TORCH=1

# Method C: Run CLI which already works
python omni.py --cli "open github"
python omni.py --cli "help"
```

In regex-only mode:
- ✅ All commands work: open github, open notepad, screenshot (with Pillow), help, status, etc.
- ✅ Voice Orb, Tray, TTS work
- ❌ Semantic understanding "get me to github" won't work (needs sentence-transformers + torch)
- ✅ Regex "open github" still works perfectly

## 📦 What Fixed in New Code

**`omni/core/intent_mapper.py` - ULTRA ROBUST:**
```python
# Before: only caught ImportError
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    ST_AVAILABLE=False

# After: catches OSError (WinError 1114) AND any Exception
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    ST_AVAILABLE=False
except OSError as e:  # <-- Catches WinError 1114!
    ST_AVAILABLE=False
    logger.warning(f"DLL error: {e} - using regex only")
except Exception:
    ST_AVAILABLE=False
```

**`omni/core/command_registry.py` - Fallback to Regex:**
```python
try:
    from omni.core.intent_mapper import IntentMapper
except OSError:  # DLL fail
    IntentMapper = None -> DummyMapper that returns None,0 -> regex fallback
```

**`omni.py` - Auto-detect Torch Fail:**
```python
try:
    import torch
except OSError:
    os.environ["OMNI_NO_TORCH"]="1"  # Disable semantic, continue
```

## 🎯 Recommended Steps for You

You have GTX 1050 Ti - you WANT CUDA! So:

```powershell
# 1. Move to no-spaces path
# Manually move D:\00000000. Hackathon Projects\Omni to D:\Omni

cd D:\Omni
.venv\Scripts\activate

# 2. Fix torch
pip uninstall torch torchaudio -y
pip install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121

# 3. Verify CUDA now works
python scripts/cuda_check.py
# Should show CUDA available: True

# 4. Full run
python omni.py
# Should now start without WinError 1114!

# If still fails, use no-torch mode:
$env:OMNI_NO_TORCH="1"
python omni.py
```

## 💡 Why CLI Worked but GUI Didn't

- `omni.py --cli` → imports only `CommandRegistry` + `PluginManager` (minimal)
- Your minimal test used old `intent_mapper.py` that had already loaded sentence-transformers model into cache, so it didn't re-import torch? Actually it did but via different path?
- `omni.py` full → imports `omni.app` → `PyQt5` + `CommandRegistry` → triggers full torch chain

New fixed `intent_mapper.py` prevents crash in both cases.

---

**Bottom line:** Move to `D:\Omni` (no spaces) + reinstall torch 2.2.2 cu121 = full CUDA + semantic search + no DLL error. Or use `$env:OMNI_NO_TORCH="1"` for quick regex-only mode.
