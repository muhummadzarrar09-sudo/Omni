# 🔌 OMNI V3 — API Reference

> The full HTTP API. Open http://localhost:8765/docs for the interactive Swagger UI.

**Base URL:** `http://localhost:8765`
**Content-Type:** `application/json`
**WebSocket:** `ws://localhost:8765/ws`

---

## Core Endpoints

### `GET /`
Health check / metadata.

**Response:**
```json
{
  "name": "OMNI V3 FastAPI",
  "version": "3.2.0",
  "description": "Pretty damn good backend for Next.js beautiful neomorphism UI",
  "endpoints": ["/api/health", "/api/devices", "/api/execute", "..."],
  "frontend": "Next.js at http://localhost:3000"
}
```

### `GET /api/health`
Detailed health check.

**Response:**
```json
{
  "status": "ok",
  "brain_ready": true,
  "proactive_active": true,
  "audio": "Realtek Audio (ch=2)",
  "stt": {"model": "base.en", "device": "cuda", "init_status": "loaded_cuda_int8"},
  "tts": {"engine": "edge-tts", "persona": "jarvis"},
  "fix": "sounddevice only, no PyAudio, no 404, no D:/Omni hardcode"
}
```

### `POST /api/execute`
**The main brain command.** Run a user utterance through the multi-agent system.

**Request:**
```json
{
  "command": "open github"
}
```

**Response:**
```json
{
  "success": true,
  "message": "✅ Opened in isolated profile OMNI-Profile: https://github.com (no email, privacy by design)",
  "logs": [
    "[Brain] tier=llm, tools=17",
    "[Brain] 1832ms | tools=1 | text=''",
    "[Executor] brain.browser_navigate -> success=True | Monitor: True | ✅ Opened in isolated profile..."
  ],
  "steps": 1,
  "mock": false,
  "brain": {
    "tier": "llm",
    "latency_ms": 1832.4,
    "thoughts": "",
    "tool_count": 1,
    "raw": "{\"tool\": \"browser_navigate\", \"args\": {\"url\": \"https://github.com\"}}"
  }
}
```

### `POST /api/execute/stream`
SSE streaming version. Returns Server-Sent Events as the LLM thinks.

**Request:** Same as `/api/execute`

**Response (event stream):**
```
event: thinking
data: {"token": "I", "tier": "llm"}

event: thinking
data: {"token": " should", "tier": "llm"}

...

event: tool_call
data: {"tool": "browser_navigate", "args": {"url": "https://github.com"}}

event: final
data: {"success": true, "message": "..."}
```

### `WebSocket /ws`
Live events for the UI: wake word, voice commands, brain thoughts, proactive suggestions.

**Client → Server:**
```json
{"type": "ping"}
```

**Server → Client:**
```json
{"type": "wake", "ts": 1234567890.123}
{"type": "voice_command", "text": "open github", "ts": 1234567890.456}
{"type": "voice_result", "result": {...}, "ts": 1234567890.789}
{"type": "demo_scene", "scene": 3, "title": "I can think", "narration": "..."}
{"type": "scheduled_task", "task": "morning brief", "command": "brief my day", "ts": 1234567891.0}
```

### `GET /api/devices`
List audio input devices.

### `POST /api/test-mic`
Test microphone RMS (sound level).

### `POST /api/ptt/start`
Start push-to-talk recording (PTT button in UI).

### `POST /api/ptt/stop`
Stop PTT, transcribe, execute as command.

---

## User Profile (Phase 1)

### `GET /api/user/profile`
Get the user's persistent profile.

**Response:**
```json
{
  "status": "ok",
  "profile": {
    "name": "Zarrar",
    "pronouns": "",
    "timezone": "Asia/Karachi",
    "work_start_hour": 9,
    "favorite_voice": "jarvis",
    "formality": "casual",
    "wake_word_sensitivity": 0.5,
    "proactive_frequency": "normal",
    "favorite_music": "lo-fi",
    "hobbies": ["coding", "music"],
    "total_commands": 247,
    "longest_session_min": 145,
    "peak_hours": [9, 10, 14, 15, 16],
    "most_used_tools": {"browser_navigate": 47, "vscode_open": 23},
    "created_at": 1752566400.0,
    "updated_at": 1752652800.0,
    "version": 2
  }
}
```

### `POST /api/user/profile`
Update profile fields.

**Request:**
```json
{
  "name": "Zarrar",
  "timezone": "Asia/Karachi",
  "favorite_voice": "friday",
  "hobbies": ["coding", "music", "gaming"]
}
```

### `DELETE /api/user/profile/{field}`
Forget (reset to default) a specific field.

**Example:** `DELETE /api/user/profile/birthday`

### `GET /api/user/greeting`
Get a personalized greeting.

**Response:**
```json
{
  "status": "ok",
  "greeting": "Good morning, Zarrar ☀️",
  "body": "It's Tuesday, July 15, 2026. Yesterday you worked on github.",
  "name": "Zarrar",
  "has_name": true,
  "has_history": true,
  "last_seen": "2026-07-14T18:23:45"
}
```

### `GET /api/user/stats`
Get behavioral statistics.

**Response:**
```json
{
  "status": "ok",
  "profile_stats": {
    "name": "Zarrar",
    "total_commands": 247,
    "avg_daily_commands": 35,
    "longest_session_min": 145,
    "peak_hours": [9, 10, 14, 15, 16],
    "top_tools": [["browser_navigate", 47], ["vscode_open", 23], ["files_write", 15]],
    "active_projects": ["Omni"],
    "member_since": 1752566400.0,
    "days_using_omni": 1
  },
  "session_stats": {
    "active_session_id": "sess_abc123",
    "active_session_commands": 12,
    "active_session_duration_min": 8.3
  },
  "weekly_summary": {
    "days_active": 5,
    "total_commands": 247,
    "total_minutes": 340.5,
    "top_topics": [["github", 47], ["auth", 23], ["music", 12]]
  }
}
```

---

## Memory (Phase 1)

### `GET /api/memory/sessions?days=7`
List recent sessions.

**Response:**
```json
{
  "status": "ok",
  "sessions": [
    {
      "id": "sess_abc123",
      "started_at": 1752649200.0,
      "ended_at": 1752651900.0,
      "duration_min": 45.0,
      "command_count": 23,
      "tool_calls": [{"tool": "browser_navigate", "args": "{}", "result": "success", "timestamp": 1752649300.0}],
      "commands": ["open github", "search for iron man", "play lo-fi"],
      "topics": ["github", "music", "code"],
      "summary": "Used OMNI for 23 commands across 1 sessions (45 min). Focused on: github, code, music.",
      "mood": "focused",
      "project": "Omni"
    }
  ],
  "count": 1
}
```

### `GET /api/memory/session/{session_id}`
Get specific session details.

### `GET /api/memory/search?q=github&days=30`
Search across all sessions by topic, command, or project.

**Response:**
```json
{
  "status": "ok",
  "query": "github",
  "matches": [/* session objects */],
  "count": 5
}
```

### `GET /api/memory/today`
Get today's digest.

### `GET /api/memory/yesterday`
Get yesterday's digest.

### `GET /api/memory/weekly`
Get 7-day summary.

---

## Personality (Phase 2)

### `GET /api/personality`
Get current personality settings.

**Response:**
```json
{
  "status": "ok",
  "personality": {
    "formality": 0.2,
    "warmth": 0.7,
    "wit": 0.6,
    "verbosity": 0.5,
    "mood": "helpful",
    "use_emoji": true,
    "use_dry_humor": true,
    "address_by_name": true,
    "version": 1
  }
}
```

### `POST /api/personality`
Update personality dimensions (clamped to 0-1).

**Request:**
```json
{
  "wit": 0.9,
  "formality": 0.1,
  "warmth": 0.8
}
```

### `POST /api/personality/mood`
Set the current mood.

**Request:**
```json
{"mood": "playful"}
```

Valid moods: `helpful`, `focused`, `playful`, `concerned`, `celebratory`.

### `POST /api/personality/test`
Generate sample phrases with current personality.

**Response:**
```json
{
  "status": "ok",
  "acknowledgment": "On it.",
  "success": "Done. That was fast. ✨",
  "empathy": "Hmm, that didn't work. Let me try again.",
  "observation": "You've opened Twitter 4 times today. Working or procrastinating?",
  "mood": "playful"
}
```

---

## Proactive Engine

### `GET /api/proactive/suggestions`
Get pending proactive suggestions (battery warnings, break reminders, etc.).

**Response:**
```json
{
  "status": "ok",
  "suggestions": [
    {
      "id": "morning_20260715",
      "title": "Good morning, Zarrar ☀️",
      "body": "It's Tuesday, July 15. Yesterday you worked on github.",
      "priority": 1,
      "category": "time",
      "actions": [
        {"label": "Brief me", "command": "brief my day"},
        {"label": "What did I do yesterday?", "command": "what did I do yesterday"},
        {"label": "Skip", "command": "_ack"}
      ]
    }
  ],
  "daily_count": 1
}
```

### `POST /api/proactive/action`
Mark a suggestion as dismissed or acted on.

**Request:**
```json
{
  "suggestion_id": "morning_20260715",
  "action": "dismiss"  // or "act"
}
```

### `POST /api/proactive/context`
Push context (calendar, inbox, code status) to the engine.

**Request:**
```json
{
  "calendar": {"next_event": {"title": "Standup", "start_timestamp": 1752656400.0}},
  "inbox": {"urgent_unread": 5},
  "code": {"last_test_status": "failed", "failed_count": 2},
  "system": {"battery_percent": 12, "plugged_in": false}
}
```

---

## Onboarding (Phase 3)

### `GET /api/onboarding`
Get current onboarding state.

**Response:**
```json
{
  "status": "ok",
  "onboarding": {
    "completed": false,
    "current_step": 2,
    "skipped": false,
    "name": "",
    "should_show": true,
    "current_step_data": {
      "id": 2,
      "title": "Let's test the mic",
      "body": "I want to make sure I can hear you. Say anything...",
      "expected_input": "hello",
      "duration_sec": 10
    }
  }
}
```

### `POST /api/onboarding/advance`
Advance to next step (optionally capture name).

**Request:**
```json
{"name": "Zarrar"}
```

### `POST /api/onboarding/skip`
Skip the entire onboarding flow.

### `POST /api/onboarding/reset`
Reset to step 1 (re-onboard).

---

## Demo Mode (Phase 3)

### `POST /api/demo`
Control the 8-scene cinematic demo.

**Request:**
```json
{
  "action": "start",  // or "stop", "pause", "resume", "skip_to"
  "scene_id": 3       // required for "skip_to"
}
```

**Response:**
```json
{
  "status": "ok",
  "action": "started",
  "script_size": 8
}
```

### `GET /api/demo/status`
Get current demo state.

**Response:**
```json
{
  "status": "ok",
  "demo": {
    "running": true,
    "paused": false,
    "current_scene_id": 3,
    "current_scene_title": "I can think",
    "elapsed_sec": 32.4,
    "total_scenes": 8
  }
}
```

### `GET /api/demo/script`
Get the full 8-scene script (titles, durations, actions).

---

## Stats (Phase 3)

### `GET /api/stats`
Full dashboard data.

**Response:**
```json
{
  "status": "ok",
  "stats": {
    "lifetime": {
      "total_commands": 247,
      "total_sessions": 12,
      "total_tool_calls": 189,
      "avg_commands_per_session": 20.6,
      "days_using_omni": 1
    },
    "today": {
      "date": "2026-07-15",
      "total_commands": 23,
      "total_duration_min": 45.0,
      "top_topics": [["github", 8], ["music", 3]],
      "mood": "focused"
    },
    "tool_breakdown": [
      {"tool": "browser_navigate", "count": 47},
      {"tool": "vscode_open", "count": 23}
    ],
    "peak_hours": {"9": 12, "10": 18, "11": 8, "14": 15, "15": 20, "16": 9},
    "weekly_chart": {"2026-07-15": {"sessions": 2, "commands": 47, "minutes": 120.0}},
    "time_saved": {
      "commands": 247,
      "seconds_saved": 7410,
      "minutes_saved": 123.5,
      "hours_saved": 2.1,
      "human_readable": "2h 3m"
    }
  }
}
```

### `GET /api/stats/today`
Just today's stats.

### `GET /api/stats/lifetime`
Just lifetime stats.

### `GET /api/stats/time-saved`
Just the time-saved estimate.

---

## Vision (Phase 4)

### `POST /api/vision`
Process a file (image/PDF) or capture the screen.

**Request (file):**
```json
{
  "file_path": "C:/path/to/image.png",
  "query": "What is in this image?"
}
```

**Request (screen capture):**
```json
{
  "capture_screen": true,
  "query": "What is on my screen right now?"
}
```

**Response:**
```json
{
  "status": "ok",
  "result": {
    "success": true,
    "file_type": "image",
    "description": "The image shows a GitHub repository page with...",
    "extracted_text": "Pull requests · Zarrar/Omni...",
    "objects_detected": [],
    "metadata": {"size": [1920, 1080], "mode": "RGB", "ocr_chars": 234},
    "duration_ms": 1234.5,
    "model_used": "tesseract+moondream2",
    "error": ""
  }
}
```

### `GET /api/vision/status`
Check vision dependencies.

---

## Voice Cloning (Phase 4)

### `POST /api/voice/clone/start`
Start recording audio for voice cloning.

### `POST /api/voice/clone/stop`
Stop recording and save to WAV.

**Response:**
```json
{
  "status": "ok",
  "sample_path": "D:/Omni/data/voice_clone/samples/sample_12345.wav"
}
```

### `POST /api/voice/clone/train`
Train a voice from a sample.

**Request:**
```json
{
  "sample_path": "D:/Omni/data/voice_clone/samples/sample_12345.wav",
  "voice_name": "my_voice"
}
```

### `GET /api/voice/clone/samples`
List recorded samples.

### `GET /api/voice/clone/voices`
List cloned voices.

### `GET /api/voice/clone/status`
Get current voice clone state.

---

## Skill Marketplace (Phase 4)

### `GET /api/skills/marketplace?category=developer&search=git`
Browse the marketplace.

**Response:**
```json
{
  "status": "ok",
  "items": [
    {
      "id": "github_pr_reviewer",
      "name": "GitHub PR Reviewer",
      "description": "Review open PRs in your repos and summarize changes",
      "author": "omni-community",
      "version": "1.0.0",
      "category": "developer",
      "tags": ["github", "pr", "review"],
      "rating": 4.8,
      "installs": 1247,
      "installed": false
    }
  ],
  "categories": ["developer", "media", "productivity"],
  "total": 1
}
```

### `POST /api/skills/install`
Install a skill.

**Request:**
```json
{"skill_id": "morning_briefing"}
```

### `POST /api/skills/uninstall`
Uninstall a skill.

### `GET /api/skills/installed`
List installed skills.

### `GET /api/skills/updates`
Check for skill updates.

---

## Voice

### `GET /api/voice/personas`
List available TTS personas.

**Response:**
```json
{
  "status": "ok",
  "personas": {
    "jarvis": "en-US-GuyNeural",
    "jarvis_british": "en-GB-RyanNeural",
    "friday": "en-US-JennyNeural",
    "aria": "en-US-AriaNeural",
    "davis": "en-US-DavisNeural",
    "sara": "en-US-SaraNeural"
  }
}
```

### `POST /api/voice/set`
Change voice persona.

**Request:**
```json
{"persona": "jarvis_british"}
```

---

## Scheduler

### `GET /api/scheduler/tasks`
List all scheduled tasks.

### `POST /api/scheduler/cron`
Add a cron-style task.

**Request:**
```json
{
  "name": "morning brief",
  "command": "brief my day",
  "cron": "0 8 * * 1-5"  // 8am weekdays
}
```

### `POST /api/scheduler/interval`
Add an interval task.

**Request:**
```json
{
  "name": "stretch break",
  "command": "remind me to stretch",
  "minutes": 30
}
```

### `POST /api/scheduler/once`
Add a one-shot task.

**Request:**
```json
{
  "name": "meeting prep",
  "command": "prep notes for the standup",
  "run_at": "2026-07-15T15:00:00"
}
```

### `POST /api/scheduler/remove`
Remove a task.

**Request:**
```json
{"task_id": "cron_1234567890"}
```

---

## Plugin SDK (Phase 4)

### `GET /api/sdk`
Get SDK info.

**Response:**
```json
{
  "status": "ok",
  "sdk": {
    "name": "OMNI V3 Plugin SDK",
    "version": "1.0.0",
    "import": "from omni_v2.sdk import skill, command, ok, fail, reply",
    "example_code_path": "omni_v2/sdk/__init__.py",
    "skills_dir": "data/skills/installed/",
    "marketplace_count": 8
  }
}
```

---

## Error Responses

All endpoints return standard HTTP status codes:

- `200` — Success
- `400` — Bad request (empty command, invalid input)
- `404` — Not found
- `413` — Payload too large (>64KB)
- `429` — Rate limit exceeded
- `500` — Internal error

**Error body:**
```json
{
  "status": "error",
  "error": "Description of what went wrong",
  "logs": ["[Error] ..."],
  "steps": 0
}
```

---

## Rate Limiting

- **60 requests per minute** per client
- Resets every 60 seconds
- Returns HTTP 429 if exceeded
- Body: `{"status": "error", "error": "Rate limit: 60/60 per minute for 'global'"}`

---

## Authentication

**None required for local use.** This is a local-first tool. The FastAPI
server binds to `0.0.0.0:8765` by default — change to `127.0.0.1:8765` in
`main.py` to restrict to localhost.

For remote access, run behind a reverse proxy (nginx, Caddy) with auth.

---

## CORS

CORS is configured to allow all origins (`allow_origins=["*"]`) for
hackathon/demo use. For production, restrict to your UI domain.

---

## See Also

- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture
- **[docs/CHANGELOG.md](CHANGELOG.md)** — Version history
- **[docs/AIM.md](AIM.md)** — The AIM
- **[docs/PERFORMANCE.md](PERFORMANCE.md)** — Benchmarks
