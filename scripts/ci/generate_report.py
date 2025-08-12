#!/usr/bin/env python3
"""Generate test report in various formats for GitHub Actions."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


def generate_markdown_report(results: Dict[str, Any], coverage_data: Optional[Dict[str, Any]] = None) -> str:
    """Generate a markdown formatted test report."""
    report = []
    
    # Header
    report.append("# Test Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary
    report.append("## Summary")
    report.append("")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Total Tests | {results.get('total_tests', 0)} |")
    report.append(f"| Passed | ✅ {results.get('passed', 0)} |")
    report.append(f"| Failed | ❌ {results.get('failed', 0)} |")
    report.append(f"| Skipped | ⏭️ {results.get('skipped', 0)} |")
    report.append(f"| Errors | 🔥 {results.get('errors', 0)} |")
    report.append(f"| Success Rate | {results.get('success_rate', 0):.1f}% |")
    report.append(f"| Duration | {results.get('duration', 0):.2f}s |")
    
    if coverage_data:
        report.append(f"| Coverage | {coverage_data.get('coverage_percent', 0):.1f}% |")
    
    report.append("")
    
    # Shard results if available
    if "shards" in results and results["shards"]:
        report.append("## Shard Results")
        report.append("")
        report.append("| Shard | Tests | Passed | Failed | Duration |")
        report.append("|-------|-------|--------|--------|----------|")
        
        for shard in results["shards"]:
            shard_name = shard.get("shard", "unknown")
            report.append(
                f"| {shard_name} | "
                f"{shard.get('total_tests', 0)} | "
                f"{shard.get('passed', 0)} | "
                f"{shard.get('failed', 0)} | "
                f"{shard.get('duration', 0):.2f}s |"
            )
        report.append("")
    
    # Failures
    if results.get("failures"):
        report.append("## Failed Tests")
        report.append("")
        
        for failure in results["failures"][:10]:  # Show first 10 failures
            report.append(f"### ❌ {failure.get('test_name', 'Unknown Test')}")
            if "shard" in failure:
                report.append(f"**Shard:** {failure['shard']}")
            if "error_message" in failure:
                report.append("```")
                report.append(failure["error_message"][:500])  # Truncate long messages
                report.append("```")
            report.append("")
        
        if len(results["failures"]) > 10:
            report.append(f"*... and {len(results['failures']) - 10} more failures*")
            report.append("")
    
    # Errors
    if results.get("errors_list"):
        report.append("## Test Errors")
        report.append("")
        
        for error in results["errors_list"][:5]:  # Show first 5 errors
            report.append(f"### 🔥 {error.get('test_name', 'Unknown Test')}")
            if "shard" in error:
                report.append(f"**Shard:** {error['shard']}")
            if "error_message" in error:
                report.append("```")
                report.append(error["error_message"][:500])  # Truncate long messages
                report.append("```")
            report.append("")
        
        if len(results["errors_list"]) > 5:
            report.append(f"*... and {len(results['errors_list']) - 5} more errors*")
            report.append("")
    
    return "\n".join(report)


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