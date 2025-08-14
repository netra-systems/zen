#!/usr/bin/env python3
"""Run security tests for the Netra platform."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple


def run_security_tests(output_file: Path) -> int:
    """Run security-specific tests and generate results."""
    results = _initialize_security_results()
    security_tests = _get_security_test_patterns()
    
    _print_security_header()
    _run_all_security_tests(security_tests, results)
    _run_static_analysis(results)
    _finalize_security_results(results, output_file)
    return _determine_exit_code(results)

def _initialize_security_results() -> Dict[str, Any]:
    """Initialize the security test results structure"""
    return {
        "test_type": "security",
        "timestamp": time.time(),
        "tests": [],
        "vulnerabilities": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "security_issues": []
        }
    }

def _get_security_test_patterns() -> List[str]:
    """Get the list of security test patterns to run"""
    return [
        "test_auth_critical",
        "test_security_service",
        "test_tool_permission_service",
        "test_environment_config",
        "test.*authentication",
        "test.*authorization",
        "test.*permission",
        "test.*secret",
        "test.*token"
    ]

def _print_security_header() -> None:
    """Print the security tests header"""
    print("=" * 60)
    print("RUNNING SECURITY TESTS")
    print("=" * 60)

def _run_all_security_tests(security_tests: List[str], results: Dict[str, Any]) -> None:
    """Run all security test patterns"""
    for test_pattern in security_tests:
        print(f"\nRunning security test: {test_pattern}")
        test_result = _run_single_security_test(test_pattern)
        results["tests"].append(test_result)
        results["summary"]["total"] += 1
        _update_test_summary(test_result, results)

def _run_single_security_test(test_pattern: str) -> Dict[str, Any]:
    """Run a single security test pattern"""
    test_result = _create_test_result_template(test_pattern)
    start_time = time.time()
    
    try:
        cmd = _build_pytest_command(test_pattern)
        result = _execute_security_test(cmd)
        test_result["duration"] = time.time() - start_time
        _process_test_output(result, test_result)
        _set_test_status(result, test_result)
    except subprocess.TimeoutExpired:
        _handle_test_timeout(test_result)
    except Exception as e:
        _handle_test_error(test_result, e)
    
    return test_result

def _create_test_result_template(test_pattern: str) -> Dict[str, Any]:
    """Create the initial test result structure"""
    return {
        "name": test_pattern,
        "status": "pending",
        "duration": 0,
        "security_checks": []
    }

def _build_pytest_command(test_pattern: str) -> List[str]:
    """Build the pytest command for security tests"""
    return [
        sys.executable, "-m", "pytest",
        "-k", test_pattern,
        "--tb=short",
        "-v",
        "--capture=no"  # Show output for security tests
    ]

def _execute_security_test(cmd: List[str]) -> subprocess.CompletedProcess:
    """Execute the security test command"""
    return subprocess.run(
        cmd,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=180  # 3 minute timeout per test
    )

def _process_test_output(result: subprocess.CompletedProcess, test_result: Dict[str, Any]) -> None:
    """Process test output for security issues"""
    output_lower = result.stdout.lower() + result.stderr.lower()
    security_patterns = _get_security_issue_patterns()
    
    for issue_name, pattern in security_patterns:
        if pattern in output_lower:
            test_result["security_checks"].append({
                "check": issue_name,
                "found": True
            })

def _get_security_issue_patterns() -> List[Tuple[str, str]]:
    """Get security issue patterns to check for"""
    return [
        ("hardcoded password", "password"),
        ("exposed secret", "secret"),
        ("sql injection", "sql"),
        ("xss vulnerability", "xss"),
        ("csrf vulnerability", "csrf"),
        ("insecure token", "token"),
        ("weak encryption", "encryption"),
        ("missing authentication", "auth")
    ]

def _set_test_status(result: subprocess.CompletedProcess, test_result: Dict[str, Any]) -> None:
    """Set the test status based on result"""
    if result.returncode == 0:
        test_result["status"] = "passed"
        print(f"  [PASS] Passed in {test_result['duration']:.2f}s")
    else:
        test_result["status"] = "failed"
        print(f"  [FAIL] Failed in {test_result['duration']:.2f}s")

def _handle_test_timeout(test_result: Dict[str, Any]) -> None:
    """Handle test timeout scenario"""
    test_result["status"] = "timeout"
    test_result["duration"] = 180
    print(f"  [TIMEOUT] Timeout after 180s")

def _handle_test_error(test_result: Dict[str, Any], error: Exception) -> None:
    """Handle test execution error"""
    test_result["status"] = "error"
    test_result["error"] = str(error)
    print(f"  [ERROR] Error: {error}")

def _update_test_summary(test_result: Dict[str, Any], results: Dict[str, Any]) -> None:
    """Update the test summary with results"""
    if test_result["status"] == "passed":
        results["summary"]["passed"] += 1
    else:
        results["summary"]["failed"] += 1
    
    # Add security issues found to summary
    for check in test_result["security_checks"]:
        results["summary"]["security_issues"].append({
            "test": test_result["name"],
            "issue": check["check"]
        })

def _run_static_analysis(results: Dict[str, Any]) -> None:
    """Run bandit static security analysis"""
    print("\n" + "=" * 60)
    print("RUNNING STATIC SECURITY ANALYSIS")
    print("=" * 60)
    
    try:
        bandit_result = _execute_bandit_scan()
        _process_bandit_results(bandit_result, results)
    except Exception as e:
        print(f"  [WARNING] Could not run static security analysis: {e}")

def _execute_bandit_scan() -> subprocess.CompletedProcess:
    """Execute bandit security scanner"""
    bandit_cmd = [
        sys.executable, "-m", "bandit",
        "-r", "app",
        "-f", "json",
        "-ll"  # Only show medium and high severity issues
    ]
    
    return subprocess.run(
        bandit_cmd,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=60
    )

def _process_bandit_results(bandit_result: subprocess.CompletedProcess, results: Dict[str, Any]) -> None:
    """Process bandit scan results"""
    if bandit_result.stdout:
        bandit_data = json.loads(bandit_result.stdout)
        if "results" in bandit_data:
            _add_vulnerabilities_to_results(bandit_data["results"], results)
            print(f"  Found {len(bandit_data['results'])} potential security issues")

def _add_vulnerabilities_to_results(bandit_issues: List[Dict], results: Dict[str, Any]) -> None:
    """Add bandit vulnerabilities to results"""
    for issue in bandit_issues:
        results["vulnerabilities"].append({
            "type": "static_analysis",
            "severity": issue.get("issue_severity", "unknown"),
            "confidence": issue.get("issue_confidence", "unknown"),
            "description": issue.get("issue_text", ""),
            "file": issue.get("filename", ""),
            "line": issue.get("line_number", 0)
        })

def _finalize_security_results(results: Dict[str, Any], output_file: Path) -> None:
    """Finalize and save security test results"""
    _calculate_security_metrics(results)
    _save_results_to_file(results, output_file)
    _print_security_summary(results)

def _calculate_security_metrics(results: Dict[str, Any]) -> None:
    """Calculate security metrics"""
    summary = results["summary"]
    summary["success_rate"] = (
        summary["passed"] / summary["total"] * 100
        if summary["total"] > 0 else 0
    )
    summary["vulnerability_count"] = len(results["vulnerabilities"])
    summary["security_issue_count"] = len(summary["security_issues"])

def _save_results_to_file(results: Dict[str, Any], output_file: Path) -> None:
    """Save results to output file"""
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

def _print_security_summary(results: Dict[str, Any]) -> None:
    """Print the security test summary"""
    print("\n" + "=" * 60)
    print("SECURITY TEST SUMMARY")
    print("=" * 60)
    _print_basic_summary(results)
    _print_vulnerability_summary(results)
    _print_security_issues_summary(results)

def _print_basic_summary(results: Dict[str, Any]) -> None:
    """Print basic test summary statistics"""
    summary = results["summary"]
    print(f"Total Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")

def _print_vulnerability_summary(results: Dict[str, Any]) -> None:
    """Print vulnerability summary from static analysis"""
    if results["vulnerabilities"]:
        print(f"\n[WARNING] Static Analysis Issues: {len(results['vulnerabilities'])}")
        severity_counts = _count_vulnerabilities_by_severity(results["vulnerabilities"])
        for severity, count in severity_counts.items():
            print(f"  - {severity}: {count}")

def _count_vulnerabilities_by_severity(vulnerabilities: List[Dict]) -> Dict[str, int]:
    """Count vulnerabilities by severity level"""
    severity_counts = {}
    for vuln in vulnerabilities:
        severity = vuln["severity"]
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return severity_counts

def _print_security_issues_summary(results: Dict[str, Any]) -> None:
    """Print security issues found in tests"""
    security_issues = results["summary"]["security_issues"]
    if security_issues:
        print(f"\n[SECURITY] Security Test Issues: {len(security_issues)}")
        for issue in security_issues[:5]:
            print(f"  - {issue['test']}: {issue['issue']}")

def _determine_exit_code(results: Dict[str, Any]) -> int:
    """Determine the exit code based on test results"""
    failed_tests = results["summary"]["failed"]
    vulnerabilities = len(results["vulnerabilities"])
    return 0 if (failed_tests == 0 and vulnerabilities == 0) else 1


def main():
    parser = argparse.ArgumentParser(description="Run security tests")
    parser.add_argument("--output", required=True, help="Output JSON file for results")
    
    args = parser.parse_args()
    
    return run_security_tests(Path(args.output))


if __name__ == "__main__":
    sys.exit(main())