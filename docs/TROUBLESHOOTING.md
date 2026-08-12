# OMNI installation and troubleshooting

**Qualification date:** 2026-08-12

**Project status:** experimental personal build; not a published or production-ready release

This document is the installation authority for the closed B01 package work and
the active B02 source-checkout runtime work. It does not imply that unfinished
capabilities are stable or that B02 is qualified. Consult the generated
[Capability Matrix](CAPABILITY_MATRIX.md) and
[Quality Scorecard](QUALITY_SCORECARD.md) for capability truth.

## Supported environment

### Python

- Interpreter contract: **CPython `>=3.11,<3.12`**.
- Tested interpreter: **CPython 3.11.2**.
- Resolver and hash-lock qualification: **Linux x86_64 with CPython 3.11**.
- Python 3.10, Python 3.12+, PyPy, Windows dependency resolution, and macOS
  dependency resolution are not qualified by B01.
- NVIDIA DGX Station for Windows on native Windows 11 Arm64 is the primary owner
  target. Windows 11 x64 is a secondary hardware-independent qualification host.
- Neither native Windows architecture is B02-qualified yet. Both must pass the
  unattended B02 matrix on the same exact commit; x64 evidence cannot substitute
  for Arm64 evidence. Physical DGX GPU/model performance remains a later gate.

Do not bypass `Requires-Python` with `--ignore-requires-python`.

### Frontend

The B01 frontend qualification uses Node.js `>=22.22.2 <23` and npm `12.0.2`.
The exact npm version is recorded in `frontend_next/package.json` and is now
selected explicitly with `corepack npm@12.0.2`; global npm is not a prerequisite. The reviewed
`unrs-resolver@1.12.2` native-binding postinstall is the only explicitly
allowlisted install script.

## B02 native Windows source-checkout path (Arm64 primary, x64 secondary)

> **Qualification boundary:** NVIDIA DGX Station for Windows on native Windows
> 11 Arm64 is the intended primary path. B02 remains open until native Arm64 and
> x64 lanes both produce and pass the full unattended same-commit evidence
> matrix. The scripts and workflow are implemented; their presence is not proof
> that either lane passed. Hosted Arm64 is architecture-equivalent B02 evidence,
> not physical DGX GPU, model-throughput, or sustained-use evidence.

Prerequisites:

- native Windows 11 Arm64 or x64 workstation edition (build 22000 or newer;
  Windows Server and domain-controller products do not qualify, and x64
  emulation on Arm64 is not native Arm64 evidence);
- architecture-matched 64-bit CPython `>=3.11,<3.12` available as `py -3.11` or `python`;
- an architecture-matched PowerShell process (PowerShell 7 `pwsh` is recommended on Arm64; the qualifier rejects an emulated shell);
- outbound HTTPS access to the official `nodejs.org` distribution endpoint and
  the package indexes used by the governed Python/frontend locks;
- Visual Studio 2022 Build Tools with `Microsoft.VisualStudio.Workload.VCTools`,
  `Microsoft.VisualStudio.Component.Windows11SDK.26100`, and the native target
  component: `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` for x64 or
  `Microsoft.VisualStudio.Component.VC.Tools.ARM64` for Arm64;
- a complete source checkout, not an arbitrary package from an index.

The unattended `scripts/qualify_b02.ps1` path does **not** trust or require
Node.js or Corepack on ambient `PATH`. It downloads the architecture-matched
official portable Node.js `22.22.2` ZIP into the unique qualification temporary
root, verifies the committed archive and `node.exe` SHA-256 values from
`quality/windows-native-build-contract.json`, invokes that archive's explicit
`node.exe` and `corepack.cmd` paths, and isolates Corepack/npm caches under the
same temporary root. A global Node 24 installation can remain installed and is
ignored. A hash or architecture mismatch fails before dependency resolution.
The standalone installer commands below still require architecture-matched
Node.js `>=22.22.2,<23` with Corepack on `PATH` when run outside the unattended
qualifier.

From Windows Command Prompt:

```bat
install.bat
start.bat
```

From PowerShell:

```powershell
.\scripts\install.ps1 -Core       # default and recommended B02 profile
.\scripts\start.ps1               # owned backend + production frontend
```

The installer creates `.venv`, installs the local `core` profile, runs
`pip check`, initializes canonical non-secret configuration, performs exact
`corepack npm@12.0.2 ci`, builds the frontend with that same npm, and runs
primary/frontend preflight. `-All` is
explicitly optional and much larger; it is not the default merely to make every
hardware subsystem importable.

A repeated install verifies the existing native CPython 3.11 environment,
safely stops only a runtime whose PID/creation-time/executable ownership matches
persisted state, preserves `config.json`, and rebuilds generated assets. It
refuses to replace an incompatible or cross-architecture `.venv` implicitly.

### Windows dependency-lock and unattended qualification boundary

The installer selects
`requirements/locks/cpython-3.11-windows-{arm64|x86_64}/<profile>.txt` from the
native OS architecture and uses `--require-hashes`. A separate architecture
`build.txt` is the only build bootstrap authority. It pins one reviewed wheel
and SHA-256 for CMake, Ninja, Packaging, Pathspec, pip, scikit-build-core,
setuptools, and wheel; the lock's versions **and artifact hashes** must match
`quality/windows-native-build-contract.json`. CMake and Ninja must also report
the exact governed CLI identities. The build bootstrap is wheel-only,
no-dependency, hash-required, and cache-free.

The same contract lists every approved x64 and Arm64 source distribution by
name, version, filename, hash, backend, and controlled build tools. Resolution
of `all` must select exactly that architecture's complete sdist set (12 on x64,
9 on Arm64), not merely a subset containing no unknown source. Runtime and local
project builds use `--no-build-isolation --no-cache-dir`; the installer rejects
resolver/runtime-lock drift before installing. The native tool preflight proves
Visual Studio component presence, architecture-correct `cl.exe` and `link.exe`
paths, a `vcvarsall.bat` environment that explicitly selects governed Windows
SDK `10.0.26100.0`, a compiled executable, and its PE target (`8664` for x64,
`AA64` for Arm64). Installing the component while allowing `vcvarsall.bat` to
select another default SDK is not accepted. x64 or emulated tools cannot
qualify Arm64.

The qualifier separately audits the exact build, dev, and all authorities with
`pip-audit --disable-pip --require-hashes`, inventories licenses using the
interpreter that owns each environment, and rejects missing, unexpected,
conflicting, or version-drifted installed distributions. Package qualification
uses `python -m build --no-isolation`; the sdist install test bootstraps the exact
architecture build lock and disables build isolation. The declared
`setuptools>=83,<85` range remains a security boundary: the earlier x64 audit
proved that 81.0.0 was affected by PYSEC-2026-3447 / CVE-2026-59890. Do not
waive that finding or rerun failed commits unchanged. Outside qualification, an
absent runtime lock produces a warning and index-resolution fallback. That
fallback is never accepted as B02 evidence.

Do not manually assemble closure evidence. From a clean checkout, the single
lane command creates an external detached worktree for the exact commit,
resolves all six profiles twice, compares the exact locks, verifies the native
source-build authority, installs, reinstalls, starts twice, restarts, performs
authenticated readiness, stops, safely uninstalls, explicitly removes isolated
data, repeats uninstall, runs Python, audit, license, package, configuration, and
frontend test/lint/build gates, and writes the native lane attestation outside
the worktree. Its `finally` paths attempt managed stop, terminate only recorded
or unique-lane-owned surviving processes, remove every generated environment,
frontend output, data root, and detached worktree, verify those invariants, and
fail the lane if cleanup is incomplete:

Run this inside an architecture-matched PowerShell session:

```powershell
.\scripts\qualify_b02.ps1 `
  -LaneOnly `
  -CommitSha <full-40-character-commit> `
  -EvidenceRoot C:\b02-evidence
```

The versioned template
`quality/evidence/B02/hosted-windows-qualification.workflow.yml` defines a
hosted `windows-11-arm`/`windows-latest` diagnostic attempt with exact CPython
3.11.9 plus the qualifier's hash-governed portable Node.js bootstrap, evidence
upload on failure, and fail-closed aggregation. It is intentionally **inactive**
at this commit: the automation credential cannot create `.github/workflows`
files. No hosted run is claimed.
A repository owner with GitHub workflow permission may activate the unchanged
template in a later commit:

```powershell
New-Item -ItemType Directory -Force .github\workflows | Out-Null
Copy-Item quality\evidence\B02\hosted-windows-qualification.workflow.yml `
  .github\workflows\b02-windows-qualification.yml
git add .github\workflows\b02-windows-qualification.yml
git commit -m "Activate B02 Windows qualification workflow"
git push origin arena/019ff0df-omni
```

When activated, pull-request events explicitly check out the exact PR head SHA
rather than GitHub's synthetic merge commit; a dispatch may supply another
exact SHA after the workflow reaches the default branch. The Arm64 label
supplies the architecture-equivalent Windows 11 attempt. GitHub's standard
hosted x64 labels may supply Windows Server rather than a Windows 11
workstation; the qualifier deliberately rejects ProductType other than
workstation and preserves a failed diagnostic lane. **A `windows-latest` server
result cannot replace the required run on the native Windows 11 x64 laptop.**
Run the same `-LaneOnly` command on that laptop at the exact commit, then place
its evidence directory and a same-commit Arm64 lane under one evidence root.
The equivalent local aggregate command is:

```powershell
.\scripts\qualify_b02.ps1 `
  -AggregateOnly `
  -CommitSha <the-same-full-40-character-commit> `
  -EvidenceRoot C:\b02-matrix
```

Only an aggregate exit code of zero with `ALL SYSTEMS GO — B03 UNLOCKED` is a
B02 technical unlock signal. A missing, failed, malformed, digest-mismatched,
wrong-architecture, duplicate, or wrong-commit lane fails closed. Formal B02
closure still requires review and committed evidence; script output alone does
not mutate the batch authority.

`scripts/verify_windows_install.ps1` is the inner destructive lifecycle verifier
used by the unattended lane. It may be run for diagnosis, but its standalone
pass is not the complete B02 gate.

### Managed lifecycle

The runtime owns one generation in `%LOCALAPPDATA%\OMNI\run\runtime.json` by
default. Lifecycle commands verify PID, process creation time, executable, and
the OMNI-specific HTTP readiness identity; an owned but unresponsive process is
reported as `unhealthy`, not healthy. Startup is readiness-bounded and partial
startup is cleaned up. It does not use process-name-wide termination.

```powershell
.\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli status
.\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli restart
.\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli stop
.\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli preflight --primary --frontend
```

`start.bat --Restart`, `scripts\start.ps1 -Restart`, and the CLI restart command
replace the owned process tree. A normal second launcher invocation preserves an
already healthy generation, while the launchers replace an owned unhealthy
generation. `-BackendOnly` skips Next.js and opens the API documentation instead.

Lifecycle mutations are serialized by
`%LOCALAPPDATA%\OMNI\run\lifecycle.lock`. A process crash can leave this file
behind. OMNI never age-expires or automatically breaks an unverifiable lock,
because doing so could race a legitimate long operation. First confirm that no
install/start/restart/stop operation is active and inspect `status`; only then
remove the stale lock manually and retry.

### Canonical configuration and secrets

Effective precedence is: safe built-in defaults, then
`%LOCALAPPDATA%\OMNI\config.json`, then environment overrides. Initialize or
inspect it without exposing secret values:

```powershell
.\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli --json config init
.\.venv\Scripts\python.exe -m omni_v2.core.runtime_cli --json config show
```

The contract centralizes backend/frontend/discovery/browser-debug ports, bind
hosts, exact CORS origins, data/model/database/log/runtime paths, GGUF and STT
models, STT device, TTS voice/cloud policy, microphone preference, browser
executable/profile/debug port, and the offline request. Common overrides include:

```powershell
$env:OMNI_DATA_DIR = "D:\OMNI-data"
$env:OMNI_BACKEND_PORT = "8765"
$env:OMNI_FRONTEND_PORT = "3000"
$env:OMNI_MODEL_PATH = "D:\models\assistant.gguf"
$env:OMNI_STT_MODEL = "base.en"
$env:OMNI_STT_DEVICE = "cpu"       # auto, cpu, or cuda
$env:OMNI_BROWSER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$env:OMNI_BROWSER_PROFILE_DIR = "browser\chrome_profile"
$env:OMNI_BROWSER_DEBUG_PORT = "9222"
$env:OMNI_OFFLINE = "true"
```

`OMNI_OFFLINE` is a centralized request, **not** a proven no-egress sandbox;
that enforcement is a B15 gate. `OMNI_API_TOKEN`, `HF_TOKEN` (or legacy
`HUGGINGFACE_TOKEN`), and `PICOVOICE_ACCESS_KEY` are environment-only secrets.
Secret values are rejected in `config.json`, omitted from diagnostics, and
represented only by configured/not-configured booleans.

The frontend keeps browser HTTP and WebSocket traffic on same-origin `/api/...`
and `/ws` paths. Server-side API routes inject `OMNI_API_TOKEN` when configured;
the browser never receives that long-lived secret. For WebSockets, the browser
requests a 30-second one-use ticket through the authenticated server route and
the managed frontend relays the upgrade to `OMNI_BACKEND_URL`. All proxy targets
come only from canonical launcher settings. Direct `npm run build`, `dev`, or
`start` without the required managed environment intentionally fails instead of
silently assuming a browser-visible localhost service.

### Preflight and diagnostics

Preflight reports pass/warn/fail for platform, interpreter, configuration,
writable paths, required Python packages, configured ports, model presence,
microphone discovery, browser discovery, frontend build, optional packages,
and the truthful offline boundary. JSON is persisted under
`<data-dir>\diagnostics\preflight.json`.

A missing GGUF, microphone backend/device, browser, or optional voice/vision
package is named with remediation rather than presented as an unexplained
startup crash. Core/API startup can remain ready with optional warnings.

### Safe uninstall

```bat
uninstall.bat
```

or:

```powershell
.\scripts\uninstall.ps1
.\scripts\uninstall.ps1 -RemoveUserData  # explicit destructive opt-in
```

The default removes only checkout-generated `.venv`, `frontend_next\.next`, and
`frontend_next\node_modules` after safely stopping the owned process tree. It
preserves canonical user data. `-RemoveUserData` resolves and validates the
canonical path; refuses repository, home, drive-root, enclosing, and reparse-point
deletion targets; and verifies every requested deletion. Repeating either command
is supported and reports already-absent assets rather than fabricating removals.
If managed runtime state remains but `.venv` is unavailable, uninstall fails closed:
restore the environment, stop OMNI, and rerun the uninstaller.

### Unix-like developer launcher

Linux remains a developer environment, not the B02 product platform. The
repaired path uses the same canonical config and lifecycle without claiming
Linux/macOS product qualification:

```bash
./scripts/install.sh --core
./start.sh
./start.sh --restart
.venv/bin/python -m omni_v2.core.runtime_cli stop
```

The Unix installer is index-resolved and explicitly not B01 installation
evidence. macOS remains unsupported and unverified.

## Python installation profiles

The base distribution is intentionally dependency-free. It supports package
inspection and the lightweight CLI paths exercised by package tests. Runtime
capabilities require one of these extras:

| Profile | Purpose | B01 Linux resolver result |
| --- | --- | ---: |
| `core` | FastAPI, orchestration, persistence, scheduling, and vault | 36 distributions including OMNI |
| `voice` | Audio, microphone, STT, TTS, and wake word | 90 distributions including OMNI |
| `vision` | Capture, OCR, face recognition, and visual models | 88 distributions including OMNI |
| `desktop` | Native UI, browser, and desktop automation | 26 distributions including OMNI |
| `dev` | Core plus build, test, lock, vulnerability, and license tools | 92 distributions including OMNI |
| `all` | Complete runtime dependency surface; excludes development tools | 219 distributions including OMNI |

`voice`, `vision`, `desktop`, and especially `all` contain native or very large
dependencies. B01 proves that all six profiles resolve on the qualified Linux
environment. It does **not** claim clean native installation or hardware
operation for every profile. The exact core profile is additionally installed
and exercised in a disposable environment outside the checkout.

The canonical import-to-distribution map is
`quality/dependency-profiles.json`. Exact Linux locks are under
`requirements/locks/cpython-3.11-linux-x86_64/`.

## Install the qualified local artifact

There is currently no qualified PyPI release. Build and install the exact local
artifact instead of assuming `omni-agi` on an index is this checkout.

```bash
python3.11 -m venv .venv
source .venv/bin/activate                    # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip

# From the repository root, build both artifacts.
python -m pip install 'build>=1.2,<2'
python -m build

# Install the exact qualified core dependency lock, then the wheel itself.
python -m pip install --require-hashes \
  -r requirements/locks/cpython-3.11-linux-x86_64/core.txt
python -m pip install --no-deps dist/omni_agi-3.2.0-py3-none-any.whl

omni --help
omni install
omni engine info
```

After a future index release is created and qualified, normal extra syntax will
be:

```bash
python -m pip install 'omni-agi[core]'
```

That command is documented as future index syntax, not evidence that a release
currently exists.

## Reproduce the B01 package gates

Use the exact development lock on the qualified Linux environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes \
  -r requirements/locks/cpython-3.11-linux-x86_64/dev.txt

python scripts/resolve_profiles.py
rm -rf build dist omni_agi.egg-info
python -m build
python scripts/check_package_contents.py dist/*.whl dist/*.tar.gz
python -m twine check dist/*
python -m pytest -q tests/package
python scripts/smoke_installed_artifact.py \
  dist/omni_agi-3.2.0-py3-none-any.whl
python -m pip_audit --require-hashes \
  -r requirements/locks/cpython-3.11-linux-x86_64/dev.txt
python scripts/audit_python_licenses.py \
  requirements/locks/cpython-3.11-linux-x86_64/dev.txt
```

The installed-artifact smoke creates a new virtual environment, installs the
hash-locked core dependencies, installs the exact wheel with `--no-deps`, moves
to a directory outside the checkout, checks package resources and imports,
executes meaningful CLI dispatch, and starts the backend health path.

Frontend gates:

```bash
cd frontend_next
corepack npm@12.0.2 ci
corepack npm@12.0.2 install-scripts ls
corepack npm@12.0.2 ls --all
corepack npm@12.0.2 audit --audit-level=low
corepack npm@12.0.2 run lint
corepack npm@12.0.2 run build
```

## Runtime data location

Installed package code may be read-only. OMNI therefore does not store runtime
state in the repository or beside files under `site-packages`.

Defaults:

- Windows: `%LOCALAPPDATA%\OMNI`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/omni`
- macOS path behavior exists but is not B01-qualified:
  `~/Library/Application Support/OMNI`

Set `OMNI_DATA_DIR` to choose another writable location:

```bash
# Linux/macOS shell
export OMNI_DATA_DIR="$HOME/omni-data"

# PowerShell
$env:OMNI_DATA_DIR = "$HOME\omni-data"
```

The explicit override may target another drive, encrypted mount, or temporary
test directory. The user running OMNI must have permission to create and modify
it.

## Common installation failures

### `ERROR: Package ... requires a different Python`

Check the active interpreter:

```bash
python -VV
python -c "import sys; print(sys.executable); print(sys.version_info)"
```

Create the environment with CPython 3.11. Do not try to repair this by removing
the upper bound; Python 3.12+ has not been qualified.

### Hash mismatch while installing a lock

A downloaded file does not match the exact lock, the lock is being used on the
wrong platform, or the package index changed unexpectedly. Stop rather than
using `--no-deps` or removing hashes. Confirm:

```bash
python -VV
python -c "import platform; print(platform.system(), platform.machine())"
```

The committed locks are only for CPython 3.11 on Linux x86_64. Regenerate them
with `scripts/resolve_profiles.py` only as a reviewed dependency update.

### Native build errors (`CMake`, compiler, PortAudio, dlib, or PyAudio)

The selected profile includes a native dependency without a compatible wheel.
Do not treat resolver success as proof that the native toolchain works. Start
with `core`; defer `voice`, `vision`, `desktop`, or `all` until the target OS
has the required compiler, system libraries, devices, and a dedicated
qualification run.

### `omni: command not found`

Ensure the environment is active and inspect the scripts directory:

```bash
python -m pip show omni-agi
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
python -m omni.cli --help
```

Do not use `pip install -e .` as a workaround for artifact validation. Editable
installs can hide missing packages in a wheel.

### `ModuleNotFoundError` for an optional dependency

Install the profile that owns the capability. Examples:

```bash
# Future qualified index syntax
python -m pip install 'omni-agi[voice]'
python -m pip install 'omni-agi[vision]'
python -m pip install 'omni-agi[desktop]'
```

For the current checkout, use the matching exact lock followed by the wheel.
Do not install undeclared packages one at a time; that creates an environment
which the evidence cannot reproduce.

### Permission error under `site-packages` or the source checkout

Upgrade to the B01 artifact and set a writable `OMNI_DATA_DIR`. A final B01
installed smoke explicitly verifies that voice recording state is created
under the configured data root rather than under the installed package.

### Backend cannot be reached from the frontend

The browser uses same-origin `/api/...` and `/ws` paths. Managed Next.js API
routes proxy HTTP, while `frontend_next/server.js` relays WebSocket upgrades;
both use `OMNI_BACKEND_URL` with no silent fallback. First inspect managed state
and canonical configuration:

```bash
.venv/bin/python -m omni_v2.core.runtime_cli status
.venv/bin/python -m omni_v2.core.runtime_cli --json config show
.venv/bin/python -m omni_v2.core.runtime_cli preflight --frontend
```

Use `start.bat` on Windows or `./start.sh` on a Unix development host instead of
launching independently configured backend and frontend processes. If doing
frontend-only development intentionally, export the effective backend URL,
frontend host, and frontend port as `OMNI_BACKEND_URL`, `OMNI_FRONTEND_HOST`,
and `OMNI_FRONTEND_PORT` before `npm run dev`. Browser code must not hard-code a
cross-origin localhost URL.

### Frontend clean install reports blocked scripts

Run:

```bash
corepack npm@12.0.2 install-scripts ls
```

The qualified tree reports no unreviewed scripts. Do not approve a new package
without reviewing its exact version and install script and committing the
resulting explicit allowlist change.

## Audit interpretation

- A zero-vulnerability result means the audit databases had no known advisory
  for the exact locked versions at audit time. It is not a permanent security
  guarantee.
- The Python license report requires an entry for every exact dev-lock
  distribution and fails on missing or unknown metadata.
- `docutils` and `qrcode` expose mixed classifier metadata that remains listed
  under `review_required`. The inventory is not legal advice or a claim that
  every possible redistribution is license-compatible.
- Models, external executables, browser downloads, OS packages, and remote
  services are outside this Python metadata inventory and require separate
  audits in later batches.

## Evidence

B01 machine-readable evidence is stored under `quality/evidence/B01/`, including
profile resolution, installed-artifact smoke, vulnerability audits, license
inventory, frontend dependency-tree validation, and final closure evidence.
