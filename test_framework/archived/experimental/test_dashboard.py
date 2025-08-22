#!/usr/bin/env python
"""
Test Dashboard Viewer - Display test results from the single authoritative file.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class TestDashboard:
    """Display test results from the single test_results.json file."""
    
    def __init__(self):
        self.results_file = Path(__file__).parent.parent / "test_reports" / "test_results.json"
    
    def load_results(self) -> Optional[Dict]:
        """Load test results from file."""
        if not self.results_file.exists():
            print(f"[ERROR] No test results found at {self.results_file}")
            return None
        
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Error loading test results: {e}")
            return None
    
    def display_dashboard(self):
        """Display the complete test dashboard."""
        results = self.load_results()
        if not results:
            return
        
        self._display_header(results)
        self._display_current_state(results)
        self._display_statistics(results)
        self._display_components(results)
        self._display_categories(results)
        self._display_failing_tests(results)
        self._display_recent_history(results)
    
    def _display_header(self, results: Dict):
        """Display dashboard header."""
        print("\n" + "="*80)
        print("                      TEST RESULTS DASHBOARD")
        print("="*80)
        
        meta = results.get("metadata", {})
        print(f"Version: {meta.get('version', 'unknown')}")
        print(f"Last Update: {meta.get('last_update', 'never')}")
        print(f"Total Runs: {meta.get('total_runs', 0)}")
        print("="*80)
    
    def _display_current_state(self, results: Dict):
        """Display current test state."""
        state = results.get("current_state", {})
        print("\n[CURRENT STATE]")
        print("-"*40)
        print(f"Overall Status: {state.get('overall_status', 'unknown')}")
        print(f"Last Run Level: {state.get('last_run_level', 'none')}")
        print(f"Last Run Time: {state.get('last_run_time', 'never')}")
        print(f"Last Exit Code: {state.get('last_exit_code', 'N/A')}")
    
    def _display_statistics(self, results: Dict):
        """Display test statistics."""
        stats = results.get("statistics", {})
        print("\n[STATISTICS]")
        print("-"*40)
        print(f"Known Tests: {stats.get('total_tests_known', 0)}")
        print(f"Tests Run: {stats.get('total_tests_run', 0)}")
        print(f"Passed: {stats.get('total_passed', 0)}")
        print(f"Failed: {stats.get('total_failed', 0)}")
        print(f"Skipped: {stats.get('total_skipped', 0)}")
        print(f"Pass Rate: {stats.get('pass_rate', 0.0)}%")
    
    def _display_components(self, results: Dict):
        """Display component results."""
        components = results.get("component_results", {})
        if not components:
            return
        
        print("\n[COMPONENT RESULTS]")
        print("-"*40)
        print(f"{'Component':<12} {'Status':<12} {'Tests':<8} {'Passed':<8} {'Failed':<8} {'Duration':<10}")
        print("-"*70)
        
        for name, data in components.items():
            counts = data.get("last_counts", {})
            status = data.get("status", "unknown")[:10]
            total = counts.get("total", 0)
            passed = counts.get("passed", 0)
            failed = counts.get("failed", 0)
            duration = f"{data.get('last_duration', 0):.1f}s"
            
            print(f"{name.upper():<12} {status:<12} {total:<8} {passed:<8} {failed:<8} {duration:<10}")
    
    def _display_categories(self, results: Dict):
        """Display category results."""
        categories = results.get("category_results", {})
        if not categories:
            return
        
        print("\n[CATEGORY RESULTS]")
        print("-"*40)
        print(f"{'Category':<15} {'Expected':<10} {'Actual':<10} {'Status':<20} {'Last Run':<20}")
        print("-"*75)
        
        for name, data in sorted(categories.items()):
            expected = data.get("expected", 0)
            actual = data.get("actual", 0)
            status = data.get("status", "[NOT RUN]")
            last_run = data.get("last_run", None)
            if last_run and last_run != "never":
                try:
                    dt = datetime.fromisoformat(last_run)
                    last_run = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    last_run = "never"
            else:
                last_run = "never"
            
            print(f"{name:<15} {expected:<10} {actual:<10} {status:<20} {last_run:<20}")
    
    def _display_failing_tests(self, results: Dict):
        """Display failing tests."""
        failing = results.get("failing_tests", [])
        if not failing:
            print("\n[PASS] No failing tests!")
            return
        
        print(f"\n[FAILING TESTS] ({len(failing)})")
        print("-"*40)
        
        for item in failing[:10]:  # Show first 10
            component = item.get("component", "unknown")
            test = item.get("test", "unknown")
            print(f"  [{component.upper()}] {test}")
        
        if len(failing) > 10:
            print(f"  ... and {len(failing) - 10} more")
    
    def _display_recent_history(self, results: Dict):
        """Display recent test history."""
        history = results.get("test_history", [])
        if not history:
            return
        
        print("\n[RECENT HISTORY] (last 5 runs)")
        print("-"*40)
        print(f"{'Time':<20} {'Level':<15} {'Status':<25} {'Pass Rate':<10}")
        print("-"*70)
        
        for entry in history[-5:]:
            timestamp = entry.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            
            level = entry.get("level", "unknown")
            status = entry.get("status", "unknown")
            stats = entry.get("statistics", {})
            pass_rate = f"{stats.get('pass_rate', 0):.1f}%"
            
            print(f"{timestamp:<20} {level:<15} {status:<25} {pass_rate:<10}")
    
    def display_summary(self):
        """Display a brief summary."""
        results = self.load_results()
        if not results:
            return
        
        state = results.get("current_state", {})
        stats = results.get("statistics", {})
        
        print(f"\n[TEST SUMMARY]")
        print(f"Status: {state.get('overall_status', 'unknown')}")
        print(f"Last Level: {state.get('last_run_level', 'none')}")
        print(f"Pass Rate: {stats.get('pass_rate', 0.0)}%")
        print(f"Failed: {stats.get('total_failed', 0)}")


def main():
    """Main entry point."""
    dashboard = TestDashboard()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        dashboard.display_summary()
    else:
        dashboard.display_dashboard()


if __name__ == "__main__":
    main()