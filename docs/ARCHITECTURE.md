# 🏗️ OMNI V3 — Architecture

A complete guide to how OMNI works, from the user interface down to the LLM.

---

## High-Level Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                 │
│                                                                            │
│  ┌─────────────────────────┐      ┌─────────────────────────┐              │
│  │  Next.js 14 (port 3000) │      │  FastAPI Docs (port 8765)│              │
│  │  Cinematic UI           │      │  Swagger / OpenAPI      │              │
│  │  - Live thought stream  │      │  Interactive endpoint   │              │
│  │  - Tool call cards      │      │  browser                │              │
│  │  - Brain state orb      │      │                         │              │
│  │  - Proactive banner     │      │                         │              │
│  │  - Stats panel          │      │                         │              │
│  │  - Memory drawer        │      │                         │              │
│  └─────────────────────────┘      └─────────────────────────┘              │
│              │                                 │                          │
│              └─────────────┬───────────────────┘                          │
│                            │ HTTP / WebSocket / SSE                       │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                                   │
│                                                                            │
│  backend_fastapi/main.py  ←  65+ endpoints                                │
│  ├─ /api/execute             (main brain command)                          │
│  ├─ /api/execute/stream      (SSE streaming)                              │
│  ├─ /ws                      (WebSocket)                                   │
│  ├─ /api/user/*              (Phase 1: profile, greeting, stats)           │
│  ├─ /api/memory/*            (Phase 1: sessions, digests, search)          │
│  ├─ /api/personality/*       (Phase 2: dimensions, mood)                   │
│  ├─ /api/proactive/*         (suggestions, context)                        │
│  ├─ /api/onboarding/*       (Phase 3: first-run flow)                     │
│  ├─ /api/demo/*              (Phase 3: 8-scene auto-demo)                  │
│  ├─ /api/stats/*             (Phase 3: dashboard)                          │
│  ├─ /api/vision/*            (Phase 4: multi-modal vision)                  │
│  ├─ /api/voice/clone/*      (Phase 4: voice cloning)                      │
│  ├─ /api/skills/*            (Phase 4: marketplace)                        │
│  ├─ /api/voice/*             (TTS persona selection)                       │
│  ├─ /api/scheduler/*         (cron / interval / one-shot)                   │
│  └─ /api/sdk                 (Phase 4: plugin SDK info)                     │
│                                                                            │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────────┐
│                       BRAIN LAYER                                          │
│                                                                            │
│  backend_fastapi/core/brain.py  (OMNIBrain wrapper)                       │
│  └─ orchestrates:                                                           │
│      ┌─────────────────────────────────────────────────────────┐          │
│      │ 1. Smart Router (pre-router)                            │          │
│      │    If "create + code" pattern → force tool calls       │          │
│      │    Skip LLM for known patterns                         │          │
│      └─────────────────────────────────────────────────────────┘          │
│                                │                                          │
│                                ▼                                          │
│      ┌─────────────────────────────────────────────────────────┐          │
│      │ 2. LLM Brain (omni_v2/llm/brain.py)                    │          │
│      │    Qwen2.5-1.5B via llama.cpp                          │          │
│      │    - Tool-use JSON prompts                             │          │
│      │    - Conversation history (last 5 turns)               │          │
│      │    - Date/time context                                 │          │
│      │    - Streaming tokens via on_thought callback          │          │
│      └─────────────────────────────────────────────────────────┘          │
│                                │                                          │
│                                ▼                                          │
│      ┌─────────────────────────────────────────────────────────┐          │
│      │ 3. Executor (omni_v2/agents/executor.py)              │          │
│      │    Dispatches tool calls via PluginManager             │          │
│      │    Wraps in safe_execute (never crashes)               │          │
│      └─────────────────────────────────────────────────────────┘          │
│                                │                                          │
│                                ▼                                          │
│      ┌─────────────────────────────────────────────────────────┐          │
│      │ 4. Opinion Engine (omni_v2/agents/opinion.py)         │          │
│      │    Maybe opine? (rate-limited, mood-aware)             │          │
│      │    Append "💬 observation" to response                 │          │
│      └─────────────────────────────────────────────────────────┘          │
│                                │                                          │
│                                ▼                                          │
│      ┌─────────────────────────────────────────────────────────┐          │
│      │ 5. TTS (omni_v2/voice/tts_best.py)                    │          │
│      │    Speaks the final response with chosen persona       │          │
│      │    Edge TTS (natural) → SAPI5 (fallback)               │          │
│      └─────────────────────────────────────────────────────────┘          │
│                                                                            │
│  Cross-cutting:                                                            │
│  ├─ User Profile (Phase 1)   — name, prefs, behavioral stats              │
│  ├─ Session Memory (Phase 1)  — every command logged                      │
│  ├─ Personality (Phase 2)     — formality, wit, mood                      │
│  └─ Proactive V2 (Phase 0)    — speaks first when context demands          │
│                                                                            │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────────┐
│                       TOOL LAYER (100+ plugins)                            │
│                                                                            │
│  PluginManager (omni_v2/core/plugin_manager.py)                            │
│  ├─ Alias routing (browser_navigate, windows_launch, ...)                 │
│  ├─ Auto-fallback (chrome → msedge → graceful error)                      │
│  └─ Safe execute wrapper (timeouts, no crashes)                            │
│                                                                            │
│  Tool plugins (omni_v2/tools/):                                            │
│  ├─ browser_v3         (Chrome with isolated profile, no email)            │
│  ├─ browser_playwright  (headless Chromium automation) [Phase 4]          │
│  ├─ windows_launch      (open apps, with SAFE_APPS allowlist)              │
│  ├─ files               (sandboxed file writes to data/output/)           │
│  ├─ vscode_control      (open files, terminal)                             │
│  ├─ system_screenshot   (screen capture)                                  │
│  ├─ ai_chat             (conversational fallback)                          │
│  ├─ media_play_music    (Spotify, YouTube, etc.)                          │
│  ├─ integrations        (Gmail, Calendar, Smart Home)                     │
│  └─ ...100+ more                                                            │
│                                                                            │
│  Phase 4: Skill Marketplace                                                │
│  ├─ 1-click install from data/skills/installed/                            │
│  ├─ Auto-update checking                                                  │
│  └─ Plugin SDK for custom skills                                          │
│                                                                            │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────────┐
│                       VISION & VOICE                                       │
│                                                                            │
│  Vision (omni_v2/vision/):                                                 │
│  ├─ multimodal.py  (Phase 4) — drag image/PDF → explain                    │
│  │   - OCR (Tesseract)                                                    │
│  │   - Description (Moondream2 1.9B)                                      │
│  │   - Screen capture (mss)                                               │
│  └─ screen.py      (live screen capture for vision)                        │
│                                                                            │
│  Voice (omni_v2/voice/):                                                   │
│  ├─ STT: faster-whisper (CUDA int8 / CPU int8)                             │
│  ├─ TTS: tts_best.py (edge-tts Microsoft natural voices, 6 personas)       │
│  ├─ Wake Word: wake_word_best.py (openWakeWord + Whisper-tiny)              │
│  ├─ Voice Clone: voice_clone.py (Phase 4) (Piper TTS)                     │
│  └─ Pipeline: pipeline_v3_fixed (sounddevice, -9999 fixed)               │
│                                                                            │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────────┐
│                       MEMORY LAYER                                          │
│                                                                            │
│  omni_v2/memory/                                                            │
│  ├─ sqlite_store.py      (long-term: interactions, preferences)           │
│  ├─ vector_store.py      (ChromaDB: semantic recall)                      │
│  ├─ fast_af_store.py     (sub-ms semantic lookup)                         │
│  └─ session_memory.py    (Phase 1: sessions + daily digests)              │
│                                                                            │
│  data/                                                                     │
│  ├─ profiles/user.json          (user profile)                            │
│  ├─ personality/personality.json (4 dims + mood)                          │
│  ├─ memory.db                    (long-term SQLite)                       │
│  ├─ chroma/                      (vector store)                          │
│  ├─ memory/sessions/             (Phase 1: per-day session files)         │
│  ├─ memory/digests/              (Phase 1: daily summary files)           │
│  ├─ onboarding/state.json        (Phase 3: first-run state)                │
│  ├─ vision/uploads/              (Phase 4: uploaded images)               │
│  └─ voice_clone/{samples,models}/ (Phase 4: voice clone data)             │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow: `POST /api/execute {"command": "open github"}`

```
1. FastAPI receives request
   ↓
2. GUARD-04: Rate limiter check (60 req/min)
   ↓
3. GUARD-05: Prompt injection scan (log only)
   ↓
4. PHASE-1: Record command in session memory + user profile
   ↓
5. Brain wrapper (backend_fastapi/core/brain.py)
   ├─ Smart Router: pattern match? (skip LLM if obvious)
   │  ├─ YES → force tool calls
   │  └─ NO  → continue
   ├─ LLM Brain (Qwen2.5-1.5B)
   │  ├─ Builds system prompt (personality, tools, history, date)
   │  ├─ Generate tokens (streamed via on_thought)
   │  └─ Parse output → tool_calls + text + thoughts
   ├─ Executor: dispatch tool calls
   │  ├─ safe_execute wrapper (no crash, 30s timeout)
   │  ├─ Tool: browser_v3 (chromium isolated)
   │  └─ Result: success=True, message="Opened github"
   ├─ Monitor: verify each tool call
   ├─ Evaluator: check overall success
   │  └─ If failure: replan, retry, or self-heal
   ├─ Opinion Engine: should we add a comment? (rate-limited)
   │  └─ If yes: append "💬 observation"
   └─ TTS: speak the final response (persona)
   ↓
6. PHASE-2: Personality tracks success → mood update
   ↓
7. Return response: { success, message, logs, steps, brain }
```

---

## Module Dependency Graph

```
backend_fastapi/
├── main.py (FastAPI app, 65+ endpoints)
└── core/
    └── brain.py (OMNIBrain wrapper)
        └── imports omni_v2.llm.brain

omni_v2/
├── llm/
│   └── brain.py              (Qwen2.5-1.5B via llama.cpp)
│
├── agents/
│   ├── planner.py            (Plan steps)
│   ├── executor.py           (Dispatch tool calls, safe wrapper)
│   ├── monitor.py            (Track results)
│   ├── evaluator.py          (Self-heal: 5 rules)
│   ├── memory.py             (Long-term store)
│   ├── proactive.py          (V1)
│   ├── proactive_v2.py       (V2: 9 rules, profile-aware)
│   ├── scheduler.py          (APScheduler: cron, interval, one-shot)
│   ├── user_profile.py       (Phase 1: persistent profile)
│   ├── session_memory.py     (Phase 1: sessions + digests)
│   ├── personality.py        (Phase 2: 4 dims, 5 moods)
│   ├── opinion.py            (Phase 2: 7 opinion rules)
│   ├── onboarding.py         (Phase 3: 5-step first run)
│   ├── demo_mode.py          (Phase 3: 8-scene auto-demo)
│   └── stats.py              (Phase 3: dashboard)
│
├── voice/
│   ├── tts_simple.py         (V1)
│   ├── tts_best.py           (edge-tts, 6 personas)
│   ├── wake_word.py          (V1)
│   ├── wake_word_best.py     (openWakeWord + Whisper)
│   ├── voice_clone.py        (Phase 4: Piper TTS)
│   ├── stt_simple.py         (faster-whisper)
│   ├── audio_device_v3.py    (sounddevice primary)
│   └── pipeline_v3_fixed.py  (Full STT + TTS + wake pipeline)
│
├── vision/
│   ├── multimodal.py         (Phase 4: drag image/PDF)
│   ├── screen.py             (Live screen capture)
│   └── llava.py              (Alt vision model)
│
├── tools/
│   ├── browser_v3.py         (Chrome isolated)
│   ├── browser_playwright.py (Phase 4: real headless)
│   ├── windows_launch.py     (with SAFE_APPS)
│   ├── files.py              (sandboxed writes)
│   ├── vscode_control.py     (open files, terminal)
│   ├── system_screenshot.py  (screen capture)
│   ├── ai.py                 (conversational)
│   ├── media.py              (Spotify, YouTube)
│   ├── integrations.py       (Gmail, Calendar, Smart Home)
│   └── ...100+ more
│
├── memory/
│   ├── sqlite_store.py       (long-term)
│   ├── vector_store.py       (ChromaDB)
│   ├── fast_af_store.py      (sub-ms lookup)
│   └── session_memory.py     (Phase 1: per-day)
│
├── core/
│   ├── plugin_manager.py     (100+ tool routing)
│   ├── command_registry.py   (regex patterns)
│   ├── paths.py              (data/ paths, portable)
│   ├── guardrails.py         (10 security defenses)
│   ├── safe_execute.py       (never-crash tool wrapper)
│   ├── event_bus.py          (pub/sub)
│   └── config_manager.py     (settings)
│
├── skills/
│   ├── generator.py          (AST-verify LLM-generated skills)
│   ├── registry.py           (skill catalog)
│   ├── verifier.py           (AST safety check)
│   └── marketplace.py        (Phase 4: 1-click install)
│
├── sdk/
│   └── __init__.py           (Phase 4: @skill, @command decorators)
│
├── sync/
│   └── __init__.py           (Phase 4: E2E sync stub)
│
├── utils/
│   ├── utf8.py               (Windows cp1252 fix)
│   └── logger.py
│
└── tests/
    ├── test_security_guardrails.py
    ├── test_fast_af_db.py
    ├── test_hermes_refinement.py
    ├── test_skill_synthesis.py
    ├── test_user_profile.py
    ├── test_session_memory.py
    ├── test_personality.py
    ├── test_opinion.py
    ├── test_onboarding.py
    ├── test_demo_mode.py
    ├── test_stats.py
    ├── test_vision.py
    ├── test_voice_clone.py
    └── test_marketplace.py
```

---

## Key Design Decisions

### Why a 1.5B model?

- **Speed:** 8.6 tok/s on 1050 Ti 4GB vs 0.9 tok/s for 3B (10x faster)
- **Size:** 1.1GB fits in VRAM with headroom for Whisper + Moondream2 + TTS
- **Format:** Qwen2.5 trained for tool-use JSON out of the box (vs Llama-3.2 needs json_schema mode)
- **Local:** Runs entirely in llama.cpp, no Ollama, no cloud

See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for benchmark details.

### Why multi-agent?

- **Separation of concerns:** planning vs execution vs verification
- **Self-healing visible:** Evaluator catches failures and replans
- **Testable:** each agent is independently testable
- **Extensible:** new agents (Personality, Opinion) plug in cleanly

### Why Phase 1-4 incremental?

- **AIM as north star:** every phase hits specific AIM items
- **Each phase standalone:** can ship after any phase
- **Tests grow with features:** 26 → 140+ tests, 0 regressions
- **Reusable modules:** Profile, Memory, Personality all used by multiple features

### Why local-first?

- **Privacy:** data never leaves the machine
- **No API costs:** $0/month vs $20-200/month for cloud LLMs
- **Offline:** works on planes, in remote areas, during outages
- **Speed:** no network latency
- **Hackathon-judge friendly:** "I can show this offline" is impressive

### Why sounddevice over PyAudio?

- **No -9999 errors:** PyAudio has a notorious bug on Realtek
- **Cross-platform:** works on Windows, macOS, Linux without recompile
- **Simpler API:** less code, fewer crashes

### Why edge-tts over pyttsx3?

- **Quality:** SAPI5 sounds robotic, edge-tts sounds human
- **Voices:** 300+ Edge voices vs 1-2 SAPI5 voices
- **Free:** no API key, no cost, runs offline after first call
- **Streaming:** low latency, can start playing while generating

### Why Playwright over pyautogui?

- **Real browser:** headless Chromium vs screen-coordinate clicks
- **DOM manipulation:** click elements by selector, fill forms, run JS
- **Screenshots:** element-level captures
- **Reliable:** no "wait for animation" hacks
- **Profile isolation:** persistent user data dir per OMNI install

---

## Threading Model

- **FastAPI:** async handlers (uvicorn + asyncio)
- **Brain:** sync (Qwen2.5 + llama.cpp is synchronous, ~1-2s per turn)
- **Voice pipeline:** background thread (daemon)
- **Proactive engine:** background thread (daemon, 60s loop)
- **Wake word:** background thread (daemon, 80ms audio blocks)
- **Scheduler:** APScheduler BackgroundScheduler (daemon)
- **TTS speak_async:** background thread (daemon)
- **Demo mode:** background thread (daemon, fires on_scene callback)

All long-running tasks use daemon threads so they don't block exit.

---

## Data Flow

```
User utterance
  → FastAPI /api/execute
  → Rate limiter + injection scan
  → Record to session memory + profile
  → Brain wrapper
    → Smart Router (pre-router) — pattern match?
    → LLM Brain (Qwen2.5-1.5B) — reason
    → Parse output → tool calls
    → Executor → safe_execute → tools (100+)
    → Monitor → verify
    → Evaluator → self-heal if failed
    → Personality → mood update
    → Opinion → maybe add comment
    → TTS → speak response
  → Return response
  → WebSocket broadcast (for UI live updates)
  → TTS speaks
  → Session memory + profile updated
```

The whole flow takes 1-2 seconds for action commands, <500ms for cached patterns.

---

## File Counts (current)

- **Python source:** ~10,000 lines (omni_v2/ + backend_fastapi/)
- **Tests:** ~2,000 lines (14 test suites)
- **Docs:** ~3,500 lines (AIM, ROADMAP, ARCHITECTURE, API, CHANGELOG, PHASE_x_DONE)
- **Total:** ~15,500 lines

---

## Where to add new features

| To add... | Edit... |
|---|---|
| A new tool | `omni_v2/tools/my_tool.py` (see `omni_v2/sdk/__init__.py` for the template) |
| A new proactive rule | `omni_v2/agents/proactive_v2.py` (`_check_my_rule()`) |
| A new opinion rule | `omni_v2/agents/opinion.py` (`_rule_my_rule()`) |
| A new FastAPI endpoint | `backend_fastapi/main.py` (follow existing patterns) |
| A new personality mood | `omni_v2/agents/personality.py` (`mood_tone` deltas) |
| A new demo scene | `omni_v2/agents/demo_mode.py` (`DEMO_SCRIPT`) |
| A new marketplace skill | `omni_v2/skills/marketplace.py` (`MARKETPLACE_INDEX`) |
| A new test | `omni_v2/tests/test_my_thing.py` (follow existing patterns) |

---

**See [docs/CHANGELOG.md](docs/CHANGELOG.md) for what's new, and [docs/AIM.md](docs/AIM.md) for the north star.**
