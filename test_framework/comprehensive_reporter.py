#!/usr/bin/env python
"""
Comprehensive Test Reporter - Clear, accurate test reporting with persistent tracking.

This module provides:
- Complete tracking of ALL test categories and levels
- Persistent test count tracking (known tests even if collection fails)
- Clear, readable dashboards and summaries
- Accurate test result aggregation
- No legacy artifacts or confusing reports
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict


class ComprehensiveTestReporter:
    """Manages comprehensive test reporting with persistent tracking."""
    
    # All known test levels from test_config.py
    KNOWN_TEST_LEVELS = [
        "smoke", "unit", "agents", "integration", "critical",
        "comprehensive", "comprehensive-backend", "comprehensive-frontend",
        "comprehensive-core", "comprehensive-agents", "comprehensive-websocket",
        "comprehensive-database", "comprehensive-api", "all",
        "real_e2e", "real_services", "mock_only"
    ]
    
    # All known test categories with expected test counts
    KNOWN_CATEGORIES = {
        "smoke": {"description": "Quick smoke tests", "expected_count": 10},
        "unit": {"description": "Unit tests", "expected_count": 100},
        "integration": {"description": "Integration tests", "expected_count": 50},
        "critical": {"description": "Critical path tests", "expected_count": 20},
        "agents": {"description": "Agent tests", "expected_count": 30},
        "websocket": {"description": "WebSocket tests", "expected_count": 15},
        "database": {"description": "Database tests", "expected_count": 25},
        "api": {"description": "API tests", "expected_count": 40},
        "e2e": {"description": "End-to-end tests", "expected_count": 20},
        "real_services": {"description": "Real service tests", "expected_count": 15}
    }
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)
        
        # Persistent storage files
        self.state_file = reports_dir / "test_state.json"
        self.history_file = reports_dir / "test_history.json"
        self.dashboard_file = reports_dir / "dashboard.md"
        self.summary_file = reports_dir / "summary.md"
        
        # Load persistent state
        self.test_state = self._load_test_state()
        self.test_history = self._load_test_history()
    
    def _load_test_state(self) -> Dict:
        """Load persistent test state including known test counts."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Initialize with default state
        return {
            "known_tests": {},
            "last_successful_counts": {},
            "category_status": {},
            "last_update": None
        }
    
    def _load_test_history(self) -> List[Dict]:
        """Load test run history."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    # Keep only last 50 runs
                    return data[-50:] if isinstance(data, list) else []
            except:
                pass
        return []
    
    def _save_test_state(self):
        """Save persistent test state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.test_state, f, indent=2)
    
    def _save_test_history(self):
        """Save test run history."""
        with open(self.history_file, 'w') as f:
            json.dump(self.test_history[-50:], f, indent=2)
    
    def generate_comprehensive_report(self, 
                                     level: str, 
                                     results: Dict,
                                     config: Dict,
                                     exit_code: int) -> str:
        """Generate comprehensive test report with all categories."""
        
        # Update persistent state
        self._update_test_state(level, results)
        
        # Generate reports
        dashboard = self._generate_dashboard(level, results, exit_code)
        summary = self._generate_summary(level, results, exit_code)
        
        # Save reports
        self._save_dashboard(dashboard)
        self._save_summary(summary)
        
        # Update history
        self._add_to_history(level, results, exit_code)
        
        return dashboard
    
    def _update_test_state(self, level: str, results: Dict):
        """Update persistent test state with current results."""
        timestamp = datetime.now().isoformat()
        
        # Update known test counts for successful collections
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                counts = results[component].get("test_counts", {})
                if counts.get("total", 0) > 0:
                    # Store successful counts
                    if component not in self.test_state["last_successful_counts"]:
                        self.test_state["last_successful_counts"][component] = {}
                    self.test_state["last_successful_counts"][component][level] = {
                        "total": counts.get("total", 0),
                        "timestamp": timestamp
                    }
        
        self.test_state["last_update"] = timestamp
        self._save_test_state()
    
    def _generate_dashboard(self, level: str, results: Dict, exit_code: int) -> str:
        """Generate comprehensive dashboard with all categories."""
        dashboard = []
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Header
        dashboard.append("# Test Dashboard")
        dashboard.append(f"**Level**: {level} | **Time**: {timestamp}")
        dashboard.append("")
        
        # Overall status
        overall_status = self._determine_overall_status(results, exit_code)
        dashboard.append(f"## Overall Status: {overall_status}")
        dashboard.append("")
        
        # Component summary table
        dashboard.append("## Component Summary")
        dashboard.append("")
        dashboard.append("| Component | Status | Tests | Passed | Failed | Errors | Import Errors | Duration |")
        dashboard.append("|-----------|--------|-------|--------|--------|--------|---------------|----------|")
        
        # Add rows for each component
        for component in ["backend", "frontend", "e2e"]:
            row = self._generate_component_row(component, results)
            dashboard.append(row)
        
        dashboard.append("")
        
        # Test categories table
        dashboard.append("## Test Categories")
        dashboard.append("")
        dashboard.append("| Category | Description | Expected | Actual | Status | Last Success |")
        dashboard.append("|----------|-------------|----------|--------|--------|--------------|")
        
        # Add rows for each known category
        for category, info in self.KNOWN_CATEGORIES.items():
            row = self._generate_category_row(category, info, results)
            dashboard.append(row)
        
        dashboard.append("")
        
        # Issues section
        issues = self._collect_issues(results)
        if issues:
            dashboard.append("## 🔴 Issues Detected")
            dashboard.append("")
            for issue in issues:
                dashboard.append(f"- {issue}")
            dashboard.append("")
        
        # Statistics
        stats = self._calculate_statistics(results)
        dashboard.append("## Statistics")
        dashboard.append("")
        dashboard.append(f"- **Total Tests**: {stats['total']}")
        dashboard.append(f"- **Passed**: {stats['passed']}")
        dashboard.append(f"- **Failed**: {stats['failed']}")
        dashboard.append(f"- **Errors**: {stats['errors']}")
        dashboard.append(f"- **Skipped**: {stats['skipped']}")
        dashboard.append(f"- **Total Duration**: {stats['duration']:.2f}s")
        dashboard.append(f"- **Pass Rate**: {stats['pass_rate']:.1f}%")
        dashboard.append("")
        
        # Test level information
        dashboard.append("## Available Test Levels")
        dashboard.append("")
        dashboard.append("| Level | Command | Purpose |")
        dashboard.append("|-------|---------|---------|")
        for test_level in self.KNOWN_TEST_LEVELS[:5]:  # Show first 5
            dashboard.append(f"| {test_level} | `python test_runner.py --level {test_level}` | See test_config.py |")
        dashboard.append("| ... | See all levels with `python test_runner.py --list` | ... |")
        dashboard.append("")
        
        # Quick actions
        dashboard.append("## Quick Actions")
        dashboard.append("")
        dashboard.append("```bash")
        dashboard.append("# Run specific test levels")
        dashboard.append("python test_runner.py --level unit")
        dashboard.append("python test_runner.py --level smoke")
        dashboard.append("python test_runner.py --level comprehensive")
        dashboard.append("")
        dashboard.append("# List all available tests")
        dashboard.append("python test_runner.py --list")
        dashboard.append("")
        dashboard.append("# Run failing tests")
        dashboard.append("python test_runner.py --run-failing")
        dashboard.append("```")
        dashboard.append("")
        
        return "\n".join(dashboard)
    
    def _generate_summary(self, level: str, results: Dict, exit_code: int) -> str:
        """Generate concise summary."""
        summary = []
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        summary.append("# Test Summary")
        summary.append(f"**Level**: {level} | **Time**: {timestamp}")
        summary.append("")
        
        overall_status = self._determine_overall_status(results, exit_code)
        summary.append(f"**Status**: {overall_status}")
        summary.append("")
        
        # Component summaries
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                comp_summary = self._generate_component_summary(component, results[component])
                summary.append(f"**{component.title()}**: {comp_summary}")
        
        summary.append("")
        
        # Issues
        issues = self._collect_issues(results)
        if issues:
            summary.append("## Issues")
            for issue in issues:
                summary.append(f"- {issue}")
        
        summary.append("")
        
        return "\n".join(summary)
    
    def _determine_overall_status(self, results: Dict, exit_code: int) -> str:
        """Determine overall test status."""
        if exit_code == 0:
            return "✅ All tests passed"
        
        # Count failures
        total_failed = 0
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                counts = results[component].get("test_counts", {})
                total_failed += counts.get("failed", 0)
                total_failed += counts.get("errors", 0)
        
        if total_failed > 0:
            return f"❌ Failed - {total_failed} test(s) failed"
        else:
            return "⚠️ Collection or execution issues"
    
    def _generate_component_row(self, component: str, results: Dict) -> str:
        """Generate table row for a component."""
        if component not in results:
            # Use last known good counts if available
            last_counts = self.test_state["last_successful_counts"].get(component, {})
            return f"| {component.title()} | ⚫ not_run | - | - | - | - | - | - |"
        
        data = results[component]
        counts = data.get("test_counts", {})
        
        # Determine status icon
        status = data.get("status", "unknown")
        if status == "passed":
            icon = "✅"
        elif status == "failed":
            icon = "❌"
        elif status == "collection_failed":
            icon = "⚫"
            status = "collection_failed"
        else:
            icon = "⚠️"
        
        return (f"| {component.title()} | {icon} {status} | "
                f"{counts.get('total', 0)} | {counts.get('passed', 0)} | "
                f"{counts.get('failed', 0)} | {counts.get('errors', 0)} | "
                f"{counts.get('import_errors', 0)} | "
                f"{data.get('duration', 0):.2f}s |")
    
    def _generate_category_row(self, category: str, info: Dict, results: Dict) -> str:
        """Generate table row for a test category."""
        # Try to find actual counts from results
        actual_count = 0
        status = "⚪"
        
        # Check each component for this category
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                # Look for category-specific counts if available
                comp_data = results[component]
                if "categories" in comp_data:
                    cat_data = comp_data["categories"].get(category, {})
                    actual_count += cat_data.get("count", 0)
                    if cat_data.get("failed", 0) > 0:
                        status = "❌"
                    elif cat_data.get("passed", 0) > 0:
                        status = "✅"
        
        # Get last successful run for this category
        last_success = self.test_state.get("category_status", {}).get(category, {}).get("last_success", "Never")
        
        return (f"| {category} | {info['description']} | "
                f"{info['expected_count']} | {actual_count} | {status} | {last_success} |")
    
    def _collect_issues(self, results: Dict) -> List[str]:
        """Collect all issues from test results."""
        issues = []
        
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                data = results[component]
                counts = data.get("test_counts", {})
                
                if counts.get("failed", 0) > 0:
                    issues.append(f"{component}: {counts['failed']} test(s) failed")
                
                if counts.get("errors", 0) > 0:
                    issues.append(f"{component}: {counts['errors']} error(s)")
                
                if data.get("status") == "collection_failed":
                    issues.append(f"{component}: Test collection failed")
        
        return issues
    
    def _calculate_statistics(self, results: Dict) -> Dict:
        """Calculate overall statistics."""
        stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "duration": 0.0,
            "pass_rate": 0.0
        }
        
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                counts = results[component].get("test_counts", {})
                stats["total"] += counts.get("total", 0)
                stats["passed"] += counts.get("passed", 0)
                stats["failed"] += counts.get("failed", 0)
                stats["errors"] += counts.get("errors", 0)
                stats["skipped"] += counts.get("skipped", 0)
                stats["duration"] += results[component].get("duration", 0)
        
        if stats["total"] > 0:
            stats["pass_rate"] = (stats["passed"] / stats["total"]) * 100
        
        return stats
    
    def _generate_component_summary(self, component: str, data: Dict) -> str:
        """Generate component summary text."""
        counts = data.get("test_counts", {})
        status = data.get("status", "unknown")
        
        if status == "collection_failed":
            return "⚫ No tests ran"
        
        parts = []
        if counts.get("passed", 0) > 0:
            parts.append(f"{counts['passed']} passed")
        if counts.get("failed", 0) > 0:
            parts.append(f"{counts['failed']} failed")
        if counts.get("skipped", 0) > 0:
            parts.append(f"{counts['skipped']} skipped")
        
        if not parts:
            return "⚫ No tests ran"
        
        icon = "✅" if status == "passed" else "❌"
        return f"{icon} {', '.join(parts)}"
    
    def _add_to_history(self, level: str, results: Dict, exit_code: int):
        """Add current run to history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "exit_code": exit_code,
            "stats": self._calculate_statistics(results)
        }
        
        self.test_history.append(entry)
        self._save_test_history()
    
    def _save_dashboard(self, content: str):
        """Save dashboard to file."""
        with open(self.dashboard_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _save_summary(self, content: str):
        """Save summary to file."""
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def cleanup_old_reports(self, keep_days: int = 7):
        """Clean up old report files."""
        # This is intentionally simple - we keep persistent state
        # but can clean up old detailed reports
        pass