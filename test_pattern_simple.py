#!/usr/bin/env python3
"""
Simple test to verify Issue #1270 pattern filtering fix using dry-run
"""

import subprocess
import sys
from pathlib import Path

def test_dry_run_pattern_filtering():
    """Test pattern filtering using actual unified test runner with dry-run."""

    print("Testing database category with pattern (should NOT apply pattern filtering)...")

    # Test database category with a pattern - should NOT add -k flag
    result = subprocess.run([
        sys.executable, "tests/unified_test_runner.py",
        "--category", "database",
        "--pattern", "connection",
        "--dry-run",
        "--no-docker"
    ], capture_output=True, text=True, cwd=Path(__file__).parent)

    print(f"Return code: {result.returncode}")
    print(f"Output:\n{result.stdout}")
    if result.stderr:
        print(f"Stderr:\n{result.stderr}")

    # Check if the command contains pattern filtering
    output = result.stdout
    if '-k "connection"' in output:
        print("❌ FAIL: Pattern filtering was applied to database category")
        return False
    else:
        print("✅ PASS: Pattern filtering was NOT applied to database category")

    print("\n" + "="*60 + "\n")

    print("Testing websocket category with pattern (should apply pattern filtering)...")

    # Test websocket category with a pattern - should add -k flag
    result = subprocess.run([
        sys.executable, "tests/unified_test_runner.py",
        "--category", "websocket",
        "--pattern", "connection",
        "--dry-run",
        "--no-docker"
    ], capture_output=True, text=True, cwd=Path(__file__).parent)

    print(f"Return code: {result.returncode}")
    print(f"Output:\n{result.stdout}")
    if result.stderr:
        print(f"Stderr:\n{result.stderr}")

    # Check if the command contains pattern filtering
    output = result.stdout
    if '-k "connection"' in output:
        print("✅ PASS: Pattern filtering was applied to websocket category")
        return True
    else:
        print("❌ FAIL: Pattern filtering was NOT applied to websocket category")
        return False

if __name__ == "__main__":
    print("Testing Issue #1270 pattern filtering fix with dry-run...")
    print("=" * 60)

    try:
        success = test_dry_run_pattern_filtering()
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