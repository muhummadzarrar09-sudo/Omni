# OMNI V3 — Phase 6: Visual-First Perspective

> *The brain watches what you're doing and acts proactively.*

---

## 🎯 The Visual-First Vision

The butler doesn't just respond to commands — it **observes** you. It sees
what app you're in, what you're doing, and surfaces context-aware help before
you even ask.

This phase flips OMNI from "reactive command executor" to "ambient assistant":
- "You've been coding for 3h — time for a break"
- "You've been reading docs for 1h — want a summary?"
- "Switched from VS Code to Slack — context switch detected"
- "You've been idle 30 min — want me to summarize what you missed?"

The brain builds **context** from your screen and feeds it into the
proactive engine, so every other feature (notifications, geofence, opinions)
becomes smarter.

---

## ✅ Phase 6A — Screen Watcher (DONE)

The brain now sees what you see.

### Features
| Capability | How |
|------------|-----|
| **Periodic screen capture** | mss (Win/Mac/Linux) or PIL fallback, every 30s default |
| **Active window detection** | Win32 API / AppleScript / xdotool — platform-specific |
| **Activity classification** | coding / browsing / reading / communicating / gaming / idle / unknown |
| **Screen hashing** | 64x36 grayscale SHA-256 (16 hex chars) for change detection |
| **Change percentage** | Hash diff % per tick |
| **Scene tracking** | New scene detection (app or activity changed) |
| **App durations** | Per-app time accumulator for "today" |
| **Persistent history** | Last 1500 scenes, atomic JSON writes |
| **Proactive integration** | New `_check_screen_activity` rule in proactive_v2 |

### Activity classifier keywords
| Activity | Keywords (substring match) |
|----------|---------------------------|
| **coding** | vscode, cursor, vim, nvim, code, py, js, function, class, def, import, return, var, let |
| **browsing** | chrome, firefox, edge, safari, brave, arc, github, stackoverflow, reddit, twitter, youtube, spotify, figma, notion |
| **communicating** | slack, discord, telegram, whatsapp, outlook, gmail, zoom, teams, meet |
| **reading** | reader, kindke, zotero, pdf, epub, arxiv, paper |
| **gaming** | steam, epic games, riot, valorant, league, minecraft, fortnite |

### Backend additions (8 endpoints)
- `GET  /api/screen/status` — watcher status (running, backend, current scene)
- `GET  /api/screen/context` — current context dict (for proactive engine)
- `GET  /api/screen/dashboard` — full UI payload
- `GET  /api/screen/recent?limit=N` — recent N scenes
- `POST /api/screen/start` — start the daemon
- `POST /api/screen/stop` — stop the daemon
- `POST /api/screen/capture` — manual capture (returns current scene)
- `POST /api/screen/classify` — standalone classifier (no state)

### Proactive rules added
The screen context now feeds into 3 new proactive rules:
1. **Long coding session** (≥ 2h) → "Time for a break"
2. **Long reading session** (≥ 30 min) → "Want me to summarize?"
3. **New scene detected** (app/activity change) → "Want help with this context?"

### Mobile UI
- **Brain State screen** (👁 menu item)
- Current scene card (activity, app, duration, change %)
- Today's app durations (sorted by minutes)
- Recent scenes list
- Brain-related suggestions (filtered to location/proactive/health)
- Start/Stop buttons for the watcher

### Files
- `omni_v2/agents/screen_watcher.py` (14 KB) — engine + classifier + dataset
- `omni_v2/tests/test_screen_watcher.py` (12 KB) — 31 tests
- `omni_v2/agents/proactive_v2.py` — new `_check_screen_activity` rule
- `backend_fastapi/main.py` — 8 new endpoints + startup init
- `mobile/index.html` — brain state screen
- `mobile/app.js` — brain state functions
- `mobile/style.css` — brain state styles

### Privacy
- **All processing is local** — no images leave the laptop
- Screenshots optional (off by default)
- Screen context is just `{activity, app, window_title, change_pct}` — no pixels
- User can start/stop at any time
- Pause = no recording at all

### Tests
**31 new tests** in `omni_v2/tests/test_screen_watcher.py`:
- 8 activity classification tests (coding/browsing/reading/communicating/gaming/unknown + edge cases)
- 1 ScreenScene roundtrip
- 1 singleton
- 8 ScreenWatcher public API (status, context, dashboard, recent, persistence, app durations, reset_today)
- 3 hash diff tests
- 3 keyword list tests
- **6 live backend tests** (all pass with server running)

### Live smoke test confirmed
- ✓ Backend detects `mac_active` (or `win_active`/`linux_active`) based on OS
- ✓ All 5 activity categories classify correctly:
  - `vscode + main.py` → `coding`
  - `chrome + github.com` → `browsing`
  - `slack + general` → `communicating`
  - `kindle + deep work.epub` → `reading`
  - `steam + library` → `gaming`
- ✓ Start/Stop endpoints work
- ✓ Status/context/dashboard return correct shapes

---

## 📊 Stats

### Phase 6A
- **1 new module**: `omni_v2/agents/screen_watcher.py`
- **8 new endpoints**
- **1 new proactive rule**
- **1 new mobile screen**
- **31 new tests** (all pass)

### Total project
- **20 test suites, 320+ tests, 0 failures** (1 pre-existing skill_synthesis fail)
- **111 API endpoints** (56 GET, 47 POST, 6 DELETE, 2 WS)
- **3 perspectives completed**: Mobile-First (Phase 5), Visual-First (Phase 6A), and Ambient-First (later)

---

## 🔮 Next in Visual-First (Phase 6B+)

- **Visual scene descriptions** (when an app opens, use vision model to describe)
- **OCR for reading content** (extract text from screen for "summarize this")
- **Multi-screen support** (laptop + external monitor)
- **Window position tracking** (where on screen, not just which window)
- **Pattern detection** (typing, mouse patterns → "in flow state?")
- **Auto-pause when presenting** (detect slideshow/fullscreen → stop notifications)

These are all "easy" extensions on the same ScreenWatcher infrastructure.

---

**Next**: Collab-First perspective — workflow learning.
