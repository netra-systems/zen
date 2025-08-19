#!/usr/bin/env python3
"""WebSocket Concurrent Connection Test Runner

Quick runner script for the concurrent connection test.
Provides standalone execution with proper environment setup.

Usage:
    python run_concurrent_test.py
    python run_concurrent_test.py --verbose
    python run_concurrent_test.py --dry-run
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pytest


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run WebSocket concurrent connection tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be tested")
    parser.add_argument("--fast-fail", action="store_true", help="Stop on first failure")
    
    args = parser.parse_args()
    
    test_file = Path(__file__).parent / "test_concurrent_connections.py"
    
    if args.dry_run:
        print(f"Would run tests from: {test_file}")
        print("Test cases:")
        print("- test_concurrent_connections_core_functionality")
        print("- test_connection_limit_enforcement") 
        print("- test_connection_failure_isolation")
        return 0
    
    # Build pytest arguments
    pytest_args = [str(test_file)]
    
    if args.verbose:
        pytest_args.append("-v")
    
    if args.fast_fail:
        pytest_args.append("-x")
    
    # Add asyncio support
    pytest_args.extend(["-s", "--tb=short"])
    
    print(f"Running WebSocket concurrent connection tests...")
    print(f"Test file: {test_file}")
    print(f"Arguments: {pytest_args}")
    print("-" * 60)
    
    # Run the tests
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("-" * 60)
        print("✅ All concurrent connection tests passed!")
    else:
        print("-" * 60)
        print("❌ Some tests failed or encountered errors")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())