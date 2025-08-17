#!/usr/bin/env python
"""
Test runner wrapper script.

This script provides a convenient way to run tests from the project root.
It simply imports and runs the test framework's main test runner.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import and run the test framework's main function
from test_framework.test_runner import main

if __name__ == "__main__":
    main()