#!/usr/bin/env python3
"""
Validate Test Collection Pattern for Issue #1176

This script directly tests pytest collection behavior to expose the
"0 tests executed but claiming success" pattern.
"""

import sys
import os
import subprocess
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def test_pytest_collection(test_file):
    """Test pytest collection behavior for a specific file."""
    print(f"\n{'='*60}")
    print(f"TESTING COLLECTION: {test_file}")
    print(f"{'='*60}")

    if not Path(test_file).exists():
        print(f"❌ Test file does not exist: {test_file}")
        return {
            'test_file': test_file,
            'status': 'file_not_found',
            'collected_count': 0,
            'executed_count': 0,
            'claimed_success': False
        }

    try:
        # First, test collection only
        print("📊 TESTING COLLECTION ONLY...")
        collection_result = subprocess.run([
            sys.executable, '-m', 'pytest',
            test_file,
            '--collect-only', '-q'
        ], capture_output=True, text=True, cwd=project_root, timeout=60)

        print(f"Collection return code: {collection_result.returncode}")
        print(f"Collection stdout: {collection_result.stdout}")
        if collection_result.stderr:
            print(f"Collection stderr: {collection_result.stderr}")

        # Now test actual execution
        print("\n🚀 TESTING ACTUAL EXECUTION...")
        execution_result = subprocess.run([
            sys.executable, '-m', 'pytest',
            test_file,
            '-v', '--tb=short', '--no-cov'
        ], capture_output=True, text=True, cwd=project_root, timeout=60)

        print(f"Execution return code: {execution_result.returncode}")
        print(f"Execution stdout: {execution_result.stdout}")
        if execution_result.stderr:
            print(f"Execution stderr: {execution_result.stderr}")

        # Analyze for the problematic pattern
        collection_stdout = collection_result.stdout
        execution_stdout = execution_result.stdout

        # Check for "collected 0 items" pattern
        collected_zero = "collected 0 items" in collection_stdout or "collected 0 items" in execution_stdout

        # Check for "no tests ran" pattern
        no_tests_ran = "no tests ran" in execution_stdout

        # Check for 0.00s execution time
        zero_time = "0.00s" in execution_stdout

        # Check if pytest claims success (return code 0) despite no tests
        claimed_success = execution_result.returncode == 0

        # Extract test counts
        collected_count = 0
        executed_count = 0

        # Parse collection output
        if "collected" in collection_stdout:
            for line in collection_stdout.split('\n'):
                if "collected" in line and "items" in line:
                    try:
                        # Extract number from "collected X items"
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "collected" and i + 1 < len(parts):
                                collected_count = int(parts[i + 1])
                                break
                    except (ValueError, IndexError):
                        pass

        # Parse execution output for passed/failed counts
        for line in execution_stdout.split('\n'):
            if "passed" in line or "failed" in line or "error" in line:
                # Look for patterns like "X passed", "X failed", etc.
                parts = line.split()
                for i, part in enumerate(parts):
                    if part in ["passed", "failed", "error"] and i > 0:
                        try:
                            executed_count += int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass

        # Detect the problematic pattern
        false_green = (claimed_success and (collected_zero or no_tests_ran or zero_time) and executed_count == 0)

        result = {
            'test_file': test_file,
            'status': 'analyzed',
            'collection_return_code': collection_result.returncode,
            'execution_return_code': execution_result.returncode,
            'collected_count': collected_count,
            'executed_count': executed_count,
            'claimed_success': claimed_success,
            'collected_zero_items': collected_zero,
            'no_tests_ran': no_tests_ran,
            'zero_time_execution': zero_time,
            'false_green_pattern': false_green,
            'collection_output': collection_stdout,
            'execution_output': execution_stdout
        }

        if false_green:
            print(f"\n⚠️  FALSE GREEN PATTERN DETECTED!")
            print(f"   - Claimed success: {claimed_success}")
            print(f"   - Collected count: {collected_count}")
            print(f"   - Executed count: {executed_count}")
            print(f"   - Zero items collected: {collected_zero}")
            print(f"   - No tests ran: {no_tests_ran}")
            print(f"   - Zero time execution: {zero_time}")
        else:
            print(f"✅ No false green pattern detected")
            print(f"   - Collected: {collected_count}, Executed: {executed_count}")

        return result

    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout during test execution")
        return {
            'test_file': test_file,
            'status': 'timeout',
            'collected_count': 0,
            'executed_count': 0,
            'claimed_success': False
        }
    except Exception as e:
        print(f"❌ Error during test execution: {e}")
        return {
            'test_file': test_file,
            'status': 'error',
            'error': str(e),
            'collected_count': 0,
            'executed_count': 0,
            'claimed_success': False
        }

def main():
    """Main validation function."""
    print("ISSUE #1176 - TEST COLLECTION PATTERN VALIDATION")
    print("=" * 60)

    # Test files that are likely to exhibit the pattern
    test_files = [
        'tests/unit/test_issue_1176_factory_pattern_integration_conflicts.py',
        'tests/unit/test_issue_1176_websocket_manager_interface_mismatches.py',
        'tests/unit/test_issue_1176_messagerouter_fragmentation_conflicts.py',
        'tests/integration/test_issue_1176_factory_integration_conflicts_non_docker.py',
    ]

    all_results = []
    false_green_count = 0

    for test_file in test_files:
        result = test_pytest_collection(test_file)
        all_results.append(result)

        if result.get('false_green_pattern', False):
            false_green_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total test files analyzed: {len(all_results)}")
    print(f"False green patterns detected: {false_green_count}")

    if false_green_count > 0:
        print(f"\n🚨 CRITICAL: {false_green_count} test files exhibit the '0 tests executed but claiming success' pattern!")
        print("This confirms the Issue #1176 recursive manifestation pattern.")
    else:
        print(f"\n✅ No false green patterns detected in analyzed files.")

    # Save results
    results_file = 'TEST_COLLECTION_PATTERN_VALIDATION_RESULTS.json'
    with open(results_file, 'w') as f:
        json.dump({
            'analysis_summary': {
                'total_files': len(all_results),
                'false_green_count': false_green_count,
                'pattern_confirmed': false_green_count > 0
            },
            'detailed_results': all_results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")

    return false_green_count > 0

if __name__ == "__main__":
    pattern_confirmed = main()
    sys.exit(1 if pattern_confirmed else 0)