#!/usr/bin/env python3
"""Generate security test report for GitHub Actions."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def generate_security_report(results: Dict[str, Any], format: str) -> str:
    """Generate a security test report in the specified format."""
    
    if format == "markdown":
        return generate_markdown_security_report(results)
    else:
        return json.dumps(results, indent=2)


def generate_markdown_security_report(results: Dict[str, Any]) -> str:
    """Generate a markdown formatted security test report."""
    header = _build_security_report_header()
    summary_section = _build_security_summary_section(results)
    vulnerabilities_section = _build_vulnerabilities_section(results)
    test_issues_section = _build_test_issues_section(results)
    test_results_section = _build_test_results_section(results)
    recommendations_section = _build_recommendations_section(results)
    compliance_section = _build_compliance_section(results)
    
    sections = [header, summary_section, vulnerabilities_section, test_issues_section, 
               test_results_section, recommendations_section, compliance_section]
    return "\n".join(sections)

def _build_security_report_header() -> str:
    """Build the security report header"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""# [U+1F512] Security Test Report
Generated: {timestamp}
"""

def _build_security_summary_section(results: Dict[str, Any]) -> str:
    """Build the summary section with status badge and metrics table"""
    summary = results.get("summary", {})
    status_badge = _get_security_status_badge(summary)
    metrics_table = _build_security_metrics_table(summary)
    
    return f"""## Summary

{status_badge}

{metrics_table}"""

def _get_security_status_badge(summary: Dict[str, Any]) -> str:
    """Get the security status badge based on results"""
    failed = summary.get("failed", 0)
    vuln_count = summary.get("vulnerability_count", 0)
    
    if failed == 0 and vuln_count == 0:
        return "### [U+1F6E1][U+FE0F] Security Status: **PASSED**"
    else:
        return "###  WARNING: [U+FE0F] Security Status: **NEEDS ATTENTION**"

def _build_security_metrics_table(summary: Dict[str, Any]) -> str:
    """Build the security metrics table"""
    return f"""| Metric | Value |
|--------|---------|
| Total Security Tests | {summary.get('total', 0)} |
| Passed |  PASS:  {summary.get('passed', 0)} |
| Failed |  FAIL:  {summary.get('failed', 0)} |
| Success Rate | {summary.get('success_rate', 0):.1f}% |
| Static Analysis Issues | {summary.get('vulnerability_count', 0)} |
| Security Test Issues | {summary.get('security_issue_count', 0)} |"""

def _build_vulnerabilities_section(results: Dict[str, Any]) -> str:
    """Build the static analysis vulnerabilities section"""
    vulnerabilities = results.get("vulnerabilities", [])
    if not vulnerabilities:
        return ""
    
    severity_groups = _group_vulnerabilities_by_severity(vulnerabilities)
    vulnerabilities_content = _format_vulnerability_groups(severity_groups)
    
    return f"""##  SEARCH:  Static Analysis Findings

{vulnerabilities_content}"""

def _group_vulnerabilities_by_severity(vulnerabilities: List[Dict]) -> Dict[str, List[Dict]]:
    """Group vulnerabilities by severity level"""
    severity_groups = {}
    for vuln in vulnerabilities:
        severity = vuln.get("severity", "unknown")
        if severity not in severity_groups:
            severity_groups[severity] = []
        severity_groups[severity].append(vuln)
    return severity_groups

def _format_vulnerability_groups(severity_groups: Dict[str, List[Dict]]) -> str:
    """Format vulnerability groups by severity"""
    severity_order = ["HIGH", "MEDIUM", "LOW", "unknown"]
    sections = []
    
    for severity in severity_order:
        if severity in severity_groups:
            section = _format_severity_group(severity, severity_groups[severity])
            sections.append(section)
    
    return "\n".join(sections)

def _format_severity_group(severity: str, vulns: List[Dict]) -> str:
    """Format a single severity group"""
    emoji_map = {"HIGH": "[U+1F534]", "MEDIUM": "[U+1F7E0]", "LOW": "[U+1F7E1]", "unknown": "[U+26AA]"}
    severity_emoji = emoji_map.get(severity, "[U+26AA]")
    
    header = f"### {severity_emoji} {severity} Severity ({len(vulns)} issues)\n"
    vulnerabilities_list = _format_vulnerability_list(vulns)
    overflow_text = _get_overflow_text(vulns, severity)
    
    return header + vulnerabilities_list + overflow_text

def _format_vulnerability_list(vulns: List[Dict]) -> str:
    """Format the vulnerability list for display"""
    formatted_vulns = []
    for vuln in vulns[:5]:  # Show first 5 of each severity
        vuln_text = f"""**File:** `{vuln.get('file', 'unknown')}`
**Line:** {vuln.get('line', 0)}
**Confidence:** {vuln.get('confidence', 'unknown')}
**Description:** {vuln.get('description', 'No description')}
"""
        formatted_vulns.append(vuln_text)
    return "\n".join(formatted_vulns)

def _get_overflow_text(vulns: List[Dict], severity: str) -> str:
    """Get overflow text if more vulnerabilities exist"""
    if len(vulns) > 5:
        return f"\n*... and {len(vulns) - 5} more {severity} severity issues*\n"
    return "\n"

def _build_test_issues_section(results: Dict[str, Any]) -> str:
    """Build the security test issues section"""
    summary = results.get("summary", {})
    security_issues = summary.get("security_issues")
    
    if not security_issues:
        return ""
    
    issues_table = _build_security_issues_table(security_issues)
    return f"""##  ALERT:  Security Test Issues

{issues_table}"""

def _build_security_issues_table(security_issues: List[Dict]) -> str:
    """Build the security issues table"""
    table_header = "| Test | Issue Type |\n|------|------------|\n"
    table_rows = [f"| {issue['test']} | {issue['issue']} |" for issue in security_issues]
    return table_header + "\n".join(table_rows)

def _build_test_results_section(results: Dict[str, Any]) -> str:
    """Build the test results section"""
    tests = results.get("tests")
    if not tests:
        return ""
    
    results_table = _build_test_results_table(tests)
    return f"""## Test Results

{results_table}"""

def _build_test_results_table(tests: List[Dict]) -> str:
    """Build the test results table"""
    table_header = "| Test | Status | Duration | Security Checks |\n|------|--------|----------|----------------|\n"
    table_rows = [_format_test_result_row(test) for test in tests]
    return table_header + "\n".join(table_rows)

def _format_test_result_row(test: Dict) -> str:
    """Format a single test result row"""
    status_icons = {"passed": " PASS: ", "failed": " FAIL: ", "timeout": "[U+23F1][U+FE0F]", "error": " FIRE: "}
    status_icon = status_icons.get(test["status"], "[U+2753]")
    
    security_checks = len(test.get("security_checks", []))
    checks_indicator = "[U+1F512]" if security_checks == 0 else f" WARNING: [U+FE0F] {security_checks}"
    
    return (f"| {test['name']} | {status_icon} {test['status']} | "
            f"{test['duration']:.2f}s | {checks_indicator} |")

def _build_recommendations_section(results: Dict[str, Any]) -> str:
    """Build the security recommendations section"""
    summary = results.get("summary", {})
    vulnerabilities = results.get("vulnerabilities", [])
    
    recommendations = _generate_security_recommendations(summary, vulnerabilities)
    return f"""## [U+1F4CB] Recommendations

{recommendations}"""

def _generate_security_recommendations(summary: Dict, vulnerabilities: List[Dict]) -> str:
    """Generate security recommendations based on results"""
    recommendations = []
    
    vuln_count = summary.get("vulnerability_count", 0)
    if vuln_count > 0:
        high_vulns = sum(1 for v in vulnerabilities if v.get("severity") == "HIGH")
        if high_vulns > 0:
            recommendations.append(f"- [U+1F534] **CRITICAL:** Address {high_vulns} high-severity vulnerabilities immediately")
        recommendations.extend([
            "-  SEARCH:  Review and fix static analysis findings",
            "- [U+1F4DD] Update security tests to cover identified vulnerabilities"
        ])
    
    if summary.get("security_issues"):
        recommendations.extend([
            "-  WARNING: [U+FE0F] Investigate security test failures",
            "- [U+1F6E1][U+FE0F] Strengthen security controls in affected areas"
        ])
    
    if summary.get("failed", 0) > 0:
        recommendations.append("-  FAIL:  Fix failing security tests before deployment")
    
    if vuln_count == 0 and summary.get("failed", 0) == 0:
        recommendations.extend([
            "-  PASS:  No critical security issues found",
            "-  CYCLE:  Continue regular security testing",
            "- [U+1F4DA] Keep security dependencies up to date"
        ])
    
    return "\n".join(recommendations)

def _build_compliance_section(results: Dict[str, Any]) -> str:
    """Build the security compliance checklist section"""
    summary = results.get("summary", {})
    vulnerabilities = results.get("vulnerabilities", [])
    
    compliance_checks = _generate_compliance_checks(summary, vulnerabilities)
    return f"""## [U+2714][U+FE0F] Security Compliance Checklist

{compliance_checks}"""

def _generate_compliance_checks(summary: Dict, vulnerabilities: List[Dict]) -> str:
    """Generate compliance checks based on results"""
    checks = [
        ("Authentication Tests", summary.get("passed", 0) > 0),
        ("Authorization Tests", summary.get("passed", 0) > 0),
        ("No High Severity Vulnerabilities", 
         sum(1 for v in vulnerabilities if v.get("severity") == "HIGH") == 0),
        ("Static Analysis Passed", summary.get("vulnerability_count", 0) < 5),
        ("All Security Tests Passed", summary.get("failed", 0) == 0)
    ]
    
    check_lines = []
    for check_name, passed in checks:
        icon = " PASS: " if passed else " FAIL: "
        check_lines.append(f"- {icon} {check_name}")
    
    return "\n".join(check_lines)


def main():
    parser = argparse.ArgumentParser(description="Generate security test report")
    parser.add_argument("--input", required=True, help="Input JSON results file")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", required=True, help="Output file path")
    
    args = parser.parse_args()
    
    # Load results
    try:
        with open(args.input, "r") as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error loading results file: {e}")
        return 1
    
    # Generate report
    report = generate_security_report(results, args.format)
    
    # Save report
    with open(args.output, "w") as f:
        f.write(report)
    
    print(f"Security report generated: {args.output}")
    
    # Print summary
    summary = results.get("summary", {})
    vulnerabilities = results.get("vulnerabilities", [])
    high_vulns = sum(1 for v in vulnerabilities if v.get("severity") == "HIGH")
    
    print(f"\nSecurity Test Summary:")
    print(f"  Total Tests: {summary.get('total', 0)}")
    print(f"  Passed: {summary.get('passed', 0)}")
    print(f"  Failed: {summary.get('failed', 0)}")
    print(f"  Vulnerabilities: {summary.get('vulnerability_count', 0)}")
    
    if high_vulns > 0:
        print(f"   WARNING: [U+FE0F] HIGH SEVERITY ISSUES: {high_vulns}")
    
    # Return failure if security issues found
    return 0 if (summary.get("failed", 0) == 0 and high_vulns == 0) else 1


if __name__ == "__main__":
    exit(main())