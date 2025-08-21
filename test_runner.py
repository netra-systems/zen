#!/usr/bin/env python
"""
Backwards compatibility wrapper for unified test runner.
This file redirects to the new unified_test_runner.py
"""

import sys
import subprocess
from pathlib import Path

# Add deprecation warning
print("⚠️  DEPRECATION WARNING: test_runner.py is deprecated.")
print("    Please use 'python unified_test_runner.py' instead.")
print("    Redirecting to unified test runner...\n")

# Get the path to the unified runner
unified_runner = Path(__file__).parent / "unified_test_runner.py"

# Forward all arguments to the unified runner
args = [sys.executable, str(unified_runner)] + sys.argv[1:]

# Execute the unified runner
sys.exit(subprocess.call(args))