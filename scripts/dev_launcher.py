#!/usr/bin/env python3
"""
Redirect to the main dev_launcher.py at the project root.

This script is deprecated - use the main dev_launcher.py instead.
"""

import sys
import os
from pathlib import Path

# Get project root
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent

# Add deprecation warning
print("=" * 70)
print("DEPRECATION WARNING:")
print("scripts/dev_launcher.py is deprecated!")
print(f"Please use: python {PROJECT_ROOT}/dev_launcher.py")
print("=" * 70)
print()

# Change to project root directory
os.chdir(PROJECT_ROOT)

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Import and run the new launcher
from dev_launcher.__main__ import main

if __name__ == "__main__":
    main()