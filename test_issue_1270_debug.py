#!/usr/bin/env python3
"""
Debug script to reproduce Issue #1270 - Pattern filtering bug
Tests exact command generation for database category with patterns.
"""

import sys
import os
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the unified test runner
from tests.unified_test_runner import UnifiedTestRunner

def test_database_pattern_filtering():
    """Test database category pattern filtering behavior."""
    print("=== Issue #1270 Debug Test ===")
    print("Testing database category pattern filtering behavior\n")

    # Create test runner instance
    runner = UnifiedTestRunner()

    # Create mock args with pattern - include all required attributes
    args = argparse.Namespace()
    args.pattern = "test_connection"
    args.verbose = True
    args.no_coverage = True
    args.fast_fail = True
    args.real_services = False
    args.env = "test"
    args.parallel = False
    args.workers = 1
    args.staging_e2e = False
    args.min_coverage = 80
    args.markers = None
    args.keyword = None

    # Test the pattern filtering decision
    print("1. Testing _should_category_use_pattern_filtering() for database:")
    should_filter = runner._should_category_use_pattern_filtering("database")
    print(f"   Result: {should_filter}")
    print(f"   Expected: False (database should NOT use pattern filtering)")
    print(f"   Status: {'✅ CORRECT' if not should_filter else '❌ BUG FOUND'}\n")

    # Test command generation
    print("2. Testing command generation for database category:")
    try:
        command = runner._build_pytest_command("backend", "database", args)
        print(f"   Generated command: {command}")

        # Check if -k filter is applied
        has_k_filter = '-k "test_connection"' in command
        print(f"   Contains -k filter: {has_k_filter}")
        print(f"   Expected: False (no -k filter should be applied)")
        print(f"   Status: {'❌ BUG CONFIRMED' if has_k_filter else '✅ WORKING CORRECTLY'}\n")

        if has_k_filter:
            print("🚨 BUG CONFIRMED: Database category incorrectly applies -k filter")
            print("   This confirms Issue #1270 exists")
        else:
            print("✅ No bug found: Database category correctly ignores pattern")

    except Exception as e:
        print(f"   Error generating command: {e}")
        print("   This may indicate a configuration issue")

    # Test other categories for comparison
    print("\n3. Testing other categories for comparison:")
    test_categories = ["e2e", "unit", "integration", "websocket"]

    for category in test_categories:
        should_filter = runner._should_category_use_pattern_filtering(category)
        print(f"   {category}: should_filter={should_filter}")

    print("\n=== Debug Test Complete ===")

if __name__ == "__main__":
    test_database_pattern_filtering()