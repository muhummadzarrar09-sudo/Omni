# OMNI Living Audit Tracker

Baseline audit date: 2026-07-18
Repository: muhummadzarrar09-sudo/Omni

## Baseline gate

- pytest: 321 passed, 33 skipped, 1 failed
- Known failing test: `omni_v2/tests/test_skill_synthesis.py::test_skill_synthesis`
- Static compilation: passes
- Runtime databases are committed
- No production authentication boundary

## Operating rule

Every fix must include:

1. A minimal regression test.
2. An edge-case test.
3. Documentation update where behavior changes.
4. A clean test run.
5. A second audit pass after the batch.

Do not mark an item done because a happy-path test passes. It must pass failure, concurrency, malformed-input, restart, and no-optional-dependency cases where applicable.

## P0 — block dangerous behavior

- [x] P0-01 Verify every downloaded/generated skill before import.
- [x] P0-02 Remove arbitrary Python execution from marketplace installation or isolate it in a subprocess sandbox.
- [x] P0-03 Sandbox file reads, writes, vision paths, and uploaded-file access. (HTTP vision path and FilesTool paths hardened; upload byte caps remain in the next batch.)
- [x] P0-04 Add authentication to mutating HTTP and WebSocket operations. (Token-enforced when `OMNI_API_TOKEN` is configured; device tokens accepted after pairing; WebSocket query-token and message-size checks added.)
- [x] P0-05 Fix pairing verification: issued-code lookup, expiry, one-time use, device token. (Issued/expiry/one-time validation and 30-day device-token issuance implemented.)
- [x] P0-06 Default server to loopback; require explicit LAN mode.
- [x] P0-07 Fix `/api/execute/stream` duplicate execution and apply common authorization/rate limiting. (Duplicate execution and rate-limit bypass fixed; token middleware applies to mutating stream requests.)
- [x] P0-08 Remove interpreters/package managers from generic shell allowlist.
- [x] P0-09 Stop returning success for failed subprocesses.

## P1 — correctness and state integrity

- [ ] P1-01 Remove or correct `SkillRegistry` singleton injection bug.
- [ ] P1-02 Remove unsafe singleton state from profile/geofence/marketplace components.
- [ ] P1-03 Centralize all storage paths through `DATA_DIR`. (Scheduler path corrected; remaining modules still need migration.)
- [x] P1-04 Fix scheduler task ID collisions, one-shot cleanup, command validation, and restart behavior. (Unique UUID IDs, atomic persistence, one-shot removal, shutdown added; command validation remains in the next validation batch.)
- [ ] P1-05 Add lifecycle shutdown for wake word, scheduler, mDNS, notification, screen, and audio services. (Scheduler, wake-word, and mDNS shutdown hooks added; notification/screen/audio remain.)
- [ ] P1-06 Fix incorrect action aliases; unsupported actions must fail explicitly.
- [ ] P1-07 Use proper HTTP status codes for application failures.
- [ ] P1-08 Remove global rate limiter; use bounded per-client limiting.
- [ ] P1-09 Bound all upload and file reads before allocation.
- [ ] P1-10 Reuse Whisper/STT models instead of loading per request.

## P1 — marketplace and supply chain

- [ ] P1-11 Add skill hash/signature verification.
- [ ] P1-12 Download to temporary files and atomically install only after verification.
- [ ] P1-13 Never report offline stubs as successful real installations.
- [ ] P1-14 Prevent GET marketplace calls from mutating global index objects.
- [ ] P1-15 Make uninstall remove registry/plugin state, not only the file.
- [ ] P1-16 Add publisher/version/dependency validation.

## P2 — privacy and product-contract correctness

- [ ] P2-01 Resolve Edge TTS versus offline/private claims.
- [ ] P2-02 Remove personal name/local IP from unauthenticated discovery metadata.
- [ ] P2-03 Ensure browser profile isolation, downloads, cookies, and allowed domains are explicit.
- [ ] P2-04 Remove committed runtime memory/database artifacts.
- [ ] P2-05 Unify dependency manifests and remove the PyAudio contradiction.
- [ ] P2-06 Unify version reporting.
- [ ] P2-07 Remove hardcoded `D:/Omni` from prompts and runtime fallbacks.

## P2 — validation and edge cases

- [ ] P2-08 Validate geofence coordinates, radius, NaN, infinity, and timezone behavior.
- [ ] P2-09 Validate scheduler cron, interval, date, timezone, past dates, and DST transitions.
- [ ] P2-10 Validate pairing URI/QR parsing, URL encoding, IPv6, ports, and malformed payloads.
- [ ] P2-11 Validate command length, Unicode controls, null bytes, normalization, and encoded traversal.
- [ ] P2-12 Validate corrupted JSON/SQLite/Chroma state and recovery behavior.
- [ ] P2-13 Validate concurrent profile/memory/notification writes.
- [ ] P2-14 Validate absent microphone, display, GPU, browser, Tesseract, and optional models.
- [ ] P2-15 Validate graceful shutdown and repeated startup/reload.

## P3 — release quality

- [ ] P3-01 Add CI test and static-analysis gates.
- [ ] P3-02 Replace hard-coded test-count documentation with CI status.
- [ ] P3-03 Mark archive code unsupported and keep it out of package discovery.
- [ ] P3-04 Replace broad exception swallowing around security/persistence with typed handling.
- [ ] P3-05 Redact secrets and personal data from logs/errors.
- [ ] P3-06 Add API contract tests generated from the documented API surface.
- [ ] P3-07 Add a clean-install smoke test from a fresh checkout.
- [ ] P3-08 Add a second audit report after every remediation batch.

## Required audit passes

### Pass A — security boundary

Authentication, authorization, local/LAN exposure, CORS, WebSocket security, file paths, shell execution, skill loading, uploads, secrets, logs.

### Pass B — correctness

Every API endpoint, every tool alias, every agent transition, success/failure propagation, retry behavior, timeouts, idempotency, duplicate execution.

### Pass C — state and concurrency

Singletons, global variables, persistence, atomic writes, corrupt state, simultaneous requests, restart/reload, background workers.

### Pass D — portability

Windows/Linux/macOS, working-directory changes, path separators, Unicode paths, permissions, missing optional dependencies, CPU-only operation.

### Pass E — product contract

README, docs, comments, API models, health responses, dependency manifests, version numbers, privacy/offline claims.

### Pass F — release gate

Fresh clone, clean install, no runtime artifacts, tests, static analysis, smoke tests, API contract tests, and documented known limitations.
