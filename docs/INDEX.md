# OMNI Documentation Index

> **Current product status: pre-alpha recovery.** This index separates authoritative quality state from historical or unqualified material. No document may override the machine-readable authorities in `quality/`.

## Start Here — Current and Authoritative

1. **[README](../README.md)** — Truthful project overview, boundaries, and current developer warnings.
2. **[Capability Matrix](CAPABILITY_MATRIX.md)** — Generated lifecycle, implementation-reality, workflow, platform, ownership, entry-point, requirements, test-type, data/network, interface-audit, and known-gap matrix.
3. **[Quality Scorecard](QUALITY_SCORECARD.md)** — Generated current scores, evidence, and 10/10 exit criteria.
4. **[OMNI 10/10 Plan](OMNI_10_OUT_OF_10_PLAN.md)** — Detailed sequential quality and release plan.

Machine-readable authorities:

- [`quality/capabilities.json`](../quality/capabilities.json) — Product promise, non-goals, platforms, workflows, lifecycle definitions, and capability status.
- [`quality/scorecard.json`](../quality/scorecard.json) — Evidence-backed category scores and closure gates.
- [`quality/policy.json`](../quality/policy.json) — Active feature freeze, claim rules, and post-10 protocol.
- [`quality/batches.json`](../quality/batches.json) — Locked B00–B16 and E01–E10 executable manifest.
- [`quality/inventory.json`](../quality/inventory.json) — Generated source, endpoint, tool-declaration, and code inventory.

Regenerate and validate the human-readable artifacts with:

```bash
python scripts/quality_baseline.py generate
python scripts/quality_baseline.py check
```

## Documentation Status Rules

- **Authoritative:** Defines current scope, status, policy, or quality gates.
- **Reference, unqualified:** May explain implementation but has not passed current command, API, architecture, privacy, or platform drift checks.
- **Historical:** Records prior intent, milestones, audits, or pull-request narratives. “Done,” “complete,” “product-grade,” performance, test-count, privacy, and readiness language in these files is not a current claim.
- **Generated:** Must be changed through its machine-readable source, not edited directly.

## Reference Material — Not Release-Qualified

| Document | Status | Use |
|---|---|---|
| [API.md](API.md) | Reference snapshot, unqualified | Earlier HTTP API descriptions; use `quality/inventory.json` for the generated route inventory until B06/B14 drift gates close. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Reference snapshot, unqualified | Earlier architecture narrative; several overlapping runtimes remain unresolved. |
| [AWAY_MODE.md](AWAY_MODE.md) | Experimental subsystem reference | Away/remote behavior is outside the locked personal core and has not passed security or autonomy qualification. |
| [DESKTOP_SECURITY.md](DESKTOP_SECURITY.md) | Experimental subsystem reference | Face/lockdown behavior and dependencies are not release-qualified. |
| [PERFORMANCE.md](PERFORMANCE.md) | Historical benchmark snapshot | Performance claims are not current target-hardware evidence. |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Reference snapshot, unverified | Commands and remedies require fresh-install validation in B01–B02/B14. |
| [JARVIS_BRAIN.md](JARVIS_BRAIN.md) | Historical/aspirational design | Does not establish production autonomy or human-level intelligence. |

## Historical Product and Milestone Documents

These files are retained for provenance only:

- [AIM.md](AIM.md) — Earlier demo-oriented AIM criteria.
- [ROADMAP.md](ROADMAP.md) — Earlier feature-focused roadmap, superseded by the quality plan for execution order.
- [CHANGELOG.md](CHANGELOG.md) — Earlier version narrative; not a release ledger for qualified artifacts.
- [PHASE_1_DONE.md](PHASE_1_DONE.md) — Profile/memory/greeting milestone narrative.
- [PHASE_2_DONE.md](PHASE_2_DONE.md) — Personality/opinion milestone narrative.
- [PHASE_3_DONE.md](PHASE_3_DONE.md) — Demo/onboarding/stats milestone narrative.
- [PHASE_4_DONE.md](PHASE_4_DONE.md) — Vision/voice-clone/marketplace/SDK milestone narrative; its “product-grade” wording is superseded.
- [PHASE_5_MOBILE.md](PHASE_5_MOBILE.md) — Mobile companion milestone narrative.
- [PHASE_6_VISUAL.md](PHASE_6_VISUAL.md) — Screen-context milestone narrative.
- [PR_SUMMARY.md](PR_SUMMARY.md), [FINAL_PR_DESCRIPTION.md](FINAL_PR_DESCRIPTION.md), and [FINAL_PR_DESCRIPTION_V16.md](FINAL_PR_DESCRIPTION_V16.md) — Historical change descriptions, not release evidence.
- [`FINAL_AUDIT_STATUS.md`](../FINAL_AUDIT_STATUS.md), [`AUDIT_TRACKER.md`](../AUDIT_TRACKER.md), and [`AUDIT_CHANGELOG.md`](../AUDIT_CHANGELOG.md) — Earlier audit snapshots; current blockers and scores live in the quality authorities.
- [`diagnostic/`](../diagnostic/) — Earlier diagnostic and remediation snapshots.

## Implementation Map

This is a navigation aid, not a statement that each module works end to end.

| Area | Primary paths | Current authority |
|---|---|---|
| Runtime and CLI | `omni_v2/app.py`, `omni_v2/core/`, `omni/` | `runtime.*` capabilities |
| Brain and agents | `omni_v2/llm/`, `omni_v2/agents/`, `omni_v2/engine/` | `brain.*` capabilities |
| Memory and personal data | `omni_v2/memory/`, `omni_v2/personal/` | `memory.*`, `personal.*` |
| Tools and automation | `omni_v2/tools/`, `omni_v2/automation/`, `omni_v2/schedule/` | `tools.*`, `automation.*`, `integrations.*` |
| Voice and vision | `omni_v2/voice/`, `omni_v2/vision/` | `voice.*`, `vision.*` |
| Security and vault | `omni_v2/security/`, `omni_v2/vault/`, guardrails | `security.*` |
| API | `backend_fastapi/` | `api.fastapi` plus generated endpoint inventory |
| Web/desktop UI | `frontend_next/`, `omni_v2/ui/`, `omni_v2/gui/` | `ui.*` |
| Mobile/network/sync | `mobile/`, `omni_v2/network/`, `omni_v2/sync/`, `omni_v2/mesh/` | Experimental/unavailable capability entries |
| Tests | `omni_v2/tests/` | Generated inventory and captured baseline; test presence is not release qualification |

## Current Test and Command Policy

Do not copy historical pass counts into current documentation. A test claim must identify the exact command, environment, result, and date. The current B00 baseline command is:

```bash
python scripts/quality_baseline.py capture
```

It records dependency resolution, wheel contents, Python compilation/tests, backend-live checks, frontend lint/build/audit, endpoint inventory, and runtime tool inventory. Non-passing probes remain blockers rather than being hidden behind aggregate counts.

## Missing Quickstart Is Intentional

The previous index linked to a nonexistent `QUICKSTART.md` and described unverified one-click setup. A release quickstart will be written only after B01–B02 prove clean installation, package contents, startup, restart, model handling, and primary-platform behavior.
