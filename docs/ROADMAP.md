# 🚀 OMNI V3 — The JARVIS + AGI Flex Roadmap (FULL SPEC)

> **The AIM:** *"Make a user say 'holy sh*t it's actually an AGI' within 2 minutes."*
> **The Vibe:** JARVIS (the butler that knows you) + AGI showcase (you SEE it think)
> **The Goal:** 10/10 AIM features. Each one makes OMNI noticeably more "AGI."

---

## 📋 Master AIM Checklist

| # | Feature | What it does | Status |
|---|---|---|---|
| 1 | 🗣️ **Wake word "Hey OMNI"** | Always-listening, sub-100ms, real backend | ✅ Done |
| 2 | 👋 **Greets you by name** | "Good morning Zarrar, here's your day" | ⏳ TODO |
| 3 | 🧠 **Shows its thinking** | Live thought stream on screen | ✅ Done |
| 4 | 🛠️ **Shows its tools** | Cards appear as it acts | ✅ Done |
| 5 | 🔁 **Shows its recovery** | Self-healing drama on failure | ✅ Done |
| 6 | 💡 **Speaks first** | Proactive nudges (battery, meetings, breaks) | ⏳ TODO |
| 7 | 🎭 **Has a voice** | Natural edge-tts, 6 personas | ✅ Done |
| 8 | 🧠 **Remembers across sessions** | "Yesterday you were debugging X..." | ⏳ TODO |
| 9 | 😏 **Has opinions** | "Twitter again? Working or procrastinating?" | ⏳ TODO |
| 10 | ⚡ **Cinematic & fast** | Orb animations, live states, sub-second | ✅ Done |

**Current: 5/10 done. 5 to go.**

---

# PHASE 1: The "It Remembers You" Layer
## AIM #2 (Greets by name) + AIM #8 (Remembers across sessions)

**The why:** A butler that doesn't know your name is just a tool. Once OMNI knows you, every interaction becomes "I remember you" instead of "Who are you?"

**Effort: 6-8 hours of focused work**

---

### 1A. User Profile Store

**File:** `omni_v2/agents/user_profile.py` (NEW, ~250 lines)

**Storage:** `data/user_profile.json` (portable, human-readable, git-friendly)

**Data model:**
```python
@dataclass
class UserProfile:
    # Identity
    name: str = ""                          # "Zarrar"
    pronouns: str = ""                      # "he/him" or "they/them"
    timezone: str = "UTC"                   # "Asia/Karachi"
    
    # Schedule
    work_start_hour: int = 9                # 9am
    work_end_hour: int = 17                  # 5pm
    work_days: List[int] = [0,1,2,3,4]      # Mon-Fri (0=Monday)
    lunch_hour: int = 13                     # 1pm
    
    # Preferences
    favorite_voice: str = "jarvis"          # persona name
    formality: str = "casual"               # "casual" | "formal" | "sarcastic"
    theme: str = "dark"                     # "dark" | "light" | "neon"
    wake_word_sensitivity: float = 0.5      # 0.0-1.0
    proactive_frequency: str = "normal"     # "low" | "normal" | "high"
    
    # Personal
    hobbies: List[str] = []                  # ["coding", "gaming", "music"]
    favorite_music: str = "lo-fi"            # default music style
    pet_names: Dict[str, str] = {}           # {"cat": "Whiskers"}
    family: Dict[str, str] = {}              # {"sister": "Aisha"}
    location: str = ""                       # "Rawalpindi, Pakistan"
    birthday: str = ""                       # "March 31"
    
    # Projects
    current_projects: List[Dict] = []        # [{"name":"Omni","status":"active"}]
    active_apps: List[str] = []              # ["VS Code", "Chrome", "Spotify"]
    
    # Behavioral patterns (learned)
    avg_daily_commands: int = 0              # rolling 7-day average
    most_used_tools: Dict[str, int] = {}     # {"browser_navigate": 47, ...}
    peak_hours: List[int] = []               # [9, 10, 14, 15, 16]
    longest_session_min: int = 0             # longest focused session
    
    # Meta
    created_at: float = 0.0
    updated_at: float = 0.0
    version: int = 1                         # schema version
```

**API surface:**
```python
# Get
profile = get_profile()                     # full profile
name = profile.get("name")                  # shortcut for any field
defaults = profile.get_defaults()           # safe defaults for missing fields

# Set
profile.set("name", "Zarrar")
profile.set("pronouns", "he/him")
profile.set_many(name="Zarrar", timezone="Asia/Karachi", work_start_hour=9)

# Forget (remove a field, revert to default)
profile.forget("birthday")

# Learn (behavioral patterns)
profile.record_command("browser_navigate")
profile.record_tool_usage("vscode_open")
profile.record_session_duration(45)         # 45 minutes focused

# Serialization
profile.save()                              # to JSON
profile.reload()                            # from JSON
```

**FastAPI endpoints (in `backend_fastapi/main.py`):**
```
GET  /api/user/profile              → full profile JSON
POST /api/user/profile              → update fields, body: {"name": "Zarrar", ...}
DELETE /api/user/profile/{field}    → forget a field
POST /api/user/learn                → record behavioral event, body: {"type": "command", "tool": "browser_navigate"}
GET  /api/user/greeting             → context-aware greeting string (e.g. "Good morning Zarrar")
GET  /api/user/stats                → behavioral stats
```

**UI components (in `frontend_next/app/page.js`):**
- Settings panel with profile fields
- "Edit profile" button → opens modal
- Greeting shows in header on first load of the day
- Stats card shows: "OMNI has learned: 47 commands, peak at 10am, favorite: VS Code"

**Tests:** `omni_v2/tests/test_user_profile.py` (NEW)
```python
# 15+ tests covering:
- get/set/forget round-trip
- serialization to/from JSON
- defaults for missing fields
- behavioral learning (commands, tools, sessions)
- concurrent access (thread-safety)
- corrupted JSON recovery
- schema migration (v1 → v2)
```

**Acceptance criteria:**
- [ ] Profile persists across backend restarts
- [ ] OMNI greets "Good morning Zarrar" after first name set
- [ ] Stats update after each command
- [ ] Forgetting a field reverts to default
- [ ] No data loss on concurrent updates (file lock or atomic write)

---

### 1B. Session Memory

**File:** `omni_v2/memory/session_memory.py` (NEW, ~350 lines)

**Storage:** `data/memory/sessions/` (one JSON per session, indexed by date)

**Data model:**
```python
@dataclass
class SessionEntry:
    id: str                                  # uuid
    started_at: float                        # unix timestamp
    ended_at: Optional[float]                # None if active
    duration_min: float                      # computed when ended
    command_count: int = 0
    tool_calls: List[Dict] = []              # [{"tool":"browser_navigate","args":{...},"result":...}]
    topics: List[str] = []                   # extracted topics: ["github", "auth tests"]
    summary: str = ""                        # auto-generated summary
    mood: str = "neutral"                    # "focused" | "exploratory" | "frustrated" | "neutral"
    project: str = ""                        # detected project name
    
@dataclass
class DailyDigest:
    date: str                                # "2026-07-15"
    sessions: List[str]                      # session IDs
    total_commands: int
    top_topics: List[Tuple[str, int]]       # [("github", 5), ("auth", 3)]
    summary: str                            # "You worked on Omni, debugged auth tests, had 2 meetings"
    accomplishments: List[str]              # ["Fixed auth tests", "Opened 5 PRs"]
    unfinished: List[str]                   # ["Still need to commit .env fix"]
```

**API surface:**
```python
# Session management
session = start_session()                   # creates new session, returns ID
session.record_command("open github", result="OK")
session.record_tool_call("browser_navigate", {"url":"github.com"}, "success")
session.end()                               # marks session complete, generates summary

# Recall
recent = recall_sessions(days=7)            # List[SessionEntry]
matches = search_history("auth", days=30)   # List[SessionEntry] matching topic
today = get_today_digest()                  # DailyDigest
yesterday = get_digest(date_offset=-1)
weekly = get_weekly_summary()

# Auto-summarization (uses LLM brain)
summary = await session.generate_summary(brain)  # uses Qwen 1.5B
```

**FastAPI endpoints:**
```
GET  /api/memory/sessions?days=7           → list of recent sessions
GET  /api/memory/session/{id}              → specific session details
GET  /api/memory/search?q=auth&days=30     → search across history
GET  /api/memory/today                     → today's digest
GET  /api/memory/yesterday                 → yesterday's digest
GET  /api/memory/weekly                    → weekly summary
POST /api/memory/summarize/{session_id}    → force regenerate summary
```

**UI components:**
- New "Memory" tab in left drawer (alongside History)
- Shows recent sessions as cards
- Each card: date, duration, command count, top topics, summary
- Click a session → see full transcript
- Search bar at top: "What did I do last Tuesday?"
- "Today" / "Yesterday" / "This Week" tabs

**Tests:** `omni_v2/tests/test_session_memory.py` (NEW)
```python
# 20+ tests covering:
- Session start/end lifecycle
- Recording commands and tool calls
- Auto-summarization (mocked brain)
- Search by topic
- Daily digest generation
- Cross-session recall
- Cleanup of old sessions (>90 days)
- Concurrent session recording
- Recovery from corrupted session files
```

**Acceptance criteria:**
- [ ] Each command creates a session entry
- [ ] Session auto-saves every 30 seconds
- [ ] Search returns relevant results in <100ms
- [ ] Daily digest auto-generated at midnight
- [ ] "Yesterday" works even if there were 50 sessions
- [ ] Memory survives backend restart

---

### 1C. Greeting System

**File:** integrated into `omni_v2/agents/proactive_v2.py` (modify existing)

**Logic:**
```python
def generate_greeting() -> Optional[ProactiveSuggestion]:
    """Generate a personalized greeting based on time + history."""
    now = datetime.now()
    hour = now.hour
    profile = get_profile()
    name = profile.get("name", "")
    name_part = f" {name}" if name else ""
    
    # First load of the day
    if not is_greeted_today():
        if 5 <= hour < 12:
            title = f"Good morning{name_part} ☀️"
            body = await generate_morning_brief()
        elif 12 <= hour < 17:
            title = f"Good afternoon{name_part}"
            body = await generate_afternoon_checkin()
        elif 17 <= hour < 22:
            title = f"Good evening{name_part}"
            body = await generate_evening_wrapup()
        else:
            return None  # don't greet late night
        
        mark_greeted_today()
        return ProactiveSuggestion(
            id=f"greeting_{now.date()}",
            title=title,
            body=body,
            priority=1,
            category="time",
            actions=[
                {"label": "Brief me", "command": "brief my day"},
                {"label": "Skip", "command": "_ack"},
            ],
        )
    
    # Returning after 1+ days
    last_seen = get_last_seen()
    if last_seen and (now - last_seen).days >= 1:
        digest = get_digest(date=last_seen.date())
        title = f"Welcome back{name_part}!"
        body = f"Last time you were working on {digest.topics[0]}. {digest.summary[:200]}"
        return ProactiveSuggestion(
            id=f"welcome_back_{now.date()}",
            title=title,
            body=body,
            priority=1,
            category="time",
            actions=[
                {"label": "Catch me up", "command": "what did I miss"},
                {"label": "Continue", "command": f"continue {digest.topics[0]}"},
                {"label": "Skip", "command": "_ack"},
            ],
        )
    
    return None

async def generate_morning_brief() -> str:
    """Build a personalized morning brief from calendar + emails + yesterday."""
    parts = []
    
    # Calendar
    events = get_todays_events()
    if events:
        next_event = events[0]
        parts.append(f"You have {len(events)} things today. {next_event.title} at {next_event.start_time}.")
    
    # Inbox
    urgent = get_urgent_emails()
    if urgent:
        parts.append(f"{len(urgent)} urgent emails.")
    
    # Yesterday
    yesterday = get_digest(date_offset=-1)
    if yesterday.unfinished:
        parts.append(f"Yesterday you didn't finish: {yesterday.unfinished[0]}")
    
    # Weather (if location set)
    if profile.get("location"):
        weather = get_weather(profile.get("location"))
        if weather:
            parts.append(f"It's {weather.temp}° and {weather.condition} outside.")
    
    if not parts:
        return "Ready when you are."
    
    return " ".join(parts)
```

**Tests:** Add to `omni_v2/tests/test_proactive_v2.py`
```python
# 8+ tests:
- Morning greeting (8-10am) with name
- Afternoon greeting (12-5pm)
- Evening greeting (5-10pm)
- No greeting at 3am
- Welcome back after 1+ day absence
- "What did I miss" command returns yesterday digest
- "Continue X" picks up yesterday's topic
- Greeting suppressed after dismissal
```

**Acceptance criteria:**
- [ ] First load of the day shows greeting
- [ ] Greeting uses user's name
- [ ] Greeting includes today's calendar
- [ ] Greeting includes yesterday's unfinished work
- [ ] Welcome back message after absence
- [ ] "Skip" dismisses for the rest of the day
- [ ] Returns to active listening after dismissal

---

### 1D. Wire-up & Integration

**File modifications:**

**`backend_fastapi/main.py`:**
- Add startup hook: `init_user_profile()`, `init_session_memory()`
- Wire every `/api/execute` call to `session.record_command()`
- Add new endpoints from 1A, 1B, 1C
- Add `/api/user/greeting` endpoint

**`backend_fastapi/core/brain.py`:**
- Pass user profile to brain for context-aware responses
- Add `personality` field to BrainResponse

**`frontend_next/app/page.js`:**
- Add `ProfilePanel` component (settings tab)
- Add `MemoryPanel` component (memory tab in drawer)
- Add greeting banner on first load
- Add "Welcome back" banner
- Show stats card: "47 commands today · peak 10am · favorite: VS Code"

**`omni_v2/core/safe_execute.py`:**
- No changes needed

**New tests:** All in `omni_v2/tests/`

**Total new files:**
- `omni_v2/agents/user_profile.py` (~250 lines)
- `omni_v2/memory/session_memory.py` (~350 lines)
- `omni_v2/tests/test_user_profile.py` (~150 lines)
- `omni_v2/tests/test_session_memory.py` (~200 lines)
- `docs/PHASE_1_DONE.md` (summary)

**Total modifications:**
- `backend_fastapi/main.py` (+200 lines)
- `frontend_next/app/page.js` (+400 lines)
- `omni_v2/agents/proactive_v2.py` (+100 lines for greeting)

**Total Phase 1 effort: ~1650 lines of new code + tests**

---

# PHASE 2: The "It Has Opinions" Layer
## AIM #9 (Has opinions) + polish AIM #2, #8

**The why:** OMNI knowing your name is one thing. OMNI having a TAKE on your habits is what makes it feel like a butler with personality, not a search engine.

**Effort: 8-10 hours of focused work**

---

### 2A. Personality Engine

**File:** `omni_v2/agents/personality.py` (NEW, ~400 lines)

**Data model:**
```python
@dataclass
class Personality:
    # Tone
    formality: str = "casual"               # "casual" | "professional" | "sarcastic"
    warmth: float = 0.7                      # 0.0 = cold, 1.0 = warm
    wit: float = 0.6                         # 0.0 = serious, 1.0 = dry wit
    verbosity: float = 0.5                   # 0.0 = terse, 1.0 = elaborate
    
    # Catchphrases (rotating, not annoying)
    acknowledgments: List[str] = field(default_factory=lambda: [
        "On it.", "Got it.", "Doing it now.", "Say no more.",
        "Right away.", "Consider it done.", "Yep."
    ])
    successes: List[str] = field(default_factory=lambda: [
        "Done. That was fast.", "Finished. You're welcome.",
        "Done in {ms}ms. Not bad.", "All set.", "✨ Done.",
        "Took care of it."
    ])
    failures_empathetic: List[str] = field(default_factory=lambda: [
        "Hmm, that didn't work. Let me try again.",
        "That failed. Trying a different approach.",
        "Okay that's weird. Let me investigate.",
        "Not quite. One moment."
    ])
    
    # Observation templates (the opinions)
    activity_nudge: List[str] = field(default_factory=lambda: [
        "You've opened {app} {count} times today. Working or procrastinating?",
        "You've been on {app} for {minutes} min. Want focus mode?",
        "That's the {count}th time you've checked {app}. Everything OK?",
    ])
    pattern_recognition: List[str] = field(default_factory=lambda: [
        "You usually {action} around this time. Want me to {proactive_action}?",
        "Last 3 days you've asked about {topic} first thing. Should I just brief you automatically?",
        "I notice you always have {app} open. Want me to learn that workflow?",
    ])
    suggestions: List[str] = field(default_factory=lambda: [
        "Pro tip: I can do {capability} if you ever need it.",
        "FYI: I learned a new trick — {trick}. Want to try?",
        "I'd suggest {option_a}, but {option_b} if you're feeling {mood}.",
    ])
```

**API surface:**
```python
# Get/set
personality = get_personality()
personality.set("wit", 0.8)                 # increase wit
personality.add_acknowledgment("Bet.")     # add custom phrase

# Use
ack = personality.pick_acknowledgment()     # "On it."
success = personality.format_success(ms=120)  # "Done in 120ms."
observation = personality.observe_activity(app="Twitter", count=4)  # "You've opened Twitter 4 times today..."

# Apply tone to a sentence (using LLM)
toned = await personality.apply_tone("Task completed successfully", brain)
# casual: "Done!"
# formal: "The task has been completed successfully."
# sarcastic: "Oh look, it actually worked. You're welcome."
```

**Tests:** `omni_v2/tests/test_personality.py` (~150 lines)
```python
# 12+ tests:
- Pick acknowledgment varies (not always same)
- Format success includes latency
- Observation templates fill placeholders correctly
- Tone application produces different outputs
- Custom phrases can be added/removed
- Wit doesn't cross into rude territory (max 0.95)
```

---

### 2B. Opinion Generator

**File:** `omni_v2/agents/opinion.py` (NEW, ~300 lines)

**Triggers (when to have an opinion):**
- User opened same app 3+ times in 30 min
- User spent >2hrs without break
- User asked about same topic 3+ times today
- User's disk is filling up
- User has unfinished tasks from yesterday
- It's Friday afternoon
- User just finished a hard task (celebrate)
- User failed at something twice (encourage)

**Logic:**
```python
class OpinionEngine:
    def __init__(self, profile, personality, session, brain):
        self.profile = profile
        self.personality = personality
        self.session = session
        self.brain = brain
    
    def maybe_opine(self, action: str, result: dict) -> Optional[str]:
        """Called after every action. Returns an opinion or None."""
        # Don't opine on every action - max 1 per 10 actions
        if self.opinions_this_hour >= 3:
            return None
        if random.random() > self.personality.wit:
            return None  # not every time, even with high wit
        
        opinion = None
        
        # Activity pattern
        if self._is_repeating_action(action):
            opinion = self.personality.observe_activity(
                app=self._extract_app(action),
                count=self._action_count(action, window_min=30)
            )
        
        # Time-based
        elif self._is_friday_evening():
            opinion = "It's Friday and you've been crushing it. Want me to wrap up your week?"
        
        # Failure encouragement
        elif not result.get("success"):
            opinion = self.personality.pick_failure_empathy()
        
        # Celebration
        elif action == "code_commit" and result.get("success"):
            opinion = random.choice([
                "Another one. Ship it.",
                "That's {count} commits today. You good.",
                "Look at you, being productive.",
            ])
        
        if opinion:
            self.opinions_this_hour += 1
            return opinion
        return None
```

**Wire into brain responses:** in `backend_fastapi/core/brain.py`:
```python
# After tool execution
opinion = opinion_engine.maybe_opine(action, result)
if opinion:
    brain_response.text += f"\n\n{opinion}"  # appended to response
```

**Tests:** `omni_v2/tests/test_opinion.py` (~150 lines)
```python
# 10+ tests:
- Max 1 opinion per response
- Max 3 opinions per hour
- Wit level affects opinion frequency
- Activity pattern triggers correct opinion
- Friday evening triggers wrap-up opinion
- Commit triggers celebration
- Failure triggers empathy
- Opinion respects formality setting
```

---

### 2C. Mood System

**File:** integrated into `personality.py`

**5 moods:**
- **helpful** (default) — "Done.", "Got it."
- **focused** (when user is in flow) — quieter, fewer opinions
- **playful** (after success) — more wit
- **concerned** (after repeated failure) — more empathy, fewer jokes
- **celebratory** (after big win) — "🎉", caps, emojis

**API:**
```python
personality.set_mood("playful")             # triggered after 3+ successes
personality.set_mood("concerned")           # triggered after 2+ failures
personality.get_mood_tone()                 # returns tone modifier for LLM
```

---

### 2D. Wire-up & Integration

**File modifications:**

**`backend_fastapi/core/brain.py`:**
- After every action, call `opinion_engine.maybe_opine()`
- Append opinion to brain_response.text
- Log opinions for review

**`backend_fastapi/main.py`:**
- Add `/api/personality` endpoints (get/set)
- Inject personality into brain

**`frontend_next/app/page.js`:**
- Show opinions as styled "aside" text after brain responses
- Mood indicator in header (small emoji or color)
- Settings panel: formality slider, wit slider, warmth slider

**New files:**
- `omni_v2/agents/personality.py` (~400 lines)
- `omni_v2/agents/opinion.py` (~300 lines)
- `omni_v2/tests/test_personality.py` (~150 lines)
- `omni_v2/tests/test_opinion.py` (~150 lines)
- `docs/PHASE_2_DONE.md` (summary)

**Total Phase 2 effort: ~1000 lines of new code + tests**

---

# PHASE 3: The "Demo Polish" Layer
## AIM polish (all 10 features, 2-min demo, anyone-gets-it-in-30-sec)

**The why:** All the smarts in the world don't matter if people don't get it. Phase 3 makes sure the first 2 minutes of using OMNI feel like magic, every time.

**Effort: 10-12 hours of focused work**

---

### 3A. Onboarding Experience

**File:** `omni_v2/agents/onboarding.py` (NEW, ~300 lines)

**First-time flow:**
```
[Step 1: Welcome]
  "Hi, I'm OMNI. I'm a local AGI — all private, all yours.
   Want a quick tour? (30 seconds)"

  [Take tour]  [Skip]

[Step 2: Mic test]
  "Let me make sure I can hear you.
   Say 'Hey OMNI, hello!'"
  
  [Live: I'm hearing you]  [Try again]  [Skip]

[Step 3: Name]
  "What should I call you?"
  
  [Text input]  [Submit]

[Step 4: First command]
  "Try this: say 'open github'"
  [Live execution]
  "Nice. I'm pretty fast, right?"

[Step 5: Wake word]
  "I can also be always-listening. Say 'Hey OMNI' from anywhere.
   Want me to start listening?"
  
  [Yes, start listening]  [No, I'll use the button]
```

**State:** `data/onboarding_state.json` with `{completed: bool, current_step: int, skipped: bool}`

**API:**
```python
state = get_onboarding_state()
state.mark_step(3)
state.complete()
state.skip()
state.should_show()  # bool, only true on first run
```

**UI components:**
- Full-screen overlay on first launch
- Step indicator (1/5, 2/5, etc.)
- Animated orb in center
- Skip button always available
- "Replay tour" option in settings

**Tests:** `omni_v2/tests/test_onboarding.py` (~100 lines)
```python
# 8+ tests:
- First launch shows onboarding
- Second launch skips
- Each step advances correctly
- Skip works from any step
- Replay from settings works
- State persists across restarts
```

---

### 3B. Demo Mode

**File:** `omni_v2/agents/demo_mode.py` (NEW, ~400 lines)

**The 8-scene demo (auto-advances on user input or timer):**

```python
DEMO_SCRIPT = [
    {
        "scene": 1,
        "title": "Welcome to OMNI",
        "narration": "I'm OMNI V3 — a local, private AGI. I run entirely on this laptop. No cloud, no spying.",
        "action": "say",
        "duration_sec": 8,
    },
    {
        "scene": 2,
        "title": "I can hear you",
        "narration": "Say something — anything.",
        "action": "wait_for_speech",
        "expected": ["hello", "hi", "hey", "test", "yo"],
        "duration_sec": 10,
    },
    {
        "scene": 3,
        "title": "I can think",
        "user_command": "what's on my plate today?",
        "narration": "Watch my thoughts as I figure that out.",
        "action": "execute",
        "shows": ["thought_stream", "tool_cards", "calendar", "inbox"],
        "duration_sec": 15,
    },
    {
        "scene": 4,
        "title": "I can take action",
        "user_command": "open github",
        "narration": "And then I just... do it.",
        "action": "execute",
        "shows": ["browser_open", "profile_isolated"],
        "duration_sec": 8,
    },
    {
        "scene": 5,
        "title": "I can recover",
        "narration": "Sometimes things fail. Watch me try again.",
        "action": "simulate_failure",
        "command": "open this doesn't exist.exe",
        "shows": ["failure", "self_healing", "fallback"],
        "duration_sec": 12,
    },
    {
        "scene": 6,
        "title": "I can remember",
        "user_command": "what did I do yesterday?",
        "narration": "I keep track of everything.",
        "action": "execute",
        "shows": ["memory_panel", "yesterday_digest"],
        "duration_sec": 10,
    },
    {
        "scene": 7,
        "title": "I can speak first",
        "narration": "And sometimes I tell YOU what to do.",
        "action": "trigger_proactive",
        "shows": ["battery_warning", "disk_full", "morning_brief"],
        "duration_sec": 8,
    },
    {
        "scene": 8,
        "title": "I'm yours",
        "narration": "All local. All private. All yours. Welcome to your AGI.",
        "action": "end",
        "duration_sec": 5,
    },
]
```

**API:**
```python
demo = get_demo_mode()
demo.start()                                 # begin 2-min demo
demo.skip_to(scene_id)                       # jump to scene 5
demo.pause()
demo.resume()
demo.stop()
```

**UI components:**
- "Start 2-min demo" button in settings
- Full-screen takeover during demo
- Scene counter ("Scene 3 of 8")
- Skip / pause controls
- Cinematic transitions between scenes

**Tests:** `omni_v2/tests/test_demo_mode.py` (~150 lines)
```python
# 10+ tests:
- All 8 scenes defined
- Each scene has valid action
- Timing is correct
- Skip works
- Pause/resume works
- Demo completes in ~2 min
- Demo can be restarted
```

---

### 3C. Stats & Telemetry Panel

**File:** `omni_v2/agents/stats.py` (NEW, ~200 lines)

**Metrics tracked:**
- Total commands (lifetime)
- Commands today
- Commands this week
- Tokens generated (lifetime)
- Tools called (by tool, with count)
- Success rate (% successful)
- Avg response time (ms)
- Peak hour
- Most active day
- Longest session
- Memory size (MB)
- Time saved (estimate: 5 min per command)

**API:**
```python
stats = get_stats()
stats.dict()                                 # full stats
stats.todays_summary()                       # "47 commands today, peak at 10am"
stats.week_chart()                           # data for bar chart
```

**UI components:**
- New "Stats" tab
- Big number: "OMNI V3 — 2,847 commands this week"
- Bar chart: commands by hour
- Pie chart: tool usage breakdown
- Fun stats: "Time saved: ~3.5 hours this week"

**Tests:** `omni_v2/tests/test_stats.py` (~100 lines)

---

### 3D. Settings Page (Polished)

**File:** integrated into `frontend_next/app/page.js` (rebuild existing settings modal)

**Sections:**
- 👤 **Profile** — name, pronouns, timezone
- 🎭 **Personality** — formality, wit, warmth sliders
- 🔊 **Voice** — persona dropdown (jarvis, friday, aria, etc.)
- 🎤 **Wake word** — sensitivity slider, on/off toggle
- 💡 **Proactive** — frequency (low/normal/high), what to suggest
- 🧠 **Memory** — what's remembered, "forget everything", export
- 🎨 **Theme** — dark/light/neon
- 📊 **Stats** — see all metrics
- 🔒 **Privacy** — what's stored locally, what's not

**Tests:** UI only (manual)

---

### 3E. Wire-up & Integration

**New files:**
- `omni_v2/agents/onboarding.py` (~300 lines)
- `omni_v2/agents/demo_mode.py` (~400 lines)
- `omni_v2/agents/stats.py` (~200 lines)
- `omni_v2/tests/test_onboarding.py` (~100 lines)
- `omni_v2/tests/test_demo_mode.py` (~150 lines)
- `omni_v2/tests/test_stats.py` (~100 lines)
- `docs/PHASE_3_DONE.md` (summary)

**Modified files:**
- `frontend_next/app/page.js` (+600 lines for settings)
- `backend_fastapi/main.py` (+200 lines for new endpoints)

**Total Phase 3 effort: ~2050 lines of new code + tests**

---

# PHASE 4: The "Product Grade" Layer
## AIM quality (wake training, voice clone, marketplace, multi-modal)

**The why:** This is the "go from impressive demo to daily-use product" phase. Each feature is optional but each one adds depth.

**Effort: 30+ hours. Pick and choose.**

---

### 4A. Custom Wake Word Training
**File:** `omni_v2/voice/wake_train.py` (~200 lines)
- Record user saying "Hey OMNI" 5x
- Train personalized openWakeWord model
- Save to `data/wake_models/user/`
- Auto-load on startup if exists
- 95% accuracy, 0% false positives

### 4B. Voice Cloning
**File:** `omni_v2/voice/voice_clone.py` (~300 lines)
- Use piper-tts or coqui-tts
- 30-second voice sample → custom voice model
- OMNI speaks in YOUR voice
- Privacy: all local, no upload

### 4C. Skill Marketplace
**File:** `omni_v2/skills/marketplace.py` (~400 lines)
- Registry of community skills
- One-click install (`omni install skill github-pr-reviewer`)
- Auto-update mechanism
- 10 starter skills bundled
- Sandboxed execution (skills can't break the brain)

### 4D. Multi-modal Vision
**File:** `omni_v2/vision/multimodal.py` (~500 lines)
- Drag screenshot into OMNI → explains
- Drag PDF → summarizes
- Drag image → describes
- "What's on my screen right now?"
- Uses Moondream2 / LLaVA locally

### 4E. Cloud Sync (E2E encrypted)
**File:** `omni_v2/sync/e2e.py` (~400 lines)
- Sync memory between your devices
- E2E encrypted (XChaCha20-Poly1305)
- Conflict resolution
- "Continue on phone" → pick up on desktop

### 4F. Mobile Companion
**File:** `omni_v2/mobile/` (NEW package, ~600 lines)
- React Native app
- Connects to OMNI on your laptop
- Voice input from phone
- Push notifications
- "Hey OMNI" on the go

### 4G. Plugin SDK
**File:** `omni_v2/sdk/` (NEW package, ~300 lines)
- Build your own skills in 50 lines
- Hot-reload
- Auto-generate from OpenAPI spec
- Publish to marketplace

**Total Phase 4 effort: 2700+ lines. Many days.**

---

# 📊 Effort & Progress Summary

| Phase | What | New LOC | Test LOC | Total LOC | Time | AIM impact |
|---|---|---|---|---|---|---|
| **1: Remembers You** | Profile + memory + greeting | 700 | 550 | 1250 | 6-8h | +2 (8/10) |
| **2: Has Opinions** | Personality + mood + wit | 700 | 300 | 1000 | 8-10h | +1 (9/10) |
| **3: Demo Polish** | Onboarding + demo + stats + settings | 900 | 350 | 1250 | 10-12h | polish (10/10) |
| **4: Product Grade** | Wake train + voice clone + more | 2700+ | 500+ | 3200+ | 30h+ | real product |

**Total: ~6700 new lines of code + tests for a real AGI butler.**

---

# 🎯 The Strategy

**Build in order:**
1. **Phase 1** (4-6h) → 8/10 AIM, OMNI knows you
2. **Phase 2** (6-8h) → 9/10 AIM, OMNI feels alive
3. **Phase 3** (8-10h) → 10/10 AIM, anyone gets the magic in 2 min
4. **Phase 4** (later) → real product, daily use

**Each phase:**
- Standalone (can be done in one sitting)
- Has clear acceptance criteria
- Has its own tests
- Updates the AIM checklist
- Creates a "DONE" doc

---

# 🚀 The First Action

When you're ready to start **Phase 1**:
1. Read `docs/AIM.md` (the high-level aim)
2. Read this file (`docs/ROADMAP.md`) for the full spec
3. Create `omni_v2/agents/user_profile.py` (start with 1A)
4. Run `python -m omni_v2.tests.test_user_profile.py` after each change
5. When 1A is done, do 1B, then 1C
6. Update the AIM checklist when done
7. Move to Phase 2

**Each phase = 1 git commit with a `[PHASE X DONE]` message.**

---

**The AIM is clear. The roadmap is clear. Let's build it.** 🚀
