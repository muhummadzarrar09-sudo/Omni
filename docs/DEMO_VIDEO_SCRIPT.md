# 🎬 OMNI V3 — Demo Video Script (2 Minutes)

> A 2-minute demo video for showing off OMNI.
> Format: screen recording with voiceover
> Target audience: anyone curious about local AI / AGI

---

## Pre-Recording Setup (5 min)

**Environment:**
- Clean desktop, no other windows
- OMNI running in background: `omni start` + `cd frontend_next && npm run dev`
- Browser tabs: http://localhost:3000 (cinematic UI), http://localhost:8765/docs (Swagger)
- Terminal: open in second monitor or picture-in-picture for backend logs
- Mic: tested, audio levels good
- Screen recorder: OBS, Loom, or built-in (Win+G)

**Set the scene:**
- Dark theme everywhere
- Volume: music off, voiceover on
- Run `curl -X POST http://localhost:8765/api/onboarding/skip` to skip onboarding
- Set your name: `curl -X POST http://localhost:8765/api/user/profile -H "Content-Type: application/json" -d "{\"name\":\"Zarrar\"}"`

---

## THE SCRIPT (2:00)

### [0:00–0:15] COLD OPEN — The Hook

**Visual:** Cinematic UI, dark background, orb pulsing slowly in center. Camera zooms in slowly.

**Voiceover (calm, curious):**
> "This is OMNI V3 — a local AGI assistant. It runs entirely on this laptop. No cloud, no API keys, no data leaves this machine. Watch what happens when I ask it to do real work."

**Action:** Click the input box at the bottom of the cinematic UI.

---

### [0:15–0:30] SCENE 1 — I Can Think

**Visual:** Type `what's on my plate today?` in the input. Press enter.

**Voiceover:**
> "I asked it what's on my plate today. Watch — it's not a chatbot. You can see the LLM thinking in real-time, the tool calls appearing as cards, the brain state cycling through 'Reasoning' to 'Executing'."

**Action:** Point at the live thought stream. Point at the tool call cards as they appear.

**Result on screen:** "Based on your profile and yesterday's work, here are 3 things: standup at 10, 5 urgent emails, the auth tests are failing..."

---

### [0:30–0:50] SCENE 2 — I Can Take Action

**Visual:** Type `open github` in the input. Press enter.

**Voiceover:**
> "And it just does it. No 'I can't do that.' No 'click here to open your browser.' It just opens github, in an isolated profile with no email signed in. Privacy by design."

**Action:** Chrome opens with github.com, OMNI-Profile. The brain state shows "Done." with a small celebration emoji.

**Tip:** The thought stream shows "browser_navigate" → "success" → "Done in 1.2 seconds." 🎯

---

### [0:50–1:10] SCENE 3 — I Can Recover

**Visual:** Type `open this_doesnt_exist.exe` in the input. Press enter.

**Voiceover:**
> "Here's where most agents fail. They just say 'command not found' and give up. OMNI doesn't. Watch — it tries alternatives. Chrome → msedge → graceful error. That's the Hermes self-healing loop."

**Action:** The brain state cycles through "Error" → "Retrying" → "Self-heal" → "Fallback". The tool cards show multiple attempts.

**Result on screen:** "I tried chrome, msedge, and the LaunchService. None worked. Want me to install the app, or open it in the browser instead?"

---

### [1:10–1:25] SCENE 4 — I Can Remember

**Visual:** Type `what did I do yesterday?` in the input. Press enter.

**Voiceover:**
> "Yesterday I worked on the auth tests. I committed a fix at 2am, opened 2 PRs, and replied to 3 reviews. I remember because OMNI logs every session. Today, when I open the UI, it's going to greet me by name and recap yesterday's work."

**Action:** The memory panel shows yesterday's digest: 47 commands, 3 sessions, top topic "auth".

---

### [1:25–1:45] SCENE 5 — I Can Speak First

**Visual:** Wait. Do nothing. Let the proactive engine fire.

**Voiceover:**
> "I didn't ask for anything. OMNI is watching. It knows my disk is almost full, I've been coding for 2 hours, and my battery is at 12%. It's about to interrupt me."

**Action:** A floating amber banner slides in from below the orb:

> 💡 "Battery at 12%. Want me to dim the screen and close heavy apps to save power?"

**Voiceover (over):**
> "That's the proactive engine. 9 rules. Battery, disk, coding time, meetings, idle, morning brief, end of day, weekly review, welcome back. It sees you need help before you ask."

---

### [1:45–2:00] COLD CLOSE — The Flex

**Visual:** Pull back to show the full OMNI window. Orb pulsing. Tool cards visible. Memory panel. Stats panel.

**Voiceover (low, cinematic):**
> "100+ tools. 1.5 billion parameter brain. Voice I/O. Vision. Multi-agent self-healing. Persistent memory. Personality with opinions. 10 security defenses. 110+ tests passing. All local. All private. All yours. This is OMNI V3. The local AGI that actually does stuff."

**Final visual:** Cut to the cinematic UI, orb centered, title card overlay:

> **OMNI V3 — Local, Private, Cinematic AGI**
> github.com/muhummadzarrar09-sudo/Omni

**[END]**

---

## Post-Production Notes

**Pacing:** The first 30 seconds are the hook. Don't linger.

**Visual style:** Dark theme, high contrast, minimal text on screen. Let OMNI do the talking. The orb + tool cards are visually striking — they ARE the demo.

**Audio:** Voiceover should be calm, not hyped. Let the actions speak. Add subtle background music (lo-fi, very low) to fill silence.

**Length:** 2:00 is the TARGET. Don't go over 2:30. Judges have attention spans.

**Cuts:** If a tool call takes >5 seconds, cut. Don't show loading. Show the RESULT.

**B-roll:** If you have time, cut to:
- Terminal showing `omni test` with green checkmarks
- Stats panel: "847 commands, 5.2 hours saved, peak at 10am"
- The 8-scene demo mode running (`POST /api/demo {"action":"start"}`)

---

## The 30-Second Version (for Twitter/LinkedIn)

Same content, cut to 30s:
- 0:00–0:05 Cold open (UI)
- 0:05–0:15 "What's on my plate today?" → multi-tool execution
- 0:15–0:20 "Open github" → done
- 0:20–0:25 "Open this_doesnt_exist.exe" → self-heal
- 0:25–0:30 Proactive banner slides in. End.

---

## The 60-Second Version (for product hunt, Reddit, HN)

- 0:00–0:10 Cold open
- 0:10–0:25 "What's on my plate" → thinking + tool cards visible
- 0:25–0:35 "Open github" + "Open this_doesnt_exist.exe" (self-heal)
- 0:35–0:50 "What did I do yesterday?" → memory panel
- 0:50–0:60 Proactive banner slides in. End with stats: "847 commands, 5.2 hours saved, 100% local"

---

## The 5-Minute Version (for deep-dive reviews)

Add:
- 0:00–0:30: Architecture diagram, brief code walkthrough
- 1:00: `omni test` showing 110+ tests
- 1:30: Stats dashboard
- 2:00: `omni shell` (interactive REPL)
- 2:30: The 8-scene auto-demo running in full
- 3:00: Voice I/O working
- 3:30: Settings panel (personality sliders, voice personas, theme)
- 4:00: The README tour
- 4:30: Outro with call-to-action

---

## What to AVOID

- ❌ Don't show error messages or stack traces
- ❌ Don't show code being typed (boring)
- ❌ Don't show "loading..." spinners (cut them out)
- ❌ Don't talk about technology (talk about what it DOES)
- ❌ Don't show the terminal unless the action is impressive
- ❌ Don't apologize for anything ("oh this is still rough")
- ❌ Don't compare to other products

## What TO SHOW

- ✅ The orb (cinematic, real-time, changes color)
- ✅ The thought stream (live LLM tokens)
- ✅ Tool call cards (visual, satisfying)
- ✅ The brain state labels (Reasoning → Executing → Done)
- ✅ The proactive banner (interruption is impressive)
- ✅ The stats panel (numbers flex)
- ✅ "Done in 1.2 seconds" messages
- ✅ The greeting by name

---

## Recording Checklist

- [ ] OMNI running, both backend (:8765) and UI (:3000)
- [ ] User profile set with name
- [ ] Onboarding skipped
- [ ] Several commands run before recording (so memory has data)
- [ ] Mic tested, no echo
- [ ] Screen recorder at 1080p+, 30+ FPS
- [ ] Dark theme everywhere
- [ ] 2-minute target
- [ ] Backup of: just in case the brain takes too long, have a "fast mode" setting

---

**You've got a 2-minute script. Now go record and submit.** 🏆
