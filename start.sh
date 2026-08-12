#!/usr/bin/env bash
# Managed Unix developer launcher. This does not claim Linux/macOS product support.
set -euo pipefail

RESTART=0
BACKEND_ONLY=0
OPEN_BROWSER=1
for argument in "$@"; do
    case "$argument" in
        --restart) RESTART=1 ;;
        --backend-only) BACKEND_ONLY=1 ;;
        --no-browser) OPEN_BROWSER=0 ;;
        -h|--help)
            echo "Usage: ./start.sh [--restart] [--backend-only] [--no-browser]"
            exit 0
            ;;
        *) echo "ERROR: unsupported option: $argument" >&2; exit 2 ;;
    esac
done

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
if [ ! -x .venv/bin/python ] || { [ "$BACKEND_ONLY" -eq 0 ] && [ ! -f frontend_next/.next/BUILD_ID ]; }; then
    args=(--core)
    if [ "$BACKEND_ONLY" -eq 1 ]; then args+=(--backend-only); fi
    "$ROOT/scripts/install.sh" "${args[@]}"
fi
PY="$ROOT/.venv/bin/python"

is_requested_runtime_running() {
    "$PY" -c "from omni_v2.core.lifecycle import status; r=status(); raise SystemExit(0 if r.ok and ($BACKEND_ONLY == 1 or any(s.name == 'frontend' and s.status == 'running' for s in r.services)) else 1)"
}

args=()
if [ "$BACKEND_ONLY" -eq 1 ]; then args+=(--backend-only); fi
if [ "$RESTART" -eq 1 ]; then
    "$PY" -m omni_v2.core.runtime_cli restart "${args[@]}"
elif is_requested_runtime_running; then
    echo "OMNI is already running under verified process ownership."
else
    # Replace a verified backend-only generation to add the frontend, or safely
    # recover an owned generation whose process exists but readiness has failed.
    if "$PY" -c "from omni_v2.core.lifecycle import status; r=status(); raise SystemExit(0 if r.ok or any(s.status in {'unhealthy', 'unverified'} for s in r.services) else 1)"; then
        "$PY" -m omni_v2.core.runtime_cli restart "${args[@]}"
    else
        "$PY" -m omni_v2.core.runtime_cli start "${args[@]}"
    fi
fi

if [ "$BACKEND_ONLY" -eq 1 ]; then
    URL=$("$PY" -c 'from omni_v2.core.config import load_config; print(load_config().backend_docs_url)')
else
    URL=$("$PY" -c 'from omni_v2.core.config import load_config; print(load_config().frontend_url)')
fi
echo "OMNI developer runtime is ready at $URL"
echo "This host is development-only; Windows 11 x64 remains the primary product platform."
if [ "$OPEN_BROWSER" -eq 1 ]; then
    (xdg-open "$URL" >/dev/null 2>&1 || open "$URL" >/dev/null 2>&1 || true) &
fi
