#!/usr/bin/env python3
"""
Issue #860 Test Runner: WebSocket Windows Connection Failures

This script runs the comprehensive test suite for Issue #860 to validate
Windows WebSocket connection failures and their resolution.

CRITICAL REQUIREMENTS:
1. Tests SHOULD FAIL initially to prove they reproduce WinError 1225
2. Only run non-Docker tests (unit, integration without Docker, E2E staging)
3. Follow SSOT patterns and TEST_CREATION_GUIDE.md requirements
4. Provide detailed reporting on test results and issue reproduction

Usage:
    python tests/issue_860_test_runner.py --reproduce-only  # Only run failure reproduction
    python tests/issue_860_test_runner.py --staging-only    # Only test staging solutions
    python tests/issue_860_test_runner.py --full-suite     # Run complete test suite
"""

import sys
import asyncio
import platform
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env

class Issue860TestRunner:
    """Test runner for Issue #860 WebSocket Windows connection failures."""

    def __init__(self):
        self.env = get_env()
        self.is_windows = platform.system().lower() == 'windows'
        self.test_results = {}
        self.start_time = time.time()

        # Test suite definitions
        self.test_suites = {
            "reproduction": {
                "description": "Tests that reproduce Issue #860 WinError 1225 failures",
                "should_fail": True,
                "tests": [
                    "tests/unit/websocket_windows_issues/test_issue_860_websocket_windows_connection_failures.py",
                    "tests/integration/websocket_windows/test_issue_860_websocket_infrastructure_failures.py"
                ]
            },
            "staging_solution": {
                "description": "Tests that validate staging environment solutions",
                "should_fail": False,
                "tests": [
                    "tests/e2e/staging_windows/test_issue_860_staging_websocket_compatibility.py"
                ]
            }
        }

    def run_comprehensive_test_suite(self, suite_filter=None):
        """Run the comprehensive Issue #860 test suite."""
        print("=" * 80)
        print("Issue #860 WebSocket Windows Connection Failures - Test Suite")
        print("=" * 80)
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if not self.is_windows:
            print("⚠️  WARNING: Running on non-Windows platform")
            print("   Issue #860 is Windows-specific, results may not be representative")
            print()

        # Run each test suite
        for suite_name, suite_config in self.test_suites.items():
            if suite_filter and suite_filter != suite_name:
                continue

            print(f"[TEST] Running {suite_name} test suite...")
            print(f"   {suite_config['description']}")
            print(f"   Expected result: {'FAIL' if suite_config['should_fail'] else 'PASS'}")
            print()

            suite_results = self._run_test_suite(suite_name, suite_config)
            self.test_results[suite_name] = suite_results

            self._print_suite_results(suite_name, suite_results)
            print()

        # Generate final report
        self._generate_final_report()

    def _run_test_suite(self, suite_name: str, suite_config: Dict) -> Dict[str, Any]:
        """Run a specific test suite and capture results."""
        suite_results = {
            "suite_name": suite_name,
            "description": suite_config["description"],
            "should_fail": suite_config["should_fail"],
            "tests": [],
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0
            }
        }

        for test_file in suite_config["tests"]:
            print(f"  Running: {test_file}")

            # Check if test file exists
            test_path = project_root / test_file
            if not test_path.exists():
                test_result = {
                    "test_file": test_file,
                    "status": "file_not_found",
                    "error": f"Test file not found: {test_path}",
                    "execution_time": 0
                }
                suite_results["tests"].append(test_result)
                suite_results["summary"]["errors"] += 1
                continue

            # Run the test
            test_result = self._run_single_test(test_file)
            suite_results["tests"].append(test_result)

            # Update summary
            suite_results["summary"]["total_tests"] += 1
            if test_result["status"] == "passed":
                suite_results["summary"]["passed"] += 1
            elif test_result["status"] == "failed":
                suite_results["summary"]["failed"] += 1
            elif test_result["status"] == "skipped":
                suite_results["summary"]["skipped"] += 1
            else:
                suite_results["summary"]["errors"] += 1

        return suite_results

    def _run_single_test(self, test_file: str) -> Dict[str, Any]:
        """Run a single test file and capture results."""
        start_time = time.time()

        try:
            # Use pytest to run the specific test file
            cmd = [
                sys.executable, '-m', 'pytest',
                test_file,
                '-v',
                '--tb=short',
                '--no-header',
                '--tb=line'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout per test file
            )

            execution_time = time.time() - start_time

            # Parse pytest output
            status = "passed" if result.returncode == 0 else "failed"

            # Check for skipped tests
            if "SKIPPED" in result.stdout or "skip" in result.stdout:
                status = "skipped"

            return {
                "test_file": test_file,
                "status": status,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "command": " ".join(cmd)
            }

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                "test_file": test_file,
                "status": "timeout",
                "error": "Test execution timed out after 120 seconds",
                "execution_time": execution_time
            }

        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "test_file": test_file,
                "status": "error",
                "error": str(e),
                "execution_time": execution_time
            }

    def _print_suite_results(self, suite_name: str, results: Dict[str, Any]):
        """Print test suite results."""
        summary = results["summary"]
        should_fail = results["should_fail"]

        print(f"[RESULTS] {suite_name} Results:")
        print(f"   Total: {summary['total_tests']}")
        print(f"   Passed: {summary['passed']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Skipped: {summary['skipped']}")
        print(f"   Errors: {summary['errors']}")

        # Evaluate if results match expectations
        if should_fail:
            expected_behavior = summary['failed'] > 0 or summary['errors'] > 0
            evaluation = "[CORRECT]" if expected_behavior else "[UNEXPECTED]"
            print(f"   Expected: FAILURES (to reproduce Issue #860)")
            print(f"   Actual: {evaluation}")
        else:
            expected_behavior = summary['passed'] > 0 and summary['failed'] == 0
            evaluation = "[CORRECT]" if expected_behavior else "[UNEXPECTED]"
            print(f"   Expected: SUCCESS (solution validation)")
            print(f"   Actual: {evaluation}")

        # Print individual test details
        for test_result in results["tests"]:
            status_icon = {
                "passed": "[PASS]",
                "failed": "[FAIL]",
                "skipped": "[SKIP]",
                "timeout": "[TIME]",
                "error": "[ERR]",
                "file_not_found": "[404]"
            }.get(test_result["status"], "[?]")

            print(f"     {status_icon} {test_result['test_file']} ({test_result['status']})")

            # Print error details for failures
            if test_result["status"] in ["failed", "error", "timeout"]:
                error_info = test_result.get("error") or test_result.get("stderr", "")
                if error_info:
                    # Print first few lines of error
                    error_lines = error_info.split('\n')[:3]
                    for line in error_lines:
                        if line.strip():
                            print(f"       {line.strip()}")

    def _generate_final_report(self):
        """Generate final comprehensive report."""
        total_time = time.time() - self.start_time

        print("=" * 80)
        print("ISSUE #860 TEST EXECUTION FINAL REPORT")
        print("=" * 80)
        print(f"Execution Time: {total_time:.2f} seconds")
        print(f"Platform: {platform.system()}")
        print()

        # Overall summary
        total_tests = sum(results["summary"]["total_tests"] for results in self.test_results.values())
        total_passed = sum(results["summary"]["passed"] for results in self.test_results.values())
        total_failed = sum(results["summary"]["failed"] for results in self.test_results.values())
        total_skipped = sum(results["summary"]["skipped"] for results in self.test_results.values())
        total_errors = sum(results["summary"]["errors"] for results in self.test_results.values())

        print(f"[SUMMARY] OVERALL SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")
        print(f"   Skipped: {total_skipped}")
        print(f"   Errors: {total_errors}")
        print()

        # Issue #860 specific analysis
        print(f"[ANALYSIS] ISSUE #860 ANALYSIS:")

        reproduction_results = self.test_results.get("reproduction", {})
        staging_results = self.test_results.get("staging_solution", {})

        # Check if we successfully reproduced the issue
        issue_reproduced = False
        if reproduction_results:
            issue_reproduced = (
                reproduction_results["summary"]["failed"] > 0 or
                reproduction_results["summary"]["errors"] > 0
            )

        print(f"   Issue Reproduction: {'[SUCCESS]' if issue_reproduced else '[FAILED]'}")

        # Check if staging solution works
        solution_validated = False
        if staging_results:
            solution_validated = (
                staging_results["summary"]["passed"] > 0 and
                staging_results["summary"]["failed"] == 0
            )

        print(f"   Solution Validation: {'[SUCCESS]' if solution_validated else '[FAILED]'}")

        # Overall assessment
        if issue_reproduced and solution_validated:
            assessment = "[COMPLETE] - Issue reproduced AND solution validated"
        elif issue_reproduced:
            assessment = "[PARTIAL] - Issue reproduced but solution not validated"
        elif solution_validated:
            assessment = "[PARTIAL] - Solution works but issue not reproduced"
        else:
            assessment = "[INCOMPLETE] - Neither reproduction nor solution validated"

        print(f"   Overall Assessment: {assessment}")
        print()

        # Recommendations
        print(f"[RECOMMENDATIONS] RECOMMENDATIONS:")
        if not issue_reproduced:
            print("   - Verify that local services are NOT running (Docker down)")
            print("   - Confirm Windows platform detection is working")
            print("   - Check that test environment reproduces original conditions")

        if not solution_validated:
            print("   - Verify staging environment connectivity")
            print("   - Check network access to staging.netrasystems.ai")
            print("   - Validate WebSocket staging endpoints are working")

        if issue_reproduced and solution_validated:
            print("   - Issue #860 test suite is working correctly")
            print("   - Can proceed with implementing fixes")
            print("   - Use staging environment as workaround for Windows developers")

        print()

        # Save results to file
        self._save_results_to_file()

    def _save_results_to_file(self):
        """Save test results to JSON file for analysis."""
        results_file = project_root / "test_results" / "issue_860_test_results.json"
        results_file.parent.mkdir(exist_ok=True)

        output_data = {
            "issue": "Issue #860 WebSocket Windows Connection Failures",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "python_version": sys.version
            },
            "execution_time": time.time() - self.start_time,
            "test_results": self.test_results
        }

        with open(results_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"[FILE] Results saved to: {results_file}")


def main():
    """Main entry point for Issue #860 test runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Issue #860 WebSocket Windows Connection Failures Test Suite"
    )
    parser.add_argument(
        "--reproduce-only",
        action="store_true",
        help="Only run tests that reproduce the issue (should fail)"
    )
    parser.add_argument(
        "--staging-only",
        action="store_true",
        help="Only run staging solution validation tests (should pass)"
    )
    parser.add_argument(
        "--full-suite",
        action="store_true",
        help="Run the complete test suite (default)"
    )

    args = parser.parse_args()

    # Determine which suites to run
    suite_filter = None
    if args.reproduce_only:
        suite_filter = "reproduction"
    elif args.staging_only:
        suite_filter = "staging_solution"

    # Run the test suite
    runner = Issue860TestRunner()
    runner.run_comprehensive_test_suite(suite_filter)


if __name__ == "__main__":
    main()