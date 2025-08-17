#!/usr/bin/env python
"""
Enhanced Test Reporter - Clear, accurate test reporting with proper error handling.
Handles import errors, zero counts, and provides actionable insights.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TestStatus:
    """Represents the status of a test run component."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    import_errors: int = 0
    duration: float = 0.0
    status: str = "unknown"
    exit_code: int = 0
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100
    
    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return (self.failed > 0 or self.errors > 0 or 
                self.import_errors > 0 or self.status == "import_error")
    
    @property
    def status_icon(self) -> str:
        """Get icon representing status."""
        if self.status == "import_error":
            return "🔴"
        elif self.status == "timeout":
            return "⏱️"
        elif self.has_issues:
            return "❌"
        elif self.passed > 0:
            return "✅"
        elif self.skipped > 0:
            return "⏭️"
        else:
            return "⚫"
    
    @property
    def summary_text(self) -> str:
        """Get summary text for status."""
        if self.status == "import_error":
            return f"Import errors ({self.import_errors})"
        elif self.status == "timeout":
            return "Timed out"
        elif self.status == "no_tests":
            return "No tests found"
        elif self.total == 0:
            return "No tests ran"
        else:
            parts = []
            if self.passed > 0:
                parts.append(f"{self.passed} passed")
            if self.failed > 0:
                parts.append(f"{self.failed} failed")
            if self.errors > 0:
                parts.append(f"{self.errors} errors")
            if self.skipped > 0:
                parts.append(f"{self.skipped} skipped")
            return ", ".join(parts) if parts else "No results"


class EnhancedReporter:
    """Enhanced test reporting with clear status and error handling."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.latest_dir = reports_dir / "latest"
        self.latest_dir.mkdir(exist_ok=True)
        self.history_dir = reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        
    def generate_report(self, results: Dict, level: str) -> str:
        """Generate enhanced test report."""
        # Parse results into TestStatus objects
        statuses = self._parse_results(results)
        
        # Generate different report formats
        self._save_json_report(statuses, level)
        dashboard = self._generate_dashboard(statuses, level)
        summary = self._generate_summary(statuses, level)
        
        # Save reports
        self._save_markdown_reports(dashboard, summary)
        
        return summary
    
    def _parse_results(self, results: Dict) -> Dict[str, TestStatus]:
        """Parse raw results into TestStatus objects."""
        statuses = {}
        
        for component in ["backend", "frontend", "e2e"]:
            if component not in results:
                statuses[component] = TestStatus(status="not_run")
                continue
                
            result = results[component]
            status = TestStatus()
            
            # Extract counts if available
            if "test_counts" in result:
                counts = result["test_counts"]
                status.total = counts.get("total", 0)
                status.passed = counts.get("passed", 0)
                status.failed = counts.get("failed", 0)
                status.skipped = counts.get("skipped", 0)
                status.errors = counts.get("errors", 0)
                status.import_errors = counts.get("import_errors", 0)
                if "status" in counts:
                    status.status = counts["status"]
            
            # Get other metadata
            status.duration = result.get("duration", 0.0)
            status.exit_code = result.get("exit_code", 0)
            
            # Determine status if not set
            if status.status == "unknown":
                status.status = self._determine_status(result, status)
            
            statuses[component] = status
        
        return statuses
    
    def _determine_status(self, result: Dict, status: TestStatus) -> str:
        """Determine test status from result data."""
        output = result.get("output", "")
        
        # Check for import errors
        if "ImportError" in output or "ModuleNotFoundError" in output:
            return "import_error"
        
        # Check for timeout
        if result.get("status") == "timeout":
            return "timeout"
        
        # Check exit code
        if status.exit_code != 0:
            if status.total == 0:
                return "collection_failed"
            return "failed"
        
        # Check test counts
        if status.total == 0:
            if "collected 0 items" in output.lower():
                return "no_tests"
            return "unknown"
        
        if status.failed > 0 or status.errors > 0:
            return "failed"
        elif status.passed > 0:
            return "passed"
        elif status.skipped > 0:
            return "skipped"
        
        return "unknown"
    
    def _generate_dashboard(self, statuses: Dict[str, TestStatus], level: str) -> str:
        """Generate dashboard view."""
        lines = []
        lines.append("# Test Dashboard\n")
        lines.append(f"**Level**: {level} | ")
        lines.append(f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overall status
        overall_status = self._get_overall_status(statuses)
        lines.append(f"## Overall Status: {overall_status}\n\n")
        
        # Component summary table
        lines.append("## Component Summary\n\n")
        lines.append("| Component | Status | Tests | Passed | Failed | Errors | Import Errors | Duration |\n")
        lines.append("|-----------|--------|-------|--------|--------|--------|---------------|----------|\n")
        
        for component, status in statuses.items():
            lines.append(f"| {component.title()} | {status.status_icon} {status.status} | ")
            lines.append(f"{status.total} | {status.passed} | {status.failed} | ")
            lines.append(f"{status.errors} | {status.import_errors} | {status.duration:.2f}s |\n")
        
        # Issues section
        issues = self._collect_issues(statuses)
        if issues:
            lines.append("\n## 🔴 Issues Detected\n\n")
            for issue in issues:
                lines.append(f"- {issue}\n")
        
        # Statistics
        lines.append("\n## Statistics\n\n")
        total_tests = sum(s.total for s in statuses.values())
        total_passed = sum(s.passed for s in statuses.values())
        total_failed = sum(s.failed for s in statuses.values())
        total_errors = sum(s.errors for s in statuses.values())
        total_skipped = sum(s.skipped for s in statuses.values())
        total_duration = sum(s.duration for s in statuses.values())
        
        lines.append(f"- **Total Tests**: {total_tests}\n")
        lines.append(f"- **Passed**: {total_passed}\n")
        lines.append(f"- **Failed**: {total_failed}\n")
        lines.append(f"- **Errors**: {total_errors}\n")
        lines.append(f"- **Skipped**: {total_skipped}\n")
        lines.append(f"- **Total Duration**: {total_duration:.2f}s\n")
        
        if total_tests > 0:
            overall_pass_rate = (total_passed / total_tests) * 100
            lines.append(f"- **Pass Rate**: {overall_pass_rate:.1f}%\n")
        
        # Quick actions
        lines.append("\n## Quick Actions\n\n")
        lines.append("```bash\n")
        if any(s.import_errors > 0 for s in statuses.values()):
            lines.append("# Fix import errors first\n")
            lines.append("python -m pip install -r requirements.txt\n")
            lines.append("python scripts/check_imports.py\n\n")
        
        lines.append("# Run specific test levels\n")
        lines.append("python test_runner.py --level unit\n")
        lines.append("python test_runner.py --level smoke\n")
        lines.append("python test_runner.py --level comprehensive\n")
        lines.append("```\n")
        
        return "".join(lines)
    
    def _generate_summary(self, statuses: Dict[str, TestStatus], level: str) -> str:
        """Generate concise summary."""
        lines = []
        lines.append("# Test Summary\n")
        lines.append(f"**Level**: {level} | ")
        lines.append(f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Quick status line
        overall = self._get_overall_status(statuses)
        lines.append(f"**Status**: {overall}\n\n")
        
        # Component results
        for component, status in statuses.items():
            lines.append(f"**{component.title()}**: {status.status_icon} {status.summary_text}\n")
        
        # Key issues
        issues = self._collect_issues(statuses)
        if issues:
            lines.append("\n## Issues\n")
            for issue in issues[:5]:  # Show top 5 issues
                lines.append(f"- {issue}\n")
            if len(issues) > 5:
                lines.append(f"- ...and {len(issues) - 5} more issues\n")
        
        return "".join(lines)
    
    def _get_overall_status(self, statuses: Dict[str, TestStatus]) -> str:
        """Determine overall test status."""
        if any(s.status == "import_error" for s in statuses.values()):
            return "🔴 Import Errors - Tests Cannot Run"
        elif any(s.status == "timeout" for s in statuses.values()):
            return "⏱️ Timeout - Tests Did Not Complete"
        elif any(s.failed > 0 or s.errors > 0 for s in statuses.values()):
            total_failures = sum(s.failed + s.errors for s in statuses.values())
            return f"❌ Failed - {total_failures} test(s) failed"
        elif all(s.status == "no_tests" or s.status == "not_run" for s in statuses.values()):
            return "⚫ No Tests Found or Run"
        elif any(s.passed > 0 for s in statuses.values()):
            return "✅ Passed - All tests passing"
        else:
            return "⚠️ Unknown - Check test output"
    
    def _collect_issues(self, statuses: Dict[str, TestStatus]) -> List[str]:
        """Collect all issues from test results."""
        issues = []
        
        for component, status in statuses.items():
            if status.import_errors > 0:
                issues.append(f"{component}: {status.import_errors} import error(s)")
            if status.status == "timeout":
                issues.append(f"{component}: Tests timed out after {status.duration:.1f}s")
            if status.failed > 0:
                issues.append(f"{component}: {status.failed} test(s) failed")
            if status.errors > 0:
                issues.append(f"{component}: {status.errors} test error(s)")
            if status.status == "collection_failed":
                issues.append(f"{component}: Test collection failed")
            if status.status == "no_tests":
                issues.append(f"{component}: No tests found to run")
        
        return issues
    
    def _save_json_report(self, statuses: Dict[str, TestStatus], level: str):
        """Save JSON format report."""
        # Convert TestStatus objects to dict using asdict
        components = {}
        for k, v in statuses.items():
            status_dict = asdict(v)
            # Add computed properties
            status_dict["pass_rate"] = v.pass_rate
            status_dict["has_issues"] = v.has_issues
            status_dict["status_icon"] = v.status_icon
            status_dict["summary_text"] = v.summary_text
            components[k] = status_dict
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "components": components,
            "overall_status": self._get_overall_status(statuses),
            "issues": self._collect_issues(statuses)
        }
        
        json_file = self.latest_dir / "test_report.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    
    def _save_markdown_reports(self, dashboard: str, summary: str):
        """Save markdown reports."""
        # Save dashboard
        dashboard_file = self.reports_dir / "dashboard.md"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(dashboard)
        
        # Save summary
        summary_file = self.reports_dir / "summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        # Also save to latest directory
        latest_dashboard = self.latest_dir / "dashboard.md"
        with open(latest_dashboard, 'w', encoding='utf-8') as f:
            f.write(dashboard)
        
        latest_summary = self.latest_dir / "summary.md"
        with open(latest_summary, 'w', encoding='utf-8') as f:
            f.write(summary)
    
    def generate_comprehensive_report(self, level: str, results: Dict, 
                                     config: Dict, exit_code: int) -> str:
        """Generate comprehensive report (alias for generate_report)."""
        return self.generate_report(results, level)
    
    def save_report(self, level: str, report_content: str, 
                   results: Dict, metrics: Dict):
        """Save report content to files."""
        # Already saved by generate_report, this is for compatibility
        pass
    
    def cleanup_old_reports(self, keep_days: int = 7):
        """Clean up old reports in history directory."""
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        
        for report_file in self.history_dir.glob("*.md"):
            if datetime.fromtimestamp(report_file.stat().st_mtime) < cutoff_time:
                report_file.unlink()
                print(f"[CLEANUP] Removed old report: {report_file.name}")