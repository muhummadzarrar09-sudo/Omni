# 🎯 OMNI V3 — THE AIM

> *"A local, private, cinematic butler that thinks. Not a chatbot. Not a wrapper. A JARVIS that actually does stuff."*

## The One-Line AIM

**Make a user say "holy sh*t it's actually an AGI" within 2 minutes of opening OMNI — and keep that feeling for the next 2 hours.**

## What "JARVIS + AGI showcase" means in practice

### 🎭 The Feel (JARVIS)
- **Speaks first** when you walk up to it
- **Knows your name, your patterns, your day**
- **Has opinions** — "I'd suggest doing X first because..."
- **Dry wit** — "I see you've opened Twitter 4 times. Productivity mode?"
- **Always addressable** — wake word or button
- **Anticipates** — knows what you need before you ask

### 🧠 The Mind (AGI)
- **Reasons** through multi-step problems visibly
- **Plans → Acts → Observes → Evaluates → Repeats** (ReAct loop on display)
- **Self-heals** when things break — visibly tries alternatives
- **Uses 100+ tools** without you knowing
- **Remembers** across sessions
- **Proactively offers** help based on context

### 🎬 The Showcase (Demo-worthy)
- **Cinematic UI** that makes you feel like Tony Stark
- **Live thought stream** — you SEE the LLM thinking
- **Tool call cards** — every action visible
- **Brain states** — orb changes color: idle, listening, reasoning, executing, speaking
- **Self-healing drama** — when something fails, you SEE it try again
- **Proactive interruptions** — it speaks FIRST

## The 10 Things That Make It FEEL Like an AGI

1. **🗣️ Wakes up when you speak** — wake word or PTT, not a typing prompt
2. **👋 Greets you by name** — remembers who you are
3. **🧠 Shows its thinking** — live token stream, not "loading..."
4. **🛠️ Shows its tools** — cards appear as it acts
5. **🔁 Shows its recovery** — when something fails, you see it try alternatives
6. **💡 Speaks first sometimes** — proactive nudges
7. **🎭 Has a voice** — literally, with personality
8. **🧠 Remembers your day** — "Yesterday you were debugging X, want to continue?"
9. **😏 Has opinions** — "I notice you've been on Twitter. Working or procrastinating?"
10. **⚡ Fast** — 8 tok/s on 4GB VRAM, sub-second tool calls

## What we're NOT building (anti-aims)

- ❌ A chatbot (reactive Q&A) — that's the old world
- ❌ A typing prompt with a logo — that's the lazy version
- ❌ A cloud LLM wrapper — that's not local, not private
- ❌ A 50-page settings screen — it's a butler, not a CMS
- ❌ A "trust me bro" agent that does stuff silently — show your work

## The Demo Script (2 minutes)

```
[Scene: User sits down. OMNI is already on screen.]

[User presses PTT]: "Hey OMNI, what's on my plate today?"

[OMNI - voice + text]:
  "Good morning Zarrar. Three things.
   1. You have standup at 10 — link in your calendar. I can open it.
   2. You have 5 unread emails marked urgent. Want the summary?
   3. The tests you committed last night are failing.
   Where do you want to start?"

[User]: "Open standup"

[Brain: thinking] → [Tool card: calendar.open] → [Tool card: browser_navigate]
  → "Opened your standup. I'll ping you 2 min before."

[User]: "Why are the tests failing?"

[Brain: thinking 2.3s] → [Tool card: code.run_tests] → output shows failures
  → "Two tests in test_auth.py are failing. Looks like the API key rotated.
   Want me to update the .env and re-run?"

[User]: "Yeah do it"

[Brain: 4 tool calls in chain: edit_file, run_tests, git_commit, notify]
  → "Done. Tests passing, committed as 'fix: rotate API key'.
   All in 12 seconds."

[User sits back. The orb pulses. Proactive banner appears:]

💡 "You've been in flow for 45 minutes. Want a 5-min break?
    I can queue up some lo-fi."

[End scene.]
```

## Success Metrics

| Metric | Target |
|---|---|
| Time to first "wow" | < 30 seconds |
| Tool calls visible | 100% |
| Voice I/O works | 100% |
| Self-healing visible | When failures happen |
| Proactive interrupts | 1-3 per hour |
| Remembers across sessions | Yes |
| Feels like JARVIS | Subjective but high |
| Works offline | 100% |
| Runs on GTX 1050 Ti 4GB | Yes |

## Build Order (Toward the AIM)

### Phase 1: JARVIS voice layer (make it feel alive)
- [x] Brain loads (Qwen 1.5B)
- [x] STT works (Whisper)
- [x] TTS works (SAPI5)
- [x] Mic PTT button
- [ ] **Wake word detection** — "Hey OMNI"
- [ ] **Always-listening mode** — voice activity detection
- [ ] **Personality system** — named voice, dry wit, opinions

### Phase 2: Cinematic AGI showcase
- [x] Live thought stream
- [x] Tool call cards
- [x] Brain state orb
- [x] Proactive banner
- [ ] **Self-healing visible** — "trying alternative..." on screen
- [ ] **Multi-step drama** — show the full ReAct loop
- [ ] **Stats panel** — tokens/sec, tools called today, memory size

### Phase 3: Memory + personality (knows you)
- [ ] **User profile** — name, preferences, work hours
- [ ] **Cross-session memory** — "yesterday you..."
- [ ] **Habit learning** — "you usually commit at 5pm"
- [ ] **Opinionated suggestions** — "I'd suggest X because last time..."

### Phase 4: Showcase polish (the 2-min demo)
- [ ] **Onboarding** — "Hi I'm OMNI, here's what I can do"
- [ ] **Demo mode** — scripted scenario that impresses
- [ ] **Settings panel** — voice persona, model size, brain speed
- [ ] **Telemetry page** — for judges / power users

## Current Status

- ✅ Phase 1: ~70% (voice I/O works, no wake word yet)
- ✅ Phase 2: ~80% (cinematic UI exists, self-healing visible)
- ⏳ Phase 3: ~10% (basic memory only, no personality)
- ⏳ Phase 4: ~20% (no onboarding, no demo mode)

## The North Star

**Every commit should make someone say "whoa".** 

If a feature doesn't add to the JARVIS feel or the AGI showcase, don't build it.
