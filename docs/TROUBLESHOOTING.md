# OMNI installation and troubleshooting

**Qualification date:** 2026-08-11

**Project status:** experimental personal build; not a published or production-ready release

This document is the current installation authority for B01. It does not imply
that unfinished capabilities are stable. Consult the generated
[Capability Matrix](CAPABILITY_MATRIX.md) and
[Quality Scorecard](QUALITY_SCORECARD.md) for capability truth.

## Supported environment

### Python

- Interpreter contract: **CPython `>=3.11,<3.12`**.
- Tested interpreter: **CPython 3.11.2**.
- Resolver and hash-lock qualification: **Linux x86_64 with CPython 3.11**.
- Python 3.10, Python 3.12+, PyPy, Windows dependency resolution, and macOS
  dependency resolution are not qualified by B01.
- Windows 11 x64 remains the intended primary owner platform, but its complete
  install cannot be called qualified until a Windows gate runs in a later
  platform batch.

Do not bypass `Requires-Python` with `--ignore-requires-python`.

### Frontend

The B01 frontend qualification uses Node.js `>=22.22.2 <23` and npm `12.0.2`.
The exact npm version is recorded in `frontend_next/package.json`. The reviewed
`unrs-resolver@1.12.2` native-binding postinstall is the only explicitly
allowlisted install script.

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
npx --yes npm@12.0.2 ci
npx --yes npm@12.0.2 install-scripts ls
npx --yes npm@12.0.2 ls --all
npx --yes npm@12.0.2 audit --audit-level=low
npm run lint
npm run build
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

The browser uses same-origin `/api/...` and `/ws` paths. Next.js proxies those
requests to `OMNI_BACKEND_URL`, which defaults to `http://127.0.0.1:8765` on
the server side.

```bash
# Terminal 1, repository root with the core environment active
python -m uvicorn backend_fastapi.main:app --host 127.0.0.1 --port 8765

# Terminal 2
cd frontend_next
npx --yes npm@12.0.2 ci
npm run dev
```

If the backend uses another address, set `OMNI_BACKEND_URL` before starting
Next.js. Browser code should not be changed to hard-code a cross-origin
`localhost` URL.

### Frontend clean install reports blocked scripts

Run:

```bash
npx --yes npm@12.0.2 install-scripts ls
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
