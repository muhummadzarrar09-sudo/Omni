#!/bin/bash
# ============================================================
#  OMNI V3 - One-click launcher for Unix/macOS
#  Run: ./start.sh
# ============================================================

set -e

echo ""
echo "  ====================================================="
echo "   OMNI V3 - Starting the AGI..."
echo "  ====================================================="
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "  First run - installing OMNI..."
    echo ""
    ./install.sh
fi

# Activate venv
echo "  Activating virtual environment..."
source .venv/bin/activate

# Check if model is downloaded
if [ ! -f "data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf" ]; then
    echo ""
    echo "  Model not found - downloading Qwen2.5-1.5B (~1.1GB)..."
    echo "  This is a one-time download."
    echo ""
    omni model download
fi

# Open browser after 5 seconds
(sleep 5 && (xdg-open http://localhost:8765/docs 2>/dev/null || open http://localhost:8765/docs 2>/dev/null)) &

# Start the backend
echo ""
echo "  ====================================================="
echo "   OMNI V3 is running!"
echo ""
echo "    Backend:  http://localhost:8765"
echo "    API Docs: http://localhost:8765/docs"
echo ""
echo "    Press Ctrl+C to stop."
echo "  ====================================================="
echo ""

omni start
