# 🤖 OMNI V3 / PHASE 6 PRD: AGI-LEVEL HERMES ORCHESTRATION, SEMANTIC REFINEMENT & CUSTOM SKILL SYNTHESIS

**Document ID:** `docs/42-PHASE-6-AGI-HERMES-ORCHESTRATION-PRD.md`  
**Date:** July 14, 2026 | **Target Phase:** Phase 6 (AGI & Autonomous Mastery)  
**Hardware Constraint:** GTX 1050 Ti 4GB VRAM (`Llama-3.2-3B-Instruct.Q4_K_M.gguf` / `Llama-3.1-8B-Instruct.Q4_K_M.gguf` + `TurboVLM Moondream2`)  
**Core Reference Architecture:** Hermes Agent (`eadmin2/jarvis_ai` research from `docs/15-JARVIS-RESEARCH.md`) + Bagillion Loop (`docs/37-BAGILLION-PERCENT-LOOP.md`)

---

## 1. Executive Summary & Why This Architecture is Required

To transition OMNI from a **high-end automated voice assistant** into an **autonomous, AGI-feeling desktop entity (JARVIS / Hermes Agent)**, the system must break free from static tool boundaries. 

In `docs/15-JARVIS-RESEARCH.md`, our analysis of `eadmin2/jarvis_ai` (Hermes Agent) revealed its core superpower: **One Brain, Persistent Memory, and Dynamic Skill Generation.** If an action is missing or fails, Hermes does not halt; it synthesizes code, tests it, learns from errors, and stores the solution permanently.

This PRD formalizes **Phase 6: AGI Hermes Orchestration**, introducing:
1. **The Semantic & Self-Refinement Loop (`Multi-Orchestrator V3`):** Closed-loop `Plan -> Act -> Observe -> Evaluate -> Refine` execution that self-corrects runtime errors autonomously.
2. **Dynamic Custom Skill Synthesis (`SkillMakerAgent`):** On-the-fly Python skill creation, verification, and permanent registration when pre-built tools are insufficient.
3. **The "Fast AF" Hybrid Database (`DuckDB` + `FAISS/Chroma` In-Memory Index):** Sub-millisecond (`<1ms`) semantic retrieval and analytical querying, keeping the GTX 1050 Ti 100% responsive.

---

## 2. Multi-Orchestration & The Semantic Refinement Loop

### 2.1 The Closed-Loop Multi-Orchestrator Architecture
We evolve the Phase 1 multi-agent skeleton (`Planner -> Executor -> Monitor -> Evaluator`) into an **asynchronous, self-refining cognitive engine**:

```
 [ User Command / Voice ]
           │
           ▼
 [ 1. SemanticRouter (Fast AF DB / FAISS <1ms) ]
           │
           ├───► [ Match Found (>0.85) ] ─────────────────► [ Execute Pre-Built / Custom Skill ]
           │                                                            │
           └───► [ No Match / Complex Goal ]                            ▼
                         │                                    [ 4. MonitorAgent ]
                         ▼                                    (Captures stdout/stderr/screen)
                 [ 2. PlannerAgent (GGUF LLM) ]                         │
                 (Breaks goal into JSON steps)                          ▼
                         │                                    [ 5. EvaluatorAgent ]
                         ▼                                              │
                 [ 3. ExecutorAgent ] ──────────────────────────────────┤
                                                                        ▼
                                                       ┌─── [ Goal Achieved? ] ───┐
                                                       │ YES                      │ NO
                                                       ▼                          ▼
                                             [ Log & Store Skill ]     [ 6. Refinement Loop ]
                                             (Fast AF DB update)       (Feeds error back to GGUF)
                                                                                  │
                                                                       ┌──────────┴──────────┐
                                                                       ▼                     ▼
                                                              [ Action Retry ]     [ 7. SkillMaker ]
                                                              (Param tweak <3x)    (Synthesizes code)
```

### 2.2 The Self-Refinement Engine (`EvaluatorAgent` + `RefinementLoop`)
When an execution step fails (e.g., `Errno 2: chrome.exe not found` or `Invalid CLI syntax`), the system does not return an error to the user:
1. **Error Capture:** `MonitorAgent` intercepts the exact traceback, exit code, and optional `TurboVLM` screen capture of the error popup.
2. **Refinement Prompting:** `EvaluatorAgent` constructs a compressed GGUF repair prompt:
   ```json
   {
     "original_goal": "Open Chrome and go to YouTube",
     "failed_step": "windows_launch {'app': 'chrome'}",
     "error_observed": "[Errno 2] No such file or directory: 'chrome.exe'",
     "instruction": "Refine the step using fallback applications or alternative system paths."
   }
   ```
3. **Autonomous Self-Correction:** The GGUF reasoning brain outputs: `{"tool": "windows_launch", "app": "msedge", "url": "https://youtube.com"}` or executes a path discovery tool. The step is re-executed up to `max_retries=3`.

---

## 3. Autonomous Custom Skill Synthesis (`SkillMakerAgent`)

### 3.1 Why Custom Skills? (The "Do ANYTHING" Superpower)
Even with 100+ tools (`omni_v2/tools/`), unique user requests like *"Schedule a meeting with John tomorrow at 3pm and notify me via Telegram"* or *"Parse my local CSV and plot a bar chart"* require ad-hoc logic.

### 3.2 The `SkillMakerAgent` Lifecycle
When `EvaluatorAgent` determines that no existing tool or sequence can accomplish the goal, it triggers `SkillMakerAgent`:

1. **Synthesis (`omni_v2/skills/generator.py`):**  
   The `Llama-3.2-3B / Llama-3.1-8B` model writes a self-contained, typed Python plugin conforming to the `CommandPlugin` base class:
   ```python
   # Auto-generated by SkillMakerAgent on 2026-07-14
   from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult
   import subprocess

   class CustomScheduleEventSkill(CommandPlugin):
       metadata = CommandMetadata(
           name="custom_schedule_event",
           category="system_management",
           description="Schedules calendar events natively via Windows URI/Outlook",
           patterns=["schedule meeting", "add calendar event"],
           examples=["schedule a meeting with John tomorrow at 3pm"]
       )
       async def execute(self, entities: dict, context: dict) -> CommandResult:
           title = entities.get("title", "New Event")
           time_str = entities.get("time", "tomorrow")
           # Native Windows Outlook/Calendar URI invocation
           uri = f"outlookcal:addevent?subject={title}&start={time_str}"
           subprocess.run(["cmd", "/c", "start", uri], shell=True)
           return CommandResult.ok(f"Scheduled event: {title} at {time_str}")
   ```

2. **Sandboxed Verification (`omni_v2/skills/verifier.py`):**  
   `SkillMakerAgent` compiles the generated code (`py_compile`), inspects for dangerous imports (`os.system('rm -rf')`, network exfiltration to unauthorized endpoints), and runs a mock unit test inside a restricted sub-process.

3. **Permanent Registration (`SkillRegistry` + Fast AF DB):**  
   Once verified, the skill is saved to `data/skills/custom_schedule_event.py`, dynamically loaded via `importlib`, and its semantic embedding is written to the `Fast AF DB` vector index.

4. **Continuous Mastery:**  
   The next time the user asks to schedule an event, `SemanticRouter` matches `custom_schedule_event` at `0ms` planning latency. OMNI literally **gets faster and smarter the more you use it.**

---

## 4. The "Fast AF" Hybrid Database Architecture

### 4.1 Memory & Storage Bottlenecks on GTX 1050 Ti
Standard SQLite text searches or raw JSON vector scanning (`vector_fallback.json`) degrade when execution logs, 5-turn context histories, and 200+ skill embeddings accumulate. The GPU VRAM is reserved for `Llama-3.2-3B GGUF` + `faster-whisper INT8`; CPU/RAM must handle database lookups with zero lag.

### 4.2 The 3-Tier Hybrid Engine (`omni_v2/memory/fast_af_store.py`)

```
+---------------------------------------------------------------------------------+
|                                 FAST AF DB HYBRID                               |
+------------------------------------+--------------------------------------------+
| TIER 1: In-Memory Vector Cache     | FAISS / ChromaDB (RAM - Sub-millisecond)   |
|                                    | • 100+ Core Tools & Custom Skills Index    |
|                                    | • 5-Turn Active Context Vector Map         |
+------------------------------------+--------------------------------------------+
| TIER 2: Analytical & Log Engine    | DuckDB Embedded (Disk/RAM - 10x-50x speed) |
|                                    | • Execution traces, latency benchmarks     |
|                                    | • Telemetry & multi-agent step history     |
+------------------------------------+--------------------------------------------+
| TIER 3: ACID Persistent Core       | SQLite (`data/memory.db` - Zero corruption)|
|                                    | • User preferences, face auth hashes       |
|                                    | • Permanent skill metadata & registry      |
+------------------------------------+--------------------------------------------+
```

### 4.3 Performance Specification
* **Semantic Tool/Skill Lookup:** `<1.2 ms` (Tier 1 FAISS/Chroma).
* **10,000 Step History Analytical Query:** `<5.0 ms` (Tier 2 DuckDB columnar execution).
* **ACID Transaction Commit:** `<2.0 ms` (Tier 3 SQLite WAL mode).

---

## 5. Implementation Roadmap (Phase 6 Phased Rollout)

### Phase 6.1: Fast AF DB & Semantic Router Upgrade (Target: 2 Hours)
* [ ] Implement `omni_v2/memory/fast_af_store.py` encapsulating `DuckDB` + `FAISS/Chroma` + `SQLite WAL`.
* [ ] Wire `SemanticRouter` to query `Fast AF DB` before hitting `CommandRegistry` regex.
* [ ] Benchmark lookup latency (`assert lookup_ms < 2.0`).

### Phase 6.2: Multi-Orchestrator Refinement Loop (Target: 3 Hours)
* [ ] Update `omni_v2/agents/evaluator.py` to construct GGUF repair prompts on `CommandResult.error()`.
* [ ] Modify `omni_v2/agents/executor.py` to support `execute_step_with_retry(step, max_retries=3)`.
* [ ] Connect `MonitorAgent` to feed `stderr` and `TurboVLM` error screenshots into the refinement prompt.

### Phase 6.3: `SkillMakerAgent` & Custom Skill Synthesis (Target: 3 Hours)
* [ ] Create `omni_v2/skills/` directory (`__init__.py`, `generator.py`, `verifier.py`, `registry.py`).
* [ ] Implement GGUF code generation templates for system management (`calendar_control`, `task_scheduler`, `file_organizer`).
* [ ] Build AST safety verifier to block unsafe shell injections.
* [ ] Verify end-to-end flow: Unknown Voice Command -> Skill Generated -> Verified -> Registered -> Executed.

---

## 6. Verification & Acceptance Criteria (For Judges & DevPost)

When Phase 6 is complete, the following integration test must pass 10/10 without human intervention:

```powershell
python -m omni_v2.tests.test_hermes_orchestration
```

1. **Test 1 (`Refinement Loop`):** Command `open chrome` when `chrome.exe` is missing -> `EvaluatorAgent` detects `Errno 2` -> Refines to `open msedge` -> ✅ Passes.
2. **Test 2 (`Custom Skill Synthesis`):** Command `schedule meeting with John tomorrow at 3pm` -> No exact tool exists -> `SkillMakerAgent` synthesizes `CustomScheduleEventSkill` -> Verifies AST -> Registers in `Fast AF DB` -> Executes native Windows Calendar URI -> ✅ Passes.
3. **Test 3 (`Fast AF DB Speed`):** Querying 100+ tools and 50 custom skills via semantic vector lookup completes in `<1.5 ms` on CPU -> ✅ Passes.
4. **Test 4 (`Continuous Learning`):** Second invocation of `schedule meeting` uses the cached `CustomScheduleEventSkill` directly (`0ms` planning, `0` LLM tokens consumed) -> ✅ Passes.

---

**END OF PHASE 6 PRD — OMNI V3 IS READY FOR AGI HERMES MASTERY**  
*Zarrar + Agent | July 14, 2026*
