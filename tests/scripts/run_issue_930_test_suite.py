"""
Issue #930 JWT Auth Configuration Failures - Test Suite Executor

This script runs the comprehensive failing test suite for Issue #930, designed to reproduce
and validate the exact JWT authentication configuration failures observed in staging.

The tests are DESIGNED TO FAIL initially to demonstrate the root causes of:
1. JWT_SECRET_STAGING validation failures
2. SSOT vs direct os.environ access inconsistencies
3. Service authentication 403 errors for 'service:netra-backend'
4. Environment variable inheritance and configuration drift issues

Usage:
    python tests/scripts/run_issue_930_test_suite.py [--verbose] [--category unit|integration|all]

Business Impact: $500K+ ARR - Critical for fixing Golden Path authentication breakdown
"""
import subprocess
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json
import time


class Issue930TestRunner:
    """Test runner for Issue #930 comprehensive failing test suite."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results = {}
        self.repo_root = Path(__file__).parent.parent.parent

    def run_test_file(self, test_file_path: str, category: str) -> Dict[str, Any]:
        """Run a single test file and capture results."""
        print(f"\n{'='*60}")
        print(f"Running {category.upper()} Test: {Path(test_file_path).name}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            # Run pytest with appropriate options
            cmd = [
                sys.executable, '-m', 'pytest',
                test_file_path,
                '-v' if self.verbose else '-q',
                '--tb=short',
                '--no-header',
                '--disable-warnings'
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test file
            )

            duration = time.time() - start_time

            # Parse pytest output for test counts
            output_lines = result.stdout.split('\n')
            failed_tests = []
            passed_tests = []

            for line in output_lines:
                if ' FAILED ' in line:
                    test_name = line.split('::')[-1].split(' ')[0]
                    failed_tests.append(test_name)
                elif ' PASSED ' in line:
                    test_name = line.split('::')[-1].split(' ')[0]
                    passed_tests.append(test_name)

            # Extract summary line
            summary_line = ""
            for line in reversed(output_lines):
                if ' failed' in line or ' passed' in line or ' error' in line:
                    summary_line = line.strip()
                    break

            return {
                'file': Path(test_file_path).name,
                'category': category,
                'duration': duration,
                'return_code': result.returncode,
                'summary': summary_line,
                'failed_tests': failed_tests,
                'passed_tests': passed_tests,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            return {
                'file': Path(test_file_path).name,
                'category': category,
                'duration': 300,
                'return_code': -1,
                'summary': 'Test execution timeout after 5 minutes',
                'failed_tests': [],
                'passed_tests': [],
                'stdout': '',
                'stderr': 'Timeout',
                'success': False
            }
        except Exception as e:
            return {
                'file': Path(test_file_path).name,
                'category': category,
                'duration': time.time() - start_time,
                'return_code': -2,
                'summary': f'Test execution error: {str(e)}',
                'failed_tests': [],
                'passed_tests': [],
                'stdout': '',
                'stderr': str(e),
                'success': False
            }

    def run_unit_tests(self) -> List[Dict[str, Any]]:
        """Run all unit tests for Issue #930."""
        unit_test_files = [
            'tests/unit/issue_930/test_jwt_secret_staging_validation_failure.py',
            'tests/unit/issue_930/test_environment_access_ssot_violations.py'
        ]

        results = []
        for test_file in unit_test_files:
            full_path = self.repo_root / test_file
            if full_path.exists():
                result = self.run_test_file(str(full_path), 'unit')
                results.append(result)
                self.print_test_result(result)
            else:
                print(f"WARNING: Test file not found: {test_file}")

        return results

    def run_integration_tests(self) -> List[Dict[str, Any]]:
        """Run all integration tests for Issue #930."""
        integration_test_files = [
            'tests/integration/issue_930/test_jwt_environment_access_patterns.py',
            'tests/integration/issue_930/test_service_startup_authentication_failure.py'
        ]

        results = []
        for test_file in integration_test_files:
            full_path = self.repo_root / test_file
            if full_path.exists():
                result = self.run_test_file(str(full_path), 'integration')
                results.append(result)
                self.print_test_result(result)
            else:
                print(f"WARNING: Test file not found: {test_file}")

        return results

    def print_test_result(self, result: Dict[str, Any]) -> None:
        """Print formatted test result."""
        status = "CHECK PASSED" if result['success'] else "X FAILED"
        print(f"\n{status} - {result['file']} ({result['duration']:.2f}s)")
        print(f"Summary: {result['summary']}")

        if result['failed_tests']:
            print(f"Failed Tests ({len(result['failed_tests'])}):")
            for test in result['failed_tests']:
                print(f"  - {test}")

        if result['passed_tests']:
            print(f"Passed Tests ({len(result['passed_tests'])}):")
            for test in result['passed_tests']:
                print(f"  - {test}")

        if not result['success'] and self.verbose:
            print("\nSTDOUT:")
            print(result['stdout'])
            if result['stderr']:
                print("\nSTDERR:")
                print(result['stderr'])

    def generate_summary_report(self, all_results: List[Dict[str, Any]]) -> None:
        """Generate comprehensive summary report."""
        print(f"\n{'='*80}")
        print("ISSUE #930 JWT AUTH CONFIGURATION FAILURES - TEST SUITE SUMMARY")
        print(f"{'='*80}")

        total_files = len(all_results)
        total_failed_files = len([r for r in all_results if not r['success']])
        total_passed_files = len([r for r in all_results if r['success']])

        total_failed_tests = sum(len(r['failed_tests']) for r in all_results)
        total_passed_tests = sum(len(r['passed_tests']) for r in all_results)
        total_tests = total_failed_tests + total_passed_tests

        total_duration = sum(r['duration'] for r in all_results)

        print(f"\nEXECUTION SUMMARY:")
        print(f"  Test Files: {total_files} (Passed: {total_passed_files}, Failed: {total_failed_files})")
        print(f"  Individual Tests: {total_tests} (Passed: {total_passed_tests}, Failed: {total_failed_tests})")
        print(f"  Total Duration: {total_duration:.2f} seconds")

        print(f"\nTEST CATEGORIES:")
        categories = {}
        for result in all_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'files': 0, 'failed_files': 0, 'failed_tests': 0, 'passed_tests': 0}
            categories[cat]['files'] += 1
            if not result['success']:
                categories[cat]['failed_files'] += 1
            categories[cat]['failed_tests'] += len(result['failed_tests'])
            categories[cat]['passed_tests'] += len(result['passed_tests'])

        for cat, stats in categories.items():
            success_rate = (stats['files'] - stats['failed_files']) / stats['files'] * 100
            print(f"  {cat.upper()}: {stats['files']} files, {success_rate:.1f}% success rate")
            print(f"    Tests: {stats['failed_tests']} failed, {stats['passed_tests']} passed")

        print(f"\nFAILED TESTS BY CATEGORY:")
        for result in all_results:
            if result['failed_tests']:
                print(f"\n{result['category'].upper()} - {result['file']}:")
                for test in result['failed_tests']:
                    print(f"  X {test}")

        print(f"\nEXPECTED FAILURES (Tests designed to expose Issue #930 root causes):")
        expected_failure_patterns = [
            'jwt_secret_staging_missing_environment_variable_failure',
            'jwt_secret_staging_environment_hierarchy_failure',
            'ssot_vs_direct_environment_access_inconsistency',
            'backend_service_authentication_initialization_failure',
            'database_session_creation_authentication_failure',
            'service_to_service_authentication_mismatch',
            'direct_os_environ_jwt_secret_access_violation',
            'environment_variable_inheritance_ssot_violation'
        ]

        found_expected_failures = []
        for result in all_results:
            for test in result['failed_tests']:
                for pattern in expected_failure_patterns:
                    if pattern in test:
                        found_expected_failures.append(f"{result['file']}::{test}")

        print(f"  Found {len(found_expected_failures)} expected failure tests:")
        for failure in found_expected_failures:
            print(f"    CHECK {failure}")

        print(f"\nRECOMMENDED NEXT STEPS:")
        print(f"  1. Review failed tests to understand JWT configuration root causes")
        print(f"  2. Implement fixes for JWT_SECRET_STAGING resolution in staging environment")
        print(f"  3. Ensure all services use SSOT IsolatedEnvironment for environment access")
        print(f"  4. Configure proper SERVICE_SECRET in staging (not development defaults)")
        print(f"  5. Validate cross-service JWT secret consistency")
        print(f"  6. Re-run tests to verify fixes resolve authentication failures")

    def run_all_tests(self, category: str = 'all') -> None:
        """Run the complete test suite for Issue #930."""
        print("ISSUE #930 JWT AUTH CONFIGURATION FAILURES - COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print("These tests are DESIGNED TO FAIL to expose the root causes of staging authentication issues.")
        print("Expected failures will help identify specific JWT configuration problems.")
        print("=" * 80)

        all_results = []

        if category in ['all', 'unit']:
            print(f"\n🧪 RUNNING UNIT TESTS...")
            unit_results = self.run_unit_tests()
            all_results.extend(unit_results)

        if category in ['all', 'integration']:
            print(f"\n🔗 RUNNING INTEGRATION TESTS...")
            integration_results = self.run_integration_tests()
            all_results.extend(integration_results)

        # Generate comprehensive summary
        self.generate_summary_report(all_results)

        # Save results to file
        report_file = self.repo_root / 'tests' / 'reports' / 'issue_930_test_results.json'
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'category': category,
                'results': all_results,
                'summary': {
                    'total_files': len(all_results),
                    'failed_files': len([r for r in all_results if not r['success']]),
                    'total_failed_tests': sum(len(r['failed_tests']) for r in all_results),
                    'total_passed_tests': sum(len(r['passed_tests']) for r in all_results),
                    'total_duration': sum(r['duration'] for r in all_results)
                }
            }, f, indent=2)

        print(f"\n📊 Detailed results saved to: {report_file}")


def main():
    """Main entry point for Issue #930 test suite."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive failing test suite for Issue #930 JWT authentication failures'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output with full test details'
    )
    parser.add_argument(
        '--category', '-c',
        choices=['unit', 'integration', 'all'],
        default='all',
        help='Test category to run (default: all)'
    )

    args = parser.parse_args()

    runner = Issue930TestRunner(verbose=args.verbose)
    runner.run_all_tests(category=args.category)


if __name__ == "__main__":
    main()