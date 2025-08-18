#!/usr/bin/env python
"""
Runner for Real Service Tests

This script specifically runs tests that require real external services like:
- Real LLM providers (OpenAI, Anthropic, Google)
- Real databases (PostgreSQL, ClickHouse, Redis)
- Real external APIs

These tests are separated from the basic plumbing tests for better organization.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.tests.test_categories import (
    TEST_CATEGORIES,
    get_runnable_categories,
    categorize_test_files,
    validate_environment_for_category,
    should_run_category
)


class RealServiceTestRunner:
    """Runner for tests that require real external services."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.test_dir = Path(__file__).parent
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def check_environment(self) -> Dict[str, bool]:
        """Check which real service categories can be run."""
        self._print_environment_header()
        runnable = get_runnable_categories()
        real_service_categories = self._get_real_service_categories()
        results = self._check_category_availability(runnable, real_service_categories)
        return results
    
    def _print_environment_header(self) -> None:
        """Print environment check header."""
        print("\n" + "="*60)
        print("CHECKING ENVIRONMENT FOR REAL SERVICE TESTS")
        print("="*60)
    
    def _get_real_service_categories(self) -> List[str]:
        """Get list of real service categories."""
        return ["real_llm", "real_database", "real_clickhouse", "real_redis"]
    
    def _check_category_availability(self, runnable: Dict, categories: List[str]) -> Dict[str, bool]:
        """Check availability of each category."""
        results = {}
        for category in categories:
            results[category] = self._check_single_category(runnable, category)
        return results
    
    def _check_single_category(self, runnable: Dict, category: str) -> bool:
        """Check single category availability and print status."""
        can_run = runnable.get(category, False)
        is_valid, missing = validate_environment_for_category(category)
        self._print_category_status(category, can_run, missing)
        return can_run
    
    def _print_category_status(self, category: str, can_run: bool, missing: List[str]) -> None:
        """Print status for a single category."""
        status = "[OK]" if can_run else "[MISSING]"
        print(f"\n{status} {category.upper()}")
        if not can_run and missing:
            print(f"  Missing: {', '.join(missing)}")
        elif can_run:
            print(f"  Ready to run")
    
    def _setup_test_environment(self, category: str) -> Dict[str, str]:
        """Setup environment variables for test category."""
        env = os.environ.copy()
        if category == "real_llm":
            env["ENABLE_REAL_LLM_TESTING"] = "true"
        return env
    
    def _build_pytest_command(self, test_file: Path, category: str) -> List[str]:
        """Build pytest command for test execution."""
        cmd = [sys.executable, "-m", "pytest", str(test_file)]
        cmd.extend(["-v" if self.verbose else "-q", "--tb=short", "--no-header"])
        cmd.extend(["-W", "ignore::DeprecationWarning"])
        if category == "real_llm":
            cmd.extend(["-m", "not skip"])
        return cmd
    
    def _parse_test_output(self, output: str, relative_path: Path) -> tuple[int, int, int, List[str]]:
        """Parse pytest output and extract test counts."""
        import re
        passed, failed, skipped = self._extract_test_counts(output, re)
        errors = self._extract_test_errors(output, relative_path, re)
        return passed, failed, skipped, errors
    
    def _extract_test_counts(self, output: str, re) -> tuple[int, int, int]:
        """Extract passed, failed, and skipped counts from output."""
        passed = self._extract_count(output, r'(\d+) passed', re)
        failed = self._extract_count(output, r'(\d+) failed', re)
        skipped = self._extract_count(output, r'(\d+) skipped', re)
        return passed, failed, skipped
    
    def _extract_count(self, output: str, pattern: str, re) -> int:
        """Extract single count from output using pattern."""
        if match := re.search(pattern, output):
            return int(match.group(1))
        return 0
    
    def _extract_test_errors(self, output: str, relative_path: Path, re) -> List[str]:
        """Extract error messages from test output."""
        errors = []
        if match := re.search(r'(\d+) failed', output):
            errors.append(f"{relative_path}: {match.group(0)}")
        return errors
    
    def _execute_single_test(self, test_file: Path, category: str) -> tuple[int, int, int, List[str]]:
        """Execute a single test file and return results."""
        relative_path = test_file.relative_to(self.test_dir.parent.parent)
        print(f"\n> Running: {relative_path}")
        cmd = self._build_pytest_command(test_file, category)
        env = self._setup_test_environment(category)
        return self._run_test_subprocess(cmd, env, relative_path)
    
    def _run_test_subprocess(self, cmd: List[str], env: Dict[str, str], relative_path: Path) -> tuple[int, int, int, List[str]]:
        """Run test subprocess and handle results."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            return self._process_test_result(result, relative_path)
        except subprocess.TimeoutExpired:
            return self._handle_timeout(relative_path)
        except Exception as e:
            return self._handle_error(e, relative_path)
    
    def _process_test_result(self, result: subprocess.CompletedProcess, relative_path: Path) -> tuple[int, int, int, List[str]]:
        """Process successful test execution result."""
        output = result.stdout + result.stderr
        passed, failed, skipped, errors = self._parse_test_output(output, relative_path)
        failed = self._check_execution_error(result, output, relative_path, failed, errors)
        self._print_verbose_output(result, output)
        return passed, failed, skipped, errors
    
    def _check_execution_error(self, result: subprocess.CompletedProcess, output: str, relative_path: Path, failed: int, errors: List[str]) -> int:
        """Check for execution errors and update failed count."""
        if result.returncode != 0 and "failed" not in output:
            errors.append(f"{relative_path}: Test execution error")
            failed += 1
        return failed
    
    def _print_verbose_output(self, result: subprocess.CompletedProcess, output: str) -> None:
        """Print verbose output if enabled and test failed."""
        if self.verbose and result.returncode != 0:
            print(f"  Output: {output[:500]}")
    
    def _handle_timeout(self, relative_path: Path) -> tuple[int, int, int, List[str]]:
        """Handle subprocess timeout."""
        print(f"  [TIMEOUT] Test took longer than 5 minutes")
        return 0, 1, 0, [f"{relative_path}: Timeout"]
    
    def _handle_error(self, error: Exception, relative_path: Path) -> tuple[int, int, int, List[str]]:
        """Handle subprocess error."""
        print(f"  [ERROR] {str(error)}")
        return 0, 1, 0, [f"{relative_path}: {str(error)}"]
    
    def _aggregate_results(self, category: str, duration: float, passed: int, failed: int, skipped: int, errors: List[str]) -> Dict:
        """Aggregate test results into final dictionary."""
        basic_info = self._create_basic_result_info(category, duration, passed, failed, skipped)
        extended_info = self._add_extended_result_info(errors, failed)
        return {**basic_info, **extended_info}
    
    def _create_basic_result_info(self, category: str, duration: float, passed: int, failed: int, skipped: int) -> Dict:
        """Create basic result information."""
        return {
            "category": category,
            "duration": duration,
            "total": passed + failed + skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped
        }
    
    def _add_extended_result_info(self, errors: List[str], failed: int) -> Dict:
        """Add extended result information."""
        return {
            "errors": errors,
            "status": "passed" if failed == 0 else "failed"
        }
    
    def run_category_tests(self, category: str, test_files: List[Path]) -> Dict:
        """Run tests for a specific category."""
        self._print_category_header(category)
        print(f"Found {len(test_files)} test files")
        start_time = time.time()
        passed, failed, skipped, errors = self._execute_test_files(test_files, category)
        return self._aggregate_results(category, time.time() - start_time, passed, failed, skipped, errors)
    
    def _print_category_header(self, category: str) -> None:
        """Print category test header."""
        print(f"\n{'='*60}\nRUNNING {category.upper()} TESTS\n{'='*60}")
    
    def _execute_test_files(self, test_files: List[Path], category: str) -> tuple[int, int, int, List[str]]:
        """Execute all test files for a category."""
        passed = failed = skipped = 0
        errors = []
        for test_file in test_files:
            p, f, s, e = self._execute_single_test(test_file, category)
            passed += p; failed += f; skipped += s; errors.extend(e)
        return passed, failed, skipped, errors
    
    def run_real_service_tests(self, categories: Optional[List[str]] = None):
        """Run all real service tests that have proper environment setup."""
        self.start_time = datetime.now()
        runnable = self.check_environment()
        categorized = categorize_test_files(self.test_dir)
        categories_to_run = self._determine_categories_to_run(categories, runnable)
        self._execute_real_service_tests(categories_to_run, categorized)
    
    def _determine_categories_to_run(self, categories: Optional[List[str]], runnable: Dict[str, bool]) -> List[str]:
        """Determine which categories should be run."""
        if categories:
            return [c for c in categories if runnable.get(c, False)]
        real_service_categories = ["real_llm", "real_database", "real_clickhouse", "real_redis"]
        return [c for c in real_service_categories if runnable.get(c, False)]
    
    def _execute_real_service_tests(self, categories_to_run: List[str], categorized: Dict) -> None:
        """Execute real service tests for specified categories."""
        if not categories_to_run:
            self._print_no_tests_warning()
            return
        print(f"\n[RUNNING] Tests for categories: {', '.join(categories_to_run)}")
        self._run_category_tests_loop(categories_to_run, categorized)
        self._finalize_test_execution()
    
    def _print_no_tests_warning(self) -> None:
        """Print warning when no tests can be run."""
        print("\n[WARNING] No real service tests can be run!")
        print("Set appropriate environment variables to enable:")
        print("  - ENABLE_REAL_LLM_TESTING=true + API keys for LLM tests")
        print("  - ENABLE_REAL_DB_TESTING=true + DATABASE_URL for database tests")
        print("  - ENABLE_REAL_CLICKHOUSE_TESTING=true + CLICKHOUSE_URL for ClickHouse tests")
        print("  - ENABLE_REAL_REDIS_TESTING=true + REDIS_URL for Redis tests")
    
    def _run_category_tests_loop(self, categories_to_run: List[str], categorized: Dict) -> None:
        """Run tests for each category in the loop."""
        for category in categories_to_run:
            test_files = categorized.get(category, [])
            if test_files:
                result = self.run_category_tests(category, test_files)
                self.results[category] = result
    
    def _finalize_test_execution(self) -> None:
        """Finalize test execution by setting end time and printing summary."""
        self.end_time = datetime.now()
        self.print_summary()
    
    def run_plumbing_tests(self):
        """Run only the basic plumbing tests (no external services required)."""
        self.start_time = datetime.now()
        self._print_plumbing_header()
        categorized = categorize_test_files(self.test_dir)
        categories_to_run = self._get_plumbing_categories()
        self._run_category_tests_loop(categories_to_run, categorized)
        self._finalize_test_execution()
    
    def _print_plumbing_header(self) -> None:
        """Print plumbing tests header."""
        print("\n" + "="*60)
        print("RUNNING PLUMBING TESTS (No External Services)")
        print("="*60)
    
    def _get_plumbing_categories(self) -> List[str]:
        """Get list of plumbing test categories."""
        return ["plumbing", "websocket", "integration"]
    
    def print_summary(self):
        """Print test execution summary."""
        if not self.results:
            return
        self._print_summary_header()
        totals = self._calculate_totals()
        self._print_category_results()
        self._print_final_totals(totals)
    
    def _print_summary_header(self) -> None:
        """Print summary header."""
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
    
    def _calculate_totals(self) -> Dict[str, float]:
        """Calculate total test counts and duration."""
        return {
            "passed": sum(r["passed"] for r in self.results.values()),
            "failed": sum(r["failed"] for r in self.results.values()),
            "skipped": sum(r["skipped"] for r in self.results.values()),
            "duration": sum(r["duration"] for r in self.results.values())
        }
    
    def _print_category_results(self) -> None:
        """Print results for each category."""
        for category, result in self.results.items():
            self._print_single_category_result(category, result)
    
    def _print_single_category_result(self, category: str, result: Dict) -> None:
        """Print result for a single category."""
        status_icon = "[PASS]" if result["status"] == "passed" else "[FAIL]"
        print(f"\n{status_icon} {category.upper()}")
        self._print_category_stats(result)
        self._print_category_errors(result)
    
    def _print_category_stats(self, result: Dict) -> None:
        """Print statistics for a category."""
        print(f"  Passed: {result['passed']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Skipped: {result['skipped']}")
        print(f"  Duration: {result['duration']:.2f}s")
    
    def _print_category_errors(self, result: Dict) -> None:
        """Print errors for a category."""
        if result["errors"]:
            print(f"  Errors:")
            for error in result["errors"][:5]:
                print(f"    - {error}")
    
    def _print_final_totals(self, totals: Dict[str, float]) -> None:
        """Print final totals and execution time."""
        print(f"\n{'='*60}")
        print(f"TOTAL: {int(totals['passed'])} passed, {int(totals['failed'])} failed, {int(totals['skipped'])} skipped")
        print(f"Duration: {totals['duration']:.2f}s")
        print(f"Status: {'SUCCESS' if totals['failed'] == 0 else 'FAILED'}")
        self._print_execution_time()
    
    def _print_execution_time(self) -> None:
        """Print execution time if available."""
        if self.start_time and self.end_time:
            print(f"Execution Time: {self.end_time - self.start_time}")


def main():
    """Main entry point."""
    import argparse
    parser = _create_argument_parser()
    args = parser.parse_args()
    runner = RealServiceTestRunner(verbose=args.verbose)
    _execute_based_on_args(runner, args)

def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(description="Run real service tests")
    _add_category_argument(parser)
    _add_boolean_arguments(parser)
    return parser

def _add_category_argument(parser: argparse.ArgumentParser) -> None:
    """Add category argument to parser."""
    parser.add_argument(
        "--category",
        choices=["real_llm", "real_database", "real_clickhouse", "real_redis", "plumbing", "all"],
        help="Specific category to run"
    )

def _add_boolean_arguments(parser: argparse.ArgumentParser) -> None:
    """Add boolean arguments to parser."""
    parser.add_argument("--plumbing-only", action="store_true", help="Run only plumbing tests (no external services)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--check-only", action="store_true", help="Only check environment, don't run tests")

def _execute_based_on_args(runner: RealServiceTestRunner, args) -> None:
    """Execute appropriate action based on parsed arguments."""
    if args.check_only:
        runner.check_environment()
    elif args.plumbing_only:
        runner.run_plumbing_tests()
    elif args.category:
        _handle_category_argument(runner, args.category)
    else:
        _run_default_tests(runner)

def _handle_category_argument(runner: RealServiceTestRunner, category: str) -> None:
    """Handle category-specific test execution."""
    if category == "all":
        runner.run_real_service_tests()
    elif category == "plumbing":
        runner.run_plumbing_tests()
    else:
        runner.run_real_service_tests([category])

def _run_default_tests(runner: RealServiceTestRunner) -> None:
    """Run default tests (plumbing)."""
    print("Running plumbing tests by default. Use --category to run real service tests.")
    runner.run_plumbing_tests()


if __name__ == "__main__":
    main()