"""
Runner for the Top 100 E2E Staging Tests
Executes tests with proper pytest reporting
"""

import subprocess
import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime

def run_pytest_tests():
    """Run pytest tests and capture output"""
    
    # Change to staging directory
    staging_dir = Path(__file__).parent
    os.chdir(staging_dir)
    
    print("=" * 70)
    print("RUNNING TOP 100 E2E STAGING TESTS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Pytest command with various output formats
    pytest_args = [
        sys.executable, "-m", "pytest",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-m", "staging",  # Only run staging tests
        "--junit-xml=test_results.xml",  # JUnit XML output
        "--html=test_results.html",  # HTML report (requires pytest-html)
        "--self-contained-html",  # Embed CSS/JS in HTML
        "--json-report",  # JSON report (requires pytest-json-report)
        "--json-report-file=test_results.json",
        "--capture=no",  # Show print statements
        "."  # Current directory
    ]
    
    # Run pytest
    print("Executing pytest with full reporting...")
    print(f"Command: {' '.join(pytest_args)}")
    print("-" * 70)
    
    result = subprocess.run(
        pytest_args,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print("-" * 70)
    
    # Parse and display results
    parse_test_results()
    
    return result.returncode

def parse_test_results():
    """Parse test results from various formats"""
    
    staging_dir = Path(__file__).parent
    
    # Try to read JSON report if available
    json_report = staging_dir / "test_results.json"
    if json_report.exists():
        with open(json_report, encoding='utf-8') as f:
            data = json.load(f)
            
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        summary = data.get("summary", {})
        print(f"Total Tests: {summary.get('total', 0)}")
        print(f"Passed: {summary.get('passed', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Skipped: {summary.get('skipped', 0)}")
        print(f"Duration: {data.get('duration', 0):.2f} seconds")
        
        # List failed tests
        if summary.get('failed', 0) > 0:
            print("\n[X] FAILED TESTS:")
            for test in data.get("tests", []):
                if test.get("outcome") == "failed":
                    print(f"  - {test['nodeid']}")
                    if test.get("call", {}).get("longrepr"):
                        print(f"    Error: {test['call']['longrepr'][:100]}...")
        
        # List by priority
        print("\nTESTS BY PRIORITY:")
        priority_count = {}
        
        for test in data.get("tests", []):
            # Extract priority from markers or test name
            markers = test.get("keywords", [])
            priority = "normal"
            
            if "critical" in markers:
                priority = "critical"
            elif "high" in markers:
                priority = "high"
            elif "medium" in markers:
                priority = "medium"
            elif "low" in markers:
                priority = "low"
            
            if priority not in priority_count:
                priority_count[priority] = {"total": 0, "passed": 0, "failed": 0}
            
            priority_count[priority]["total"] += 1
            if test.get("outcome") == "passed":
                priority_count[priority]["passed"] += 1
            elif test.get("outcome") == "failed":
                priority_count[priority]["failed"] += 1
        
        for priority, counts in sorted(priority_count.items()):
            print(f"  {priority.upper()}: {counts['passed']}/{counts['total']} passed")
    
    # Generate markdown report
    generate_markdown_report()

def generate_markdown_report():
    """Generate comprehensive markdown report"""
    
    staging_dir = Path(__file__).parent
    report_path = staging_dir.parent.parent.parent / "STAGING_100_TESTS_REPORT.md"
    
    # Read test results
    json_report = staging_dir / "test_results.json"
    
    if not json_report.exists():
        # Create basic report without JSON data
        with open(report_path, "w", encoding='utf-8') as f:
            f.write("# Staging 100 Tests Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write("Test results not available. Run tests with pytest-json-report installed.\n")
        return
    
    with open(json_report, encoding='utf-8') as f:
        data = json.load(f)
    
    with open(report_path, "w", encoding='utf-8') as f:
        f.write("# Top 100 E2E Staging Tests - Execution Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Environment:** Staging - https://api.staging.netrasystems.ai\n")
        f.write(f"**Test Framework:** Pytest {data.get('pytest_version', 'unknown')}\n\n")
        
        # Executive Summary
        summary = data.get("summary", {})
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Tests:** {summary.get('total', 0)}\n")
        f.write(f"- **Passed:** {summary.get('passed', 0)}\n")
        f.write(f"- **Failed:** {summary.get('failed', 0)}\n")
        f.write(f"- **Skipped:** {summary.get('skipped', 0)}\n")
        f.write(f"- **Duration:** {data.get('duration', 0):.2f} seconds\n")
        
        pass_rate = (summary.get('passed', 0) / summary.get('total', 1)) * 100
        f.write(f"- **Pass Rate:** {pass_rate:.1f}%\n\n")
        
        # Test Results Table
        f.write("## Test Results\n\n")
        f.write("### Pytest Output\n\n")
        f.write("```\n")
        
        # Generate pytest-style output
        tests = data.get("tests", [])
        for test in tests:
            outcome = test.get("outcome", "unknown").upper()
            nodeid = test.get("nodeid", "unknown")
            duration = test.get("duration", 0)
            
            if outcome == "PASSED":
                f.write(f"{nodeid} PASSED [{duration:.2f}s]\n")
            elif outcome == "FAILED":
                f.write(f"{nodeid} FAILED [{duration:.2f}s]\n")
            elif outcome == "SKIPPED":
                f.write(f"{nodeid} SKIPPED\n")
        
        f.write(f"\n{'='*60}\n")
        f.write(f"{summary.get('passed', 0)} passed")
        if summary.get('failed', 0) > 0:
            f.write(f", {summary.get('failed', 0)} failed")
        if summary.get('skipped', 0) > 0:
            f.write(f", {summary.get('skipped', 0)} skipped")
        f.write(f" in {data.get('duration', 0):.2f}s\n")
        f.write("```\n\n")
        
        # Detailed Results by Priority
        f.write("## Results by Priority\n\n")
        
        priority_tests = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "normal": []
        }
        
        for test in tests:
            markers = test.get("keywords", [])
            priority = "normal"
            
            if "critical" in markers:
                priority = "critical"
            elif "high" in markers:
                priority = "high"
            elif "medium" in markers:
                priority = "medium"
            elif "low" in markers:
                priority = "low"
            
            priority_tests[priority].append(test)
        
        priority_labels = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]",
            "medium": "[MEDIUM]",
            "low": "[LOW]",
            "normal": "[NORMAL]"
        }
        
        for priority, label in priority_labels.items():
            tests = priority_tests[priority]
            if tests:
                passed = sum(1 for t in tests if t.get("outcome") == "passed")
                failed = sum(1 for t in tests if t.get("outcome") == "failed")
                
                f.write(f"### {label} Priority\n\n")
                f.write(f"**Results:** {passed}/{len(tests)} passed")
                if failed > 0:
                    f.write(f", {failed} failed")
                f.write("\n\n")
                
                f.write("| Test | Result | Duration |\n")
                f.write("|------|--------|----------|\n")
                
                for test in tests:
                    name = test.get("nodeid", "").split("::")[-1]
                    outcome = test.get("outcome", "unknown")
                    duration = test.get("duration", 0)
                    
                    icon = "[PASS]" if outcome == "passed" else "[FAIL]" if outcome == "failed" else "[SKIP]"
                    f.write(f"| {name} | {icon} {outcome} | {duration:.3f}s |\n")
                
                f.write("\n")
        
        # Failed Test Details
        failed_tests = [t for t in data.get("tests", []) if t.get("outcome") == "failed"]
        if failed_tests:
            f.write("## Failed Test Details\n\n")
            
            for test in failed_tests:
                f.write(f"### [FAILED] {test.get('nodeid', 'unknown')}\n\n")
                
                if test.get("call", {}).get("longrepr"):
                    f.write("**Error:**\n")
                    f.write("```\n")
                    f.write(test["call"]["longrepr"][:1000])
                    if len(test["call"]["longrepr"]) > 1000:
                        f.write("...\n")
                    f.write("```\n\n")
        
        # Test Coverage
        f.write("## Test Coverage Analysis\n\n")
        f.write("| Category | Total | Passed | Failed | Coverage |\n")
        f.write("|----------|-------|--------|--------|----------|\n")
        
        categories = {
            "WebSocket": ["websocket", "ws"],
            "Agent": ["agent"],
            "Message": ["message", "thread"],
            "Auth": ["auth", "jwt", "oauth"],
            "Error": ["error", "exception"],
            "Performance": ["performance", "latency"]
        }
        
        all_tests = data.get("tests", [])
        for category, keywords in categories.items():
            cat_tests = [t for t in all_tests 
                        if any(kw in t.get("nodeid", "").lower() for kw in keywords)]
            
            if cat_tests:
                passed = sum(1 for t in cat_tests if t.get("outcome") == "passed")
                failed = sum(1 for t in cat_tests if t.get("outcome") == "failed")
                coverage = (passed / len(cat_tests)) * 100 if cat_tests else 0
                
                f.write(f"| {category} | {len(cat_tests)} | {passed} | {failed} | {coverage:.1f}% |\n")
        
        # Environment Info
        f.write("\n## Environment Information\n\n")
        f.write("- **Python Version:** " + data.get("environment", {}).get("Python", "unknown") + "\n")
        f.write("- **Platform:** " + data.get("environment", {}).get("Platform", "unknown") + "\n")
        
        # Recommendations
        f.write("\n## Recommendations\n\n")
        
        if pass_rate >= 95:
            f.write("[SUCCESS] **System is production ready** - Pass rate exceeds 95%\n\n")
        elif pass_rate >= 80:
            f.write("[WARNING] **System needs attention** - Pass rate is between 80-95%\n\n")
        else:
            f.write("[FAILURE] **System not ready** - Pass rate below 80%\n\n")
        
        if failed_tests:
            f.write("### Priority Actions:\n\n")
            critical_failures = [t for t in failed_tests 
                               if "critical" in t.get("keywords", [])]
            if critical_failures:
                f.write(f"1. **Fix {len(critical_failures)} critical test failures immediately**\n")
            
            high_failures = [t for t in failed_tests 
                           if "high" in t.get("keywords", [])]
            if high_failures:
                f.write(f"2. **Address {len(high_failures)} high priority failures**\n")
        
        f.write("\n---\n")
        f.write("*Report generated by Top 100 E2E Test Framework*\n")
    
    print(f"\n[REPORT] Report saved to: {report_path.absolute()}")

def main():
    """Main execution function"""
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest is not installed")
        print("Install with: pip install pytest pytest-html pytest-json-report")
        sys.exit(1)
    
    # Run tests
    exit_code = run_pytest_tests()
    
    # Show final status
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("[SUCCESS] ALL TESTS PASSED")
    else:
        print(f"[FAILURE] TESTS FAILED (exit code: {exit_code})")
    print("=" * 70)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())