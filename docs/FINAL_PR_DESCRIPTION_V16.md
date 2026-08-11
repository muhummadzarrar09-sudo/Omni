# OMNI V3 — Away Mode + Jarvis Brain + Platform: A Fully-Local, Self-Improving Assistant

> **Document status (2026-08-11): historical or unqualified reference.** This file records earlier intent, implementation, audit, or setup work. Its completion, test-count, performance, privacy, platform, and production-readiness statements are **not current release claims**. Use the generated [Capability Matrix](CAPABILITY_MATRIX.md) and [Quality Scorecard](QUALITY_SCORECARD.md) for current truth.


This PR is the cumulative result of a **16-phase build**: a **local, private, autonomous**
assistant that works while you're away, remembers long-term & short-term, thinks about its
own thinking, **improves its own harness**, controls your GUI, syncs across machines, and is
**DGX-ready**.

**Everything is local / offline-first.** Runs on a 4GB GTX 1050 Ti today and scales to a DGX
Station (128GB+ unified memory) with no rewrite.

Branch: `arena/019fea64-omni` → `main` · **33 commits · ~21,500 additions · 664 tests passing**

---

## Phase 7 — Away Mode
- **Hybrid RAG + CAG memory** (`memory/hybrid_memory.py`): LONG-term RAG (semantic vector
  retrieval) + SHORT/fast CAG (always-injected cache), fused into every prompt. Offline
  zero-dependency embeddings.
- **Knowledge base**, **Research agent**, **Away task queue**, **Reporter**, **Messenger**
  (file/WhatsApp/Telegram + Pakistan +92 setup), **Remote commands** (`/research /digest /kb`).
- FastAPI `/api/away/*`.

## Phase 8 — Desktop App + Camera Security
- **Full Python desktop app** (`omni_desktop.py`): Dashboard, KB, Research, Away Tasks,
  Reports, Messenger, Identity, Goals, Patterns, Episodes, Voice, Guardian, Harness, MCP,
  Security.
- **Camera security** (`security/*`): pluggable face verifier (LBPH default / dlib / gradient),
  multi-sample enrollment, cross-platform lockdown with pre-lock alert + cancelable countdown.

## Phase 9 — Jarvis Brain
1. **Identity core + user model** · 2. **Model tiering** (1.5B fast + 3B deep) ·
3. **Goal stack** (+ auto post-goal refine) · 4. **Metacognition** (evaluate → replan/ask/escalate) ·
5. **Episodic reflection + patterns**. Section-C polish (plan-before-acting, offline piper TTS,
   follow-through).

## Phase 10 — Voice Loop + Proactive Guardian
Hands-free "Hey OMNI" → hear → think → speak, voice-driven goals. Guardian watches processes/
health/files and notifies on anomalies.

## Phase 11 — Knowledge Graph, Morning Briefing, Skill Installer
Interactive memory graph (web viewer), scheduled personal digest, `omni add-skill <url>`
(AST-verified, auto-wired).

## Phase 12 — Continual Harness (self-improving)
Versioned, refinable skills/memory/lessons; refine-from-trajectory; snapshot + rollback;
auto post-goal flow; **auto skill verification**.

## Phase 13 — Platform / Scalability
1. **MCP Bridge** · 2. **Auto Skill Verification** · 3. **Context auto-compaction** ·
4. **Sub-agent delegation** (RLM-style parallel) · 5. **Automation triggers** (webhook/schedule/file) ·
6. **LLM Router V2** (cost-aware, DGX-ready).

## Phase 14 — Resident + Personal
**Daemon + auto-start** (always-on) · **Self-improvement benchmark** (proves the harness) ·
**Skill sandbox** (isolated subprocess, timeout/memory/network-guarded) · **Credential vault**
(Fernet-encrypted, permission-gated) · **Personal context** (calendar + contacts) ·
**RAG-with-citations** · **Wake routine** ("Good morning Zarrar") · **Harness leaderboard**.

## Phase 15 — Operational Depth
**Recurring scheduler** (cron/interval actions) · **Action journal** (replay + safe undo) ·
**Photo memory** (caption images into KB) · **Backup & restore** (whole state to folder/zip) ·
**NL file manager** (safe, sandboxed file ops) · **LAN remote control** (token-authed).

## Phase 16 — Big Subsystems
1. **QueryEngine** — OpenHarness-style **agentic tool-calling runtime** (tool registry,
   permission gate, pre/post hooks, cost metering, compaction, max-turn loop).
2. **Meta-Harness** — the **self-improvement outer loop**: mine failure traces → propose
   harness edits → validate via regression → keep only improvements.
3. **OMNI Mesh** — **multi-machine state sync** (export/import/reconcile brain, harness, KB,
   goals, identity) between laptop and DGX, newest-timestamp-wins.
4. **GUI Agent** — vision-driven, **sandboxed** screen automation (screenshot → vision →
   click/type), journaled for undo.

---

## Fixes & hygiene
- Fixed pre-existing `omni/cli.py` f-string syntax bug (blocked CLI on Python ≤3.11).
- Fixed `D:/Omni` hardcoded path in `backend_fastapi/core/brain.py`.
- TTS offline-first (piper), wake word openwakeword (no key), STT faster-whisper.
- `data/memory.db` untracked + gitignored.

## Tests
**61 suites · 664 tests passing · 33 skipped — fully offline.**
```
python -m pytest omni_v2/tests/ -q     # 664 passed
```

## Privacy / local-first
- All memory, research, reports, goals, security, voice, and brain state are local.
- TTS = piper (offline) by default; edge-tts (cloud) only if opted in.
- Optional external channels (WhatsApp Web / Telegram) always fall back to a local file.
- **DGX-ready**: model-agnostic scaffold — swap in bigger local models (14B/72B+) and the
  RLM/Continual-Harness tiers reach full power with no rewrite.
