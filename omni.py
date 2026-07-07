#!/usr/bin/env python3
"""
OMNI - Autonomous Personal Agent
Entry point for the application.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "omni"))
from omni.app import main

if __name__ == "__main__":
    main()
