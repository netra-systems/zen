"""Test Report Analyzer - Analyzes test reports and identifies issues."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TestReportAnalyzer:
    """Analyzes test reports for team updates."""
    
    def __init__(self, project_root: Path):
        """Initialize with project root."""
        self.project_root = project_root
        self.test_reports_dir = project_root / "test_reports"
        self.metrics_file = self.test_reports_dir / "metrics" / "test_history.json"
    
    async def analyze(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Analyze test reports in time range."""
        latest_reports = await self.load_latest_reports()
        failures = self.extract_failures(latest_reports)
        coverage_delta = self.calculate_coverage_delta()
        
        return {
            "test_status": self._determine_overall_status(latest_reports),
            "test_failures": failures,
            "coverage_info": coverage_delta,
            "test_metrics": self._extract_metrics(latest_reports)
        }
    
    async def load_latest_reports(self) -> Dict[str, Any]:
        """Load test reports from test_reports/."""
        reports = {}
        report_files = [
            "unified_report.md",
            "latest/unit_report.md",
            "dashboard.md"
        ]
        
        for file_name in report_files:
            file_path = self.test_reports_dir / file_name
            if file_path.exists():
                content = file_path.read_text()
                reports[file_name] = self._parse_report_content(content)
        
        return reports
    
    def extract_failures(self, reports: Dict) -> List[Dict]:
        """Identify test failures and flaky tests."""
        failures = []
        for report_name, data in reports.items():
            if not data: continue
            
            for failure in data.get("failures", []):
                failures.append({
                    "test": failure.get("name", "Unknown"),
                    "reason": self._simplify_error(failure.get("error", "")),
                    "file": failure.get("file", ""),
                    "type": "failure"
                })
        
        return failures[:10]  # Limit to top 10
    
    def calculate_coverage_delta(self) -> Dict[str, Any]:
        """Show coverage changes."""
        if not self.metrics_file.exists():
            return {"current": 0, "previous": 0, "delta": 0}
        
        try:
            history = json.loads(self.metrics_file.read_text())
            recent = history.get("recent_runs", [])
            if len(recent) >= 2:
                current = recent[-1].get("coverage", 0)
                previous = recent[-2].get("coverage", 0)
                return {
                    "current": current,
                    "previous": previous,
                    "delta": round(current - previous, 2)
                }
        except Exception:
            pass
        
        return {"current": 0, "previous": 0, "delta": 0}
    
    def _determine_overall_status(self, reports: Dict) -> str:
        """Determine overall test health status."""
        total_failures = sum(
            len(r.get("failures", [])) for r in reports.values() if r
        )
        
        if total_failures == 0:
            return "healthy"
        elif total_failures <= 3:
            return "minor_issues"
        elif total_failures <= 10:
            return "degraded"
        else:
            return "critical"
    
    def _parse_report_content(self, content: str) -> Dict[str, Any]:
        """Parse markdown report content."""
        data = {"failures": [], "passed": 0, "total": 0}
        
        # Extract test counts
        count_pattern = r'(\d+)\s+passed.*?(\d+)\s+total'
        match = re.search(count_pattern, content)
        if match:
            data["passed"] = int(match.group(1))
            data["total"] = int(match.group(2))
        
        # Extract failures
        failure_pattern = r'FAILED\s+([\w/\.]+::\w+)'
        for match in re.finditer(failure_pattern, content):
            data["failures"].append({"name": match.group(1)})
        
        return data
    
    def _simplify_error(self, error: str) -> str:
        """Simplify error message for readability."""
        if not error:
            return "Test assertion failed"
        
        # Remove stack traces
        lines = error.split('\n')
        for line in lines:
            if 'assert' in line.lower() or 'error' in line.lower():
                return line[:100]
        
        return error[:100] if error else "Test failed"
    
    def _extract_metrics(self, reports: Dict) -> Dict[str, Any]:
        """Extract key test metrics."""
        total_tests = sum(r.get("total", 0) for r in reports.values() if r)
        passed_tests = sum(r.get("passed", 0) for r in reports.values() if r)
        
        pass_rate = 0
        if total_tests > 0:
            pass_rate = round((passed_tests / total_tests) * 100, 1)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": pass_rate,
            "flaky_tests": self._identify_flaky_tests()
        }
    
    def _identify_flaky_tests(self) -> List[str]:
        """Identify tests that fail intermittently."""
        # Check bad_tests.json if it exists
        bad_tests_file = self.test_reports_dir / "bad_tests.json"
        if bad_tests_file.exists():
            try:
                data = json.loads(bad_tests_file.read_text())
                return data.get("flaky_tests", [])[:5]
            except Exception:
                pass
        return []