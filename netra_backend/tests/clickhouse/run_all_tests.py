"""
ClickHouse Test Runner
Runs all ClickHouse test suites and generates coverage report
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest


def run_clickhouse_tests():
    """Run all ClickHouse test suites"""
    _print_test_header()
    test_suites = _get_test_suites()
    results, total_passed, total_failed = _run_test_suites(test_suites)
    _print_test_summary(results, test_suites, total_passed, total_failed)
    _generate_coverage_report()
    _save_test_results(results, test_suites, total_passed, total_failed)
    return total_failed == 0

def _print_test_header():
    """Print test run header information."""
    print("=" * 80)
    print("CLICKHOUSE QUERY TESTS - COMPREHENSIVE VALIDATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print()

def _get_test_suites() -> list:
    """Get list of test suites to run."""
    return [
        ("Query Correctness", "test_query_correctness.py"),
        ("Performance & Edge Cases", "test_performance_edge_cases.py"),
        ("Corpus Generation Coverage", "test_corpus_generation_coverage.py")
    ]

def _run_test_suites(test_suites: list) -> tuple:
    """Run all test suites and collect results."""
    results = {}
    total_passed = 0
    total_failed = 0
    for suite_name, test_file in test_suites:
        result_code = _run_single_test_suite(suite_name, test_file)
        results[suite_name] = _create_suite_result(test_file, result_code)
        total_passed, total_failed = _update_counters(result_code, total_passed, total_failed, suite_name)
    return results, total_passed, total_failed

def _run_single_test_suite(suite_name: str, test_file: str) -> int:
    """Run a single test suite and return exit code."""
    _print_suite_header(suite_name, test_file)
    pytest_args = _get_pytest_args(test_file)
    return pytest.main(pytest_args)

def _print_suite_header(suite_name: str, test_file: str):
    """Print header for individual test suite."""
    print(f"\n{'=' * 60}")
    print(f"Running Test Suite: {suite_name}")
    print(f"File: {test_file}")
    print("=" * 60)

def _get_pytest_args(test_file: str) -> list:
    """Get pytest arguments for test execution."""
    return [
        "-v", "-x", "--tb=short", f"app/tests/clickhouse/{test_file}",
        "--cov=app.services.corpus_service", "--cov=app.services.generation_service",
        "--cov=app.agents.data_sub_agent", "--cov=app.db.clickhouse",
        "--cov=app.db.clickhouse_init", "--cov=app.db.models_clickhouse",
        "--cov-append", "-p", "no:warnings"
    ]

def _create_suite_result(test_file: str, result_code: int) -> dict:
    """Create result dictionary for test suite."""
    return {
        "file": test_file,
        "exit_code": result_code,
        "status": "PASSED" if result_code == 0 else "FAILED"
    }

def _update_counters(result_code: int, total_passed: int, total_failed: int, suite_name: str) -> tuple:
    """Update pass/fail counters and print result."""
    if result_code == 0:
        total_passed += 1
        print(f"✅ {suite_name}: PASSED")
    else:
        total_failed += 1
        print(f"❌ {suite_name}: FAILED")
    return total_passed, total_failed

def _print_test_summary(results: dict, test_suites: list, total_passed: int, total_failed: int):
    """Print comprehensive test summary."""
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    _print_individual_results(results)
    _print_summary_counts(test_suites, total_passed, total_failed)

def _print_individual_results(results: dict):
    """Print individual test suite results."""
    for suite_name, result in results.items():
        status_icon = "✅" if result["status"] == "PASSED" else "❌"
        print(f"{status_icon} {suite_name}: {result['status']}")

def _print_summary_counts(test_suites: list, total_passed: int, total_failed: int):
    """Print summary counts."""
    print(f"\nTotal Suites: {len(test_suites)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")

def _generate_coverage_report():
    """Generate coverage report using pytest."""
    print("\n" + "=" * 80)
    print("COVERAGE REPORT")
    print("=" * 80)
    coverage_args = _get_coverage_args()
    pytest.main(coverage_args)

def _get_coverage_args() -> list:
    """Get pytest arguments for coverage report generation."""
    return [
        "--cov=app.services.corpus_service", "--cov=app.services.generation_service",
        "--cov=app.agents.data_sub_agent", "--cov=app.db.clickhouse",
        "--cov=app.db.clickhouse_init", "--cov=app.db.models_clickhouse",
        "--cov-report=term-missing", "--cov-report=html:htmlcov/clickhouse",
        "--cov-report=json:coverage-clickhouse.json", "--no-header", "-q"
    ]

def _save_test_results(results: dict, test_suites: list, total_passed: int, total_failed: int):
    """Save test results to JSON file."""
    results_file = Path("test_reports/clickhouse_test_results.json")
    results_file.parent.mkdir(exist_ok=True)
    result_data = _create_result_data(results, test_suites, total_passed, total_failed)
    _write_results_file(results_file, result_data)
    _print_result_locations(results_file)

def _create_result_data(results: dict, test_suites: list, total_passed: int, total_failed: int) -> dict:
    """Create result data structure for JSON export."""
    return {
        "timestamp": datetime.now().isoformat(),
        "suites": results,
        "summary": {"total": len(test_suites), "passed": total_passed, "failed": total_failed}
    }

def _write_results_file(results_file: Path, result_data: dict):
    """Write results to JSON file."""
    with open(results_file, "w") as f:
        json.dump(result_data, f, indent=2)

def _print_result_locations(results_file: Path):
    """Print locations of generated reports."""
    print(f"\nResults saved to: {results_file}")
    print(f"HTML coverage report: htmlcov/clickhouse/index.html")


if __name__ == "__main__":
    success = run_clickhouse_tests()
    sys.exit(0 if success else 1)