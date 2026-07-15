#!/usr/bin/env bash
# OMNI V3 - One-shot install for Linux/macOS
# Handles the llama-cpp-python prebuilt wheel issue automatically.
#
# Usage:
#   ./install.sh                  # full install (CPU only, works on any laptop)
#   ./install.sh --cuda cu121     # NVIDIA GPU acceleration
#   ./install.sh --minimal        # just the brain, no voice/UI
#
# After install:
#   omni model download
#   omni test
#   omni start

set -e

echo ""
echo "  ====================================================="
echo "   OMNI V3 - Install"
echo "  ====================================================="
echo ""

# Parse args
CUDA=""
MINIMAL=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cuda)
      CUDA="$2"
      shift 2
      ;;
    --minimal)
      MINIMAL=true
      shift
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

# 1. Detect Python
if ! command -v python3 &> /dev/null; then
  if ! command -v python &> /dev/null; then
    echo "  ❌ Python 3 not found. Install from https://python.org"
    exit 1
  fi
  PY=python
else
  PY=python3
fi
PY_VERSION=$($PY -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python: $PY ($PY_VERSION)"

# 2. Create venv if not in one
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ ! -d .venv ]]; then
    echo "  Creating venv at .venv..."
    $PY -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  echo "  Activated venv"
fi
PY=python

# 3. Upgrade pip
echo "  Upgrading pip..."
$PY -m pip install --upgrade pip wheel setuptools --quiet

# 4. Install llama-cpp-python FIRST with prebuilt wheel
# (this is the package that fails to build from source on most machines)
echo "  Installing llama-cpp-python (prebuilt wheel)..."
if [[ -n "$CUDA" ]]; then
  # NVIDIA GPU
  echo "    → CUDA variant: $CUDA"
  $PY -m pip install "llama-cpp-python" \
    --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/$CUDA" \
    --quiet
else
  # CPU only (works on any machine)
  echo "    → CPU variant (no GPU needed)"
  $PY -m pip install "llama-cpp-python" \
    --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu" \
    --quiet
fi

# 5. Install the rest of OMNI
echo "  Installing OMNI V3..."
if $MINIMAL; then
  $PY -m pip install -e .[brain] --quiet
else
  $PY -m pip install -e .[all] --quiet
fi

echo ""
echo "  ====================================================="
echo "  ✅ OMNI V3 installed!"
echo "  ====================================================="
echo ""
echo "  Next steps:"
echo "    $ omni model download    # fetches 1.1GB Qwen2.5-1.5B GGUF"
echo "    $ omni test              # runs 4 test suites"
echo "    $ omni start             # starts backend on :8765"
echo ""
echo "  Or, the old way (no install):"
echo "    $ python omni.py --test"
echo ""
