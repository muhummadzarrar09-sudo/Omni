#!/bin/bash
# OMNI V3 - One-shot install for Unix/macOS - LATEST DEPENDENCIES
#
# Usage:
#   ./install.sh                  # full install (CPU)
#   ./install.sh --cuda cu121      # NVIDIA GPU acceleration
#   ./install.sh --minimal        # just the brain
#   ./install.sh --upgrade        # upgrade all packages to latest
#
# After install:
#   omni model download
#   omni test
#   omni start

set -e

echo ""
echo "  ====================================================="
echo "   OMNI V3 - Install (Unix/macOS) - LATEST DEPS"
echo "  ====================================================="
echo ""

# Parse args
CUDA=""
MINIMAL=""
UPGRADE=""
for arg in "$@"; do
    case $arg in
        --cuda)
            CUDA="$2"
            shift 2
            ;;
        --minimal)
            MINIMAL="1"
            shift
            ;;
        --upgrade)
            UPGRADE="1"
            shift
            ;;
    esac
done

# 1. Find Python
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
    echo "  ❌ Python 3 not found. Install from https://python.org"
    exit 1
fi
PY_VERSION=$($PY -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python: $PY ($PY_VERSION)"

# 2. Create venv
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d ".venv" ]; then
        echo "  Creating venv at .venv..."
        $PY -m venv .venv
    fi
    echo "  Activated venv: .venv"
    source .venv/bin/activate
    PY=python
fi

# 3. Upgrade pip + setuptools + wheel to LATEST
echo "  Upgrading pip, setuptools, wheel to LATEST..."
$PY -m pip install --upgrade --quiet pip setuptools wheel
echo "    -> $($PY -m pip --version)"

# 4. Install llama-cpp-python FIRST with prebuilt wheel
echo "  Installing llama-cpp-python (prebuilt wheel, latest)..."
if [ -n "$CUDA" ]; then
    echo "    -> CUDA variant: $CUDA"
    $PY -m pip install --upgrade "llama-cpp-python" \
        --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/$CUDA" \
        --quiet
else
    echo "    -> CPU variant (no GPU needed)"
    $PY -m pip install --upgrade "llama-cpp-python" \
        --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu" \
        --quiet
fi

# 5. Install the rest
echo "  Installing OMNI V3 with LATEST dependencies..."
if [ -n "$MINIMAL" ]; then
    $PY -m pip install -e ".[brain]" --upgrade --quiet
else
    $PY -m pip install -e ".[all]" --upgrade --quiet
fi

# 6. Playwright browsers
if [ -z "$MINIMAL" ]; then
    echo "  Ensuring Playwright browser binaries..."
    $PY -m playwright install chromium 2>&1 | tail -2 || true
    echo "    -> Chromium ready"
fi

# 7. Show versions
echo ""
echo "  ====================================================="
echo "  ✅ OMNI V3 installed with LATEST deps!"
echo "  ====================================================="
echo ""
echo "  Installed versions:"
for pkg in llama-cpp-python faster-whisper edge-tts openwakeword playwright fastapi uvicorn apscheduler sentence-transformers chromadb; do
    ver=$($PY -m pip show $pkg 2>/dev/null | grep "^Version:" | awk '{print $2}')
    if [ -n "$ver" ]; then
        echo "    $pkg: $ver"
    fi
done
echo ""
echo "  Next steps:"
echo "    omni model download    # fetches 1.1GB Qwen2.5-1.5B GGUF"
echo "    omni test              # runs 4 test suites"
echo "    omni start             # starts backend on :8765"
echo ""
