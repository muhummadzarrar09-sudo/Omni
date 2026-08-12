#!/usr/bin/env bash
# OMNI source-checkout developer installer for Unix-like hosts.
# This is not B01 evidence and does not claim Linux/macOS product support.
# The primary B02 path is Windows 11 x64. See docs/TROUBLESHOOTING.md.

set -euo pipefail

PROFILE="core"
FRONTEND=1
for argument in "$@"; do
    case "$argument" in
        --minimal|--core) PROFILE="core" ;;
        --all) PROFILE="all" ;;
        --backend-only) FRONTEND=0 ;;
        -h|--help)
            echo "Usage: scripts/install.sh [--core|--all] [--backend-only]"
            exit 0
            ;;
        *)
            echo "ERROR: unsupported option: $argument" >&2
            exit 2
            ;;
    esac
done

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PY=$(command -v python3.11 || command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
    echo "ERROR: CPython 3.11 was not found." >&2
    exit 1
fi
if ! "$PY" -c 'import platform, sys; raise SystemExit(0 if platform.python_implementation() == "CPython" and sys.version_info[:2] == (3, 11) else 1)'; then
    echo "ERROR: OMNI requires CPython >=3.11,<3.12; found $("$PY" -VV 2>&1)." >&2
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    if [ -d .venv ] || [ -f .venv ] || [ -L .venv ]; then
        echo "ERROR: .venv exists but does not contain a Unix Python executable." >&2
        exit 1
    fi
    "$PY" -m venv .venv
fi
PY="$ROOT/.venv/bin/python"
if ! "$PY" -c 'import platform, sys; raise SystemExit(0 if platform.python_implementation() == "CPython" and sys.version_info[:2] == (3, 11) else 1)'; then
    echo "ERROR: existing .venv is not CPython 3.11; remove it explicitly and retry." >&2
    exit 1
fi

# The checkout is importable even in an empty venv, so detect an installed
# distribution rather than using find_spec before importing lifecycle deps.
if "$PY" -c "import importlib.metadata as m; raise SystemExit(0 if any(d.metadata.get('Name', '').lower() == 'omni-agi' for d in m.distributions()) else 1)"; then
    "$PY" -m omni_v2.core.runtime_cli stop >/dev/null
fi

echo "OMNI Unix developer install: profile=$PROFILE (index-resolved; not B01 evidence)"
"$PY" -m pip install ".[${PROFILE}]"
"$PY" -m pip check
"$PY" -m omni_v2.core.runtime_cli --json config init >/dev/null

if [ "$FRONTEND" -eq 1 ]; then
    NODE=$(command -v node || true)
    COREPACK=$(command -v corepack || true)
    if [ -z "$NODE" ] || [ -z "$COREPACK" ]; then
        echo "ERROR: Node.js >=22.22.2,<23 with Corepack is required for the interface." >&2
        exit 1
    fi
    if ! "$NODE" --eval='const [major,minor,patch]=process.versions.node.split(".").map(Number); process.exit(major===22 && (minor>22 || (minor===22 && patch>=2)) ? 0 : 1)'; then
        echo "ERROR: Node.js >=22.22.2,<23 is required; found $("$NODE" --version)." >&2
        exit 1
    fi
    NPM=("$COREPACK" "npm@12.0.2")
    if [ "$("${NPM[@]}" --version)" != "12.0.2" ]; then
        echo "ERROR: Corepack could not provide npm 12.0.2 required by frontend_next/package.json." >&2
        exit 1
    fi
    export OMNI_BACKEND_URL
    OMNI_BACKEND_URL=$("$PY" -c 'from omni_v2.core.config import load_config; print(load_config().backend_url)')
    "${NPM[@]}" --prefix frontend_next ci
    "${NPM[@]}" --prefix frontend_next run build
    "$PY" -m omni_v2.core.runtime_cli preflight --frontend --root "$ROOT"
else
    "$PY" -m omni_v2.core.runtime_cli preflight --root "$ROOT"
fi

echo "Developer installation ready. This host is not a qualified product platform."
