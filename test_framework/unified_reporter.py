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
        self._populate_unified_report(report, results, deltas, level)
        return "".join(report)
    
    def _populate_unified_report(self, report: List[str], results: Dict, deltas: List[TestDelta], level: str):
        """Populate report with all sections."""
        self._add_header(report, level)
        self._add_status_section(report, results)
        self._add_critical_changes(report, deltas)
        self._add_summary_and_failures(report, results)
        self._add_flaky_tests_and_links(report)
    
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
        broken = self._filter_broken_tests(deltas)
        if broken:
            self._format_broken_tests_section(report, broken)
    
    def _filter_broken_tests(self, deltas: List[TestDelta]) -> List[TestDelta]:
        """Filter deltas to get only broken tests."""
        return [d for d in deltas if d.category == "broken"]
    
    def _format_broken_tests_section(self, report: List[str], broken: List[TestDelta]):
        """Format broken tests section in report."""
        report.append(f"### 🚨 {len(broken)} New Failures\n")
        self._add_broken_test_entries(report, broken)
        self._add_overflow_indicator(report, broken)
        report.append("\n")
    
    def _add_broken_test_entries(self, report: List[str], broken: List[TestDelta]):
        """Add individual broken test entries."""
        for delta in broken[:3]:
            report.append(f"- {delta.component}: {delta.test_name}\n")
    
    def _add_overflow_indicator(self, report: List[str], items: List):
        """Add overflow indicator if there are more items than displayed."""
        if len(items) > 3:
            report.append(f"- ...and {len(items) - 3} more\n")
    
    def _add_fixed_tests(self, report: List[str], deltas: List[TestDelta]):
        """Add fixed tests section."""
        fixed = self._filter_fixed_tests(deltas)
        if fixed:
            self._format_fixed_tests_section(report, fixed)
    
    def _filter_fixed_tests(self, deltas: List[TestDelta]) -> List[TestDelta]:
        """Filter deltas to get only fixed tests."""
        return [d for d in deltas if d.category == "fixed"]
    
    def _format_fixed_tests_section(self, report: List[str], fixed: List[TestDelta]):
        """Format fixed tests section in report."""
        report.append(f"### ✅ {len(fixed)} Tests Fixed\n")
        self._add_fixed_test_entries(report, fixed)
        self._add_overflow_indicator(report, fixed)
        report.append("\n")
    
    def _add_fixed_test_entries(self, report: List[str], fixed: List[TestDelta]):
        """Add individual fixed test entries."""
        for delta in fixed[:3]:
            report.append(f"- {delta.component}: {delta.test_name}\n")
    
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
        self._process_component_failures(report, failures)
    
    def _process_component_failures(self, report: List[str], failures: Dict):
        """Process failures for each component."""
        for component, tests in failures.items():
            if tests:
                self._add_component_failure_section(report, component, tests)
    
    def _add_component_failure_section(self, report: List[str], component: str, tests: List):
        """Add failure section for a component."""
        report.append(f"\n### {component.title()} ({len(tests)})\n")
        self._add_test_failure_entries(report, tests)
        self._add_test_overflow_indicator(report, tests)
    
    def _add_test_failure_entries(self, report: List[str], tests: List):
        """Add individual test failure entries."""
        for test in tests[:5]:
            self._add_single_test_failure(report, test)
    
    def _add_single_test_failure(self, report: List[str], test: Dict):
        """Add a single test failure entry."""
        report.append(f"- {test['name']}\n")
        if test.get('error'):
            error_preview = test['error'][:100]
            report.append(f"  ```{error_preview}...```\n")
    
    def _add_test_overflow_indicator(self, report: List[str], tests: List):
        """Add overflow indicator for test failures."""
        if len(tests) > 5:
            report.append(f"- ...and {len(tests) - 5} more\n")
    
    def _add_flaky_tests_and_links(self, report: List[str]):
        """Add flaky tests section and navigation links."""
        self._add_flaky_tests_section(report)
        self._add_navigation_links(report)
    
    def _add_flaky_tests_section(self, report: List[str]):
        """Add flaky tests section if any exist."""
        flaky_tests = self.delta_reporter.get_flaky_tests()
        if flaky_tests:
            self._format_flaky_tests(report, flaky_tests)
    
    def _format_flaky_tests(self, report: List[str], flaky_tests: List):
        """Format flaky tests section."""
        report.append("\n## ⚠️ Flaky Tests\n")
        self._add_flaky_test_entries(report, flaky_tests)
        self._add_flaky_overflow_indicator(report, flaky_tests)
    
    def _add_flaky_test_entries(self, report: List[str], flaky_tests: List):
        """Add individual flaky test entries."""
        for test_key in flaky_tests[:5]:
            report.append(f"- {test_key}\n")
    
    def _add_flaky_overflow_indicator(self, report: List[str], flaky_tests: List):
        """Add overflow indicator for flaky tests."""
        if len(flaky_tests) > 5:
            report.append(f"- ...and {len(flaky_tests) - 5} more\n")
    
    def _add_navigation_links(self, report: List[str]):
        """Add navigation links to related reports."""
        report.append("\n---\n")
        report.append("📊 [Full Dashboard](dashboard.md) | ")
        report.append("📈 [Delta Details](latest/delta_summary.md) | ")
        report.append("🚨 [Critical Changes](latest/critical_changes.md)\n")
    
    def _create_dashboard(self) -> str:
        """Create dashboard showing last 3 runs."""
        history = self.delta_reporter.load_history()
        runs = self._get_recent_runs(history)
        return self._generate_dashboard_content(runs)
    
    def _get_recent_runs(self, history: Dict) -> List[Dict]:
        """Get the last 3 runs from history."""
        return history.get("runs", [])[-3:]
    
    def _generate_dashboard_content(self, runs: List[Dict]) -> str:
        """Generate dashboard content based on runs."""
        if not runs:
            return "# Test Dashboard\n\nNo test runs recorded yet.\n"
        dashboard = self._build_dashboard_structure(runs)
        return "".join(dashboard)
    
    def _build_dashboard_structure(self, runs: List[Dict]) -> List[str]:
        """Build complete dashboard structure."""
        dashboard = []
        self._add_dashboard_header(dashboard)
        self._populate_dashboard_sections(dashboard, runs)
        return dashboard
    
    def _add_dashboard_header(self, dashboard: List[str]):
        """Add dashboard header with title and timestamp."""
        dashboard.append("# Test Dashboard\n")
        dashboard.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def _populate_dashboard_sections(self, dashboard: List[str], runs: List[Dict]):
        """Populate all dashboard sections."""
        self._add_trends_table(dashboard, runs)
        self._add_component_breakdown(dashboard, runs)
        self._add_key_metrics(dashboard, runs)
        self._add_quick_actions(dashboard)
    
    def _add_trends_table(self, dashboard: List[str], runs: List[Dict]):
        """Add trends overview table."""
        self._add_trends_table_header(dashboard)
        self._populate_trends_table_rows(dashboard, runs)
    
    def _add_trends_table_header(self, dashboard: List[str]):
        """Add header for trends table."""
        dashboard.append("## Last 3 Runs\n\n")
        dashboard.append("| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |\n")
        dashboard.append("|-----|------|-------|---------|---------|---------|-------|\n")
    
    def _populate_trends_table_rows(self, dashboard: List[str], runs: List[Dict]):
        """Populate rows for trends table."""
        for i, run in enumerate(reversed(runs), 1):
            self._add_trends_table_row(dashboard, runs, run, i)
    
    def _add_trends_table_row(self, dashboard: List[str], runs: List[Dict], run: Dict, row_num: int):
        """Add a single row to trends table."""
        row_data = self._prepare_trends_row_data(runs, run, row_num)
        self._format_trends_table_row(dashboard, row_data)
    
    def _prepare_trends_row_data(self, runs: List[Dict], run: Dict, row_num: int) -> Dict:
        """Prepare data for a trends table row."""
        timestamp = datetime.fromisoformat(run["timestamp"])
        time_str = timestamp.strftime("%m/%d %H:%M")
        summary = self._get_run_summary(run)
        trend = self._calculate_trend(runs, len(runs) - row_num)
        return {"row_num": row_num, "time_str": time_str, "summary": summary, "trend": trend}
    
    def _format_trends_table_row(self, dashboard: List[str], row_data: Dict):
        """Format and append a trends table row."""
        dashboard.append(f"| {row_data['row_num']} | {row_data['time_str']} | ")
        dashboard.append(f"{row_data['summary']['total']} | ")
        dashboard.append(f"{row_data['summary']['passed']} | ")
        dashboard.append(f"{row_data['summary']['failed']} | ")
        dashboard.append(f"{row_data['summary']['skipped']} | ")
        dashboard.append(f"{row_data['trend']} |\n")
    
    def _add_component_breakdown(self, dashboard: List[str], runs: List[Dict]):
        """Add component breakdown for latest run."""
        if not runs:
            return
        latest = runs[-1]
        self._add_breakdown_header(dashboard)
        self._process_latest_run_components(dashboard, latest)
    
    def _add_breakdown_header(self, dashboard: List[str]):
        """Add header for component breakdown section."""
        dashboard.append("\n## Latest Run Details\n\n")
        dashboard.append("| Component | Status | Tests | Pass Rate | Duration |\n")
        dashboard.append("|-----------|--------|-------|-----------|----------|\n")
    
    def _process_latest_run_components(self, dashboard: List[str], latest: Dict):
        """Process components from the latest run."""
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
            self._add_calculated_metrics(dashboard, runs)
    
    def _add_calculated_metrics(self, dashboard: List[str], runs: List[Dict]):
        """Add calculated metrics to dashboard."""
        metrics = self._calculate_dashboard_metrics(runs)
        self._format_metrics_output(dashboard, metrics)
    
    def _calculate_dashboard_metrics(self, runs: List[Dict]) -> Dict:
        """Calculate key metrics from runs."""
        total_failures = sum(self._get_run_summary(r)["failed"] for r in runs)
        avg_duration = sum(self._get_run_duration(r) for r in runs) / len(runs)
        flaky_count = len(self.delta_reporter.get_flaky_tests())
        return {"total_failures": total_failures, "avg_duration": avg_duration, "flaky_count": flaky_count}
    
    def _format_metrics_output(self, dashboard: List[str], metrics: Dict):
        """Format metrics output to dashboard."""
        dashboard.append(f"- **Total Failures (last 3 runs)**: {metrics['total_failures']}\n")
        dashboard.append(f"- **Average Duration**: {metrics['avg_duration']:.1f}s\n")
        dashboard.append(f"- **Flaky Tests**: {metrics['flaky_count']}\n")
    
    def _add_quick_actions(self, dashboard: List[str]):
        """Add quick actions section."""
        dashboard.append("\n## Quick Actions\n\n")
        self._add_action_commands_block(dashboard)
    
    def _add_action_commands_block(self, dashboard: List[str]):
        """Add command block with quick actions."""
        dashboard.append("```bash\n")
        self._add_test_commands(dashboard)
        self._add_view_commands(dashboard)
        dashboard.append("```\n")
    
    def _add_test_commands(self, dashboard: List[str]):
        """Add test execution commands."""
        dashboard.append("# Run smoke tests\n")
        dashboard.append("python test_runner.py --level smoke\n\n")
        dashboard.append("# Run comprehensive tests\n")
        dashboard.append("python test_runner.py --level comprehensive\n\n")
    
    def _add_view_commands(self, dashboard: List[str]):
        """Add view/report commands."""
        dashboard.append("# View critical changes\n")
        dashboard.append("cat test_reports/latest/critical_changes.md\n")
    
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
        self._add_summary_table_header(table)
        self._populate_summary_table_rows(table, results)
        return "".join(table)
    
    def _add_summary_table_header(self, table: List[str]):
        """Add header row for summary table."""
        table.append("| Component | Status | Tests | Passed | Failed | Duration |\n")
        table.append("|-----------|--------|-------|--------|--------|----------|\n")
    
    def _populate_summary_table_rows(self, table: List[str], results: Dict):
        """Populate table rows for each component."""
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                self._add_component_row(table, component, results[component])
    
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
        self._extract_failures_by_component(failures, results)
        return failures
    
    def _extract_failures_by_component(self, failures: Dict, results: Dict):
        """Extract failures for each component."""
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                failures[component] = self._extract_component_failures(results[component])
    
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