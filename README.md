# OMNI Personal Core

> **Status: pre-alpha recovery. Not release-ready. No capability is currently qualified as stable.**
>
> **Execution:** B00 is closed. B01 is ready but has not started; the feature freeze remains active.

OMNI is a personal, local-first assistant under active reconstruction. The intended product is deliberately narrower than the repository's historical “AGI” and “100+ tools” language: one owner, one qualified Windows 11 x64 machine, and ten safe daily desktop, file, browser, memory, scheduling, and voice workflows.

The repository contains substantial working code and tests, but it also contains overlapping implementations, optional backends, demos, placeholders, stubs, unsafe successful fallbacks, broken packaging, and unqualified platform paths. Those are tracked openly rather than counted as finished features.

## Current Source of Truth

| Question | Authoritative answer |
|---|---|
| What is in scope? | [Capability matrix](docs/CAPABILITY_MATRIX.md) generated from [`quality/capabilities.json`](quality/capabilities.json) |
| How good is it now? | [Quality scorecard](docs/QUALITY_SCORECARD.md) generated from [`quality/scorecard.json`](quality/scorecard.json) |
| What is the execution plan? | [Locked B00–B16 batches](docs/EXECUTION_BATCHES.md) and the [10/10 quality plan](docs/OMNI_10_OUT_OF_10_PLAN.md) |
| What changes are allowed? | Feature-freeze and post-10 policy in [`quality/policy.json`](quality/policy.json) |
| What does the repository contain? | Reproducible [`quality/inventory.json`](quality/inventory.json) |

Historical phase reports, architecture diagrams, API references, audit snapshots, and changelogs describe earlier intent or implementation snapshots. They do **not** override the files above and are not release evidence.

## Locked Personal-Core Promise

OMNI aims to become:

> A local-first personal assistant for one owner that safely handles a deliberately limited set of daily desktop, file, browser, memory, scheduling, and voice workflows, and reports unavailable or failed work truthfully.

The ten locked workflows are:

1. Real daily briefing from explicitly configured sources.
2. Persistent reminder lifecycle.
3. Local document retrieval with source paths.
4. Safe file creation/editing with preview and verification.
5. Browser navigation/search in an isolated profile.
6. Approved application and window control.
7. Timed focus session with state restoration.
8. Inspectable personal session recall.
9. Push-to-talk local voice task with verified local TTS.
10. Truthful degraded behavior when an optional component is absent.

All ten are currently **not qualified**. Their measurable outcomes and qualification batches are in the [capability matrix](docs/CAPABILITY_MATRIX.md).

## What Exists Today

The source tree includes real or partial implementations for local model loading, planning and execution, memory stores, profile/session persistence, local calendar and contacts, scheduling, file and Windows actions, browser automation, voice capture/STT/TTS, guardrails, a credential vault, FastAPI, Next.js, desktop UI variants, backup/restore, and other experimental subsystems.

That implementation breadth is not the same as release readiness:

- The runtime plugin loader currently creates 16 wrapper instances and includes a duplicate; aliases are not independent tools.
- Gmail, calendar, smart-home, weather, and related connectors in `omni_v2/tools/integrations.py` include canned/demo behavior.
- Voice cloning records samples and metadata but does not train or run a cloned voice model.
- End-to-end encrypted sync is a disabled stub.
- MCP, mobile, marketplace, autonomous generation, vision, wake word, remote access, and similar surfaces remain experimental or unavailable until their gates pass.
- A fallback must not report success unless it performed and verified the requested effect. Existing violations are blockers.

See the generated matrix for every capability's lifecycle, implementation reality, source ownership, and known gaps.

## Platform and Installation Status

| Platform | Current claim |
|---|---|
| Windows 11 x64 | Primary target, **not yet qualified** |
| Linux | Development-only and unqualified as a product |
| macOS | Unsupported and unverified |

There is currently **no supported clean installation path**. Known blockers include unresolved Python dependency constraints, an incomplete wheel, divergent installers, and broken launcher assumptions. Do not treat `pip install -e .`, `start.bat`, or `start.sh` as release-qualified setup instructions. Installation and startup are scheduled for B01–B02.

## Privacy and Network Truth

“Local-first” does not currently mean “no network traffic under every configuration.”

| Surface | Current behavior |
|---|---|
| Local stores, profile, memory, calendar, contacts, and many core actions | Designed to operate on local data |
| Local LLM/STT/TTS backends | Can be local when installed and explicitly selected |
| Edge TTS | Online service; text leaves the machine when selected |
| Model/package/browser downloads | Require network access |
| Web research, remote access, messaging, mobile/LAN, marketplace, MCP, and external integrations | Network-capable, optional, experimental, or demo depending on the subsystem |
| Enforced offline mode | Not yet implemented and no no-egress release test currently passes |

Do not provide sensitive data to an unreviewed build. API authentication, consent enforcement, dependency vulnerabilities, logging/redaction, and remote exposure remain open security work.

## Reproducible Quality Inventory

The B00 generator uses only Python's standard library for deterministic inventory and documentation generation:

```bash
python scripts/quality_baseline.py generate
python scripts/quality_baseline.py check
```

To capture environment-dependent baseline probes (dependency resolution, wheel contents, Python tests, backend-live checks, frontend lint/build/audit, and runtime tool inventory):

```bash
python scripts/quality_baseline.py capture
```

Full probe output is written to ignored `quality/.local/`. A concise reviewed result may be published explicitly with `--publish <path>`. A failing probe is expected at this stage and must remain visible; baseline capture is not a claim that the build passes.

## Development Warning

Development currently requires manual environment repair and does not represent a fresh install. If you already have a prepared environment, useful diagnostics are:

```bash
python -m compileall -q omni_v2 omni backend_fastapi
python -m pytest -q
cd frontend_next && npm run build
```

Results depend on installed optional dependencies, models, services, hardware, current time, and platform. Record the exact command and environment when reporting a result. Frontend lint is not configured for unattended execution, backend-live tests can skip when no service is running, and a manually repaired environment is not packaging evidence.

## Repository Map

```text
omni_v2/             Principal Python implementation and tests
backend_fastapi/     HTTP/WebSocket API surface
frontend_next/       Next.js interface
mobile/              Experimental PWA companion
omni/                 CLI package
quality/              Scope, scorecard, policy, inventory, and evidence
docs/                 Current quality docs plus labeled historical material
scripts/              Installers and quality tooling
_archive/             Excluded legacy/hackathon material
```

## Release Standard

OMNI Personal Core is not “10/10” until all batch gates B00–B16 close in order. Final qualification requires, among other gates:

- Exact release artifacts installed and tested outside the checkout.
- Every locked workflow completed at least 20 times with at least 95% success.
- Zero unsafe false successes and zero data-loss incidents.
- Enforced offline mode passing a no-egress test.
- Backup/restore and degraded recovery proven.
- Thirty consecutive days of genuine owner dogfooding.
- Exact-artifact final audit and evidence freeze.

New end-user features remain frozen until that foundation closes. Commercial validation is a separate optional post-10 track and is not implied by this personal build.

## License

[MIT](LICENSE). The license permits use; it does not certify security, fitness, privacy, or production readiness.
