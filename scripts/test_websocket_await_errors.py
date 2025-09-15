#!/usr/bin/env python3
"""Quick test runner for WebSocket await error reproduction.

This script runs the specific tests created for Issue #1184 to validate
that the await errors can be reproduced and assessed.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and capture output."""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {cmd}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        print(f"RETURN CODE: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Run WebSocket await error tests."""
    print("WebSocket Await Error Test Runner - Issue #1184")
    print("=" * 60)

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")

    results = {}

    # Test 1: Unit tests to reproduce errors
    results['unit_tests'] = run_command(
        "python -m pytest tests/unit/test_websocket_await_error_reproduction.py -v --tb=short",
        "Unit Tests - Error Reproduction"
    )

    # Test 2: Integration tests
    results['integration_tests'] = run_command(
        "python -m pytest tests/integration/test_websocket_manager_sync_async_integration.py -v --tb=short",
        "Integration Tests - WebSocket Manager Patterns"
    )

    # Test 3: Mission critical tests
    results['mission_critical_tests'] = run_command(
        "python -m pytest tests/mission_critical/test_websocket_await_error_mission_critical.py -v --tb=short",
        "Mission Critical Tests - Business Impact"
    )

    # Test 4: Quick validation using unified test runner
    results['unified_runner'] = run_command(
        "python tests/unified_test_runner.py --category unit --pattern websocket_await_error --execution-mode development",
        "Unified Test Runner - Quick Validation"
    )

    # Print summary
    print("\n" + "="*60)
    print("TEST EXECUTION SUMMARY")
    print("="*60)

    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)

    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{test_name:.<40} {status}")

    print(f"\nOVERALL: {passed_tests}/{total_tests} test suites executed successfully")

    if passed_tests < total_tests:
        print("\nNOTE: Some test failures are EXPECTED as they reproduce the await errors.")
        print("Review the detailed output above to confirm error reproduction.")

    print("\nNEXT STEPS:")
    print("1. Review test output for specific TypeError messages about await expressions")
    print("2. Check which WebSocket functionality remains working despite errors")
    print("3. Use results to prioritize fixes for the most critical components")

    return 0

if __name__ == "__main__":
    sys.exit(main())