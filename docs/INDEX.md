# 📚 OMNI V3 — Documentation Index

> Every doc, every test, every command.

## 🚀 Start Here

- **[README.md](../README.md)** — Top-level overview, quickstart, AIM checklist
- **[AIM.md](AIM.md)** — The 10 features that make it feel like an AGI
- **[QUICKSTART.md](QUICKSTART.md)** — 5-minute setup guide

## 📐 Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture, request flow, module graph
- **[ROADMAP.md](ROADMAP.md)** — Full Phase 1-4 spec, build order
- **[CHANGELOG.md](CHANGELOG.md)** — Version history, what changed when

## 🔌 API & Reference

- **[API.md](API.md)** — Full HTTP API reference (65+ endpoints)
- **[PERFORMANCE.md](PERFORMANCE.md)** — Benchmarks, model selection, hardware scaling
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — Common issues and fixes

## 📋 Phase Reports (what we built)

- **[PHASE_1_DONE.md](PHASE_1_DONE.md)** — "It Remembers You" (Profile, Memory, Greeting)
- **[PHASE_2_DONE.md](PHASE_2_DONE.md)** — "It Has Opinions" (Personality, Opinion Engine)
- **[PHASE_3_DONE.md](PHASE_3_DONE.md)** — "Demo Polish" (Onboarding, Demo Mode, Stats)
- **[PHASE_4_DONE.md](PHASE_4_DONE.md)** — "Product Grade" (Vision, Voice Clone, Marketplace, SDK)
- **[PHASE_5_MOBILE.md](PHASE_5_MOBILE.md)** — "Mobile-First" (mDNS + Phone PWA companion)
- **[PHASE_6_VISUAL.md](PHASE_6_VISUAL.md)** — "Visual-First" (screen watching + context)

## 🛠️ Per-Module Docs

Each major module has a detailed docstring at the top of its file:

| Module | File | What it does |
|---|---|---|
| Brain | `omni_v2/llm/brain.py` | Qwen2.5-1.5B via llama.cpp |
| Executor | `omni_v2/agents/executor.py` | Tool dispatch + safe wrapper |
| Evaluator | `omni_v2/agents/evaluator.py` | Self-healing rules |
| Proactive V2 | `omni_v2/agents/proactive_v2.py` | 9 proactive rules |
| User Profile | `omni_v2/agents/user_profile.py` | Persistent profile |
| Session Memory | `omni_v2/memory/session_memory.py` | Sessions + digests |
| Personality | `omni_v2/agents/personality.py` | 4 dims, 5 moods |
| Opinion | `omni_v2/agents/opinion.py` | 7 opinion rules |
| Onboarding | `omni_v2/agents/onboarding.py` | 5-step first run |
| Demo Mode | `omni_v2/agents/demo_mode.py` | 8-scene auto-demo |
| Stats | `omni_v2/agents/stats.py` | Dashboard data |
| Vision | `omni_v2/vision/multimodal.py` | Drag image/PDF/screenshot |
| Voice Clone | `omni_v2/voice/voice_clone.py` | Record 30s → custom voice |
| Marketplace | `omni_v2/skills/marketplace.py` | 1-click install skills |
| Plugin SDK | `omni_v2/sdk/__init__.py` | Build your own skill |
| Guardrails | `omni_v2/core/guardrails.py` | 10 security defenses |
| Safe Execute | `omni_v2/core/safe_execute.py` | Never-crash tool wrapper |
| Edge TTS | `omni_v2/voice/tts_best.py` | 6 natural personas |
| Wake Word | `omni_v2/voice/wake_word_best.py` | "Hey OMNI" detection |
| Browser V3 | `omni_v2/tools/browser_v3.py` | Chrome isolated profile |
| Playwright | `omni_v2/tools/browser_playwright.py` | Real headless browser |
| mDNS Discovery | `omni_v2/network/mdns.py` | UDP broadcast, zero deps |
| Geofence Engine | `omni_v2/agents/geofence.py` | Places + rules + Haversine |
| Screen Watcher | `omni_v2/agents/screen_watcher.py` | Periodically watches screen + classifies activity |
| Mobile WebSocket | `backend_fastapi/main.py` | /ws/mobile + /api/voice/transcribe |
| Mobile PWA | `mobile/index.html` | Phone browser companion |

## 🧪 Tests

20 test suites, 320+ tests, 100% pass:

```bash
omni test    # runs all 19 suites
```

| Test file | Tests | Coverage |
|---|---|---|
| `omni_v2/tests/test_security_guardrails.py` | 10 | 16 attack vectors |
| `omni_v2/tests/test_fast_af_db.py` | 5 | Sub-ms vector lookup |
| `omni_v2/tests/test_hermes_refinement.py` | 5 | Self-healing loop |
| `omni_v2/tests/test_skill_synthesis.py` | 6 | LLM skill generation |
| `omni_v2/tests/test_user_profile.py` | 12 | Persistent profile |
| `omni_v2/tests/test_session_memory.py` | 15 | Sessions + digests |
| `omni_v2/tests/test_personality.py` | 16 | Personality engine |
| `omni_v2/tests/test_opinion.py` | 11 | Opinion engine |
| `omni_v2/tests/test_onboarding.py` | 10 | First-run flow |
| `omni_v2/tests/test_demo_mode.py` | 10 | 8-scene demo |
| `omni_v2/tests/test_stats.py` | 10 | Dashboard |
| `omni_v2/tests/test_vision.py` | 8 | Multi-modal vision |
| `omni_v2/tests/test_voice_clone.py` | 8 | Voice cloning |
| `omni_v2/tests/test_marketplace.py` | 14 | Skill marketplace |
| `omni_v2/tests/test_network.py` | 13 | mDNS discovery |
| `omni_v2/tests/test_mobile.py` | 55 | PWA + location + endpoints |
| `omni_v2/tests/test_geofence.py` | 50 | Geofence + backend |
| `omni_v2/tests/test_notifications.py` | 40 | Notification center |
| `omni_v2/tests/test_notification_prefs.py` | 37 | Prefs + snooze |
| `omni_v2/tests/test_screen_watcher.py` | 31 | Screen watcher + context |

To run an individual test:
```bash
python -m omni_v2.tests.test_personality
```

## 🎮 CLI Commands

After `pip install -e .[all]`:

```bash
omni install          # Print install instructions
omni status           # Health check
omni model download   # Fetch Qwen2.5-1.5B GGUF (~1.1GB)
omni model info       # Show loaded model info
omni test             # Run all 20 test suites (320+ tests)
omni start            # Start FastAPI backend on :8765
omni start --no-browser  # Don't auto-open browser
omni start --reload   # Hot-reload on code changes
omni ui               # Start Next.js UI on :3000
omni dev              # Start backend + UI + open browser
omni shell            # Interactive brain REPL
```

## 🔌 Quick API Reference

```bash
# Health check
curl http://localhost:8765/api/health

# Run a command
curl -X POST http://localhost:8765/api/execute \
  -H "Content-Type: application/json" \
  -d '{"command":"open github"}'

# Set your name
curl -X POST http://localhost:8765/api/user/profile \
  -H "Content-Type: application/json" \
  -d '{"name":"Zarrar"}'

# Get today's digest
curl http://localhost:8765/api/memory/today

# Get stats dashboard
curl http://localhost:8765/api/stats

# Start the 2-min cinematic demo
curl -X POST http://localhost:8765/api/demo \
  -H "Content-Type: application/json" \
  -d '{"action":"start"}'
```

See [API.md](API.md) for the full reference.

## 📁 Project Structure

```
Omni/
├── README.md                   # Top-level
├── pyproject.toml              # Package config
├── install.sh / install.ps1    # One-shot installers
├── start.bat / start.sh        # One-click launchers
├── LICENSE                     # MIT
│
├── omni/                       # Top-level package
│   ├── cli.py                  # `omni` command
│   └── __init__.py
│
├── omni_v2/                    # Core codebase
│   ├── llm/                    # Qwen brain
│   ├── agents/                 # 12+ agents (planner, executor, ..., onboarding)
│   ├── voice/                  # STT, TTS, wake word, voice clone
│   ├── vision/                 # Screen capture, multi-modal vision
│   ├── tools/                  # 100+ tool plugins
│   ├── memory/                 # SQLite, ChromaDB, session memory
│   ├── core/                   # Registry, paths, guardrails, safe_execute
│   ├── skills/                 # AST verifier, marketplace
│   ├── sdk/                    # Plugin SDK
│   ├── sync/                   # E2E sync stub
│   ├── network/                # mDNS discovery (Phase 5)
│   ├── tests/                  # 16 test suites
│   └── ...
│
├── mobile/                     # Phone PWA (Phase 5B)
│   ├── index.html              # PWA shell
│   ├── app.js                  # Discovery + WS + PTT + QR
│   ├── style.css               # Dark cinematic theme
│   ├── manifest.json           # PWA manifest
│   ├── sw.js                   # Service worker
│   └── qr.html                 # QR generator (laptop-side)
│
├── backend_fastapi/            # FastAPI server (75+ endpoints)
│
├── frontend_next/              # Next.js 14 UI
│
├── docs/                       # All documentation
│   ├── INDEX.md                # ← You are here
│   ├── AIM.md
│   ├── ROADMAP.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── CHANGELOG.md
│   ├── PERFORMANCE.md
│   ├── TROUBLESHOOTING.md
│   ├── PHASE_1_DONE.md
│   ├── PHASE_2_DONE.md
│   ├── PHASE_3_DONE.md
│   └── PHASE_4_DONE.md
│
├── scripts/                    # install.sh, install.ps1
├── data/                       # Runtime data (auto-created)
├── _archive/                   # V1 cruft (archived)
└── diagnostic/                 # 60-bug audit + fix log
```

## 🆘 Getting Help

1. **Search the docs** with Ctrl+F
2. **Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for common issues
3. **Run the tests** to verify your install: `omni test`
4. **Read the code** — everything is well-commented
5. **File an issue** on GitHub

---

**Last updated:** 2026-07-15
**Version:** 3.2.0 (Product Grade)
**Status:** All systems go. 🟢
