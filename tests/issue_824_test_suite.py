#!/usr/bin/env python3
"""Issue #824 Test Suite - WebSocket Manager Fragmentation Detection

PURPOSE: Comprehensive test suite for detecting WebSocket Manager fragmentation issues

BUSINESS IMPACT:
- Priority: P0 CRITICAL
- Impact: $500K+ ARR Golden Path functionality
- Root Cause: Multiple WebSocket Manager implementations causing race conditions

TEST EXECUTION:
This suite aggregates all Issue #824 tests for unified execution and reporting.

EXPECTED BEHAVIOR:
- Tests should FAIL with current fragmentation (proving the problem exists)
- Tests should PASS after SSOT consolidation (proving the solution works)
"""

import sys
import os
import subprocess
from typing import List, Dict, Any
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_issue_824_test_suite():
    """
    Run comprehensive Issue #824 test suite.

    Returns:
        Dict containing test results for each test category
    """
    test_files = [
        "tests/unit/websocket_ssot/test_websocket_manager_fragmentation_detection.py",
        "tests/integration/websocket_ssot/test_websocket_manager_ssot_compliance_integration.py",
        "tests/e2e/staging/test_websocket_manager_golden_path_fragmentation_e2e.py"
    ]

    results = {}

    for test_file in test_files:
        test_path = os.path.join(project_root, test_file)
        if os.path.exists(test_path):
            print(f"\n{'='*80}")
            print(f"RUNNING: {test_file}")
            print(f"{'='*80}")

            try:
                # Run test with pytest
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    test_path, "-v", "--tb=short"
                ], capture_output=True, text=True, cwd=project_root)

                results[test_file] = {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'success': result.returncode == 0
                }

                print(f"RESULT: {'PASS' if result.returncode == 0 else 'FAIL'}")
                if result.stdout:
                    print("STDOUT:")
                    print(result.stdout)
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr)

            except Exception as e:
                results[test_file] = {
                    'returncode': -1,
                    'stdout': '',
                    'stderr': str(e),
                    'success': False,
                    'exception': str(e)
                }
                print(f"EXCEPTION: {e}")
        else:
            print(f"TEST FILE NOT FOUND: {test_file}")
            results[test_file] = {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Test file not found',
                'success': False,
                'file_missing': True
            }

    return results


def print_summary_report(results: Dict[str, Any]):
    """Print summary report of all Issue #824 tests."""
    print(f"\n{'='*80}")
    print(f"ISSUE #824 TEST SUITE SUMMARY REPORT")
    print(f"{'='*80}")

    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r.get('success'))
    failed_tests = total_tests - passed_tests

    print(f"Total test files: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100):.1f}%")

    print(f"\nDETAILED RESULTS:")
    for test_file, result in results.items():
        status = "CHECK PASS" if result.get('success') else "X FAIL"
        print(f"  {status} {test_file}")

        if not result.get('success'):
            if result.get('file_missing'):
                print(f"    -> File not found")
            elif result.get('exception'):
                print(f"    -> Exception: {result['exception']}")
            else:
                print(f"    -> Return code: {result['returncode']}")

    print(f"\nEXPECTED BEHAVIOR:")
    print(f"  - Tests should FAIL with current fragmentation (proving problem exists)")
    print(f"  - Tests should PASS after SSOT consolidation (proving solution works)")
    print(f"  - Current failures indicate WebSocket Manager fragmentation needs remediation")


if __name__ == '__main__':
    print("Issue #824 WebSocket Manager Fragmentation Test Suite")
    print("=" * 60)

    # Run comprehensive test suite
    test_results = run_issue_824_test_suite()

    # Print summary report
    print_summary_report(test_results)

    # Exit with appropriate code
    all_passed = all(r.get('success') for r in test_results.values())
    sys.exit(0 if all_passed else 1)