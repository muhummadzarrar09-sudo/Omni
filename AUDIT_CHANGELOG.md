# OMNI Audit Changelog

This file records audit/remediation batches. Detailed status lives in `AUDIT_TRACKER.md`.

## Batch 2026-07-19 — P1 state integrity and edge validation

- Added FastAFStore locking around skill registration and semantic lookup.
- Made user-profile multi-field updates atomic and added fsync before replacement.
- Made notification-preference bulk updates atomic.
- Hardened scheduler IDs, validation, atomic persistence, one-shot cleanup, and shutdown.
- Added shutdown handling for scheduler, screen watcher, notification center, wake-word service, and mDNS.
- Migrated multiple runtime modules away from working-directory-dependent data paths.
- Added consistent API error helper to selected mutating endpoint families.
- Fixed guardrail docstring warnings and hardware-test return-value warnings.
- Added geofence validation for coordinates, radius, rule command length, and timing values.

## Verification

- `pytest -q`: 320 passed, 35 skipped, 0 failed, 0 warnings.
- Remaining skipped tests are environment-dependent hardware/optional-dependency cases.

## Outstanding

- Cross-process locks for JSON stores.
- Full HTTP status migration across all endpoint families.
- Voice/audio lifecycle teardown.
- Chroma/DuckDB concurrent initialization.
- Marketplace install race tests.
- Full clean-install and multi-process stress pass.

## Batch 2026-07-19 — state validation and test determinism

- Added geofence coordinate/radius/rule validation.
- Made profile multi-field updates one atomic locked write.
- Made notification preference bulk updates one atomic locked write.
- Added FastAFStore locking around registration and lookup.
- Made opinion rate-limit test deterministic by controlling randomness instead of relying on timing/random chance.
- Verification: `pytest -q` — 320 passed, 35 skipped, 0 failed, 0 warnings.


## Batch 2026-07-19 — HTTP contract migration (profile/personality/onboarding/notifications)

- Migrated selected profile, personality, onboarding, and notification endpoint failures away from HTTP 200 application errors.
- Invalid input now maps to HTTP 400 where the handler raises `ValueError`.
- Unexpected failures are logged server-side and return a generic HTTP 500 response.
- Raw exception strings are no longer returned from those endpoint families.
- Verification: `pytest -q` — 320 passed, 35 skipped, 0 failed, 0 warnings.


## Batch 2026-07-19 — HTTP contract migration (vision/voice/network/mobile/screen)

- Migrated selected vision, voice-clone, network, mobile, and screen endpoint failures away from HTTP 200 application errors.
- Invalid values map to HTTP 400 where validation raises `ValueError`.
- Unexpected failures are logged server-side and return generic HTTP 500 responses.
- Raw exception details are no longer returned by the migrated endpoint families.
- Verification: `pytest -q` — 320 passed, 35 skipped, 0 failed, 0 warnings.

## Batch 2026-07-19 — HTTP contract migration (demo/execute/PTT/WebSocket)

- Migrated selected demo, core execute, PTT, and WebSocket-adjacent endpoint failures away from HTTP 200 application errors.
- Invalid values map to HTTP 400 where validation raises `ValueError`.
- Unexpected failures are logged server-side and return generic HTTP 500 responses.
- Verification: `pytest -q` — 320 passed, 35 skipped, 0 failed, 0 warnings.

## Batch 2026-07-19 — API input bounds

- Added bounded Pydantic fields for execute commands, scheduler names/commands, vision paths/queries, skill IDs, and voice-training inputs.
- Added bounded query parameters for memory, notification, geofence, and screen list endpoints.
- Added skill ID character validation to prevent path/control-character abuse.
- Verification: `pytest -q` — 320 passed, 35 skipped, 0 failed, 0 warnings.

## Batch 2026-07-19 — resource lifecycle and marketplace install integrity

- Added `FastAFStore.close()` for SQLite/DuckDB connection cleanup.
- Marketplace downloads now enforce the 50KB cap by reading one byte beyond the limit.
- Marketplace files are written to a temporary download path and atomically replaced only after the complete payload arrives.
- Verification: `pytest -q` — 320 passed, 35 skipped, 0 failed, 0 warnings.

## Batch 2026-07-19 — final lifecycle wiring and release verification

- Registered FastAFStore cleanup in FastAPI shutdown lifecycle.
- FastAFStore database handles now close during application shutdown.
- Completed marketplace atomic-download, size-limit, and failure-cleanup path.
- Re-ran compilation and full test suite.
- Verification: `pytest -q` — 320 passed, 35 skipped, 0 failed, 0 warnings.

## Batch 2026-07-19 — release hygiene and privacy contract

- Removed committed runtime memory/vector database artifacts.
- Added ignore rules so runtime data is not re-committed.
- Removed the contradictory PyAudio dependency from the backend requirements.
- Remaining privacy documentation must explicitly identify Edge TTS as an online optional backend; offline mode requires a local TTS backend.
