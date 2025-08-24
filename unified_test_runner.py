#!/usr/bin/env python3
"""
Unified Test Runner - Root Reference
Direct invocation of the test runner from the root directory.
"""
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

# Import and run the actual test runner
from scripts.unified_test_runner import main

if __name__ == "__main__":
    sys.exit(main())