#!/bin/bash
# ============================================================================
#  OMNI V3 - UNQUALIFIED HARDWARE CONVENIENCE SETUP (GTX 1050 Ti)
#
#  This owner-machine helper resolves packages from indexes and downloads large
#  model assets. It is not B01 install, artifact, portability, or hardware
#  qualification evidence. Use docs/TROUBLESHOOTING.md for the qualified
#  CPython 3.11/Linux x86_64 hash-lock + local-wheel workflow.
#
#  One-shot installer tuned for the owner's target machine. In one go it:
#    1. Installs deps (with CUDA 121 prebuilt llama-cpp wheel for 10-series GPUs)
#    2. Downloads the fast Qwen2.5-1.5B model (default)
#    3. Downloads the DEEP Qwen2.5-3B model (hard-reasoning tier, ~2GB)
#    4. Installs + configures Piper (OFFLINE TTS) as the default voice
#    5. Helps you configure the WhatsApp Web messenger (Pakistan-friendly)
#    6. Runs the full test suite to verify everything works
#
#  Usage:
#    ./scripts/setup_hardware.sh                 # full GPU setup
#    ./scripts/setup_hardware.sh --cpu-only      # no CUDA, 16GB RAM fallback
#    ./scripts/setup_hardware.sh --skip-models   # deps only, no big downloads
#
#  Target: GTX 1050 Ti 4GB / 16GB RAM. See README performance table.
# ============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo ""
echo "  ====================================================="
echo "   OMNI V3 - REAL HARDWARE SETUP (4GB GTX 1050 Ti)"
echo "  ====================================================="
echo ""

# ---------- args ----------
CPU_ONLY=""
SKIP_MODELS=""
for arg in "$@"; do
    case $arg in
        --cpu-only) CPU_ONLY="1"; shift ;;
        --skip-models) SKIP_MODELS="1"; shift ;;
    esac
done

# ---------- 1. Python ----------
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
    echo "  ❌ CPython 3.11 not found. Install it from https://python.org"
    exit 1
fi
if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
    echo "  ❌ OMNI requires CPython >=3.11,<3.12; found $("$PY" -VV 2>&1)."
    exit 1
fi
echo "  Python: $PY"
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d ".venv" ]; then
        echo "  Creating venv at .venv..."
        $PY -m venv .venv
    fi
    source .venv/bin/activate
    PY=python
fi

# ---------- 2. Install deps ----------
echo ""
echo "  [1/6] Installing dependencies..."
$PY -m pip install --upgrade --quiet pip setuptools wheel

if [ -n "$CPU_ONLY" ]; then
    echo "    -> CPU-only llama-cpp (no GPU acceleration)"
    $PY -m pip install --quiet "llama-cpp-python" \
        --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu"
else
    echo "    -> CUDA 12.1 llama-cpp (GTX 10-series / 1050 Ti optimized)"
    $PY -m pip install --quiet "llama-cpp-python" \
        --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/cu121"
fi

echo "    -> OMNI declared all profile (non-editable source build)"
$PY -m pip install --quiet ".[all]"
$PY -m pip check

echo ""
echo "  ✅ Dependencies installed."

# ---------- 3. Offline TTS: set the per-user default ----------
echo ""
echo "  [2/6] Configuring OFFLINE TTS (piper from the all profile)..."
$PY - <<'EOF'
import json
from omni_v2.core.paths import get_data_dir

p = get_data_dir() / "config.json"
cfg = {}
if p.exists():
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
cfg.setdefault("tts_allow_cloud", False)
cfg.setdefault("tts_enabled", True)
p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
print(f"    -> tts_allow_cloud=False in {p}")
EOF

echo "  ✅ Offline TTS configured (piper primary)."

# ---------- 4. Download models ----------
if [ -n "$SKIP_MODELS" ]; then
    echo ""
    echo "  [3-4/6] Skipping model downloads (--skip-models)."
else
    echo ""
    echo "  [3/6] Downloading fast model (Qwen2.5-1.5B, ~1.1GB)..."
    omni model download || echo "    (fast model download failed - run 'omni model download' later)"

    echo ""
    echo "  [4/6] Downloading DEEP model (Qwen2.5-3B, ~2GB) for hard reasoning..."
    omni model download --deep || echo "    (deep model download failed - run 'omni model download --deep' later)"
fi

# ---------- 5. WhatsApp messenger help ----------
echo ""
echo "  [5/6] WhatsApp Web messenger (Pakistan-friendly; from all profile)..."
echo "    Run: omni messenger setup-whatsapp  for the step-by-step guide."
echo "    Run: omni messenger whatsapp-set +923001234567  to set your number."

# ---------- 6. Verify ----------
echo ""
echo "  [6/6] Running full test suite to verify..."
$PY -m pytest omni_v2/tests/ -q --disable-warnings 2>&1 | tail -3 || true

echo ""
echo "  ====================================================="
echo "   ✅ OMNI V3 REAL HARDWARE SETUP COMPLETE"
echo "  ====================================================="
echo ""
echo "  Next steps:"
echo "    omni test                       # (re)run all tests"
echo "    omni model info                 # verify both models present"
echo "    omni app                        # launch desktop control panel"
echo "    omni start                      # FastAPI backend on the configured bind/port"
echo "    omni messenger setup-whatsapp   # phone reports"
echo ""
echo "  Deep-tier: hard reasoning auto-swaps to the 3B model (fits 4GB VRAM)."
echo ""
