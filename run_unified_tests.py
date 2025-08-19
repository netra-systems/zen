#!/usr/bin/env python
"""
Unified Test Runner - Single command to run all tests

USAGE:
    python run_unified_tests.py              # Run all tests in parallel
    python run_unified_tests.py --sequential # Run tests sequentially
    
This script provides a convenient entry point to the unified test orchestrator.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the unified orchestrator
from test_framework.unified_orchestrator import main

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)