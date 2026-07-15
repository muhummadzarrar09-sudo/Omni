# 🤖 OMNI V3 — A Local, Private, Cinematic AGI

> **"A butler that thinks. Not a chatbot. Not a wrapper. A JARVIS that actually does stuff."**
>
> Multi-agent local AGI powered by Qwen2.5-1.5B. Voice I/O. Memory that remembers. Personality that has opinions. **All private. All offline. All yours.**

[![AIM Score](https://img.shields.io/badge/AIM-10%2F10-brightgreen)](docs/AIM.md)
[![Tests](https://img.shields.io/badge/tests-110%2B%20passing-brightgreen)](docs/PHASE_3_DONE.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![MIT](https://img.shields.io/badge/license-MIT-green)]()

---

## What is OMNI?

OMNI is a **local AGI assistant** that runs entirely on your laptop. It:

- **Thinks** with a real 1.5B-parameter LLM brain (Qwen2.5, runs in llama.cpp)
- **Hears** you with Whisper voice recognition
- **Speaks** with Microsoft Edge natural voices (6 personas)
- **Sees** your screen with vision models
- **Acts** with 100+ tools (browser, files, code, calendar, smart home, etc.)
- **Remembers** what you did yesterday, this morning, last week
- **Has opinions** — "You've opened Twitter 3 times today. Working or procrastinating?"
- **Self-heals** when tools fail
- **Defends** against 16+ attack vectors (path traversal, shell injection, prompt injection)

**No cloud. No API keys. No data leaves your machine. Ever.**

---

## ⚡ 30-second quickstart

```powershell
# Windows
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
.\install.ps1                # one-shot installer
omni model download            # fetches 1.1GB Qwen brain
omni test                      # 110+ tests
omni start                     # backend on :8765
```

```bash
# Linux / macOS
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
./install.sh
omni model download
omni test
omni start
```

For the **cinematic UI** (separate terminal):
```bash
cd frontend_next
npm install
npm run dev                    # UI on :3000
```

Or just open http://localhost:8765/docs for the FastAPI Swagger UI.

---

## 🎯 The AIM — 10/10 Achieved

Every AGI demo on YouTube has the same problem: it's a chatbot in disguise. OMNI hits all 10 AIM features:

| # | Feature | What it does | Phase |
|---|---------|--------------|-------|
| 1 | 🗣️ **Wake word "Hey OMNI"** | Always-listening, sub-100ms, 3 backends | 0 |
| 2 | 👋 **Greets by name** | "Good morning Zarrar" with yesterday's recap | 1 |
| 3 | 🧠 **Shows thinking** | Live LLM token stream on screen | 0 |
| 4 | 🛠️ **Shows tools** | Cards appear as it acts | 0 |
| 5 | 🔁 **Shows recovery** | Self-healing visibly tries alternatives | 0 |
| 6 | 💡 **Speaks first** | Battery warnings, break reminders, 9 rules | 0 |
| 7 | 🎭 **Has a voice** | 6 natural personas (jarvis, friday, aria, etc.) | 0 |
| 8 | 🧠 **Remembers** | "Yesterday you worked on github" | 1 |
| 9 | 😏 **Has opinions** | "That's 3 commits today. You good. 🚀" | 2 |
| 10 | ⚡ **Cinematic & fast** | 1:46 auto-demo, onboarding, stats dashboard | 3 |

**The 2-minute wow is built.** See [docs/AIM.md](docs/AIM.md) for the full spec.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14, :3000) — Cinematic UI                  │
│  Live thought stream · Tool call cards · Brain state orb     │
└────────────────────────────────────────────────────────────────┘
                              ↑ WebSocket + SSE
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  FastAPI backend (:8765) — 50+ endpoints                       │
│  /api/execute · /api/memory/* · /api/personality · /api/demo   │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  OMNIBrain — Multi-agent ReAct loop                            │
│                                                                  │
│  ┌──────────┐   ┌────────┐   ┌─────────┐   ┌───────────┐        │
│  │ Planner  │ → │Executor│ → │ Monitor │ → │ Evaluator │        │
│  └──────────┘   └────────┘   └─────────┘   └───────────┘        │
│       ↑                                              │            │
│       └────────── self-heal on failure ─────────────┘            │
│                                                                  │
│  Plus: Proactive (V2) · Memory · Personality · Opinion         │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  LLM Brain (Qwen2.5-1.5B GGUF, llama.cpp)                       │
│  + 100+ Tools · Voice (Whisper/edge-tts) · Vision · Wake Word │
└────────────────────────────────────────────────────────────────┘
```

See [docs/03-Architecture.md](docs/03-Architecture.md) for the full picture.

---

## 🎬 The 2-Minute Demo

```powershell
# Start the cinematic auto-demo from API
curl -X POST http://localhost:8765/api/demo -H "Content-Type: application/json" -d "{\"action\":\"start\"}"
```

**The 8 scenes (1:46 total):**

1. **Welcome to OMNI** (12s) — "I'm OMNI V3, a local AGI. No cloud, no spying."
2. **I can hear you** (12s) — Say something, live transcription shown
3. **I can think** (18s) — "What's on my plate today?" → multi-tool execution with visible thought stream
4. **I can take action** (12s) — "Open github" → browser opens
5. **I can recover** (18s) — Simulated failure → self-healing fallback
6. **I can remember** (14s) — "What did I do yesterday?" → memory recall
7. **I can speak first** (12s) — Proactive suggestion triggered
8. **I'm yours** (8s) — Closing statement

---

## 🧪 The Tests

**110+ tests, 11 test suites, 100% pass, 0 failures.**

```bash
omni test    # runs all 11 suites
```

| Suite | Tests | What it covers |
|-------|-------|-----------------|
| `test_security_guardrails` | 10 | 16 attack vectors: path traversal, shell injection, JSON DoS, etc. |
| `test_fast_af_db` | 5 | Sub-ms semantic vector lookup |
| `test_hermes_refinement` | 5 | Self-healing loop: chrome.exe missing → msedge |
| `test_skill_synthesis` | 6 | LLM synthesizes new skills for unknown goals |
| `test_user_profile` | 12 | Persistent user profile (Phase 1) |
| `test_session_memory` | 15 | Session tracking, daily digests, search (Phase 1) |
| `test_personality` | 16 | 4 dimensions, 5 moods, 5 phrase banks (Phase 2) |
| `test_opinion` | 11 | 7 opinion rules, rate limits (Phase 2) |
| `test_onboarding` | 10 | 5-step first-run experience (Phase 3) |
| `test_demo_mode` | 10 | 8-scene cinematic auto-demo (Phase 3) |
| `test_stats` | 10 | Lifetime, today, peak hours, time-saved (Phase 3) |

---

## 🎮 CLI Reference

After `pip install -e .[all]`:

| Command | What it does |
|---------|--------------|
| `omni install` | Print install instructions |
| `omni status` | Health check |
| `omni model download` | Fetch Qwen2.5-1.5B GGUF (~1.1GB) |
| `omni model info` | Show loaded model info |
| `omni test` | Run all 110+ tests |
| `omni start` | Start FastAPI backend on :8765 |
| `omni ui` | Start Next.js UI on :3000 |
| `omni dev` | Start backend + UI + open browser |
| `omni shell` | Interactive brain REPL |

---

## 🔌 API Surface (50+ endpoints)

**Core:**
- `POST /api/execute` — run a command through the brain
- `WS /ws` — live events (wake word, demo scenes, brain thoughts)

**User (Phase 1):**
- `GET/POST/DELETE /api/user/profile` — persistent profile
- `GET /api/user/greeting` — "Good morning Zarrar"
- `GET /api/user/stats` — behavioral stats

**Memory (Phase 1):**
- `GET /api/memory/sessions?days=7` — list recent
- `GET /api/memory/search?q=...` — search history
- `GET /api/memory/today|yesterday|weekly` — digests

**Personality (Phase 2):**
- `GET/POST /api/personality` — formality, warmth, wit, verbosity
- `POST /api/personality/mood` — set mood (helpful/focused/playful/concerned/celebratory)
- `POST /api/personality/test` — sample phrases

**Proactive (V2):**
- `GET /api/proactive/suggestions` — pending nudges
- `POST /api/proactive/action` — dismiss/act

**Demo (Phase 3):**
- `POST /api/demo` — start/stop/pause/resume/skip_to
- `GET /api/demo/status` — current state
- `GET /api/demo/script` — full 8-scene script

**Stats (Phase 3):**
- `GET /api/stats` — full dashboard
- `GET /api/stats/today|lifetime|time-saved`

**Onboarding (Phase 3):**
- `GET /api/onboarding` — current state
- `POST /api/onboarding/advance|skip|reset`

**Voice:**
- `POST /api/voice/set` — set persona (jarvis/friday/aria/davis/sara/jarvis_british)

**Scheduler:**
- `POST /api/scheduler/cron|interval|once` — schedule tasks

See [docs/PHASE_3_DONE.md](docs/PHASE_3_DONE.md) for the full API.

---

## 🔒 Security

OMNI has 10 security defenses:

1. **Path traversal blocked** — writes sandboxed to `data/output/`
2. **Shell injection blocked** — 25 forbidden patterns + base-command allowlist
3. **JSON DoS protected** — 100KB input cap
4. **ReDoS resistant** — bounded regex + size caps
5. **Rate limited** — 60 req/min per client
6. **Prompt injection detected** — 6 patterns logged
7. **URL guard** — blocks `javascript:`, `vbscript:`, `file:///C:/Windows`
8. **Loop bound** — max 3 retries on self-heal
9. **Atomic writes** — temp file + rename, no partial corruption
10. **No tool crashes the executor** — `safe_execute` wrapper + 30s timeout

Tested against 16 attack vectors. **0 successful breaches.**

---

## 📊 Performance

| Hardware | Speed | Notes |
|----------|-------|-------|
| GTX 1050 Ti 4GB | 8.6 tok/s, 1-2s/turn | Target hardware |
| 16GB RAM, no GPU | 0.9 tok/s, 5-10s/turn | CPU fallback |
| RTX 3090 | 50+ tok/s, <500ms/turn | Overkill |
| Apple M1/M2 | ~2-4s/turn | Native ARM llama.cpp |

**Model:** Qwen2.5-1.5B Q4_K_M (1.1GB). Beating Qwen-3B (10x slower), Llama-3.2-3B (wrong format), Gemma-2-2B (no system role). See [docs/MODEL_BENCHMARK.md](docs/MODEL_BENCHMARK.md).

---

## 📁 Project Structure

```
Omni/
├── pyproject.toml              # Modern Python package
├── install.sh / install.ps1    # One-shot installers
├── README.md                   # ← You are here
│
├── omni/                       # Top-level package
│   ├── cli.py                  # `omni` command
│   └── __init__.py
│
├── omni_v2/                    # Core codebase
│   ├── llm/brain.py            # Qwen brain
│   ├── agents/                 # Planner, Executor, Monitor, Evaluator
│   │   ├── personality.py      # 4 dimensions, 5 moods (Phase 2)
│   │   ├── opinion.py          # 7 opinion rules (Phase 2)
│   │   ├── onboarding.py       # 5-step first run (Phase 3)
│   │   ├── demo_mode.py        # 8-scene demo (Phase 3)
│   │   ├── stats.py            # dashboard data (Phase 3)
│   │   ├── user_profile.py     # persistent profile (Phase 1)
│   │   ├── session_memory.py   # sessions + digests (Phase 1)
│   │   ├── scheduler.py        # APScheduler
│   │   ├── proactive_v2.py     # 9 rules
│   │   └── ...
│   ├── voice/                  # STT, TTS, mic, PTT, wake word
│   │   ├── tts_best.py         # edge-tts natural voices
│   │   ├── wake_word_best.py   # openWakeWord + Whisper
│   │   └── ...
│   ├── tools/                  # 100+ tool plugins
│   │   ├── browser_playwright.py  # real headless browser
│   │   ├── files.py            # safe file writes
│   │   └── ...
│   ├── memory/                 # SQLite, ChromaDB, session_memory
│   ├── core/                   # registry, paths, safe_execute, guardrails
│   └── tests/                  # 110+ tests
│
├── backend_fastapi/            # FastAPI server
│   ├── main.py                 # 50+ endpoints
│   └── core/brain.py           # Brain wrapper
│
├── frontend_next/              # Next.js 14 UI
│   └── app/page.js             # Cinematic command center
│
├── data/                       # Runtime data
│   ├── profiles/               # user profile (Phase 1)
│   ├── personality/            # personality (Phase 2)
│   ├── memory/sessions/        # session logs (Phase 1)
│   ├── memory/digests/         # daily digests (Phase 1)
│   ├── onboarding/             # onboarding state (Phase 3)
│   ├── stats/                  # stats cache (Phase 3)
│   ├── proactive/              # proactive state
│   ├── models/                 # GGUF models
│   ├── chroma/                 # vector store
│   └── chrome_profile/OMNI-Profile/  # isolated browser
│
├── scripts/                    # install.sh, install.ps1
├── docs/                       # AIM, ROADMAP, PHASE_X_DONE
│   ├── AIM.md                  # the AIM
│   ├── ROADMAP.md              # full spec
│   ├── PHASE_1_DONE.md         # It Remembers You
│   ├── PHASE_2_DONE.md         # It Has Opinions
│   ├── PHASE_3_DONE.md         # Demo Polish
│   └── ...
└── _archive/                  # V1 cruft
```

---

## 🎯 Use Cases

- **Personal butler:** "Good morning Zarrar. Your standup is in 10 min. The auth tests are still failing. Want me to look at them?"
- **Productivity:** "Open github, search for my open PRs, summarize them"
- **Code review:** "What did I do yesterday?" → "You committed the auth fix, opened 2 PRs, and replied to 3 reviews"
- **Focus mode:** "I've been coding 2 hours. Want a break? Queue up lo-fi."
- **Smart home:** "Turn off the lights, set temp to 72"
- **Memory:** "Last time I was working on Omni, what was the next step?"
- **Self-healing demo:** "Open this_doesnt_exist.exe" → tries chrome, msedge, and gives a graceful error

---

## 🛠️ Hardware Targets

| Hardware | Expected speed | Notes |
|----------|----------------|-------|
| 1050 Ti 4GB | 1-2s/turn | Target |
| 16GB RAM, no GPU | 5-10s/turn | CPU fallback works |
| RTX 3090 | <500ms/turn | All GPU layers |
| Apple M1/M2 | 2-4s/turn | Native ARM |

---

## 📚 Documentation

- **[docs/AIM.md](docs/AIM.md)** — the AIM (10 things that make it feel like an AGI)
- **[docs/ROADMAP.md](docs/ROADMAP.md)** — full Phase 1-4 spec
- **[docs/PHASE_1_DONE.md](docs/PHASE_1_DONE.md)** — "It Remembers You"
- **[docs/PHASE_2_DONE.md](docs/PHASE_2_DONE.md)** — "It Has Opinions"
- **[docs/PHASE_3_DONE.md](docs/PHASE_3_DONE.md)** — "Demo Polish"
- **[docs/MODEL_BENCHMARK.md](docs/MODEL_BENCHMARK.md)** — why Qwen 1.5B
- **[docs/03-Architecture.md](docs/03-Architecture.md)** — architecture
- **[diagnostic/](diagnostic/)** — 60-bug audit + fixes

---

## License

MIT — see [LICENSE](LICENSE).

---

## Credits

Built by **Zarrar** with the help of an agent (Claude / Arena AI). All code in this repo, all bugs found and fixed, all features built from scratch.

The model is Qwen2.5-1.5B by Alibaba. The voice is Whisper by OpenAI + edge-tts by Microsoft. The browser is Playwright. The wake word is openWakeWord. **All open source. All local. All yours.**

🤖 **OMNI V3 — A local, private, cinematic AGI.**
