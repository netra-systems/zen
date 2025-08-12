#!/usr/bin/env python3
"""Process test results and generate reports."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


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
            
    def generate_markdown_report(self) -> str:
        """Generate a markdown formatted test report."""
        report = []
        
        # Summary section
        summary = self.results.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        duration = summary.get("duration", 0)
        
        # Calculate pass rate
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # Status badge
        if failed == 0:
            status = "✅ **All tests passed!**"
        else:
            status = f"❌ **{failed} test(s) failed**"
            
        report.append(f"{status}\n")
        report.append(f"**Pass Rate:** {pass_rate:.1f}% ({passed}/{total})")
        report.append(f"**Duration:** {duration:.2f}s")
        
        if skipped > 0:
            report.append(f"**Skipped:** {skipped}")
            
        # Failed tests details
        if failed > 0:
            report.append("\n### Failed Tests")
            failed_tests = [t for t in self.results.get("tests", []) if t.get("status") == "failed"]
            
            for test in failed_tests[:10]:  # Show first 10 failures
                report.append(f"\n#### `{test['name']}`")
                report.append(f"**File:** `{test.get('file', 'unknown')}`")
                report.append(f"**Error:** {test.get('error', 'No error message')}")
                
                if test.get("traceback"):
                    report.append("<details>")
                    report.append("<summary>Stack Trace</summary>")
                    report.append("")
                    report.append("```python")
                    report.append(test["traceback"][:1000])  # Limit traceback length
                    report.append("```")
                    report.append("</details>")
                    
            if len(failed_tests) > 10:
                report.append(f"\n*... and {len(failed_tests) - 10} more failures*")
                
        # Slow tests
        slow_tests = sorted(
            [t for t in self.results.get("tests", []) if t.get("duration", 0) > 1],
            key=lambda x: x.get("duration", 0),
            reverse=True
        )[:5]
        
        if slow_tests:
            report.append("\n### Slowest Tests")
            for test in slow_tests:
                report.append(f"- `{test['name']}`: {test['duration']:.2f}s")
                
        # Coverage information if available
        if "coverage" in self.results:
            coverage = self.results["coverage"]
            report.append("\n### Coverage")
            report.append(f"**Overall:** {coverage.get('total', 0):.1f}%")
            
            if "files" in coverage:
                report.append("\n<details>")
                report.append("<summary>File Coverage</summary>")
                report.append("")
                report.append("| File | Coverage |")
                report.append("|------|----------|")
                
                for file, cov in sorted(coverage["files"].items()):
                    report.append(f"| `{file}` | {cov:.1f}% |")
                    
                report.append("</details>")
                
        return "\n".join(report)
        
    def generate_json_summary(self) -> Dict[str, Any]:
        """Generate a JSON summary of test results."""
        summary = self.results.get("summary", {})
        
        return {
            "status": "success" if summary.get("failed", 0) == 0 else "failure",
            "timestamp": datetime.utcnow().isoformat(),
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