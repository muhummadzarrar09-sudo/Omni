# 🎬 OMNI V3 — Quick Demo (90 seconds)

Watch OMNI think, act, recover, remember, and have opinions.

## What you'll see

1. **Brain thinks live** — LLM tokens stream onto the screen
2. **Tools fire as cards** — you see exactly what it does
3. **Self-heals on failure** — tries alternatives visibly
4. **Remembers yesterday** — "Last time you worked on auth"
5. **Has opinions** — "You've opened Twitter 3 times today. Working or procrastinating?"
6. **Speaks first** — proactive banner appears when you need help

## 90-second scripted demo

```powershell
# Start the backend
omni start

# In another terminal, run the cinematic auto-demo
curl -X POST http://localhost:8765/api/demo -H "Content-Type: application/json" -d "{\"action\":\"start\"}"

# Or open the UI
# http://localhost:3000
```

The 8-scene demo runs for 1:46. Each scene broadcasts via WebSocket to the UI.

## Manual demo (3 commands)

```powershell
# 1. It thinks
curl -X POST http://localhost:8765/api/execute -H "Content-Type: application/json" -d "{\"command\":\"what can you do\"}"

# 2. It acts
curl -X POST http://localhost:8765/api/execute -H "Content-Type: application/json" -d "{\"command\":\"open github\"}"

# 3. It remembers
curl -X POST http://localhost:8765/api/execute -H "Content-Type: application/json" -d "{\"command\":\"what did I do yesterday\"}"
```

## What to look for

- **Live thought stream** — the LLM's actual reasoning, not a fake
- **Tool call cards** — appear as the LLM decides what to do
- **Brain state orb** — color changes: idle (gray) → listening (cyan) → reasoning (orange) → executing (purple) → speaking (green)
- **Proactive banner** — appears automatically based on context
- **Stats panel** — "847 commands, 5.2 hours saved"

See [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md) for the full video script.
