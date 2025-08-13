#!/usr/bin/env python3
"""Generate security test report for GitHub Actions."""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def generate_security_report(results: Dict[str, Any], format: str) -> str:
    """Generate a security test report in the specified format."""
    
    if format == "markdown":
        return generate_markdown_security_report(results)
    else:
        return json.dumps(results, indent=2)


def generate_markdown_security_report(results: Dict[str, Any]) -> str:
    """Generate a markdown formatted security test report."""
    report = []
    
    # Header
    report.append("# 🔒 Security Test Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary
    summary = results.get("summary", {})
    report.append("## Summary")
    report.append("")
    
    # Security status badge
    if summary.get("failed", 0) == 0 and summary.get("vulnerability_count", 0) == 0:
        report.append("### 🛡️ Security Status: **PASSED**")
    else:
        report.append("### ⚠️ Security Status: **NEEDS ATTENTION**")
    report.append("")
    
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Total Security Tests | {summary.get('total', 0)} |")
    report.append(f"| Passed | ✅ {summary.get('passed', 0)} |")
    report.append(f"| Failed | ❌ {summary.get('failed', 0)} |")
    report.append(f"| Success Rate | {summary.get('success_rate', 0):.1f}% |")
    report.append(f"| Static Analysis Issues | {summary.get('vulnerability_count', 0)} |")
    report.append(f"| Security Test Issues | {summary.get('security_issue_count', 0)} |")
    report.append("")
    
    # Vulnerabilities from static analysis
    vulnerabilities = results.get("vulnerabilities", [])
    if vulnerabilities:
        report.append("## 🔍 Static Analysis Findings")
        report.append("")
        
        # Group by severity
        severity_groups = {}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "unknown")
            if severity not in severity_groups:
                severity_groups[severity] = []
            severity_groups[severity].append(vuln)
        
        # Sort by severity
        severity_order = ["HIGH", "MEDIUM", "LOW", "unknown"]
        
        for severity in severity_order:
            if severity in severity_groups:
                vulns = severity_groups[severity]
                severity_emoji = {
                    "HIGH": "🔴",
                    "MEDIUM": "🟠",
                    "LOW": "🟡",
                    "unknown": "⚪"
                }.get(severity, "⚪")
                
                report.append(f"### {severity_emoji} {severity} Severity ({len(vulns)} issues)")
                report.append("")
                
                for vuln in vulns[:5]:  # Show first 5 of each severity
                    report.append(f"**File:** `{vuln.get('file', 'unknown')}`")
                    report.append(f"**Line:** {vuln.get('line', 0)}")
                    report.append(f"**Confidence:** {vuln.get('confidence', 'unknown')}")
                    report.append(f"**Description:** {vuln.get('description', 'No description')}")
                    report.append("")
                
                if len(vulns) > 5:
                    report.append(f"*... and {len(vulns) - 5} more {severity} severity issues*")
                    report.append("")
    
    # Security test issues
    if summary.get("security_issues"):
        report.append("## 🚨 Security Test Issues")
        report.append("")
        report.append("| Test | Issue Type |")
        report.append("|------|------------|")
        
        for issue in summary["security_issues"]:
            report.append(f"| {issue['test']} | {issue['issue']} |")
        report.append("")
    
    # Test Results
    if results.get("tests"):
        report.append("## Test Results")
        report.append("")
        report.append("| Test | Status | Duration | Security Checks |")
        report.append("|------|--------|----------|----------------|")
        
        for test in results["tests"]:
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "timeout": "⏱️",
                "error": "🔥"
            }.get(test["status"], "❓")
            
            security_checks = len(test.get("security_checks", []))
            checks_indicator = "🔒" if security_checks == 0 else f"⚠️ {security_checks}"
            
            report.append(
                f"| {test['name']} | "
                f"{status_icon} {test['status']} | "
                f"{test['duration']:.2f}s | "
                f"{checks_indicator} |"
            )
        report.append("")
    
    # Security Recommendations
    report.append("## 📋 Recommendations")
    report.append("")
    
    if summary.get("vulnerability_count", 0) > 0:
        high_vulns = sum(1 for v in vulnerabilities if v.get("severity") == "HIGH")
        if high_vulns > 0:
            report.append(f"- 🔴 **CRITICAL:** Address {high_vulns} high-severity vulnerabilities immediately")
        report.append("- 🔍 Review and fix static analysis findings")
        report.append("- 📝 Update security tests to cover identified vulnerabilities")
    
    if summary.get("security_issues"):
        report.append("- ⚠️ Investigate security test failures")
        report.append("- 🛡️ Strengthen security controls in affected areas")
    
    if summary.get("failed", 0) > 0:
        report.append("- ❌ Fix failing security tests before deployment")
    
    if summary.get("vulnerability_count", 0) == 0 and summary.get("failed", 0) == 0:
        report.append("- ✅ No critical security issues found")
        report.append("- 🔄 Continue regular security testing")
        report.append("- 📚 Keep security dependencies up to date")
    
    report.append("")
    
    # Compliance checklist
    report.append("## ✔️ Security Compliance Checklist")
    report.append("")
    
    checks = [
        ("Authentication Tests", summary.get("passed", 0) > 0),
        ("Authorization Tests", summary.get("passed", 0) > 0),
        ("No High Severity Vulnerabilities", 
         sum(1 for v in vulnerabilities if v.get("severity") == "HIGH") == 0),
        ("Static Analysis Passed", summary.get("vulnerability_count", 0) < 5),
        ("All Security Tests Passed", summary.get("failed", 0) == 0)
    ]
    
    for check_name, passed in checks:
        icon = "✅" if passed else "❌"
        report.append(f"- {icon} {check_name}")
    
    report.append("")
    
    return "\n".join(report)


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
        print(f"  ⚠️ HIGH SEVERITY ISSUES: {high_vulns}")
    
    # Return failure if security issues found
    return 0 if (summary.get("failed", 0) == 0 and high_vulns == 0) else 1


if __name__ == "__main__":
    exit(main())