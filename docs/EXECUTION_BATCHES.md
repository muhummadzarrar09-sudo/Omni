# OMNI Locked Execution Batches

> **Generated file.** Edit `quality/batches.json` or `quality/policy.json`, then run `python scripts/quality_baseline.py generate`.

**Current batch:** `none`<br>
**Next batch:** `B02`<br>
**Feature freeze:** `enabled`<br>
**Execution rule:** one batch at a time; implementation, tests, audit, documentation, evidence, and the complete exit gate must pass before the next batch starts.

## Sequence

| Batch | Title | Status | Dependency | Solo estimate |
|---|---|---|---|---|
| `B00` | Scope Lock and Truth Reset | `closed` | None | 2-4 focused days |
| `B01` | Dependency and Package Rescue | `closed` | B00 | 4-8 focused days |
| `B02` | Install, Configuration, and Startup Qualification | `ready` | B01 | 5-10 focused days plus Windows hardware access |
| `B03` | Continuous Verification and Flake Elimination | `locked` | B02 | 6-12 focused days |
| `B04` | Truthful Result Contract and Degraded Recovery | `locked` | B03 | 6-12 focused days |
| `B05` | Canonical Capability and Tool Registry | `locked` | B04 | 8-15 focused days |
| `B06` | API and Transport Contract Hardening | `locked` | B05 | 8-15 focused days |
| `B07` | Data Ownership, Migration, and Recovery | `locked` | B06 | 8-15 focused days |
| `B08` | Architecture Consolidation and Maintainability | `locked` | B07 | 10-20 focused days |
| `B09` | Desktop, File, Browser, Reminder, and Focus Workflows | `locked` | B08 | 15-30 focused days plus Windows hardware access |
| `B10` | Personal Memory and Briefing Workflows | `locked` | B09 | 10-20 focused days plus owner evaluation |
| `B11` | Local Voice Workflow and Authenticity Closure | `locked` | B10 | 12-25 focused days plus microphone/hardware access |
| `B12` | Security, Privacy, and Safe Autonomy | `locked` | B11 | 12-25 focused days plus independent review |
| `B13` | User Experience, Accessibility, and Performance | `locked` | B12 | 10-20 focused days plus owner usability sessions |
| `B14` | Documentation, Release, and Claim Integrity | `locked` | B13 | 6-12 focused days |
| `B15` | Thirty-Day Personal Dogfood Qualification | `locked` | B14 | 30 consecutive calendar days plus repair time |
| `B16` | Exact-Artifact Final Audit and 10/10 Freeze | `locked` | B15 | 5-10 focused days after B15 plus independent review |

## Batch Contracts

### B00 — Scope Lock and Truth Reset

**Status:** `closed`<br>
**Depends on:** `none`<br>
**Solo estimate:** 2-4 focused days<br>
**Evidence:** `quality/evidence/B00/`

**Objective:** Create one enforceable source of truth for what OMNI is, what exists, what is excluded, how it is scored, and how later work is allowed to proceed.

**In scope**

- Lock one-owner personal-core promise, primary platform, ten workflows, non-goals, and stable-result semantics
- Classify every active capability by lifecycle and implementation reality
- Generate source, endpoint, route, tool-declaration, test, and code inventory
- Capture dependency, wheel, test, frontend, audit, and runtime-tool baseline without hiding failures
- Reset top-level public claims and label historical material
- Lock feature freeze, B00-B16 sequence, E01-E10 expansion queue, and optional commercial separation

**Target paths**

- `quality/capabilities.json`
- `quality/scorecard.json`
- `quality/policy.json`
- `quality/batches.json`
- `quality/inventory.json`
- `scripts/quality_baseline.py`
- `docs/CAPABILITY_MATRIX.md`
- `docs/QUALITY_SCORECARD.md`
- `docs/EXECUTION_BATCHES.md`
- `README.md`
- `docs/INDEX.md`
- `quality/evidence/B00/`
- `scripts/quality_baseline_selftest.py`

**Verification commands**

- `python scripts/quality_baseline.py capture --publish quality/evidence/B00/baseline-summary.json`
- `python scripts/quality_baseline.py check`
- `python scripts/check_markdown_links.py --local-only README.md docs quality/evidence`
- `python -m compileall -q scripts`
- `git diff --check`
- `python scripts/quality_baseline_selftest.py`

**Principal risks**

- Large historical surface can conceal a false claim
- Grouped capability coverage can be mistaken for per-effect qualification
- A manually repaired local environment can create false installation confidence

**Exit gate**

- [x] Stable personal core, platforms, non-goals, and ten outcomes are explicitly locked
- [x] Every active capability group and active product source file is represented in the matrix
- [x] No capability is called stable before release qualification
- [x] README and docs index contain no known false completion, privacy, test, platform, installer, integration, voice-clone, sync, or tool-count claim
- [x] Historical/unqualified documents are unmistakably labeled
- [x] Baseline capture runs from one command and records every required non-passing probe
- [x] Feature freeze, batch order, and post-10 policy are machine-readable
- [x] Generated artifacts and local links pass drift validation
- [x] B00 audit evidence records commands, results, limitations, and approval

### B01 — Dependency and Package Rescue

**Status:** `closed`<br>
**Depends on:** `B00`<br>
**Solo estimate:** 4-8 focused days<br>
**Evidence:** `quality/evidence/B01/`

**Objective:** Make supported Python installation profiles resolve reproducibly and produce complete wheel/sdist artifacts.

**In scope**

- Set and enforce the supported Python range and one canonical distribution version
- Separate minimal/core, voice, vision, desktop, development, and full dependency profiles
- Map every locked-scope production import to declared profiles and correct impossible or undeclared requirements
- Generate exact hash-locked CPython 3.11 Linux x86_64 profile resolutions and audit the development lock
- Replace manual package lists with complete package discovery and explicit package data
- Keep runtime state out of the source and installed package trees through one writable-data authority
- Build wheel and sdist, inspect exact contents, and validate metadata
- Install the exact artifact outside the checkout and smoke imports, resources, CLI dispatch, backend health, clean-CWD behavior, and installed-tree immutability
- Repair and qualify the exact frontend lock, install-script policy, dependency tree, audit, lint, and production build
- Document the qualified path and every interpreter, platform, native dependency, artifact, and release limitation

**Target paths**

- `pyproject.toml`
- `requirements.txt`
- `backend_fastapi/requirements.txt`
- `requirements/locks/cpython-3.11-linux-x86_64/`
- `quality/dependency-profiles.json`
- `frontend_next/package.json`
- `frontend_next/package-lock.json`
- `scripts/resolve_profiles.py`
- `scripts/check_package_contents.py`
- `scripts/smoke_installed_artifact.py`
- `scripts/audit_python_licenses.py`
- `tests/package/`
- `omni_v2/core/paths.py`
- `docs/TROUBLESHOOTING.md`
- `quality/evidence/B01/`

**Verification commands**

- `python scripts/resolve_profiles.py`
- `python -m pip install --require-hashes -r requirements/locks/cpython-3.11-linux-x86_64/dev.txt`
- `python -m pip check`
- `python -m build`
- `python scripts/check_package_contents.py --json dist/*.whl dist/*.tar.gz`
- `python -m twine check dist/*`
- `python -m pytest -q tests/package`
- `python scripts/smoke_installed_artifact.py dist/omni_agi-3.2.0-py3-none-any.whl`
- `python -m pip_audit --require-hashes -r requirements/locks/cpython-3.11-linux-x86_64/dev.txt`
- `python scripts/audit_python_licenses.py requirements/locks/cpython-3.11-linux-x86_64/dev.txt`
- `cd frontend_next && npx --yes npm@12.0.2 ci && npx --yes npm@12.0.2 install-scripts ls && npx --yes npm@12.0.2 ls --all && npx --yes npm@12.0.2 audit --audit-level=low && npx --yes npm@12.0.2 run lint && npx --yes npm@12.0.2 run build`

**Principal risks**

- Native audio/vision dependencies vary by platform
- Overly broad full profile can remain unmaintainable
- Source-checkout imports can mask missing wheel packages

**Exit gate**

- [x] Every declared profile resolves on every declared Python version
- [x] Wheel and sdist contain every intended runtime package and no runtime data leakage
- [x] Clean isolated artifact install starts CLI and backend smoke paths
- [x] Dependency declarations match imports for locked scope
- [x] B01 evidence reproduces without the repaired B00 environment

### B02 — Install, Configuration, and Startup Qualification

**Status:** `ready`<br>
**Depends on:** `B01`<br>
**Solo estimate:** 5-10 focused days plus Windows hardware access<br>
**Evidence:** `quality/evidence/B02/`

**Objective:** Provide one documented, idempotent primary-platform installation and startup path with centralized configuration and truthful diagnostics.

**In scope**

- Unify Windows installer and launcher behavior
- Repair Unix developer launcher without claiming Linux product support
- Centralize ports, URLs, origins, paths, models, devices, offline setting, and secrets
- Remove browser-facing localhost assumptions
- Add preflight and actionable unavailable states
- Verify install, start, stop, restart, second install, and uninstall/cleanup behavior

**Target paths**

- `install.bat`
- `start.bat`
- `start.sh`
- `scripts/install.ps1`
- `scripts/install.sh`
- `omni/cli.py`
- `omni_v2/core/config.py`
- `backend_fastapi/`
- `frontend_next/`
- `tests/install/`

**Verification commands**

- `powershell -File scripts/verify_windows_install.ps1`
- `python -m pytest -q tests/install`
- `python scripts/verify_config_contract.py`
- `python scripts/smoke_startup.py --restart`
- `python scripts/quality_baseline.py check`

**Principal risks**

- Linux-only development cannot qualify Windows automation
- Model downloads and hardware devices produce long and failure-prone first run
- Divergent launch paths can regress configuration

**Exit gate**

- [ ] Fresh Windows 11 x64 machine reaches a useful first-run state from one documented path
- [ ] Installer is idempotent and second run is safe
- [ ] Startup, shutdown, and restart leave no orphan services
- [ ] UI reaches backend through centralized configuration
- [ ] Missing model, microphone, browser, or optional dependency is diagnosed without mock success

### B03 — Continuous Verification and Flake Elimination

**Status:** `locked`<br>
**Depends on:** `B02`<br>
**Solo estimate:** 6-12 focused days<br>
**Evidence:** `quality/evidence/B03/`

**Objective:** Turn existing tests into deterministic release-relevant CI, remove hidden skips, and establish required quality jobs.

**In scope**

- Configure pytest markers, timeouts, warnings, temporary state, and coverage boundaries
- Fix wall-clock-dependent calendar test and every current failure
- Start backend services automatically for live API tests
- Configure frontend lint and add focused component/API tests
- Add package, install, offline, migration, security, and core-workflow jobs
- Run flaky suites repeatedly and quarantine only with an owner, reason, and deadline

**Target paths**

- `pyproject.toml`
- `.github/workflows/`
- `omni_v2/tests/`
- `frontend_next/`
- `tests/`
- `.pre-commit-config.yaml`
- `quality/evidence/B03/`

**Verification commands**

- `python -m pytest -q`
- `python -m pytest -q -m live`
- `python scripts/repeat_tests.py --runs 20 --suite core`
- `cd frontend_next && npm run lint && npm test && npm run build`
- `python -m build && python -m pytest -q tests/package`

**Principal risks**

- Large test count can hide shallow assertions
- Hardware and network tests need explicit lab lanes
- Optional dependency skips can silently become release gaps

**Exit gate**

- [ ] All required CI jobs pass from a clean checkout
- [ ] No release-required test is skipped
- [ ] Backend live checks self-host their service
- [ ] Twenty repeated core-suite runs show zero flaky failures
- [ ] Lint, build, dependency, package, migration, security, and offline jobs publish inspectable summaries

### B04 — Truthful Result Contract and Degraded Recovery

**Status:** `locked`<br>
**Depends on:** `B03`<br>
**Solo estimate:** 6-12 focused days<br>
**Evidence:** `quality/evidence/B04/`

**Objective:** Make every user-visible operation report success, partial, unavailable, denied, failed, or demo consistently and prohibit false successful fallback.

**In scope**

- Define one typed result/error/availability contract
- Propagate result state from adapters through executor, API, WebSocket, and UI
- Remove blanket catch-and-success paths
- Isolate and visibly label demo mode
- Define timeout, cancellation, retry, provenance, verification, and recovery metadata
- Qualify W10 across missing-model, browser, microphone, integration, and dependency cases

**Target paths**

- `omni_v2/core/`
- `omni_v2/agents/executor.py`
- `omni_v2/engine/`
- `backend_fastapi/`
- `frontend_next/`
- `mobile/`
- `omni_v2/tests/test_degraded_contract.py`

**Verification commands**

- `python -m pytest -q omni_v2/tests/test_degraded_contract.py`
- `python -m pytest -q tests/contract`
- `cd frontend_next && npm test -- degraded`
- `python scripts/audit_success_paths.py`

**Principal risks**

- Changing result semantics touches most layers
- Legacy callers may treat text as success
- Fallback convenience can reintroduce dishonesty

**Exit gate**

- [ ] Every stable-path operation uses the canonical result contract
- [ ] No unavailable, exception, demo, placeholder, or unverified path reports success
- [ ] UI preserves state and recovery details
- [ ] Timeout and cancellation are tested
- [ ] W10 passes its repeated target-platform qualification

### B05 — Canonical Capability and Tool Registry

**Status:** `locked`<br>
**Depends on:** `B04`<br>
**Solo estimate:** 8-15 focused days<br>
**Evidence:** `quality/evidence/B05/`

**Objective:** Replace inflated aliases and overlapping dispatch with one registry for a small, excellent, measurable canonical tool set.

**In scope**

- Select 20-30 canonical personal-core tools
- Define schema, availability, risk, consent, execution, verification, lifecycle, runtime, owner, and documentation in one registry
- Remove duplicate loader instances and unsupported aliases
- Route unknown actions to unavailable rather than generic AI success
- Generate runtime/API/UI documentation from registry
- Add collision, schema, availability, consent, and effect-verification tests

**Target paths**

- `omni_v2/core/capability_registry.py`
- `omni_v2/core/plugin_manager.py`
- `omni_v2/tools/`
- `omni_v2/agents/executor.py`
- `backend_fastapi/`
- `frontend_next/`
- `scripts/generate_capability_docs.py`

**Verification commands**

- `python scripts/audit_tool_registry.py --max-canonical 30`
- `python -m pytest -q tests/tools tests/registry`
- `python scripts/check_registry_drift.py`
- `python scripts/quality_baseline.py check`

**Principal risks**

- Removing aliases can break historical demos
- Tool count pressure can undermine scope
- Verification is platform-specific for desktop effects

**Exit gate**

- [ ] One registry owns every stable tool declaration
- [ ] Canonical set contains at most 30 tools and no duplicate or count-inflating alias
- [ ] Every stable tool has real availability, risk, consent, execution, and verification behavior
- [ ] Registry/API/UI/docs drift checks pass
- [ ] Unsupported requests return truthful unavailable states

### B06 — API and Transport Contract Hardening

**Status:** `locked`<br>
**Depends on:** `B05`<br>
**Solo estimate:** 8-15 focused days<br>
**Evidence:** `quality/evidence/B06/`

**Objective:** Reduce the broad HTTP/WebSocket surface to explicit owned contracts with secure defaults and generated drift checks.

**In scope**

- Inventory all routes and clients
- Select personal-core API and mark experimental routes
- Split domain routers from composition
- Standardize request, response, status, pagination, validation, timeout, cancellation, and WebSocket event schemas
- Centralize origin and exposure policy
- Generate OpenAPI and compare it in CI

**Target paths**

- `backend_fastapi/main.py`
- `backend_fastapi/*_routes.py`
- `backend_fastapi/core/`
- `frontend_next/app/api/`
- `frontend_next/lib/`
- `tests/api/`
- `quality/openapi.json`

**Verification commands**

- `python scripts/export_openapi.py --check`
- `python -m pytest -q tests/api`
- `python scripts/check_api_clients.py`
- `python scripts/audit_routes.py --fail-unowned`
- `cd frontend_next && npm test -- api`

**Principal risks**

- Monolithic main module has hidden shared state
- UI proxy routes may conceal backend contract drift
- Remote routes expand the security boundary

**Exit gate**

- [ ] Every route has an owner, lifecycle, auth/exposure rule, schema, and test
- [ ] Personal-core OpenAPI is generated and drift-checked
- [ ] Unknown exceptions never leak as successful 200 responses
- [ ] WebSocket reconnect/backpressure/cancellation behavior is tested
- [ ] Experimental API cannot be mistaken for stable core

### B07 — Data Ownership, Migration, and Recovery

**Status:** `locked`<br>
**Depends on:** `B06`<br>
**Solo estimate:** 8-15 focused days<br>
**Evidence:** `quality/evidence/B07/`

**Objective:** Make all personal state inspectable, migratable, concurrency-safe, exportable, deletable, backed up, and restorable.

**In scope**

- Choose authoritative stores for profile, sessions, reminders, tasks, calendar, audit, and settings
- Add schema versions and forward migrations
- Define process ownership, transactions, locking, corruption handling, retention, redaction, export, and delete propagation
- Create consistent backup snapshots
- Test restore onto a fresh artifact installation and rollback after failed migration

**Target paths**

- `omni_v2/memory/`
- `omni_v2/personal/`
- `omni_v2/schedule/`
- `omni_v2/backup/`
- `omni_v2/history/`
- `omni_v2/core/paths.py`
- `tests/data/`

**Verification commands**

- `python -m pytest -q tests/data tests/migrations tests/backup`
- `python scripts/test_migration_matrix.py`
- `python scripts/verify_backup_manifest.py`
- `python scripts/corruption_recovery_test.py`

**Principal risks**

- Overlapping stores may contain incompatible truth
- Backup during writes can be inconsistent
- Deletion and retention can miss derived indexes

**Exit gate**

- [ ] Each stable datum has one authoritative owner and documented schema
- [ ] Forward migration and failed-migration rollback pass from every supported schema
- [ ] Concurrent access and corruption tests pass
- [ ] Export/delete propagate through derived data
- [ ] Fresh-machine backup restore reproduces all locked state without data loss

### B08 — Architecture Consolidation and Maintainability

**Status:** `locked`<br>
**Depends on:** `B07`<br>
**Solo estimate:** 10-20 focused days<br>
**Evidence:** `quality/evidence/B08/`

**Objective:** Consolidate duplicate runtimes and oversized modules behind clear boundaries without changing qualified contracts.

**In scope**

- Declare one canonical composition root, backend, web UI, browser adapter, voice path, memory owner, and desktop path
- Split backend routers/services/repositories/adapters
- Split frontend clients/state/features/components
- Remove or archive superseded variants
- Enforce dependency direction, typing, lint, and bounded complexity
- Record architecture decisions and ownership

**Target paths**

- `omni_v2/app.py`
- `omni_v2/engine/`
- `omni_v2/agents/`
- `backend_fastapi/`
- `frontend_next/`
- `docs/architecture/`
- `tests/architecture/`

**Verification commands**

- `python -m pytest -q tests/architecture`
- `python scripts/check_dependency_boundaries.py`
- `ruff check omni_v2 backend_fastapi`
- `mypy omni_v2 backend_fastapi`
- `cd frontend_next && npm run lint && npm test && npm run build`

**Principal risks**

- Large refactors can invalidate earlier evidence
- Premature abstraction can make a personal build harder to maintain
- Archived variants may still be imported dynamically

**Exit gate**

- [ ] One canonical runtime path is documented and enforced
- [ ] Backend and frontend monoliths are decomposed to agreed limits
- [ ] Duplicate stable implementations are removed or isolated
- [ ] Dependency, lint, type, complexity, and dead-code policies pass
- [ ] All earlier contract/data/packaging suites remain green

### B09 — Desktop, File, Browser, Reminder, and Focus Workflows

**Status:** `locked`<br>
**Depends on:** `B08`<br>
**Solo estimate:** 15-30 focused days plus Windows hardware access<br>
**Evidence:** `quality/evidence/B09/`

**Objective:** Make W02-W07 excellent on the primary Windows platform with consent, verification, rollback, and recovery.

**In scope**

- Reminder create/read/update/trigger/cancel across restart
- Approved-root document search and safe file preview/write/edit/rollback
- Isolated browser navigation/search and absence recovery
- Allowlisted app/window launch/focus/minimize/maximize/close with effect verification
- Focus timer, notification quieting, cancellation, and state restoration
- Adversarial paths, ambiguity, permissions, timezones, clock changes, and interruption tests

**Target paths**

- `omni_v2/tools/files.py`
- `omni_v2/files/`
- `omni_v2/tools/browser_v3.py`
- `omni_v2/tools/windows.py`
- `omni_v2/schedule/`
- `omni_v2/agents/notifications.py`
- `tests/workflows/W02_W07/`

**Verification commands**

- `python -m pytest -q tests/workflows/W02_W07`
- `python scripts/run_workflow.py W02 W03 W04 W05 W06 W07 --runs 20 --platform windows`
- `python scripts/audit_effect_verification.py --workflows W02-W07`

**Principal risks**

- Desktop/window APIs vary across applications
- File rollback semantics differ by operation
- Browser updates and profile locks cause flakes
- Time-based behavior is prone to race conditions

**Exit gate**

- [ ] Each of W02-W07 completes at least 20 target-platform runs at 95% or better
- [ ] No workflow reports an unsafe false success
- [ ] Destructive or external effects require correct consent
- [ ] Restart, cancellation, timeout, interruption, absence, and rollback cases pass
- [ ] No data loss or approved-root escape occurs

### B10 — Personal Memory and Briefing Workflows

**Status:** `locked`<br>
**Depends on:** `B09`<br>
**Solo estimate:** 10-20 focused days plus owner evaluation<br>
**Evidence:** `quality/evidence/B10/`

**Objective:** Qualify W01 and W08 against real owner-controlled data with provenance, uncertainty, privacy controls, and deletion.

**In scope**

- Real local calendar/task/reminder briefing with per-source availability
- Session capture and yesterday recall with timestamps and provenance
- Inspect, export, correct, and delete controls
- Timezone, recurrence, missing-source, conflicting-source, and stale-data behavior
- Owner-grounded retrieval and briefing evaluation sets
- No canned integration data in real mode

**Target paths**

- `omni_v2/briefing/`
- `omni_v2/personal/`
- `omni_v2/memory/`
- `omni_v2/agents/user_profile.py`
- `frontend_next/`
- `tests/workflows/W01_W08/`
- `quality/evaluation/personal/`

**Verification commands**

- `python -m pytest -q tests/workflows/W01_W08 tests/privacy/memory`
- `python scripts/run_workflow.py W01 W08 --runs 20 --fixture real-redacted`
- `python scripts/evaluate_retrieval.py quality/evaluation/personal`
- `python scripts/test_delete_propagation.py`

**Principal risks**

- Synthetic fixtures can overstate personal usefulness
- Inferred personal facts can be wrong or sensitive
- Calendar recurrence/timezone edge cases are extensive

**Exit gate**

- [ ] W01 and W08 each complete at least 20 runs at 95% or better
- [ ] Every factual item carries inspectable source and time provenance
- [ ] Unavailable and conflicting sources are explicit
- [ ] Owner can inspect, export, correct, and delete data and derivations
- [ ] No demo/canned content reaches real briefing or recall

### B11 — Local Voice Workflow and Authenticity Closure

**Status:** `locked`<br>
**Depends on:** `B10`<br>
**Solo estimate:** 12-25 focused days plus microphone/hardware access<br>
**Evidence:** `quality/evidence/B11/`

**Objective:** Qualify one push-to-talk STT and local TTS path for W09 and remove or isolate every misleading mock, placeholder, and demo claim in the assessed core.

**In scope**

- Select one microphone capture/STT pipeline and one local TTS default
- Expose device/model/backend availability and online status
- Add cancellation, timeout, audio-retention, privacy, latency, and noisy-room tests
- Qualify voice execution through a real core workflow
- Keep wake word experimental unless accuracy/privacy gates pass
- Rename or disable fake voice-clone training, mock vision, canned integrations, and all equivalent false affordances

**Target paths**

- `omni_v2/voice/`
- `omni_v2/vision/`
- `omni_v2/tools/integrations.py`
- `backend_fastapi/`
- `frontend_next/`
- `tests/workflows/W09/`
- `quality/evaluation/voice/`

**Verification commands**

- `python -m pytest -q tests/workflows/W09 tests/authenticity`
- `python scripts/run_workflow.py W09 --runs 20 --platform windows`
- `python scripts/evaluate_voice.py quality/evaluation/voice --hardware-manifest quality/hardware/windows-primary.json`
- `python scripts/audit_mock_boundaries.py`

**Principal risks**

- Audio model performance depends heavily on hardware and environment
- Online TTS can violate offline expectations
- Renaming fake features can break presentation code

**Exit gate**

- [ ] W09 completes at least 20 runs at 95% or better on declared hardware
- [ ] Selected default STT and TTS are local and block network in offline mode
- [ ] Missing audio devices/models produce truthful recovery
- [ ] No demo, mock, placeholder, or stub is presented as a real working capability
- [ ] Wake word, vision, voice clone, and integrations retain only evidence-appropriate lifecycle labels

### B12 — Security, Privacy, and Safe Autonomy

**Status:** `locked`<br>
**Depends on:** `B11`<br>
**Solo estimate:** 12-25 focused days plus independent review<br>
**Evidence:** `quality/evidence/B12/`

**Objective:** Threat-model and harden the exact stable attack surface, enforce privacy modes, and independently review high-risk behavior.

**In scope**

- Threat model assets, actors, boundaries, routes, tools, storage, models, plugins, LAN, browser, and update paths
- Secure-by-default authentication and origin/exposure policy
- Consent enforcement outside model control
- Path/command/prompt/URL/SSRF/replay/rate/loop/resource defenses
- Secret storage, logging/redaction, data retention, dependency and supply-chain review
- Enforced offline no-egress mode
- Independent review and finding closure

**Target paths**

- `docs/security/THREAT_MODEL.md`
- `omni_v2/core/guardrails.py`
- `omni_v2/core/safe_execute.py`
- `omni_v2/vault/`
- `backend_fastapi/`
- `frontend_next/`
- `tests/security/`
- `quality/evidence/B12/`

**Verification commands**

- `python -m pytest -q tests/security`
- `python scripts/no_egress_test.py --artifact dist/OMNI-*`
- `python scripts/adversarial_actions.py`
- `pip-audit`
- `cd frontend_next && npm audit --audit-level=high`
- `python scripts/verify_threat_model_coverage.py`

**Principal risks**

- Local software still has substantial file, shell, browser, camera, and LAN authority
- Offline enforcement is OS-sensitive
- Plugin and model input are untrusted supply-chain surfaces

**Exit gate**

- [ ] Threat model covers every stable capability and data flow
- [ ] Remote/LAN access is disabled or strongly authenticated by default
- [ ] Consent cannot be bypassed by model output
- [ ] Offline artifact passes no-egress testing
- [ ] No unaccepted critical/high runtime dependency finding remains
- [ ] Independent review findings are closed or explicitly remove affected scope

### B13 — User Experience, Accessibility, and Performance

**Status:** `locked`<br>
**Depends on:** `B12`<br>
**Solo estimate:** 10-20 focused days plus owner usability sessions<br>
**Evidence:** `quality/evidence/B13/`

**Objective:** Make the qualified personal core understandable, accessible, responsive, cancellable, recoverable, and genuinely faster than manual work.

**In scope**

- One canonical first-run and daily-use UI
- Visible connection/model/microphone/offline/remote/action/result states
- Progress, timeout, cancel, retry, rollback, and recovery interactions
- Keyboard, focus, contrast, motion, screen-reader, scaling, and error-message accessibility
- Startup, idle memory, response, action, and voice latency budgets on target hardware
- Owner workflow usability studies and annoyance controls

**Target paths**

- `frontend_next/`
- `omni_v2/ui/`
- `docs/UX_SPEC.md`
- `tests/e2e/`
- `quality/evaluation/ux/`
- `quality/benchmarks/windows-primary/`

**Verification commands**

- `cd frontend_next && npm run lint && npm test && npm run test:e2e && npm run build`
- `python scripts/accessibility_audit.py`
- `python scripts/benchmark_release.py --platform windows`
- `python scripts/run_usability_protocol.py quality/evaluation/ux`

**Principal risks**

- Visual polish can conceal state ambiguity
- Animation can harm performance and accessibility
- Synthetic benchmarks can miss daily friction

**Exit gate**

- [ ] Fresh owner completes first run without undocumented intervention
- [ ] All required status, progress, cancellation, and recovery states are visible
- [ ] Automated and manual accessibility checks pass the declared standard
- [ ] Target-hardware latency/resource budgets pass
- [ ] Usability evidence shows each core workflow provides real owner value

### B14 — Documentation, Release, and Claim Integrity

**Status:** `locked`<br>
**Depends on:** `B13`<br>
**Solo estimate:** 6-12 focused days<br>
**Evidence:** `quality/evidence/B14/`

**Objective:** Make every public command and claim derive from current contracts and prepare a reproducible signed release candidate.

**In scope**

- Generate API, tool, capability, config, and version references
- Test every README, quickstart, troubleshooting, migration, backup, and recovery command
- Document privacy/network matrix, limitations, hardware, models, data paths, and uninstall
- Add changelog/release-note discipline and artifact checksums
- Remove or archive superseded material
- Automate link, claim, version, route, registry, and command drift checks

**Target paths**

- `README.md`
- `docs/`
- `quality/`
- `scripts/check_docs.py`
- `scripts/build_release.py`
- `.github/workflows/release.yml`
- `CHANGELOG.md`

**Verification commands**

- `python scripts/check_docs.py --all-commands`
- `python scripts/quality_baseline.py check`
- `python scripts/export_openapi.py --check`
- `python scripts/check_registry_drift.py`
- `python scripts/build_release.py --reproducible`
- `python scripts/verify_release_manifest.py`

**Principal risks**

- Large historical docs invite drift
- Documentation tests can accidentally rely on source checkout
- Release metadata can differ across operating systems

**Exit gate**

- [ ] Every top-level claim maps to current evidence
- [ ] Every documented command passes in its declared clean environment
- [ ] Generated API/tool/capability/config docs have zero drift
- [ ] Privacy, limitations, data, migration, backup, restore, and uninstall behavior are explicit
- [ ] Release candidate is reproducible and has a complete manifest/checksums

### B15 — Thirty-Day Personal Dogfood Qualification

**Status:** `locked`<br>
**Depends on:** `B14`<br>
**Solo estimate:** 30 consecutive calendar days plus repair time<br>
**Evidence:** `quality/evidence/B15/`

**Objective:** Prove OMNI Personal Core earns daily use for thirty consecutive days without changing the qualified scope underneath the evidence.

**In scope**

- Freeze a release candidate and hardware/config manifest
- Use OMNI for genuine owner tasks every day
- Record starts, workflows, durations, corrections, failures, false successes, safety events, data integrity, recovery, and manual alternatives
- Repeat backup/restore and offline checks
- Fix blockers only through controlled candidate rebuild and reset affected evidence window
- Collect owner usefulness and annoyance notes

**Target paths**

- `quality/dogfood/protocol.json`
- `quality/dogfood/daily/`
- `quality/dogfood/incidents/`
- `quality/evidence/B15/`
- `quality/hardware/`

**Verification commands**

- `python scripts/dogfood.py validate --days 30`
- `python scripts/dogfood.py summarize`
- `python scripts/verify_artifact_identity.py`
- `python scripts/check_slos.py quality/dogfood/`

**Principal risks**

- Scope or artifact changes invalidate comparability
- Low daily sample volume can hide failures
- Self-reported success can be biased
- A personal build can be technically sound but not worth keeping active

**Exit gate**

- [ ] Thirty consecutive qualified days use the recorded candidate lineage
- [ ] At least 100 starts achieve 99% or better success
- [ ] Every locked workflow has at least 20 genuine runs and 95% or better completion
- [ ] Zero unsafe false successes, zero data loss, and no unresolved severe incident
- [ ] Offline and backup/restore drills pass repeatedly
- [ ] Owner elects to keep OMNI active for demonstrated value

### B16 — Exact-Artifact Final Audit and 10/10 Freeze

**Status:** `locked`<br>
**Depends on:** `B15`<br>
**Solo estimate:** 5-10 focused days after B15 plus independent review<br>
**Evidence:** `quality/evidence/B16/`

**Objective:** Audit, install, attack, recover, and score the exact distributable artifacts, then freeze the personal-core 10/10 evidence before any expansion begins.

**In scope**

- Freeze version, source revision, artifacts, checksums, SBOM, models, configuration, hardware, and evidence
- Install artifacts on clean primary and declared development environments
- Re-run package, workflow, security, no-egress, migration, recovery, accessibility, performance, documentation, and dogfood gates
- Conduct independent final review
- Set only proven capability lifecycle states and category scores
- Publish immutable limitations and post-10 baseline

**Target paths**

- `dist/`
- `quality/release-manifest.json`
- `quality/sbom/`
- `quality/evidence/B16/`
- `quality/capabilities.json`
- `quality/scorecard.json`
- `quality/policy.json`
- `docs/RELEASE_NOTES.md`

**Verification commands**

- `python scripts/final_audit.py --manifest quality/release-manifest.json`
- `python scripts/verify_release_manifest.py --exact`
- `python scripts/no_egress_test.py --manifest quality/release-manifest.json`
- `python scripts/check_all_gates.py B00 B01 B02 B03 B04 B05 B06 B07 B08 B09 B10 B11 B12 B13 B14 B15 B16`

**Principal risks**

- Source tests can pass while artifacts fail
- Last-minute rebuilds invalidate hashes and dogfood lineage
- Pressure to call 10/10 can weaken a gate

**Exit gate**

- [ ] Exact artifacts install and pass every required gate on clean target systems
- [ ] All ten workflows, security, offline, recovery, accessibility, performance, and docs checks pass against artifact hashes
- [ ] Every 10/10 score has direct immutable evidence
- [ ] No open blocker or unaccepted severe finding remains
- [ ] Personal-core scope and evidence are formally frozen
- [ ] Policy unlocks E01-E10 evaluation only after closure

## Post-10 Expansion Queue

These items remain locked until B16 closes the exact-artifact 10/10 freeze. A listed idea is not a promise or working-capability claim.

| Expansion | Title | Independent promotion gate |
|---|---|---|
| `E01` | Proactive intelligence | Owner-configured triggers, explanations, cooldowns, quiet hours, opt-out, and measured acceptance must add value without annoyance. |
| `E02` | Wake-word operation | Hardware-specific recall, false-positive, resource, privacy, mute, and no-egress requirements must pass before always-listening promotion. |
| `E03` | Qualified multimodal vision | One real model must pass curated accuracy, latency, hardware, provenance, capture-consent, retention, and offline gates. |
| `E04` | Secure mobile and remote companion | Mutual identity, strong pairing, revocation, replay resistance, least privilege, encrypted transport, and external review must pass. |
| `E05` | Real external integrations | Each service needs real setup, least scopes, token lifecycle, revocation, consent, effect verification, rate/error behavior, and privacy disclosure; canned connectors do not qualify. |
| `E06` | Skill SDK and marketplace | Signed publisher identity, package integrity, permission review, isolation, compatibility, rollback, removal, and supply-chain review must pass. |
| `E07` | Encrypted multi-device sync | Threat model, key lifecycle, transport, identity, conflicts, deletion, recovery, and independent cryptographic review must pass. |
| `E08` | Autonomous skill and code generation | Generated code remains untrusted and must pass isolation, review, tests, bounded permissions, rollback, and owner-approval gates. |
| `E09` | Additional platform qualification | A platform is supported only after clean install, hardware, workflow, security, accessibility, recovery, and artifact gates match the primary-platform standard. |
| `E10` | Optional commercial validation | Separate track requiring a narrow segment, real external users, retention, support, distribution, willingness-to-pay, legal/privacy work, and defensibility evidence; it never inflates personal-core evidence. |

## Freeze and Claim Rules

- Execute one batch at a time in the declared order.
- Do not start the next batch until the current batch has implementation, tests, audit, documentation, evidence, and exit-gate approval.
- A passing test is evidence for only the behavior and environment it actually exercised.
- Absence of a defect report is not evidence of correctness.
- The exact release artifact, not a mutable source checkout, is the final qualification subject.

- Evaluate one expansion independently against owner value, maintenance cost, privacy, risk, and fit with the core promise.
- A new feature starts experimental; it cannot inherit stable status from the core release.
- Every expansion must define availability, result states, consent, timeouts, cancellation, verification, tests, documentation, telemetry boundaries, and removal policy before promotion.
- Expansion failure must not regress a qualified core workflow.
- Commercial validation remains a separate optional track and cannot retroactively inflate the personal-core score.
