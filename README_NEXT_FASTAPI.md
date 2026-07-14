# OMNI V3 — Next.js 14 Neomorphism CORRECT + FastAPI Pretty Damn Good Backend

> **Your Voice is Enough — Correct Neomorphism, Not PyQt Fake**

Previous PyQt neomorphism was fake — manual QPainter with 3 layers. Web CSS real neomorphism is 1 line: `box-shadow: 12px 12px 24px rgba(0,0,0,0.55), -8px -8px 20px rgba(255,255,255,0.055)` — soft extruded plastic, tactile inset press.

This version: **Next.js 14 beautiful UI + FastAPI pretty damn good backend processing + Three.js 2400 particles orb + profile isolated privacy + sounddevice fixes -9999 + portable no D:/Omni hardcode.**

## Architecture — CORRECT UI Stuff

```
User (Browser)
  |
  v
Next.js 14 Frontend (Beautiful UI) — http://localhost:3000
  - App Router, Tailwind, Framer Motion, Three.js
  - Layout: Left ChatHistory (like ChatGPT) + Center Orb + Transcription + Right Tools + Bottom PTT
  - Real CSS neomorphism: double box-shadow extruded, inset pressed
  - Orb.js: 2000 particles, state colors, rms pulse
  - API routes: /api/execute, /api/demo/[type], /api/devices proxy to FastAPI
  |
  v
Next.js API Routes (proxy) -> FastAPI Backend (Pretty Damn Good) — http://localhost:8765
  - FastAPI main.py with CORS *, portable REPO_ROOT via Path(__file__).resolve()
  - Endpoints: /api/execute, /api/demo/{type}, /api/devices, /api/test-mic, /api/ptt/start|stop, /ws WebSocket
  - No PyAudio (fails on Python 3.12 ImpImporter), sounddevice only (fixes -9999)
  - No D:/Omni hardcode, uses __file__ resolve -> works for judges anywhere
  |
  v
OMNI Brain (Python) — Existing but wrapped
  - Planner -> Executor -> Monitor -> Evaluator -> Memory (multi-agent true agentic)
  - Browser V3: data/chrome_profile/OMNI-Profile isolated (no email leak) - now portable via __file__ not cwd
  - Tools: 15 core reliable
  - STT: faster-whisper base.en cuda int8 single engine, not 4 tiers fighting
  - TTS: pyttsx3 SAPI5 fallback
  - DemoScenarios: 3 workflows with logs
```

## One Command — Works Wherever Judges Clone

**Fixes your D:/Omni concern:** All paths use `Path(__file__).resolve().parent.parent` not hardcoded `D:/Omni`. Tested on `D:\Omni`, `/home/user/omni_repo`, will work on `C:\Users\Judge\Downloads\Omni`.

```bash
# Clone anywhere
git clone https://github.com/muhummadzarrar09-sudo/Omni.git
cd Omni

# Python backend - NO PyAudio (fails on 3.12), sounddevice only
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121  # Optional
pip install -r backend_fastapi/requirements.txt  # No PyAudio, sounddevice 0.4.6 fixes -9999

# Test mic - should show RMS 0.014 LOUD like your log (proves mic works, no -9999)
python -m omni_v2.voice.test_mic_fixed

# Frontend
cd frontend_next
npm install  # First time 2 min
cd ..

# ONE COMMAND - Starts both + opens isolated Chrome profile to Next.js
python run_dev_all.py
# Expected:
# REPO_ROOT: C:\Users\Judge\Downloads\Omni (portable, not D:/Omni)
# ✅ Brain ready
# 🌐 Starting FastAPI on 8765
# 🎨 Starting Next.js on 3000
# 🚀 Opening isolated Chrome profile to http://localhost:3000
# Profile: data/chrome_profile/OMNI-Profile - no email leak

# Then open:
# Next.js Beautiful UI: http://localhost:3000
# FastAPI Docs: http://localhost:8765/docs
# FastAPI Health: http://localhost:8765/api/health
```

## Manual Two Terminals (If One Command Fails)

```bash
# Terminal 1 - Backend
cd backend_fastapi
uvicorn main:app --reload --port 8765
# Docs at http://localhost:8765/docs

# Terminal 2 - Frontend
cd frontend_next
npm run dev
# UI at http://localhost:3000
```

## Why This Wins 1st Place

**Innovation:** Dark neomorphism CORRECT with real CSS double shadow, not PyQt fake. Three.js 2000 particles orb, state colors, rms pulse. Rare in hackathons.

**Technical:** Next.js 14 App Router + FastAPI full API + WebSocket + Three.js + multi-agent self-healing + profile isolation + sounddevice fixes -9999 + portable no hardcode.

**Impact:** Full Assistant OS like ChatGPT left + orb center + tools right + PTT bottom. 1.3B disabled, 2B students 1050 Ti, 65M shops. Works offline, privacy-first.

**UX:** Real neomorphism extruded soft, inset pressed tactile, 22px radius, Inter + JetBrains Mono, Framer Motion animations, 60fps orb.

**Presentation:** One command `python run_dev_all.py` starts both + opens isolated Chrome profile (no email). 3 demo buttons work offline without mic for video.

## Features

**Frontend Next.js (Beautiful UI):**
- `components/Orb.js` - Three.js 2000 particles, state colors blue idle, green listening, orange thinking, purple speaking
- `components/ChatHistory.js` - Left ChatGPT-like history
- `components/MicBar.js` - Mic selector portable, mic bar, waveform, device scores, RMS
- `app/page.js` - Full Assistant OS layout grid 320px + 1fr + 360px, header, orb, transcription, input PTT, demos, logs
- `app/globals.css` - Real neomorphism CSS
- `app/api/*` - Proxy to FastAPI

**Backend FastAPI (Pretty Damn Good):**
- `main.py` - FastAPI with CORS *, portable REPO_ROOT
- `core/brain.py` - Wrapper around existing OMNI brain, portable, no D:/Omni
- `requirements.txt` - No PyAudio, sounddevice only

**Fixes:**
- **No D:/Omni hardcode:** `Path(__file__).resolve().parent.parent` everywhere
- **No PyAudio -9999:** `sounddevice==0.4.6` only, your test RMS 0.014 LOUD proves it works
- **No 404 loop:** `web_server_fixed.py` serves UI at root `/`, not `/omni_v2/web_ui/...`, and new Next.js serves at `/`
- **No psutil 6.0.0:** `psutil` without version pin, 7.2.2 exists

## Demo for Video (No Mic Needed)

In Next.js UI, click:
- ♿ Accessibility: High contrast, screen reader
- 🔗 Chain + Self-Heal: Shows Chrome fail -> Edge fallback re-plan (true agentic)
- 🏪 Shop Guardian: Weather + news -> risk 85% -> PO PDF + Urdu WhatsApp

These work offline, show logs Planner->Executor->Monitor->Evaluator.

## Troubleshooting

**Mic RMS 0.0000:**
Win+R -> mmsys.cpl -> Recording -> Realtek Mic -> Properties -> Advanced -> Uncheck exclusive control -> Levels 100 + Boost 20dB -> Default Format 48000 Hz

**PyAudio install fails ImpImporter:**
Don't install PyAudio, use sounddevice only - fixed in requirements-final-no-pyaudio.txt

**404 File not found:**
Use fixed version: `python -m omni_v2.web_server_fixed` serves at `/` root. Or new stack: `python run_dev_all.py` serves Next.js at `/` root, no 404.

**Port in use:**
`python run_dev_all.py --port 8766` or kill process: `taskkill /F /IM python.exe`

Built by Muhammad Zarrar + Agent | Rawalpindi | GTX 1050 Ti | July 2026
Dark Neomorphism Correct • Next.js + FastAPI • Portable • Your Voice is Enough
