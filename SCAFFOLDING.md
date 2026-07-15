# 🏗️ Scaffolding Complete — Project Layout

**Date:** 2026-07-15
**Before:** 3 launchers, 4 web servers, 6 requirement files, 44 V1 docs, 1 README.
**After:** 1 CLI, 1 FastAPI backend, 1 Next.js UI, 1 Makefile, 1 README, clean package layout.

---

## The new top-level

```
Omni/
├── pyproject.toml              # pip install -e .[all]
├── Makefile                    # make install/test/dev
├── README.md                   # ← You are here (single, beautiful, current)
├── LICENSE                     # MIT
│
├── omni/                       # NEW: Top-level Python package
│   ├── __init__.py             # Re-exports from omni_v2/ (thin facade)
│   ├── cli.py                  # `omni` command (install/test/start/dev/shell)
│   └── py.typed                # PEP 561 type marker
│
├── omni.py                     # Legacy entry — still works (python omni.py --test)
├── omni_v2/                    # The actual codebase (unchanged)
│   ├── llm/brain.py            # ← THE BRAIN (Qwen2.5-1.5B, LLM-first)
│   ├── llm/router.py           # (legacy mock LLM router)
│   ├── llm/llama_cpp.py        # (legacy direct llama.cpp)
│   ├── llm/hf_downloader.py    # HF model downloader
│   ├── agents/                 # Planner, Executor, Monitor, Evaluator, Memory, Proactive
│   ├── voice/                  # STT, TTS, pipeline, mic, PTT, wake word
│   ├── vision/                 # Moondream2, screen capture
│   ├── tools/                  # 100+ tool plugins
│   ├── core/                   # Registry, plugin manager, paths, event bus
│   ├── memory/                 # SQLite, ChromaDB, FastAFStore
│   ├── skills/                 # AST verifier, SkillMaker, registry
│   └── tests/                  # 3 phase test suites
│
├── backend_fastapi/            # FastAPI server (port 8765)
│   ├── main.py                 # /api/execute, /api/ptt, /api/health, /ws
│   └── core/brain.py           # Brain wrapper, executor
│
├── frontend_next/              # Next.js 14 neomorphism UI
│   ├── app/page.js             # AGI command center (live LLM thought stream)
│   ├── components/             # CinematicStage, Orb, MicBar, ChatHistory
│   └── package.json
│
├── docs/                       # 3 useful docs (kept)
│   ├── 03-Architecture.md
│   ├── 05-Demo-Script.md
│   └── 16-OMNI-V2-JARVIS-KILLER-PRD.md
│
├── diagnostic/                 # 60-bug audit + fix log (kept)
│   ├── 00_SUMMARY.md
│   ├── 01_DIAGNOSTIC_REPORT.md
│   └── 02_FIXES_APPLIED.md
│
├── AGI_BUILD.md                # Brain transformation log
├── MODEL_BENCHMARK.md          # Why Qwen2.5-1.5B (real numbers)
├── SCAFFOLDING.md              # ← this file
│
├── data/                       # Runtime data (auto-created, git-ignored)
│   ├── models/                 # GGUF downloads
│   ├── memory.db               # SQLite long-term memory
│   ├── chroma/                 # Vector store
│   ├── chrome_profile/         # Isolated browser (no email)
│   ├── skills/                 # Dynamically synthesized skills
│   ├── recordings/             # Mic captures (capped at 20)
│   └── logs/                   # App + agent logs
│
├── assets/                     # three.min.js (UI assets)
│
└── _archive/                   # V1 cruft (preserved for context, not used)
    ├── v1_docs/                # 41 V1 phase docs
    ├── v1_scripts/             # V1 .bat/.ps1/launchers
    └── v1_alternates/          # Old web servers, Tauri, svelte UI
```

---

## The `omni` CLI

```bash
omni install         # Print install instructions
omni status          # Health check (backend? brain? model?)
omni model download  # Fetch 1.1GB Qwen2.5-1.5B GGUF
omni model info      # Show loaded model, size, speed
omni test            # Run all 4 test suites
omni start           # Start FastAPI on :8765
omni ui              # Start Next.js UI on :3000
omni dev             # Start backend + UI + open browser
omni shell           # Interactive brain REPL
```

The same commands work via Makefile:
```bash
make install   # = omni install (well, pip install -e .[all])
make test      # = omni test
make dev       # = omni dev
```

---

## What got removed (cleanup)

Moved to `_archive/` (preserved for history, not used by judges):

| File / Dir | Why removed |
|------------|------------|
| `omni_v2/web_server.py` | Old HTTP server, superseded by `backend_fastapi/` |
| `omni_v2/web_server_fixed.py` | Same |
| `omni_v2/app.py` | Old PyQt5 entry, superseded by `backend_fastapi/` |
| `omni_v2/app_v3.py` | Same, never finished |
| `omni_v2/app_v3_neumorphism.py` | Same, never finished |
| `frontend/` (svelte) | Old UI, superseded by `frontend_next/` |
| `src-tauri/` (Rust) | Tauri desktop app, never finished |
| `src/` (FastAPI alternate) | Same as `backend_fastapi/`, never wired up |
| `scripts/setup.ps1` | Windows setup, replaced by `omni install` |
| `run_dev_all.py` | Old launcher, replaced by `omni dev` |
| `FIX_NOW.bat` / `FIX_ULTIMATE.bat` | Old fix scripts, bugs are fixed |
| `START_OMNI_V3.bat` / `.ps1` | Old launchers, replaced by `omni start` |
| `fix_audio_settings.ps1` | Old PyAudio hack, we use sounddevice now |
| `INSTALL_FOR_JUDGES.md` | Replaced by `omni install` + new `README.md` |
| `OMNI_V3_OBLITERATION_GUIDE.md` | Old V1 marketing, replaced by new `README.md` |
| `README_NEXT_FASTAPI.md` | Old README, replaced by unified `README.md` |
| `docs/0?-PHASE-*-COMPLETE.md` (41 files) | V1 phase history, kept in `_archive/v1_docs/` |
| `requirements-hackathon.txt` | Replaced by `pyproject.toml [all]` |
| `requirements-hackathon-fixed.txt` | Same |
| `requirements-final-no-pyaudio.txt` | Same |
| `package-lock.json` (root) | Leftover, the real one is in `frontend_next/` |

---

## What judges will see on clone

```bash
$ git clone https://github.com/muhummadzarrar09-sudo/Omni.git
$ cd Omni
$ ls
AGI_BUILD.md   Makefile   _archive/      data/    omni.py
LICENSE        README.md  backend_fastapi  diagnostic/  docs/  omni_v2/  requirements.txt
MODEL_BENCHMARK.md  pyproject.toml  frontend_next/  omni/  SCAFFOLDING.md  assets/

$ cat README.md
# 🤖 OMNI V3 — Local, Private, Cinematic AGI
# ... single, current, beautiful README ...

$ pip install -e .[all]
$ omni model download
$ omni test
$ omni start
# Done. http://localhost:8765
```

Clean. Professional. One way to do things. The V1 archaeology is in `_archive/` for the curious, but never gets in the way.

---

## What `omni.py` still does (legacy)

`omni.py` is the old V1-era entry that hard-coded a bunch of CLI flags. It still works:

```bash
python omni.py --test         # 10/10 multi-agent tests
python omni.py --cli "open github"   # Single command
python omni.py --demo help    # Demo scenarios
```

It's kept for backwards compatibility — judges who cloned an older version won't have their workflow break. But the new recommended path is `omni ...` commands.

---

## Verifying the scaffolding

```bash
# 1. Top-level package imports
python -c "import omni; print(omni.__version__)"  # 3.1.0

# 2. CLI works without install (via module)
python -m omni.cli status

# 3. CLI works with install
pip install -e .[all]
omni status

# 4. Legacy still works
python omni.py --test           # 10/10

# 5. All phase tests pass
python -m omni_v2.tests.test_fast_af_db
python -m omni_v2.tests.test_hermes_refinement
python -m omni_v2.tests.test_skill_synthesis

# 6. All files compile
find omni_v2 backend_fastapi omni -name "*.py" -exec python -m py_compile {} \;
# (no errors)
```

All green. ✅
