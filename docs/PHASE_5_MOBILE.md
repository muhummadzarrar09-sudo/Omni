# 📱 OMNI V3 — Mobile Companion (Phase 5: Mobile-First)

> **The butler in your pocket. Same WiFi, auto-discover, direct WebSocket. ZERO cloud.**

## Why Mobile-First?

A butler that lives on your **laptop** is useful. A butler that lives on your **phone** is **always there**. Push-to-talk from anywhere on your network. Location-aware nudges. Notifications. The form factor unlocks things the laptop can't.

## How They Talk: Local mDNS

When OMNI starts on the laptop, it broadcasts a service over **mDNS/Bonjour**:
- Service name: `_omni-brain._tcp.local.`
- Port: 8765 (or whatever the backend is on)
- TXT records: `version=3.2.0`, `model=qwen2.5-1.5b`, `name=Zarrar's OMNI`

The phone app scans the local network for this service, finds it, and connects directly via **WebSocket**. No relay, no cloud, no accounts.

```
┌─────────────────────┐         ┌─────────────────────┐
│   PHONE             │         │   LAPTOP            │
│  ┌───────────────┐  │         │  ┌───────────────┐  │
│  │ OMNI Mobile   │  │         │  │ OMNI Brain    │  │
│  │ (React Native)│  │  WiFi  │  │ (FastAPI)     │  │
│  └───────────────┘  │◄───────►│  └───────────────┘  │
│         │           │  mDNS   │         │           │
│  ┌──────▼──────┐    │ discovery│  ┌──────▼──────┐    │
│  │ PTT Button  │    │         │  │ mDNS Service │    │
│  │ Voice I/O   │    │         │  │ Broadcaster  │    │
│  │ Location    │    │         │  └─────────────┘    │
│  │ Notifications│   │         │                     │
│  └─────────────┘    │         │                     │
└─────────────────────┘         └─────────────────────┘
              │                              │
              └──── Direct WebSocket ────────┘
                  (ws://laptop.local:8765/ws)
```

## 4 Features in Phase 5 (all mobile-related)

### 5A. mDNS Service Discovery (`omni_v2/network/mdns.py`)
- OMNI laptop auto-broadcasts `_omni-brain._tcp.local.` on port 8765
- Phone app scans for the service
- Auto-connect when in range
- No manual IP addresses, no setup

**Files:**
- `omni_v2/network/__init__.py`
- `omni_v2/network/mdns.py` — laptop-side broadcaster
- `omni_v2/network/discovery.py` — shared protocol

### 5B. Mobile Web App (`mobile/`)
- Single-page web app that runs in the phone's browser
- No install required — just open the URL
- Works on iOS Safari, Android Chrome
- PWA (Progressive Web App) — can be added to home screen
- Push-to-talk button (uses phone's mic)
- Shows live brain state + thought stream
- Receives notifications from OMNI

**Files:**
- `mobile/index.html` — the web app (single file, no build)
- `mobile/app.js` — interactivity
- `mobile/style.css` — mobile-first responsive design

### 5C. Mobile API Endpoints
The phone talks to the laptop via existing + new endpoints:

**New (Phase 5):**
- `GET /api/network/info` — laptop's IP, hostname, port, capabilities
- `POST /api/network/pair` — generate a one-time pairing code
- `GET /api/network/qr` — QR code for instant phone connection
- `POST /api/network/discover` — list all OMNI instances on the LAN
- `WebSocket /ws/mobile` — dedicated mobile WebSocket (binary-safe, lower latency)

### 5D. Proactive + Location Push
- Phone reports location → OMNI knows "you're at the coffee shop" → proactive reminder about your meeting
- Phone reports battery → OMNI shows "phone at 8%" notification
- Phone receives proactive banners as push notifications when app is backgrounded
- Geofencing: "when you arrive home, set the lights"

**Files:**
- `omni_v2/network/location.py` — location push from phone
- `omni_v2/agents/proactive_v2.py` — add geofence rules

## Build Order

We'll start with **5A (mDNS discovery)** since that's the foundation everything else builds on.

1. **5A** — mDNS service discovery on the laptop side
2. **5C** — Mobile API endpoints (info, pair, discover)
3. **5B** — Mobile web app (uses discovery to find laptop)
4. **5D** — Location + proactive push (polish)

## Why This Complements The AIM

The current OMNI is **laptop-tethered**. A butler that can only help when you're at your desk is half a butler. With mobile:

- **AIM #1 Wake word** — works from your phone mic, not just laptop mic
- **AIM #2 Greet by name** — greets on phone unlock
- **AIM #6 Speak first** — push notifications anywhere
- **AIM #8 Remembers** — phone notifications recap yesterday

It's not a NEW feature, it's an **extension** that makes every existing AIM feature work everywhere.

## Privacy Promise

- ✅ **No cloud**: zero servers, zero accounts
- ✅ **No data leaves your devices**: phone and laptop only
- ✅ **Same WiFi only**: won't work outside your home
- ✅ **No telemetry**: nothing phoned home
- ✅ **Open source**: anyone can verify

The hackathon is over. The product is real. Now we make it **mobile**.

---

**Starting with 5A: mDNS service discovery.** Let's go.
