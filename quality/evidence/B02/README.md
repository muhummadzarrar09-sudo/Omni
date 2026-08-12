# B02 — Install, Configuration, and Startup Qualification progress

**Decision:** implementation hardened; batch remains `in_progress` and fail-closed<br>
**Primary target:** NVIDIA DGX Station for Windows, native Windows 11 Arm64<br>
**Secondary qualification host:** native Windows 11 x64 laptop/workstation<br>
**Available agent host:** Linux x86_64, developer evidence only<br>
**Next authority:** B03 remains locked

The machine-readable ledger is [`progress.json`](progress.json). This directory deliberately has no `closure.json`. B02 can close only after complete native Arm64 and x64 unattended lanes pass on the same exact commit and the aggregate verifier accepts both evidence bundles.

## Required evidence matrix

| Lane | Role | Current result |
|---|---|---|
| Windows 11 Arm64 | Architecture-equivalent software/control-plane evidence for the primary target | Not run; required |
| Windows 11 x64 | Hardware-independent qualification on the available laptop/workstation | Failed diagnostics only; latest run at `66843dd` stopped after exact-commit verification on a PowerShell interpolation parser error; cleanup passed and `d681ba8` corrects the parser defect |
| Linux x86_64 | Development tests only | Current exact-dev Python, package, frontend, static, and governance gates pass; never native Windows evidence |
| Physical DGX Station | GPU/model/device throughput, performance, and sustained owner use | Deliberately deferred to B11, B13, B15, and B16 |

An x64 pass cannot qualify Arm64. x64 emulation on Arm64 is not native evidence. Hosted Arm64 can be architecture-equivalent B02 evidence, but cannot qualify physical-DGX GPU, model, or sustained-use behavior.

## Current unattended contract

`scripts/qualify_b02.ps1` is the single lane and aggregate driver. Each lane must:

1. verify a clean exact commit and create an external detached worktree;
2. prove native Windows 11 workstation, PowerShell, CPython 3.11, Node 22, architecture-correct Visual Studio compiler/linker identities, explicit governed SDK `10.0.26100.0` selection, an executable probe, and its PE target;
3. bootstrap the architecture-specific wheel-only exact build lock with hashes, no cache, and no dependency resolution;
4. resolve all six profiles twice without third-party build isolation and compare byte-identical exact locks;
5. require the selected `all` sdists to equal the full reviewed architecture source-build contract (12 x64, 9 Arm64), including exact filenames and hashes;
6. audit and license-inventory the isolated build, exact dev, and exact all-runtime authorities, then reject missing, unexpected, conflicting, or version-drifted installed distributions;
7. run the configured Python suite, fatal Ruff gate, compilation, wheel/sdist build, artifact installation/content/metadata checks, and frontend clean-install/install-script/tree/audit/proxy/lint/build gates;
8. run installation, second installation, startup, idempotent second startup, restart, authenticated readiness, stop, preserving uninstall, explicit isolated-data removal, and repeated uninstall; and
9. attempt managed stop on every exit path, terminate only identity-recorded or unique-lane-owned survivors, remove generated environments/frontend outputs/data/worktree state, verify every cleanup invariant, and fail if cleanup is incomplete.

The exact build authority is `requirements/locks/cpython-3.11-windows-{x86_64|arm64}/build.txt` plus `quality/windows-native-build-contract.json`. Both versions and architecture-specific wheel hashes must agree. CMake and Ninja CLI identities are separately governed. Runtime/source builds use `--no-build-isolation --no-cache-dir`; default PEP 517 isolation and cached wheels cannot count as evidence.

`hosted-windows-qualification.workflow.yml` remains an inactive, owner-installable template because the Arena GitHub credential cannot add active workflow files. No hosted execution is claimed. A standard hosted x64 image may be Windows Server and will correctly fail the workstation gate; it cannot replace the required Windows 11 x64 laptop lane.

## Validation completed on the developer host

The latest Linux developer validation, after the source-build and cleanup hardening, reports:

- complete exact-dev Python suite: `738 passed, 36 skipped, 5 known deprecation warnings`;
- package suite against exactly one wheel and one sdist: `17 passed`;
- fatal Ruff gate (`E9,F63,F7,F82`): pass;
- frontend with Corepack npm `12.0.2`: 13 proxy tests, zero-warning lint, zero vulnerabilities, no unreviewed install scripts, and successful production build;
- focused install/package/governance tests, JSON parsing, Python compilation, changed PowerShell Tree-sitter parsing, an explicit unsafe `$Name:` interpolation regression scan, and `git diff --check`: pass at the current review checkpoint.

The exact Linux `all` profile still cannot be installed unchanged on this host because dlib, evdev, and PyAudio require unavailable native development prerequisites. That does not weaken or replace either required Windows lane. The broad repository Ruff scan is also not the B02 gate: it contains thousands of pre-existing style findings, while the defined fatal correctness subset passes.

## Failed native diagnostics retained as failures

Earlier x64 attempts exposed PowerShell 5.1 architecture detection, interpreter/Node selection, UTF-8 report decoding, and vulnerable setuptools authority defects. `f8908503` passed repeatable resolution and exact-dev installation before correctly failing on vulnerable `setuptools==81.0.0`. `4bc1c9d` used the corrected backend and reached full installation, where dlib and llama-cpp-python demonstrated that native source builds lacked a controlled Visual C++/CMake/Ninja contract.

The operator-reported external lane JSON for `66843dd` has `status=fail`, `cleanup_passed=true`, and only `detached_exact_commit` completed. PowerShell rejected the unbraced `$ArchitectureSlug:` interpolation in `scripts/windows_build_tools.ps1` before the native toolchain probe. Commit `d681ba8` braces that variable and adds a repository-wide regression that rejects unsafe unbraced variable/colon interpolation while allowing legitimate scoped forms. None of these failed runs is lane evidence.

The current implementation addresses the discovered failure classes with exact architecture build locks and wheel hashes, reviewed sdist equality, native toolchain and PE probes, exact installed-environment parity, correctly scoped audits/licenses, architecture capability exclusions, strict failure cleanup, and the interpolation regression. Those controls remain **unqualified implementation** until executed natively.

B02 is not closed. B03 has not started. No product-platform, physical-DGX, release, offline-no-egress, commercial-traction, or 10/10 claim is made.
