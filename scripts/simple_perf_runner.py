from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Simple Performance Test Runner
Runs performance tests without loading the full application stack to avoid import issues.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def _setup_environment():
    """Setup Python paths and environment variables"""
    current_dir = Path(__file__).parent
    app_dir = current_dir / "app"
    os.environ['TESTING'] = '1'
    os.environ['SKIP_APP_INIT'] = '1'

def _get_performance_test_files():
    """Return list of performance test files"""
    files = [
        'app/tests/performance/test_benchmark_metrics.py',
        'app/tests/performance/test_database_performance.py',
        'app/tests/performance/test_concurrent_processing.py'
    ]
    return files + _get_additional_test_files()

def _get_additional_test_files():
    """Return additional performance test files"""
    return [
        'app/tests/performance/test_corpus_generation_perf.py',
        'app/tests/performance/test_large_scale_generation.py',
        'app/tests/performance/test_agent_load_stress.py'
    ]

def _build_pytest_command(test_file):
    """Build pytest command for test file"""
    return [
        sys.executable, '-m', 'pytest', test_file,
        '--no-cov', '--tb=short', '-v', '--disable-warnings',
        '--no-header', '--override-ini', 'python_files=test_*.py',
        '--ignore-glob=*conftest.py'
    ]

def _run_single_test(test_file):
    """Execute single test file with subprocess"""
    cmd = _build_pytest_command(test_file)
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=300
    )

def _create_result_dict(test_file, result):
    """Create result dictionary from subprocess result"""
    return {
        'file': test_file,
        'returncode': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr
    }

def _handle_test_success(test_file):
    """Handle successful test result"""
    print(f"PASSED: {test_file}")

def _handle_test_failure(test_file, result):
    """Handle failed test result with output"""
    print(f"FAILED: {test_file}")
    if result.stdout:
        print(f"Output: {result.stdout[:500]}...")
    if result.stderr:
        print(f"Error: {result.stderr[:500]}...")

def _handle_timeout(test_file):
    """Handle test timeout case"""
    print(f"TIMEOUT: {test_file}")
    return {
        'file': test_file, 'returncode': -1,
        'stdout': '', 'stderr': 'Test timed out after 5 minutes'
    }

def _handle_error(test_file, error):
    """Handle general test error"""
    print(f"ERROR: {test_file} - {error}")
    return {
        'file': test_file, 'returncode': -2,
        'stdout': '', 'stderr': str(error)
    }

def _process_test_file(test_file):
    """Process single test file and return result"""
    if not os.path.exists(test_file):
        print(f"WARNING: Test file not found: {test_file}")
        return None
    
    print(f"\nRunning {test_file}...")
    return _execute_test(test_file)

def _execute_test(test_file):
    """Execute test with error handling"""
    try:
        return _run_and_process_test(test_file)
    except subprocess.TimeoutExpired:
        return _handle_timeout(test_file)
    except Exception as e:
        return _handle_error(test_file, e)

def _run_and_process_test(test_file):
    """Run test and process result"""
    result = _run_single_test(test_file)
    result_dict = _create_result_dict(test_file, result)
    _handle_test_result(test_file, result)
    return result_dict

def _handle_test_result(test_file, result):
    """Handle test result output"""
    if result.returncode == 0:
        _handle_test_success(test_file)
    else:
        _handle_test_failure(test_file, result)

def _print_summary_header():
    """Print summary section header"""
    print("\n" + "="*80)
    print("PERFORMANCE TEST SUMMARY")
    print("="*80)

def _calculate_results(results):
    """Calculate passed and failed counts"""
    passed = sum(1 for r in results if r['returncode'] == 0)
    failed = sum(1 for r in results if r['returncode'] != 0)
    return passed, failed

def _print_result_counts(results, passed, failed):
    """Print test result counts"""
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

def _print_failed_tests(results):
    """Print details of failed tests"""
    print("\nFAILED TESTS:")
    for result in results:
        if result['returncode'] != 0:
            print(f"  - {result['file']}")
            if result['stderr']:
                print(f"    Error: {result['stderr'][:200]}...")

def _print_summary(results):
    """Print complete test summary"""
    _print_summary_header()
    passed, failed = _calculate_results(results)
    _print_result_counts(results, passed, failed)
    if failed > 0:
        _print_failed_tests(results)

def run_performance_tests():
    """Run performance tests with minimal dependencies"""
    _setup_environment()
    test_files = _get_performance_test_files()
    results = _run_all_tests(test_files)
    _print_summary(results)
    return results

def _run_all_tests(test_files):
    """Execute all test files and collect results"""
    results = []
    for test_file in test_files:
        result = _process_test_file(test_file)
        if result:
            results.append(result)
    return results

if __name__ == "__main__":
    results = run_performance_tests()
    failed_count = sum(1 for r in results if r['returncode'] != 0)
    sys.exit(failed_count)
