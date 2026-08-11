# OMNI Capability Matrix

> **Generated file.** Edit `quality/capabilities.json`, then run `python scripts/quality_baseline.py generate`.

**Authority verified:** 2026-08-11  
**Release state:** pre-alpha recovery  
**Source inventory digest:** `12c045db881c35936ce758e59b160b507c5525db648a948925d526a76261e240`

## Locked Product Promise

A local-first personal assistant for one owner that safely handles a deliberately limited set of daily desktop, file, browser, memory, scheduling, and voice workflows, and reports unavailable or failed work truthfully.

## Platform Scope

| Platform | Status | Reason |
|---|---|---|
| Windows 11 x64 (primary) | `target_not_qualified` | The dominant desktop automation implementation is Windows-specific; qualification is scheduled for later batches. |
| Linux | `development_only_unqualified` | Compilation and most unit tests run on Linux, but desktop, audio, installation, and E2E product behavior are not qualified. |
| macOS | `unsupported_unverified` | No current end-to-end installation, hardware, automation, or release evidence exists. |

## Pre-10 Non-goals

- General artificial intelligence or human-level general reasoning
- One hundred independent production-grade tools
- Unsupervised high-risk or irreversible autonomy
- Production support for every desktop operating system
- Cloud sync, marketplace, or mobile parity before their security and reliability gates pass
- Commercial traction or business defensibility
- A guarantee that no network traffic occurs unless enforceable offline mode is enabled and verified

## Locked Core Workflows

| ID | Workflow | Current status | Qualification batch | Verifiable outcome |
|---|---|---|---|---|
| W01 | Real daily briefing | `not_qualified` | B10 | Summarize the owner's real local calendar, tasks, reminders, and explicitly configured sources with provenance and honest unavailable states. |
| W02 | Reminder lifecycle | `not_qualified` | B09 | Create, inspect, update, trigger, and cancel a reminder with persistence across restart. |
| W03 | Local document retrieval | `not_qualified` | B09 | Find an approved local document, extract relevant content, summarize it with source paths, and respect access boundaries. |
| W04 | Safe file creation and editing | `not_qualified` | B09 | Preview, create or modify a file in an approved workspace, verify contents, and offer rollback where applicable. |
| W05 | Isolated browser task | `not_qualified` | B09 | Open the isolated browser profile, navigate or search, verify the resulting page state, and recover from browser absence. |
| W06 | Application and window control | `not_qualified` | B09 | Launch, focus, minimize, maximize, and close approved applications on the primary platform with visible verification. |
| W07 | Focus session | `not_qualified` | B09 | Start a timed focus session, apply configured notification quieting, report status, and restore state at completion or cancellation. |
| W08 | Personal session recall | `not_qualified` | B10 | Answer what the owner did yesterday from inspectable stored sessions, with timestamps, provenance, uncertainty, and delete controls. |
| W09 | Local voice task | `not_qualified` | B11 | Accept a push-to-talk command, execute one safe core workflow, and speak the verified result through a local TTS backend. |
| W10 | Truthful degraded recovery | `not_qualified` | B04 | When the model, browser, microphone, integration, or optional dependency is absent, report the exact unavailable state and provide a tested recovery path without mock success. |

## Inventory Summary

- **Capability groups:** 52
- **Mapped active source files:** 185
- **Stable capabilities:** 0
- **Stable claim policy:** no capability is stable until exact-artifact qualification passes.

| Lifecycle | Count | Definition |
|---|---:|---|
| `stable` | 0 | Release-qualified for the declared platform with real effects, failure states, tests, documentation, and dogfood evidence. |
| `beta` | 24 | A real implementation exists and has meaningful tests, but one or more release gates remain open. |
| `experimental` | 25 | Incomplete, shallow, unqualified, or likely to change; off by default in the target product. |
| `demo` | 1 | Canned or simulated behavior intended only for an explicitly labeled demo mode. |
| `unavailable` | 2 | Concept or interface exists but no usable implementation is present. |
| `removed` | 0 | Legacy implementation retained temporarily for migration or deletion and not part of product scope. |

| Implementation reality | Count | Definition |
|---|---:|---|
| `real` | 9 | Performs the represented effect through a concrete local or configured external backend. |
| `partial` | 39 | Some concrete behavior exists, but important actions, verification, or integrations are incomplete. |
| `demo` | 1 | Primarily canned or simulated output. |
| `placeholder` | 1 | Creates metadata or presentation state without performing the headline capability. |
| `stub` | 1 | Interface exists but is intentionally disabled or not implemented. |
| `infrastructure` | 1 | Internal support code rather than a direct user capability. |

## Capability Status

Lifecycle and implementation reality are separate. `beta/real` means concrete behavior exists but release qualification is still open; `demo/demo`, `unavailable/placeholder`, and `unavailable/stub` are not working product claims.

| ID | Capability | Area | Lifecycle | Reality | Target | Summary |
|---|---|---|---|---|---|---|
| `runtime.application` | Application runtime, configuration, events, and paths | core | `beta` | `infrastructure` | `personal_core` | Core application composition, workspace paths, configuration, event bus, intent mapping, guardrails, and utility setup exist. |
| `runtime.cli_launchers` | CLI and launchers | core | `experimental` | `partial` | `personal_core` | A large CLI and platform launch scripts exist, but documented one-click installation and distribution are broken. |
| `brain.local_llm` | Local LLM loading and routing | brain | `beta` | `partial` | `personal_core` | Local GGUF loading, model download, routing, fallback, and compaction code exists. |
| `brain.agent_execution` | Planning, execution, monitoring, and evaluation | brain | `beta` | `partial` | `personal_core` | Planner, executor, monitor, evaluator, memory-agent, and query-engine layers exist. |
| `brain.identity_personality` | Identity, personality, mood, and opinions | brain | `beta` | `real` | `personal_core` | Persistent identity/personality models and deterministic opinion/mood behaviors exist with unit tests. |
| `brain.goals` | Persistent goals and step progression | brain | `experimental` | `partial` | `post_10_candidate` | Goal storage, progression, failure, follow-up, abandonment, and delegation interfaces exist. |
| `brain.reflection_metacognition` | Reflection and metacognition | brain | `experimental` | `partial` | `post_10_candidate` | Episode reflection, weakness-pattern tracking, and rule proposal/application code exists. |
| `brain.subagents_harness` | Subagents, continual harness, and meta-harness | brain | `experimental` | `partial` | `post_10_candidate` | Delegation, harness artifacts, verification loops, rollback, and meta-harness concepts are implemented to varying depth. |
| `memory.profile_sessions` | User profile and session memory | memory | `beta` | `real` | `personal_core` | Profile fields, session records, daily digests, search, and persistence exist with unit tests. |
| `memory.stores_retrieval` | SQLite, vector, hybrid, and fast retrieval stores | memory | `beta` | `real` | `personal_core` | Several local memory-store implementations and sparse/dense retrieval paths exist. |
| `memory.graph_history_photos` | Knowledge graph, action history, and photo memory | memory | `experimental` | `partial` | `post_10_candidate` | Knowledge-graph generation, an action journal, and photo indexing/search implementations exist. |
| `personal.calendar_contacts` | Local calendar and contacts | personal | `beta` | `real` | `personal_core` | ICS parsing and local contact storage exist. |
| `personal.briefing` | Morning briefing and wake routine | personal | `beta` | `partial` | `personal_core` | Briefing and wake-routine composition exists over local sources. |
| `personal.proactive_experience` | Proactive suggestions, onboarding, stats, and demo orchestration | personal | `beta` | `partial` | `personal_core` | Proactive rules, greeting/onboarding state, usage statistics, and explicit demo scenes exist. |
| `automation.scheduler` | Scheduled and recurring tasks | automation | `beta` | `real` | `personal_core` | One-shot, interval, cron-style, and recurring scheduling implementations exist with persistence and tests. |
| `automation.triggers` | Automation triggers and webhooks | automation | `experimental` | `partial` | `post_10_candidate` | Trigger storage and webhook/time/event execution concepts exist. |
| `automation.away_mode` | Away tasks, remote commands, research, reporting, and messaging | automation | `experimental` | `partial` | `post_10_candidate` | Away task queueing, command polling, desktop actions, local knowledge, research, reports, and messaging adapters exist. |
| `automation.geofence` | Geofence rules and location history | automation | `experimental` | `real` | `post_10_candidate` | Place/rule models, Haversine checks, location history, events, and API integration exist with substantial tests. |
| `automation.screen_context` | Screen watcher and activity context | automation | `experimental` | `partial` | `post_10_candidate` | Periodic screen/window capture classification and activity context APIs exist. |
| `system.guardian_daemon` | Guardian monitoring, auto-start, and daemon control | system | `experimental` | `partial` | `post_10_candidate` | Health/process/file checks, autostart backends, and daemon lifecycle controls exist. |
| `tools.registry_routing` | Plugin routing and alias map | tools | `experimental` | `partial` | `personal_core` | A plugin manager, loader, supported-action lists, and broad alias map route commands to a small plugin set. |
| `tools.files` | File tools | tools | `beta` | `partial` | `personal_core` | Directory listing, folder creation, file writing, search, and related command routing exist. |
| `tools.windows_system` | Windows and system controls | tools | `beta` | `partial` | `personal_core` | Allowlisted app launch, basic window hotkeys, screenshot, and generic system-action paths exist. |
| `tools.browser` | Browser automation | tools | `beta` | `partial` | `personal_core` | Legacy browser, isolated-profile browser, and Playwright browser implementations exist. |
| `tools.desktop_productivity` | VS Code, media, accessibility, and OMNI utility tools | tools | `experimental` | `partial` | `personal_core_subset` | VS Code, media, accessibility, and OMNI utility command handlers exist. |
| `tools.ai` | AI chat, summarize, translate, and code routing | tools | `beta` | `partial` | `personal_core_subset` | AI utility commands route through the local brain where available. |
| `integrations.demo_connectors` | Gmail, calendar, smart-home, weather, and timer integration tools | integrations | `demo` | `demo` | `replace_or_remove` | Plugin interfaces exist, but Gmail, calendar, smart-home, weather, and timer paths include canned or generic demo success. |
| `notifications.local_mobile` | Notification center, preferences, snooze, and phone delivery | integrations | `beta` | `partial` | `personal_core_subset` | Local notifications, preferences, snooze state, subscriptions, and phone notification plugin paths exist with tests. |
| `voice.capture_stt` | Audio devices, push-to-talk, and speech recognition | voice | `beta` | `partial` | `personal_core` | Audio device discovery, capture pipelines, push-to-talk, faster-whisper integration, and fallback paths exist. |
| `voice.tts` | Local and online text-to-speech | voice | `beta` | `partial` | `personal_core` | SAPI/pyttsx3-style local speech and Edge TTS paths exist with selectable personas. |
| `voice.wake_word` | Wake-word detection | voice | `experimental` | `partial` | `personal_core_candidate` | OpenWakeWord, Porcupine, Whisper, and energy fallback implementations exist. |
| `voice.cloning` | Voice cloning | voice | `unavailable` | `placeholder` | `post_10_candidate` | Recording and metadata workflow exists, but training writes metadata and marks a voice ready without training a voice model. |
| `vision.multimodal` | Screen capture, OCR, and visual-language understanding | vision | `experimental` | `partial` | `post_10_candidate` | Screen capture, OCR/basic analysis, multimodal routing, and LLaVA/TurboVLM wrappers exist. |
| `security.guardrails_execution` | Guardrails and safe execution | security | `beta` | `real` | `personal_core` | Path, command, JSON, prompt, argument, URL, loop, rate, nonce, and safe-execution controls exist with focused tests. |
| `security.vault` | Credential vault | security | `beta` | `real` | `personal_core` | Fernet-backed credential storage with permissions and tests exists. |
| `security.face_lockdown` | Face authentication, guard monitoring, and lockdown | security | `experimental` | `partial` | `post_10_candidate` | LBPH/gradient/deep verifier selection, guard monitor, machine lock, and lockdown controller code exists. |
| `skills.sdk_registry` | Skill SDK and local registry | skills | `experimental` | `partial` | `post_10_candidate` | Decorators/helpers and a local skill registry exist. |
| `skills.marketplace_install` | Skill marketplace and installer | skills | `experimental` | `partial` | `post_10_candidate` | Marketplace metadata, installation, update checks, atomic download, and local installation management exist. |
| `skills.generation` | Dynamic skill generation | skills | `experimental` | `partial` | `post_10_candidate` | A skill-maker agent can generate candidate skill source and metadata. |
| `skills.sandbox_verification` | Skill sandbox and verification | skills | `beta` | `partial` | `post_10_prerequisite` | Static verification, subprocess sandboxing, and skill verification-loop code exists. |
| `api.fastapi` | FastAPI HTTP and WebSocket surface | api | `beta` | `partial` | `personal_core` | A broad HTTP/WebSocket API exists across a monolithic main module and domain routers. |
| `ui.next_web` | Next.js web interface | ui | `beta` | `partial` | `personal_core` | A cinematic Next.js interface and API proxy routes build successfully. |
| `ui.desktop` | Desktop HUD, tray, dashboard, and voice UI variants | ui | `experimental` | `partial` | `select_or_remove` | Several desktop UI implementations exist using different toolkits and visual approaches. |
| `mobile.pwa` | Mobile PWA companion | mobile | `experimental` | `partial` | `post_10_candidate` | A mobile web shell, service worker, pairing UI, WebSocket/PTT/location interactions, and notifications exist. |
| `network.discovery_pairing` | LAN discovery, pairing, and mobile transport | network | `experimental` | `partial` | `post_10_candidate` | mDNS/UDP discovery data, pairing codes, QR payloads, and backend mobile transport exist. |
| `sync.e2e` | End-to-end encrypted sync | sync | `unavailable` | `stub` | `post_10_candidate` | A disabled E2ESyncService interface explicitly reports that sync is not implemented. |
| `sync.mesh` | Mesh state synchronization | sync | `experimental` | `partial` | `post_10_candidate` | A local mesh-sync abstraction and status interface exist. |
| `interop.mcp` | Model Context Protocol bridge | interop | `experimental` | `partial` | `post_10_candidate` | MCP tool wrapping and server registration interfaces exist, including a fake provider used for current behavior/tests. |
| `data.backup` | Backup and restore | data | `beta` | `real` | `personal_core` | Backup creation/listing/restoration logic exists. |
| `files.natural_language` | Natural-language local file management | files | `beta` | `partial` | `personal_core_subset` | Natural-language intent parsing and local file operations exist. |
| `evaluation.benchmarks` | Benchmarks and leaderboard | evaluation | `experimental` | `partial` | `internal_quality` | Benchmark cases/results and a local leaderboard exist. |
| `personal.pda_shell` | Personal digital assistant shell | personal | `experimental` | `partial` | `select_or_merge` | A separate personal-digital-assistant entry point composes several personal modules. |

## Per-Capability Evidence, Requirements, and Ownership

Test paths below record only the presence of relevant test code. They do not imply passing release qualification. Empty lists mean no mapped coverage of that type. Platform lists remain empty until a release-qualified platform run exists.

### `runtime.application` — Application runtime, configuration, events, and paths

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/app.py`
- **Source paths:** `omni_v2/app.py`, `omni_v2/core/*.py`, `omni_v2/utils/*.py`, `omni_v2/__init__.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_brain_polish.py`, `omni_v2/tests/test_router_v2.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** configuration, process state, events, logs
- **Network mode:** `mixed`
- **Network destinations:** `destinations selected by composed adapters`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Configuration is fragmented across modules and environment variables
  - Clean installed-package startup is not qualified
  - Several broad fallbacks obscure component availability

### `runtime.cli_launchers` — CLI and launchers

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni/*.py`
- **Source paths:** `omni/*.py`, `omni.py`, `omni_daemon.py`, `omni_desktop.py`, `start.sh`, `start.bat`, `install.bat`, `scripts/install.sh`, `scripts/install.ps1`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** configuration, process state, events, logs
- **Network mode:** `optional`
- **Network destinations:** `package indexes`, `model download hosts`, `configured service endpoints`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - start.sh calls a missing root install.sh
  - Built wheel omits most application packages
  - Installer profiles and dependency constraints are not reproducible

### `brain.local_llm` — Local LLM loading and routing

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/llm/*.py`
- **Source paths:** `omni_v2/llm/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `llama-cpp-python`, `huggingface-hub`
- **Models:** `configured GGUF language model`
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_brain_polish.py`, `omni_v2/tests/test_compaction.py`, `omni_v2/tests/test_model_tiering.py`, `omni_v2/tests/test_router_v2.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner requests, prompts, plans, model responses, execution history
- **Network mode:** `optional`
- **Network destinations:** `model download host when explicitly requested`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Primary model is not qualified on target hardware
  - Model download and dependency installation are not release-safe
  - Fallback behavior and tool-call parsing require stricter contracts

### `brain.agent_execution` — Planning, execution, monitoring, and evaluation

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/planner.py`
- **Source paths:** `omni_v2/agents/planner.py`, `omni_v2/agents/executor.py`, `omni_v2/agents/monitor.py`, `omni_v2/agents/evaluator.py`, `omni_v2/agents/memory.py`, `omni_v2/engine/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_brain_polish.py`, `omni_v2/tests/test_query_engine.py`, `omni_v2/tests/test_hermes_refinement.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner requests, prompts, plans, model responses, execution history
- **Network mode:** `mixed`
- **Network destinations:** `destinations selected by invoked tools`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Policy, execution, verification, recovery, and response responsibilities overlap
  - Some verification methods return true without observing effects
  - Mock-success and generic routing remain reachable

### `brain.identity_personality` — Identity, personality, mood, and opinions

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/brain/identity.py`
- **Source paths:** `omni_v2/brain/identity.py`, `omni_v2/agents/personality.py`, `omni_v2/agents/opinion.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_identity.py`, `omni_v2/tests/test_personality.py`, `omni_v2/tests/test_opinion.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner requests, prompts, plans, model responses, execution history
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Not qualified through the complete UI/backend flow
  - Personality must never hide uncertainty, denial, or failure
  - Personal-data consent and retention need final policy

### `brain.goals` — Persistent goals and step progression

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/brain/goals.py`
- **Source paths:** `omni_v2/brain/goals.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_goals.py`, `omni_v2/tests/test_post_goal_flow.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner requests, prompts, plans, model responses, execution history
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Autonomous goal execution is not qualified
  - External side effects and consent boundaries are incomplete
  - No daily-use evidence

### `brain.reflection_metacognition` — Reflection and metacognition

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/brain/reflect.py`
- **Source paths:** `omni_v2/brain/reflect.py`, `omni_v2/brain/metacog.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_reflect.py`, `omni_v2/tests/test_metacog.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner requests, prompts, plans, model responses, execution history
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Quality benefit is not evaluated
  - Self-modification governance and rollback require stronger controls
  - Descriptions overstate autonomous improvement

### `brain.subagents_harness` — Subagents, continual harness, and meta-harness

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/subagents.py`
- **Source paths:** `omni_v2/agents/subagents.py`, `omni_v2/harness/*.py`, `omni_v2/meta/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_subagents.py`, `omni_v2/tests/test_harness.py`, `omni_v2/tests/test_meta_harness.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner requests, prompts, plans, model responses, execution history
- **Network mode:** `mixed`
- **Network destinations:** `destinations selected by delegated tools`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - No production autonomy qualification
  - Generated changes and verification boundaries need isolation
  - Benefits are demonstrated mostly through internal tests

### `memory.profile_sessions` — User profile and session memory

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/user_profile.py`
- **Source paths:** `omni_v2/agents/user_profile.py`, `omni_v2/memory/session_memory.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_user_profile.py`, `omni_v2/tests/test_session_memory.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner profile, sessions, stored documents, embeddings, retrieval history
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Cross-process integrity is not fully qualified
  - Sensitive inference consent and provenance need strengthening
  - Backup, migration, retention, and complete UI controls remain open

### `memory.stores_retrieval` — SQLite, vector, hybrid, and fast retrieval stores

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/memory/fast_af_store.py`
- **Source paths:** `omni_v2/memory/fast_af_store.py`, `omni_v2/memory/hybrid_memory.py`, `omni_v2/memory/sqlite_store.py`, `omni_v2/memory/vector_store.py`, `omni_v2/memory/__init__.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `numpy`, `configured vector/embedding backend`
- **Models:** `configured embedding model`
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_fast_af_db.py`, `omni_v2/tests/test_hybrid_memory.py`, `omni_v2/tests/test_knowledge_base.py`, `omni_v2/tests/test_query_engine.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner profile, sessions, stored documents, embeddings, retrieval history
- **Network mode:** `optional`
- **Network destinations:** `configured model download or retrieval backend`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Overlapping authoritative stores have not been consolidated
  - Multi-process lifecycle and corruption recovery are not fully tested
  - Retrieval quality lacks an owner-grounded evaluation set

### `memory.graph_history_photos` — Knowledge graph, action history, and photo memory

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/graph/*.py`
- **Source paths:** `omni_v2/graph/*.py`, `omni_v2/history/*.py`, `omni_v2/photos/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_knowledge_graph.py`, `omni_v2/tests/test_history_photos_backup.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner profile, sessions, stored documents, embeddings, retrieval history
- **Network mode:** `optional`
- **Network destinations:** `configured caption/model backend`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Not qualified as one coherent personal-memory system
  - Provenance, deletion propagation, and access policy need work
  - Photo and graph usefulness is not dogfooded

### `personal.calendar_contacts` — Local calendar and contacts

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/personal/*.py`
- **Source paths:** `omni_v2/personal/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_personal.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, calendar, tasks, contacts, preferences, assistant responses
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Calendar test is wall-clock brittle
  - Timezone and recurring-event behavior need qualification
  - This is distinct from the canned CalendarTool integration

### `personal.briefing` — Morning briefing and wake routine

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/briefing/*.py`
- **Source paths:** `omni_v2/briefing/*.py`, `omni_v2/wake/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_briefing.py`, `omni_v2/tests/test_wake_leaderboard.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, calendar, tasks, contacts, preferences, assistant responses
- **Network mode:** `mixed`
- **Network destinations:** `explicitly configured briefing sources`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Not qualified against real owner data
  - Source availability and provenance must be explicit
  - External/canned sources must not contaminate real briefings

### `personal.proactive_experience` — Proactive suggestions, onboarding, stats, and demo orchestration

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/proactive.py`
- **Source paths:** `omni_v2/agents/proactive.py`, `omni_v2/agents/proactive_v2.py`, `omni_v2/agents/onboarding.py`, `omni_v2/agents/stats.py`, `omni_v2/agents/demo_mode.py`, `omni_v2/tools/demo_scenarios.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_demo_mode.py`, `omni_v2/tests/test_onboarding.py`, `omni_v2/tests/test_stats.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, calendar, tasks, contacts, preferences, assistant responses
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Proactive usefulness and annoyance are not measured
  - Demo mode is not fully isolated from normal success claims
  - Stats and time-saved estimates need truthful definitions

### `automation.scheduler` — Scheduled and recurring tasks

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/scheduler.py`
- **Source paths:** `omni_v2/agents/scheduler.py`, `omni_v2/schedule/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_recurring.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** task definitions, triggers, schedules, execution results
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Restart, clock-change, timezone, and long-duration qualification remain incomplete
  - Scheduled effects need the same consent and verification rules as interactive actions

### `automation.triggers` — Automation triggers and webhooks

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/automation/*.py`
- **Source paths:** `omni_v2/automation/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_automation.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** task definitions, triggers, schedules, execution results
- **Network mode:** `required_for_network_trigger`
- **Network destinations:** `configured webhook and trigger destinations`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Authentication and exposure policy need full qualification
  - No stable workflow contract
  - Failure compensation and replay behavior are incomplete

### `automation.away_mode` — Away tasks, remote commands, research, reporting, and messaging

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/away/*.py`
- **Source paths:** `omni_v2/away/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_away_agent.py`, `omni_v2/tests/test_command_channel.py`, `omni_v2/tests/test_messenger.py`, `omni_v2/tests/test_research.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** task definitions, triggers, schedules, execution results
- **Network mode:** `required_for_remote_paths`
- **Network destinations:** `user-configured research URLs`, `messaging provider`, `remote command endpoint`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Remote high-risk autonomy is not qualified
  - External messaging requires robust authentication, consent, and account setup
  - Research depends on network access and source-quality controls

### `automation.geofence` — Geofence rules and location history

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/geofence.py`
- **Source paths:** `omni_v2/agents/geofence.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_geofence.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** task definitions, triggers, schedules, execution results
- **Network mode:** `lan_or_remote_optional`
- **Network destinations:** `paired mobile/backend endpoint`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Location privacy and retention require final policy
  - Mobile-origin authenticity and spoofing controls need qualification
  - No daily-use evidence

### `automation.screen_context` — Screen watcher and activity context

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/screen_watcher.py`
- **Source paths:** `omni_v2/agents/screen_watcher.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_screen_watcher.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** task definitions, triggers, schedules, execution results
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Privacy/consent UX is not release-qualified
  - Classification may be heuristic or backend-dependent
  - No retention and redaction qualification for captured context

### `system.guardian_daemon` — Guardian monitoring, auto-start, and daemon control

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/guardian/*.py`
- **Source paths:** `omni_v2/guardian/*.py`, `omni_v2/daemon/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_guardian.py`, `omni_v2/tests/test_daemon.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** process health, file observations, daemon state, alerts
- **Network mode:** `optional`
- **Network destinations:** `configured remote alert destination`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Cross-platform behavior is uneven
  - Background lifecycle/resource cleanup requires target-machine qualification
  - Monitoring should not overstate protection

### `tools.registry_routing` — Plugin routing and alias map

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/tools/__init__.py`
- **Source paths:** `omni_v2/tools/__init__.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_brain_polish.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, tool arguments/results, approved local files or application state
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Aliases have been marketed as independent tools
  - Loader returns a duplicate SystemTool
  - Unknown actions can route to generic AI output rather than an unavailable result

### `tools.files` — File tools

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/tools/files.py`
- **Source paths:** `omni_v2/tools/files.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, tool arguments/results, approved local files or application state
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Several advertised aliases share generic execution paths
  - Preview, rollback, and effect verification are incomplete
  - Approved-root policy needs full E2E qualification

### `tools.windows_system` — Windows and system controls

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/tools/windows.py`
- **Source paths:** `omni_v2/tools/windows.py`, `omni_v2/tools/system.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `pyautogui`, `Windows platform APIs`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `Windows desktop session`
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, tool arguments/results, approved local files or application state
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Many declared actions return generic text rather than confirmed effects
  - Primary Windows E2E qualification is absent
  - Some exception paths still return successful-looking messages

### `tools.browser` — Browser automation

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/tools/browser.py`
- **Source paths:** `omni_v2/tools/browser.py`, `omni_v2/tools/browser_v3.py`, `omni_v2/tools/browser_playwright.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `Playwright and/or Selenium`, `compatible browser`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `installed browser`
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, tool arguments/results, approved local files or application state
- **Network mode:** `required`
- **Network destinations:** `user-requested websites and search destinations`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Multiple overlapping implementations need consolidation
  - Browser dependencies and binaries are not clean-install qualified
  - Action verification and robust page-state contracts are incomplete

### `tools.desktop_productivity` — VS Code, media, accessibility, and OMNI utility tools

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/tools/vscode.py`
- **Source paths:** `omni_v2/tools/vscode.py`, `omni_v2/tools/media.py`, `omni_v2/tools/accessibility.py`, `omni_v2/tools/omni.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `pyautogui`, `application-specific desktop interfaces`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `supported desktop applications`
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, tool arguments/results, approved local files or application state
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Many action aliases are generic or shallow
  - Real effect verification is incomplete
  - Stable subset has not been selected or qualified

### `tools.ai` — AI chat, summarize, translate, and code routing

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/tools/ai.py`
- **Source paths:** `omni_v2/tools/ai.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** `configured local language model`
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, tool arguments/results, approved local files or application state
- **Network mode:** `optional`
- **Network destinations:** `configured model endpoint when non-local`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Unavailable-model behavior must be truthful
  - Several labels map to one generic handler
  - Quality evaluation for summarize/translate/code tasks is absent

### `integrations.demo_connectors` — Gmail, calendar, smart-home, weather, and timer integration tools

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/tools/integrations.py`
- **Source paths:** `omni_v2/tools/integrations.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** `real service accounts after demo replacement`
- **Hardware:** none recorded
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** canned/demo connector inputs and outputs
- **Network mode:** `demo_only`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - No real account/service integration for several claims
  - Canned calendar and smart-home outputs can be mistaken for real data
  - Setup, tokens, scopes, revocation, and confirmation are not complete

### `notifications.local_mobile` — Notification center, preferences, snooze, and phone delivery

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/agents/notifications.py`
- **Source paths:** `omni_v2/agents/notifications.py`, `omni_v2/agents/notification_prefs.py`, `omni_v2/tools/send_to_phone.py`, `omni_v2/tools/snooze.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `optional WebSocket/push transport`
- **Models:** none recorded
- **Accounts or keys:** `paired device for remote delivery`
- **Hardware:** `notification-capable device`
- **Unit/contract test paths:** `omni_v2/tests/test_notifications.py`, `omni_v2/tests/test_notification_prefs.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** notification content, preferences, subscriptions or device tokens
- **Network mode:** `lan_or_remote_optional`
- **Network destinations:** `paired phone, WebSocket, or push destination`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Durable device-token lifecycle and revocation need qualification
  - Remote/mobile authentication and delivery E2E are incomplete
  - Notification usefulness and annoyance require dogfood evidence

### `voice.capture_stt` — Audio devices, push-to-talk, and speech recognition

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/voice/audio_device.py`
- **Source paths:** `omni_v2/voice/audio_device.py`, `omni_v2/voice/audio_device_v3.py`, `omni_v2/voice/pipeline.py`, `omni_v2/voice/pipeline_v3.py`, `omni_v2/voice/pipeline_v3_fixed.py`, `omni_v2/voice/ptt_manager.py`, `omni_v2/voice/stt_manager.py`, `omni_v2/voice/stt_simple.py`, `omni_v2/voice/test_mic_fixed.py`, `omni_v2/voice/voice_loop.py`, `omni_v2/voice/loop.py`, `omni_v2/voice/__init__.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `sounddevice`, `numpy`, `faster-whisper or selected STT adapter`
- **Models:** `speech-recognition model`
- **Accounts or keys:** none recorded
- **Hardware:** `microphone`
- **Unit/contract test paths:** `omni_v2/tests/test_offline_voice.py`, `omni_v2/tests/test_voice_loop.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** microphone audio, transcripts, voice configuration, generated audio
- **Network mode:** `optional`
- **Network destinations:** `configured remote STT endpoint when selected`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Target microphone/hardware qualification is absent
  - Overlapping pipeline implementations need consolidation
  - Audio retention, cancellation, and degraded-state UX need final validation

### `voice.tts` — Local and online text-to-speech

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/voice/tts_best.py`
- **Source paths:** `omni_v2/voice/tts_best.py`, `omni_v2/voice/tts_simple.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `pyttsx3 or selected local TTS adapter`, `edge-tts only in online mode`
- **Models:** `selected TTS voice/model`
- **Accounts or keys:** none recorded
- **Hardware:** `audio output`
- **Unit/contract test paths:** `omni_v2/tests/test_offline_voice.py`, `omni_v2/tests/test_voice_loop.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** microphone audio, transcripts, voice configuration, generated audio
- **Network mode:** `optional`
- **Network destinations:** `Microsoft Edge TTS service when edge-tts is selected`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Edge TTS is online and privacy claims have not consistently disclosed it
  - A single local default must be qualified
  - Offline mode does not yet prove that online backends are blocked

### `voice.wake_word` — Wake-word detection

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/voice/wake_word.py`
- **Source paths:** `omni_v2/voice/wake_word.py`, `omni_v2/voice/wake_word_best.py`, `omni_v2/voice/wake_word_v3.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `openwakeword or pvporcupine`
- **Models:** `wake-word model`
- **Accounts or keys:** `Porcupine key only when that backend is selected`
- **Hardware:** `microphone`
- **Unit/contract test paths:** `omni_v2/tests/test_offline_voice.py`, `omni_v2/tests/test_voice_loop.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** microphone audio, transcripts, voice configuration, generated audio
- **Network mode:** `optional`
- **Network destinations:** `licensed backend or model download host`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - False-positive and positive-recall measurements are absent
  - Some fallbacks are not true wake-word recognition
  - Always-listening privacy and kill-switch UX are not qualified

### `voice.cloning` — Voice cloning

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/voice/voice_clone.py`
- **Source paths:** `omni_v2/voice/voice_clone.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `audio capture dependencies; training stack is absent`
- **Models:** `no cloned-voice model is implemented`
- **Accounts or keys:** none recorded
- **Hardware:** `microphone`
- **Unit/contract test paths:** `omni_v2/tests/test_voice_clone.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** microphone audio, transcripts, voice configuration, generated audio
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - No real model training
  - No cloned-voice inference artifact
  - Status terminology is misleading
  - Consent and abuse controls are incomplete

### `vision.multimodal` — Screen capture, OCR, and visual-language understanding

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/vision/*.py`
- **Source paths:** `omni_v2/vision/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `Pillow`, `pytesseract`, `opencv`, `optional model adapter`
- **Models:** `optional OCR/VLM model`
- **Accounts or keys:** none recorded
- **Hardware:** `screen or image input`
- **Unit/contract test paths:** `omni_v2/tests/test_vision.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** screenshots/images, OCR text, derived visual output
- **Network mode:** `optional`
- **Network destinations:** `model download host or configured visual-model endpoint`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Several model paths are mock/demo or unqualified
  - No target-hardware benchmark or curated accuracy set
  - Capture consent, retention, and offline guarantees need qualification

### `security.guardrails_execution` — Guardrails and safe execution

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/core/guardrails.py`
- **Source paths:** `omni_v2/core/guardrails.py`, `omni_v2/core/safe_execute.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_security_guardrails.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** commands, paths, policy decisions, audit state, security-specific biometrics or secrets
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Security controls are not yet enforced uniformly through every API and tool path
  - Mutation/adversarial E2E coverage is incomplete
  - Broad successful fallbacks can undermine security semantics

### `security.vault` — Credential vault

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/vault/*.py`
- **Source paths:** `omni_v2/vault/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `cryptography`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `OS-protected key storage not yet integrated`
- **Unit/contract test paths:** `omni_v2/tests/test_vault.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** commands, paths, policy decisions, audit state, security-specific biometrics or secrets
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Cryptography is not correctly declared in the root package
  - OS credential-store integration and key lifecycle need qualification
  - Backup/recovery and multi-profile behavior require release tests

### `security.face_lockdown` — Face authentication, guard monitoring, and lockdown

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/security/*.py`
- **Source paths:** `omni_v2/security/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `opencv-contrib-python or selected verifier`
- **Models:** `optional face-verification model`
- **Accounts or keys:** none recorded
- **Hardware:** `camera`, `target-platform lock capability`
- **Unit/contract test paths:** `omni_v2/tests/test_security.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** commands, paths, policy decisions, audit state, security-specific biometrics or secrets
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - OpenCV contrib dependency is misdeclared
  - Biometric accuracy, spoof resistance, and hardware behavior are not qualified
  - Security-sensitive fallbacks require explicit policy

### `skills.sdk_registry` — Skill SDK and local registry

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/sdk/*.py`
- **Source paths:** `omni_v2/sdk/*.py`, `omni_v2/skills/registry.py`, `omni_v2/skills/__init__.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_skill_synthesis.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** skill source, package metadata, permissions, verification/install state
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Compatibility contract is not release-stable
  - Permission model and isolation are incomplete
  - No supported third-party ecosystem

### `skills.marketplace_install` — Skill marketplace and installer

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/skills/marketplace.py`
- **Source paths:** `omni_v2/skills/marketplace.py`, `omni_v2/skills/installer.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `HTTP/archive/install tooling`
- **Models:** none recorded
- **Accounts or keys:** `marketplace service is not established`
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_marketplace.py`, `omni_v2/tests/test_skill_installer.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** skill source, package metadata, permissions, verification/install state
- **Network mode:** `required`
- **Network destinations:** `configured marketplace/package hosts`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Publisher authenticity/signatures are missing
  - Supply-chain trust and rollback require qualification
  - Marketplace content and network service are not established

### `skills.generation` — Dynamic skill generation

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/skills/generator.py`
- **Source paths:** `omni_v2/skills/generator.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** `configured language model`
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_skill_synthesis.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** skill source, package metadata, permissions, verification/install state
- **Network mode:** `optional`
- **Network destinations:** `configured model endpoint when non-local`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Generated code is untrusted
  - No safe automatic promotion path
  - Practical quality and value are not measured

### `skills.sandbox_verification` — Skill sandbox and verification

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/skills/sandbox.py`
- **Source paths:** `omni_v2/skills/sandbox.py`, `omni_v2/skills/verifier.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_sandbox.py`, `omni_v2/tests/test_skill_verify.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** skill source, package metadata, permissions, verification/install state
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Process sandbox is not a complete security boundary
  - OS/resource/network isolation needs stronger guarantees
  - Malicious-package E2E testing is incomplete

### `api.fastapi` — FastAPI HTTP and WebSocket surface

- **Owner:** `personal_repository_owner`
- **Entry points:** `backend_fastapi/*.py`
- **Source paths:** `backend_fastapi/*.py`, `backend_fastapi/core/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `fastapi`, `uvicorn`, `WebSocket dependencies`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_mobile.py`, `omni_v2/tests/test_geofence.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** requests, responses, WebSocket events, authentication/session state
- **Network mode:** `lan_optional`
- **Network destinations:** `configured API clients`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Authentication is optional by default
  - Thirty-three live API checks skip without a manually running service
  - Status/error contracts and route ownership are not fully audited
  - Main module is approximately 2871 lines

### `ui.next_web` — Next.js web interface

- **Owner:** `personal_repository_owner`
- **Entry points:** `frontend_next/app/*.js`
- **Source paths:** `frontend_next/app/*.js`, `frontend_next/app/**/*.js`, `frontend_next/app/*.css`, `frontend_next/components/*.js`, `frontend_next/next.config.js`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `packages locked by frontend_next/package-lock.json`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `modern browser`
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** commands, responses, connection state, displayed personal data
- **Network mode:** `lan_optional`
- **Network destinations:** `OMNI backend`, `Google Fonts under current styling`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Large monolithic client page
  - Hard-coded localhost backend/WebSocket assumptions
  - Successful mock execute fallback
  - Lint is unconfigured
  - Dependency audit has critical/high findings

### `ui.desktop` — Desktop HUD, tray, dashboard, and voice UI variants

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/ui/*.py`
- **Source paths:** `omni_v2/ui/*.py`, `omni_v2/ui/*.html`, `omni_v2/gui/*.py`, `omni_v2/web_ui/*.html`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `selected Tkinter/PySide/desktop GUI stack`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `desktop session`
- **Unit/contract test paths:** `omni_v2/tests/test_desktop.py`, `omni_v2/tests/test_gui_agent.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** commands, responses, connection state, displayed personal data
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Overlapping interfaces have no declared canonical desktop UI
  - Cross-platform and accessibility behavior is unqualified
  - Packaging does not reliably ship/run the interfaces

### `mobile.pwa` — Mobile PWA companion

- **Owner:** `personal_repository_owner`
- **Entry points:** `mobile/*.js`
- **Source paths:** `mobile/*.js`, `mobile/*.html`, `mobile/*.css`, `mobile/*.json`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `modern mobile browser`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `phone or mobile browser`
- **Unit/contract test paths:** `omni_v2/tests/test_mobile.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** pairing data, commands, voice/location input, notifications
- **Network mode:** `lan_optional`
- **Network destinations:** `paired OMNI backend`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Remote/LAN threat model and durable authentication need closure
  - Phone/browser E2E qualification is absent
  - Offline shell does not imply offline assistant functionality

### `network.discovery_pairing` — LAN discovery, pairing, and mobile transport

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/network/*.py`
- **Source paths:** `omni_v2/network/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `optional mDNS/network adapters`
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** `LAN interface`
- **Unit/contract test paths:** `omni_v2/tests/test_network.py`, `omni_v2/tests/test_mobile.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`, `hardware`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** device identity, LAN addresses, pairing tokens, transport messages
- **Network mode:** `lan`
- **Network destinations:** `local mDNS/UDP/WebSocket peers`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Remote mode is not secure-by-default
  - Durable tokens/revocation and replay resistance require full E2E tests
  - Network exposure and host/origin policy need hardening

### `sync.e2e` — End-to-end encrypted sync

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/sync/*.py`
- **Source paths:** `omni_v2/sync/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner state selected for synchronization, node/transport metadata
- **Network mode:** `none_active`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - No transport
  - No key lifecycle
  - No conflict resolution
  - No cross-device persistence or recovery

### `sync.mesh` — Mesh state synchronization

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/mesh/*.py`
- **Source paths:** `omni_v2/mesh/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_mesh.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner state selected for synchronization, node/transport metadata
- **Network mode:** `lan_optional`
- **Network destinations:** `configured mesh peers`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Not a qualified secure cross-device sync product
  - Consistency, identity, transport, conflicts, and threat model remain incomplete

### `interop.mcp` — Model Context Protocol bridge

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/mcp/*.py`
- **Source paths:** `omni_v2/mcp/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** `real MCP adapter dependency not selected`
- **Models:** none recorded
- **Accounts or keys:** `configured MCP server after qualification`
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_mcp.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** tool schemas, tool arguments/results, provider metadata
- **Network mode:** `optional`
- **Network destinations:** `configured MCP server`
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_qualified` over all declared actions and routes in mapped source paths; evidence: none recorded
- **Known gaps:**
  - Real server interoperability is not qualified
  - Permission and trust boundaries need design
  - Fake provider must not be represented as live integration

### `data.backup` — Backup and restore

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/backup/*.py`
- **Source paths:** `omni_v2/backup/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_history_photos_backup.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** local application state, backup manifests, restored data
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Not all current stores have proven inclusion and consistency
  - Restore is not part of a release qualification flow
  - Encryption and retention policy need final decisions

### `files.natural_language` — Natural-language local file management

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/files/*.py`
- **Source paths:** `omni_v2/files/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_nlfiles_remote.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner command, approved paths, file metadata/content, operation history
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Must be consolidated with FilesTool
  - Destructive action consent and rollback need qualification
  - Ambiguous intent handling requires adversarial tests

### `evaluation.benchmarks` — Benchmarks and leaderboard

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/benchmark/*.py`
- **Source paths:** `omni_v2/benchmark/*.py`, `omni_v2/leaderboard/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** none recorded
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** `omni_v2/tests/test_benchmark.py`, `omni_v2/tests/test_wake_leaderboard.py`
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** benchmark cases, timings, scores, leaderboard records
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Benchmarks do not yet represent the ten locked owner workflows
  - Performance claims are not generated from target hardware qualification

### `personal.pda_shell` — Personal digital assistant shell

- **Owner:** `personal_repository_owner`
- **Entry points:** `omni_v2/pda/*.py`
- **Source paths:** `omni_v2/pda/*.py`
- **Requirements audit:** `known_subset_dependency_closure_in_B01`
- **Known packages:** none recorded
- **Models:** `configured language model`
- **Accounts or keys:** none recorded
- **Hardware:** none recorded
- **Unit/contract test paths:** none recorded
- **Integration test paths:** none recorded
- **End-to-end test paths:** none recorded
- **Hardware test paths:** none recorded
- **Required test types before stable:** `unit_or_contract`, `integration`, `end_to_end`
- **Test qualification:** `not_qualified` — Mapped files are presence only; skips, mocks, and broad baseline failures prevent a release claim.
- **Verified platforms:** none recorded
- **Platform note:** No release-qualified platform evidence exists at B00; target-platform qualification is scheduled in B13.
- **Data accessed:** owner commands, calendar, tasks, contacts, preferences, assistant responses
- **Network mode:** `none_expected`
- **Network destinations:** none recorded
- **Privacy qualification:** `not_qualified`
- **Network disclosure:** Inventory only: destination enforcement, consent, offline no-egress, and exact privacy behavior remain unqualified until B08/B11.
- **Tool/API interface audit:** `not_applicable` over not_applicable; evidence: none recorded
- **Known gaps:**
  - Overlaps the main application and backend
  - No declared canonical runtime
  - Installation and daily-use path are unqualified
