#!/usr/bin/env python3
"""Generate performance test report for GitHub Actions."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def generate_performance_report(results: Dict[str, Any], format: str) -> str:
    """Generate a performance test report in the specified format."""
    
    if format == "markdown":
        return generate_markdown_performance_report(results)
    else:
        return json.dumps(results, indent=2)


def add_report_header(report: list) -> None:
    """Add header section to performance report."""
    report.append("# Performance Test Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")


def add_summary_section(report: list, summary: Dict[str, Any]) -> None:
    """Add summary section to performance report."""
    report.append("## Summary")
    report.append("")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Total Tests | {summary.get('total', 0)} |")
    report.append(f"| Passed |  PASS:  {summary.get('passed', 0)} |")
    report.append(f"| Failed |  FAIL:  {summary.get('failed', 0)} |")
    report.append(f"| Success Rate | {summary.get('success_rate', 0):.1f}% |")


def add_summary_timing(report: list, summary: Dict[str, Any]) -> None:
    """Add timing information to summary section."""
    report.append(f"| Total Duration | {summary.get('total_duration', 0):.2f}s |")
    report.append(f"| Average Duration | {summary.get('average_duration', 0):.2f}s |")
    report.append("")


def add_performance_issues(report: list, summary: Dict[str, Any]) -> None:
    """Add performance issues section if any exist."""
    if not summary.get("performance_issues"):
        return
    report.append("##  WARNING: [U+FE0F] Performance Issues")
    report.append("")
    report.append("| Test | Issue | Duration |")
    report.append("|------|-------|----------|")
    for issue in summary["performance_issues"]:
        report.append(f"| {issue['test']} | {issue['issue']} | {issue['duration']:.2f}s |")
    report.append("")


def get_status_icon(status: str) -> str:
    """Get status icon for test result."""
    icons = {
        "passed": " PASS: ", "failed": " FAIL: ",
        "timeout": "[U+23F1][U+FE0F]", "error": " FIRE: "
    }
    return icons.get(status, "[U+2753]")


def get_performance_indicator(duration: float) -> str:
    """Get performance indicator based on test duration."""
    if duration < 1:
        return "[U+1F7E2] Excellent"
    elif duration < 5:
        return "[U+1F7E1] Good"
    elif duration < 10:
        return "[U+1F7E0] Acceptable"
    return "[U+1F534] Slow"


def add_test_results(report: list, tests: list) -> None:
    """Add test results section to performance report."""
    if not tests:
        return
    report.append("## Test Results")
    report.append("")
    report.append("| Test | Status | Duration | Performance |")
    report.append("|------|--------|----------|-------------|")
    for test in tests:
        status_icon = get_status_icon(test["status"])
        perf = get_performance_indicator(test["duration"])
        report.append(f"| {test['name']} | {status_icon} {test['status']} | {test['duration']:.2f}s | {perf} |")
    report.append("")


def add_duration_metrics(report: list, tests: list) -> None:
    """Add duration distribution metrics."""
    report.append("## Performance Metrics")
    report.append("")
    report.append("### Test Duration Distribution")
    report.append("")
    if not tests:
        return
    durations = sorted([t["duration"] for t in tests])
    report.append("| Percentile | Duration |")
    report.append("|------------|----------|")


def add_percentile_data(report: list, durations: list) -> None:
    """Add percentile data to duration metrics."""
    percentiles = [50, 75, 90, 95, 99]
    for p in percentiles:
        idx = min(int(len(durations) * p / 100), len(durations) - 1)
        report.append(f"| P{p} | {durations[idx]:.2f}s |")
    report.append("")


def add_recommendations(report: list, summary: Dict[str, Any]) -> None:
    """Add recommendations section based on test results."""
    report.append("## Recommendations")
    report.append("")
    if summary.get("performance_issues"):
        report.append("-  SEARCH:  Investigate timeout issues in slow tests")
        report.append("-  LIGHTNING:  Consider parallelizing long-running tests")
        report.append("-  CHART:  Profile tests with duration > 10s")
    else:
        report.append("-  PASS:  Performance is within acceptable limits")
    if summary.get("average_duration", 0) > 5:
        report.append("- [U+23F1][U+FE0F] Average test duration is high, consider optimization")
    report.append("")


def generate_markdown_performance_report(results: Dict[str, Any]) -> str:
    """Generate a markdown formatted performance test report."""
    report = []
    summary = results.get("summary", {})
    tests = results.get("tests", [])
    
    add_report_header(report)
    add_summary_section(report, summary)
    add_summary_timing(report, summary)
    add_performance_issues(report, summary)
    add_test_results(report, tests)
    add_duration_metrics(report, tests)
    if tests:
        durations = sorted([t["duration"] for t in tests])
        add_percentile_data(report, durations)
    add_recommendations(report, summary)
    
    return "\n".join(report)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate performance test report")
    parser.add_argument("--input", required=True, help="Input JSON results file")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", required=True, help="Output file path")
    return parser.parse_args()


def load_results(input_file: str) -> Dict[str, Any]:
    """Load test results from JSON file."""
    try:
        with open(input_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading results file: {e}")
        raise


def save_report(report: str, output_file: str) -> None:
    """Save generated report to file."""
    with open(output_file, "w") as f:
        f.write(report)
    print(f"Performance report generated: {output_file}")


def print_summary(summary: Dict[str, Any]) -> None:
    """Print performance test summary to console."""
    print(f"\nPerformance Test Summary:")
    print(f"  Total: {summary.get('total', 0)}")
    print(f"  Passed: {summary.get('passed', 0)}")
    print(f"  Failed: {summary.get('failed', 0)}")
    print(f"  Performance Issues: {len(summary.get('performance_issues', []))}")


def main():
    """Main function for performance report generation."""
    args = parse_arguments()
    
    try:
        results = load_results(args.input)
        report = generate_performance_report(results, args.format)
        save_report(report, args.output)
        
        summary = results.get("summary", {})
        print_summary(summary)
        
        return 0 if summary.get("failed", 0) == 0 else 1
    except Exception:
        return 1


if __name__ == "__main__":
    exit(main())