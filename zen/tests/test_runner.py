#!/usr/bin/env python3
"""
Test runner for ZEN tests

Runs all unit and integration tests for the ZEN orchestrator.
"""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all tests for ZEN Orchestrator"""
    tests_dir = Path(__file__).parent
    service_root = tests_dir.parent

    # List of test files to run
    test_files = [
        "test_zen_unit.py",
        "test_zen_commands.py",
        "test_zen_metrics.py",
        "test_zen_integration.py"
    ]

    total_passed = 0
    total_failed = 0

    print("=" * 80)
    print("Running ZEN Orchestrator Tests")
    print("=" * 80)

    for test_file in test_files:
        test_path = tests_dir / test_file

        if not test_path.exists():
            print(f"[FAIL] Test file not found: {test_file}")
            total_failed += 1
            continue

        print(f"\n[TEST] Running {test_file}...")
        print("-" * 50)

        try:
            # Run pytest on the specific file with proper Python path
            env = {"PYTHONPATH": str(service_root.parent)}
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=tests_dir,
                env=env
            )

            if result.returncode == 0:
                print(f"[PASS] {test_file} - PASSED")
                total_passed += 1
            else:
                print(f"[FAIL] {test_file} - FAILED")
                print(f"STDOUT:\n{result.stdout}")
                print(f"STDERR:\n{result.stderr}")
                total_failed += 1

        except Exception as e:
            print(f"[ERROR] {test_file} - ERROR: {e}")
            total_failed += 1

    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"[PASS] Passed: {total_passed}")
    print(f"[FAIL] Failed: {total_failed}")
    print(f"[INFO] Total:  {total_passed + total_failed}")

    if total_failed == 0:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {total_failed} test suite(s) failed")
        return 1


def run_specific_test(test_name):
    """Run a specific test file"""
    tests_dir = Path(__file__).parent
    test_path = tests_dir / f"test_zen_{test_name}.py"

    if not test_path.exists():
        print(f"[FAIL] Test file not found: {test_path}")
        return 1

    print(f"[TEST] Running {test_path.name}...")

    try:
        env = {"PYTHONPATH": str(tests_dir.parent.parent)}
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v"],
            cwd=tests_dir,
            env=env
        )
        return result.returncode
    except Exception as e:
        print(f"[ERROR] Error running test: {e}")
        return 1


def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        return run_specific_test(test_name)
    else:
        # Run all tests
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())