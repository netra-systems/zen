"""Bad Test Detector - Tracks consistently failing tests across runs.

This module monitors test failures over time to identify consistently 
failing tests that may need to be fixed or removed.
"""

import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BadTestDetector:
    """Detects and tracks consistently failing tests."""
    
    def __init__(self, data_file: Path = None):
        """Initialize the bad test detector.
        
        Args:
            data_file: Path to persist failure data (defaults to test_reports/bad_tests.json)
        """
        self.data_file = data_file or self._get_default_data_file()
        self.failure_data = self._load_failure_data()
        self.current_run_id = self._generate_run_id()
        self.current_run_failures = defaultdict(list)
    
    def _get_default_data_file(self) -> Path:
        """Get default data file path."""
        # Using dedicated bad_tests.json file as per specification
        reports_dir = Path(__file__).parent.parent / "test_reports"
        reports_dir.mkdir(exist_ok=True)
        return reports_dir / "bad_tests.json"
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 100000}"
    
    def _load_failure_data(self) -> Dict:
        """Load existing failure data from file."""
        if not self.data_file.exists():
            return self._create_empty_data_structure()
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return self._validate_data_structure(data)
        except (json.JSONDecodeError, IOError):
            return self._create_empty_data_structure()
    
    def _create_empty_data_structure(self) -> Dict:
        """Create empty data structure."""
        return {
            "version": "1.0",
            "tests": {},
            "runs": [],
            "stats": {
                "total_runs": 0,
                "last_updated": None
            }
        }
    
    def _validate_data_structure(self, data: Dict) -> Dict:
        """Validate and fix data structure if needed."""
        required_keys = ["version", "tests", "runs", "stats"]
        for key in required_keys:
            if key not in data:
                if key == "version":
                    data[key] = "1.0"
                elif key == "tests":
                    data[key] = {}
                elif key == "runs":
                    data[key] = []
                elif key == "stats":
                    data[key] = {"total_runs": 0, "last_updated": None}
        return data
    
    def record_test_result(self, test_name: str, component: str, 
                          status: str, error_type: str = None,
                          error_message: str = None):
        """Record a single test result.
        
        Args:
            test_name: Full test name (e.g., "app/tests/test_auth.py::TestAuth::test_login")
            component: Component (backend/frontend/e2e)
            status: Test status (passed/failed/skipped/error)
            error_type: Type of error if failed
            error_message: Error message if failed
        """
        if status == "failed":
            self._record_failure(test_name, component, error_type, error_message)
        elif status == "passed":
            self._record_pass(test_name, component)
    
    def _record_failure(self, test_name: str, component: str, 
                       error_type: str, error_message: str):
        """Record a test failure."""
        if test_name not in self.failure_data["tests"]:
            self.failure_data["tests"][test_name] = self._create_test_entry(component)
        
        test_data = self.failure_data["tests"][test_name]
        test_data["total_failures"] += 1
        test_data["consecutive_failures"] += 1
        test_data["last_failure"] = datetime.now().isoformat()
        
        # Record failure details
        failure_detail = {
            "run_id": self.current_run_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message[:500] if error_message else None
        }
        
        # Keep only last 10 failure details
        test_data["recent_failures"].append(failure_detail)
        test_data["recent_failures"] = test_data["recent_failures"][-10:]
        
        # Track current run failures
        self.current_run_failures[test_name].append(failure_detail)
    
    def _record_pass(self, test_name: str, component: str):
        """Record a test pass."""
        if test_name not in self.failure_data["tests"]:
            return  # No need to track if never failed
        
        test_data = self.failure_data["tests"][test_name]
        test_data["consecutive_failures"] = 0
        test_data["last_pass"] = datetime.now().isoformat()
        test_data["total_passes"] += 1
    
    def _create_test_entry(self, component: str) -> Dict:
        """Create a new test entry."""
        return {
            "component": component,
            "first_seen": datetime.now().isoformat(),
            "last_failure": None,
            "last_pass": None,
            "total_failures": 0,
            "total_passes": 0,
            "consecutive_failures": 0,
            "recent_failures": [],
            "marked_as_bad": False,
            "bad_reason": None
        }
    
    def finalize_run(self, total_tests: int = 0, passed: int = 0, 
                     failed: int = 0) -> Dict:
        """Finalize the current test run and save data.
        
        Args:
            total_tests: Total number of tests run
            passed: Number of tests passed
            failed: Number of tests failed
            
        Returns:
            Summary of bad tests detected
        """
        # Record run stats
        run_stats = {
            "run_id": self.current_run_id,
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "bad_tests_count": len(self.current_run_failures)
        }
        
        self.failure_data["runs"].append(run_stats)
        self.failure_data["runs"] = self.failure_data["runs"][-100:]  # Keep last 100 runs
        
        # Update stats
        self.failure_data["stats"]["total_runs"] += 1
        self.failure_data["stats"]["last_updated"] = datetime.now().isoformat()
        
        # Identify bad tests
        bad_tests = self._identify_bad_tests()
        
        # Save data
        self._save_failure_data()
        
        return bad_tests
    
    def _identify_bad_tests(self) -> Dict:
        """Identify tests that should be marked as bad.
        
        A test is considered bad if:
        - It has failed 5+ times consecutively
        - It has failed in 80% of the last 10 runs it was present
        - It has a high failure rate (>70%) overall with 10+ failures
        """
        bad_tests = {
            "consistently_failing": [],
            "high_failure_rate": [],
            "recent_failures": [],
            "recommended_for_fix": [],
            "recommended_for_deletion": []
        }
        
        for test_name, test_data in self.failure_data["tests"].items():
            failure_rate = self._calculate_failure_rate(test_data)
            
            # Consistently failing (5+ consecutive)
            if test_data["consecutive_failures"] >= 5:
                bad_tests["consistently_failing"].append({
                    "test": test_name,
                    "consecutive_failures": test_data["consecutive_failures"],
                    "component": test_data["component"]
                })
                bad_tests["recommended_for_fix"].append(test_name)
            
            # High failure rate (70% failure with 10+ total runs)
            total_runs = test_data["total_failures"] + test_data["total_passes"]
            if failure_rate > 0.7 and total_runs >= 10:
                bad_tests["high_failure_rate"].append({
                    "test": test_name,
                    "failure_rate": failure_rate,
                    "total_runs": total_runs,
                    "total_failures": test_data["total_failures"],
                    "component": test_data["component"]
                })
                
                # If very high failure rate (90%+), recommend deletion
                if failure_rate >= 0.9:
                    bad_tests["recommended_for_deletion"].append(test_name)
            
            # Recent failures (failed in last run)
            if test_name in self.current_run_failures:
                bad_tests["recent_failures"].append({
                    "test": test_name,
                    "error": self.current_run_failures[test_name][-1]["error_type"],
                    "component": test_data["component"]
                })
        
        return bad_tests
    
    def _calculate_failure_rate(self, test_data: Dict) -> float:
        """Calculate failure rate for a test."""
        total = test_data["total_failures"] + test_data["total_passes"]
        if total == 0:
            return 0.0
        return test_data["total_failures"] / total
    
    def _save_failure_data(self):
        """Save failure data to file."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.failure_data, f, indent=2, default=str)
        except IOError as e:
            print(f"[WARNING] Could not save bad test data: {e}")
    
    def get_bad_test_report(self) -> str:
        """Generate a human-readable bad test report.
        
        Returns:
            Formatted report string
        """
        bad_tests = self._identify_bad_tests()
        report_lines = ["", "=" * 80, "BAD TEST DETECTION REPORT", "=" * 80]
        
        # Summary
        total_bad = len(set(
            [t["test"] for t in bad_tests["consistently_failing"]] +
            [t["test"] for t in bad_tests["high_failure_rate"]]
        ))
        
        report_lines.append(f"\nTotal Bad Tests Detected: {total_bad}")
        report_lines.append(f"Total Test Runs Analyzed: {self.failure_data['stats']['total_runs']}")
        
        # Consistently failing tests
        if bad_tests["consistently_failing"]:
            report_lines.extend([
                "\n" + "=" * 40,
                "CONSISTENTLY FAILING TESTS",
                "=" * 40
            ])
            for test in bad_tests["consistently_failing"]:
                report_lines.append(
                    f"  [U+2022] {test['test']}\n"
                    f"    Consecutive Failures: {test['consecutive_failures']}\n"
                    f"    Component: {test['component']}"
                )
        
        # High failure rate tests
        if bad_tests["high_failure_rate"]:
            report_lines.extend([
                "\n" + "=" * 40,
                "HIGH FAILURE RATE TESTS",
                "=" * 40
            ])
            for test in bad_tests["high_failure_rate"]:
                report_lines.append(
                    f"  [U+2022] {test['test']}\n"
                    f"    Failure Rate: {test['failure_rate']:.1%}\n"
                    f"    Total Failures: {test['total_failures']}\n"
                    f"    Component: {test['component']}"
                )
        
        # Recommendations
        if bad_tests["recommended_for_fix"]:
            report_lines.extend([
                "\n" + "=" * 40,
                "RECOMMENDED FOR IMMEDIATE FIX",
                "=" * 40
            ])
            for test in bad_tests["recommended_for_fix"]:
                report_lines.append(f"  [U+2022] {test}")
        
        if bad_tests["recommended_for_deletion"]:
            report_lines.extend([
                "\n" + "=" * 40,
                "RECOMMENDED FOR DELETION/REWRITE",
                "=" * 40
            ])
            for test in bad_tests["recommended_for_deletion"]:
                report_lines.append(f"  [U+2022] {test}")
        
        report_lines.append("\n" + "=" * 80 + "\n")
        return "\n".join(report_lines)
    
    def get_test_history(self, test_name: str) -> Optional[Dict]:
        """Get detailed history for a specific test.
        
        Args:
            test_name: Full test name
            
        Returns:
            Test history data or None if not found
        """
        return self.failure_data["tests"].get(test_name)
    
    def reset_test_data(self, test_name: str = None):
        """Reset failure data for a specific test or all tests.
        
        Args:
            test_name: Test to reset (None to reset all)
        """
        if test_name:
            if test_name in self.failure_data["tests"]:
                del self.failure_data["tests"][test_name]
        else:
            self.failure_data["tests"] = {}
        
        self._save_failure_data()
    
    def get_statistics(self) -> Dict:
        """Get overall statistics about test failures.
        
        Returns:
            Dictionary with statistics
        """
        total_tests = len(self.failure_data["tests"])
        bad_tests = self._identify_bad_tests()
        
        return {
            "total_tracked_tests": total_tests,
            "total_runs": self.failure_data["stats"]["total_runs"],
            "consistently_failing": len(bad_tests["consistently_failing"]),
            "high_failure_rate": len(bad_tests["high_failure_rate"]),
            "last_updated": self.failure_data["stats"]["last_updated"],
            "fake_tests_detected": self.get_fake_tests_count()
        }
    
    def get_fake_tests_count(self) -> int:
        """Get count of fake tests detected in current run.
        
        Returns:
            Number of fake tests detected
        """
        try:
            from test_framework.archived.duplicates.fake_test_detector import FakeTestDetector
            # This would be set by the test runner when fake tests are detected
            return getattr(self, '_fake_tests_count', 0)
        except ImportError:
            return 0
    
    def set_fake_tests_count(self, count: int):
        """Set the fake tests count for current run.
        
        Args:
            count: Number of fake tests detected
        """
        self._fake_tests_count = count