#!/usr/bin/env python
"""
Delta Reporter - Tracks test result changes and critical deltas between runs.
Focuses on what changed rather than generating repetitive reports.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TestDelta:
    """Represents a change in test status between runs."""
    test_name: str
    previous_status: str
    current_status: str
    category: str  # "fixed", "broken", "flaky", "new", "removed"
    component: str  # "backend", "frontend", "e2e"
    details: Optional[str] = None


class DeltaReporter:
    """Manages test result deltas and history tracking."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.history_file = reports_dir / "metrics" / "test_history.json"
        self.delta_file = reports_dir / "latest" / "delta_summary.md"
        self.critical_file = reports_dir / "latest" / "critical_changes.md"
        
    def load_history(self) -> Dict:
        """Load test history from JSON file."""
        if not self.history_file.exists():
            return {"runs": [], "tests": {}}
        with open(self.history_file, 'r') as f:
            return json.load(f)
    
    def save_history(self, history: Dict):
        """Save test history to JSON file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2, default=str)
    
    def detect_deltas(self, current_results: Dict, 
                     previous_results: Optional[Dict] = None) -> List[TestDelta]:
        """Detect changes between current and previous test runs."""
        if not previous_results:
            history = self.load_history()
            if history["runs"]:
                # Check if the last run has results
                last_run = history["runs"][-1]
                if "results" in last_run:
                    previous_results = last_run["results"]
                else:
                    # Old format compatibility
                    return self._all_new_tests(current_results)
            else:
                return self._all_new_tests(current_results)
        
        deltas = []
        
        # Check each component
        for component in ["backend", "frontend", "e2e"]:
            curr_tests = self._extract_tests(current_results, component)
            prev_tests = self._extract_tests(previous_results, component)
            
            # Find status changes
            for test_name, curr_status in curr_tests.items():
                prev_status = prev_tests.get(test_name)
                
                if not prev_status:
                    deltas.append(TestDelta(
                        test_name=test_name,
                        previous_status="none",
                        current_status=curr_status,
                        category="new",
                        component=component
                    ))
                elif prev_status != curr_status:
                    category = self._categorize_change(prev_status, curr_status)
                    deltas.append(TestDelta(
                        test_name=test_name,
                        previous_status=prev_status,
                        current_status=curr_status,
                        category=category,
                        component=component
                    ))
            
            # Find removed tests
            for test_name in prev_tests:
                if test_name not in curr_tests:
                    deltas.append(TestDelta(
                        test_name=test_name,
                        previous_status=prev_tests[test_name],
                        current_status="removed",
                        category="removed",
                        component=component
                    ))
        
        return deltas
    
    def _extract_tests(self, results: Dict, component: str) -> Dict[str, str]:
        """Extract individual test results from component results."""
        tests = {}
        if component not in results:
            return tests
        
        comp_data = results[component]
        if "test_details" in comp_data:
            for test in comp_data["test_details"]:
                tests[test["name"]] = test["status"]
        
        return tests
    
    def _categorize_change(self, prev: str, curr: str) -> str:
        """Categorize the type of status change."""
        if prev == "failed" and curr == "passed":
            return "fixed"
        elif prev == "passed" and curr == "failed":
            return "broken"
        elif prev in ["failed", "passed"] and curr in ["failed", "passed"]:
            return "flaky"
        else:
            return "changed"
    
    def _all_new_tests(self, results: Dict) -> List[TestDelta]:
        """Handle first run - all tests are new."""
        deltas = []
        for component in ["backend", "frontend", "e2e"]:
            tests = self._extract_tests(results, component)
            for test_name, status in tests.items():
                deltas.append(TestDelta(
                    test_name=test_name,
                    previous_status="none",
                    current_status=status,
                    category="new",
                    component=component
                ))
        return deltas
    
    def update_history(self, results: Dict, level: str):
        """Update test history with new run data."""
        history = self.load_history()
        
        # Keep only last 10 runs
        if len(history["runs"]) >= 10:
            history["runs"] = history["runs"][-9:]
        
        # Add new run
        run_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "results": results,
            "summary": self._create_summary(results)
        }
        history["runs"].append(run_data)
        
        # Update test tracking
        for component in ["backend", "frontend", "e2e"]:
            tests = self._extract_tests(results, component)
            for test_name, status in tests.items():
                key = f"{component}::{test_name}"
                if key not in history["tests"]:
                    history["tests"][key] = {"runs": []}
                
                # Keep last 5 results per test
                test_history = history["tests"][key]["runs"]
                if len(test_history) >= 5:
                    test_history = test_history[-4:]
                
                test_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "status": status
                })
                history["tests"][key]["runs"] = test_history
        
        self.save_history(history)
    
    def _create_summary(self, results: Dict) -> Dict:
        """Create summary statistics for a test run."""
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for component in ["backend", "frontend", "e2e"]:
            if component in results and "test_counts" in results[component]:
                counts = results[component]["test_counts"]
                for key in summary:
                    summary[key] += counts.get(key, 0)
        
        return summary
    
    def generate_delta_report(self, deltas: List[TestDelta]) -> str:
        """Generate a human-readable delta report."""
        if not deltas:
            return "✅ No changes detected from previous run\n"
        
        report = []
        report.append("# Test Delta Report\n")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Group deltas by category
        fixed = [d for d in deltas if d.category == "fixed"]
        broken = [d for d in deltas if d.category == "broken"]
        flaky = [d for d in deltas if d.category == "flaky"]
        new = [d for d in deltas if d.category == "new"]
        removed = [d for d in deltas if d.category == "removed"]
        
        # Critical changes first
        if broken:
            report.append("\n## 🔴 NEWLY BROKEN TESTS\n")
            for delta in broken:
                report.append(f"- **{delta.component}**: {delta.test_name}\n")
        
        if fixed:
            report.append("\n## ✅ FIXED TESTS\n")
            for delta in fixed:
                report.append(f"- **{delta.component}**: {delta.test_name}\n")
        
        if flaky:
            report.append("\n## ⚠️ FLAKY TESTS\n")
            for delta in flaky:
                report.append(f"- **{delta.component}**: {delta.test_name} ")
                report.append(f"({delta.previous_status} → {delta.current_status})\n")
        
        if new:
            report.append(f"\n## 🆕 NEW TESTS ({len(new)})\n")
            if len(new) <= 10:
                for delta in new:
                    report.append(f"- **{delta.component}**: {delta.test_name}\n")
            else:
                report.append(f"- {len(new)} new tests added\n")
        
        if removed:
            report.append(f"\n## 🗑️ REMOVED TESTS ({len(removed)})\n")
            if len(removed) <= 10:
                for delta in removed:
                    report.append(f"- **{delta.component}**: {delta.test_name}\n")
            else:
                report.append(f"- {len(removed)} tests removed\n")
        
        return "".join(report)
    
    def generate_critical_report(self, deltas: List[TestDelta], 
                                results: Dict) -> str:
        """Generate report focusing only on critical issues."""
        report = []
        report.append("# Critical Changes\n")
        
        broken = [d for d in deltas if d.category == "broken"]
        
        if not broken and self._all_passing(results):
            report.append("✅ **All tests passing - no critical issues**\n")
            return "".join(report)
        
        if broken:
            report.append(f"\n## 🚨 {len(broken)} Tests Now Failing\n")
            for delta in broken[:5]:  # Show max 5
                report.append(f"- {delta.component}: {delta.test_name}\n")
            if len(broken) > 5:
                report.append(f"- ...and {len(broken) - 5} more\n")
        
        # Current failures
        failures = self._get_current_failures(results)
        if failures:
            report.append(f"\n## 📊 Total Failures: {len(failures)}\n")
            for component, tests in failures.items():
                if tests:
                    report.append(f"- **{component}**: {len(tests)} failures\n")
        
        return "".join(report)
    
    def _all_passing(self, results: Dict) -> bool:
        """Check if all tests are passing."""
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                if results[component].get("status") not in ["passed", "skipped"]:
                    return False
        return True
    
    def _get_current_failures(self, results: Dict) -> Dict[str, List[str]]:
        """Get all currently failing tests."""
        failures = {"backend": [], "frontend": [], "e2e": []}
        
        for component in failures:
            if component in results and "test_details" in results[component]:
                for test in results[component]["test_details"]:
                    if test["status"] == "failed":
                        failures[component].append(test["name"])
        
        return failures
    
    def save_reports(self, deltas: List[TestDelta], results: Dict):
        """Save delta and critical reports."""
        self.delta_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save delta report
        delta_content = self.generate_delta_report(deltas)
        with open(self.delta_file, 'w', encoding='utf-8') as f:
            f.write(delta_content)
        
        # Save critical report
        critical_content = self.generate_critical_report(deltas, results)
        with open(self.critical_file, 'w', encoding='utf-8') as f:
            f.write(critical_content)
    
    def get_test_trend(self, test_key: str) -> List[Dict]:
        """Get historical trend for a specific test."""
        history = self.load_history()
        if "tests" in history and test_key in history["tests"]:
            return history["tests"][test_key]["runs"]
        return []
    
    def get_flaky_tests(self, threshold: int = 2) -> List[str]:
        """Identify tests that have changed status multiple times."""
        history = self.load_history()
        flaky = []
        
        # Check if tests key exists (for compatibility)
        if "tests" not in history:
            return flaky
        
        for test_key, data in history["tests"].items():
            runs = data["runs"]
            if len(runs) < 3:
                continue
            
            # Count status changes
            changes = 0
            for i in range(1, len(runs)):
                if runs[i]["status"] != runs[i-1]["status"]:
                    changes += 1
            
            if changes >= threshold:
                flaky.append(test_key)
        
        return flaky