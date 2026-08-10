# PR #1 — OMNI V3 "Away & Jarvis Brain" — Full Feature Summary

This PR is the cumulative result of the whole build: a **local, private, autonomous
assistant** that can work while you're away, remember long-term and short-term, think
about its own thinking, and feel like Jarvis. Everything is fully local / offline-first
and runs on a 4GB GPU.

Branch: `arena/019fea64-omni` → `main`

---

## 1. Away Mode (Phase 7) — work while you're away

- **Hybrid RAG + CAG memory** (`omni_v2/memory/hybrid_memory.py`)
  - LONG-term → RAG: persistent semantic vector store; top-K chunks retrieved at
    answer time.
  - SHORT/fast → CAG: always-injected, zero-retrieval cache (pinned facts, recent).
  - Fused into every prompt via a `context_provider` hook. Offline zero-dependency
    sparse-hash embeddings (no model download, no API).
- **Knowledge base** (`omni_v2/away/knowledge_base.py`) — ingest files/folders/URLs.
- **Research agent** (`omni_v2/away/research.py`) — autonomous multi-step research →
  saved reports + KB.
- **Away task queue** (`omni_v2/away/away_agent.py`) — persistent unattended tasks
  (research / digest / notify).
- **Reporter** (`omni_v2/away/reporter.py`) — markdown reports & digests in
  `data/reports/`.
- **Messenger** (`omni_v2/away/messenger.py`) — file / WhatsApp / Telegram bridge with
  graceful offline fallback. Pakistan-friendly WhatsApp setup + `+92` number
  normalization.
- **Remote commands** (`omni_v2/away/command_channel.py`) — `/research`, `/digest`,
  `/kb`, `/status`, `/help` from your phone.
- **API** — `/api/away/*` router.

## 2. Desktop App + Camera Security (Phase 8)

- **Full Python desktop app** (`omni_desktop.py`, customtkinter) — tabs for Dashboard,
  Knowledge Base, Research, Away Tasks, Reports, Messenger, Identity, Goals, Patterns,
  Episodes, Security.
- **Camera security** (`omni_v2/security/*`):
  - `face_auth.py` — pluggable verifier: **LBPH** (OpenCV contrib, trained, offline)
    default, **dlib deep embeddings** optional, gradient fallback. Multi-sample
    enrollment.
  - `lockdown.py` — cross-platform machine lock with pre-lock alert + countdown.
  - `guard_monitor.py` — background camera watchdog: requires enrollment, debounces N
    unknown verdicts, no-face never locks, alert-before-lock, cancelable countdown.
- **CLI** — `omni app`, `omni security enroll/arm/disarm/snapshot/lock`.

## 3. Jarvis Brain (Phase 9) — the "complete brain of itself"

All 5 steps complete:

1. **Identity core + user model** (`omni_v2/brain/identity.py`) — name, persona, mood,
   values, goals-today, reflections + persistent memory of the user (likes, tone,
   prefs). Injected into every prompt. CLI `omni brain`, `/api/brain/*`.
2. **Model tiering** (`omni_v2/llm/brain.py`) — 1.5B fast + 3B deep (Q4, fits 4GB),
   swapped in only for hard reasoning via `needs_deep()` heuristic + safe VRAM handoff.
   `omni model download --deep`.
3. **Goal stack** (`omni_v2/brain/goals.py`) — decompose big intents → steps,
   dependency-aware execution, progress across sessions, replan-on-failure,
   follow-up (report/reminder). CLI `omni goal`, `/api/goals/*`.
4. **Metacognition** (`omni_v2/brain/metacog.py`) — evaluator's verdict → structured
   Verdict (cause taxonomy → replan / ask-user / retry / escalate-to-deep) + confidence
   gate. CLI `omni meta`, `/api/metacog/*`.
5. **Episodic reflection + patterns** (`omni_v2/brain/reflect.py`) — "today was…"
   recaps saved as episodic memory; detects repeated commands, tool loops, stuck
   topics, research-heavy blends. CLI `omni reflect`, `/api/reflect/*`.

### Section-C polish
- **C2** plan-before-acting (`BrainResponse.plan`).
- **C3** fully-local TTS — piper (offline) first; edge-tts cloud only if `tts_allow_cloud`.
- **C4** follow-through — goal completion pushes report via messenger.

## 4. Web UI (Next.js)

- Cinematic command center now has a **🧠 BRAIN** button → Identity / Goals / Episodes /
  Patterns / Away / Metacog tabs, and a **🔒 SECURITY** button → Camera Security panel
  (enroll / arm / disarm / lock / history).
- New API route wrappers under `frontend_next/app/api/{brain,goals,reflect,away,
  security,metacog}/*` proxy to FastAPI. Verified with `npm run build` (all routes
  compile) and FastAPI TestClient (all brain-family routers serve 200).

## 4.5 Real-hardware setup + offline voice

- **`scripts/setup_hardware.sh`** — one-shot installer tuned for a 4GB GTX 1050 Ti:
  installs deps (CUDA 121 llama-cpp for 10-series), downloads fast 1.5B + deep 3B
  models, configures piper (offline TTS), and prints the WhatsApp setup steps.
- **Offline voice:** wake word now defaults to **openwakeword** (free, offline, no key);
  Picovoice demoted to an explicit opt-in requiring `PICOVOICE_KEY`. New
  `wakeword_engine` config (default `openwakeword`). STT stays on faster-whisper
  (fully offline).

## 5. Fixes & hygiene

- Fixed pre-existing `omni/cli.py` f-string syntax bug (blocked CLI on Python ≤ 3.11).
- Fixed `D:/Omni` hardcoded path in `backend_fastapi/core/brain.py`.
- Made TTS offline-first (edge-tts no longer the default).
- `.gitignore`: ignore `.next` build artifacts.

## Tests

**34 suites, 447 tests passing, 33 skipped — fully offline.**
(Up from 140+ at the start of the PR.)

```
python -m pytest omni_v2/tests/ -q     # 447 passed
```

New suites: hybrid_memory, knowledge_base, research, away_agent, messenger,
command_channel, security, desktop, identity, model_tiering, goals, metacog, reflect,
brain_polish.

## Commands at a glance

```
omni kb add/query/search        omni research <topic>
omni away start/status/add/run  omni report list/digest
omni app                        omni security enroll/arm/disarm/lock
omni messenger setup-whatsapp   omni brain status/user/reflect
omni model download --deep      omni goal new/list/advance/follow-up
omni meta evaluate --goal <id>  omni reflect today/patterns/episodes
```

## Privacy / local-first

- All memory, research, reports, goals, security, and brain state are local.
- TTS is piper (offline) by default; edge-tts (cloud) only if explicitly opted in.
- The only optional external channel is the messenger (WhatsApp Web / Telegram / file),
  which always falls back to a local file when not configured.
