#!/usr/bin/env python
"""
SINGLE AUTHORITATIVE TEST REPORTER - All test results in ONE file.
No legacy reports, no confusion, just clarity.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict


class ComprehensiveTestReporter:
    """Single source of truth for ALL test reporting."""
    
    # ALL test levels from test_config.py
    TEST_LEVELS = [
        "smoke", "unit", "agents", "integration", "critical",
        "comprehensive", "comprehensive-backend", "comprehensive-frontend",
        "comprehensive-core", "comprehensive-agents", "comprehensive-websocket",
        "comprehensive-database", "comprehensive-api", "all",
        "real_e2e", "real_services", "mock_only"
    ]
    
    # Complete test category mapping with expected counts
    TEST_CATEGORIES = {
        "smoke": {"description": "Quick smoke tests", "expected": 10},
        "unit": {"description": "Unit tests", "expected": 450},
        "integration": {"description": "Integration tests", "expected": 60},
        "critical": {"description": "Critical path tests", "expected": 20},
        "agents": {"description": "Agent tests", "expected": 45},
        "websocket": {"description": "WebSocket tests", "expected": 25},
        "database": {"description": "Database tests", "expected": 35},
        "api": {"description": "API tests", "expected": 50},
        "e2e": {"description": "End-to-end tests", "expected": 20},
        "real_services": {"description": "Real service tests", "expected": 15},
        "auth": {"description": "Authentication tests", "expected": 30},
        "corpus": {"description": "Corpus management tests", "expected": 20},
        "synthetic_data": {"description": "Synthetic data tests", "expected": 25},
        "metrics": {"description": "Metrics tests", "expected": 15},
        "frontend": {"description": "Frontend tests", "expected": 40},
        "comprehensive": {"description": "Full comprehensive suite", "expected": 500}
    }
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)
        
        # SINGLE authoritative results file
        self.results_file = reports_dir / "test_results.json"
        
        # Load or initialize test results
        self.test_results = self._load_test_results()
    
    def _load_test_results(self) -> Dict:
        """Load the single test results file."""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Initialize with complete structure
        return {
            "metadata": {
                "version": "2.0",
                "last_update": None,
                "total_runs": 0
            },
            "current_state": {
                "overall_status": "unknown",
                "last_run_level": None,
                "last_run_time": None,
                "last_exit_code": None
            },
            "known_test_counts": {},  # Persistent test counts by level/component
            "category_results": {},    # Results by category
            "component_results": {},   # Results by component (backend/frontend/e2e)
            "failing_tests": [],       # Currently failing tests
            "test_history": [],        # Last 20 runs
            "statistics": {
                "total_tests_known": 0,
                "total_tests_run": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_skipped": 0,
                "pass_rate": 0.0
            }
        }
    
    def generate_comprehensive_report(self, 
                                     level: str, 
                                     results: Dict,
                                     config: Dict,
                                     exit_code: int) -> None:
        """Generate and save the SINGLE comprehensive test report."""
        
        timestamp = datetime.now().isoformat()
        
        # Update metadata
        self.test_results["metadata"]["last_update"] = timestamp
        self.test_results["metadata"]["total_runs"] += 1
        
        # Update current state
        self.test_results["current_state"]["overall_status"] = self._determine_status(results, exit_code)
        self.test_results["current_state"]["last_run_level"] = level
        self.test_results["current_state"]["last_run_time"] = timestamp
        self.test_results["current_state"]["last_exit_code"] = exit_code
        
        # Update known test counts (persistent)
        self._update_known_counts(level, results)
        
        # Update category results
        self._update_category_results(level, results)
        
        # Update component results
        self._update_component_results(results)
        
        # Update failing tests
        self._update_failing_tests(results)
        
        # Update statistics
        self._update_statistics(results)
        
        # Add to history
        self._add_to_history(level, results, exit_code, timestamp)
        
        # Save the single file
        self._save_results()
    
    def _determine_status(self, results: Dict, exit_code: int) -> str:
        """Determine overall test status."""
        if exit_code == 0:
            return "[PASSED]"
        
        total_failed = 0
        total_errors = 0
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                counts = results[component].get("test_counts", {})
                total_failed += counts.get("failed", 0)
                total_errors += counts.get("errors", 0)
        
        if total_failed > 0:
            return f"[FAILED] {total_failed} failures"
        elif total_errors > 0:
            return f"[ERRORS] {total_errors} errors"
        else:
            return "[UNKNOWN]"
    
    def _update_known_counts(self, level: str, results: Dict):
        """Update persistent known test counts."""
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                counts = results[component].get("test_counts", {})
                total = counts.get("total", 0)
                
                # Only update if we got valid counts
                if total > 0:
                    key = f"{level}:{component}"
                    self.test_results["known_test_counts"][key] = {
                        "total": total,
                        "passed": counts.get("passed", 0),
                        "failed": counts.get("failed", 0),
                        "skipped": counts.get("skipped", 0),
                        "errors": counts.get("errors", 0),
                        "last_update": datetime.now().isoformat()
                    }
    
    def _update_category_results(self, level: str, results: Dict):
        """Update results for each test category."""
        # Initialize all categories if not present
        for category, info in self.TEST_CATEGORIES.items():
            if category not in self.test_results["category_results"]:
                self.test_results["category_results"][category] = {
                    "description": info["description"],
                    "expected": info["expected"],
                    "actual": 0,
                    "passed": 0,
                    "failed": 0,
                    "last_run": None,
                    "status": "[NOT RUN]"
                }
        
        # Update based on current run
        # For now, we'll map level to categories (this can be enhanced)
        if level in self.TEST_CATEGORIES:
            cat_result = self.test_results["category_results"][level]
            
            # Calculate totals from all components
            total = 0
            passed = 0
            failed = 0
            
            for component in ["backend", "frontend", "e2e"]:
                if component in results:
                    counts = results[component].get("test_counts", {})
                    total += counts.get("total", 0)
                    passed += counts.get("passed", 0)
                    failed += counts.get("failed", 0)
            
            cat_result["actual"] = total
            cat_result["passed"] = passed
            cat_result["failed"] = failed
            cat_result["last_run"] = datetime.now().isoformat()
            
            if failed > 0:
                cat_result["status"] = f"[FAILED] {failed} failures"
            elif passed > 0:
                cat_result["status"] = f"[PASSED] {passed} tests"
            else:
                cat_result["status"] = "[NO TESTS]"
    
    def _update_component_results(self, results: Dict):
        """Update component-level results."""
        for component in ["backend", "frontend", "e2e"]:
            if component not in self.test_results["component_results"]:
                self.test_results["component_results"][component] = {
                    "status": "unknown",
                    "last_counts": {},
                    "last_duration": 0,
                    "last_run": None
                }
            
            if component in results:
                data = results[component]
                comp_result = self.test_results["component_results"][component]
                
                comp_result["status"] = data.get("status", "unknown")
                comp_result["last_counts"] = data.get("test_counts", {})
                comp_result["last_duration"] = data.get("duration", 0)
                comp_result["last_run"] = datetime.now().isoformat()
    
    def _update_failing_tests(self, results: Dict):
        """Update list of currently failing tests."""
        failing = []
        
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                output = results[component].get("output", "")
                
                # Parse output for failing test names
                for line in output.split('\n'):
                    if "FAILED" in line and "::" in line:
                        # Extract test name
                        parts = line.split("FAILED")[-1].strip()
                        if parts:
                            failing.append({
                                "component": component,
                                "test": parts,
                                "timestamp": datetime.now().isoformat()
                            })
        
        # Keep only unique failures
        seen = set()
        unique_failing = []
        for item in failing:
            key = f"{item['component']}:{item['test']}"
            if key not in seen:
                seen.add(key)
                unique_failing.append(item)
        
        self.test_results["failing_tests"] = unique_failing
    
    def _update_statistics(self, results: Dict):
        """Update overall statistics."""
        stats = self.test_results["statistics"]
        
        # Calculate totals
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                counts = results[component].get("test_counts", {})
                total += counts.get("total", 0)
                passed += counts.get("passed", 0)
                failed += counts.get("failed", 0)
                skipped += counts.get("skipped", 0)
        
        stats["total_tests_run"] = total
        stats["total_passed"] = passed
        stats["total_failed"] = failed
        stats["total_skipped"] = skipped
        
        # Calculate pass rate
        if total > 0:
            stats["pass_rate"] = round((passed / total) * 100, 2)
        else:
            stats["pass_rate"] = 0.0
        
        # Update known total from all known counts
        known_total = 0
        for key, counts in self.test_results["known_test_counts"].items():
            known_total = max(known_total, counts.get("total", 0))
        stats["total_tests_known"] = known_total
    
    def _add_to_history(self, level: str, results: Dict, exit_code: int, timestamp: str):
        """Add current run to history."""
        history_entry = {
            "timestamp": timestamp,
            "level": level,
            "exit_code": exit_code,
            "status": self.test_results["current_state"]["overall_status"],
            "statistics": self.test_results["statistics"].copy()
        }
        
        # Keep only last 20 runs
        self.test_results["test_history"].append(history_entry)
        self.test_results["test_history"] = self.test_results["test_history"][-20:]
    
    def _save_results(self):
        """Save the single test results file."""
        with open(self.results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
    
    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard display."""
        return self.test_results
    
    def cleanup_old_reports(self, keep_days: int = 7):
        """Clean up old report files - NO LONGER NEEDED."""
        # Delete all legacy report files
        legacy_files = [
            "dashboard.md", "summary.md", "test_state.json", 
            "test_history.json", "bad_tests.json"
        ]
        
        for filename in legacy_files:
            file_path = self.reports_dir / filename
            if file_path.exists():
                file_path.unlink()
        
        # Delete latest directory
        latest_dir = self.reports_dir / "latest"
        if latest_dir.exists():
            import shutil
            shutil.rmtree(latest_dir)