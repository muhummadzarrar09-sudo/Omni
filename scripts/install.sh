#!/usr/bin/env bash
# OMNI source-checkout convenience installer.
#
# This script resolves declared dependency ranges from package indexes. It is
# not B01 qualification evidence. The qualified CPython 3.11/Linux x86_64
# hash-lock + local-wheel workflow is documented in docs/TROUBLESHOOTING.md.

set -euo pipefail

PROFILE="all"
for argument in "$@"; do
    case "$argument" in
        --minimal|--core)
            PROFILE="core"
            ;;
        --all)
            PROFILE="all"
            ;;
        -h|--help)
            echo "Usage: scripts/install.sh [--core|--minimal|--all]"
            exit 0
            ;;
        *)
            echo "ERROR: unsupported option: $argument" >&2
            echo "Use --core or --all. CUDA and unconstrained upgrade modes were removed." >&2
            exit 2
            ;;
    esac
done

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
    echo "ERROR: CPython 3.11 was not found." >&2
    exit 1
fi
if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
    echo "ERROR: OMNI requires CPython >=3.11,<3.12; found $("$PY" -VV 2>&1)." >&2
    exit 1
fi

if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ ! -d .venv ]; then
        "$PY" -m venv .venv
    fi
    # shellcheck disable=SC1091
    source .venv/bin/activate
    PY=python
fi

echo "OMNI source install: profile=$PROFILE (index-resolved; not B01 evidence)"
echo "For the qualified workflow, see docs/TROUBLESHOOTING.md."
"$PY" -m pip install ".[${PROFILE}]"
"$PY" -m pip check

echo "Installed OMNI from this checkout with the '$PROFILE' profile."
echo "Run: omni --help"
