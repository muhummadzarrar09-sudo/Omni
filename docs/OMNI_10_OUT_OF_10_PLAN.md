# OMNI 10/10 Recovery, Mastery, and Expansion Plan

**Plan version:** 1.0  
**Created:** 2026-08-11  
**Target:** OMNI as an exceptional personal, local-first assistant  
**Rule:** Earn the 10/10 foundation first; stack additional capabilities only after the foundation is frozen and verified.

---

## 1. Mission

Turn OMNI from a broad, ambitious prototype into a dependable personal daily driver that:

1. Installs correctly from a fresh checkout.
2. Starts reliably with one supported command.
3. Never presents mocks, canned data, or unavailable operations as successful real work.
4. Performs a deliberately selected set of personal-assistant workflows extremely well.
5. Protects personal data and dangerous actions by default.
6. Is maintainable enough that adding the next feature does not destabilize existing behavior.
7. Proves its quality through repeatable automated tests and a 30-day personal dogfood period.
8. Describes itself exactly as it behaves—no inflated counts or absolute claims without evidence.

This is a **quality-first plan**, not a line-count or feature-count plan.

---

## 2. What “10/10” Means

A literal perfect system does not exist. In this plan, **10/10 means every declared requirement for the chosen scope is met, measured, and reproducible**. A capability outside the declared stable scope can be experimental without lowering the stable product score, but it must be labeled experimental and may not claim success when unavailable.

A category reaches 10 only when:

- Its objective exit criteria are met.
- Evidence is produced automatically where possible.
- The evidence works from a fresh machine, not only the development checkout.
- Failures are visible and truthful.
- The result survives the 30-day dogfood gate.

No category receives a 10 based on code volume, route count, test count, UI polish, or documentation claims alone.

---

## 3. Scope Decision: Personal Build vs. Commercial Product

### 3.1 Primary target: 10/10 personal build

The primary target is a **single-owner personal assistant**, optimized first for the owner’s real hardware, operating system, accounts, routines, and privacy expectations.

For this target:

- Personal utility replaces market traction as a core score.
- One deeply supported operating system is better than three falsely supported systems.
- Integrations only need to support services the owner actually uses.
- Cloud features are optional and must be explicitly enabled.
- Reliability, privacy, recovery, and daily usefulness matter more than public popularity.

### 3.2 Optional commercial track

Commercial defensibility cannot honestly score 10 without users, retention, support, distribution, and some advantage that is not freely copied from the public MIT repository. That track is documented separately in Phase 10 and is **not required for the personal-build 10/10 release**.

The project must never relabel “not commercially evaluated” as “10/10 commercial traction.” It should be shown as **N/A for personal scope** until the commercial track is deliberately activated.

---

## 4. Current Verified Baseline

The plan begins from evidence gathered on 2026-08-11:

### Strengths

- Approximately 36,600 active production Python lines.
- Approximately 10,300 Python test lines.
- 183 non-test Python files.
- 190 FastAPI route decorators.
- Active Python sources compile successfully.
- Next.js production build succeeds and generates 25 routes.
- Latest manually repaired test environment: **663 passed, 1 failed, 33 skipped**.

### Release blockers

- The declared full Python environment does not resolve on Python 3.11 because of an invalid `numpy>=2.5.1` requirement.
- Required capabilities use undeclared or incorrectly declared dependencies, including OpenCV contrib functionality and cryptography.
- Built wheel omits almost all `omni_v2` subpackages.
- `start.sh` references a missing root `install.sh`, while the actual script is under `scripts/`.
- Frontend linting is not configured and enters an interactive setup prompt.
- Frontend dependency audit reports 1 critical and 10 high vulnerabilities.
- There is no repository CI workflow.
- One calendar test depends on the wall clock and currently fails after its fixed event time.
- Thirty-three backend API checks skip unless a live server is manually running.
- API authentication is optional by default.
- Browser-facing code hard-codes `localhost:8765`.
- Some unavailable paths report successful mock or demo results.
- Voice cloning reports a voice as ready without training a real model.
- Sync is an explicit stub.
- Several vision paths can use mock/demo behavior.
- “100+ tools” is largely an alias count; the loader currently returns 16 plugin objects, including a duplicate system plugin.
- Documentation contains stale counts, missing paths, unsupported absolute privacy statements, and completed-feature claims that conflict with implementation.

This baseline is the starting line. The score rises only when these items are closed with evidence.

---

## 5. Non-Negotiable Operating Rules

### Rule 1: Foundation freeze

Until Phases 0–3 pass, do not add new headline capabilities. Bug fixes, tests, packaging, observability, and refactors are allowed. New feature ideas go to the post-10 backlog.

### Rule 2: No fake success

Every operation must return exactly one of:

- `success`: the requested effect was performed and, where possible, verified.
- `partial`: part of the effect occurred, with the incomplete portion identified.
- `unavailable`: dependency, model, account, device, or service is not configured.
- `denied`: policy or user consent blocked the action.
- `failed`: execution was attempted and failed, with a safe diagnostic.
- `demo`: canned behavior intentionally requested by the user in demo mode.

A fallback may not return `success` unless it really completed the requested effect.

### Rule 3: Stable, beta, and experimental are separate

Every capability receives one lifecycle label:

- **Stable:** all quality gates pass; included in normal claims.
- **Beta:** functional but missing at least one non-safety quality gate.
- **Experimental:** may change or be incomplete; off by default.
- **Unavailable:** known concept with no functional implementation.
- **Removed:** no longer exposed.

### Rule 4: Supported platforms are explicit

Choose the initial primary target—recommended: the owner’s Windows 11 machine—and test it deeply. Linux may be supported for development/backend operation only until an end-to-end platform run passes. macOS must not be claimed until tested.

### Rule 5: Claims are generated from evidence

Endpoint counts, tool counts, test outcomes, supported platforms, model requirements, and privacy behavior should be generated or validated in CI. They must not be hand-maintained marketing numbers.

### Rule 6: No skipped release evidence

Tests that require a backend, browser, model, microphone, GPU, or OS are allowed to live in separate suites. The required release jobs for the declared stable scope must run; they may not silently skip.

### Rule 7: Every feature includes its failure path

A feature is not done until it has:

- Success behavior.
- Unavailable behavior.
- Failure behavior.
- Cancellation and timeout behavior.
- Security/privacy review.
- Automated tests.
- User-facing status and recovery instructions.

### Rule 8: New work cannot lower existing gates

After the 10/10 foundation is reached, every additional change must preserve all gates. If a gate regresses, expansion stops until it is restored.

---

## 6. 10/10 Category Scorecard

| Category | Current estimate | 10/10 exit standard |
|---|---:|---|
| Product vision | 7.5 | One clear personal-assistant promise, stable scope, explicit non-goals, and measurable daily workflows |
| Implementation breadth | 6.5 | Every advertised stable capability has a real implementation, capability probe, tests, and truthful failure behavior |
| Automated quality | 6.0 | Green unit, integration, contract, E2E, package, and required platform suites with no required skips |
| User experience | 5.5 | Fresh install to first successful task is guided, accessible, understandable, and recoverable |
| Feature authenticity | 3.5 | No mock success; demo data isolated; stable features prove real effects |
| Architecture/maintainability | 3.5 | Modular backend/frontend, typed contracts, bounded complexity, documented ownership, and safe migrations |
| Installation/packaging | 1.5 | Fresh-checkout installation, wheel/sdist installation, startup, upgrade, and uninstall all pass automatically |
| Security/privacy | 2.5 | Secure network defaults, consent gates, no high/critical known dependency issues, enforceable offline mode, threat-model tests |
| Documentation accuracy | 2.0 | Docs generated/verified against runtime and independently reproducible |
| Personal utility/reliability | Not measured | 30 consecutive days of real use with target success, startup, latency, and data-integrity SLOs |
| Commercial defensibility | 0.5 | Optional track only: adoption, retention, revenue/distribution, support, and defensible assets |

---

# PART I — EARN THE FOUNDATION

## Phase 0 — Truth Reset and Scope Lock

**Priority:** P0  
**Estimated effort:** 2–4 focused days  
**Goal:** Establish a single truthful source of product status before changing implementation.

### Q0-01: Define the stable personal core

Create a capability inventory and place each capability in a tier.

#### Recommended Stable Core

1. Local text conversation with model capability detection.
2. Safe file listing, reading, writing, searching, and creating.
3. Safe app launching and basic window control on the declared primary OS.
4. Browser navigation/search with isolated profile.
5. Persistent profile and memory with inspect/export/delete controls.
6. Calendar/tasks/reminders using real local data.
7. Push-to-talk STT and one verified local TTS backend.
8. Wake word, only if false-positive and privacy gates pass.
9. Backend, web UI, health/status diagnostics, and audit history.
10. Scheduler/proactive notices with user-configured quiet hours.

#### Beta/Experimental until proven

- Voice cloning.
- Autonomous skill synthesis.
- Marketplace installs.
- Multimodal local vision models.
- Mobile companion.
- Multi-device sync.
- Smart-home control.
- Gmail/account integrations.
- Fully autonomous code editing/committing.

For each feature, record:

- Lifecycle status.
- Implementation entry point.
- Required dependencies/models/accounts.
- Whether it performs real work.
- Whether it has unit, integration, E2E, and hardware tests.
- Platforms verified.
- Known limitations.
- Data accessed and network destinations.

### Q0-02: Establish a living quality scorecard

Create machine-readable status data, for example `quality/capabilities.yaml`, and generate a Markdown summary from it. CI must reject:

- Stable capability without an owner/module.
- Stable capability without tests.
- Stable network capability without privacy disclosure.
- Claimed tool or endpoint with no implementation.
- `mock` or `demo` result represented as stable success.

### Q0-03: Record an executable baseline

Add one script that captures:

- Python and Node versions.
- Dependency resolution result.
- Wheel contents.
- Python test counts and skips.
- Backend live-test result.
- Frontend lint/test/build result.
- Dependency audit summary.
- Generated endpoint and tool inventory.

Write results to ignored local artifacts and publish a concise CI summary.

### Q0-04: Correct top-level claims immediately

Before feature work resumes:

- Replace “10/10 achieved” with the current release status.
- Remove “100+ tools” unless the definition and verified inventory justify it.
- Replace absolute “no data ever leaves the machine” language with an explicit offline/online matrix.
- Mark voice cloning, sync, mock vision, and demo integrations accurately.
- Update test/module/endpoint numbers or generate them.
- Correct installer paths and supported-platform language.

### Phase 0 exit gate

- [ ] Stable core is explicitly approved.
- [ ] Every current capability has a lifecycle label.
- [ ] README has no known false completion claim.
- [ ] Baseline script runs from one command.
- [ ] Feature freeze and post-10 backlog are recorded.

---

## Phase 1 — Reproducible Installation, Packaging, and Startup

**Priority:** P0  
**Estimated effort:** 1–3 weeks  
**Goal:** A fresh checkout becomes a working application without hand repair.

### Q1-01: Rebuild Python dependency strategy

Refactor `pyproject.toml` into clear layers:

- `core`: small dependency set required by every installation.
- `api`: FastAPI server.
- `brain`: local model runtime.
- `voice-local`: offline STT/TTS.
- `voice-online`: network TTS, clearly opt-in.
- `vision`: correct OpenCV contrib and OCR/model dependencies.
- `browser`: Playwright and browser binaries.
- `memory`: selected storage backend, avoiding several heavy alternatives by default.
- `integrations`: account/network connectors.
- `dev`: pinned quality and test tooling.
- `all`: a tested union, not a recursive self-reference that has never been resolved.

Actions:

1. Replace future/nonexistent minimum versions with available, tested constraints.
2. Remove duplicate dependencies.
3. Add missing cryptography requirement where needed.
4. Replace ordinary OpenCV with the exact variant required by face authentication, or redesign face authentication not to require contrib by default.
5. Decide whether Python 3.10, 3.11, 3.12, and 3.13 are supported based on actual dependency resolution.
6. Produce lock/constraints files for each supported platform and installation profile.
7. Add a dependency-update process that opens updates individually and runs full gates.

### Q1-02: Fix package discovery and contents

Replace the explicit two-package setuptools list with correct package discovery. Validate both wheel and sdist.

Required automated checks:

1. Build wheel and sdist in an isolated environment.
2. Assert all intended `omni_v2` subpackages are present.
3. Install the wheel into a brand-new environment outside the repository.
4. Run `omni --help`, `omni status`, package imports, and a minimal backend smoke test from that environment.
5. Assert runtime data, tests, local databases, secrets, caches, and models are not included accidentally.
6. Verify `pip check` returns clean.

### Q1-03: Make installers thin and reliable

Use one Python bootstrap/install implementation with thin wrappers:

- `scripts/install.sh`
- `scripts/install.ps1`
- `install.bat`
- `start.sh`
- `start.bat`

Fix `start.sh` to call the real installer path. Installers must:

- Detect an unsupported Python version before modifying the system.
- Create a local environment.
- Install a selected profile.
- Check disk space before model/browser downloads.
- Verify checksums for downloaded models.
- Explain online downloads before performing them.
- Resume interrupted downloads safely.
- Print actionable failure diagnostics.
- Be idempotent.

Do not silently swallow Playwright installation failure.

### Q1-04: Centralize configuration

Add a typed configuration layer and a safe `.env.example` or generated config template containing:

- Bind host and port.
- Frontend/backend public origin.
- API token mode.
- Offline mode.
- Enabled model backends.
- Data and model directories.
- Log level and retention.
- Integration opt-ins.
- Consent policy.

Browser code must use relative URLs or one public runtime configuration source. It must not hard-code `localhost`.

### Q1-05: Frontend reproducibility

- Configure ESLint non-interactively.
- Add formatting and type checking.
- Upgrade vulnerable packages to tested, supported versions.
- Commit a deterministic lockfile.
- Make `npm ci`, lint, typecheck, tests, and production build all pass.
- Avoid build-time dependence on Google Fonts or other external hosts; self-host or include a local fallback.

### Q1-06: Add clean-install CI

CI jobs must test:

- Source editable install for development.
- Wheel install for users.
- Minimal/core profile.
- Stable personal profile.
- Full profile if still advertised.
- Windows primary target.
- Linux only to the level explicitly claimed.

### Phase 1 exit gate

- [ ] `pip install .` succeeds on every declared Python/OS pair.
- [ ] `pip install .[all]` succeeds if `[all]` remains advertised.
- [ ] Built wheel contains all intended packages.
- [ ] Fresh wheel environment passes smoke tests.
- [ ] `npm ci`, lint, typecheck, tests, audit policy, and build pass non-interactively.
- [ ] One-click startup succeeds twice consecutively on a fresh primary machine.
- [ ] No hard-coded browser-facing backend host remains.
- [ ] Install and startup failures are actionable and leave no corrupted state.

---

## Phase 2 — Testing and Continuous Verification

**Priority:** P0  
**Estimated effort:** 2–4 weeks  
**Goal:** Convert the large test collection into release evidence.

### Q2-01: Define test layers

Use explicit pytest markers and separate commands:

- `unit`: pure and fast, no network/hardware/processes.
- `integration`: storage, real module composition, temporary filesystem.
- `api`: live FastAPI server and real HTTP/WebSocket calls.
- `e2e`: backend + frontend + browser user flows.
- `platform`: OS automation.
- `hardware`: microphone, speaker, camera, GPU, wake word.
- `model`: real local model inference.
- `offline`: verifies prohibited network access.
- `security`: abuse and policy tests.

Every skip must include a reason. Required release jobs run their target suite with a policy that fails on unexpected skips.

### Q2-02: Eliminate brittle tests

- Replace the fixed-date calendar event with a generated future event or freeze the clock.
- Remove dependence on local timezone unless the test explicitly validates timezone behavior.
- Use temporary paths for all state.
- Ban order-dependent tests.
- Add deterministic random seeds where randomness is not under test.
- Make async cleanup strict so no server, task, socket, or thread leaks between tests.

### Q2-03: Make API tests real

Start the backend in the API test fixture and wait for health readiness. Test:

- Every stable HTTP route.
- Every stable WebSocket message type.
- Authentication required/optional modes.
- Validation and status codes.
- Payload size/time/rate boundaries.
- Cancellation and disconnect cleanup.
- OpenAPI schema stability.
- Error envelope consistency.

No “backend not running, skip” behavior is allowed in the release API job.

### Q2-04: Add frontend tests

Introduce:

- Component tests for status, errors, consent, onboarding, settings, memory, and tool cards.
- Contract tests generated from the backend schema or shared typed client.
- Playwright E2E tests for installation/onboarding, text command, tool execution, unavailable model, offline mode, settings, and shutdown/restart.
- Accessibility checks using automated tooling plus a manual keyboard/screen-reader checklist.
- Visual regression snapshots for primary screens at supported resolutions.

### Q2-05: Add package and migration tests

Test:

- New empty data directory.
- Upgrade from each retained data schema version.
- Corrupt/partial JSON and database recovery.
- Backup and restore.
- Concurrent writes from expected processes.
- Downgrade behavior or a clear refusal when downgrade is unsafe.
- Uninstall without deleting personal data unless explicitly requested.

### Q2-06: Quality thresholds

Initial targets, raised gradually rather than gamed:

- Stable core branch coverage: at least 85%.
- Security/permission/storage modules: at least 95% branch coverage.
- Overall meaningful coverage: at least 75%.
- Mutation testing on guardrails, consent, path restrictions, token checks, and result-state logic.
- Zero flaky failures over 20 repeated unit/integration runs.
- Zero warnings unless allowlisted with an owner and expiry date.

Coverage does not make weak assertions acceptable. Tests must prove effects, not only that functions return truthy values.

### Q2-07: CI pipeline

Required checks on every change:

1. Python lint and formatting.
2. Python type checking for stable core.
3. Unit tests across supported Python versions.
4. Integration/API tests on the primary version.
5. Wheel/sdist build and installed-wheel smoke tests.
6. Frontend lint, typecheck, tests, and build.
7. Dependency and secret scanning.
8. Generated-doc drift check.
9. Capability-matrix consistency.
10. Primary E2E smoke test.

Nightly or scheduled checks:

- Full model suite.
- Browser suite.
- Hardware suite on the owner’s machine/self-hosted runner.
- Dependency audit.
- Repeated flaky-test detection.
- Performance regression suite.

### Phase 2 exit gate

- [ ] Required unit/integration/API suites are green with zero unexpected skips.
- [ ] Backend live tests start automatically.
- [ ] Frontend has real component and E2E coverage.
- [ ] Package install and schema migrations are tested.
- [ ] Security-critical code meets the high branch-coverage target.
- [ ] Twenty consecutive required-suite runs contain no flaky failures.
- [ ] CI is required before declaring a release candidate.

---

## Phase 3 — Architecture and Maintainability

**Priority:** P1, but required before feature completion  
**Estimated effort:** 4–8 weeks  
**Goal:** Make the system understandable, testable, and safe to extend.

### Q3-01: Decompose the backend

Reduce `backend_fastapi/main.py` to application composition, lifespan, middleware, and router mounting.

Recommended structure:

```text
backend_fastapi/
  app.py
  config.py
  dependencies.py
  lifespan.py
  errors.py
  middleware/
  routers/
  schemas/
  services/
  repositories/
```

Rules:

- Routers translate HTTP to typed service calls.
- Services contain use-case logic.
- Repositories own persistence.
- Hardware/model/network adapters implement explicit interfaces.
- Dependency injection selects real, unavailable, or test implementations.
- A demo adapter can only be selected in explicit demo mode.

Target: composition file under roughly 300 lines, with domain routers/services small enough to review independently.

### Q3-02: Decompose the frontend

Split the large `frontend_next/app/page.js` into:

- Typed API client.
- WebSocket client with reconnect state machine.
- State stores/hooks.
- Layout components.
- Conversation components.
- Tool execution components.
- Settings/privacy components.
- Memory/history components.
- Voice components.
- Error and degraded-mode components.

Prefer TypeScript for new stable frontend code and migrate touched code incrementally. UI components must not know raw backend URLs or invent backend result states.

### Q3-03: Introduce one capability registry

Create one canonical registry with:

- Capability/tool ID.
- Display name.
- Description.
- Input/output schema.
- Risk level.
- Required consent.
- Required dependency/model/account.
- Supported platform.
- Availability probe.
- Execute function.
- Verification function.
- Lifecycle status.

Aliases remain aliases and are not counted as independent tools. Runtime and docs both read from this registry.

### Q3-04: Standardize execution results

Use one result model across plugins, brain, backend, WebSocket, and frontend. Include:

- State (`success`, `partial`, `unavailable`, `denied`, `failed`, `demo`).
- User-safe message.
- Machine error code.
- Details safe for logs.
- Effect/verification evidence.
- Retryability.
- Recovery action.
- Duration and correlation ID.

Remove code that catches exceptions and returns `ok(...)` merely to keep the demo moving.

### Q3-05: Untangle brain and tool execution

Separate:

1. Intent interpretation.
2. Planning.
3. Policy/consent.
4. Tool dispatch.
5. Observation.
6. Verification.
7. Retry/recovery.
8. User response.
9. Memory write.

The LLM may propose actions; it may not bypass policy or mark an effect successful. Verification comes from the tool/adaptor layer.

### Q3-06: Storage architecture

Inventory every JSON, SQLite, DuckDB, Chroma, Lance, and filesystem store. For each:

- Declare the authoritative store.
- Add schema versioning and migrations.
- Use atomic writes.
- Add process/thread locking where multiple writers are possible.
- Define backup/restore.
- Define retention and deletion.
- Define encryption needs.
- Test abrupt termination and corruption recovery.

Consolidate overlapping stores where they solve the same problem.

### Q3-07: Code-quality enforcement

- Ruff rules agreed and enforced.
- Formatting enforced.
- Mypy/pyright strictness increased module by module.
- No bare `except` in stable code.
- Broad exceptions must add context and preserve failure state.
- No new stable module above an agreed size limit without a written exception.
- Complexity hotspots tracked and reduced.
- Dead and duplicate implementations removed after migration.
- `_archive` remains excluded from product execution and metrics.

### Q3-08: Observability

Implement structured, privacy-aware logs with:

- Correlation/session IDs.
- Action lifecycle.
- Capability availability changes.
- Model timings.
- Tool timings and verification.
- Startup diagnostics.
- Redaction of tokens, message bodies, voice transcripts, and personal paths by default.
- Bounded log retention and user-controlled deletion/export.

### Phase 3 exit gate

- [ ] Backend composition is modular and monolith responsibilities are extracted.
- [ ] Frontend page is decomposed into tested components and clients.
- [ ] One canonical capability registry drives runtime and docs.
- [ ] One truthful result-state model reaches the UI.
- [ ] LLM planning cannot bypass policy or verification.
- [ ] Stores have explicit locking, migration, recovery, and retention behavior.
- [ ] Stable core passes lint/type/complexity policy with no unexplained exceptions.

---

# PART II — MAKE EVERY STABLE CAPABILITY REAL

## Phase 4 — Feature Authenticity and Core Capability Excellence

**Priority:** P1  
**Estimated effort:** 6–16 weeks depending on final stable scope  
**Goal:** Replace broad claims with a smaller set of deeply reliable capabilities.

### Q4-01: Eliminate mock-success behavior

Search for mock, stub, placeholder, demo, fallback, fake, canned, and “would execute.” Review each occurrence manually.

Required remediation:

- Backend unavailable → `unavailable`, never successful mock execution.
- Model unavailable → explicit regex/basic mode, with visible limits.
- Integration unconfigured → setup prompt, not canned calendar/email/home data.
- System effect unverified → `partial` or `failed`, not success.
- Demo responses → only inside explicit demo mode with visible DEMO labeling.
- Exceptions → preserve correct result state and diagnostic.

Add a CI check for newly introduced mock-success patterns, with explicit allowlisting only under demo/test modules.

### Q4-02: Tool quality contract

A stable tool must have:

1. Unique canonical ID and schema.
2. Clear examples and unsupported cases.
3. Availability probe.
4. Risk classification.
5. Consent requirement.
6. Deterministic execution interface.
7. Effect verification where technically possible.
8. Timeout/cancellation.
9. Unit and integration tests.
10. Primary-platform E2E test.
11. Audit event.
12. Documentation generated from metadata.

Do not target “100 tools.” Target **20–30 tools that work extremely well**, then expand deliberately.

### Q4-03: Core workflow scorecard

Define at least ten owner workflows. Recommended examples:

1. Ask for a daily briefing using real calendar/tasks.
2. Add, update, and cancel a reminder.
3. Find and summarize a local document.
4. Create a file in an approved workspace and confirm contents.
5. Open and search the browser in the isolated profile.
6. Launch/focus/close an approved application.
7. Start a focus session and suppress noncritical notifications.
8. Ask what was done yesterday and retrieve accurate memory.
9. Use push-to-talk to run a task and hear a local spoken response.
10. Recover cleanly when the model, browser, or microphone is unavailable.

For each workflow define:

- Starting state.
- Exact steps.
- Expected effect.
- Verification method.
- Maximum acceptable latency.
- Failure/recovery behavior.
- Data/network behavior.
- Automated test coverage.
- Manual hardware run procedure.

Run every workflow at least 20 times before release. Stable target: at least 95% successful completion, with no unsafe false success.

### Q4-04: Local LLM and reasoning quality

- Support a clearly documented primary model and one fallback.
- Probe model availability and hardware fit at startup.
- Measure first-token latency, generation rate, memory use, and tool-call validity.
- Use structured tool schemas rather than fragile free-form JSON extraction where the model/runtime supports it.
- Validate every proposed tool and argument before execution.
- Bound planning depth, execution time, and retries.
- Add golden command sets and adversarial prompts.
- Distinguish conversation-only answers from action requests.
- Never expose private chain-of-thought; show concise plans, action state, and user-safe rationale instead.

### Q4-05: Memory and personalization

- Make stored memories inspectable, editable, exportable, and deletable.
- Store provenance and timestamps.
- Separate user facts from model inference.
- Ask before persisting sensitive inferred facts.
- Add TTL/retention options.
- Prevent one user/profile from reading another profile’s data.
- Evaluate retrieval precision on an owner-created question set.
- Prevent stale or low-confidence memory from being stated as fact.
- Test backup, restore, migration, corruption, and concurrent use.

### Q4-06: Voice

Stable voice scope should initially include:

- Device selection and test.
- Push-to-talk STT.
- One fully local TTS option.
- Cancellation/barge-in.
- Clear microphone state.
- Offline enforcement.

Wake word becomes stable only after measured tests on the owner’s actual environment:

- At least 100 positive utterances across distance/noise conditions.
- At least eight hours of background audio for false activation measurement.
- Configurable sensitivity and a visible always-listening indicator.
- Immediate kill switch.
- No raw audio retention by default.

Voice cloning must either:

- Train/use a real local model, produce a usable voice artifact, document time/hardware/quality, and pass a sample-based E2E test; or
- Be renamed to “voice sample/profile setup” and remain experimental.

Metadata creation alone is not voice cloning.

### Q4-07: Vision

A stable vision capability must:

- Use a real selected model or OCR pipeline.
- Report which backend produced the answer.
- Handle model absence honestly.
- Enforce capture/path permissions.
- Avoid silently uploading images.
- Pass a curated image/screenshot benchmark with expected answer criteria.
- Measure latency and GPU/RAM requirements on target hardware.

Mock scene descriptions remain demo-only.

### Q4-08: Integrations

Only stabilize integrations the owner actually uses. For each:

- Real OAuth/token setup or local API configuration.
- Least required permissions.
- Secure token storage and revocation.
- Read vs. write scopes separated.
- Confirmation for externally visible writes.
- Rate-limit and offline handling.
- Test account or sandbox integration tests.
- Clear deletion/disconnect behavior.

Canned Gmail, calendar, smart-home, and weather responses must not appear in normal mode.

### Q4-09: Sync, marketplace, and synthesis

These remain experimental until all of the following exist:

- Sync: real encrypted transport, key management, conflict resolution, revocation, replay protection, recovery, and cross-device tests.
- Marketplace: publisher identity, signed artifacts, hashes, permission manifest, sandboxing, rollback, update policy, and malicious-skill tests.
- Skill synthesis: generated code is untrusted, statically checked, sandboxed, permission-scoped, reviewed before activation, and never auto-promoted to stable.

Removing or honestly deferring these features is preferable to shallow completion.

### Phase 4 exit gate

- [ ] No stable path reports a mock/demo as real success.
- [ ] Each stable tool meets the tool quality contract.
- [ ] Ten core workflows meet the repeated success target.
- [ ] Model/tool errors are visible and recoverable.
- [ ] Memory controls and correctness evaluation pass.
- [ ] Voice and vision claims match measured real backends.
- [ ] Unconfigured integrations return setup/unavailable states.
- [ ] Experimental features are isolated and off by default.

---

## Phase 5 — Security, Privacy, and Safe Autonomy

**Priority:** P0 for dangerous actions; P1 overall  
**Estimated effort:** 3–7 weeks plus external review  
**Goal:** Make personal data and machine control safe by default.

### Q5-01: Threat model

Document assets, trust boundaries, attackers, and abuse cases for:

- Local API and WebSockets.
- LAN/mobile access.
- Browser automation.
- Filesystem and shell/app control.
- Microphone, camera, and screenshots.
- Models and prompt injection.
- Skills/marketplace.
- Accounts and tokens.
- Memory, history, logs, backups, and sync.
- Dependency/model download supply chain.

Every stable capability must map to threats and controls.

### Q5-02: Secure network defaults

- Bind to loopback by default.
- If LAN/remote binding is enabled, require authentication automatically.
- Generate strong tokens rather than relying on users to invent them.
- Authenticate HTTP and WebSocket paths consistently.
- Use strict CORS allowlists.
- Add origin/host validation.
- Add request size, rate, concurrency, and timeout limits.
- Never log tokens.
- Provide token rotation/revocation.
- Make remote mode visibly different in the UI.

### Q5-03: Permission and consent system

Classify actions:

- **Read-only/local low risk:** may run after normal request.
- **Sensitive read:** requires scoped permission.
- **Reversible write:** preview and configurable confirmation.
- **External communication:** explicit confirmation by default.
- **Destructive/irreversible:** explicit per-action confirmation; never inferred.
- **Credential/security changes:** elevated confirmation and audit.

Add dry-run/preview where useful. Never let the LLM suppress a required confirmation.

### Q5-04: Filesystem and process safety

- Canonicalize paths before policy checks.
- Default to approved roots.
- Prevent traversal, symlink escape, UNC/network surprises, and alternate path encodings.
- Keep shell execution off by default.
- Use argument arrays and allowlists.
- Bound subprocess time/output/resources.
- Verify process effects where possible.
- Add undo/backup for file writes and deletes.
- Test adversarial paths and commands on every supported OS.

### Q5-05: Enforceable offline mode

Offline mode must be a technical control, not a label:

- Disable Edge TTS and all cloud/account connectors.
- Prevent URL ingestion and external model downloads while active.
- Disable telemetry if ever introduced.
- Surface blocked egress attempts.
- Run an automated no-egress test with network calls intercepted/denied.
- Publish an explicit online-feature matrix.

### Q5-06: Personal data protection

- Inventory data classes and storage paths.
- Encrypt secrets with OS credential storage where available.
- Consider at-rest encryption for highly sensitive stores.
- Redact sensitive logs.
- Add retention and secure deletion controls.
- Add one-command export and one-command verified backup.
- Add profile isolation.
- Scan the current tree and history for committed personal data/secrets.

### Q5-07: Supply-chain security

- Reach zero known critical/high runtime vulnerabilities, or document a narrowly justified temporary exception with owner and expiry.
- Add Python and Node dependency scanning.
- Pin and checksum models/install artifacts.
- Generate an SBOM for releases.
- Use hashes/signatures for skill packages.
- Add secret scanning.
- Review install scripts for download and command-injection risks.

### Q5-08: Security verification

Required tests include:

- Authentication bypass attempts.
- WebSocket auth and replay.
- CORS/origin/host abuse.
- Path traversal and symlink escape.
- Shell metacharacter and argument injection.
- Oversized/slow payloads.
- Prompt injection attempting to bypass consent.
- Malicious skill package.
- Token persistence/revocation.
- Corrupt encrypted data.
- Offline egress attempts.
- Cross-profile data access.

Before final release, obtain at least one independent security review or structured second-person audit of the stable attack surface.

### Phase 5 exit gate

- [ ] Threat model covers every stable capability.
- [ ] Local-only default is safe; remote mode requires strong authentication.
- [ ] Consent cannot be bypassed by model output.
- [ ] Path/process controls pass adversarial tests.
- [ ] Offline mode passes a technical no-egress test.
- [ ] Secrets and personal data have explicit storage/retention controls.
- [ ] No unaccepted critical/high runtime dependency vulnerabilities remain.
- [ ] Independent security findings are closed or explicitly block release.

---

# PART III — MAKE IT A DAILY-DRIVER MASTERPIECE

## Phase 6 — User Experience, Accessibility, and Performance

**Priority:** P1  
**Estimated effort:** 4–8 weeks  
**Goal:** Make the correct, safe system effortless and enjoyable to use daily.

### Q6-01: First-run experience

The first run must:

1. Explain local vs. online features.
2. Run hardware/dependency diagnostics.
3. Let the user select the stable install profile.
4. Set name/timezone/quiet hours/data location.
5. Test microphone and speaker.
6. Detect/download a compatible model with size/checksum disclosure.
7. Explain permissions before requesting them.
8. Complete one real, reversible task.
9. Show where memory, logs, privacy controls, and shutdown live.

Target: fresh checkout to first successful non-model task in under 10 minutes excluding downloads, with no undocumented terminal repair.

### Q6-02: Unified status and degraded modes

The UI must always show:

- Backend connection.
- Model availability and active backend.
- Online/offline state.
- Microphone/listening state.
- Current plan/action/verification state.
- Remote-access state.
- Capability-specific setup requirements.

A missing optional dependency should degrade only its capability, not crash startup.

### Q6-03: Interaction quality

- Clear distinction between chat, proposed action, running action, confirmed effect, and failure.
- Cancel button for all long operations.
- Timeout with recovery guidance.
- Undo for reversible operations.
- Confirmation previews for sensitive writes.
- Searchable history and audit trail.
- Notifications respect quiet hours and cooldowns.
- Personality never hides uncertainty or failure.
- No raw private chain-of-thought display; use concise plan/progress summaries.

### Q6-04: Accessibility

Meet a documented WCAG 2.2 AA-oriented checklist for the web UI:

- Keyboard-only operation.
- Focus visibility and logical order.
- Screen-reader labels/status announcements.
- Contrast and reduced-motion modes.
- Captions/text equivalents for voice interactions.
- No color-only status.
- Scalable text and responsive layouts.

Perform both automated checks and manual keyboard/screen-reader verification.

### Q6-05: Performance budgets

Measure on the declared primary hardware. Suggested budgets:

- UI first useful paint: under 2 seconds after frontend startup.
- API health response: p95 under 100 ms.
- Immediate acknowledgment of a user command: under 250 ms.
- Simple local tool dispatch overhead: p95 under 300 ms excluding the tool itself.
- Status updates during long operations: at least every second.
- No unbounded memory growth over an eight-hour session.
- Shutdown: under 5 seconds with clean resource release.
- Startup: a documented warm and cold target based on model choice.
- LLM first-token and tokens/second targets measured, not guessed, on target hardware.

Add benchmark baselines and fail CI/self-hosted tests on material regressions.

### Q6-06: Personal workflow polish

For each of the ten core workflows:

- Minimize unnecessary confirmations without weakening policy.
- Add keyboard and voice paths.
- Add recovery suggestions.
- Store preferences where appropriate.
- Ensure results are easy to inspect.
- Measure task time compared with doing it manually.

The goal is not “OMNI can technically do it.” The goal is “using OMNI is reliably better than doing it manually.”

### Phase 6 exit gate

- [ ] First-run flow succeeds without undocumented repair.
- [ ] All degraded states are visible and capability-scoped.
- [ ] Every long action can cancel, time out, and recover.
- [ ] Accessibility checklist passes automated and manual review.
- [ ] Performance budgets pass on target hardware.
- [ ] Ten core workflows are faster or meaningfully more convenient than manual execution.

---

## Phase 7 — Documentation and Release Integrity

**Priority:** P1  
**Estimated effort:** 1–3 weeks, then continuous  
**Goal:** Make the repository a trustworthy representation of the product.

### Q7-01: Documentation hierarchy

Maintain:

- README: concise promise, supported scope, truthful quickstart.
- Installation guide: profiles, requirements, supported platforms.
- Capability matrix: stable/beta/experimental and dependencies.
- Privacy/network matrix.
- Security model and safe-use guidance.
- Architecture and data flow.
- Generated API reference.
- Tool reference generated from capability registry.
- Development/testing guide.
- Troubleshooting and recovery.
- Data export/backup/delete guide.
- Changelog and migration notes.

Archive or rewrite stale phase-completion documents that conflict with current status.

### Q7-02: Automated documentation checks

CI verifies:

- Internal links.
- Commands shown in quickstart.
- Referenced files.
- CLI help snapshots.
- OpenAPI/API reference drift.
- Tool/capability inventory drift.
- Supported Python/Node versions.
- Test count only if displayed, preferably generated.
- Version consistency across Python, frontend, docs, and release metadata.

### Q7-03: Release artifacts

A release candidate includes:

- Tagged source.
- Wheel and sdist.
- Platform installer/package if maintained.
- Checksums/signatures.
- SBOM.
- Changelog and migration notes.
- Known limitations.
- Dependency/model manifest.
- Reproducible test summary.
- Backup/rollback instructions.

### Phase 7 exit gate

- [ ] Every README claim maps to current evidence.
- [ ] All documented commands pass from a fresh checkout.
- [ ] API and tool docs are generated or drift-checked.
- [ ] Versions and counts are consistent.
- [ ] Release artifact installation passes outside the repository.
- [ ] Known limitations are explicit.

---

## Phase 8 — 30-Day Personal Reliability Qualification

**Priority:** Final release gate  
**Calendar duration:** 30 consecutive days minimum  
**Goal:** Prove OMNI is a real personal daily driver rather than a test/demo artifact.

### Q8-01: Define service-level objectives

Suggested personal SLOs:

- Startup success: at least 99% across 100 starts, and no repeated unexplained startup failure.
- Stable core workflow success: at least 95% over at least 20 runs per workflow.
- Unsafe false-success rate: 0%.
- Data-loss incidents: 0.
- Unrecoverable crashes during normal use: 0.
- Required daily backup success: 100%, with weekly restore verification.
- API/UI disconnect recovery: under 10 seconds where local services remain healthy.
- No unbounded eight-hour memory/resource leak.
- No unexpected network egress in offline mode.
- High/critical security incidents: 0.

### Q8-02: Dogfood log

Record, without leaking private contents:

- Date/session duration.
- Workflow attempted.
- Outcome state.
- Latency.
- Recovery required.
- Bug or friction category.
- Whether OMNI saved time.

Do not manipulate the measurement by excluding failures. Demo-mode runs do not count.

### Q8-03: Weekly chaos/recovery drills

Test one or more each week:

- Model missing or corrupt.
- Backend killed mid-action.
- Browser closed unexpectedly.
- Network disabled.
- Microphone disconnected.
- Disk nearly full.
- Corrupt JSON/database copy.
- Expired/revoked integration token.
- Interrupted model download.
- Upgrade followed by restore/rollback.

### Q8-04: Personal value review

At day 30 answer:

- Which workflows were used without forcing usage?
- Which saved measurable time?
- Which were annoying or ignored?
- Which generated false confidence?
- Which should be removed from stable scope?
- What personal information should not have been stored?

A 10/10 personal build can have fewer features after this review. Removing weak features is a successful outcome.

### Phase 8 exit gate

- [ ] Thirty consecutive days completed.
- [ ] SLOs met without excluding failures.
- [ ] No unresolved P0/P1 defects.
- [ ] Backup and restore proved with real data copy.
- [ ] Stable capability list updated based on actual use.
- [ ] Owner would keep OMNI running daily without needing to “test the project.”

---

## Phase 9 — Final 10/10 Audit and Quality Freeze

**Priority:** Release decision  
**Estimated effort:** 1–2 weeks  
**Goal:** Verify every category independently against this plan.

### Required audit runs

1. Fresh primary-OS machine or clean VM install.
2. Installed-wheel test outside source checkout.
3. Full required CI pipeline.
4. Real backend/frontend E2E suite.
5. Stable workflow repeated-run results.
6. Hardware/voice test on target machine.
7. Offline no-egress test.
8. Security regression suite and review.
9. Backup/restore/migration test.
10. Documentation command/link/claim verification.
11. Performance baseline comparison.
12. 30-day dogfood report.

### Scoring rule

A category receives 10 only if all its exit criteria pass. Otherwise it receives the evidence-supported lower score and remains open. Scores are never rounded up to complete a release narrative.

### Quality-freeze release

When all personal-build categories pass:

- Create a release candidate.
- Freeze new features.
- Run the complete audit again on the exact release artifact.
- Publish the evidence and limitations.
- Mark that artifact as the first 10/10 personal-core release.

---

# PART IV — OPTIONAL COMMERCIAL TRACK

## Phase 10 — Commercial Defensibility and Market Validation

This phase is optional. It is required only if OMNI is to be scored as a business rather than a personal build.

### Q10-01: Choose a narrow user and problem

“Local AGI for everyone” is not sufficiently focused. Select one initial segment and recurring job, for example:

- Privacy-focused Windows power users.
- Developers wanting local workflow automation.
- Accessibility users requiring voice-first desktop control.
- Small professional teams needing private document/task assistance.

Conduct interviews and measure existing alternatives, pain, willingness to switch, and willingness to pay.

### Q10-02: Establish differentiation

Because the current code is public MIT, defensibility must come from something else:

- Superior tested workflow packs.
- Signed integration ecosystem.
- Proprietary optional models/evaluation data, if legally appropriate.
- Trusted privacy/security reputation.
- Distribution partnerships.
- Fast support and deployment.
- Community/network effects.
- Managed enterprise features.

Do not claim exclusivity over already published MIT code.

### Q10-03: Adoption evidence

Before high commercial scores, demonstrate:

- Real activated users.
- Four- and twelve-week retention.
- Weekly successful tasks per retained user.
- Low support burden.
- Conversion or clear willingness to pay.
- Repeatable acquisition channel.
- Testimonials/case studies with permission.

### Q10-04: Commercial operations

- License and third-party attribution review.
- Privacy policy and terms where applicable.
- Support and security-response process.
- Signed release/update infrastructure.
- Crash/update process that remains privacy respecting.
- Sustainable pricing and costs.
- Brand/domain/release ownership.

### Commercial 10/10 gate

Commercial defensibility is not achieved by more code. It requires sustained retention, revenue or equivalent adoption, trusted operations, and a repeatable advantage. Until then, the category remains N/A for personal scope or low for business scope.

---

# PART V — STACK ADDITIONAL CHANGES AFTER 10/10

## 11. Expansion Protocol

Once the quality-freeze release passes, additional features may be stacked on top. Every feature must use this protocol.

### 11.1 Feature RFC

Before coding, document:

1. Personal problem being solved.
2. Evidence the problem occurs.
3. Why existing stable capabilities cannot solve it.
4. Proposed UX.
5. Stable/beta/experimental target.
6. Dependencies and hardware requirements.
7. Data touched and network destinations.
8. Threat model and consent needs.
9. Success, partial, unavailable, denied, failed, and cancellation behavior.
10. Test plan.
11. Performance budget.
12. Migration and rollback.
13. Documentation impact.
14. Removal criteria if unused.

### 11.2 Feature branch gates

A feature cannot merge into the stable product until:

- Existing 10/10 gates remain green.
- Its RFC acceptance criteria pass.
- Capability matrix and docs are updated.
- No new high/critical dependency issue is introduced.
- Offline behavior is known and tested.
- New state has backup/migration/delete behavior.
- Owner dogfoods it in beta before stable promotion.

### 11.3 Promotion model

`experimental → beta → stable`

- Experimental: implementation can evolve; off by default.
- Beta: real implementation and safety checks; needs usage/reliability evidence.
- Stable: repeated success, complete tests/docs/recovery, and no open P0/P1 issues.

No direct experimental-to-stable promotion.

---

## 12. Post-10 Innovation Backlog

Priority is determined by personal value, not spectacle.

### Expansion A — Personal workflow learning

- Observe repeated command sequences with consent.
- Propose a workflow rather than silently creating one.
- Show every step, required permission, and rollback.
- Track whether suggested workflows save time.

### Expansion B — Semantic desktop workspace

- Local index of approved folders, notes, tasks, and project history.
- Provenance for every answer.
- Per-folder access controls and retention.
- Fast incremental indexing and deletion propagation.

### Expansion C — Deeper local multimodal assistance

- Real screen/image understanding on selected hardware.
- Region-level capture consent.
- OCR/model confidence and provenance.
- Benchmarked personal screenshot set.

### Expansion D — Advanced voice experience

- Barge-in and interruption.
- Speaker/noise robustness.
- Real local voice cloning only after authenticity and abuse controls.
- Multiple voice profiles with explicit consent.

### Expansion E — Reliable workflow automation

- Visual workflow builder.
- Dry run and step-by-step approvals.
- Retry and compensation actions.
- Versioned workflows and execution history.

### Expansion F — Device companion and sync

- Start with authenticated LAN companion.
- Add encrypted sync only after key lifecycle and conflict testing.
- Remote mode remains off by default.

### Expansion G — Skills ecosystem

- Permissioned SDK.
- Sandboxed process/container boundary.
- Signed package registry.
- Review, rollback, and compatibility guarantees.

### Expansion H — Better model routing

- Select model based on task, privacy, latency, and hardware.
- Measure quality with a stable evaluation set.
- Never silently choose an online model in local/offline mode.

### Expansion I — Proactive intelligence

- User-configured triggers and quiet hours.
- Explain why a suggestion appeared.
- Strong cooldowns and easy opt-out.
- Measure acceptance vs. annoyance.

### Expansion J — Commercialization, only if desired

- Narrow segment.
- Installer/update polish for nontechnical users.
- Support model.
- Privacy/security review.
- Retention and willingness-to-pay validation.

---

# PART VI — EXECUTION ORDER

## 13. Critical Path

```text
Phase 0: Truth/scope
    ↓
Phase 1: Install/package/start
    ↓
Phase 2: CI + real tests
    ↓
Phase 3: Architecture/contracts
    ↓
Phase 4: Real stable capabilities
    ↓
Phase 5: Security/privacy hardening
    ↓
Phase 6: UX/performance polish
    ↓
Phase 7: Release/docs integrity
    ↓
Phase 8: 30-day dogfood
    ↓
Phase 9: Exact artifact audit + quality freeze
    ↓
Post-10 expansion protocol
```

Security work begins earlier for existing dangerous actions, but Phase 5 is where the complete stable attack surface receives final review.

---

## 14. Recommended First Six Sprints

### Sprint 0 — Truth and feature freeze

- [ ] Create capability matrix.
- [ ] Label stable/beta/experimental/demo/unavailable.
- [ ] Correct README and index claims.
- [ ] Generate endpoint/plugin/test inventory.
- [ ] Record baseline command.

**Exit:** no known false top-level claim remains.

### Sprint 1 — Python package rescue

- [ ] Fix package discovery.
- [ ] Correct dependency groups and invalid versions.
- [ ] Add OpenCV/cryptography requirements correctly.
- [ ] Build/install/test wheel outside checkout.
- [ ] Add package-content tests.

**Exit:** fresh wheel installation runs CLI and backend smoke test.

### Sprint 2 — Startup and frontend rescue

- [ ] Fix installer/start script paths.
- [ ] Centralize configuration and origins.
- [ ] Remove browser-facing localhost constants.
- [ ] Configure lint/typecheck.
- [ ] Upgrade vulnerable frontend dependencies.
- [ ] Make first-run diagnostics truthful.

**Exit:** fresh primary-OS checkout starts backend and frontend without hand edits.

### Sprint 3 — CI and deterministic tests

- [ ] Add CI workflows.
- [ ] Fix calendar wall-clock test.
- [ ] Start backend automatically for API tests.
- [ ] Fail on unexpected skips.
- [ ] Add wheel, frontend, and security jobs.

**Exit:** required pipeline is reproducibly green.

### Sprint 4 — Truthful execution states

- [ ] Introduce canonical result model.
- [ ] Replace successful mock fallbacks.
- [ ] Isolate explicit demo mode.
- [ ] Add unavailable/degraded UI states.
- [ ] Add regression tests for false success.

**Exit:** no stable unavailable path claims completion.

### Sprint 5 — Capability registry and core workflows

- [ ] Build canonical registry.
- [ ] Remove duplicate tool registration.
- [ ] Separate aliases from tool counts.
- [ ] Select ten core workflows.
- [ ] Add schemas, probes, risk levels, verification, and tests.

**Exit:** stable capability inventory is runtime-generated and all selected tools satisfy the initial contract.

After Sprint 5, reassess estimates before beginning the larger backend/frontend decomposition and authenticity work.

---

## 15. Realistic Solo Timeline

Exact duration depends on how many current headline features remain in stable scope.

### Focused personal-core route

A smaller, deeply supported stable core:

- Foundation and packaging: 3–6 weeks.
- Tests and architecture: 6–12 weeks.
- Capability authenticity/security/UX: 8–16 weeks.
- Dogfood qualification: 4 calendar weeks, partly overlapping final polish.

**Expected:** roughly 4–8 months of focused solo work, or longer part-time.

### Complete-every-current-claim route

Making voice cloning, sync, marketplace, mobile, all integrations, vision, broad OS automation, and every API genuinely production-grade can take **9–18+ months solo**. Reducing stable scope is the responsible path to a real 10/10 sooner.

Any plan promising a complete 10/10 conversion in a few days is not credible.

---

## 16. Definition of Done for Every Change

A change is done only when all applicable items pass:

- [ ] Requirement and user outcome are explicit.
- [ ] Stable/beta/experimental scope is selected.
- [ ] Success and all failure states are implemented.
- [ ] Security/privacy/data implications are reviewed.
- [ ] Unit tests added or updated.
- [ ] Integration/API/E2E tests added where appropriate.
- [ ] No required test becomes skipped.
- [ ] Types, lint, formatting, and build pass.
- [ ] Performance impact is measured where relevant.
- [ ] Capability registry and docs are updated.
- [ ] Migration/backup/delete behavior exists for new persistent data.
- [ ] Existing 10/10 gates do not regress.
- [ ] User-facing errors provide a recovery action.
- [ ] No mock/demo behavior can be mistaken for real success.

---

## 17. Final Acceptance Checklist

OMNI is a 10/10 personal build only when:

### Vision

- [ ] Stable scope and non-goals are clear.
- [ ] Ten high-value personal workflows are defined and used.

### Implementation

- [ ] Every stable claim maps to real code and verified effects.
- [ ] Aliases, endpoints, and modules are not inflated as capabilities.

### Testing

- [ ] Required CI is fully green.
- [ ] No required release suite skips.
- [ ] E2E, platform, hardware, offline, security, package, and migration evidence exists.

### UX

- [ ] Fresh setup is guided and repeatable.
- [ ] Status, consent, cancellation, failure, recovery, and undo are understandable.
- [ ] Accessibility and performance budgets pass.

### Authenticity

- [ ] No stable mock success or canned integration data exists.
- [ ] Demo mode is explicit and isolated.

### Architecture

- [ ] Backend and frontend monoliths are decomposed.
- [ ] Capability, result, configuration, and storage contracts are canonical.

### Installation

- [ ] Source, wheel, installer, first start, restart, upgrade, and backup/restore pass on primary OS.

### Security/privacy

- [ ] Secure defaults, threat model, permission system, offline enforcement, dependency policy, and independent review pass.

### Documentation

- [ ] Every claim and command is verified against the release artifact.

### Personal value

- [ ] Thirty-day dogfood SLOs pass.
- [ ] The owner uses OMNI because it is useful—not because the project needs testing.

### Commercial, if activated

- [ ] Real adoption, retention, support, distribution, and defensibility evidence exists.

---

## 18. Immediate Next Action

Begin **Sprint 0**, then Sprint 1. Do not start by adding more AI capabilities.

The first implementation sequence should be:

1. Add the machine-readable capability matrix.
2. Correct public status claims.
3. Repair `pyproject.toml` dependency and package discovery.
4. Add isolated wheel-install smoke tests.
5. Repair launch scripts and runtime configuration.
6. Add CI and make the existing suite deterministic.
7. Introduce truthful execution states and remove mock success.

That sequence directly attacks the lowest-scoring categories and creates the platform on which every later improvement can safely stack.

---

**North star:** Fewer claims, more proof. Fewer shallow tools, more completed workflows. No fake success. No hidden failure. Private by enforcement, useful by daily evidence, and expandable without breaking the foundation.
