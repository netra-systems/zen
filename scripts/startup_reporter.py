#!/usr/bin/env python
"""
Startup Test Reporter
Handles report generation for startup tests
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List

from startup_test_executor import TestResult


class TestSummary:
    """Test execution summary"""
    
    def __init__(self, tests: List[TestResult]):
        self.tests = tests
        self.total = len(tests)
        self.passed = sum(1 for t in tests if t.passed)
        self.failed = self.total - self.passed
        self.duration = sum(t.duration for t in tests)
        self.success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "duration": self.duration,
            "success_rate": self.success_rate
        }


class ReportData:
    """Container for all report data"""
    
    def __init__(self, args, environment: Dict[str, Any], tests: List[TestResult]):
        self.start_time = datetime.now().isoformat()
        self.args = args
        self.environment = environment
        self.tests = [t.to_dict() if hasattr(t, 'to_dict') else t for t in tests]
        self.summary = TestSummary([t for t in tests if t]).to_dict()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "start_time": self.start_time,
            "tests": self.tests,
            "summary": self.summary,
            "environment": self.environment
        }


class JsonReportGenerator:
    """Generates JSON test reports"""
    
    def generate(self, report_data: ReportData) -> str:
        """Generate JSON report and return filename"""
        filename = self._create_filename("json")
        with open(filename, "w") as f:
            json.dump(report_data.to_dict(), f, indent=2, default=str)
        return filename
    
    def _create_filename(self, extension: str) -> str:
        """Create timestamped filename"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"reports/system-startup/test_report_{timestamp}.{extension}"


class MarkdownReportGenerator:
    """Generates Markdown test reports"""
    
    def __init__(self, args):
        self.args = args
    
    def generate(self, report_data: ReportData) -> str:
        """Generate Markdown report and return filename"""
        content = self._build_report_content(report_data)
        filename = self._create_filename("md")
        with open(filename, "w") as f:
            f.write("\n".join(content))
        return filename
    
    def _build_report_content(self, report_data: ReportData) -> List[str]:
        """Build complete report content"""
        content = []
        content.extend(self._build_header())
        content.extend(self._build_summary(report_data.summary))
        content.extend(self._build_test_results(report_data.tests))
        content.extend(self._build_environment(report_data.environment))
        content.extend(self._build_failed_details(report_data.tests))
        return content
    
    def _build_header(self) -> List[str]:
        """Build report header"""
        return [
            "# System Startup Test Report",
            f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Mode:** {self.args.mode}",
            f"**Platform:** {sys.platform}"
        ]
    
    def _build_summary(self, summary: Dict[str, Any]) -> List[str]:
        """Build summary section"""
        return [
            "\n## Summary",
            f"- **Total Tests:** {summary['total']}",
            f"- **Passed:** {summary['passed']} [OK]",
            f"- **Failed:** {summary['failed']} [FAIL]",
            f"- **Success Rate:** {summary['success_rate']:.1f}%",
            f"- **Duration:** {summary['duration']:.2f}s"
        ]
    
    def _build_test_results(self, tests: List[Dict[str, Any]]) -> List[str]:
        """Build test results table"""
        content = [
            "\n## Test Results",
            "\n| Test | Status | Duration |",
            "|------|--------|----------|"
        ]
        for test in tests:
            status = "[OK] Pass" if test["passed"] else "[FAIL] Fail"
            content.append(f"| {test['name']} | {status} | {test['duration']:.2f}s |")
        return content
    
    def _build_environment(self, env: Dict[str, Any]) -> List[str]:
        """Build environment section"""
        return [
            "\n## Environment",
            f"- **Python:** {env['python_version'].split()[0]}",
            f"- **Platform:** {env['platform']}",
            f"- **CPU Cores:** {env['cpu_count']}",
            f"- **Memory:** {env['memory_total']:.1f} GB"
        ]
    
    def _build_failed_details(self, tests: List[Dict[str, Any]]) -> List[str]:
        """Build failed test details section"""
        failed = [t for t in tests if not t["passed"]]
        if not failed:
            return []
        content = ["\n## Failed Test Details"]
        for test in failed:
            content.append(f"\n### {test['name']}")
            if test.get("errors"):
                content.extend(["```", test["errors"][:1000], "```"])
        return content
    
    def _create_filename(self, extension: str) -> str:
        """Create timestamped filename"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"reports/system-startup/test_report_{timestamp}.{extension}"


class StartupReporter:
    """Main reporter class for startup tests"""
    
    def __init__(self, args, environment: Dict[str, Any]):
        self.args = args
        self.environment = environment
        self.json_generator = JsonReportGenerator()
        self.markdown_generator = MarkdownReportGenerator(args)
    
    def generate_reports(self, tests: List[TestResult]) -> bool:
        """Generate all reports and return success status"""
        valid_tests = [t for t in tests if t is not None]
        report_data = ReportData(self.args, self.environment, valid_tests)
        self._print_summary(report_data.summary)
        self._print_individual_results(valid_tests)
        self._save_reports(report_data)
        return report_data.summary["failed"] == 0
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        print(f"\nTests Run: {summary['total']}")
        print(f"Passed: {summary['passed']} [OK]")
        print(f"Failed: {summary['failed']} [FAIL]")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Total Duration: {summary['duration']:.2f}s")
    
    def _print_individual_results(self, tests: List[TestResult]):
        """Print individual test results"""
        print("\nTest Results:")
        for test in tests:
            status = "[OK]" if test.passed else "[FAIL]"
            print(f"  {status} {test.name:30} ({test.duration:.2f}s)")
    
    def _save_reports(self, report_data: ReportData):
        """Save JSON and Markdown reports"""
        json_file = self.json_generator.generate(report_data)
        markdown_file = self.markdown_generator.generate(report_data)
        print(f"\nDetailed report saved to: {json_file}")
        print(f"Markdown report saved to: {markdown_file}")