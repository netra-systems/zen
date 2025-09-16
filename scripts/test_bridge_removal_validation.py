#!/usr/bin/env python3
"""
Bridge Removal Validation Test Runner

This script orchestrates the complete test suite for validating that the
SingletonToFactoryBridge can be safely removed without breaking functionality.

Business Value: Protects $500K+ ARR by ensuring Golden Path remains intact
after legacy code removal.

Test Strategy:
1. Mission Critical Tests - Verify bridge is unused and components work without it
2. Integration Tests - Validate WebSocket and agent flows work without bridge
3. E2E Staging Tests - Complete Golden Path validation
4. Performance Tests - Verify no performance degradation

Usage:
    python scripts/test_bridge_removal_validation.py [--category <category>] [--verbose]

Categories:
    - mission_critical: Core validation tests
    - integration: Integration flow tests
    - e2e: End-to-end staging tests
    - performance: Performance validation
    - all: Run all categories (default)
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BridgeRemovalTestRunner:
    """Test runner for bridge removal validation."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results: Dict[str, Dict] = {}
        self.start_time = time.time()

        # Test categories and their corresponding test files
        self.test_categories = {
            'mission_critical': [
                'tests/mission_critical/test_singleton_bridge_removal_validation.py'
            ],
            'integration': [
                'tests/integration/test_bridge_removal_integration.py'
            ],
            'e2e': [
                'tests/e2e/test_golden_path_without_bridge.py'
            ],
            'performance': [
                'tests/integration/test_bridge_removal_integration.py::TestPerformanceWithoutBridge'
            ]
        }

    def run_test_category(self, category: str) -> Tuple[bool, Dict]:
        """
        Run tests for a specific category.

        Args:
            category: Test category to run

        Returns:
            Tuple of (success, results_dict)
        """
        if category not in self.test_categories:
            logger.error(f"Unknown test category: {category}")
            return False, {}

        logger.info(f"Running {category} tests for bridge removal validation...")

        category_results = {
            'category': category,
            'tests': [],
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'duration': 0,
            'success': True
        }

        start_time = time.time()

        for test_file in self.test_categories[category]:
            test_result = self._run_single_test_file(test_file)
            category_results['tests'].append(test_result)
            category_results['total_tests'] += test_result.get('total', 0)
            category_results['passed_tests'] += test_result.get('passed', 0)
            category_results['failed_tests'] += test_result.get('failed', 0)

            if not test_result.get('success', False):
                category_results['success'] = False

        category_results['duration'] = time.time() - start_time

        # Log results
        if category_results['success']:
            logger.info(
                f"✅ {category} tests PASSED: "
                f"{category_results['passed_tests']}/{category_results['total_tests']} tests "
                f"in {category_results['duration']:.2f}s"
            )
        else:
            logger.error(
                f"❌ {category} tests FAILED: "
                f"{category_results['failed_tests']} failed, "
                f"{category_results['passed_tests']} passed "
                f"in {category_results['duration']:.2f}s"
            )

        return category_results['success'], category_results

    def _run_single_test_file(self, test_file: str) -> Dict:
        """
        Run a single test file and return results.

        Args:
            test_file: Path to test file

        Returns:
            Test results dictionary
        """
        logger.info(f"  Running {test_file}...")

        # Check if test file exists
        test_path = Path(test_file)
        if not test_path.exists():
            logger.error(f"Test file not found: {test_file}")
            return {
                'file': test_file,
                'success': False,
                'error': 'File not found',
                'total': 0,
                'passed': 0,
                'failed': 1
            }

        try:
            # Run the test using pytest
            cmd = [
                sys.executable, '-m', 'pytest',
                str(test_path),
                '--tb=short',
                '--no-header',
                '-v' if self.verbose else '-q'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test file
            )

            # Parse pytest output for results
            output_lines = result.stdout.split('\n')
            summary_line = None

            for line in output_lines:
                if 'passed' in line or 'failed' in line:
                    summary_line = line.strip()

            # Parse test results
            total_tests = 0
            passed_tests = 0
            failed_tests = 0

            if summary_line:
                if 'passed' in summary_line:
                    # Parse "X passed" format
                    parts = summary_line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed' and i > 0:
                            passed_tests = int(parts[i-1])
                            break

                if 'failed' in summary_line:
                    # Parse "X failed" format
                    parts = summary_line.split()
                    for i, part in enumerate(parts):
                        if part == 'failed' and i > 0:
                            failed_tests = int(parts[i-1])
                            break

                total_tests = passed_tests + failed_tests

            success = result.returncode == 0 and failed_tests == 0

            test_result = {
                'file': test_file,
                'success': success,
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'returncode': result.returncode
            }

            if not success:
                test_result['stdout'] = result.stdout
                test_result['stderr'] = result.stderr

            return test_result

        except subprocess.TimeoutExpired:
            logger.error(f"Test {test_file} timed out after 5 minutes")
            return {
                'file': test_file,
                'success': False,
                'error': 'Timeout',
                'total': 0,
                'passed': 0,
                'failed': 1
            }
        except Exception as e:
            logger.error(f"Error running test {test_file}: {e}")
            return {
                'file': test_file,
                'success': False,
                'error': str(e),
                'total': 0,
                'passed': 0,
                'failed': 1
            }

    def run_all_tests(self, categories: Optional[List[str]] = None) -> bool:
        """
        Run all test categories or specified categories.

        Args:
            categories: List of categories to run, or None for all

        Returns:
            True if all tests pass, False otherwise
        """
        if categories is None:
            categories = list(self.test_categories.keys())

        logger.info("🚀 Starting Bridge Removal Validation Test Suite")
        logger.info(f"Categories to test: {', '.join(categories)}")

        overall_success = True
        total_duration = 0

        for category in categories:
            success, results = self.run_test_category(category)
            self.test_results[category] = results
            total_duration += results.get('duration', 0)

            if not success:
                overall_success = False

        # Generate final report
        self._generate_final_report(total_duration)

        return overall_success

    def _generate_final_report(self, total_duration: float):
        """Generate final test report."""
        logger.info("\n" + "="*80)
        logger.info("🔍 BRIDGE REMOVAL VALIDATION REPORT")
        logger.info("="*80)

        total_tests = 0
        total_passed = 0
        total_failed = 0
        categories_passed = 0
        total_categories = len(self.test_results)

        for category, results in self.test_results.items():
            status = "✅ PASS" if results['success'] else "❌ FAIL"
            logger.info(
                f"{status} {category.upper():20} | "
                f"Tests: {results['passed_tests']:3}/{results['total_tests']:3} | "
                f"Time: {results['duration']:6.2f}s"
            )

            total_tests += results['total_tests']
            total_passed += results['passed_tests']
            total_failed += results['failed_tests']

            if results['success']:
                categories_passed += 1

        logger.info("-" * 80)
        logger.info(
            f"TOTAL SUMMARY: {total_passed}/{total_tests} tests passed "
            f"({categories_passed}/{total_categories} categories) "
            f"in {total_duration:.2f}s"
        )

        if total_failed == 0:
            logger.info("🎉 ALL TESTS PASSED - Bridge removal is SAFE!")
            logger.info("✅ SingletonToFactoryBridge can be removed without breaking functionality")
            logger.info("✅ Golden Path (users login → get AI responses) remains intact")
            logger.info("✅ $500K+ ARR protection validated")
        else:
            logger.error("❌ TESTS FAILED - Bridge removal is NOT SAFE!")
            logger.error(f"❌ {total_failed} test(s) failed - bridge is still needed")
            logger.error("❌ Do NOT remove SingletonToFactoryBridge until issues are resolved")

        # Save detailed results to file
        self._save_results_to_file()

    def _save_results_to_file(self):
        """Save test results to JSON file for analysis."""
        results_file = Path("test_results_bridge_removal_validation.json")

        report_data = {
            'timestamp': time.time(),
            'total_duration': time.time() - self.start_time,
            'categories': self.test_results,
            'summary': {
                'total_categories': len(self.test_results),
                'categories_passed': sum(1 for r in self.test_results.values() if r['success']),
                'total_tests': sum(r['total_tests'] for r in self.test_results.values()),
                'total_passed': sum(r['passed_tests'] for r in self.test_results.values()),
                'total_failed': sum(r['failed_tests'] for r in self.test_results.values()),
                'overall_success': all(r['success'] for r in self.test_results.values())
            }
        }

        try:
            with open(results_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"📄 Detailed results saved to: {results_file}")
        except Exception as e:
            logger.warning(f"Could not save results file: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bridge Removal Validation Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--category',
        choices=['mission_critical', 'integration', 'e2e', 'performance', 'all'],
        default='all',
        help='Test category to run (default: all)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Create test runner
    runner = BridgeRemovalTestRunner(verbose=args.verbose)

    # Run tests
    if args.category == 'all':
        success = runner.run_all_tests()
    else:
        success = runner.run_all_tests([args.category])

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()