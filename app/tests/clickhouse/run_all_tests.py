"""
ClickHouse Test Runner
Runs all ClickHouse test suites and generates coverage report
"""

import sys
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
import json


def run_clickhouse_tests():
    """Run all ClickHouse test suites"""
    
    print("=" * 80)
    print("CLICKHOUSE QUERY TESTS - COMPREHENSIVE VALIDATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    test_suites = [
        ("Query Correctness", "test_query_correctness.py"),
        ("Performance & Edge Cases", "test_performance_edge_cases.py"),
        ("Corpus Generation Coverage", "test_corpus_generation_coverage.py")
    ]
    
    results = {}
    total_passed = 0
    total_failed = 0
    
    for suite_name, test_file in test_suites:
        print(f"\n{'=' * 60}")
        print(f"Running Test Suite: {suite_name}")
        print(f"File: {test_file}")
        print("=" * 60)
        
        # Run pytest for this specific test file
        result = pytest.main([
            "-v",
            "-x",  # Stop on first failure
            "--tb=short",  # Short traceback format
            f"app/tests/clickhouse/{test_file}",
            "--cov=app.services.corpus_service",
            "--cov=app.services.generation_service",
            "--cov=app.agents.data_sub_agent",
            "--cov=app.db.clickhouse",
            "--cov=app.db.clickhouse_init",
            "--cov=app.db.models_clickhouse",
            "--cov-append",
            "-p", "no:warnings"
        ])
        
        results[suite_name] = {
            "file": test_file,
            "exit_code": result,
            "status": "PASSED" if result == 0 else "FAILED"
        }
        
        if result == 0:
            total_passed += 1
            print(f"✅ {suite_name}: PASSED")
        else:
            total_failed += 1
            print(f"❌ {suite_name}: FAILED")
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for suite_name, result in results.items():
        status_icon = "✅" if result["status"] == "PASSED" else "❌"
        print(f"{status_icon} {suite_name}: {result['status']}")
    
    print(f"\nTotal Suites: {len(test_suites)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    
    # Generate coverage report
    print("\n" + "=" * 80)
    print("COVERAGE REPORT")
    print("=" * 80)
    
    pytest.main([
        "--cov=app.services.corpus_service",
        "--cov=app.services.generation_service",
        "--cov=app.agents.data_sub_agent",
        "--cov=app.db.clickhouse",
        "--cov=app.db.clickhouse_init",
        "--cov=app.db.models_clickhouse",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/clickhouse",
        "--cov-report=json:coverage-clickhouse.json",
        "--no-header",
        "-q"
    ])
    
    # Save results to file
    results_file = Path("test_reports/clickhouse_test_results.json")
    results_file.parent.mkdir(exist_ok=True)
    
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "suites": results,
            "summary": {
                "total": len(test_suites),
                "passed": total_passed,
                "failed": total_failed
            }
        }, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    print(f"HTML coverage report: htmlcov/clickhouse/index.html")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_clickhouse_tests()
    sys.exit(0 if success else 1)