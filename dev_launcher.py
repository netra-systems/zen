#!/usr/bin/env python3
"""
Wrapper script for the refactored dev launcher.

This provides backwards compatibility with the old dev_launcher.py script.
Simply redirects to the new modular implementation.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the new launcher
from dev_launcher.__main__ import main

if __name__ == "__main__":
    main()