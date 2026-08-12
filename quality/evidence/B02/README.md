# B02 — Install, Configuration, and Startup Qualification progress

**Decision:** amended implementation draft; batch remains `in_progress` and fail-closed<br>
**Primary target:** NVIDIA DGX Station for Windows, native Windows 11 Arm64<br>
**Secondary qualification host:** native Windows 11 x64 laptop/workstation<br>
**Available agent host:** Linux x86_64, developer evidence only<br>
**Next authority:** B03 remains locked

The machine-readable ledger and current gate decision are in [`progress.json`](progress.json). This directory deliberately does **not** contain `closure.json`. B02 cannot close unless complete native Arm64 and x64 unattended lanes pass for the same exact commit and the aggregate verifier accepts both evidence bundles.

## Amended evidence matrix

| Lane | Role | Current result |
|---|---|---|
| Windows 11 Arm64 | Native architecture-equivalent B02 evidence for the primary target | Not run; required |
| Windows 11 x64 | Secondary hardware-independent qualification on the available class of laptop/host | Diagnostic attempts only: `7eb6e1481ec585b24224d130085c3b81091d3fd6` exposed incompatible PowerShell architecture detection; later `5c2bb341226ca655624d5bef1e31bc7ae3a7803c` attempts cleared native architecture, CPython 3.11 x64, Node 22.22.2 x64, and exact-commit isolation before exposing a locale-dependent pip-report decode in the resolver; UTF-8 correction added, clean corrected-commit rerun required |
| Linux x86_64 | Development tests and lifecycle smoke only | Prior checkpoint passed selected gates; never product evidence |
| Physical DGX Station | GPU/model/device throughput, performance, and sustained owner use | Deliberately deferred to B11, B13, B15, and B16 |

An x64 pass does not qualify Arm64. x64 emulation on Arm64 is not native evidence. Hosted Arm64 evidence does not qualify physical DGX hardware behavior.

## Unattended path

`scripts/qualify_b02.ps1` is the single B02 driver. For each native lane it is intended to create a detached worktree for an exact commit, resolve all six dependency profiles twice, compare exact architecture-specific locks, install twice, start twice, restart, perform authenticated readiness, stop, safely uninstall, explicitly remove isolated data, repeat uninstall, run Python/configuration/package/frontend gates, preserve evidence externally, and clean up. Package qualification builds with `python -m build --no-isolation` inside the exact dev environment; the sdist install test preinstalls that same hashed lock and disables build isolation, so no hidden package-build dependency resolution can count as evidence.

`hosted-windows-qualification.workflow.yml` is an inactive, owner-installable workflow template for hosted `windows-11-arm` and `windows-latest` attempts with exact CPython 3.11.9 and Node.js 22.22.2. The Arena credential cannot add `.github/workflows`, so this commit makes no hosted-run claim. If a repository owner activates the unchanged template, the standard hosted x64 image may be Windows Server; its ProductType then fails closed and it is diagnostic evidence only, never a replacement for the required Windows 11 x64 laptop run. The aggregate rejects missing, malformed, duplicate, wrong-commit, wrong-architecture, non-workstation, failed, or digest-mismatched lane evidence. Combine a same-commit native Arm64 result with the laptop result for the authoritative aggregate. Only a valid two-lane aggregate may print `ALL SYSTEMS GO — B03 UNLOCKED`.

## Current truth boundary

The amended Linux developer gates now include 54 passing install/lifecycle contract tests, clean exact-dev installation/audits, passing package/frontend/configuration/governance checks, and a truthful dependency boundary for `omni_v2/tests`. Running that broad suite in the exact dev environment produced `655 passed, 33 skipped, 9 failed`: all nine failures are OpenCV-dependent security tests, while the dev profile intentionally omits OpenCV and other optional all-runtime dependencies. The unattended qualifier therefore runs the broad suite only after installing and layering the exact `all` profile over the exact dev test-tool environment; it does not silently augment the dev lock. A separate exact Linux `all` installation stopped while building `dlib`, `evdev`, and `PyAudio` because this host lacks required Python/native development prerequisites, so no exact-all broad-suite result exists. The earlier `664 passed, 33 skipped` run used a disclosed same-version headless OpenCV substitution and remains diagnostic regression evidence only, not exact-lock evidence. A synthetic Linux dev lock differing only by selecting declared-compatible `setuptools==81.0.0` was used to exercise the final no-isolation build/sdist path locally; native Windows must generate and validate its own exact locks. These Linux results do not validate Windows behavior.

The first native Windows x64 invocation exposed and stopped on a real Windows PowerShell 5.1 compatibility defect before evidence initialization. The platform helper now obtains native/process architecture from Windows environment identities with CIM and reflection fallbacks rather than directly resolving modern-only `RuntimeInformation` properties. Subsequent exact-commit attempts proved that correction on the x64 laptop, then failed closed on an unqualified default Python, global Node 24, and finally a real resolver defect after explicitly selecting native CPython 3.11.9 and portable Node 22.22.2. The resolver had decoded pip's UTF-8 JSON report with Windows' cp1252 locale default; it now reads machine-generated JSON explicitly as UTF-8, and the qualifier prefers `py -3.11` over an unrelated default `python`. These are diagnostic failures, not lane evidence. A clean corrected-commit rerun is still required; no passing native lane exists. Static PowerShell/workflow-template inspection is not execution evidence.

B02 is not closed. B03 has not started. No product-platform, physical-DGX, release, exact-all broad-suite, offline no-egress, or 10/10 claim is made.
