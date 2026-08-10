# OMNI JARVIS BRAIN — Full Architecture Plan

> A complete, autonomous brain-of-itself for OMNI — on a **4GB GPU** (GTX 1050 Ti).
> Target hardware constraint, stated up front: we stay on **Q4 models between 1.5B and
> 3B** (~1–2GB VRAM). That means the *architecture* must carry most of the "Jarvis"
> experience. This doc is the plan only — **no code yet** (per request). Review it, then
> we build.

---

## 0. The guiding idea

A chatbot answers. Jarvis *has a mind*: it knows who it is, holds goals across days,
notices patterns, plans before acting, checks its own work, and remembers you. This plan
builds each of those as a real, testable subsystem that plugs into the brain OMNI already
has (`omni_v2/llm/brain.py` + `omni_v2/agents/*` + the RAG/CAG memory).

The one-line thesis:

> **Small model, big scaffold.** Every "smart" behavior comes from a tight loop of
> identity → state → memory → plan → act → evaluate → remember, and the model is just the
> language engine inside that loop.

---

## 1. The brain loop (the "mind" in one picture)

```
        ┌──────────────────────────────────────────────────────────┐
        │                    JARVIS CORE (persistent)              │
        │  Identity · Goals · User-profile · Mood · Values         │
        └───────────────▲──────────────────────────────▲───────────┘
                        │ injects every turn           │ updates
   ┌────────────┐  ┌────┴─────┐   ┌──────────┐   ┌─────┴────┐   ┌───────────┐
   │  SENSES    │→ │  STATE   │→  │  PLAN    │→  │   ACT    │→  │ EVALUATE  │
   │ wake/txt/  │  │ now/ctx/ │   │ goals→   │   │ tools/   │   │ did it    │
   │ kb/events  │  │ app/date │   │ steps    │   │ skills   │   │ work?     │
   └────────────┘  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬──────┘
                        │              │             │              │
                        └──────────────┴─────────────┴──────────────┘
                                      │ feedback into next plan
                                     MEMORY (RAG long + CAG short + episodic)
```

**What already exists (and is good):** ReAct loop, Planner/Executor/Monitor/Evaluator,
personality/opinion, scheduler, RAG+CAG hybrid memory, away task queue, security.
**What's missing (this plan):** identity core, goal stack, metacognition loop, episodic
reflection, model tiering, and wiring the evaluator's verdict back into decisions.

---

## 2. The Model Track (fits your 4GB GPU)

| Tier | When | Model | VRAM (Q4) |
|------|------|-------|-----------|
| **fast** | quick lookups, time, open app | Qwen2.5-1.5B (already have) | ~1.1GB |
| **brain** | normal conversation + tool calls | Qwen2.5-1.5B (default) | ~1.1GB |
| **deep** | hard reasoning, planning, code | Qwen2.5-3B-Instruct Q4 (add) | ~2.2GB |

**Plan:**
- Add a Qwen2.5-**3B** Q4 model (≈2.2GB) for the `deep` tier only.
- Wire `LLMRouter.tiers` into `Brain.think()` — it's half-built already. A simple
  `needs_deep(text)` heuristic (length, "why/how/plan/code/debug", multi-step words)
  escalates to the 3B; everything else stays on 1.5B for speed.
- **Never** load both at once → on a 4GB card loading the 3B evicts the 1.5B. So tiering
  is: load 1.5B by default, swap to 3B for the deep call, swap back. Document the ~2s swap.
- Fallback everywhere: no model loaded → the existing regex/smart-router path.

> This is the ONE realistic model upgrade on 4GB. 7B Q4 needs ~4.7GB — out of VRAM (would
> spill to CPU and get slower than 3B). If you ever get 8GB+, this tier table just gains a
> 7B `deep` and the 3B becomes `brain`.

---

## 3. The Identity Core (makes it "a self")

New persistent store `data/brain/identity.json`:

```
identity = {
  name: "OMNI",
  persona: "Jarvis-style butler — calm, dry, competent, protective",
  values: ["privacy", "efficiency", "honesty", "initiative"],
  mood: "neutral",            # updated by events
  goals_today: [...],         # high-level intents for today
  user: { name, style, likes, dislikes, comm_prefs },
  long_term_goals: [...],     # "become more autonomous", "learn my calendar"
  reflections: [...],         # saved episodic insights
}
```

**Behavior:**
- Every turn, the brain injects a compact **identity block** into the system prompt
  (name, persona, mood, top goal, how to address the user).
- The **opinion/personality engines** now read from identity instead of static strings,
  so "Jarvis" has consistent voice *and* evolving attitude.
- `/api/brain/identity` endpoints to read/update it (and a tab in the desktop app).

---

## 4. The Goal/Task Brain (real autonomy)

New store `data/brain/goals.json` — a persistent **goal stack**:

```
goal = {
  id, title, intent, status(pending|active|done|abandoned),
  created, deadline, progress(0-1),
  steps: [{ desc, status, depends_on }],
  history: [{ action, result, ts }],
}
```

**Behavior:**
- "Jarvis, do X" with a big X → **decompose** into steps (LLM deep tier) → queue.
- Steps execute through the existing **Executor + away queue** (research / tool / report).
- **Progress tracking across sessions**: goals persist; `progress` updates as steps complete.
- **Replan on failure**: when a step's Evaluator verdict fails, generate a new sub-step or
  ask the user — *this is the metacognition loop*.
- **Follow-through**: "remind me at 3pm" / "report when done" already have the scheduler +
  messenger; goals reference them so Jarvis *owns* the thread, not just fires-and-forgets.

---

## 5. Metacognition (thinking about its own thinking)

- The **Evaluator** agent already returns a verdict. Today it mostly logs.
- **Plan:** make `evaluate()` return a structured signal per action:
  `{succeeded, confidence, cause_of_failure, suggested_fix}` and feed it **back into the
  Planner** before the next step. Result: self-healing that's *visible* (the UI already
  shows tool cards — add "recognized failure, adjusting plan").
- Add a **confidence gate**: if the brain is unsure it asks a clarifying question instead
  of guessing (Jarvis is competent, not reckless).

---

## 6. Episodic Reflection & Pattern Awareness

- **Auto-digests**: reuse the away-mode digest machinery to write a short "today recap"
  each session end into memory (`episodic` kind in HybridMemory).
- **Pattern notices**: a lightweight rule engine over session memory flags repeats
  ("opened X 4× today", "stuck on Y for 3 days") and surfaces them as proactive
  suggestions — Jarvis noticing, not just reporting.
- **Memory of you**: user likes/dislikes/tone captured and injected every turn via the
  identity block + CAG pinned context.

---

## 7. Delivery order (build these in this sequence)

| Step | Deliverable | Impact | Effort |
|------|-------------|--------|--------|
| **1** | **Identity core** + inject into `think()` | instant "self" feel | small |
| **2** | **Model tiering** (1.5B/3B) wired into `Brain.think()` | smarter hard calls | medium |
| **3** | **Goal stack** + decompose + progress + replan | true autonomy | high |
| **4** | **Evaluator feedback loop** (metacognition) | self-correcting | medium |
| **5** | **Episodic reflection** + pattern notices | Jarvis "notices" | small–med |

Each step is testable offline (no model needed for the identity/goal/reflection logic) and
plugs into the existing CLI + desktop app + `/api/brain/*` endpoints.

---

## 8. Files we'd touch / add

- `omni_v2/brain/` (new): `identity.py`, `goals.py`, `metacog.py`, `reflect.py`
- `omni_v2/llm/brain.py`: inject identity + state + context_provider; tier escalation
- `omni_v2/llm/router.py`: wire `deep` tier to a 3B GGUF
- `omni_v2/agents/evaluator.py`: structured verdict + feedback
- `omni_v2/away/*`: reuse queue/digest/reporter
- `backend_fastapi/brain_routes.py` + `omni/cli.py` (`omni brain` subcommands)
- `omni_v2/tests/test_brain_*.py`

---

## 9. Honest expectations

- On a 4GB GPU, Jarvis feels like **a competent, self-aware local butler** — not a
  frontier LLM. The 1.5B/3B ceiling shows in complex abstract reasoning. The architecture
  makes it *feel* smart and reliable by handling memory, planning, and follow-through.
- When you upgrade hardware, the same scaffold drops in a bigger model — nothing about
  the brain architecture changes.

---

## 10. Build status

| Step | Deliverable | Status |
|------|-------------|--------|
| **1** | **Identity core (B1) + user model (B7)** | ✅ **DONE** — `omni_v2/brain/identity.py`, wired into `Brain.think()`, CLI `omni brain`, `/api/brain/*`, desktop "Identity" tab. 401 tests passing. |
| **2** | **Model tiering** (1.5B/3B) wired into `Brain.think()` | ⏳ next |
| **3** | **Goal stack** + decompose + progress + replan | ⏳ |
| **4** | **Evaluator feedback loop** (metacognition) | ⏳ |
| **5** | **Episodic reflection** + pattern notices | ⏳ |

**Usage after Step 1:**
```
omni brain status                       # see identity + user
omni brain user name=Zarrar likes=python,privacy
omni brain set-mood focused
omni brain show-prompt                  # the block injected into every turn
```
Every turn the brain's system prompt now includes `[OMNI IDENTITY]` (name, persona,
mood, values, goals today) and `[THE USER]` (name, style, tone, likes/dislikes) — so
OMNI knows who it is and who it's talking to.
