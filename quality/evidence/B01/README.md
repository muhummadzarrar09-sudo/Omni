# B01 — Dependency and Package Rescue closure

**Decision:** closed on 2026-08-11<br>
**Qualified boundary:** CPython 3.11.2 on Linux x86_64; Node.js 22.22.3/npm 12.0.2 for the frontend gate<br>
**Next authority:** B02 is ready, not started

The machine-readable decision and complete command ledger are in [`closure.json`](closure.json). This directory records B01 facts; it does not claim a release, cross-platform qualification, or whole-product readiness.

A later B02 native audit exposed that the package's `setuptools>=77,<82` build constraint forced a vulnerable backend. [`build-backend-security-amendment-2026-08-12.json`](build-backend-security-amendment-2026-08-12.json) preserves the original closure as historical evidence while governing the forward correction to `setuptools>=83,<85`. The failed native run remains failed; no advisory was waived.

## Exit-gate result

| Requirement | Result | Evidence |
|---|---:|---|
| Every declared profile resolves on supported Python | Pass | [`profile-resolution.json`](profile-resolution.json) and six exact hashed locks under `requirements/locks/cpython-3.11-linux-x86_64/` |
| Built artifact installs cleanly and imports | Pass | [`installed-artifact-smoke.json`](installed-artifact-smoke.json) |
| Installed CLI works outside the checkout | Pass | [`installed-artifact-smoke.json`](installed-artifact-smoke.json) |
| Wheel and sdist contain every runtime package/resource | Pass | [`package-contents.json`](package-contents.json) |
| Production imports map to declared profiles | Pass | `tests/package/test_package_metadata.py` |

All five B01 exit-gate conditions passed. B01 is therefore closed. B02 is only marked ready; this batch did not claim B02's idempotent installer or lifecycle qualification.

## Qualified artifacts

The final local artifacts are intentionally not treated as a public release:

| Artifact | SHA-256 | Size | Members |
|---|---|---:|---:|
| `omni_agi-3.2.0-py3-none-any.whl` | `55a29affff56591e5e2bff10c5d43b91579e1f11383ae6e1ada4b562aecb3461` | 495,796 bytes | 197 |
| `omni_agi-3.2.0.tar.gz` | `48e19771aeee1cef8e7c831c2713aefd44b842be42a26c765b987840646b8ca5` | 410,280 bytes | 207 |

Both contain all 190 source-derived runtime files and pass `twine check`. The wheel's metadata declares version `3.2.0`, Python `>=3.11,<3.12`, and the `core`, `voice`, `vision`, `desktop`, `dev`, and `all` extras.

## Resolution and install evidence

Exact CPython 3.11/Linux x86_64 resolution counts are:

- core: 36 distributions
- voice: 90 distributions
- vision: 88 distributions
- desktop: 26 distributions
- dev: 92 distributions
- all: 219 distributions

The final development environment was installed from `dev.txt` with `--require-hashes`; `pip check` reported no broken requirements. The isolated wheel smoke installed `core.txt`, changed to a temporary directory outside the checkout, disabled bytecode writes, and verified:

- imports of `omni`, `omni_v2`, and `backend_fastapi` from site-packages;
- `omni --help`, CLI engine dispatch, and optional-profile install guidance;
- both packaged HTML resources;
- backend health and explicit experimental qualification;
- the data root outside the installed package tree;
- an empty external working directory after probes; and
- no mutation of the 388-file installed package tree.

## Supply-chain evidence

- [`python-vulnerability-audit.json`](python-vulnerability-audit.json): 87 exact dev-lock dependencies, zero known vulnerabilities, and zero fixes at capture time.
- [`python-license-inventory.json`](python-license-inventory.json): all 91 expected distributions inventoried with no missing, mismatched, or unknown records. `docutils==0.23` and `qrcode==8.2` remain review-required. This is inventory completeness, not legal advice.
- [`frontend-dependency-tree.json`](frontend-dependency-tree.json): clean npm 12 tree with 1,005 dependency edges, 469 unique name/version pairs, and no reported problems.
- [`frontend-vulnerability-audit.json`](frontend-vulnerability-audit.json): zero known vulnerabilities at capture time.
- npm reported no unreviewed install scripts; the reviewed `unrs-resolver@1.12.2` native-binding postinstall is explicitly allowlisted.
- Frontend zero-warning lint and the 24-route Next.js production build passed.

## Disclosed non-gate failure

The complete Python test collection is deliberately recorded as a failing diagnostic, not rewritten as a pass: **668 passed, 33 skipped, and 10 failed in 33.68 seconds**. See [`broad-test-diagnostic.json`](broad-test-diagnostic.json).

The failures are one date-bound calendar fixture and nine optional OpenCV/face-security cases in the exact dev environment. They do not invalidate the narrower B01 artifact gate, but they do prevent a whole-product quality pass and remain assigned to B03. No B01 assertion says that the whole repository is green.

## What remains unqualified

- Python outside `>=3.11,<3.12`, Windows, macOS, and non-x86_64 Linux
- native libraries, models, devices, and actual workflows for optional profiles
- PyPI publication, signed releases, tags, release channels, and downstream installs
- installer idempotency and start/stop/restart behavior (B02)
- a green broad suite and CI enforcement (B03)
- frontend interaction/accessibility behavior
- whole-product reliability, privacy, security, or 10/10 status

B01 repairs and verifies the package foundation only. All later batches, the dogfood window, and the exact-artifact final audit remain mandatory.
