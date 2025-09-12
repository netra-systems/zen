#!/usr/bin/env python3
"""Process test results and generate reports."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class TestResultProcessor:
    """Process test results and generate formatted reports."""
    
    def __init__(self, input_file: str):
        """Initialize with test results file."""
        self.input_file = Path(input_file)
        self.results = self._load_results()
        
    def _load_results(self) -> Dict[str, Any]:
        """Load test results from JSON file."""
        if not self.input_file.exists():
            return {"tests": [], "summary": {}}
            
        with open(self.input_file) as f:
            return json.load(f)
            
    def _extract_summary_data(self) -> Dict[str, Any]:
        """Extract summary statistics from test results."""
        summary = self.results.get("summary", {})
        return {
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "duration": summary.get("duration", 0)
        }
    
    def _calculate_pass_rate(self, passed: int, total: int) -> float:
        """Calculate test pass rate percentage."""
        return (passed / total * 100) if total > 0 else 0
    
    def _generate_status_badge(self, failed: int) -> str:
        """Generate status badge based on test results."""
        if failed == 0:
            return " PASS:  **All tests passed!**"
        return f" FAIL:  **{failed} test(s) failed**"
    
    def _generate_summary_section(self, stats: Dict[str, Any]) -> List[str]:
        """Generate summary section of the report."""
        pass_rate = self._calculate_pass_rate(stats["passed"], stats["total"])
        status = self._generate_status_badge(stats["failed"])
        
        lines = [
            f"{status}\n",
            f"**Pass Rate:** {pass_rate:.1f}% ({stats['passed']}/{stats['total']})",
            f"**Duration:** {stats['duration']:.2f}s"
        ]
        
        if stats["skipped"] > 0:
            lines.append(f"**Skipped:** {stats['skipped']}")
        
        return lines
    
    def _format_test_failure(self, test: Dict[str, Any]) -> List[str]:
        """Format individual test failure details."""
        lines = [
            f"\n#### `{test['name']}`",
            f"**File:** `{test.get('file', 'unknown')}`",
            f"**Error:** {test.get('error', 'No error message')}"
        ]
        
        if test.get("traceback"):
            lines.extend(self._format_traceback(test["traceback"]))
        
        return lines
    
    def _format_traceback(self, traceback: str) -> List[str]:
        """Format traceback section for test failure."""
        return [
            "<details>",
            "<summary>Stack Trace</summary>",
            "",
            "```python",
            traceback[:1000],  # Limit traceback length
            "```",
            "</details>"
        ]
    
    def _generate_failed_tests_section(self) -> List[str]:
        """Generate failed tests section of the report."""
        failed_tests = [t for t in self.results.get("tests", []) if t.get("status") == "failed"]
        if not failed_tests:
            return []
        
        lines = ["\n### Failed Tests"]
        for test in failed_tests[:10]:  # Show first 10 failures
            lines.extend(self._format_test_failure(test))
        
        if len(failed_tests) > 10:
            lines.append(f"\n*... and {len(failed_tests) - 10} more failures*")
        
        return lines
    
    def _generate_slow_tests_section(self) -> List[str]:
        """Generate slow tests section of the report."""
        slow_tests = sorted(
            [t for t in self.results.get("tests", []) if t.get("duration", 0) > 1],
            key=lambda x: x.get("duration", 0),
            reverse=True
        )[:5]
        
        if not slow_tests:
            return []
        
        lines = ["\n### Slowest Tests"]
        for test in slow_tests:
            lines.append(f"- `{test['name']}`: {test['duration']:.2f}s")
        
        return lines
    
    def _generate_coverage_section(self) -> List[str]:
        """Generate coverage information section."""
        if "coverage" not in self.results:
            return []
        
        coverage = self.results["coverage"]
        lines = [
            "\n### Coverage",
            f"**Overall:** {coverage.get('total', 0):.1f}%"
        ]
        
        if "files" in coverage:
            lines.extend(self._format_file_coverage(coverage["files"]))
        
        return lines
    
    def _format_file_coverage(self, files: Dict[str, float]) -> List[str]:
        """Format file coverage table."""
        lines = [
            "\n<details>",
            "<summary>File Coverage</summary>",
            "",
            "| File | Coverage |",
            "|------|----------|"
        ]
        
        for file, cov in sorted(files.items()):
            lines.append(f"| `{file}` | {cov:.1f}% |")
        
        lines.append("</details>")
        return lines
    
    def generate_markdown_report(self) -> str:
        """Generate a markdown formatted test report."""
        stats = self._extract_summary_data()
        report = []
        
        report.extend(self._generate_summary_section(stats))
        report.extend(self._generate_failed_tests_section())
        report.extend(self._generate_slow_tests_section())
        report.extend(self._generate_coverage_section())
        
        return "\n".join(report)
        
    def generate_json_summary(self) -> Dict[str, Any]:
        """Generate a JSON summary of test results."""
        summary = self.results.get("summary", {})
        
        return {
            "status": "success" if summary.get("failed", 0) == 0 else "failure",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "failed_tests": [
                {
                    "name": t["name"],
                    "file": t.get("file"),
                    "error": t.get("error"),
                    "duration": t.get("duration")
                }
                for t in self.results.get("tests", [])
                if t.get("status") == "failed"
            ],
            "coverage": self.results.get("coverage"),
            "metadata": {
                "run_id": self.results.get("run_id"),
                "test_level": self.results.get("test_level"),
                "runner": self.results.get("runner")
            }
        }
        
    def save_report(self, output_file: str, format: str = "markdown"):
        """Save the generated report to a file."""
        output_path = Path(output_file)
        
        if format == "markdown":
            content = self.generate_markdown_report()
        elif format == "json":
            content = json.dumps(self.generate_json_summary(), indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
        output_path.write_text(content)
        print(f"Report saved to {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process test results")
    parser.add_argument("--input", required=True, help="Input test results JSON file")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"],
                       help="Output format")
    parser.add_argument("--output", required=True, help="Output report file")
    
    args = parser.parse_args()
    
    processor = TestResultProcessor(args.input)
    processor.save_report(args.output, args.format)


if __name__ == "__main__":
    main()