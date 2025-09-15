#!/usr/bin/env python3
"""
Quick test to verify Issue #1270 pattern filtering fix
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Import the unified test runner
from tests.unified_test_runner import UnifiedTestRunner
import argparse

def test_pattern_filtering_fix():
    """Test if the pattern filtering fix is working correctly."""

    # Create a test runner instance
    runner = UnifiedTestRunner()

    # Test database category (should NOT use pattern filtering)
    print("Testing database category pattern filtering...")
    result = runner._should_category_use_pattern_filtering('database')
    print(f"Database category uses pattern filtering: {result}")
    assert not result, "Database category should NOT use pattern filtering"

    # Test websocket category (should use pattern filtering)
    print("Testing websocket category pattern filtering...")
    result = runner._should_category_use_pattern_filtering('websocket')
    print(f"WebSocket category uses pattern filtering: {result}")
    assert result, "WebSocket category SHOULD use pattern filtering"

    # Test command building for database category with pattern
    print("\nTesting command building for database category...")
    args = argparse.Namespace()
    args.pattern = "connection"
    args.no_coverage = True
    args.env = 'test'
    args.verbose = False

    # Mock the necessary attributes
    runner.test_configs = {
        "backend": {
            "test_dir": "netra_backend/tests"
        }
    }
    runner.python_command = "python"

    # Build command for database category
    cmd = runner._build_pytest_command("backend", "database", args)
    print(f"Database command: {cmd}")

    # Check if pattern filtering is applied
    if '-k "connection"' in cmd:
        print("❌ FAIL: Pattern filtering was applied to database category")
        return False
    else:
        print("✅ PASS: Pattern filtering was NOT applied to database category")

    # Test command building for websocket category with pattern
    print("\nTesting command building for websocket category...")
    cmd = runner._build_pytest_command("backend", "websocket", args)
    print(f"WebSocket command: {cmd}")

    # Check if pattern filtering is applied
    if '-k "connection"' in cmd:
        print("✅ PASS: Pattern filtering was applied to websocket category")
        return True
    else:
        print("❌ FAIL: Pattern filtering was NOT applied to websocket category")
        return False

if __name__ == "__main__":
    print("Testing Issue #1270 pattern filtering fix...")
    print("=" * 50)

    try:
        success = test_pattern_filtering_fix()
        if success:
            print("\n🎉 All tests passed! The pattern filtering fix is working correctly.")
        else:
            print("\n💥 Tests failed! The pattern filtering fix is not working.")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)