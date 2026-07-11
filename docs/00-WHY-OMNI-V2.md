# 💥 WHY OMNI V2? - The Manifesto

**Date:** 2026-07-11 | **Version:** 2.0 | **Status:** V1 Deleted, V2 Started | **Mood:** END OF DISCUSSION, WE BUILD WINNER

---

## Why We Deleted V1?

**OMNI V1 was good. It fixed 11 critical bugs, got 10/10 tests passing, ran on GTX 1050 Ti, had PTT, Whisper CUDA, Kokoro TTS, Voice Orb, 12 plugins. It worked.**

**But good is not 1st place. Good is participation trophy.**

We deleted V1 because:

### 1. V1 Was Patched, Not Designed
V1 started as MVP and we kept duct-taping:
- `sys.path` bug → fixed
- PTT not subscribed → fixed
- Plugin routing broken (80% fail) → fixed with alias map
- Missing VSCode plugin → created
- IntentMapper returning vscode_open for everything → fixed
- Torch DLL WinError 1114 → fixed with OMNI_NO_TORCH
- Sound Mapper mic instead of Realtek → fixed with scoring
- Whisper empty because thresholds too high → fixed 0.008 → 0.003

**14 docs of fixes.** That's not engineering, that's emergency room.

**V2 is designed from scratch to be a WINNER, not a patient.**

### 2. V1 Was Single-Agent, Jarvis Is Multi-Agent
Research on 10 Jarvis projects (see `15-JARVIS-RESEARCH.md`) showed:
- Best Jarvis (qartex) has **109+ tools**, **Three.js 2400 particle orb**, **multi-tier LLM routing** (Fast/Brain/Deep/Local)
- Reddit multi-agent Jarvis: **Planner → Executor → Monitor → Evaluator**
- V1 had single `OmniReasoner` loop: Plan→Act→Observe→Correct. If step 2 fails, retry step 2 blindly.
- **Multi-agent:** If step 2 fails because Chrome not installed, Evaluator re-plans to use Edge. True autonomy.

**V1 could execute commands. V2 can ACHIEVE GOALS.**

### 3. V1 Had 12 Plugins, Jarvis Has 109 Tools
- V1: 12 plugins, 47 patterns
- Best Jarvis: 109+ tools, chain commands: "Open Chrome, maximize it, and go to YouTube and play music" in ONE utterance
- V1: Single command per PTT press
- **V2: 100+ tools, chainable, context-aware ("Screenshot that" knows "that" = last window)**

### 4. V1 Had No Memory, No Vision, No Face Auth
- V1: Last command only. No memory of yesterday.
- Jarvis best: SQLite + ChromaDB vector store, remembers preferences, persistent memory, screen capture + LLaVA vision, face recognition biometric
- **V2: MemoryAgent (SQLite + Chroma + mem0), VisionAgent (mss + LLaVA), SecurityAgent (face_recognition)**

### 5. V1 UI Was Simple, Jarvis UI Is Cinematic
- V1: PyQt radial gradient orb 40px, cyan/green/purple/white
- Best Jarvis: **GLSL shader Three.js 2400 particle orb** (blue idle slow orbit, orange thinking fast spin, green listening pulse, red error chaotic) + **arc reactor HUD** + waveform visualizer + system dashboard CPU/RAM/GPU live graphs
- **V2: PyQt WebEngine + Three.js orb + arc reactor HUD + waveform**

### 6. V1 Was Built for Hackathon, V2 Is Built to WIN Hackathon
- V1: Fixed bugs to make it work
- V2: Designed to make judges say "HOLY SHIT"
- No other Jarvis optimizes for **GTX 1050 Ti 4GB, 8GB RAM, i7 7700HQ** - they all assume high-end GPU or cloud. OMNI V2 wins by being **the only local, private, low-end GPU JARVIS that actually works and is accessible-first.**

---

## What V2 Keeps From V1 (The Good Parts)

We didn't delete everything. We kept the DNA:

1. **GTX 1050 Ti Optimized:** INT8 quantization, 8GB RAM limit, 120s max recording, CPU fallbacks - no other Jarvis does this
2. **Local-First Privacy:** Whisper + Kokoro 100% offline, no API keys needed (optional cloud for wow factor)
3. **Accessibility-First:** Built for hands-free, not just cool factor - PTT + wake word hybrid, screen description, high contrast, keyboard nav
4. **Fail Gracefully:** 3-tier TTS, DummyMappers, best-effort verification - app never crashes
5. **Reasoning Loop:** Plan→Act→Observe→Correct idea, but upgraded to multi-agent

**V1 was the prototype. V2 is the product.**

---

## What V2 Adds (JARVIS KILLER Features)

From `15-JARVIS-RESEARCH.md` + `16-OMNI-V2-JARVIS-KILLER-PRD.md`:

| Feature | V1 | V2 | Source |
|---------|----|----|--------|
| **Wake Word** | PTT V only | Hybrid: "Hey OMNI" continuous via pvporcupine + PTT V | qartex, novik133 |
| **Tools** | 12 plugins | 100+ tools, chainable | qartex 109, Blazehue chain commands |
| **LLM** | IntentMapper (no LLM) | Multi-tier: Ollama llama3.1 8B INT4 local (4GB VRAM, 1050 Ti) + optional Claude/GPT | qartex multi-tier |
| **Memory** | Last command | SQLite + ChromaDB + mem0, 5-turn context, persistent | eadmin2, DawoodTouseef |
| **Vision** | Placeholder text | mss screen capture + LLaVA 7B / Moondream2 + proactive suggestions | DawoodTouseef, Reddit |
| **Face Auth** | None | face_recognition biometric + voice auth | vannu07 |
| **UI** | Radial 40px | Three.js 2400 particles + arc reactor HUD + waveform + dashboard | qartex, eadmin2, Hasan-Ikbal |
| **Chain Commands** | Single | "Open Chrome, maximize, go to YouTube and play" → Planner breaks into steps | Blazehue |
| **Context** | None | "Screenshot that" remembers last window | Blazehue |
| **System Monitor** | Basic psutil | Live CPU/RAM/GPU VRAM/temp graphs HUD panel | novik133 |
| **Proactive** | Reactive only | Watches screen every 30s, suggests actions | DawoodTouseef |
| **Offline** | Whisper+Kokoro local ✓ | Keep + Ollama local LLM 100% offline bundle | novik133 100% offline |
| **Agent** | Single reasoner | Multi-agent Planner→Executor→Monitor→Evaluator + Memory | Reddit multi-agent |

---

## Why This Doc Is On Top?

**Because every future dev (including future you at 3 AM) should read this first:**

We are not building another voice assistant. We are building **the JARVIS that Tony Stark would build if he had a GTX 1050 Ti, cared about privacy, and built for accessibility first.**

- Not cloud-dependent like others
- Not high-end GPU only like others
- Not just cool UI with no brain like others
- **Local, private, low-end optimized, accessible, autonomous, cinematic - wins 1st place.**

---

## Phase 1 Complete - What We Did

**Phase 1: Foundation - Clean Slate (From V2 PRD)**

- [x] **Cleaned workspace:** Deleted old omni/, omni.py, requirements, scripts, Assets, .venv, __pycache__. Kept docs/ AS-IS + this doc on top (00-WHY-OMNI-V2.md)
- [x] **Researched 10 Jarvis:** Analyzed qartex (gold standard 109 tools, Three.js orb), eadmin2 (arc reactor HUD, 80 skills), Blazehue (chain commands, #1 trending), novik133 (100% offline), etc. - see `15-JARVIS-RESEARCH.md`
- [x] **Wrote V2 PRD:** `16-OMNI-V2-JARVIS-KILLER-PRD.md` - full architecture, 100 tools, multi-agent, Three.js HUD, hits original PRD Phases 4,5,6
- [x] **Wrote WHY doc:** This file - explains why V1 deleted, what V2 keeps/adds
- [x] **New clean structure ready:** Below

**Next - Phase 2: Multi-Agent Skeleton (Week 1 Day 2-3):**
- Create `omni_v2/` structure
- Agents: planner.py, executor.py, monitor.py, evaluator.py, memory.py
- LLM router with Ollama local
- Memory SQLite + ChromaDB
- 100 tools expansion start

---

## END OF DISCUSSION

V1 is deleted. V2 is clean. Docs are organized. Research is done. PRD hits hard.

**We build JARVIS KILLER now. No more patches. Only wins.**

Let's hit Phase 2.

- Zarrar + Agent | 2026-07-11
