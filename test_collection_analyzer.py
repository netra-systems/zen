#!/usr/bin/env python3
"""
Test Collection Analyzer - Comprehensive test discovery and issue analysis
"""

import subprocess
import sys
import time
from pathlib import Path

def count_tests(directory, timeout_sec=60):
    """Count tests and analyze issues in a directory"""
    try:
        start_time = time.time()
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '--collect-only', directory, '--tb=no', '-q'
        ], capture_output=True, text=True, timeout=timeout_sec)
        elapsed = time.time() - start_time

        test_count = result.stdout.count('::test_')
        warning_count = result.stderr.count('Warning')
        error_count = result.stderr.count('Error')
        import_error_count = result.stderr.count('ModuleNotFoundError')

        return {
            'directory': directory,
            'tests': test_count,
            'warnings': warning_count,
            'errors': error_count,
            'import_errors': import_error_count,
            'time': elapsed,
            'success': True,
            'stdout_size': len(result.stdout),
            'stderr_size': len(result.stderr),
            'stderr_sample': result.stderr[:500] if result.stderr else ''
        }
    except subprocess.TimeoutExpired:
        return {
            'directory': directory,
            'tests': 0,
            'warnings': 0,
            'errors': 0,
            'import_errors': 0,
            'time': timeout_sec,
            'success': False,
            'timeout': True
        }
    except Exception as e:
        return {
            'directory': directory,
            'tests': 0,
            'warnings': 0,
            'errors': 1,
            'import_errors': 0,
            'time': 0,
            'success': False,
            'exception': str(e)
        }

def main():
    """Main analysis function"""

    # Test each major directory
    directories = [
        'tests/unit/',
        'tests/e2e/',
        'tests/integration/',
        'netra_backend/tests/',
        'auth_service/tests/',
        'analytics_service/tests/',
        'dev_launcher/tests/',
        'shared/tests/',
        'test_framework/tests/'
    ]

    print("NETRA TEST COLLECTION ANALYSIS")
    print("=" * 50)

    results = []
    for directory in directories:
        if not Path(directory).exists():
            print(f"SKIP {directory} (not found)")
            continue

        print(f"Analyzing {directory}...")
        result = count_tests(directory, 45)
        results.append(result)

        status = "TIMEOUT" if result.get('timeout') else ("SUCCESS" if result['success'] else "FAILED")
        print(f"  {status}: Tests: {result['tests']}, Warnings: {result['warnings']}, Errors: {result['errors']}, Import Errors: {result['import_errors']}, Time: {result['time']:.1f}s")

        if result.get('stderr_sample') and result['errors'] > 0:
            print(f"  Error sample: {result['stderr_sample'][:200]}...")

    print("\n" + "=" * 50)
    print("SUMMARY ANALYSIS")
    print("=" * 50)

    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]

    total_tests = sum(r['tests'] for r in successful_results)
    total_warnings = sum(r['warnings'] for r in successful_results)
    total_errors = sum(r['errors'] for r in successful_results)
    total_import_errors = sum(r['import_errors'] for r in successful_results)

    print(f"Directories analyzed: {len(results)}")
    print(f"Successful collections: {len(successful_results)}")
    print(f"Failed collections: {len(failed_results)}")
    print(f"Total tests discovered: {total_tests}")
    print(f"Total warnings: {total_warnings}")
    print(f"Total errors: {total_errors}")
    print(f"Total import errors: {total_import_errors}")

    if failed_results:
        print("\nFAILED DIRECTORIES:")
        for result in failed_results:
            reason = "timeout" if result.get('timeout') else result.get('exception', 'unknown')
            print(f"  {result['directory']}: {reason}")

    # Calculate collection rate
    if total_tests > 0:
        print(f"\nCollection success rate: {(total_tests / (total_tests + total_errors)) * 100:.1f}%")

    return results

if __name__ == "__main__":
    main()