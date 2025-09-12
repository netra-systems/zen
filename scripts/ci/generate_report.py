#!/usr/bin/env python3
"""Generate test report in various formats for GitHub Actions."""

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _format_header() -> list[str]:
    """Format report header section."""
    report = []
    report.append("# Test Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    return report


def _format_summary_table(results: Dict[str, Any], coverage_data: Optional[Dict[str, Any]]) -> list[str]:
    """Format summary metrics table."""
    report = []
    report.append("## Summary")
    report.append("")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.extend(_get_summary_rows(results, coverage_data))
    report.append("")
    return report


def _get_summary_rows(results: Dict[str, Any], coverage_data: Optional[Dict[str, Any]]) -> list[str]:
    """Generate summary table rows."""
    rows = _get_base_summary_rows(results)
    if coverage_data:
        rows.append(f"| Coverage | {coverage_data.get('coverage_percent', 0):.1f}% |")
    return rows


def _get_base_summary_rows(results: Dict[str, Any]) -> list[str]:
    """Generate base summary table rows."""
    test_rows = _get_test_count_rows(results)
    metric_rows = _get_metric_rows(results)
    return test_rows + metric_rows


def _get_test_count_rows(results: Dict[str, Any]) -> list[str]:
    """Generate test count summary rows."""
    return [
        f"| Total Tests | {results.get('total_tests', 0)} |",
        f"| Passed |  PASS:  {results.get('passed', 0)} |",
        f"| Failed |  FAIL:  {results.get('failed', 0)} |",
        f"| Skipped | [U+23ED][U+FE0F] {results.get('skipped', 0)} |",
        f"| Errors |  FIRE:  {results.get('errors', 0)} |"
    ]


def _get_metric_rows(results: Dict[str, Any]) -> list[str]:
    """Generate metric summary rows."""
    return [
        f"| Success Rate | {results.get('success_rate', 0):.1f}% |",
        f"| Duration | {results.get('duration', 0):.2f}s |"
    ]


def _format_shard_results(results: Dict[str, Any]) -> list[str]:
    """Format shard results section."""
    if not ("shards" in results and results["shards"]):
        return []
    report = ["## Shard Results", "", "| Shard | Tests | Passed | Failed | Duration |", "|-------|-------|--------|--------|----------|"]  
    for shard in results["shards"]:
        report.append(_format_shard_row(shard))
    report.append("")
    return report


def _format_shard_row(shard: Dict[str, Any]) -> str:
    """Format single shard table row."""
    shard_name = shard.get("shard", "unknown")
    return (
        f"| {shard_name} | "
        f"{shard.get('total_tests', 0)} | "
        f"{shard.get('passed', 0)} | "
        f"{shard.get('failed', 0)} | "
        f"{shard.get('duration', 0):.2f}s |"
    )


def _format_failures(results: Dict[str, Any]) -> list[str]:
    """Format failed tests section."""
    if not results.get("failures"):
        return []
    report = ["## Failed Tests", ""]
    for failure in results["failures"][:10]:  # Show first 10 failures
        report.extend(_format_single_failure(failure))
    if len(results["failures"]) > 10:
        report.extend([f"*... and {len(results['failures']) - 10} more failures*", ""])
    return report


def _format_single_failure(failure: Dict[str, Any]) -> list[str]:
    """Format single failure entry."""
    lines = [f"###  FAIL:  {failure.get('test_name', 'Unknown Test')}"]
    if "shard" in failure:
        lines.append(f"**Shard:** {failure['shard']}")
    if "error_message" in failure:
        lines.extend([""", failure["error_message"][:500], """])
    lines.append("")
    return lines


def _format_errors(results: Dict[str, Any]) -> list[str]:
    """Format test errors section."""
    if not results.get("errors_list"):
        return []
    report = ["## Test Errors", ""]
    for error in results["errors_list"][:5]:  # Show first 5 errors
        report.extend(_format_single_error(error))
    if len(results["errors_list"]) > 5:
        report.extend([f"*... and {len(results['errors_list']) - 5} more errors*", ""])
    return report


def _format_single_error(error: Dict[str, Any]) -> list[str]:
    """Format single error entry."""
    lines = [f"###  FIRE:  {error.get('test_name', 'Unknown Test')}"]
    if "shard" in error:
        lines.append(f"**Shard:** {error['shard']}")
    if "error_message" in error:
        lines.extend([""", error["error_message"][:500], """])
    lines.append("")
    return lines


def generate_markdown_report(results: Dict[str, Any], coverage_data: Optional[Dict[str, Any]] = None) -> str:
    """Generate a markdown formatted test report."""
    report_sections = _collect_report_sections(results, coverage_data)
    all_lines = [line for section in report_sections for line in section]
    return "\n".join(all_lines)


def _collect_report_sections(results: Dict[str, Any], coverage_data: Optional[Dict[str, Any]]) -> list[list[str]]:
    """Collect all report sections."""
    return [
        _format_header(),
        _format_summary_table(results, coverage_data),
        _format_shard_results(results),
        _format_failures(results),
        _format_errors(results)
    ]


def parse_coverage_xml(coverage_file: Path) -> Dict[str, Any]:
    """Parse coverage XML file to extract coverage percentage."""
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Extract coverage percentage from XML
        coverage_percent = float(root.attrib.get("line-rate", 0)) * 100
        
        return {
            "coverage_percent": coverage_percent,
            "lines_covered": root.attrib.get("lines-covered", 0),
            "lines_valid": root.attrib.get("lines-valid", 0)
        }
    except Exception as e:
        print(f"Warning: Could not parse coverage file: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Generate test report from results")
    parser.add_argument("--input", required=True, help="Input JSON results file")
    parser.add_argument("--coverage", help="Coverage XML file")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--output", required=True, help="Output file path")
    
    args = parser.parse_args()
    
    # Load test results
    try:
        with open(args.input, "r") as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error loading results file: {e}")
        return 1
    
    # Load coverage data if available
    coverage_data = None
    if args.coverage and Path(args.coverage).exists():
        coverage_data = parse_coverage_xml(Path(args.coverage))
    
    # Generate report
    if args.format == "markdown":
        report = generate_markdown_report(results, coverage_data)
    else:
        # For JSON, just combine results and coverage
        if coverage_data:
            results["coverage"] = coverage_data
        report = json.dumps(results, indent=2)
    
    # Save report
    with open(args.output, "w") as f:
        f.write(report)
    
    print(f"Report generated: {args.output}")
    
    # Print summary to console
    print(f"\nTest Results Summary:")
    print(f"  Total: {results.get('total_tests', 0)}")
    print(f"  Passed: {results.get('passed', 0)}")
    print(f"  Failed: {results.get('failed', 0)}")
    print(f"  Success Rate: {results.get('success_rate', 0):.1f}%")
    
    if coverage_data:
        print(f"  Coverage: {coverage_data.get('coverage_percent', 0):.1f}%")
    
    # Exit with failure if tests failed
    return 0 if results.get('failed', 0) == 0 else 1


if __name__ == "__main__":
    exit(main())