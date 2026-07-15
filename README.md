# 🤖 OMNI V3 — Local, Private, Cinematic AGI

> **A local, offline, multi-agent AGI that actually thinks.**
> Powered by a real LLM brain (Qwen2.5-1.5B GGUF), with voice I/O, vision, and 100+ tools.
> Built for the Agentic AI Innovation Challenge 2026. Runs on a GTX 1050 Ti 4GB.

**Built by:** Zarrar + Agent · **Status:** Phase 6.3 complete, all tests passing

---

## ⚡ 30-second quickstart

**Windows (PowerShell):**
```powershell
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
.\install.ps1                    # one-shot, handles llama-cpp prebuilt wheel
omni model download                # fetches 1.1GB Qwen2.5-1.5B GGUF
omni test                          # 10/10 multi-agent + 3 phase tests
omni start                         # http://localhost:8765
```

**Linux / macOS:**
```bash
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
./install.sh                      # one-shot
omni model download                # fetches 1.1GB Qwen2.5-1.5B GGUF
omni test                          # 10/10 multi-agent + 3 phase tests
omni start                         # http://localhost:8765
```

For the **UI** (Next.js 14 neomorphism, separate terminal):

```bash
omni dev                           # backend + UI + browser
```

> **⚠️ Important:** The `install.sh` / `install.ps1` script installs `llama-cpp-python` from a prebuilt wheel index (`--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu`). Without this, pip tries to build llama-cpp-python from source, which requires Visual Studio Build Tools (Windows) or gcc (Linux). If `pip install -e .[all]` ever fails with a CMake error, **run the install script instead**.

---

## 🧠 What makes this an AGI and not another LLM wrapper

| Layer | What it does | Where |
|------|--------------|-------|
| **Brain** | Qwen2.5-1.5B Q4_K_M GGUF, runs locally, does tool-use reasoning | `omni_v2/llm/brain.py` |
| **Agents** | Planner → Executor → Monitor → Evaluator → Memory (closed-loop) | `omni_v2/agents/` |
| **Self-healing** | Eval catches failures, replans with Hermes refinement (4 rules) | `omni_v2/agents/evaluator.py` |
| **Skills** | LLM synthesizes new skills for unknown commands (AST-verified) | `omni_v2/skills/` |
| **Memory** | SQLite (long-term) + ChromaDB (vector) + FastAFStore (sub-ms) | `omni_v2/memory/` |
| **Voice** | faster-whisper STT + Kokoro/SAPI TTS + sounddevice mic | `omni_v2/voice/` |
| **Vision** | Moondream2 1.9B for screen understanding | `omni_v2/vision/turbovlm.py` |
| **Tools** | 100+ aliases: browser, files, code, smart home, calendar | `omni_v2/tools/` |
| **UI** | Next.js 14 neomorphism + live LLM thought stream | `frontend_next/` |
| **API** | FastAPI on :8765 with /api/execute, /api/ptt, /ws | `backend_fastapi/` |

**The LLM is the actual reasoner**, not a fallback. Every user utterance goes:

```
User → Brain (LLM reasons, picks tool) → Executor (dispatches) → Monitor (verifies) → Memory
                                                ↓
                                          Evaluator (on failure: replan, retry, or self-heal)
```

---

## 📦 What's installed (and why)

| Dependency | Size | Required? | What it does |
|------------|------|-----------|--------------|
| `llama-cpp-python` | 5MB | Yes (brain) | Runs the LLM without Ollama overhead |
| `faster-whisper` | 50MB | Voice | Speech-to-text (base.en INT8) |
| `sounddevice` | 1MB | Voice | Mic capture, no PyAudio `-9999` bug |
| `pyttsx3` | 5MB | Voice | TTS fallback (Kokoro optional) |
| `chromadb` | 20MB | Memory | Vector store for semantic recall |
| `pyautogui` | 5MB | Tools | GUI automation |
| `PyQt5` | 100MB | UI (alt) | PyQt5 neomorphism HUD (optional) |
| `fastapi` + `uvicorn` | 30MB | API | Backend HTTP server |
| Qwen2.5-1.5B Q4_K_M | **1.1GB** | Brain | The actual LLM (downloaded separately) |

**Total disk:** ~250MB code + 1.1GB model. **Total RAM:** 2-3GB (CPU) or 1.5GB (GPU offload).

---

## 🎮 CLI reference (`omni`)

After `pip install -e .[all]`:

| Command | What it does |
|---------|--------------|
| `omni install` | Print platform-specific install instructions |
| `omni status` | Health check: backend? brain? model? |
| `omni model download` | Fetch Qwen2.5-1.5B Q4_K_M (~1.1GB) |
| `omni model info` | Show loaded model, size, speed |
| `omni test` | Run all 4 test suites (10/10 + 3 phase tests) |
| `omni start` | Start FastAPI backend on :8765 |
| `omni ui` | Start Next.js UI on :3000 |
| `omni dev` | Start backend + UI + open browser |
| `omni shell` | Interactive brain REPL — type commands, see LLM think |

For Makefile users:

```bash
make install     # pip install -e .[all]
make test        # omni test
make dev         # omni dev
make model-download
```

---

## 🧪 Testing

Four test suites, all run with `omni test`:

| Suite | What it tests | Pass criterion |
|-------|---------------|----------------|
| `omni.py --test` | 10 multi-agent commands (chain, context, tools) | 10/10 |
| `test_fast_af_db` | Sub-ms semantic vector lookup | < 2.0ms |
| `test_hermes_refinement` | Self-healing loop: chrome.exe missing → msedge | Recovers in <1ms |
| `test_skill_synthesis` | LLM synthesizes new skills for unknown goals | AST verifies + executes |

**Result:** ✅ 10/10 multi-agent · ✅ all 3 phase tests · ✅ 0 server tracebacks

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14, http://localhost:3000)                   │
│  Cinematic UI, live LLM thought stream, tool-call cards         │
└────────────────────────────────────────────────────────────────┘
                              ↑ SSE
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  FastAPI backend (http://localhost:8765)                       │
│  /api/execute · /api/execute/stream · /api/ptt · /ws          │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  OMNIBrain (backend_fastapi/core/brain.py)                     │
│   1. LLM brain reasons: emits tool calls OR natural text      │
│   2. Executor dispatches tool calls (100+ tools available)     │
│   3. Monitor verifies, captures failure context                 │
│   4. Evaluator self-heals: replan, retry, or route to ai_chat │
│   5. Memory stored in SQLite + ChromaDB                         │
└────────────────────────────────────────────────────────────────┘
              ↓                       ↓
┌─────────────────────┐    ┌────────────────────────────────┐
│  llama.cpp brain    │    │  omni_v2/tools/ (100+ tools)  │
│  Qwen2.5-1.5B       │    │  browser, files, code, lights, │
│  tool-use JSON      │    │  calendar, system, etc.        │
└─────────────────────┘    └────────────────────────────────┘
```

For full architecture, see [docs/03-Architecture.md](docs/03-Architecture.md) (legacy V1 doc, still accurate at high level).

---

## 📁 Project structure

```
Omni/
├── pyproject.toml              # Modern Python package (pip install -e .)
├── Makefile                    # make install/test/dev/etc.
├── README.md                   # ← You are here
├── LICENSE                     # MIT
│
├── omni/                       # NEW: Top-level package (re-exports omni_v2)
│   ├── __init__.py             # Thin facade over omni_v2
│   ├── cli.py                  # omni command (install/test/start/dev/shell)
│   └── py.typed                # PEP 561 type marker
│
├── omni.py                     # LEGACY: still works (python omni.py --test)
├── omni_v2/                    # The actual codebase
│   ├── llm/                    # Brain (Qwen2.5-1.5B), router, HF downloader
│   ├── agents/                 # Planner, Executor, Monitor, Evaluator, Memory
│   ├── voice/                  # STT, TTS, mic, PTT, wake word
│   ├── vision/                 # Moondream2 (TurboVLM)
│   ├── tools/                  # 100+ tool plugins
│   ├── core/                   # Event bus, paths, plugin manager, registry
│   ├── memory/                 # SQLite, ChromaDB, FastAFStore
│   ├── skills/                 # AST verifier, SkillMaker, registry
│   ├── tests/                  # 3 phase test suites
│   └── ...
│
├── backend_fastapi/            # FastAPI server
│   ├── main.py                 # Endpoints
│   └── core/brain.py           # Brain wrapper, executor
│
├── frontend_next/              # Next.js 14 neomorphism UI
│   └── app/page.js             # AGI command center
│
├── docs/                       # Legacy V1 docs (kept for context)
├── diagnostic/                 # The 60-bug audit + fix log
│   ├── 00_SUMMARY.md           # Scoreboard
│   ├── 01_DIAGNOSTIC_REPORT.md # 60 bugs documented
│   └── 02_FIXES_APPLIED.md     # All fixes
│
├── data/                       # Runtime data (auto-created)
│   ├── models/                 # GGUF models
│   ├── memory.db               # Long-term memory
│   ├── chroma/                 # Vector store
│   ├── chrome_profile/OMNI-Profile/  # Isolated browser profile
│   └── skills/                 # Dynamically synthesized skills
│
├── AGI_BUILD.md                # The LLM brain transformation log
├── MODEL_BENCHMARK.md          # Qwen2.5-1.5B vs 3B vs Llama-3.2-3B vs Gemma-2
├── diagnostic/                 # Bug audit + fix log
└── INSTALL_FOR_JUDGES.md       # (legacy, see `omni install` instead)
```

---

## 🧪 Benchmarks (real numbers, this hardware)

We tested 4 candidate models for OMNI's brain. Winner:

| Model | Cold | tok/s | Tool-call? | Verdict |
|-------|------|-------|------------|---------|
| **Qwen2.5-1.5B Q4_K_M** | 1.9s | **8.6** | ✓ JSON | ✅ **WINNER** |
| Qwen2.5-3B Q4_K_M | 4.2s | 0.9 | ✓ JSON | ❌ 10x slower |
| Llama-3.2-3B Q4_K_M | 5.1s | 0.7 | ✗ function-call | ❌ Wrong format |
| Gemma-2-2B Q4_K_M | 7.3s | — | ERROR | ❌ No system role |

**Why bigger is worse here:** Llama-3.2-3B needs `json_schema` mode for tool calls. Gemma-2 doesn't support system messages. Qwen models are **trained for tool-use JSON** out of the box. On 1050 Ti 4GB, the 1.5B fits with 2.9GB headroom for Whisper + Moondream2 + TTS.

See [MODEL_BENCHMARK.md](MODEL_BENCHMARK.md) for details.

---

## 🎯 Why OMNI wins (judges: start here)

1. **Real LLM brain** — not regex-mock-with-LLM-fallback. The LLM reasons, picks tools, emits structured JSON. Regex is just a fast-path for obvious commands.

2. **Self-healing** — `open notepad` → Errno 2 (not installed) → Evaluator replans → `vscode_open notes.txt` → success. The user sees a working answer, not an error.

3. **Closed-loop memory** — every interaction stored in SQLite + ChromaDB. The LLM sees conversation history (last 5 turns) in every prompt. Preferences persist (e.g. "my name is X", "use Chrome").

4. **Voice + vision + text** — all unified through the same brain. Press PTT (or unmute), see live thought stream, hear it speak.

5. **Cinematic UI** — not a chatbot. Live LLM tokens stream in, tool calls appear as cards, the orb reflects actual brain state (loading, thinking, listening, executing, speaking).

6. **100% local, 100% private** — no cloud calls. The isolated Chrome profile (`data/chrome_profile/OMNI-Profile`) has no email signed in.

7. **1.1GB model, 4GB VRAM** — runs on a $200 laptop. No GPU server needed.

---

## 📚 More docs

- **[diagnostic/00_SUMMARY.md](diagnostic/00_SUMMARY.md)** — 60-bug audit scoreboard
- **[diagnostic/01_DIAGNOSTIC_REPORT.md](diagnostic/01_DIAGNOSTIC_REPORT.md)** — Full bug list
- **[diagnostic/02_FIXES_APPLIED.md](diagnostic/02_FIXES_APPLIED.md)** — All fixes, phase by phase
- **[AGI_BUILD.md](AGI_BUILD.md)** — The brain transformation log (regex → LLM)
- **[MODEL_BENCHMARK.md](MODEL_BENCHMARK.md)** — Why Qwen2.5-1.5B over 3B-class models
- **[docs/03-Architecture.md](docs/03-Architecture.md)** — High-level architecture (V1 era, still accurate)
- **[docs/05-Demo-Script.md](docs/05-Demo-Script.md)** — 3-minute demo script

---

## 🛠️ Hardware targets

| Hardware | Expected speed |
|----------|-----------------|
| 1050 Ti 4GB (target) | 1-2s per brain turn, voice real-time |
| 16GB RAM, no GPU | 5-10s per brain turn, voice works |
| 32GB RAM, RTX 3090 | <500ms per turn, full speed |
| Apple M1/M2 | ~2-4s per turn, native ARM llama.cpp |

---

## License

MIT — see [LICENSE](LICENSE).
