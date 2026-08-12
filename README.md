# OMNI Personal Core

> **Status: pre-alpha recovery. Not release-ready. No capability is currently qualified as stable.**
>
> **Execution:** B00 and B01 are closed. B02 is active but not qualified; the feature freeze remains active.

OMNI is a personal, local-first assistant under active reconstruction. The intended product is deliberately narrower than the repository's historical “AGI” and “100+ tools” language: one owner, one NVIDIA DGX Station for Windows running Windows 11 Arm64, and ten safe daily desktop, file, browser, memory, scheduling, and voice workflows. A Windows 11 x64 laptop is a secondary hardware-independent qualification host, not the product target.

The repository contains substantial working code and tests, but it also contains overlapping implementations, optional backends, demos, placeholders, stubs, unsafe successful fallbacks, unqualified startup paths, and unqualified product platforms. Those are tracked openly rather than counted as finished features.

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

| Environment | Current claim |
|---|---|
| NVIDIA DGX Station for Windows, Windows 11 Arm64 | Primary product target, **not yet qualified**; native Arm64 B02 evidence and later physical-DGX hardware gates are absent |
| Windows 11 x64 | Secondary hardware-independent qualification/development host, **not** a substitute for Arm64 or physical DGX evidence |
| CPython `>=3.11,<3.12` on Linux x86_64 | B01-qualified for dependency resolution, exact-lock installation, artifact installation, package imports, lightweight CLI paths, packaged resources, and backend health smoke |
| Linux | Package-development environment only; not qualified as an end-user product |
| macOS | Unsupported and unverified |

B01 establishes a reproducible **local-artifact package path**, not a qualified product installation. There is no qualified PyPI release. Native B02 x64 diagnostics remain failures: `f8908503` exposed vulnerable `setuptools==81.0.0`, and `4bc1c9d` then cleared resolution/exact-dev gates but stopped when full installation reached native source builds without the contracted Visual C++ toolchain. The corrected path now uses architecture-specific, hash-governed wheel-only build locks; exact approved sdist sets; native compiler/linker/SDK and PE-target probes; no build isolation or cache; exact installed-environment parity; and strict failure-path cleanup. None of that is a passing Windows run. B02 remains **unqualified until native Windows 11 Arm64 and x64 lanes pass against the same exact commit and their evidence aggregates successfully**. An x64-only pass cannot unlock B03. Physical DGX GPU/model throughput and sustained use remain later B11/B13/B15/B16 gates. Follow [installation and troubleshooting](docs/TROUBLESHOOTING.md). Do not use `pip install -e .` as package evidence, and do not call `start.bat` or `start.sh` release-qualified before the B02 gate closes.

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

## B01 Package Evidence

B01 closed the dependency and package-rescue gate on 2026-08-11 for its deliberately narrow environment:

- CPython 3.11.2 on Linux x86_64; Python 3.10, Python 3.12+, PyPy, Windows, and macOS are not claimed.
- Six resolver profiles (`core`, `voice`, `vision`, `desktop`, `dev`, and `all`) with exact hash-locked Linux files.
- One wheel and one sdist containing all 190 required runtime files, with metadata validation and no forbidden runtime-data payload.
- Isolated wheel installation outside the checkout using the exact `core` lock; imports, CLI, package resources, backend health, clean working directory, and installed-tree immutability passed.
- Python development-lock vulnerability audit: 87 dependencies, zero known vulnerabilities. License inventory: 91 records complete; `docutils==0.23` and `qrcode==8.2` still require review.
- Node 22.22.3/npm 12.0.2 clean frontend install, dependency tree, audit, lint, and production build passed; the tracked npm audit has zero known vulnerabilities.

The original closure remains historical evidence. Its [forward security amendment](quality/evidence/B01/build-backend-security-amendment-2026-08-12.json) records the later `setuptools` build-backend floor correction discovered by B02; it does not convert the failed native run into a pass.

This is not a whole-product quality pass. The latest broad Python run measured **668 passed, 33 skipped, and 10 failed**: one wall-clock calendar boundary failure and nine optional-vision/security failures in an environment without OpenCV/face fixtures. Those failures remain visible for B03; no B01 package gate was weakened to hide them. See [`quality/evidence/B01/`](quality/evidence/B01/) for the closure record and raw summaries.

## Reproducible Development Environment

Use the exact B01 Linux development lock rather than repairing an environment package by package:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --require-hashes \
  -r requirements/locks/cpython-3.11-linux-x86_64/dev.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q tests/package
```

Frontend commands require Node `>=22.22.2 <23`; exact npm `12.0.2` is invoked through Corepack, so a different global npm is ignored. The complete reviewed sequence is in [installation and troubleshooting](docs/TROUBLESHOOTING.md). Results outside the qualified interpreter, operating system, architecture, lock, or exact local artifacts are not B01 evidence. Optional models, services, native libraries, and hardware remain separately unqualified.

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
