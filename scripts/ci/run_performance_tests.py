#!/usr/bin/env python3
"""Run performance tests for the Netra platform."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


def run_performance_tests(output_file: Path) -> int:
    """Run performance-specific tests and generate results."""
    results = _initialize_test_results()
    performance_tests = _get_performance_test_patterns()
    _print_test_header()
    _run_all_performance_tests(results, performance_tests)
    _calculate_performance_metrics(results)
    _save_test_results(results, output_file)
    _print_test_summary(results)
    return _get_exit_code(results)

def _initialize_test_results() -> Dict[str, Any]:
    """Initialize test results structure"""
    return {
        "test_type": "performance",
        "timestamp": time.time(),
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "performance_issues": []
        }
    }

def _get_performance_test_patterns() -> List[str]:
    """Get list of performance test patterns"""
    return [
        "test_websocket_production_realistic",
        "test_concurrent_user_load",
        "test_database_repository_critical",
        "test_agent_service_critical",
        "test_clickhouse.*performance",
        "test_redis_manager_operations",
        "test_llm_manager_provider_switching"
    ]

def _print_test_header() -> None:
    """Print test header"""
    print("=" * 60)
    print("RUNNING PERFORMANCE TESTS")
    print("=" * 60)

def _run_all_performance_tests(results: Dict, performance_tests: List[str]) -> None:
    """Run all performance tests"""
    for test_pattern in performance_tests:
        print(f"\nRunning performance test: {test_pattern}")
        test_result = _run_single_performance_test(test_pattern, results)
        results["tests"].append(test_result)
        results["summary"]["total"] += 1
        _update_summary_counters(results, test_result)

def _run_single_performance_test(test_pattern: str, results: Dict) -> Dict[str, Any]:
    """Run a single performance test"""
    test_result = _create_test_result_template(test_pattern)
    start_time = time.time()
    cmd = _build_pytest_command(test_pattern)
    return _execute_test_command(cmd, test_result, start_time, results)

def _create_test_result_template(test_pattern: str) -> Dict[str, Any]:
    """Create test result template"""
    return {
        "name": test_pattern,
        "status": "pending",
        "duration": 0,
        "metrics": {}
    }

def _build_pytest_command(test_pattern: str) -> List[str]:
    """Build pytest command for performance test"""
    return [
        sys.executable, "-m", "pytest",
        "-k", test_pattern,
        "--tb=short",
        "-v",
        "--json-report",
        "--json-report-file=temp_perf_result.json"
    ]

def _execute_test_command(cmd: List[str], test_result: Dict, start_time: float, results: Dict) -> Dict[str, Any]:
    """Execute test command and process results"""
    try:
        result = subprocess.run(
            cmd, cwd=Path.cwd(), capture_output=True,
            text=True, timeout=300
        )
        return _process_test_result(result, test_result, start_time, results)
    except subprocess.TimeoutExpired:
        return _handle_test_timeout(test_result, results)
    except Exception as e:
        return _handle_test_error(test_result, e)

def _process_test_result(result: subprocess.CompletedProcess, test_result: Dict, start_time: float, results: Dict) -> Dict[str, Any]:
    """Process completed test result"""
    test_result["duration"] = time.time() - start_time
    if result.returncode == 0:
        _mark_test_passed(test_result)
    else:
        _mark_test_failed(test_result, result, results)
    _load_detailed_results(test_result)
    return test_result

def _mark_test_passed(test_result: Dict) -> None:
    """Mark test as passed"""
    test_result["status"] = "passed"
    print(f"  ✅ Passed in {test_result['duration']:.2f}s")

def _mark_test_failed(test_result: Dict, result: subprocess.CompletedProcess, results: Dict) -> None:
    """Mark test as failed and check for performance issues"""
    test_result["status"] = "failed"
    print(f"  ❌ Failed in {test_result['duration']:.2f}s")
    if "timeout" in result.stderr.lower():
        _add_performance_issue(test_result, "timeout", results)

def _add_performance_issue(test_result: Dict, issue_type: str, results: Dict) -> None:
    """Add performance issue to results"""
    performance_issue = {
        "test": test_result["name"],
        "issue": issue_type,
        "duration": test_result["duration"]
    }
    results["summary"]["performance_issues"].append(performance_issue)

def _load_detailed_results(test_result: Dict) -> None:
    """Load detailed test results from temp file"""
    temp_result_file = Path("temp_perf_result.json")
    if temp_result_file.exists():
        try:
            with open(temp_result_file, "r") as f:
                detailed_results = json.load(f)
                test_result["details"] = detailed_results
        except:
            pass
        temp_result_file.unlink()

def _handle_test_timeout(test_result: Dict, results: Dict) -> Dict[str, Any]:
    """Handle test timeout"""
    test_result["status"] = "timeout"
    test_result["duration"] = 300
    _add_performance_issue(test_result, "hard_timeout", results)
    print(f"  ⏱️ Timeout after 300s")
    return test_result

def _handle_test_error(test_result: Dict, error: Exception) -> Dict[str, Any]:
    """Handle test execution error"""
    test_result["status"] = "error"
    test_result["error"] = str(error)
    print(f"  🔥 Error: {error}")
    return test_result

def _calculate_performance_metrics(results: Dict) -> None:
    """Calculate performance metrics"""
    total_duration = sum(t["duration"] for t in results["tests"])
    avg_duration = total_duration / len(results["tests"]) if results["tests"] else 0
    results["summary"]["total_duration"] = total_duration
    results["summary"]["average_duration"] = avg_duration
    results["summary"]["success_rate"] = _calculate_success_rate(results)

def _calculate_success_rate(results: Dict) -> float:
    """Calculate test success rate"""
    total = results["summary"]["total"]
    passed = results["summary"]["passed"]
    return (passed / total * 100) if total > 0 else 0

def _save_test_results(results: Dict, output_file: Path) -> None:
    """Save test results to file"""
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

def _print_test_summary(results: Dict) -> None:
    """Print test summary"""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    _print_summary_stats(results)
    _print_performance_issues(results)

def _print_summary_stats(results: Dict) -> None:
    """Print summary statistics"""
    summary = results["summary"]
    print(f"Total Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Duration: {summary['total_duration']:.2f}s")
    print(f"Average Duration: {summary['average_duration']:.2f}s")

def _print_performance_issues(results: Dict) -> None:
    """Print performance issues if any"""
    issues = results["summary"]["performance_issues"]
    if issues:
        print(f"\n⚠️ Performance Issues Detected: {len(issues)}")
        for issue in issues:
            print(f"  - {issue['test']}: {issue['issue']} ({issue['duration']:.2f}s)")

def _update_summary_counters(results: Dict, test_result: Dict) -> None:
    """Update summary counters based on test result"""
    status = test_result["status"]
    if status == "passed":
        results["summary"]["passed"] += 1
    else:
        results["summary"]["failed"] += 1

def _get_exit_code(results: Dict) -> int:
    """Get exit code based on test results"""
    return 0 if results["summary"]["failed"] == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Run performance tests")
    parser.add_argument("--output", required=True, help="Output JSON file for results")
    
    args = parser.parse_args()
    
    return run_performance_tests(Path(args.output))


if __name__ == "__main__":
    sys.exit(main())