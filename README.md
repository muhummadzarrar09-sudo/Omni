# 🤖 OMNI V3 — A Local, Private AGI Butler

> **"A butler that thinks. Not a chatbot. Not a wrapper. A JARVIS that actually does stuff."**
>
> Multi-agent local AGI powered by Qwen2.5-1.5B. Voice I/O. Multi-modal vision. Memory that remembers. Personality that has opinions. **All private. All offline. All yours.**

[![AIM Score](https://img.shields.io/badge/AIM-10%2F10-brightgreen)](docs/AIM.md)
[![Tests](https://img.shields.io/badge/tests-140%2B%20passing-brightgreen)](docs/CHANGELOG.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)]()

---

## What is OMNI?

OMNI is a **local AGI assistant** that runs entirely on your laptop. It's not a chatbot — it's a butler that:

- **Thinks** with a real 1.5B-parameter LLM brain (Qwen2.5 via llama.cpp)
- **Hears** you with Whisper voice recognition
- **Speaks** with Microsoft Edge natural voices (6 personas)
- **Sees** screenshots, images, PDFs (Moondream2 + Tesseract)
- **Acts** with 100+ tools (browser, files, code, calendar, smart home, etc.)
- **Remembers** what you did yesterday, this morning, last week
- **Has opinions** — "You've opened Twitter 3 times today. Working or procrastinating?"
- **Self-heals** when tools fail
- **Clones your voice** — record 30 seconds, OMNI speaks like you
- **Defends** against 16+ attack vectors (path traversal, shell injection, etc.)
- **Extends itself** — 1-click install community skills

**No cloud. No API keys. No data leaves your machine. Ever.**

---

## ⚡ Quickstart

### Windows (one-click)

```powershell
# Double-click start.bat — that's it.
start.bat
```

It auto-installs everything, downloads the 1.1GB model, opens the browser.

### Windows (manual)

```powershell
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
.\install.ps1
omni model download
omni test
omni start
# Open http://localhost:8765/docs
```

### Linux / macOS

```bash
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni
./install.sh
omni model download
omni test
omni start
```

### With the cinematic UI

```bash
# In one terminal
omni start

# In another
cd frontend_next
npm install
npm run dev
# Open http://localhost:3000
```

---

## 🎯 The AIM — 10/10 Achieved

Every AGI demo has the same problem: it's a chatbot in disguise. OMNI hits all 10 AIM features:

| # | Feature | What it does | Docs |
|---|---------|--------------|------|
| 1 | 🗣️ **Wake word** | Always-listening "Hey OMNI" | [Phase 0](docs/PHASE_4_DONE.md#4b-voice-cloning) |
| 2 | 👋 **Greets by name** | "Good morning Zarrar" + yesterday recap | [Phase 1](docs/PHASE_1_DONE.md) |
| 3 | 🧠 **Shows thinking** | Live LLM token stream on screen | Phase 0 |
| 4 | 🛠️ **Shows tools** | Cards appear as it acts | Phase 0 |
| 5 | 🔁 **Shows recovery** | Self-heals visibly | Phase 0 |
| 6 | 💡 **Speaks first** | 9 proactive rules (battery, breaks, etc.) | Phase 0 |
| 7 | 🎭 **Has a voice** | 6 natural personas | Phase 0 |
| 8 | 🧠 **Remembers** | "Yesterday you worked on github" | [Phase 1](docs/PHASE_1_DONE.md) |
| 9 | 😏 **Has opinions** | "That's 3 commits today. You good. 🚀" | [Phase 2](docs/PHASE_2_DONE.md) |
| 10 | ⚡ **Cinematic** | Orb animations, live states, onboarding | [Phase 3](docs/PHASE_3_DONE.md) |

**Plus (beyond AIM):**
- 👁️ **Multi-modal vision** — drag screenshot → OMNI explains ([Phase 4](docs/PHASE_4_DONE.md))
- 🎤 **Voice cloning** — record 30s → custom voice
- 📦 **Skill marketplace** — 1-click install community skills
- 🛠️ **Plugin SDK** — build your own skills in 50 lines

See [docs/AIM.md](docs/AIM.md) for the full spec.

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
│  FastAPI backend (:8765) — 65+ endpoints                       │
│  /api/execute · /api/memory/* · /api/personality · /api/vision │
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
│        Onboarding · Demo Mode · Stats · Vision · Voice Clone   │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  LLM Brain (Qwen2.5-1.5B GGUF, llama.cpp)                       │
│  + 100+ Tools · Voice (Whisper/edge-tts) · Vision · Wake Word  │
└────────────────────────────────────────────────────────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full picture.

---

## 🎮 CLI Reference

After `pip install -e .[all]`:

| Command | What it does |
|---------|--------------|
| `omni install` | Print install instructions |
| `omni status` | Health check |
| `omni model download` | Fetch Qwen2.5-1.5B GGUF (~1.1GB) |
| `omni model info` | Show loaded model info |
| `omni test` | Run all 140+ tests |
| `omni start` | Start FastAPI backend on :8765 |
| `omni ui` | Start Next.js UI on :3000 |
| `omni dev` | Start backend + UI + open browser |
| `omni shell` | Interactive brain REPL |

---

## 🔌 API Surface (65+ endpoints)

Open http://localhost:8765/docs for the full interactive Swagger UI.

**Core:**
- `POST /api/execute` — run a command through the brain
- `WS /ws` — live events (wake word, brain thoughts)

**User (Phase 1):**
- `GET/POST/DELETE /api/user/profile` — persistent profile
- `GET /api/user/greeting` — "Good morning Zarrar"
- `GET /api/user/stats` — behavioral stats
- `GET /api/memory/sessions?days=7` — list recent
- `GET /api/memory/search?q=...` — search history
- `GET /api/memory/today|yesterday|weekly` — digests

**Personality (Phase 2):**
- `GET/POST /api/personality` — formality, warmth, wit, verbosity
- `POST /api/personality/mood` — set mood
- `POST /api/personality/test` — sample phrases

**Proactive:**
- `GET /api/proactive/suggestions` — pending nudges
- `POST /api/proactive/action` — dismiss/act

**Onboarding (Phase 3):**
- `GET /api/onboarding` — state
- `POST /api/onboarding/advance|skip|reset`

**Demo (Phase 3):**
- `POST /api/demo` — start/stop/pause/resume
- `GET /api/demo/status` — current state
- `GET /api/demo/script` — full script

**Stats (Phase 3):**
- `GET /api/stats` — full dashboard
- `GET /api/stats/today|lifetime|time-saved`

**Vision (Phase 4):**
- `POST /api/vision` — process file or capture screen
- `GET /api/vision/status` — dependencies

**Voice Clone (Phase 4):**
- `POST /api/voice/clone/{start,stop,train}` — record + train
- `GET /api/voice/clone/{samples,voices,status}`

**Skill Marketplace (Phase 4):**
- `GET /api/skills/marketplace` — browse
- `POST /api/skills/{install,uninstall}` — manage
- `GET /api/skills/{installed,updates,marketplace/status}`

**Voice (Phase 0):**
- `POST /api/voice/set` — set persona (jarvis/friday/aria/etc.)
- `GET /api/voice/personas`

**Scheduler:**
- `POST /api/scheduler/{cron,interval,once}` — schedule tasks

**Plugin SDK (Phase 4):**
- `GET /api/sdk` — SDK info

See [docs/API.md](docs/API.md) for the full reference.

---

## 🛠️ Build Your Own Skill (50 lines)

```python
from omni_v2.sdk import skill, command, reply

@skill(
    name="my_skill",
    category="custom",
    description="What my skill does",
)
class MySkill:
    async def execute(self, entities, context):
        return reply(f"Hello! You said: {context.get('original', '')}")
```

Save to `data/skills/custom/my_skill.py`. OMNI auto-loads it. See [omni_v2/sdk/__init__.py](omni_v2/sdk/__init__.py) for the full SDK.

---

## 🔒 Security

OMNI has 10 security defenses, tested against 16 attack vectors:

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

**0 successful breaches** across all attack tests. See [omni_v2/core/guardrails.py](omni_v2/core/guardrails.py).

---

## 📊 Performance

| Hardware | Speed | Notes |
|----------|-------|-------|
| GTX 1050 Ti 4GB | 8.6 tok/s, 1-2s/turn | Target hardware |
| 16GB RAM, no GPU | 0.9 tok/s, 5-10s/turn | CPU fallback |
| RTX 3090 | 50+ tok/s, <500ms/turn | Overkill |
| Apple M1/M2 | 2-4s/turn | Native ARM |

**Model:** Qwen2.5-1.5B Q4_K_M (1.1GB). Winner over Qwen-3B (10x slower), Llama-3.2-3B (wrong format), Gemma-2-2B (no system role). See [docs/MODEL_BENCHMARK.md](_archive/v1_docs/MODEL_BENCHMARK.md) for details.

---

## 🧪 Tests

**14 test suites, 140+ tests, 100% pass, 0 failures.**

```bash
omni test    # runs all 14 suites
```

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_security_guardrails` | 10 | 16 attack vectors |
| `test_fast_af_db` | 5 | Sub-ms vector lookup |
| `test_hermes_refinement` | 5 | Self-healing loop |
| `test_skill_synthesis` | 6 | LLM skill generation |
| `test_user_profile` | 12 | Persistent profile |
| `test_session_memory` | 15 | Sessions + digests |
| `test_personality` | 16 | Personality engine |
| `test_opinion` | 11 | Opinion engine |
| `test_onboarding` | 10 | First-run flow |
| `test_demo_mode` | 10 | 8-scene demo |
| `test_stats` | 10 | Dashboard |
| `test_vision` | 8 | Multi-modal vision |
| `test_voice_clone` | 8 | Voice cloning |
| `test_marketplace` | 14 | Skill marketplace |

---

## 📁 Project Structure

```
Omni/
├── pyproject.toml              # Modern Python package
├── install.sh / install.ps1    # One-shot installers
├── start.bat / start.sh        # One-click launchers
├── README.md                   # ← You are here
├── LICENSE                     # MIT
│
├── omni/                       # Top-level package
│   ├── cli.py                  # `omni` command
│   └── __init__.py
│
├── omni_v2/                    # Core codebase
│   ├── llm/brain.py            # Qwen brain
│   ├── agents/                 # Planner, Executor, Monitor, Evaluator
│   │   ├── personality.py      # 4 dims, 5 moods (Phase 2)
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
│   │   ├── voice_clone.py      # voice cloning (Phase 4)
│   │   └── ...
│   ├── vision/                 # Screen capture, Moondream2
│   │   ├── multimodal.py       # drag-and-drop vision (Phase 4)
│   │   └── ...
│   ├── tools/                  # 100+ tool plugins
│   │   ├── browser_playwright.py
│   │   ├── files.py
│   │   └── ...
│   ├── memory/                 # SQLite, ChromaDB, session_memory
│   ├── core/                   # registry, paths, safe_execute, guardrails
│   │   ├── guardrails.py       # 10 security defenses
│   │   ├── safe_execute.py     # never-crash tool wrapper
│   │   └── ...
│   ├── skills/                 # AST verifier, SkillMaker, marketplace (Phase 4)
│   │   ├── marketplace.py
│   │   └── ...
│   ├── sdk/                    # Plugin SDK (Phase 4)
│   ├── sync/                   # E2E sync (Phase 4 stub)
│   ├── tests/                  # 14 test suites
│   └── ...
│
├── backend_fastapi/            # FastAPI server
│   ├── main.py                 # 65+ endpoints
│   └── core/brain.py
│
├── frontend_next/              # Next.js 14 UI
│   └── app/page.js             # Cinematic command center
│
├── scripts/                    # install scripts
├── docs/                       # Documentation
│   ├── AIM.md                  # The AIM
│   ├── ROADMAP.md              # Full Phase 1-4 spec
│   ├── ARCHITECTURE.md         # Architecture diagram
│   ├── API.md                  # API reference
│   ├── CHANGELOG.md            # Version history
│   ├── PHASE_1_DONE.md         # It Remembers You
│   ├── PHASE_2_DONE.md         # It Has Opinions
│   ├── PHASE_3_DONE.md         # Demo Polish
│   └── PHASE_4_DONE.md         # Product Grade
│
├── data/                       # Runtime data (auto-created)
│   ├── profiles/               # user profile
│   ├── personality/            # personality
│   ├── memory/                 # sessions + digests
│   ├── onboarding/             # onboarding state
│   ├── stats/                  # stats cache
│   ├── voice_clone/            # voice samples + models
│   ├── vision/                 # uploaded images
│   ├── models/                 # GGUF models
│   └── ...
│
├── _archive/                   # V1 cruft, archived
│
└── diagnostic/                 # 60-bug audit + fix log
```

---

## 📚 Documentation

- **[docs/AIM.md](docs/AIM.md)** — The AIM (10 things that make it feel like an AGI)
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System architecture
- **[docs/API.md](docs/API.md)** — Full API reference
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — Version history
- **[docs/ROADMAP.md](docs/ROADMAP.md)** — Full Phase 1-4 spec
- **[docs/PHASE_1_DONE.md](docs/PHASE_1_DONE.md)** — "It Remembers You"
- **[docs/PHASE_2_DONE.md](docs/PHASE_2_DONE.md)** — "It Has Opinions"
- **[docs/PHASE_3_DONE.md](docs/PHASE_3_DONE.md)** — "Demo Polish"
- **[docs/PHASE_4_DONE.md](docs/PHASE_4_DONE.md)** — "Product Grade"
- **[diagnostic/](diagnostic/)** — 60-bug audit + fixes

---

## 🎯 Use Cases

- **Personal butler:** "Good morning Zarrar. Your standup is in 10 min."
- **Productivity:** "Open github, search for my open PRs, summarize them"
- **Code review:** "What did I do yesterday?" → "You committed the auth fix, opened 2 PRs, replied to 3 reviews"
- **Focus mode:** "I've been coding 2 hours. Want a break? Queue up lo-fi."
- **Memory:** "Last time I was working on Omni, what was the next step?"
- **Self-healing demo:** "Open this_doesnt_exist.exe" → tries chrome, msedge, gives graceful error
- **Voice clone:** Record 30s → OMNI speaks in your voice
- **Vision:** "What's on my screen?" → describes it
- **Skills:** `omni skills install morning_briefing` → installs community skill

---

## 🛠️ Hardware Targets

| Hardware | Expected speed |
|----------|----------------|
| 1050 Ti 4GB | 1-2s/turn |
| 16GB RAM, no GPU | 5-10s/turn |
| 32GB RAM, RTX 3090 | <500ms/turn |
| Apple M1/M2 | 2-4s/turn |

---

## License

MIT — see [LICENSE](LICENSE).

---

## Credits

Built by **Zarrar** with the help of an agent (Claude / Arena AI).

The model is Qwen2.5-1.5B by Alibaba. The voice is Whisper by OpenAI + edge-tts by Microsoft. The browser is Playwright. The wake word is openWakeWord. The OCR is Tesseract. The vision is Moondream2. The TTS cloning is Piper.

**All open source. All local. All yours.**

🤖 **OMNI V3 — A local, private, cinematic AGI.**
