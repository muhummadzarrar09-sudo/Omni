# 🎨 OMNI V2 - UI Scope Hardened - 6 Questions Answered

**Date:** 2026-07-11 | **Status:** 6 Questions to Harden Scope - Answered | **Result:** Clear Scope for Rust Desktop App + Whisper Flow Widget

---

## User Answers to 6 Hardening Questions:

### Q1: Rust Stack?
**Answer:** `tauri_hybrid` - Tauri hybrid (Rust shell + Python backend via IPC) - Best of both, keeps your 100+ tools, fast to build

**Implication:**
- Keep Python backend `omni_v2/` with 100+ tools, multi-agent, STT 4-tier, memory SQLite+Chroma
- Build Rust shell via Tauri v2 that spawns Python as sidecar binary
- Frontend: Svelte or React (Vite) for UI, Rust via Tauri IPC
- Benefits: Small binary (vs Electron), native OS webview, secure, cross-platform Windows/Mac/Linux, keeps Python logic

**From Research:**
- Example: `dieharders/example-tauri-v2-python-server-sidecar` - Tauri + Python FastAPI sidecar via PyInstaller single-file exe
- Example: `AlanSynn/vue-tauri-fastapi-sidecar-template` - Vue + FastAPI sidecar, compiled to platform-specific exe, placed in `src-tauri/bin/api/`
- Tauri manages Python sidecar lifecycle: spawns on app start, kills on exit
- IPC: Frontend JS ↔ Tauri Rust (invoke) ↔ Python sidecar via HTTP (localhost:8000) or stdin/stdout

---

### Q2: Widget Behavior?
**Answer (Custom):** "Auto-Hide with buttons as well PLUS when spoken to it pops up and than it will listen than transcribe my request and THAN will give me an answer in its DEDICATED window with some breif description AS MUCH will be needed"

**Hardened Scope:**

**Auto-Hide Bottom Widget:**
- Normally: Hidden (or tiny 40px pill)
- On wake word "Hey OMNI" or PTT V press or click widget button: Slides up (animation)
- States:
  - Hidden → Pop up → Listening (waveform, green pulsing)
  - → Transcribing (live text appears as you speak, like Whisper Flow)
  - → Thinking (orange spin, "Thinking...")
  - → Answer in DEDICATED window (brief description as much needed, not just short)

**Buttons in Widget:**
- Mic mute/unmute (big)
- Settings gear
- Drag handle
- Close/minimize

**Dedicated Answer Window:**
- When spoken to, pops up dedicated window (not just tagline) with brief description as much needed
- Example: "open github and search for iron man" → Answer window shows "Opened github | Searching for iron man" with brief description
- Auto-hides after 5 sec or on click outside, but keeps in history

**Inspo from Whisper Flow Research:**
- Whisper Flow (Wispr Flow) is ambient AI medical scribe with floating draggable panel, record/transcribe/generate notes without leaving workflow
- Drag & drop audio/video files to transcribe (from Whisper Flow UI research)
- Batch processing multiple files
- Auto-downloads models, fully C++ Qt, Vulkan GPU acceleration

**For OMNI V2:**
- Bottom widget like Whisper Flow floating panel: Drag & drop files to transcribe (e.g., drop mp3/wav/video into widget → transcribe via Whisper)
- Record button to start/stop
- Live transcription appears while speaking
- Dedicated answer window pops up with result

### Q3: Mic Toggle?
**Answer:** `hybrid_toggle` - Hybrid: Wake word "Hey OMNI" always-on + PTT V toggle + big mic mute button + sensitivity slider

**Hardened Scope:**

**Hybrid Mic:**
- Wake word "Hey OMNI" always-on via openwakeword/pvporcupine (5% CPU, offline) - continuous listening for "Hey OMNI"
- PTT V toggle - press V to manually start/stop (for noisy env or privacy)
- Big mic mute button in UI widget + dashboard (toggles both wake word and PTT)
- Sensitivity slider in settings: VAD threshold (0.001 very sensitive to 0.01 strict) + wake word sensitivity 0.3-0.9
- Visual: Mic icon green when listening, red when muted, orange when thinking
- Settings: Toggle wake word on/off, PTT on/off, choose mic device (Realtek preferred, not Sound Mapper - fixed)

**From User Log:**
- PTT V toggle ON/OFF works (your log shows PTT monitoring started, PTT ON/OFF)
- Wake word not implemented yet switched to PTT (your log shows "No wake word engine - using PTT V toggle only")
- Fixed in Phase 3: openwakeword with ONNX not tflite, lower threshold 0.3

### Q4: Output Modes?
**Answer:** `toggle_user` - User toggle in UI: Mode A = Tagline in widget area (longer answers), Mode B = Dialog near cursor for thinking + short output (< 50 chars)

**Hardened Scope:**

**Mode A - Tagline in Widget Area (Longer Answers):**
- Answers appear in bottom widget dedicated window with brief description as much needed
- Example: "open github and search for iron man" → Widget shows "Opened: https://github.com | Searching for: iron man" with description
- Good for longer answers, history, chain commands
- Widget stays visible with answer, user can copy, close, or click to open

**Mode B - Dialog Near Cursor for Thinking + Short Output (< 50 chars):**
- Thinking state: Dialog box appears near cursor (like Whisper Flow) with "Thinking..." + pulse
- Short output (< 50 chars): Dialog near cursor shows short answer, auto-hides after 3 sec
- Example: "volume up" → Dialog near cursor: "Volume up" (short, near cursor)
- Example: "open github and search..." → Thinking near cursor "Thinking... 3 steps", then final long answer in widget tagline area

**Toggle in UI:**
- Settings → Output Mode → Dropdown: "Tagline in widget" / "Dialog near cursor" / "Both (thinking near cursor, final in widget)" / "Auto (short near cursor, long in widget)"
- User can toggle as you said
- Default: Auto - Short (< 100 chars) near cursor, long in widget, thinking always near cursor

**What is SHORT?**
- Short: < 50 chars for dialog near cursor mode (your spec: SHORT ones obviously)
- Long: >= 50 chars in widget tagline area
- Thinking: Always near cursor (pulse) regardless of mode

### Q5: Dashboard Content?
**Answer (Custom):** "Take inspo from Whisper Flow desaktop app that will give you more clarity than my words and raw ideas can but if you still want it though so i'd say use the UI to give a chat interface and some settings area, and some whiusper flow stuff like drag-dropping into it to transcribe and stuff like whisper flow"

**Hardened Scope - Inspired by Whisper Flow Desktop App Research:**

**From Whisper Flow Research:**
- EasyWhisperUI: Fast, native desktop UI for transcribing audio/video using Whisper, built C++ Qt, drag & drop multiple files, batch processing, auto-downloads models, GPU Vulkan acceleration, real-time console output
- WhisperFlow (medical): Floating draggable panel, record/transcribe/generate notes without leaving workflow, browse previous encounters, real-time transcription
- Wispr Flow vs Superwhisper vs MacWhisper: Live system-wide dictation Option-Space anywhere, custom modes per app (Slack, email, code, terminal) reshape output style

**OMNI V2 Dashboard - Chat Interface + Settings + Whisper Flow Drag-Drop:**

**Main Window (Tauri + Svelte/React):**
- **Left Panel - Chat Interface (like Whisper Flow + ChatGPT):**
  - Chat history: User voice commands + assistant responses, with timestamps
  - Each message: User bubble (transcribed text) + Assistant bubble (response + brief description as much needed)
  - Chain commands: Show steps expanded: "Step 1: Opened chrome, Step 2: Maximized, Step 3: Go to YouTube"
  - Memory: Shows recent memories, preferences (British voice, etc.)
  - Search: Search chat history via SQLite + ChromaDB vector

- **Center Panel - Orb / HUD (Cinematic):**
  - Three.js 2400 particle orb (blue idle, green listening, orange thinking, white speaking, red error)
  - Arc reactor HUD glowing ring (from eadmin2 research)
  - Waveform visualizer when listening
  - System stats: CPU/RAM/mic level
  - Click orb to start/stop listening

- **Right Panel - Settings Area:**
  - **Voice I/O:** Mic selection (Realtek preferred), mic test level live RMS bar, PTT key V, wake word toggle + sensitivity slider, VAD threshold, TTS voice af_sarah/bf_gemma + speed
  - **STT:** Engine selection auto/realtimestt/vosk/google/faster-whisper, no-cloud toggle, language auto/en
  - **LLM:** Provider ollama/local/openai/anthropic, model llama3.1:8b, tier Fast/Brain/Deep, HF_TOKEN input
  - **Vision:** Screen capture toggle, LLaVA model selection, TurboVLM moondream2/qwen2-vl
  - **System:** Start with Windows, minimize to tray, debug mode, data folder location (unanimous inside project/data/)
  - **Tools:** Enable/disable 100+ tools, custom workflows
  - **Accessibility:** High contrast, large text, audio only, keyboard nav, status announcements

- **Bottom Widget - Whisper Flow Style (Auto-Hide):**
  - **Drag & Drop Area:** Like Whisper Flow: Drag audio/video files (mp3, wav, mp4) into widget to transcribe via Whisper
  - **Record Button:** Big mic button, click to start/stop recording
  - **Live Transcription:** Shows live text as you speak (like Whisper Flow medical scribing)
  - **Tagline Answers:** Longer answers appear here with brief description as much needed
  - **Buttons:** Mic mute, settings gear, drag handle, close
  - **Auto-Hide:** Hidden when idle, pops up when spoken to (wake word or PTT), shows listening/transcribing/answer, auto-hides after 5 sec or on click outside

**Whisper Flow Inspo Features to Add:**
- Drag & drop audio/video files into widget to transcribe (like EasyWhisperUI batch processing)
- Batch processing multiple files at once
- Auto-downloads missing models (Whisper, Kokoro, Vosk) with progress bar
- Real-time console output while transcription running
- Transcript opens in widget + saves to data/logs/transcripts/
- Choose output format: txt / srt with timestamps
- Custom modes per app: For Slack, rewrite output as Slack style, for email as email style, for code as code comment style (like Superwhisper)

### Q6: Platform + IPC?
**Answer:** `cross_platform_tauri` - Cross-platform Tauri + Python sidecar, works Windows/Mac/Linux, still Python backend

**Hardened Scope:**

**Cross-Platform Tauri + Python Sidecar (Best for Hackathon):**

**From Research:**
- `dieharders/example-tauri-v2-python-server-sidecar`: Tauri v2 + Python FastAPI sidecar via PyInstaller single-file exe, compiled to platform-specific exe in `src-tauri/bin/api/`, placed via package.json build scripts
- `AlanSynn/vue-tauri-fastapi-sidecar-template`: Vue + FastAPI sidecar, Tauri manages Python sidecar lifecycle (spawns on app start, kills on exit), IPC Frontend JS ↔ Tauri Rust (invoke) ↔ Python sidecar via HTTP localhost
- Tauri orchestrates frontend and backend into native app, small binary vs Electron, uses OS webview, secure, cross-platform

**Architecture:**

```
Frontend (Svelte/React + Vite, in /frontend)
  ↓ Tauri IPC (window.TAURI.invoke)
Rust Shell (src-tauri/src/main.rs)
  ↓ Spawns and manages Python sidecar
Python Sidecar (omni_v2 as FastAPI server, compiled via PyInstaller to single exe)
  ↓ In src-tauri/bin/api/
  FastAPI: /transcribe, /chat, /tools, /memory, /vision, /wakeword
  ↓
omni_v2/ (100+ tools, multi-agent, SQLite+Chroma in data/)
```

**Project Structure for Tauri Hybrid:**

```
Omni/
├── src-tauri/ (Rust shell)
│   ├── Cargo.toml
│   ├── tauri.conf.json (app name OMNI V2, permissions fs, dialog, shell sidecar)
│   ├── src/main.rs (spawns Python sidecar, manages lifecycle, IPC)
│   ├── src/api.rs (py_api command implementation)
│   └── bin/api/ (compiled Python sidecar exe: main-x86_64-pc-windows-msvc, main-x86_64-apple-darwin, etc.)
├── frontend/ (Svelte/React UI)
│   ├── src/
│   │   ├── App.svelte (main)
│   │   ├── components/
│   │   │   ├── Orb.svelte (Three.js 2400 particles)
│   │   │   ├── HUD.svelte (arc reactor)
│   │   │   ├── BottomWidget.svelte (Whisper Flow style auto-hide)
│   │   │   ├── Dashboard.svelte (chat + settings + drag-drop)
│   │   │   ├── ChatInterface.svelte
│   │   │   └── SettingsPanel.svelte
│   │   └── lib/
│   │       └── api.js (calls Tauri invoke -> Rust -> Python sidecar HTTP)
│   └── vite.config.js
├── omni_v2/ (Python backend - sidecar)
│   ├── app_fastapi.py (FastAPI server for sidecar: /transcribe, /execute, /memory, etc.)
│   └── ... (existing multi-agent, tools, etc.)
├── scripts/
│   ├── build_sidecar.ps1 (build Python sidecar via PyInstaller)
│   └── ...
└── docs/ (29 md files)
```

**Build Process:**

```bash
# Frontend
cd frontend && npm install && npm run build

# Backend sidecar - compile Python to single exe via PyInstaller
# In package.json:
# "build:sidecar-winos": "pyinstaller --onefile --name main-x86_64-pc-windows-msvc src/backends/main.py --distpath src-tauri/bin/api"
cd src && pip install pyinstaller && pyinstaller ...

# Tauri app - bundles frontend + sidecar into MSI/DMG/AppImage
cargo tauri build
# Output: src-tauri/target/release/bundle/msi/OMNI_V2_2.0.0_x64_en-US.msi (Windows)
#         src-tauri/target/release/bundle/dmg/OMNI_V2_2.0.0_x64.dmg (macOS)
```

**IPC Flow:**

1. Frontend Svelte: User says "open github" -> calls `window.__TAURI__.invoke('execute_command', {text: 'open github'})`
2. Rust main.rs: Receives invoke, forwards to Python sidecar via HTTP `http://localhost:8000/execute` with text
3. Python sidecar FastAPI: `/execute` endpoint -> Planner→Executor→Monitor→Evaluator→Memory -> returns result
4. Rust: Returns result to frontend Svelte
5. Svelte: Shows result in bottom widget tagline or dialog near cursor, updates orb state, plays TTS via Web Audio API or via Python TTS

**Benefits:**
- Small binary vs Electron (uses OS webview)
- Secure (Tauri allowlist for fs, dialog, shell sidecar)
- Cross-platform Windows/Mac/Linux (GTX 1050 Ti Windows optimized first, but works everywhere)
- Keeps Python 100+ tools, multi-agent, SQLite+Chroma - no rewrite!
- Python sidecar compiled to single exe, no Python needed on user machine (if bundled)

**For Hackathon:**
- Dev: `cargo tauri dev` (Vite dev server + Python sidecar)
- Build: `cargo tauri build` (MSI for Windows)
- Setup wizard: NSIS installer or Tauri MSI already is installer!

---

## Hardened Scope Summary - What We Build:

**Rust Stack:** Tauri hybrid, Rust shell + Python sidecar via IPC (FastAPI + PyInstaller), Svelte frontend, keeps Python 100+ tools, cross-platform

**Widget Behavior:** Auto-hide bottom center like Whisper Flow, with buttons (mic mute, settings, drag handle), pops up when spoken to (wake word or PTT), shows listening waveform + live transcription + final answer in dedicated window with brief description as much needed, drag & drop audio/video files to transcribe (like EasyWhisperUI batch processing)

**Mic Toggle:** Hybrid - Wake word "Hey OMNI" always-on (openwakeword/pvporcupine 5% CPU) + PTT V toggle + big mic mute button in widget and dashboard + sensitivity slider (VAD threshold + wake word sensitivity)

**Output Modes:** User toggle in UI settings - Mode A Tagline in widget area (longer answers + brief description), Mode B Dialog near cursor for thinking + short output (< 50 chars), Auto mode: short near cursor, long in widget, thinking always near cursor, toggle in UI

**Dashboard Content:** Inspired by Whisper Flow - Chat interface left (history, memory, search), center orb/HUD cinematic, right settings panel (voice I/O mic selection + test level + PTT key + wake word toggle + sensitivity, STT engine + no-cloud toggle, LLM provider + model + tier + HF_TOKEN, vision, system, tools enable/disable, accessibility), bottom widget auto-hide with drag & drop files to transcribe like Whisper Flow + record button + live transcription + tagline answers, custom modes per app (Slack, email, code, terminal style)

**Platform IPC:** Cross-platform Tauri + Python sidecar, Windows optimized first (GTX 1050 Ti), works Mac/Linux, Python backend via FastAPI sidecar compiled to single exe in src-tauri/bin/api/, IPC Frontend Svelte --invoke--> Rust --HTTP--> Python sidecar, Tauri manages sidecar lifecycle (spawn on start, kill on exit), small binary vs Electron, secure allowlist

---

## Next Steps - Build Tauri Hybrid UI:

1. **Create Tauri structure:** `src-tauri/`, `frontend/`, `src/backends/main.py` (FastAPI wrapper around omni_v2)
2. **Frontend:** Svelte + Three.js orb + HUD + bottom widget auto-hide + chat + settings + drag-drop
3. **Backend sidecar:** FastAPI with endpoints: `/transcribe`, `/execute`, `/memory`, `/vision`, `/wakeword`, `/tools`
4. **Build:** `cargo tauri dev` for dev, `cargo tauri build` for MSI
5. **Integrate existing omni_v2:** Keep multi-agent, 100+ tools, SQLite+Chroma, etc., just expose via FastAPI

**This scope hardened from your 6 answers + Whisper Flow research + Tauri sidecar research**

---

- Zarrar + Agent | 2026-07-11 | UI Scope Hardened - 6 Questions Answered - Tauri Hybrid + Auto-Hide Widget + Hybrid Mic + Toggle Output + Whisper Flow Inspo + Cross-Platform
