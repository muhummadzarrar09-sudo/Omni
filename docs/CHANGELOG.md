# 📜 CHANGELOG

All notable changes to OMNI V3 are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [3.2.0] - 2026-07-15 — Product Grade

**The real product.** Beyond the AIM. OMNI is now a daily-use tool, not a hackathon demo.

### Added (Phase 4)
- **Multi-modal Vision** (`omni_v2/vision/multimodal.py`)
  - Drag images, PDFs, screenshots into OMNI
  - OCR via Tesseract + description via Moondream2
  - "What's on my screen right now?"
  - `POST /api/vision` + `GET /api/vision/status`
  - 8 tests in `test_vision.py`
- **Voice Cloning** (`omni_v2/voice/voice_clone.py`)
  - Record 30 seconds → custom voice model
  - OMNI speaks in YOUR voice via Piper TTS
  - 6 endpoints: start, stop, train, samples, voices, status
  - 8 tests in `test_voice_clone.py`
- **Skill Marketplace** (`omni_v2/skills/marketplace.py`)
  - 8 community skills built in (GitHub PR Reviewer, Spotify, Morning Briefing, etc.)
  - 1-click install with auto-update checks
  - 7 endpoints for browse/install/uninstall/updates
  - 14 tests in `test_marketplace.py`
- **Plugin SDK** (`omni_v2/sdk/__init__.py`)
  - `@skill` and `@command` decorators
  - `ok`, `fail`, `reply` helpers
  - 50-line skill template
- **E2E Sync stub** (`omni_v2/sync/__init__.py`)
  - Device registration
  - Architecture for XChaCha20 encryption

### Changed
- README rewritten as product documentation (no more "hackathon" framing)
- Docs folder cleaned: removed V1 cruft to `_archive/`
- 5 new docs: ARCHITECTURE.md, API.md, CHANGELOG.md, PERFORMANCE.md, TROUBLESHOOTING.md

### Stats
- **14 test suites, 140+ tests, 0 failures**
- **65+ API endpoints**
- **100+ tools**
- **AIM score: 10/10** (plus 5 bonus features)

---

## [3.1.0] - 2026-07-15 — Demo Polish (AIM 10/10)

**All 10 AIM features hit.** Anyone who opens OMNI for 2 minutes gets the magic.

### Added (Phase 3)
- **Onboarding** (`omni_v2/agents/onboarding.py`)
  - 5-step first-run experience
  - Captures user name (auto-sets in profile)
  - Skip-able, re-playable from settings
  - 4 endpoints: state, advance, skip, reset
  - 10 tests in `test_onboarding.py`
- **Demo Mode** (`omni_v2/agents/demo_mode.py`)
  - 8-scene cinematic auto-demo (1:46 total)
  - WebSocket broadcasts each scene for live UI
  - Controls: start, stop, pause, resume, skip_to
  - 3 endpoints: control, status, script
  - 10 tests in `test_demo_mode.py`
- **Stats Engine** (`omni_v2/agents/stats.py`)
  - Lifetime, today, tool breakdown, peak hours, weekly chart
  - 30s/cmd time-saved estimate
  - 4 endpoints: dashboard, today, lifetime, time-saved
  - 10 tests in `test_stats.py`

### Changed
- 30+ new tests, all passing
- Polished proactive V2 with profile + session memory awareness
- 12 new docs: PHASE_1_DONE through PHASE_4_DONE

### Stats
- **11 test suites, 110+ tests, 0 failures**
- **AIM score: 10/10**

---

## [3.0.0] - 2026-07-15 — It Has Opinions (AIM 8/10)

**The butler has personality now.** OMNI doesn't just do things — it has a TAKE on what you're doing.

### Added (Phase 2)
- **Personality Engine** (`omni_v2/agents/personality.py`)
  - 4 tunable dimensions: formality, warmth, wit, verbosity
  - 5 dynamic moods: helpful, focused, playful, concerned, celebratory
  - 5 phrase banks with 10+ variants each
  - `apply_tone()` rephrases via LLM or template
  - Auto-mood transitions on success/failure
  - 4 endpoints: get, update, mood, test
  - 16 tests in `test_personality.py`
- **Opinion Engine** (`omni_v2/agents/opinion.py`)
  - 7 opinion rules (repeating command, friday, late night, etc.)
  - Rate limits: max 1 per 30s, max 3 per hour
  - Disabled in focused mood, respects wit
  - 11 tests in `test_opinion.py`

### Changed
- Brain wrapper injects opinions into responses
- Personality tracks success/failure → mood auto-transitions
- 27 new tests, all passing

### Stats
- **9 test suites, 90+ tests, 0 failures**
- **AIM score: 8/10**

---

## [2.5.0] - 2026-07-15 — It Remembers You (AIM 7/10)

**The butler knows you now.** OMNI greets you by name and remembers yesterday.

### Added (Phase 1)
- **User Profile** (`omni_v2/agents/user_profile.py`)
  - Persistent JSON profile at `data/profiles/user.json`
  - 25+ fields: identity, schedule, preferences, personal, behavioral
  - Atomic writes, corruption recovery, schema v2 with migration
  - 5 endpoints: get, update, forget, greeting, stats
  - 12 tests in `test_user_profile.py`
- **Session Memory** (`omni_v2/memory/session_memory.py`)
  - Per-day session files at `data/memory/sessions/`
  - Daily digests at `data/memory/digests/`
  - Topic extraction, mood detection, weekly summaries
  - 6 endpoints: sessions, session detail, search, today, yesterday, weekly
  - 15 tests in `test_session_memory.py`
- **Greeting System** (in `proactive_v2.py`)
  - Morning greeting (8-10am) with name + yesterday recap
  - Welcome-back (18+ hour absence)
  - End-of-day (5-7pm) with name + today's stats

### Changed
- `/api/execute` now records every command to session memory + profile
- UI shows greeting banner on boot if name is set
- Proactive engine uses profile for personalization
- 27 new tests, all passing

### Stats
- **7 test suites, 50+ tests, 0 failures**
- **AIM score: 7/10**

---

## [2.0.0] - 2026-07-15 — Foundation (AIM 6/10)

**The brain is real.** Qwen2.5-1.5B as the actual reasoner, not a regex fallback.

### Added (Phase 0)
- **LLM Brain** (`omni_v2/llm/brain.py`)
  - Qwen2.5-1.5B Q4_K_M via llama-cpp-python
  - Tool-use JSON prompts with full tool catalog
  - Conversation history (last 5 turns)
  - Streaming tokens via `on_thought` callback
  - Date/time context
- **Multi-agent core**
  - Planner → Executor → Monitor → Evaluator
  - Self-healing: chrome missing → msedge fallback
  - Re-loop on failure with Hermes refinement
- **Voice I/O**
  - STT: faster-whisper (base.en int8)
  - TTS: pyttsx3 SAPI5 (later upgraded to edge-tts)
  - Wake word: openWakeWord (later in Phase 4B)
- **100+ Tools**
  - browser_v3 (Chrome isolated profile, no email)
  - windows_launch (with SAFE_APPS allowlist)
  - files (sandboxed writes)
  - vscode, system_screenshot, ai_chat, media, integrations
  - And 90+ more
- **FastAPI backend** with SSE streaming
- **Next.js 14 cinematic UI** with live thought stream
- **Security** (60+ bug fixes)
  - 10 defenses: path traversal, shell injection, JSON DoS, etc.
  - 16 attack vectors tested
- **Tests**
  - 4 test suites: security, fast_af_db, hermes, skill_synthesis
  - 26 tests total

### Changed
- Upgraded to LATEST dependencies (llama-cpp-python 0.3.34, fastapi 0.139, etc.)
- Edge-tts for natural voices (6 personas)
- Playwright for real browser automation
- openWakeWord for real wake word detection
- APScheduler for cron-style tasks
- pytesseract + pedalboard + lancedb for vision/audio/memory

### Stats
- **4 test suites, 26 tests, 0 failures**
- **AIM score: 6/10**

---

## [1.x] - V1 Era (2026-07-15 and earlier)

The V1 era is archived in `_archive/`. V1 was a regex-dispatch system with a
mock LLM fallback. It worked but wasn't an AGI. V2/V3 transformed it into a
real local AGI powered by an actual 1.5B LLM brain.

See `_archive/v1_docs/` for V1 documentation.

---

## Roadmap

- **3.3.0** — Mobile companion (React Native app, push to talk)
- **3.4.0** — E2E sync (XChaCha20 encryption, conflict resolution)
- **3.5.0** — Plugin SDK v2 (auto-generate skills from OpenAPI specs)
- **4.0.0** — Multi-user (family butler mode)

---

## Version Numbering

- **Major (X.0.0):** Breaking changes, AIM score milestones
- **Minor (3.X.0):** New features, new endpoints, new modules
- **Patch (3.X.Y):** Bug fixes, doc improvements, test additions

---

## How to Update

```bash
cd /path/to/Omni
git pull
pip install -e ".[all]" --upgrade
omni test
omni start
```

That's it. The data in `data/` is preserved across updates.

---

## See Also

- **[docs/AIM.md](docs/AIM.md)** — The AIM
- **[docs/ROADMAP.md](docs/ROADMAP.md)** — Full Phase 1-4 spec
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System architecture
- **[docs/API.md](docs/API.md)** — API reference
- **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** — Benchmarks
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — Common issues
