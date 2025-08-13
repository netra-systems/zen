#!/usr/bin/env python3
"""Generate performance test report for GitHub Actions."""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def generate_performance_report(results: Dict[str, Any], format: str) -> str:
    """Generate a performance test report in the specified format."""
    
    if format == "markdown":
        return generate_markdown_performance_report(results)
    else:
        return json.dumps(results, indent=2)


def generate_markdown_performance_report(results: Dict[str, Any]) -> str:
    """Generate a markdown formatted performance test report."""
    report = []
    
    # Header
    report.append("# Performance Test Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary
    summary = results.get("summary", {})
    report.append("## Summary")
    report.append("")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Total Tests | {summary.get('total', 0)} |")
    report.append(f"| Passed | ✅ {summary.get('passed', 0)} |")
    report.append(f"| Failed | ❌ {summary.get('failed', 0)} |")
    report.append(f"| Success Rate | {summary.get('success_rate', 0):.1f}% |")
    report.append(f"| Total Duration | {summary.get('total_duration', 0):.2f}s |")
    report.append(f"| Average Duration | {summary.get('average_duration', 0):.2f}s |")
    report.append("")
    
    # Performance Issues
    if summary.get("performance_issues"):
        report.append("## ⚠️ Performance Issues")
        report.append("")
        report.append("| Test | Issue | Duration |")
        report.append("|------|-------|----------|")
        
        for issue in summary["performance_issues"]:
            report.append(
                f"| {issue['test']} | "
                f"{issue['issue']} | "
                f"{issue['duration']:.2f}s |"
            )
        report.append("")
    
    # Test Results
    if results.get("tests"):
        report.append("## Test Results")
        report.append("")
        report.append("| Test | Status | Duration | Performance |")
        report.append("|------|--------|----------|-------------|")
        
        for test in results["tests"]:
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "timeout": "⏱️",
                "error": "🔥"
            }.get(test["status"], "❓")
            
            # Performance indicator based on duration
            duration = test["duration"]
            if duration < 1:
                perf = "🟢 Excellent"
            elif duration < 5:
                perf = "🟡 Good"
            elif duration < 10:
                perf = "🟠 Acceptable"
            else:
                perf = "🔴 Slow"
            
            report.append(
                f"| {test['name']} | "
                f"{status_icon} {test['status']} | "
                f"{duration:.2f}s | "
                f"{perf} |"
            )
        report.append("")
    
    # Performance Metrics
    report.append("## Performance Metrics")
    report.append("")
    report.append("### Test Duration Distribution")
    report.append("")
    
    if results.get("tests"):
        durations = [t["duration"] for t in results["tests"]]
        durations.sort()
        
        report.append("| Percentile | Duration |")
        report.append("|------------|----------|")
        
        percentiles = [50, 75, 90, 95, 99]
        for p in percentiles:
            idx = min(int(len(durations) * p / 100), len(durations) - 1)
            report.append(f"| P{p} | {durations[idx]:.2f}s |")
        report.append("")
    
    # Recommendations
    report.append("## Recommendations")
    report.append("")
    
    if summary.get("performance_issues"):
        report.append("- 🔍 Investigate timeout issues in slow tests")
        report.append("- ⚡ Consider parallelizing long-running tests")
        report.append("- 📊 Profile tests with duration > 10s")
    else:
        report.append("- ✅ Performance is within acceptable limits")
    
    if summary.get("average_duration", 0) > 5:
        report.append("- ⏱️ Average test duration is high, consider optimization")
    
    report.append("")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Generate performance test report")
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
    report = generate_performance_report(results, args.format)
    
    # Save report
    with open(args.output, "w") as f:
        f.write(report)
    
    print(f"Performance report generated: {args.output}")
    
    # Print summary
    summary = results.get("summary", {})
    print(f"\nPerformance Test Summary:")
    print(f"  Total: {summary.get('total', 0)}")
    print(f"  Passed: {summary.get('passed', 0)}")
    print(f"  Failed: {summary.get('failed', 0)}")
    print(f"  Performance Issues: {len(summary.get('performance_issues', []))}")
    
    return 0 if summary.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    exit(main())