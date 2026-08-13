# OMNI V3 — Phase 5: Mobile-First Perspective

> **Document status (2026-08-11): historical or unqualified reference.** This file records earlier intent, implementation, audit, or setup work. Its completion, test-count, performance, privacy, platform, and production-readiness statements are **not current release claims**. Use the generated [Capability Matrix](CAPABILITY_MATRIX.md) and [Quality Scorecard](QUALITY_SCORECARD.md) for current truth.


> *A butler in your pocket. Your laptop is the brain. Your phone is the companion.*

---

## 🎯 The Mobile-First Vision

OMNI should feel **native to your phone**. Open a URL, scan a code, talk to it
from across the room. No app store. No account. No cloud. Just local WiFi.

This phase flips OMNI from "laptop assistant" to "device-spanning butler":

```
   ┌──────────┐                              ┌──────────┐
   │  LAPTOP  │  ←──  mDNS broadcast  ──→   │  PHONE   │
   │  (Brain) │  ←──  WebSocket /ws/mobile → │  (PWA)   │
   │          │  ←──  HTTP REST /api/...  ─→  │          │
   └──────────┘                              └──────────┘
        ●                                       ●
   Qwen 1.5B                                 Browser
   100+ tools                            voice/mic/camera
   memory/personality                     (in your pocket)
```

---

## ✅ Phase 5A — mDNS Discovery (DONE)

Laptop announces itself on the local network. Phones discover it.

- **Custom UDP broadcast** (no `zeroconf` dep) on port **47624**
- **Magic header** `OMNI-DISCOVER-v1`
- **Broadcast interval**: 5s
- **Payload**: name, host, port, version, model, capabilities, timestamp
- **Phone listener**: `OMNIMDNSDiscovery` (filters by magic + recency)
- **TXT records**: `version`, `model`, `name`, `caps`, `api`

### Files
- `omni_v2/network/mdns.py` — Broadcaster + Discovery
- `omni_v2/network/discovery.py` — NetworkInfo, PairingCode, QR payload
- 13 unit tests in `omni_v2/tests/test_network.py`

### Backend
- Auto-broadcasts on startup (uses user name from profile)
- `/api/network/info` — get this brain's info
- `/api/network/pair` — generate a 6-digit code (5 min TTL)
- `/api/network/qr` — get QR code (PNG + URI)
- WebSocket `/ws/mobile` — dedicated mobile channel

---

## ✅ Phase 5B — Mobile Web App (DONE)

A complete **Progressive Web App** in `mobile/`. Opens in any phone browser,
installable to home screen, no app store needed.

### Features
| Capability | How |
|------------|-----|
| **Discovery** | HTTP probe of common local subnets + manual host entry |
| **QR scan** | In-browser QR scanner (jsQR via CDN, zero install) |
| **Pairing** | 6-digit code entry (or auto-connect from QR URI) |
| **WebSocket chat** | Live message stream, thought bubbles, tool chips |
| **Push-to-talk** | Hold mic button → faster-whisper on laptop → execute |
| **Reconnect** | Auto-reconnect with exponential backoff |
| **Persistence** | localStorage saves last brain + last 50 messages |
| **PWA install** | `beforeinstallprompt` handler, manifest, service worker |
| **Offline shell** | Service worker caches index/css/js, never WS/API |
| **Native feel** | Safe-area insets, theme color, status bar style, no bounce |

### File tree
```
mobile/
├── index.html       (5.6 KB)  - PWA shell, 4 screens (boot/discover/pair/chat)
├── style.css        (12 KB)   - Dark cinematic theme, mobile-first
├── app.js           (27 KB)   - Discovery, WS, PTT, QR scanner, state
├── manifest.json    (1.7 KB)  - PWA manifest, icons (inline SVG)
├── sw.js            (1.6 KB)  - Service worker, cache-first for shell
└── qr.html          (11 KB)   - QR generator (laptop-side, served at /mobile/qr.html)
```

### Backend additions
- `POST /api/voice/transcribe` — upload audio → text (faster-whisper)
- `POST /api/network/pair/verify` — verify 6-digit code
- `GET /api/network/pair/active` — get current valid code
- `GET /api/mobile/qr-page` — JSON data for QR page (auto-fills host/code)
- Static mount `/mobile/` — serves the whole PWA
- `app.mount("/mobile", StaticFiles(...))`

### WebSocket protocol (`/ws/mobile`)
```jsonc
// phone → laptop
{ "type": "mobile_identify", "device": "pwa", "ua": "..." }
{ "type": "text", "text": "what's the weather?" }
{ "type": "audio", "format": "webm", "data": "<base64>" }
{ "type": "location", "lat": 33.7, "lon": 73.0 }
{ "type": "ping" }

// laptop → phone
{ "type": "welcome", "brain": "OMNI" }
{ "type": "identified" }
{ "type": "thinking" }
{ "type": "transcript", "text": "..." }
{ "type": "message", "text": "..." }
{ "type": "error", "error": "..." }
{ "type": "pong" }
```

### How it works end-to-end

1. **Laptop** starts FastAPI on `:8765` + mDNS Broadcaster (UDP 47624)
2. **Phone** opens `http://<laptop-ip>:8765/mobile/` in any browser
3. PWA boots, scans the local network (HTTP probe of common IPs)
4. Found brain shows up as a card → tap → enter 6-digit code (or scan QR)
5. WebSocket connects → chat screen with live messages
6. PTT: hold mic button → record → upload → transcribe on laptop → execute
7. Phone works offline (cached shell) + reconnects automatically

### Tests
46 new tests in `omni_v2/tests/test_mobile.py`:
- File existence (7)
- HTML structure (9)
- JS syntax + handlers (9)
- CSS quality (4)
- Manifest validity (3)
- Service worker (3)
- QR page (3)
- Discovery roundtrip (1)
- **Live backend tests (7)**: actual HTTP probes to running server

All 46 pass. Total project: **185+ tests passing**.

---

## ✅ Phase 5C — Location Push & Geofencing (DONE)

The brain knows where you are. The phone tells it. The brain acts on it.

### Features
| Capability | How |
|------------|-----|
| **Places** | Named locations (Home/Work/Gym) with lat/lon + radius (default 100m) |
| **Rules** | "When I [arrive/depart/dwell] at [place] → run [command]" |
| **Dwell** | Detects staying at a place 5+ min (configurable) |
| **Cooldown** | Each rule has 30min default cooldown to prevent spam |
| **Live tracking** | `navigator.geolocation.watchPosition` for continuous updates |
| **One-shot push** | Tap "send location" to push a single fix |
| **Real-time rules** | Rules fire on push — brain executes commands via HTTP/WS |
| **Geofence UI** | Manage places + rules + events on the phone |
| **Sample data** | `POST /api/geofence/seed` adds Home/Work/Gym etc. |
| **Multi-place** | When inside overlapping places, smallest-radius wins |
| **Stats** | Per-place arrival count, dwell time, last visited |
| **History** | Last 1000 location fixes, queryable |

### File tree (new files)
```
omni_v2/agents/geofence.py        (10 KB)  - GeofenceEngine + haversine + place/rule model
omni_v2/tests/test_geofence.py    (11 KB)  - 50 tests (43 unit + 7 live)
```

### Backend additions
- `GET    /api/geofence/status` — counts + current location
- `GET    /api/geofence/dashboard` — full UI payload (places + rules + events)
- `GET    /api/geofence/places` — list all places
- `POST   /api/geofence/places` — create place
- `POST   /api/geofence/places/{id}/update` — edit place
- `DELETE /api/geofence/places/{id}` — remove (cascades rules)
- `GET    /api/geofence/rules?place_id=...` — list rules
- `POST   /api/geofence/rules` — create rule
- `DELETE /api/geofence/rules/{id}` — remove
- `GET    /api/geofence/location` — current location + which place
- `POST   /api/geofence/location` — push a fix → fires rules → brain executes
- `GET    /api/geofence/location/history?limit=N` — last N fixes
- `GET    /api/geofence/events?limit=N` — recent rule firings
- `POST   /api/geofence/seed` — add sample places
- `POST   /api/geofence/clear-events` — wipe event log
- `POST   /api/geofence/reset` — nuke everything

### WebSocket additions (`/ws/mobile`)
- Phone sends `{"type": "location", "lat": X, "lon": Y, "accuracy_m": Z}`
- Server pushes back:
  - `{"type": "location_update", "location": {...}, "current_place": {...}}`
  - `{"type": "geofence_event", "event": {place_name, event, command, ts}}`
  - `{"type": "location_ack", "fired_count": N}`

### Mobile UI additions
- **Location card** under chat input: "📍 Work · 12m away"
- **Send button**: pushes current GPS fix to brain
- **Manage button**: opens Places & Rules screen
- **Seed button**: one-tap sample places
- **Places & Rules screen**:
  - List of places with icons, lat/lon, radius
  - List of rules with colored event chips
  - Recent events with timestamps
  - Add/remove inline
- **Modals** for adding places (with "use my location") and rules
- **WS handler** for `geofence_event`, `location_update`, `location_ack`

### Geofence math
- Haversine formula, accurate to ~0.5%
- Tested: Islamabad → Lahore ≈ 270km
- Place detection: `is_inside(lat, lon, place_lat, place_lon, radius)`
- Earth radius: 6,371,000m

### Tests
50 new tests in `omni_v2/tests/test_geofence.py`:
- 5 Haversine math
- 8 Place CRUD
- 8 Rule CRUD
- 12 Location events (arrive/depart/dwell/cooldown/stats)
- 6 Status & dashboard
- 1 Singleton
- 2 Sample data
- **7 live backend tests** (all 7 pass)

### Example flow
```
1. User: "When I arrive at the gym, start my workout playlist"
2. OMNI: creates Place "Gym" at current location (r=150m)
3. OMNI: creates Rule "arrive" @ Gym → "play workout playlist"
4. User drives to gym, phone GPS pushes (33.679, 73.043) every 30s
5. GeofenceEngine: lat/lon inside Gym radius → fires event
6. Brain.execute("play workout playlist") → music starts
7. Phone receives "geofence_event" notification
8. Stats: total_arrivals++, total_dwell_min updated
```

### Privacy
- All location data stays on the laptop (`data/geofence/`)
- Phone only sends coords when user taps "send" or via continuous watch
- No GPS tracking unless user explicitly enables watch
- User can clear events / wipe history anytime
- Zero external services

---

## ✅ Phase 5D — Notification Center & Send-to-Phone (DONE)

Your brain can now push notifications to your phone, with full DND/prefs control.

### Features
| Capability | How |
|------------|-----|
| **Send to phone** | Brain tool: "send to my phone: build done" |
| **Notifications inbox** | All notifications stored, filterable by category/unread |
| **Read tracking** | Mark single/all as read |
| **VAPID web push** | Auto-generated keys, real push when browser closed |
| **Device registry** | Track all paired devices, push endpoint, capabilities |
| **Dedup** | Notifications with same dedup_key replace earlier ones |
| **Multi-format export** | Download history as JSON or CSV |
| **Categories** | info/success/warn/error/action/geofence/proactive/schedule/wake/tool |
| **Priority** | 0=low, 1=normal, 2=high, 3=urgent |

### Backend additions
- `POST /api/voice/transcribe` — phone mic audio → text
- `POST /api/notifications/subscribe` — register VAPID endpoint
- `GET  /api/notifications/devices` — list paired devices
- `GET  /api/notifications/dashboard` — full UI payload
- `POST /api/notifications` — manual create
- `GET  /api/notifications` — list (limit, category, unread_only)
- `POST /api/notifications/{id}/read` — mark read
- `POST /api/notifications/read-all` — mark all read
- `GET  /api/notifications/{id}` — get one
- `DELETE /api/notifications` — clear (by category)

### Send-to-Phone tool (registered with brain)
- `send to my phone: <message>`
- `notify my phone: <message>`
- `text me: <message>`
- `ping my phone` (with default message)

### Mobile UI
- **Bell button** in chat topbar with unread badge
- **Notifications screen** with full list, swipe to read
- **Slide-down toast** for real-time notifications
- **Auto-refresh** every WS notification event
- **Mark all read** button

---

## ✅ Phase 5E — Notification Preferences & Snooze (DONE)

User-controlled notification settings. The brain can now snooze / mute notifications via natural language.

### Features
| Capability | How |
|------------|-----|
| **Per-category mute** | Toggle info/warn/error/etc. in settings |
| **DND hours** | Set start/end hour, active days |
| **Min priority** | Only show >= priority N |
| **Daily limits** | Per-category max per day |
| **Snooze** | Mute all for N minutes (15/30/60/120 presets) |
| **Tag filters** | Allow-list / block-list by tag |
| **Export** | JSON or CSV download of full history |
| **Suppressed log** | Blocked notifications still saved for audit |

### Backend additions
- `GET  /api/notifications/prefs` — get all prefs + snooze state
- `POST /api/notifications/prefs` — update prefs (DND, mute, min_priority, etc.)
- `POST /api/notifications/prefs/reset` — reset to defaults
- `POST /api/notifications/snooze` — snooze for N minutes
- `DELETE /api/notifications/snooze` — lift snooze
- `GET  /api/notifications/export?format=json|csv` — download history

### Snooze tool (registered with brain)
- `snooze for 30 minutes`
- `mute for 1 hour`
- `silence for 15 min`
- `enable do not disturb` / `enable dnd`
- `stop snooze` / `lift` / `resume`

### Mobile UI
- **Notification Settings screen** with toggles for each category
- **DND hour pickers** (from/until)
- **Snooze preset buttons** (15/30/60/120 min)
- **Snooze banner** in notification list (with "lift" button)
- **Bell rings** when new notification arrives
- **Slide-down toast** for real-time alerts

### Critical bug fix
During Phase 5E, the `PluginManager.get_plugin()` had a bug: when an action like `communication_snooze_notifications` was looked up, it fell into a "category match" fallback that picked the **first** plugin in the `communication` category alphabetically — which was `send_to_phone`. The fix:
1. Added explicit aliases for `communication_snooze_notifications` → `snooze_notifications` and `communication_send_to_phone` → `send_to_phone`
2. Changed the category-fallback loop to match the action's **suffix** against plugin names instead of returning the first plugin

### Tests
**37 new tests** in `omni_v2/tests/test_notification_prefs.py`:
- Defaults loaded (5)
- Snooze (5)
- Should-notify logic (6)
- DND (3)
- Status (2)
- Singleton (1)
- Snooze tool (6)
- **Live backend tests (7)**: prefs, snooze, unsnooze, update, export JSON, export CSV, snooze via brain

### Total Phase 5 test suites: 5 new suites
| Test file | Tests | Coverage |
|---|---|---|
| `test_network.py` (5A) | 13 | mDNS discovery |
| `test_mobile.py` (5B) | 55 | PWA + endpoints |
| `test_geofence.py` (5C) | 50 | Geofence engine |
| `test_notifications.py` (5D) | 40 | Notification center |
| `test_notification_prefs.py` (5E) | 37 | Prefs + snooze |
| **Total Phase 5** | **195 tests** | **all pass** |

---

## 🎉 Phase 5 Summary

**Mobile-First is COMPLETE.** All 5 sub-phases shipped:
- **5A** — mDNS auto-discovery (zero deps)
- **5B** — Mobile PWA companion (chat, PTT, QR, geofence UI)
- **5C** — Geofence engine (places, rules, dwell, cooldowns)
- **5D** — Notification center + send-to-phone tool
- **5E** — Notification prefs + snooze tool

The phone is now a true **first-class companion** to the laptop brain: discoverable, connectable, pushable, geofence-aware, notification-aware, snooze-aware.

**Next**: Visual-First perspective — the brain watches what you're doing and acts proactively.

---

## 📊 AIM Score Impact

| Phase | Score | Status |
|-------|-------|--------|
| AIM 6/10 | Foundation (Qwen + tools + agents) | ✅ |
| AIM 7/10 | Memory + Profile (Phase 1) | ✅ |
| AIM 8/10 | Personality + Opinion (Phase 2) | ✅ |
| AIM 9/10 | Onboarding + Demo (Phase 3) | ✅ |
| **AIM 10/10** | **Vision + Voice clone + Marketplace + SDK (Phase 4)** | **✅** |
| Mobile-First | Phone companion (Phase 5A+5B) | ✅ |
| Visual-First | Ambient awareness | ⏳ next |
| Collab-First | Workflow learning | ⏳ |
| Ambient-First | Invisible butler | ⏳ |

Each perspective **compounds** the AIM, not just adds to it. Mobile-first
unlocks new AIM dimensions:
- **Reaches you anywhere** (butler in pocket, not tied to desk)
- **Zero-friction capture** (voice memo, photo, location → brain)
- **Always-available** (browser tab, no install)
- **Privacy by architecture** (no cloud relay, all on WiFi)

---

## 🔒 Privacy Guarantees

- ✅ **No cloud relay** — phone ↔ laptop on local WiFi only
- ✅ **No accounts** — pairing is 6-digit code, expires in 5 min
- ✅ **No telemetry** — zero analytics, zero tracking
- ✅ **No external services** — QR scanner is the only CDN dep
- ✅ **No app store** — PWA, browser-only
- ✅ **Open source** — fully auditable

---

## 🚀 Quick start

```bash
# On the laptop
omni start  # FastAPI on :8765 + mDNS broadcast

# On the phone browser
open http://<laptop-ip>:8765/mobile/
# or scan the QR code shown at http://localhost:8765/mobile/qr.html
```

That's it. Your phone is now a voice/text/location remote for OMNI.
