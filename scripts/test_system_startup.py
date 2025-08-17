#!/usr/bin/env python
"""
System Startup Test Runner
Modular test runner for system startup and E2E tests
Legacy entry point - redirects to new modular implementation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and delegate to new modular implementation
from startup_test_runner import main

if __name__ == "__main__":
    main()