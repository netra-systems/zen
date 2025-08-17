#!/usr/bin/env python3
"""
Simple Performance Test Runner
Runs performance tests without loading the full application stack to avoid import issues.
"""

import sys
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any

def _setup_test_environment() -> None:
    """Setup Python path and environment variables for testing."""
    current_dir = Path(__file__).parent
    app_dir = current_dir / "app"
    sys.path.insert(0, str(current_dir))
    sys.path.insert(0, str(app_dir))
    os.environ['TESTING'] = '1'
    os.environ['SKIP_APP_INIT'] = '1'

def _get_performance_test_files() -> List[str]:
    """Get list of performance test files to run."""
    return [
        'app/tests/performance/test_benchmark_metrics.py',
        'app/tests/performance/test_database_performance.py',
        'app/tests/performance/test_concurrent_processing.py',
        'app/tests/performance/test_corpus_generation_perf.py',
        'app/tests/performance/test_large_scale_generation.py',
        'app/tests/performance/test_agent_load_stress.py'
    ]

def _run_single_test(test_file: str) -> Dict[str, Any]:
    """Run a single test file and return result."""
    if not os.path.exists(test_file):
        print(f"WARNING: Test file not found: {test_file}")
        return None
    
    print(f"\nRunning {test_file}...")
    return _execute_pytest_command(test_file)

def _execute_pytest_command(test_file: str) -> Dict[str, Any]:
    """Execute pytest command for a test file."""
    cmd = [
        sys.executable, '-m', 'pytest', test_file,
        '--no-cov', '--tb=short', '-v', '--disable-warnings',
        '--no-header', '--override-ini', 'python_files=test_*.py',
        '--ignore-glob=*conftest.py'
    ]
    return _handle_test_execution(test_file, cmd)

def _handle_test_execution(test_file: str, cmd: List[str]) -> Dict[str, Any]:
    """Handle test execution with timeout and error handling."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        _print_test_result(test_file, result)
        return _create_result_dict(test_file, result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return _handle_timeout(test_file)
    except Exception as e:
        return _handle_error(test_file, e)

def _print_test_result(test_file: str, result: subprocess.CompletedProcess) -> None:
    """Print test result status and output."""
    if result.returncode == 0:
        print(f"PASSED: {test_file}")
    else:
        print(f"FAILED: {test_file}")
        if result.stdout:
            print(f"Output: {result.stdout[:500]}...")
        if result.stderr:
            print(f"Error: {result.stderr[:500]}...")

def _create_result_dict(test_file: str, returncode: int, stdout: str, stderr: str) -> Dict[str, Any]:
    """Create result dictionary for test execution."""
    return {
        'file': test_file,
        'returncode': returncode,
        'stdout': stdout,
        'stderr': stderr
    }

def _handle_timeout(test_file: str) -> Dict[str, Any]:
    """Handle test timeout scenario."""
    print(f"TIMEOUT: {test_file}")
    return _create_result_dict(
        test_file, -1, '', 'Test timed out after 5 minutes'
    )

def _handle_error(test_file: str, error: Exception) -> Dict[str, Any]:
    """Handle test execution error."""
    print(f"ERROR: {test_file} - {error}")
    return _create_result_dict(
        test_file, -2, '', str(error)
    )

def _print_test_summary(results: List[Dict[str, Any]]) -> None:
    """Print comprehensive test execution summary."""
    print("\n" + "="*80)
    print("PERFORMANCE TEST SUMMARY")
    print("="*80)
    _print_test_counts(results)
    _print_failed_tests(results)

def _print_test_counts(results: List[Dict[str, Any]]) -> None:
    """Print test pass/fail counts."""
    passed = sum(1 for r in results if r['returncode'] == 0)
    failed = sum(1 for r in results if r['returncode'] != 0)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

def _print_failed_tests(results: List[Dict[str, Any]]) -> None:
    """Print details of failed tests."""
    failed_results = [r for r in results if r['returncode'] != 0]
    if failed_results:
        print("\nFAILED TESTS:")
        for result in failed_results:
            print(f"  - {result['file']}")
            if result['stderr']:
                print(f"    Error: {result['stderr'][:200]}...")

def run_performance_tests() -> List[Dict[str, Any]]:
    """Run performance tests with minimal dependencies."""
    _setup_test_environment()
    test_files = _get_performance_test_files()
    results = []
    for test_file in test_files:
        result = _run_single_test(test_file)
        if result:
            results.append(result)
    _print_test_summary(results)
    return results

if __name__ == "__main__":
    results = run_performance_tests()
    failed_count = sum(1 for r in results if r['returncode'] != 0)
    sys.exit(failed_count)