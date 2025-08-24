#!/usr/bin/env python3
"""
Main development launcher for Netra platform.
This script provides a convenient entry point from the project root.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the dev launcher
from dev_launcher.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
