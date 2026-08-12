# B02 — Install, Configuration, and Startup Qualification progress

**Decision:** implementation complete on the available host; batch remains `in_progress` and externally blocked<br>
**Available host:** CPython 3.11.2 on Linux x86_64; Node.js 22.22.3/Corepack 0.34.6/npm 12.0.2<br>
**Required product host:** fresh native Windows 11 x64 workstation<br>
**Next authority:** B03 remains locked

The machine-readable command ledger and gate decision are in [`progress.json`](progress.json). This directory deliberately does **not** contain `closure.json`: B02 cannot close until the documented verifier passes on a fresh native Windows 11 x64 workstation against a native exact core lock.

## What passed on the available host

- The canonical configuration contract covers bind/connect URLs, exact origins, writable paths, model paths, STT/TTS settings, devices, offline request state, and environment-only secrets.
- The managed backend/frontend lifecycle passed real start, status, authenticated same-origin HTTP mutation, one-time-ticket WebSocket relay, restart, stop, state cleanup, and old-PID cleanup checks.
- The install suite passed 52 tests, including lifecycle, preflight, runtime CLI, Windows script boundaries, safe uninstall contracts, backend authentication, model cache/offline boundaries, and proxy-source contracts.
- The frontend passed 13 dedicated origin/proxy/WebSocket relay tests, zero-warning ESLint, and a 24-route production build using the managed backend URL environment contract.
- The configuration verifier, package suite, rebuilt wheel/sdist content checks, Twine metadata checks, fatal Ruff checks, compilation, shell syntax, local Markdown links, and generated-authority checks passed.
- Unix installation and lifecycle behavior remain developer-host evidence only; they are not substituted for Windows product qualification.

## Why B02 is not closed

The current host cannot execute Windows PowerShell 5.1, cannot prove Windows 11 workstation identity, and cannot generate or validate a native CPython 3.11 Windows x86_64 dependency lock. These required files are therefore intentionally absent:

- `requirements/locks/cpython-3.11-windows-x86_64/core.txt`
- `quality/evidence/B02/cpython-3.11-windows-x86_64-profile-resolution.json`
- `quality/evidence/B02/windows-install-qualification.json`
- `quality/evidence/B02/windows-install-qualification.log`

On the required host, `powershell -File scripts/verify_windows_install.ps1` must prove fresh install, second install, idempotent second start, restart PID replacement, stop cleanup, default data-preserving uninstall, explicit validated data removal, and idempotent second uninstall. Static inspection and Linux smoke results do not satisfy that gate.

## Current truth boundary

B02 implementation is committed as an inspectable checkpoint, not as batch closure. The quality authorities continue to report B02 as `in_progress`, B03 as `locked`, installation as blocked, and offline mode as a centralized request rather than a proven whole-process no-egress sandbox. No release, cross-platform support, or 10/10 claim is made.
