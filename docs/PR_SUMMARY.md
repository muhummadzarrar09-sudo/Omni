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

## 4.7 Voice Loop + Proactive Guardian (Phase 10)

- **Voice loop** (`omni_v2/voice/voice_loop.py`): always-on wake → listen → think →
  speak orchestration on top of the offline pieces (openwakeword / faster-whisper /
  brain / piper). Voice-driven goals ("research X and report back" → away goal).
  Headless-testable with fakes. CLI `omni voice`, `/api/assistant/voice/*`, desktop
  "Voice" tab.
- **Guardian** (`omni_v2/guardian/guardian.py`): background machine watcher
  (processes, battery/disk/CPU health, new files) that surfaces observations and
  notifies via messenger on anomalies. Pluggable checkers, headless-testable.
  CLI `omni guardian`, `/api/assistant/guardian/*`, desktop "Guardian" tab.

## 4.8 Knowledge Graph + Morning Briefing + Skill Installer (Phase 11)

- **Knowledge graph** (`omni_v2/graph/knowledge_graph.py`): builds an interactive
  node/edge graph from RAG+CAG memory + sessions (topics, files, tools, commands,
  co-occurrence/sequence edges). CLI `omni graph`, `/api/knowledge-graph`, and a web
  viewer at `/knowledge-graph` (canvas force layout, no heavy deps).
- **Morning briefing** (`omni_v2/briefing/briefing.py`): gathers open goals + yesterday
  recap + fresh research into a structured digest, delivered via messenger + saved
  report. CLI `omni briefing build|deliver`, `/api/briefing`. Ready to schedule.
- **Skill installer** (`omni_v2/skills/installer.py`): `omni add-skill <url>` fetches,
  AST-verifies (blocks destructive/network), writes to data/skills/custom, and wires it
  into the brain via the SkillRegistry. CLI `omni add-skill install|list`,
  `/api/skills/install|list`.

## 4.9 Continual Harness (Phase 12) — the self-refining "grows with you" loop

Inspired by Prime Agent's Continual Harness: a durable, versioned store of
supplemental agent state (`data/brain/harness/`) that OMNI **refines from its own
goal trajectories** — never rewriting the immutable base prompt.

- **Artifacts:** skills / memory / lessons, each versioned + snapshot on change
  (rollback-able via `omni harness rollback`).
- **Refine-from-trajectory:** given a finished goal (+ metacog verdicts), distill
  reusable knowledge; auto-create a **skill** on repeated success; add **memory**
  facts and **lessons**; self-**improve** an existing skill when metacog flags a
  misfire with a suggested fix.
- **Context on demand:** `harness.build_context(topic)` injects only relevant
  artifacts — the retrieve-on-demand token/memory efficiency win.
- **DGX-ready:** the plumbing is headless-testable with no model (deterministic
  distiller); on the DGX Station a real LLM distiller drops in for richer skills.
- **Auto post-goal flow (Phase 12.1):** GoalStack now accepts a `post_goal_hook`
  that fires automatically (in a thread) whenever a goal completes or fails —
  `build_away_stack()` wires it to auto-refine the finished goal into the Continual
  Harness (skills/memory/lessons). No manual command needed.
- CLI `omni harness status/list/refine/rollback/context`; FastAPI
  `/api/harness/*`; desktop "Harness" tab.

## 4.10 MCP Bridge (Phase 13) — connect to the MCP ecosystem

- **`omni_v2/mcp/bridge.py`**: turns MCP server tools into native OMNI plugins so the
  brain can call them like any built-in tool. `MCPToolPlugin` adapts one MCP tool into
  the plugin interface; `MCPBridge` manages servers and registers tools (namespaced as
  `<server>_<tool>`).
- **Real path**: uses the `mcp` SDK (`ClientSession` + `stdio_client`) to spawn a server,
  `list_tools()`, and `call_tool()`. **Fake provider** (`FakeMCPProvider`) lets tests and
  demo run with no MCP server.
- CLI `omni mcp status/add-demo/list/add`; FastAPI `/api/mcp/*`; desktop "MCP" tab.
- On the DGX Station, `pip install mcp` unlocks real stdio servers (filesystem, github,
  slack, etc.) — the bridge registers all their tools.

## 4.11 Auto Skill Verification Loop (Phase 13 #2)

- **`omni_v2/harness/verifier.py`**: `SkillVerificationLoop` tests a harness skill after
  creation/refinement — kept on pass, **rolled back** (to the prior version) or **dropped**
  (if new) on failure. Pluggable tester (default conservative = never wrongly blocks;
  upgrade to a real skill-executor on the DGX).
- Wired automatically: `ContinualHarness.post_skill_hook` → verifier, so every auto-refined
  skill is verified with no manual step.
- CLI `omni skill-verify status/run/history`; wired into the desktop controller + status.

## 4.12 Context Auto-Compaction (Phase 13 #3)

- **`omni_v2/llm/compaction.py`**: `Compactor.maybe_compact(messages)` summarizes the
  older middle of a transcript into a compact system note when it exceeds a token
  budget, preserving the first (task) message + the last N turns. Deterministic
  summarizer by default (works offline); pluggable LLM summarizer for the DGX.
- Wired into `Brain.think()` — long conversations auto-compact automatically.
  `get_status()` reports compactor stats.
- CLI `omni compaction status`; FastAPI `GET /api/brain/compaction`.

## 4.13 Sub-Agent Delegation (Phase 13 #4)

- **`omni_v2/agents/subagents.py`**: `SubAgentDelegator` runs a batch of sub-agent specs
  `[{name, brief}]` in **parallel** (thread pool) and aggregates **compact** results —
  the parent stays small and focused (RLM-style "sub-agents as calls").
- `delegate_goal(goal, goals_stack)`: runs each pending goal step as a sub-agent,
  completes the steps, and returns a compact report. Pluggable handlers (default routes
  steps through the research agent / ack).
- CLI `omni delegate goal/status`; FastAPI `POST /api/goals/{id}/delegate`; wired into
  the DesktopController + status.

## 4.14 Automation Triggers (Phase 13 #5)

- **`omni_v2/automation/triggers.py`**: `TriggerManager` lets external events wake OMNI.
  Three trigger types: **webhook** (HTTP endpoint), **schedule** (cron/interval), **file**
  (new file in a watched dir). Each fires an automation: start a **goal** / run
  **research** / send a **notify** / queue an **away** task (via `make_runner` wired to
  goals/research/away/messenger). Optional webhook secret. Persisted + counted.
- CLI `omni automation status/add/fire/list`; FastAPI `/api/automation/*` incl.
  `POST /api/automation/webhook/<name>`.

## 4.15 LLM Router V2 (Phase 13 #6) — DGX-ready model routing

- **`omni_v2/llm/router_v2.py`**: cost-aware multi-tier router (fast / brain / deep /
  reasoning / local). Each tier has candidate models with `cost` + `capability`; the
  router picks the **cheapest capable model** per task (OpenSquilla-style). Heuristic
  capability estimation + token estimate. Pluggable resolver for real calls.
- On the 1050 Ti: 1.5B (fast/brain) + 3B (deep). On the DGX: automatically uses 14B /
  72B+ reasoning tiers when present.
- CLI `omni router status/route`; FastAPI `GET /api/brain/router`; wired into the
  DesktopController + status.

## 4.16 Daemon + Auto-start (Phase 14 #1) — always-on resident agent

- **`omni_v2/daemon/daemon.py`**: `AutoStartManager` registers OMNI to start on boot
  (systemd user unit / XDG autostart on Linux; Windows/macOS backends pluggable).
  `DaemonController` keeps resident services (guardian, automation triggers, away agent)
  running persistently. Headless-testable with a fake platform backend.
- `omni_daemon.py` entry point; CLI `omni daemon enable/disable/status/start/stop`.

## 4.17 Self-Improvement Benchmark (Phase 14 #2)

- **`omni_v2/benchmark/benchmark.py`**: `BenchmarkRunner` runs a repeated task type and
  measures wall time, tokens, and steps per iteration. Compares the **early** cohort (no
  harness skill) vs the **late** cohort (skill present) and reports % improvement in
  time/tokens/steps — the Hermes-style "skills make you faster" claim, made measurable.
- Pluggable executor; optional real ContinualHarness (skills grow between runs).
- CLI `omni benchmark run/report`; FastAPI `GET /api/brain/benchmark`; wired into the
  DesktopController.

## 4.18 Skill Sandbox (Phase 14 #3)

- **`omni_v2/skills/sandbox.py`**: runs untrusted / harness-created skills in an **isolated
  subprocess** with OS-level guardrails — hard wall-clock timeout, memory limit
  (RLIMIT_AS), **network blocked** (socket monkeypatched in the child), clean stripped env,
  bounded JSON-safe result returned to the parent.
- `run_skill_code` / `run_skill_artifact`; a `sandbox_tester` factory lets the
  SkillVerificationLoop test skills by actually executing them safely.
- CLI `omni sandbox status/run`; FastAPI `GET /api/brain/sandbox`; wired into the
  DesktopController.

## 4.19 Credential Vault (Phase 14 #4)

- **`omni_v2/vault/vault.py`**: `CredentialVault` stores secrets locally, **Fernet-encrypted
  at rest** (keyfile or `OMNI_VAULT_KEY` passphrase). Reads are **permission-gated** by an
  allow-list per secret + an optional human-approval hook (HITL). `list` masks values.
- CLI `omni vault set/get/list/delete/stats`; FastAPI `GET /api/brain/vault`; wired into the
  DesktopController.

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
