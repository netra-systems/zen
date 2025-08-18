"""Pytest plugin for bad test detection.

This plugin integrates with pytest to track test failures and identify
consistently failing tests.
"""

import pytest
from pathlib import Path
from typing import Optional
from .bad_test_detector import BadTestDetector


class BadTestPlugin:
    """Pytest plugin for bad test detection."""
    
    def __init__(self):
        """Initialize the plugin."""
        self.detector = None
        self.component = "backend"  # Default component
        self.enabled = True
        self.verbose = False
    
    def initialize(self, config):
        """Initialize the detector with pytest config.
        
        Args:
            config: Pytest config object
        """
        # Bad test detection is now disabled - using single test_results.json
        self.enabled = False
        return
    
    def _get_data_file(self, config) -> Optional[Path]:
        """Get data file path from config.
        
        Args:
            config: Pytest config
            
        Returns:
            Path to data file
        """
        if hasattr(config.option, 'bad_test_data_file') and config.option.bad_test_data_file:
            return Path(config.option.bad_test_data_file)
        # Default to test_reports/test_results.json (single source of truth)
        return Path("test_reports/test_results.json")
    
    def record_test_outcome(self, nodeid: str, outcome: str, 
                           longrepr=None):
        """Record test outcome.
        
        Args:
            nodeid: Test node ID
            outcome: Test outcome (passed/failed/skipped)
            longrepr: Long representation of failure
        """
        if not self.enabled or not self.detector:
            return
        
        error_type = None
        error_message = None
        
        if outcome == "failed" and longrepr:
            error_type, error_message = self._extract_error_info(longrepr)
        
        self.detector.record_test_result(
            test_name=nodeid,
            component=self.component,
            status=outcome,
            error_type=error_type,
            error_message=error_message
        )
    
    def _extract_error_info(self, longrepr) -> tuple:
        """Extract error type and message from failure.
        
        Args:
            longrepr: Long representation of failure
            
        Returns:
            Tuple of (error_type, error_message)
        """
        try:
            if hasattr(longrepr, 'reprcrash'):
                message = longrepr.reprcrash.message
                # Extract error type from message
                if "AssertionError" in message:
                    return "AssertionError", message
                elif "ImportError" in message:
                    return "ImportError", message
                elif "AttributeError" in message:
                    return "AttributeError", message
                elif "TypeError" in message:
                    return "TypeError", message
                elif "ValueError" in message:
                    return "ValueError", message
                else:
                    return "Error", message
            return "Error", str(longrepr)[:500]
        except:
            return "Error", "Unknown error"
    
    def finalize(self, session):
        """Finalize the test run and generate report.
        
        Args:
            session: Pytest session
        """
        if not self.enabled or not self.detector:
            return
        
        # Get test statistics
        total = session.testscollected
        passed = len([i for i in session.items if i.stash.get(
            pytest.StashKey[bool](), False)])
        failed = session.testsfailed
        
        # Finalize run and get bad tests
        bad_tests = self.detector.finalize_run(
            total_tests=total,
            passed=total - failed,
            failed=failed
        )
        
        # Print report if verbose or bad tests found
        if self.verbose or self._has_bad_tests(bad_tests):
            report = self.detector.get_bad_test_report()
            print(report)
        
        # Print summary
        stats = self.detector.get_statistics()
        if stats["consistently_failing"] > 0:
            print(f"\n⚠️  WARNING: {stats['consistently_failing']} tests are consistently failing!")
            print("Run 'python -m test_framework.bad_test_reporter' for detailed report")
    
    def _has_bad_tests(self, bad_tests: dict) -> bool:
        """Check if there are any bad tests.
        
        Args:
            bad_tests: Bad tests dictionary
            
        Returns:
            True if bad tests exist
        """
        return bool(
            bad_tests["consistently_failing"] or 
            bad_tests["high_failure_rate"]
        )


# Plugin instance
_plugin = BadTestPlugin()


def pytest_addoption(parser):
    """Add command line options."""
    group = parser.getgroup("bad test detection")
    group.addoption(
        "--no-bad-test-detection",
        action="store_true",
        default=False,
        help="Disable bad test detection"
    )
    group.addoption(
        "--bad-test-data-file",
        action="store",
        default=None,
        help="Path to bad test data file"
    )
    group.addoption(
        "--test-component",
        action="store",
        default="backend",
        choices=["backend", "frontend", "e2e"],
        help="Component being tested"
    )


def pytest_configure(config):
    """Configure the plugin."""
    _plugin.initialize(config)


def pytest_runtest_logreport(report):
    """Hook to capture test results."""
    if report.when == "call":
        _plugin.record_test_outcome(
            nodeid=report.nodeid,
            outcome=report.outcome,
            longrepr=report.longrepr
        )


def pytest_sessionfinish(session, exitstatus):
    """Hook called after whole test run finishes."""
    _plugin.finalize(session)


# Markers for bad tests
def pytest_collection_modifyitems(config, items):
    """Mark tests that are known to be bad."""
    if _plugin.enabled and _plugin.detector:
        for item in items:
            test_history = _plugin.detector.get_test_history(item.nodeid)
            if test_history:
                # Add marker for consistently failing tests
                if test_history.get("consecutive_failures", 0) >= 5:
                    item.add_marker(pytest.mark.bad_test(
                        reason=f"Failed {test_history['consecutive_failures']} times consecutively"
                    ))
                
                # Add marker for high failure rate
                total = test_history["total_failures"] + test_history["total_passes"]
                if total > 0:
                    failure_rate = test_history["total_failures"] / total
                    if failure_rate > 0.7:
                        item.add_marker(pytest.mark.flaky(
                            reason=f"Failure rate: {failure_rate:.1%}"
                        ))