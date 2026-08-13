# OMNI V3 — Away Mode + Jarvis Brain: A Fully-Local, Self-Improving Assistant

> **Document status (2026-08-11): historical or unqualified reference.** This file records earlier intent, implementation, audit, or setup work. Its completion, test-count, performance, privacy, platform, and production-readiness statements are **not current release claims**. Use the generated [Capability Matrix](CAPABILITY_MATRIX.md) and [Quality Scorecard](QUALITY_SCORECARD.md) for current truth.


This PR is the cumulative result of a large multi-phase build: a **local, private,
autonomous** assistant that works while you're away, remembers long-term & short-term,
thinks about its own thinking, self-improves from experience, and is **DGX-ready**.

**Everything is local / offline-first.** Runs on a 4GB GTX 1050 Ti today and scales to
a DGX Station (128GB+ unified memory) with no rewrite.

Branch: `arena/019fea64-omni` → `main` · **22 commits · ~15,200 additions · 550 tests passing**

---

## Phase 7 — Away Mode
- **Hybrid RAG + CAG memory** (`omni_v2/memory/hybrid_memory.py`): LONG-term RAG (semantic
  vector retrieval) + SHORT/fast CAG (always-injected cache), fused into every prompt.
  Offline zero-dependency embeddings.
- **Knowledge base** (`omni_v2/away/knowledge_base.py`): ingest files / folders / URLs.
- **Research agent** (`omni_v2/away/research.py`): autonomous multi-step research → reports + KB.
- **Away task queue** (`omni_v2/away/away_agent.py`): persistent unattended tasks
  (research / digest / notify).
- **Reporter** (`omni_v2/away/reporter.py`): markdown reports & digests.
- **Messenger** (`omni_v2/away/messenger.py`): file / WhatsApp / Telegram bridge with
  graceful offline fallback; Pakistan-friendly WhatsApp setup + `+92` normalization.
- **Remote commands** (`omni_v2/away/command_channel.py`): `/research`, `/digest`, `/kb`, `/status`.
- FastAPI `/api/away/*`.

## Phase 8 — Desktop App + Camera Security
- **Full Python desktop app** (`omni_desktop.py`, customtkinter): Dashboard, KB, Research,
  Away Tasks, Reports, Messenger, Identity, Goals, Patterns, Episodes, Voice, Guardian,
  Harness, MCP, Security.
- **Camera security** (`omni_v2/security/*`): pluggable face verifier (**LBPH** default /
  dlib deep / gradient fallback), multi-sample enrollment, cross-platform lockdown with
  pre-lock alert + cancelable countdown, background guard watchdog.
- CLI `omni app`, `omni security enroll/arm/disarm/snapshot/lock`.

## Phase 9 — Jarvis Brain (the "complete brain of itself")
1. **Identity core + user model** (`brain/identity.py`): name, persona, mood, values +
  persistent memory of the user, injected every turn.
2. **Model tiering** (`llm/brain.py`): 1.5B fast + 3B deep, auto-swapped for hard reasoning.
3. **Goal stack** (`brain/goals.py`): decompose big intents → steps, progress across
  sessions, replan-on-failure, follow-through, **auto post-goal refine**.
4. **Metacognition** (`brain/metacog.py`): evaluator's verdict → structured action
  (replan / ask-user / retry / escalate) + confidence gate.
5. **Episodic reflection + patterns** (`brain/reflect.py`): daily recaps + pattern awareness.

### Section-C polish
- **C2** plan-before-acting (`BrainResponse.plan`).
- **C3** fully-local TTS (piper first; edge-tts cloud opt-in).
- **C4** follow-through via messenger.

## Phase 10 — Voice Loop + Proactive Guardian
- **Voice loop** (`voice/voice_loop.py`): hands-free "Hey OMNI" → hear → think → speak,
  voice-driven goals. Headless-testable.
- **Guardian** (`guardian/guardian.py`): watches processes / health / files, notifies on
  anomalies via messenger.

## Phase 11 — Knowledge Graph, Morning Briefing, Skill Installer
- **Knowledge graph** (`graph/knowledge_graph.py`): interactive node/edge viz of memory,
  web viewer at `/knowledge-graph`.
- **Morning briefing** (`briefing/briefing.py`): goals + yesterday recap + fresh research,
  delivered via messenger.
- **Skill installer** (`skills/installer.py`): `omni add-skill <url>` fetches + AST-verifies
  + auto-wires skills.

## Phase 12 — Continual Harness (self-improving)
- **`harness/harness.py`**: versioned, refinable skills/memory/lessons; refine-from-trajectory;
  snapshot + rollback; retrieve-on-demand context. **Auto post-goal flow** + **auto skill
  verification** (`harness/verifier.py`) — skills kept if they pass, rolled back if they fail.

## Phase 13 — Platform / Scalability
1. **MCP Bridge** (`mcp/bridge.py`): connect to the Model Context Protocol ecosystem;
   MCP tools register as native OMNI plugins.
2. **Auto Skill Verification Loop** — skills tested on creation/refinement, kept or rolled back.
3. **Context auto-compaction** (`llm/compaction.py`): summarize old turns to stay in budget.
4. **Sub-agent delegation** (`agents/subagents.py`): RLM-style parallel sub-agents that
   report back compactly.
5. **Automation triggers** (`automation/triggers.py`): webhook / schedule / file events
   wake OMNI → start goals / research / notify / away tasks.
6. **LLM Router V2** (`llm/router_v2.py`): cost-aware multi-tier model selection, DGX-ready.

---

## Fixes & hygiene
- Fixed pre-existing `omni/cli.py` f-string syntax bug (blocked CLI on Python ≤3.11).
- Fixed `D:/Omni` hardcoded path in `backend_fastapi/core/brain.py`.
- TTS is offline-first (piper); wake word defaults to openwakeword (no key); STT is faster-whisper.
- `data/memory.db` (binary runtime data) untracked + gitignored.

## Tests
**48 suites · 550 tests passing · 33 skipped — fully offline.**
(Up from 140+ at the start.)
```
python -m pytest omni_v2/tests/ -q     # 550 passed
```

## Privacy / local-first
- All memory, research, reports, goals, security, voice, and brain state are local.
- TTS = piper (offline) by default; edge-tts (cloud) only if explicitly opted in.
- Optional external channels (WhatsApp Web / Telegram) always fall back to a local file.
- **DGX-ready**: the scaffold is model-agnostic — swap in bigger local models (14B/72B+)
  and the RLM/Continual-Harness tiers reach full power with no rewrite.
