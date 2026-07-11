# 🚀 OMNI V2 - JARVIS KILLER PRD
## Version 2.0 | Built to Win 1st Place | Hits Original PRD Phases 4,5,6 + All Jarvis Best

**Date:** 2026-07-11 | **Status:** CLEAN WORKSPACE, RESEARCH DONE, READY TO BUILD
**Hardware:** GTX 1050 Ti 4GB | i7 7700HQ | 8GB RAM | Windows 11
**Philosophy:** Local-First, Accessibility-First, 1050 Ti Optimized, JARVIS Cool + OMNI Robust

---

## 1. Executive Summary - Why OMNI V2 Wins Over Every Jarvis

**Current OMNI V1:** 12 plugins, PTT only, simple orb, IntentMapper (no LLM), last-command memory only, no vision, no face auth, 47 patterns. Works but not wow.

**Best Jarvis (qartex):** 109 tools, wake word, Three.js 2400 particle orb, multi-tier LLM, persistent memory, vision.

**OMNI V2 Goal:** Keep OMNI's unique edges (1050 Ti optimized, accessibility-first, local-first, reasoning loop) + add ALL best Jarvis features + 10x polish = **JARVIS KILLER**.

**Core Insight:** No Jarvis optimizes for GTX 1050 Ti 4GB. They all assume high-end GPU or cloud. OMNI V2 wins hackathon by being **the only local, private, low-end GPU JARVIS that actually works**.

---

## 2. Vision - OMNI V2 is What JARVIS Should Have Been

> **OMNI V2** is the AI agent Tony Stark would build if he had a GTX 1050 Ti, cared about privacy, and built for accessibility first. It's JARVIS cool, but OMNI robust.

**Design Principles (From Original PRD + Jarvis Research):**

| Principle | OMNI V1 | OMNI V2 (JARVIS KILLER) |
|-----------|---------|------------------------|
| Local-First | Whisper+Kokoro local ✓ | Keep + add Ollama llama3.1 local LLM + optional cloud |
| Hardware-Conscious | 1050 Ti baseline ✓ | Keep + INT8 quantization for LLM, 8GB RAM limit |
| Fail Gracefully | 3-tier TTS, fallbacks ✓ | Keep + multi-agent retry, DummyMappers for torch fail |
| Accessibility-First | PTT, screen desc ✓ | Keep + wake word hybrid, waveform, high contrast, keyboard nav |
| Demo-Ready | 5 sec impression | 1 sec impression: Arc reactor HUD + particle orb + "Yes Sir" voice |
| **NEW: Cinematic** | Simple radial orb | Three.js 2400 particle orb (blue idle, orange thinking, green listening, red error) + arc reactor HUD + waveform |
| **NEW: Proactive** | Reactive only | Watches screen every 30s, suggests: "I see you're coding, want me to run tests?" |
| **NEW: Persistent Memory** | Last command only | SQLite + ChromaDB vector store, remembers yesterday, learns preferences |
| **NEW: Multi-Agent** | Single reasoner loop | Planner→Executor→Monitor→Evaluator (from Reddit research) |

---

## 3. Architecture - OMNI V2 (Hits PRD Phases 4,5,6 Hard)

### 3.1 Overall Architecture (JARVIS Best + OMNI Robust)

```
┌─────────────────────────────────────────────────────────────────┐
│                    OMNI V2 - CLEAN WORKSPACE                   │
│                                                                 │
│  Entry: omni.py --wakeword "Hey OMNI" + PTT V hybrid           │
│  UI: PyQt5 HUD + WebEngine Three.js Orb (2400 particles)       │
│  Brain: Multi-Agent + Multi-Tier LLM Router                    │
│  Voice: RealtimeSTT + Silero VAD + Faster-Whisper + Kokoro     │
│  Memory: SQLite + ChromaDB + mem0                              │
│  Vision: mss screen capture + OpenCV + LLaVA local             │
│  Security: face_recognition biometric + voice auth             │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  PERCEPTION  │     │  COGNITION   │     │   ACTION     │
│              │     │  (Multi-Agent)│     │  (100+ Tools)│
│ • Wake Word  │     │ • Planner    │     │ • Browser 15 │
│   Hey OMNI   │────▶│ • Executor   │────▶│ • Windows 15 │
│ • PTT V      │     │ • Monitor    │     │ • VSCode 10  │
│ • Silero VAD │     │ • Evaluator  │     │ • System 10  │
│ • Whisper    │     │ • Memory     │     │ • Media 10   │
│ • Vision     │     │ • Context    │     │ • Files 10   │
│   Screen+Cam │     │ • LLM Router │     │ • AI 10      │
│ • Face Auth  │     │   Fast/Brain │     │ • Integrate20│
└──────┬───────┘     │   Deep/Local │     └──────┬───────┘
       │             └──────┬───────┘            │
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                 ┌────────────────────┐
                 │     FEEDBACK       │
                 │ • Orb 2400 particles│
                 │   Blue idle        │
                 │   Orange thinking  │
                 │   Green listening  │
                 │   Red error        │
                 │ • Waveform viz     │
                 │ • Arc Reactor HUD  │
                 │ • TTS Kokoro       │
                 │   af_sarah voice   │
                 │ • System Dashboard │
                 │   CPU/RAM/Temp     │
                 └────────────────────┘
```

### 3.2 Multi-Agent System (From Reddit Research, Better Than Single Reasoner)

**Current V1:** Single `OmniReasoner.solve()` with Plan→Act→Observe→Correct loop, retries.

**V2 Multi-Agent (Planner→Executor→Monitor→Evaluator):**

```python
class PlannerAgent:
    """Breaks user utterance into steps, handles chain commands"""
    # Input: "Open Chrome, maximize it, and go to YouTube and play music"
    # Output: [Step(open, chrome), Step(maximize, window), Step(navigate, youtube), Step(play, music)]
    def plan(self, text: str) -> List[ActionStep]: ...

class ExecutorAgent:
    """Runs each step via plugin manager, uses 100+ tools"""
    def execute_step(self, step: ActionStep) -> CommandResult: ...

class MonitorAgent:
    """Watches if step succeeded - screen changed? process running? file exists?"""
    def monitor(self, step: ActionStep, result: CommandResult) -> bool: ...

class EvaluatorAgent:
    """Checks overall goal achieved, if not, re-plan. Learns from failures."""
    def evaluate(self, goal: str, steps: List[ActionStep], results: List[CommandResult]) -> ExecutionResult: ...

class MemoryAgent:
    """Persistent memory: SQLite for facts, ChromaDB for vector search, mem0 for preferences"""
    def remember(self, key, value): ...
    def recall(self, query) -> List[str]: ...
    def learn_preference(self, user_says): ...
```

**Why Multi-Agent Wins:** 
- Single reasoner: If step 2 fails, retries step 2 blindly
- Multi-agent: Evaluator sees step 2 failed because Chrome not installed, re-plans to use Edge instead = true autonomy

### 3.3 Multi-Tier LLM Routing (From qartex Research)

**Current V1:** No LLM, only IntentMapper (sentence-transformers) + regex.

**V2 Routing:**

| Tier | Use Case | Model | Latency | Cost |
|------|----------|-------|---------|------|
| **Fast** | Quick lookups, "what time is it" | Ollama llama3.1 8B INT4 / Claude Haiku | 0.5s | Free / $ |
| **Brain** | Conversation, "how are you" | Ollama llama3.1 70B / Claude Sonnet | 1-2s | Free / $$ |
| **Deep** | Complex reasoning, "plan my weekend" | Ollama deepseek-r1 / Claude Opus | 3-5s | Free / $$$ |
| **Local** | Offline, privacy, no internet | Ollama llama3.1 8B (always available) | 1s | Free |

**Router Logic:**
```python
if "time" in text or "open" in text or len(text) < 20:
    tier = Fast  # Quick, no need for big brain
elif "how" in text or "what" in text or len(text) < 100:
    tier = Brain  # Conversation
elif "plan" in text or "complex" in text or len(text) > 100:
    tier = Deep  # Complex
else:
    tier = Local  # Fallback to local Ollama
```

**For Hackathon:** Use Ollama llama3.1 8B local for demo (no API key needed, 100% offline, runs on 1050 Ti with INT4 quantization) + optional GPT API for wow factor.

### 3.4 100+ Tools Expansion (From 12 → 100, Hits PRD Phase 4 & 5)

**Current:** 12 plugins, 47 patterns

**V2:** 100+ tools organized:

**Browser (15 tools) - From simple navigate to full automation:**
- navigate, search, click, type, scroll, new_tab, close_tab, back, forward, refresh, screenshot_element, extract_text, fill_form, download, bookmark

**Windows (15 tools):**
- launch, close, minimize, maximize, move, resize, focus, pin, unpin, switch, kill, lock, sleep, restart, shutdown (with confirmation)

**VS Code (10 tools):**
- open_file, create_file, edit_file, save, close, run_terminal, run_test, format, search, goto_line

**System (10 tools):**
- screenshot, screen_record, copy, paste, volume, brightness, wifi, bluetooth, battery, clean_temp

**Media (10 tools):**
- play_music, pause, next, prev, youtube_play, spotify_control, youtube_search, volume_fade, record_audio, text_to_music (via MusicGen local)

**Files (10 tools):**
- create_folder, delete, move, copy, rename, search_files, list_dir, zip, unzip, open_with

**AI (10 tools) - NEW:**
- chat, summarize, translate, code_generate, image_generate (via SD local), explain_code, fix_code, write_email, brainstorm, research (web search)

**Integrations (20 tools) - Hits PRD Phase 4 Beta:**
- gmail_send, gmail_read, gmail_count, calendar_schedule, calendar_show, calendar_cancel, lights_on, lights_off, temp_set, lock_door, unlock, camera_show, weather, news, stocks, maps, calculator, timer, reminder, notes

**Accessibility (10 tools) - Hits PRD Phase 4 Alpha:**
- screen_describe, find_element, high_contrast, large_text, audio_only, screen_reader, magnifier, on_screen_keyboard, dictate (continuous), read_clipboard

**Total: 100 tools** – matches qartex's 109!

### 3.5 Voice Pipeline V2 (Hits PRD Phase 3 STT Robustness Hard)

**Current V1 Fixes:** Already fixed Sound Mapper bug, Realtek preferred, thresholds lowered to 0.003, 10/10 tests pass.

**V2 Upgrades:**

**Wake Word Hybrid (From Jarvis Research):**
- Continuous listening for "Hey OMNI" via pvporcupine (wake word engine, offline, low CPU)
- OR PTT V toggle (current) – user can choose in settings
- Hybrid: Wake word wakes, then VAD listens for command, then sleeps again
- Saves CPU vs always listening Whisper

**RealtimeSTT (From eadmin2 Research):**
- Instead of press V → record → stop → transcribe (batch), use streaming transcription
- RealtimeSTT library shows live transcription on screen while you talk (like eadmin2 arc reactor HUD)
- Sentence-by-sentence streaming to LLM

**Pipeline:**
```
Wake Word "Hey OMNI" (pvporcupine, offline, 5% CPU)
  → Silero VAD starts (HIGH accuracy)
    → faster-whisper streaming (shows live text on HUD)
      → IntentMapper + LLM Router (Fast tier for quick)
        → Planner breaks into steps
          → Executor runs tools
            → Monitor checks success
              → TTS Kokoro speaks sentence-by-sentence (streaming)
```

**For 1050 Ti:** Use tiny.en Whisper for wake word + base.en for command, both INT8, ~1.5x real-time still okay.

### 3.6 Memory V2 (Hits PRD Phase 5 Intelligence)

**Current V1:** Last command only

**V2:**

**Short-term (Context - 5 turns):**
- Remembers last 5 commands and results
- "Screenshot that" – knows "that" = last mentioned window
- Chain commands context: "Open Chrome, maximize it" – "it" = Chrome

**Long-term (Persistent - SQLite + Vector):**
- SQLite at `~/.omni/memory.db`: Facts like "User prefers af_sarah voice", "User's name is Zarrar", "Chrome is default browser"
- ChromaDB at `~/.omni/vector.db`: Embeds past conversations, can search "what did we talk about yesterday?"
- mem0 style: Auto-extracts preferences from conversations

**Example:**
```
User: "I prefer British voice"
→ MemoryAgent.learn_preference("TTS voice = bf_gemma")

User (next day): "Open YouTube"
→ MemoryAgent.recall("YouTube") → "User likes British voice, use bf_gemma for TTS"

User: "What did we do yesterday?"
→ ChromaDB search yesterday's conversations → "You opened GitHub and ran tests"
```

### 3.7 Vision V2 (Hits PRD Phase 6 - Never Done Before)

**Current V1:** Placeholder "what's on screen" text.

**V2:**

**Screen Capture:** `mss` library (fast) + `PIL ImageGrab` fallback
**Vision Model:** LLaVA 1.6 7B local via Ollama (runs on 1050 Ti with INT4, ~4GB VRAM) OR Moondream2 (smaller, 2GB) OR cloud Gemini Vision for better accuracy

**Features:**
- `describe_screen()` → LLaVA: "I see VS Code with main.py open, Chrome behind it"
- `find_element("login button")` → OWLv2 or YOLO to find coordinates, then click via pyautogui
- `read_text_on_screen()` → EasyOCR or Tesseract OCR
- Proactive: Every 30s, capture screen, if new window opened, suggest: "I see you opened Chrome, want me to search?"

**For Hackathon Demo:** Use pre-captured screenshots + mock LLaVA responses to avoid needing large vision model download. But architecture ready.

### 3.8 UI V2 - Cinematic HUD (Hits PRD Phase 4 Accessibility)

**Current V1:** Simple PyQt radial orb (40px, cyan/green/purple/white)

**V2 - From qartex + eadmin2 Research:**

**Three.js Orb (2400 particles):**
- Use PyQt WebEngineView to embed HTML + Three.js
- GLSL shader particle system: 2400 particles orbiting
- State colors: Blue idle (slow orbit), Orange thinking (fast spin), Green listening (pulse), Red error (chaotic)
- Much more impressive than radial gradient

**Arc Reactor HUD (From eadmin2):**
- Center ring that glows, click to talk
- Live transcription appears around ring while you speak
- Outer ring shows system stats: CPU, RAM, mic level (like novik133 system monitor)

**Waveform Visualizer (From Hasan-Ikbal):**
- When listening, show waveform animation (like Siri wave)
- Use pyqtgraph or custom QPainter

**System Dashboard (From novik133):**
- Tab in settings: Live CPU, RAM, GPU VRAM, temp graphs
- Mic level real-time (from test_mic_level.py)

**For Hackathon Quick Win:** Keep current orb but add waveform + improve to 140px, add tooltip, add context menu, make it draggable (we already did). For V2, add WebEngine Three.js later.

### 3.9 Security V2 - Biometric (From vannu07 Research)

- **Face Recognition:** `face_recognition` lib (dlib) - enroll face, then only you can use OMNI, or greet by name
- **Voice Auth:** Speaker verification via `pyannote` or simple voice embedding
- **Example:** OMNI sees you via webcam, says "Welcome back, Zarrar"

**For Privacy:** All local, no cloud.

---

## 4. Clean Workspace Structure - V2

**Current Cleaned:**
```
Omni/
├── .git/
├── Assets/
├── LICENSE
├── README.md (root only)
├── omni.py (fixed)
├── requirements.txt (fixed)
├── requirements-minimal.txt
├── docs/ (15 md files, all docs here!)
└── omni/ (core code)
```

**V2 Proposed Clean Structure:**
```
Omni/
├── README.md
├── omni.py (entry)
├── requirements.txt
├── requirements-v2.txt (new deps: chromadb, pvporcupine, mss, etc.)
├── docs/ (all md)
├── assets/ (images, models)
├── omni/ (V1 stable, keep working)
│   ├── core/
│   ├── voice/
│   ├── tts/
│   ├── plugins/ (12 plugins)
│   └── ui/
├── omni_v2/ (NEW - JARVIS KILLER)
│   ├── __init__.py
│   ├── agents/ (multi-agent)
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── monitor.py
│   │   ├── evaluator.py
│   │   └── memory.py
│   ├── llm/
│   │   └── router.py (multi-tier)
│   ├── vision/
│   │   ├── screen.py (mss capture)
│   │   └── llava.py (vision model)
│   ├── security/
│   │   └── face_auth.py
│   ├── memory/
│   │   ├── sqlite_store.py
│   │   └── vector_store.py (chroma)
│   ├── voice/
│   │   └── wake_word.py (pvporcupine)
│   ├── ui/
│   │   ├── hud.py (arc reactor)
│   │   └── orb_threejs.html (2400 particles)
│   └── tools/ (100+ tools, replaces plugins)
│       ├── browser/
│       ├── windows/
│       └── ...
└── scripts/
    ├── setup.ps1
    ├── launch-chrome.ps1
    └── test_*.py
```

**Why Keep omni/ and Add omni_v2/?** 
- omni/ V1 is stable, 10/10 tests pass, wins hackathon as backup
- omni_v2/ is experimental V2, can be built incrementally, doesn't break V1

---

## 5. Implementation Roadmap - Hit PRD Phases 4,5,6 Hard

**PRD Original Roadmap:**
- Phase 1 Foundation: DONE
- Phase 2 TTS: DONE
- Phase 3 STT Robustness: DONE
- Phase 4 Accessibility & OS: PLANNED
- Phase 5 Intelligence: PLANNED
- Phase 6 Platform & Packaging: PLANNED

**V2 Roadmap (2 Weeks to 1st Place):**

**Week 1 - Foundation + Intelligence (PRD Phase 5):**
- Day 1: Clean workspace, setup omni_v2 structure, multi-agent skeleton
- Day 2: Memory agent (SQLite + ChromaDB), context 5-turn, persistent
- Day 3: LLM router + Ollama llama3.1 8B local integration, Fast/Brain/Deep/Local tiers
- Day 4: Chain commands parser ("open chrome and maximize") + context "that"
- Day 5: 100 tools expansion (browser 15, windows 15, etc.), migrate 12 old plugins

**Week 2 - Accessibility + Platform + Polish (PRD Phase 4 & 6 + Jarvis Cinematic):**
- Day 6: Wake word "Hey OMNI" via pvporcupine + hybrid PTT
- Day 7: Vision screen capture + LLaVA mock for demo
- Day 8: Three.js 2400 particle orb + arc reactor HUD + waveform
- Day 9: System dashboard (CPU/RAM/GPU live graphs) + face auth + proactive suggestions
- Day 10: Packaging, NSIS installer, auto-setup script, demo video, presentation slides
- Day 11-14: Buffer, testing, polish, 5-min demo video

---

## 6. Tech Stack V2 - GTX 1050 Ti Optimized

| Component | V1 | V2 (JARVIS KILLER) | Why Better |
|-----------|----|--------------------|------------|
| STT | faster-whisper base.en | faster-whisper base.en + RealtimeSTT streaming + pvporcupine wake word | Live transcription, wake word, more Jarvis-like |
| VAD | Silero HIGH | Silero + energy fallback + auto-calibration | Keep, already HIGH |
| TTS | Kokoro af_sarah | Kokoro + Piper TTS option + ElevenLabs optional + streaming sentence-by-sentence | More voices, faster |
| LLM | None (IntentMapper) | Ollama llama3.1 8B INT4 local (4GB VRAM) + optional Claude/GPT | True conversation, not just commands |
| Memory | Last command | SQLite + ChromaDB + mem0 | Persistent, learns |
| Vision | Placeholder | mss + LLaVA 7B INT4 / Moondream2 | Real screen understanding |
| Face Auth | None | face_recognition + voice auth | Biometric security |
| UI | Radial orb 40px | Three.js 2400 particles + arc reactor HUD + waveform + dashboard | Cinematic, hackathon wow factor |
| Tools | 12 plugins, 47 patterns | 100+ tools, chainable, context-aware | Matches best Jarvis 109 |
| Agent | Single reasoner | Multi-agent Planner→Executor→Monitor→Evaluator | True autonomy, re-plans on fail |

**Install for V2:**
```bash
pip install -r requirements-v2.txt
# Adds: pvporcupine, chromadb, ollama, mss, opencv-python, face_recognition, eel, pyqt5-webengine, etc.

# Ollama local LLM (4GB VRAM, runs on 1050 Ti with INT4)
ollama pull llama3.1:8b
ollama pull llava:7b  # Vision

# Models still local: Whisper base.en, Kokoro, etc.
```

---

## 7. Demo Script V2 - 8 Min Hackathon Winning

**0:00-0:30 Hook:** "Imagine controlling your PC without hands, without cloud, without giving your data away. That's OMNI V2."

**0:30-1:00 Cinematic UI:** Show Three.js orb 2400 particles pulsing blue idle, arc reactor HUD glowing, "Hey OMNI" wake word.

**1:00-2:30 Voice Demo (Chain Commands + Context):**
- "Hey OMNI, open Chrome, maximize it, and go to YouTube and play music" → Planner breaks into 4 steps, Executor runs, Monitor checks, all in one utterance (chain commands - Blazehue feature)
- "Screenshot that" → Context knows "that" = YouTube
- "What can I say?" → Context-aware hints

**2:30-3:30 Accessibility (PRD Phase 4):**
- "What's on screen?" → Vision: "I see Chrome with YouTube, VS Code behind"
- "Find login button" → Vision finds coordinates, clicks
- High contrast mode toggle

**3:30-4:30 Intelligence (PRD Phase 5):**
- "Remember I prefer British voice" → Memory stores
- Next day: "Open YouTube" → Uses British voice (learned preference)
- "What did we do yesterday?" → ChromaDB recalls

**4:30-5:30 Integrations (PRD Phase 4 Beta):**
- Gmail, Calendar, Smart Home (demo mode)

**5:30-6:30 Proactive + System Monitor:**
- Show dashboard: CPU, RAM, GPU live graphs
- Proactive: "I see you're coding, want me to run tests?" (watches screen)

**6:30-7:30 Face Auth + Security:**
- Face recognition login, "Welcome back Zarrar"

**7:30-8:00 Closing:** "OMNI V2: Local, private, 1050 Ti optimized, 100+ tools, multi-agent, cinematic. Your voice is enough."

---

## 8. Why This Wins 1st Place Over Every Jarvis

**Vs qartex (109 tools, Three.js orb):** We match tools (100) + orb (2400 particles) + add 1050 Ti optimization + accessibility-first (they don't) + local-first (they use Claude cloud) + reasoning loop (they don't have Monitor/Evaluator)

**Vs eadmin2 (Hermes + arc reactor):** We match arc reactor HUD + persistent memory + add offline Ollama (they need ElevenLabs cloud) + 1050 Ti optimization + accessibility

**Vs Blazehue (chain commands):** We match chain + context + add vision + face auth + multi-agent

**Vs novik133 (100% offline):** We match offline + add chain commands + vision + face auth + multi-tier LLM

**Vs All:** No one optimizes for GTX 1050 Ti 4GB, 8GB RAM. OMNI V2 does: INT8 quantization, 60s max recording, 4GB VRAM limit, CPU fallbacks. That's our hackathon edge: **JARVIS that runs on low-end hardware, privately, accessibly.**

---

## 9. Immediate Next Steps - Start Over Clean

1. **Clean workspace done:** venv removed, pycache cleaned, docs organized (15 md files)
2. **Research done:** 10 Jarvis projects analyzed, gaps identified
3. **PRD V2 written:** This document hits original PRD Phases 4,5,6 + all Jarvis best
4. **Next:** 
   - Create `omni_v2/` structure
   - Implement multi-agent skeleton (Planner, Executor, Monitor, Evaluator, Memory)
   - LLM router with Ollama local
   - 100 tools expansion (start with browser 15)
   - Three.js orb HTML
   - Wake word "Hey OMNI" via pvporcupine

**User says "start over" - we can:**
- Keep `omni/` V1 stable (backup, already wins)
- Build `omni_v2/` from scratch clean, hitting PRD hard
- Or refactor `omni/` in place to V2

**Recommendation:** Keep V1 as `omni/` backup, build V2 as `omni_v2/` clean, then merge when ready.

---

*OMNI V2 PRD - Hits PRD Phases 4,5,6 + All Jarvis Best - Ready to Build 1st Place Winner*
