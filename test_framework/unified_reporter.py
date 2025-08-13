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
        # Detect deltas
        deltas = self.delta_reporter.detect_deltas(current_results)
        
        # Update history
        self.delta_reporter.update_history(current_results, level)
        
        # Save delta reports
        self.delta_reporter.save_reports(deltas, current_results)
        
        # Generate unified view
        report = self._create_unified_view(current_results, deltas, level)
        
        # Save unified report
        with open(self.unified_file, 'w') as f:
            f.write(report)
        
        # Generate dashboard
        dashboard = self._create_dashboard()
        with open(self.dashboard_file, 'w') as f:
            f.write(dashboard)
        
        return report
    
    def _create_unified_view(self, results: Dict, deltas: List[TestDelta], 
                            level: str) -> str:
        """Create unified view combining current results and deltas."""
        report = []
        
        # Header
        report.append("# Unified Test Report\n")
        report.append(f"**Level**: {level} | ")
        report.append(f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Quick Status
        status = self._get_overall_status(results)
        if status == "passed":
            report.append("## ✅ All Tests Passing\n\n")
        else:
            report.append("## ⚠️ Test Failures Detected\n\n")
        
        # Critical Changes (if any)
        broken = [d for d in deltas if d.category == "broken"]
        if broken:
            report.append(f"### 🚨 {len(broken)} New Failures\n")
            for delta in broken[:3]:
                report.append(f"- {delta.component}: {delta.test_name}\n")
            if len(broken) > 3:
                report.append(f"- ...and {len(broken) - 3} more\n")
            report.append("\n")
        
        fixed = [d for d in deltas if d.category == "fixed"]
        if fixed:
            report.append(f"### ✅ {len(fixed)} Tests Fixed\n")
            for delta in fixed[:3]:
                report.append(f"- {delta.component}: {delta.test_name}\n")
            if len(fixed) > 3:
                report.append(f"- ...and {len(fixed) - 3} more\n")
            report.append("\n")
        
        # Current Run Summary
        report.append("## Current Run Summary\n")
        report.append(self._format_summary_table(results))
        
        # Failure Details (if any)
        failures = self._get_all_failures(results)
        if failures:
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
        
        # Flaky Tests
        flaky_tests = self.delta_reporter.get_flaky_tests()
        if flaky_tests:
            report.append("\n## ⚠️ Flaky Tests\n")
            for test_key in flaky_tests[:5]:
                report.append(f"- {test_key}\n")
            if len(flaky_tests) > 5:
                report.append(f"- ...and {len(flaky_tests) - 5} more\n")
        
        # Links
        report.append("\n---\n")
        report.append("📊 [Full Dashboard](dashboard.md) | ")
        report.append("📈 [Delta Details](latest/delta_summary.md) | ")
        report.append("🚨 [Critical Changes](latest/critical_changes.md)\n")
        
        return "".join(report)
    
    def _create_dashboard(self) -> str:
        """Create dashboard showing last 3 runs."""
        history = self.delta_reporter.load_history()
        runs = history.get("runs", [])[-3:]  # Last 3 runs
        
        if not runs:
            return "# Test Dashboard\n\nNo test runs recorded yet.\n"
        
        dashboard = []
        dashboard.append("# Test Dashboard\n")
        dashboard.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Trend Overview
        dashboard.append("## Last 3 Runs\n\n")
        dashboard.append("| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |\n")
        dashboard.append("|-----|------|-------|---------|---------|---------|-------|\n")
        
        for i, run in enumerate(reversed(runs), 1):
            timestamp = datetime.fromisoformat(run["timestamp"])
            time_str = timestamp.strftime("%m/%d %H:%M")
            summary = run["summary"]
            
            # Calculate trend
            trend = self._calculate_trend(runs, len(runs) - i)
            
            dashboard.append(f"| {i} | {time_str} | ")
            dashboard.append(f"{summary['total']} | ")
            dashboard.append(f"{summary['passed']} | ")
            dashboard.append(f"{summary['failed']} | ")
            dashboard.append(f"{summary['skipped']} | ")
            dashboard.append(f"{trend} |\n")
        
        # Component Breakdown
        if runs:
            latest = runs[-1]
            dashboard.append("\n## Latest Run Details\n\n")
            dashboard.append("| Component | Status | Tests | Pass Rate | Duration |\n")
            dashboard.append("|-----------|--------|-------|-----------|----------|\n")
            
            for component in ["backend", "frontend", "e2e"]:
                if component in latest["results"]:
                    comp_data = latest["results"][component]
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
        
        # Key Metrics
        dashboard.append("\n## Key Metrics\n\n")
        
        # Calculate metrics
        if runs:
            total_failures = sum(r["summary"]["failed"] for r in runs)
            avg_duration = sum(
                r["results"].get("backend", {}).get("duration", 0) +
                r["results"].get("frontend", {}).get("duration", 0) +
                r["results"].get("e2e", {}).get("duration", 0)
                for r in runs
            ) / len(runs)
            
            dashboard.append(f"- **Total Failures (last 3 runs)**: {total_failures}\n")
            dashboard.append(f"- **Average Duration**: {avg_duration:.1f}s\n")
            dashboard.append(f"- **Flaky Tests**: {len(self.delta_reporter.get_flaky_tests())}\n")
        
        # Quick Actions
        dashboard.append("\n## Quick Actions\n\n")
        dashboard.append("```bash\n")
        dashboard.append("# Run smoke tests\n")
        dashboard.append("python test_runner.py --level smoke\n\n")
        dashboard.append("# Run comprehensive tests\n")
        dashboard.append("python test_runner.py --level comprehensive\n\n")
        dashboard.append("# View critical changes\n")
        dashboard.append("cat test_reports/latest/critical_changes.md\n")
        dashboard.append("```\n")
        
        return "".join(dashboard)
    
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
            if component not in results:
                continue
            
            comp_data = results[component]
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
        
        return "".join(table)
    
    def _get_all_failures(self, results: Dict) -> Dict[str, List[Dict]]:
        """Extract all failure details."""
        failures = {}
        
        for component in ["backend", "frontend", "e2e"]:
            if component not in results:
                continue
            
            comp_failures = []
            if "test_details" in results[component]:
                for test in results[component]["test_details"]:
                    if test.get("status") == "failed":
                        comp_failures.append({
                            "name": test["name"],
                            "error": test.get("error", "")
                        })
            
            failures[component] = comp_failures
        
        return failures
    
    def _calculate_trend(self, runs: List[Dict], index: int) -> str:
        """Calculate trend for a specific run."""
        if index == 0 or index >= len(runs):
            return "—"
        
        current = runs[index]["summary"]
        previous = runs[index - 1]["summary"]
        
        if current["failed"] < previous["failed"]:
            return "📈"  # Improving
        elif current["failed"] > previous["failed"]:
            return "📉"  # Worsening
        else:
            return "➡️"  # Same