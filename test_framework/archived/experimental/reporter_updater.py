#!/usr/bin/env python
"""Test results updater module."""

from datetime import datetime
from typing import Dict, List


class TestResultsUpdater:
    """Handles updating test results data."""
    
    @staticmethod
    def determine_status(results: Dict, exit_code: int) -> str:
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
    
    @staticmethod
    def update_known_counts(test_results: Dict, level: str, results: Dict):
        """Update persistent known test counts."""
        for component in ["backend", "frontend", "e2e"]:
            if component in results:
                counts = results[component].get("test_counts", {})
                total = counts.get("total", 0)
                
                # Only update if we got valid counts
                if total > 0:
                    key = f"{level}:{component}"
                    test_results["known_test_counts"][key] = {
                        "total": total,
                        "passed": counts.get("passed", 0),
                        "failed": counts.get("failed", 0),
                        "skipped": counts.get("skipped", 0),
                        "errors": counts.get("errors", 0),
                        "last_update": datetime.now().isoformat()
                    }
    
    @staticmethod
    def update_category_results(test_results: Dict, level: str, results: Dict, categories: Dict):
        """Update results for each test category."""
        # Initialize all categories if not present
        for category, info in categories.items():
            if category not in test_results["category_results"]:
                test_results["category_results"][category] = {
                    "description": info["description"],
                    "expected": info["expected"],
                    "actual": 0,
                    "passed": 0,
                    "failed": 0,
                    "last_run": None,
                    "status": "[NOT RUN]"
                }
        
        # Update based on current run
        if level in categories:
            cat_result = test_results["category_results"][level]
            
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
    
    @staticmethod
    def update_component_results(test_results: Dict, results: Dict):
        """Update component-level results."""
        for component in ["backend", "frontend", "e2e"]:
            if component not in test_results["component_results"]:
                test_results["component_results"][component] = {
                    "status": "unknown",
                    "last_counts": {},
                    "last_duration": 0,
                    "last_run": None
                }
            
            if component in results:
                data = results[component]
                comp_result = test_results["component_results"][component]
                
                comp_result["status"] = data.get("status", "unknown")
                comp_result["last_counts"] = data.get("test_counts", {})
                comp_result["last_duration"] = data.get("duration", 0)
                comp_result["last_run"] = datetime.now().isoformat()
                
                # Add frontend-specific metrics
                if component == "frontend" and "test_metrics" in data:
                    comp_result["metrics"] = data["test_metrics"]
                    # Add additional frontend insights
                    if "import_errors" in data["test_metrics"]:
                        comp_result["import_error_count"] = len(data["test_metrics"]["import_errors"])
                    if "test_categories" in data["test_metrics"]:
                        comp_result["category_count"] = len(data["test_metrics"]["test_categories"])
                        comp_result["test_file_count"] = data["test_metrics"]["total_test_files"]
    
    @staticmethod
    def update_failing_tests(test_results: Dict, results: Dict):
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
        
        test_results["failing_tests"] = unique_failing
    
    @staticmethod
    def update_statistics(test_results: Dict, results: Dict):
        """Update overall statistics."""
        stats = test_results["statistics"]
        
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
        for key, counts in test_results["known_test_counts"].items():
            known_total = max(known_total, counts.get("total", 0))
        stats["total_tests_known"] = known_total
    
    @staticmethod
    def add_to_history(test_results: Dict, level: str, exit_code: int, timestamp: str):
        """Add current run to history."""
        history_entry = {
            "timestamp": timestamp,
            "level": level,
            "exit_code": exit_code,
            "status": test_results["current_state"]["overall_status"],
            "statistics": test_results["statistics"].copy()
        }
        
        # Keep only last 20 runs
        test_results["test_history"].append(history_entry)
        test_results["test_history"] = test_results["test_history"][-20:]