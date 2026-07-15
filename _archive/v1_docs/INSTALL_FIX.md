# 🔧 The llama-cpp-python Build Fix

**Date:** 2026-07-15
**Problem:** Judges on Windows can't `pip install -e .[all]` because pip falls back to building `llama-cpp-python` from source, which needs MSVC Build Tools.

---

## The root cause

`llama-cpp-python` is a C++ binding for llama.cpp. The PyPI main index only has `.tar.gz` source distributions for most versions. Pip tries to build from source → fails because no MSVC.

The prebuilt wheels (`.whl` files) live at `https://abetlen.github.io/llama-cpp-python/whl/cpu` (and `.../whl/cu121` for NVIDIA). You have to tell pip to look there.

## The fix

I added **two one-shot install scripts** that handle this:

| File | Platform | Usage |
|------|----------|-------|
| `install.sh` | Linux / macOS | `./install.sh` or `./install.sh --cuda cu121` |
| `install.ps1` | Windows | `.\install.ps1` or `.\install.ps1 -Cuda cu121` |

Both scripts:
1. Detect Python
2. Create a venv if not in one
3. **Install `llama-cpp-python` first from the prebuilt wheel index**
4. Then install the rest of OMNI (`pip install -e .[all]`)
5. Print next-step instructions

## What you should run on Windows

```powershell
cd D:\Omni

# Clean up the half-installed state
pip uninstall -y omni-agi llama-cpp-python numpy
rmdir /s /q .venv  # if you have one
rmdir /s /q D:\Omni\omni_agi.egg-info  # if it exists

# Now run the one-shot installer
.\install.ps1

# Then download the model and test
omni model download
omni test
omni start
```

## What `install.ps1` does, step by step

```powershell
$py = python                       # find Python
# (skip venv if you're in one already)
& $py -m venv .venv                # create venv if needed
. .\.venv\Scripts\Activate.ps1    # activate
& $py -m pip install --upgrade pip wheel setuptools

# THIS is the critical step — prebuilt wheel, no MSVC needed
& $py -m pip install "llama-cpp-python" `
    --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu" `
    --quiet

# Now the rest of OMNI (deps are already installed by your previous pip attempt)
& $py -m pip install -e .[all] --quiet
```

The `llama-cpp-python` line is the key. That `--extra-index-url` points pip at a separate index that has **pre-built wheels** for Windows/Python 3.12. No CMake, no nmake, no MSVC build tools. Just a 5MB download.

## Why the build failed before

When you ran:
```
pip install llama-cpp-python
```

pip went to PyPI, found only `.tar.gz` for the version it wanted, and tried to build it. The build needs:
- **Windows:** Visual Studio Build Tools ("Desktop development with C++" workload), or
- **Linux:** gcc/clang, or
- **macOS:** Xcode Command Line Tools

You don't have any of those, so it died at:
```
CMake Error: CMAKE_C_COMPILER not set, after EnableLanguage
```

## If you already have a C++ compiler (Visual Studio Build Tools / gcc / Xcode)

Then `pip install -e .[all]` will work directly. The install scripts are just a convenience that skips the build.

## Verification

After running the install script, you should see:

```
$ python -c "import llama_cpp; print(llama_cpp.__version__)"
0.3.34

$ python -c "import omni; print(omni.__version__)"
3.1.0

$ omni test
✅ PHASE 6.1 FAST AF DB & SEMANTIC ROUTER: 100% PASSED
✅ PHASE 6.2 HERMES MULTI-ORCHESTRATOR REFINEMENT LOOP: 100% PASSED
✅ PHASE 6.3 DYNAMIC SKILL SYNTHESIS: 100% PASSED
10/10 V2 tests passed (chain commands + context)
```

## Files added in this fix

- `install.sh` (Linux/macOS one-shot installer)
- `install.ps1` (Windows one-shot installer)
- `INSTALL_FIX.md` (this file)

## Files updated

- `omni/cli.py` — `omni install` now points at the scripts
- `README.md` — quickstart uses the scripts
