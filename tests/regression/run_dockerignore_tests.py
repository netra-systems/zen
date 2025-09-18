#!/usr/bin/env python3
"""
Test Execution Script: P0 .dockerignore Monitoring Module Tests
================================================================

This script provides convenient execution of all .dockerignore regression tests
and validation tests created to prevent and validate the P0 monitoring module
exclusion fix.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - DevOps Testing
2. Business Goal: Automated Regression Prevention
3. Value Impact: Streamlined validation of critical infrastructure fixes
4. Revenue Impact: Prevents $500K+ ARR production failures through testing

USAGE:
    python tests/regression/run_dockerignore_tests.py [options]

OPTIONS:
    --all                Run all .dockerignore tests
    --regression         Run regression prevention tests only
    --validation         Run fix validation tests only
    --cicd              Run CI/CD integration tests only
    --quick             Run quick subset of critical tests
    --verbose           Verbose output with detailed metrics
    --json-report       Generate JSON test report
    --fail-fast         Stop on first test failure

EXAMPLES:
    # Run all tests
    python tests/regression/run_dockerignore_tests.py --all

    # Quick validation for CI/CD
    python tests/regression/run_dockerignore_tests.py --quick --fail-fast

    # Full regression suite with report
    python tests/regression/run_dockerignore_tests.py --regression --json-report
"""

import argparse
import json
import sys
import time
import unittest
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# SSOT imports
from test_framework.ssot.base_test_case import SSotBaseTestCase


class DockerignoreTestRunner:
    """
    Test runner for .dockerignore monitoring module tests.

    Provides organized execution of regression and validation tests
    with reporting capabilities.
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def run_tests(self, test_categories: List[str], verbose: bool = False,
                  fail_fast: bool = False) -> Dict[str, Any]:
        """
        Run specified test categories.

        Args:
            test_categories: List of test categories to run
            verbose: Enable verbose output
            fail_fast: Stop on first failure

        Returns:
            Test execution results
        """
        self.start_time = datetime.now(UTC)

        print(f"🔧 Starting .dockerignore monitoring module tests")
        print(f"📅 Started at: {self.start_time.isoformat()}")
        print(f"🎯 Categories: {', '.join(test_categories)}")
        print("=" * 60)

        results = {
            'start_time': self.start_time.isoformat(),
            'categories': test_categories,
            'test_results': {},
            'summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'skipped': 0
            }
        }

        for category in test_categories:
            category_result = self._run_test_category(category, verbose, fail_fast)
            results['test_results'][category] = category_result

            # Update summary
            results['summary']['total_tests'] += category_result.get('tests_run', 0)
            results['summary']['passed'] += len(category_result.get('passed', []))
            results['summary']['failed'] += len(category_result.get('failures', []))
            results['summary']['errors'] += len(category_result.get('errors', []))
            results['summary']['skipped'] += len(category_result.get('skipped', []))

            # Fail fast if requested and we have failures
            if fail_fast and (category_result.get('failures') or category_result.get('errors')):
                print(f"X Stopping execution due to failures in {category}")
                break

        self.end_time = datetime.now(UTC)
        results['end_time'] = self.end_time.isoformat()
        results['duration_seconds'] = (self.end_time - self.start_time).total_seconds()

        self._print_summary(results)
        return results

    def _run_test_category(self, category: str, verbose: bool, fail_fast: bool) -> Dict[str, Any]:
        """
        Run a specific test category.

        Args:
            category: Test category name
            verbose: Enable verbose output
            fail_fast: Stop on first failure

        Returns:
            Category test results
        """
        print(f"\n🧪 Running {category} tests...")

        # Map categories to test modules
        test_modules = {
            'regression': 'tests.regression.test_dockerignore_monitoring_module_exclusion',
            'validation': 'tests.regression.test_dockerignore_fix_validation',
            'cicd': 'tests.regression.test_dockerignore_cicd_validation'
        }

        if category not in test_modules:
            return {
                'error': f"Unknown test category: {category}",
                'tests_run': 0,
                'passed': [],
                'failures': [],
                'errors': [],
                'skipped': []
            }

        # Load test suite
        try:
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromName(test_modules[category])

            # Run tests
            runner = unittest.TextTestRunner(
                verbosity=2 if verbose else 1,
                failfast=fail_fast,
                stream=sys.stdout
            )

            result = runner.run(suite)

            # Process results
            category_result = {
                'tests_run': result.testsRun,
                'passed': [],
                'failures': [],
                'errors': [],
                'skipped': []
            }

            # Collect passed tests (inferred from total - failures - errors - skipped)
            total_non_passed = len(result.failures) + len(result.errors) + len(result.skipped)
            passed_count = result.testsRun - total_non_passed
            category_result['passed'] = [f"passed_test_{i}" for i in range(passed_count)]

            # Collect failures
            for test, traceback in result.failures:
                category_result['failures'].append({
                    'test': str(test),
                    'traceback': traceback
                })

            # Collect errors
            for test, traceback in result.errors:
                category_result['errors'].append({
                    'test': str(test),
                    'traceback': traceback
                })

            # Collect skipped
            for test, reason in result.skipped:
                category_result['skipped'].append({
                    'test': str(test),
                    'reason': reason
                })

            # Print category summary
            status = "CHECK PASSED" if not result.failures and not result.errors else "X FAILED"
            print(f"   {status} - {result.testsRun} tests, "
                  f"{passed_count} passed, {len(result.failures)} failed, "
                  f"{len(result.errors)} errors, {len(result.skipped)} skipped")

            return category_result

        except Exception as e:
            error_result = {
                'error': f"Failed to run category {category}: {str(e)}",
                'tests_run': 0,
                'passed': [],
                'failures': [],
                'errors': [{'test': f'{category}_loader', 'traceback': str(e)}],
                'skipped': []
            }
            print(f"   X ERROR - Failed to load/run {category} tests: {e}")
            return error_result

    def _print_summary(self, results: Dict[str, Any]) -> None:
        """Print test execution summary."""
        print("\n" + "=" * 60)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 60)

        summary = results['summary']
        duration = results.get('duration_seconds', 0)

        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"🧪 Total Tests: {summary['total_tests']}")
        print(f"CHECK Passed: {summary['passed']}")
        print(f"X Failed: {summary['failed']}")
        print(f"🚨 Errors: {summary['errors']}")
        print(f"⏭️  Skipped: {summary['skipped']}")

        # Overall status
        if summary['failed'] == 0 and summary['errors'] == 0:
            print(f"\n🎉 ALL TESTS PASSED - .dockerignore monitoring fix validated!")
            exit_code = 0
        else:
            print(f"\n💥 TESTS FAILED - Issues detected in .dockerignore configuration!")
            exit_code = 1

        # Category breakdown
        print(f"\n📋 By Category:")
        for category, category_result in results['test_results'].items():
            tests_run = category_result.get('tests_run', 0)
            failures = len(category_result.get('failures', []))
            errors = len(category_result.get('errors', []))
            status = "CHECK" if failures == 0 and errors == 0 else "X"
            print(f"   {status} {category}: {tests_run} tests ({failures} failures, {errors} errors)")

        print("=" * 60)
        return exit_code

    def generate_json_report(self, results: Dict[str, Any], output_file: Optional[str] = None) -> str:
        """
        Generate JSON test report.

        Args:
            results: Test execution results
            output_file: Optional output file path

        Returns:
            JSON report content
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"dockerignore_test_report_{timestamp}.json"

        # Enhance results with metadata
        enhanced_results = {
            **results,
            'test_suite': '.dockerignore monitoring module validation',
            'purpose': 'Prevent P0 production failures from Docker build context exclusions',
            'business_impact': '$500K+ ARR protection',
            'generated_at': datetime.now(UTC).isoformat(),
            'project_root': str(self.project_root),
            'metadata': {
                'fix_status': 'Emergency fix applied to .dockerignore',
                'critical_modules': [
                    'netra_backend.app.services.monitoring.gcp_error_reporter',
                    'netra_backend.app.middleware.gcp_auth_context_middleware'
                ],
                'test_categories': {
                    'regression': 'Prevent future exclusion issues',
                    'validation': 'Validate emergency fix effectiveness',
                    'cicd': 'Integrate validation into deployment pipeline'
                }
            }
        }

        # Write JSON report
        with open(output_file, 'w') as f:
            json.dump(enhanced_results, f, indent=2)

        print(f"📄 JSON report generated: {output_file}")
        return json.dumps(enhanced_results, indent=2)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run .dockerignore monitoring module tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--all', action='store_true',
                        help='Run all .dockerignore tests')
    parser.add_argument('--regression', action='store_true',
                        help='Run regression prevention tests only')
    parser.add_argument('--validation', action='store_true',
                        help='Run fix validation tests only')
    parser.add_argument('--cicd', action='store_true',
                        help='Run CI/CD integration tests only')
    parser.add_argument('--quick', action='store_true',
                        help='Run quick subset of critical tests')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output with detailed metrics')
    parser.add_argument('--json-report', action='store_true',
                        help='Generate JSON test report')
    parser.add_argument('--fail-fast', action='store_true',
                        help='Stop on first test failure')

    args = parser.parse_args()

    # Determine test categories
    categories = []

    if args.all:
        categories = ['regression', 'validation', 'cicd']
    elif args.quick:
        categories = ['validation']  # Quick validation for CI/CD
    else:
        if args.regression:
            categories.append('regression')
        if args.validation:
            categories.append('validation')
        if args.cicd:
            categories.append('cicd')

    # Default to validation if no categories specified
    if not categories:
        categories = ['validation']

    # Run tests
    runner = DockerignoreTestRunner()
    results = runner.run_tests(
        test_categories=categories,
        verbose=args.verbose,
        fail_fast=args.fail_fast
    )

    # Generate JSON report if requested
    if args.json_report:
        runner.generate_json_report(results)

    # Exit with appropriate code
    exit_code = 0 if results['summary']['failed'] == 0 and results['summary']['errors'] == 0 else 1
    sys.exit(exit_code)


if __name__ == '__main__':
    main()