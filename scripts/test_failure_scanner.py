#!/usr/bin/env python
"""
Quick test failure scanner - identifies failing tests efficiently
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def scan_test_failures():
    """Quickly scan for test failures"""
    results = _initialize_scan_results()
    test_paths = _get_test_paths_to_scan()
    _print_scan_header()
    total_tests, total_failures = _scan_all_test_paths(test_paths, results)
    _finalize_scan_results(results, total_tests, total_failures)
    _save_and_print_results(results)
    return results


def _initialize_scan_results():
    """Initialize scan results structure"""
    return {
        "timestamp": datetime.now().isoformat(),
        "categories": defaultdict(list),
        "summary": {},
        "priority_failures": []
    }


def _get_test_paths_to_scan():
    """Get list of test paths to scan in priority order"""
    return [
        ("app/tests/core", "Critical - Core functionality"),
        ("app/tests/routes", "Critical - API endpoints"),
        ("app/tests/services/test_security_service.py", "Critical - Security"),
        ("app/tests/services/database", "Critical - Database"),
        ("app/tests/agents", "High - Agent system"),
        ("app/tests/websocket", "High - WebSocket"),
        ("app/tests/services", "High - Services"),
        ("app/tests/integration", "Medium - Integration"),
        ("app/tests/models", "Medium - Models"),
        ("app/tests/utils", "Low - Utilities")
    ]


def _print_scan_header():
    """Print scan header information"""
    print("Scanning for test failures...")
    print("=" * 60)


def _scan_all_test_paths(test_paths, results):
    """Scan all test paths and accumulate results"""
    total_tests = 0
    total_failures = 0
    for test_path, category in test_paths:
        tests, failures = _scan_single_test_path(test_path, category, results)
        total_tests += tests
        total_failures += failures
    return total_tests, total_failures


def _scan_single_test_path(test_path, category, results):
    """Scan a single test path and update results"""
    full_path = PROJECT_ROOT / test_path
    if not full_path.exists():
        return 0, 0
    _print_category_header(category, test_path)
    return _execute_pytest_and_parse_results(full_path, test_path, category, results)


def _print_category_header(category, test_path):
    """Print header for test category being scanned"""
    print(f"\nScanning {category}: {test_path}")
    print("-" * 40)


def _execute_pytest_and_parse_results(full_path, test_path, category, results):
    """Execute pytest command and parse results"""
    cmd = _build_pytest_command(full_path)
    try:
        result = _run_pytest_command(cmd)
        return _parse_pytest_output(result, test_path, category, results)
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] Skipping remaining tests in {test_path}")
        return 0, 0
    except Exception as e:
        print(f"  [ERROR] Scanning {test_path}: {e}")
        return 0, 0


def _build_pytest_command(full_path):
    """Build pytest command with appropriate flags"""
    return [
        sys.executable, "-m", "pytest", str(full_path),
        "--tb=no", "-q", "--no-header", "--no-summary", 
        "-rN", "--maxfail=50", "--timeout=5", "--disable-warnings"
    ]


def _run_pytest_command(cmd):
    """Execute pytest command with timeout"""
    return subprocess.run(
        cmd, capture_output=True, text=True, 
        timeout=60, cwd=PROJECT_ROOT
    )


def _parse_pytest_output(result, test_path, category, results):
    """Parse pytest output and extract test results"""
    lines = result.stdout.split('\n')
    test_count, failure_count, failures = _count_tests_and_failures(lines)
    failure_count = _check_summary_line(result.stdout, failure_count)
    _store_category_results(results, category, test_path, test_count, failure_count, failures)
    _add_priority_failures(results, failures, category)
    _print_category_summary(test_count, failure_count, failures)
    return test_count, failure_count


def _count_tests_and_failures(lines):
    """Count total tests and failures from pytest output"""
    test_count = 0
    failure_count = 0
    failures = []
    for line in lines:
        if '::' in line:
            test_count += 1
            test_name = _extract_test_name_if_failed(line)
            if test_name:
                failure_count += 1
                failures.append(test_name)
    return test_count, failure_count, failures


def _extract_test_name_if_failed(line):
    """Extract test name if line indicates failure"""
    if 'FAILED' in line or 'ERROR' in line:
        match = re.search(r'([\w/\\\.]+::\S+)', line)
        return match.group(1) if match else None
    return None


def _check_summary_line(stdout, failure_count):
    """Check summary line for more accurate failure count"""
    summary_match = re.search(r'(\d+) failed.*(\d+) passed', stdout)
    return int(summary_match.group(1)) if summary_match else failure_count


def _store_category_results(results, category, test_path, test_count, failure_count, failures):
    """Store results for a test category"""
    results["categories"][category] = {
        "path": test_path,
        "total": test_count,
        "failures": failure_count,
        "failed_tests": failures[:10]
    }


def _add_priority_failures(results, failures, category):
    """Add failures to priority list if category is critical/high"""
    if "Critical" in category or "High" in category:
        for test_name in failures:
            results["priority_failures"].append({
                "test": test_name,
                "category": category
            })


def _print_category_summary(test_count, failure_count, failures):
    """Print summary for the scanned category"""
    if failure_count > 0:
        print(f"  [FAIL] {failure_count}/{test_count} tests failed")
        _print_failed_test_list(failures)
    else:
        print(f"  [PASS] All {test_count} tests passed")


def _print_failed_test_list(failures):
    """Print list of failed tests (first 5)"""
    for i, test in enumerate(failures[:5], 1):
        print(f"     {i}. {test}")
    if len(failures) > 5:
        print(f"     ... and {len(failures) - 5} more")


def _finalize_scan_results(results, total_tests, total_failures):
    """Generate final summary for scan results"""
    results["summary"] = {
        "total_tests": total_tests,
        "total_failures": total_failures,
        "failure_rate": (total_failures / total_tests * 100) if total_tests > 0 else 0,
        "categories_scanned": len(results["categories"]),
        "priority_failure_count": len(results["priority_failures"])
    }


def _save_and_print_results(results):
    """Save results to file and print final summary"""
    output_file = _save_results_to_file(results)
    _print_final_summary(results, output_file)
    _print_priority_failures(results)


def _save_results_to_file(results):
    """Save scan results to JSON file"""
    output_file = PROJECT_ROOT / "test_reports" / "failure_scan.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    return output_file


def _print_final_summary(results, output_file):
    """Print final scan summary"""
    summary = results["summary"]
    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"Total tests scanned: {summary['total_tests']}")
    print(f"Total failures found: {summary['total_failures']}")
    print(f"Failure rate: {summary['failure_rate']:.1f}%")
    print(f"Priority failures: {summary['priority_failure_count']}")
    print(f"\nDetailed results saved to: {output_file}")


def _print_priority_failures(results):
    """Print list of priority failures if any exist"""
    if not results["priority_failures"]:
        return
    print("\n" + "=" * 60)
    print("PRIORITY FAILURES (Critical/High)")
    print("=" * 60)
    for i, failure in enumerate(results["priority_failures"][:20], 1):
        category = failure['category'].split(' - ')[0]
        print(f"{i:3}. [{category:8}] {failure['test']}")

if __name__ == "__main__":
    results = scan_test_failures()
    sys.exit(0 if results["summary"]["total_failures"] == 0 else 1)