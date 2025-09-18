#!/usr/bin/env python3
"""
Execute Issue #1176 tests to validate infrastructure truth gaps

This script executes the Issue #1176 test suite directly to capture
actual results vs documentation claims.
"""

import sys
import os
import subprocess
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def execute_test_file(test_file):
    """Execute a single test file and capture results."""
    print(f"\n{'='*60}")
    print(f"EXECUTING: {test_file}")
    print(f"{'='*60}")

    try:
        # Use pytest to execute the test file
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            test_file,
            '-v', '--tb=short', '--no-cov', '--no-header'
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=300  # 5 minute timeout
        )

        print(f"RETURN CODE: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")

        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

        return {
            'test_file': test_file,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'executed': True
        }

    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: Test execution exceeded 5 minutes")
        return {
            'test_file': test_file,
            'return_code': -1,
            'stdout': '',
            'stderr': 'Test execution timeout',
            'executed': False
        }
    except Exception as e:
        print(f"EXECUTION ERROR: {e}")
        return {
            'test_file': test_file,
            'return_code': -2,
            'stdout': '',
            'stderr': str(e),
            'executed': False
        }

def main():
    """Execute all Issue #1176 tests."""
    print("ISSUE #1176 TEST EXECUTION - INFRASTRUCTURE TRUTH VALIDATION")
    print(f"Started: {datetime.now()}")
    print(f"Project Root: {project_root}")

    # List of Issue #1176 test files to execute
    test_files = [
        'tests/unit/test_issue_1176_factory_pattern_integration_conflicts.py',
        'tests/unit/test_issue_1176_websocket_manager_interface_mismatches.py',
        'tests/unit/test_issue_1176_messagerouter_fragmentation_conflicts.py',
        'tests/unit/test_issue_1176_quality_router_fragmentation_conflicts.py',
        'tests/unit/auth/test_issue_1176_service_auth_breakdown_unit.py',
    ]

    # Integration tests (Phase 2)
    integration_tests = [
        'tests/integration/test_issue_1176_factory_integration_conflicts_non_docker.py',
        'tests/integration/auth/test_issue_1176_service_auth_breakdown_integration.py',
        'tests/integration/test_issue_1176_golden_path_factory_pattern_mismatches.py',
        'tests/integration/test_issue_1176_messagerouter_routing_conflicts_integration.py',
    ]

    # E2E tests (Phase 3)
    e2e_tests = [
        'tests/e2e/test_issue_1176_golden_path_complete_user_journey.py',
    ]

    all_results = []

    print(f"\n🚀 PHASE 1: UNIT TESTS ({len(test_files)} tests)")
    for test_file in test_files:
        result = execute_test_file(test_file)
        all_results.append(result)

    print(f"\n🚀 PHASE 2: INTEGRATION TESTS ({len(integration_tests)} tests)")
    for test_file in integration_tests:
        result = execute_test_file(test_file)
        all_results.append(result)

    print(f"\n🚀 PHASE 3: E2E TESTS ({len(e2e_tests)} tests)")
    for test_file in e2e_tests:
        result = execute_test_file(test_file)
        all_results.append(result)

    # Summary analysis
    print(f"\n{'='*80}")
    print("EXECUTION SUMMARY")
    print(f"{'='*80}")

    executed_count = len([r for r in all_results if r['executed']])
    failed_count = len([r for r in all_results if r['return_code'] != 0])
    passed_count = len([r for r in all_results if r['return_code'] == 0])

    print(f"Total Tests: {len(all_results)}")
    print(f"Executed: {executed_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")

    # Identify false green patterns
    zero_second_tests = []
    for result in all_results:
        if "0.00s" in result['stdout'] or "collected 0 items" in result['stdout']:
            zero_second_tests.append(result['test_file'])

    if zero_second_tests:
        print(f"\n⚠️  FALSE GREEN PATTERN DETECTED:")
        print(f"Tests with 0.00s execution or 0 items collected:")
        for test_file in zero_second_tests:
            print(f"  - {test_file}")

    # Save detailed results
    results_file = 'ISSUE_1176_ACTUAL_TEST_EXECUTION_RESULTS.json'
    with open(results_file, 'w') as f:
        json.dump({
            'execution_time': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(all_results),
                'executed': executed_count,
                'passed': passed_count,
                'failed': failed_count,
                'false_green_detected': len(zero_second_tests)
            },
            'results': all_results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")
    print(f"Completed: {datetime.now()}")

    return all_results

if __name__ == "__main__":
    main()