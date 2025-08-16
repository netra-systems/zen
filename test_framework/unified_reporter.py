#!/usr/bin/env python
"""
Unified Reporter - Provides consolidated view of test results.
Shows last 3 runs, trends, and critical information at a glance.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from .delta_reporter import DeltaReporter, TestDelta


class UnifiedReporter:
    """Manages unified test reporting with focus on actionable insights."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.delta_reporter = DeltaReporter(reports_dir)
        self.unified_file = reports_dir / "unified_report.md"
        self.dashboard_file = reports_dir / "dashboard.md"
        
    def generate_unified_report(self, current_results: Dict, 
                               level: str, exit_code: int):
        """Generate comprehensive unified report."""
        deltas = self._process_deltas(current_results, level)
        report = self._create_unified_view(current_results, deltas, level)
        self._save_reports(report)
        
        return report
    
    def _process_deltas(self, current_results: Dict, level: str) -> List[TestDelta]:
        """Process deltas and update history."""
        deltas = self.delta_reporter.detect_deltas(current_results)
        self.delta_reporter.update_history(current_results, level)
        self.delta_reporter.save_reports(deltas, current_results)
        
        return deltas
    
    def _save_reports(self, report: str):
        """Save unified report and dashboard."""
        with open(self.unified_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        dashboard = self._create_dashboard()
        with open(self.dashboard_file, 'w', encoding='utf-8') as f:
            f.write(dashboard)
    
    def _create_unified_view(self, results: Dict, deltas: List[TestDelta], 
                            level: str) -> str:
        """Create unified view combining current results and deltas."""
        report = []
        
        self._add_header(report, level)
        self._add_status_section(report, results)
        self._add_critical_changes(report, deltas)
        self._add_summary_and_failures(report, results)
        self._add_flaky_tests_and_links(report)
        
        return "".join(report)
    
    def _add_header(self, report: List[str], level: str):
        """Add report header."""
        report.append("# Unified Test Report\n")
        report.append(f"**Level**: {level} | ")
        report.append(f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def _add_status_section(self, report: List[str], results: Dict):
        """Add overall status section."""
        status = self._get_overall_status(results)
        if status == "passed":
            report.append("## ✅ All Tests Passing\n\n")
        else:
            report.append("## ⚠️ Test Failures Detected\n\n")
    
    def _add_critical_changes(self, report: List[str], deltas: List[TestDelta]):
        """Add critical changes section."""
        self._add_broken_tests(report, deltas)
        self._add_fixed_tests(report, deltas)
    
    def _add_broken_tests(self, report: List[str], deltas: List[TestDelta]):
        """Add broken tests section."""
        broken = [d for d in deltas if d.category == "broken"]
        if broken:
            report.append(f"### 🚨 {len(broken)} New Failures\n")
            for delta in broken[:3]:
                report.append(f"- {delta.component}: {delta.test_name}\n")
            if len(broken) > 3:
                report.append(f"- ...and {len(broken) - 3} more\n")
            report.append("\n")
    
    def _add_fixed_tests(self, report: List[str], deltas: List[TestDelta]):
        """Add fixed tests section."""
        fixed = [d for d in deltas if d.category == "fixed"]
        if fixed:
            report.append(f"### ✅ {len(fixed)} Tests Fixed\n")
            for delta in fixed[:3]:
                report.append(f"- {delta.component}: {delta.test_name}\n")
            if len(fixed) > 3:
                report.append(f"- ...and {len(fixed) - 3} more\n")
            report.append("\n")
    
    def _add_summary_and_failures(self, report: List[str], results: Dict):
        """Add summary table and failure details."""
        report.append("## Current Run Summary\n")
        report.append(self._format_summary_table(results))
        
        failures = self._get_all_failures(results)
        if failures:
            self._add_failure_details(report, failures)
    
    def _add_failure_details(self, report: List[str], failures: Dict):
        """Add detailed failure information."""
        report.append("\n## Failed Tests\n")
        for component, tests in failures.items():
            if tests:
                report.append(f"\n### {component.title()} ({len(tests)})\n")
                for test in tests[:5]:
                    report.append(f"- {test['name']}\n")
                    if test.get('error'):
                        error_preview = test['error'][:100]
                        report.append(f"  ```{error_preview}...```\n")
                if len(tests) > 5:
                    report.append(f"- ...and {len(tests) - 5} more\n")
    
    def _add_flaky_tests_and_links(self, report: List[str]):
        """Add flaky tests section and navigation links."""
        flaky_tests = self.delta_reporter.get_flaky_tests()
        if flaky_tests:
            report.append("\n## ⚠️ Flaky Tests\n")
            for test_key in flaky_tests[:5]:
                report.append(f"- {test_key}\n")
            if len(flaky_tests) > 5:
                report.append(f"- ...and {len(flaky_tests) - 5} more\n")
        
        report.append("\n---\n")
        report.append("📊 [Full Dashboard](dashboard.md) | ")
        report.append("📈 [Delta Details](latest/delta_summary.md) | ")
        report.append("🚨 [Critical Changes](latest/critical_changes.md)\n")
    
    def _create_dashboard(self) -> str:
        """Create dashboard showing last 3 runs."""
        history = self.delta_reporter.load_history()
        runs = history.get("runs", [])[-3:]  # Last 3 runs
        
        if not runs:
            return "# Test Dashboard\n\nNo test runs recorded yet.\n"
        
        dashboard = self._build_dashboard_structure(runs)
        
        return "".join(dashboard)
    
    def _build_dashboard_structure(self, runs: List[Dict]) -> List[str]:
        """Build complete dashboard structure."""
        dashboard = []
        dashboard.append("# Test Dashboard\n")
        dashboard.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        self._add_trends_table(dashboard, runs)
        self._add_component_breakdown(dashboard, runs)
        self._add_key_metrics(dashboard, runs)
        self._add_quick_actions(dashboard)
        
        return dashboard
    
    def _add_trends_table(self, dashboard: List[str], runs: List[Dict]):
        """Add trends overview table."""
        dashboard.append("## Last 3 Runs\n\n")
        dashboard.append("| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |\n")
        dashboard.append("|-----|------|-------|---------|---------|---------|-------|\n")
        
        for i, run in enumerate(reversed(runs), 1):
            timestamp = datetime.fromisoformat(run["timestamp"])
            time_str = timestamp.strftime("%m/%d %H:%M")
            summary = self._get_run_summary(run)
            trend = self._calculate_trend(runs, len(runs) - i)
            
            dashboard.append(f"| {i} | {time_str} | ")
            dashboard.append(f"{summary['total']} | ")
            dashboard.append(f"{summary['passed']} | ")
            dashboard.append(f"{summary['failed']} | ")
            dashboard.append(f"{summary['skipped']} | ")
            dashboard.append(f"{trend} |\n")
    
    def _add_component_breakdown(self, dashboard: List[str], runs: List[Dict]):
        """Add component breakdown for latest run."""
        if not runs:
            return
        
        latest = runs[-1]
        dashboard.append("\n## Latest Run Details\n\n")
        dashboard.append("| Component | Status | Tests | Pass Rate | Duration |\n")
        dashboard.append("|-----------|--------|-------|-----------|----------|\n")
        
        for component in ["backend", "frontend", "e2e"]:
            if component in latest["results"]:
                self._add_component_details(dashboard, component, latest["results"][component])
    
    def _add_component_details(self, dashboard: List[str], component: str, comp_data: Dict):
        """Add details for a specific component."""
        counts = comp_data.get("test_counts", {})
        total = counts.get("total", 0)
        passed = counts.get("passed", 0)
        pass_rate = (passed / total * 100) if total > 0 else 0
        duration = comp_data.get("duration", 0)
        status_icon = "✅" if comp_data["status"] == "passed" else "❌"
        
        dashboard.append(f"| {component.title()} | ")
        dashboard.append(f"{status_icon} | ")
        dashboard.append(f"{total} | ")
        dashboard.append(f"{pass_rate:.1f}% | ")
        dashboard.append(f"{duration:.1f}s |\n")
    
    def _add_key_metrics(self, dashboard: List[str], runs: List[Dict]):
        """Add key metrics section."""
        dashboard.append("\n## Key Metrics\n\n")
        
        if runs:
            total_failures = sum(self._get_run_summary(r)["failed"] for r in runs)
            avg_duration = sum(self._get_run_duration(r) for r in runs) / len(runs)
            
            dashboard.append(f"- **Total Failures (last 3 runs)**: {total_failures}\n")
            dashboard.append(f"- **Average Duration**: {avg_duration:.1f}s\n")
            dashboard.append(f"- **Flaky Tests**: {len(self.delta_reporter.get_flaky_tests())}\n")
    
    def _add_quick_actions(self, dashboard: List[str]):
        """Add quick actions section."""
        dashboard.append("\n## Quick Actions\n\n")
        dashboard.append("```bash\n")
        dashboard.append("# Run smoke tests\n")
        dashboard.append("python test_runner.py --level smoke\n\n")
        dashboard.append("# Run comprehensive tests\n")
        dashboard.append("python test_runner.py --level comprehensive\n\n")
        dashboard.append("# View critical changes\n")
        dashboard.append("cat test_reports/latest/critical_changes.md\n")
        dashboard.append("```\n")
    
    def _get_overall_status(self, results: Dict) -> str:
        """Get overall test status."""
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                if results[component].get("status") not in ["passed", "skipped", "pending"]:
                    return "failed"
        return "passed"
    
    def _format_summary_table(self, results: Dict) -> str:
        """Format summary table for current results."""
        table = []
        table.append("| Component | Status | Tests | Passed | Failed | Duration |\n")
        table.append("|-----------|--------|-------|--------|--------|----------|\n")
        
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                self._add_component_row(table, component, results[component])
        
        return "".join(table)
    
    def _add_component_row(self, table: List[str], component: str, comp_data: Dict):
        """Add a component row to summary table."""
        counts = comp_data.get("test_counts", {})
        status_icon = {
            "passed": "✅",
            "failed": "❌",
            "skipped": "⏭️",
            "pending": "⏸️"
        }.get(comp_data.get("status", "unknown"), "❓")
        
        table.append(f"| {component.title()} | ")
        table.append(f"{status_icon} | ")
        table.append(f"{counts.get('total', 0)} | ")
        table.append(f"{counts.get('passed', 0)} | ")
        table.append(f"{counts.get('failed', 0)} | ")
        table.append(f"{comp_data.get('duration', 0):.1f}s |\n")
    
    def _get_all_failures(self, results: Dict) -> Dict[str, List[Dict]]:
        """Extract all failure details."""
        failures = {}
        
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                failures[component] = self._extract_component_failures(results[component])
        
        return failures
    
    def _extract_component_failures(self, comp_data: Dict) -> List[Dict]:
        """Extract failures for a specific component."""
        comp_failures = []
        if "test_details" in comp_data:
            for test in comp_data["test_details"]:
                if test.get("status") == "failed":
                    comp_failures.append({
                        "name": test["name"],
                        "error": test.get("error", "")
                    })
        
        return comp_failures
    
    def _calculate_trend(self, runs: List[Dict], index: int) -> str:
        """Calculate trend for a specific run."""
        if index == 0 or index >= len(runs):
            return "—"
        
        current = self._get_run_summary(runs[index])
        previous = self._get_run_summary(runs[index - 1])
        
        if current["failed"] < previous["failed"]:
            return "📈"  # Improving
        elif current["failed"] > previous["failed"]:
            return "📉"  # Worsening
        else:
            return "➡️"  # Same
    
    def _get_run_summary(self, run: Dict) -> Dict:
        """Get summary from run, handling both old and new formats."""
        if "summary" in run:
            return run["summary"]
        return self._create_legacy_summary(run)
    
    def _create_legacy_summary(self, run: Dict) -> Dict:
        """Create summary from old format run data."""
        keys = ["total", "passed", "failed", "skipped", "errors"]
        return {key: run.get(key, 0) for key in keys}
    
    def _get_run_duration(self, run: Dict) -> float:
        """Get duration from run, handling both old and new formats."""
        if "results" in run:
            return sum(run["results"].get(c, {}).get("duration", 0) 
                      for c in ["backend", "frontend", "e2e"])
        return run.get("duration", 0)