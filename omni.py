#!/usr/bin/env python3
"""
OMNI - Autonomous Personal Agent
Entry point for the application.

Usage:
    python omni.py              # Normal mode (V key toggle PTT)
    python omni.py --demo       # Demo mode (runs built-in demo script)
    python omni.py --demo "open github"  # Demo mode with specific command
    python omni.py --demo "help"         # Show help
    Ctrl+C                      # Graceful shutdown
"""
import sys
import os
import signal
from pathlib import Path

# Graceful Ctrl+C shutdown
_shutdown_flag = False

def _handle_ctrl_c(signum, frame):
    global _shutdown_flag
    if _shutdown_flag:
        print("\n[OMNI] Force exit — bye!")
        sys.exit(0)
    _shutdown_flag = True
    print("\n[OMNI] Shutting down... (Ctrl+C again to force exit)")
    # Let Qt handle the quit via atexit
    try:
        import PyQt5.QtWidgets
        app = PyQt5.QtWidgets.QApplication.instance()
        if app:
            app.quit()
    except Exception:
        pass

signal.signal(signal.SIGINT, _handle_ctrl_c)

# Add omni/ to sys.path so 'from omni' works
sys.path.insert(0, str(Path(__file__).parent / "omni"))

# Handle --demo flag BEFORE importing app (injects into environment for config)
_demo_cmd = None
if "--demo" in sys.argv:
    idx = sys.argv.index("--demo")
    # Get the demo command if provided
    if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
        _demo_cmd = sys.argv[idx + 1]
    else:
        _demo_cmd = "help"  # default demo: show help
    os.environ["OMNI_DEMO_COMMAND"] = _demo_cmd
    print(f"[OMNI DEMO MODE] Command: '{_demo_cmd}'")

# Import and run
from omni.app import main

if __name__ == "__main__":
    main()