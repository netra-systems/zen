"""Unified test runner class."""

import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, Optional, List, Tuple

from .test_config import TEST_LEVELS, RUNNERS
from .test_runners import (
    run_backend_tests, run_frontend_tests, run_e2e_tests, 
    run_simple_tests
)
from .failing_test_runner import run_failing_tests
from .test_parser import extract_failing_tests, parse_test_counts, parse_coverage
from .report_generators import generate_json_report, generate_text_report, generate_markdown_report
from .report_manager import save_test_report, print_summary
from .failing_tests_manager import (
    load_failing_tests, update_failing_tests, show_failing_tests, 
    clear_failing_tests, organize_failures_by_category
)

# Try to import enhanced reporter if available
try:
    from scripts.enhanced_test_reporter import EnhancedTestReporter
    ENHANCED_REPORTER_AVAILABLE = True
except ImportError:
    ENHANCED_REPORTER_AVAILABLE = False

PROJECT_ROOT = Path(__file__).parent.parent

class UnifiedTestRunner:
    """Unified test runner that manages all testing levels and report generation.
    
    RESPONSIBILITIES:
    1. Test Discovery: Find and categorize all tests
    2. Test Execution: Run tests with appropriate parallelization
    3. Result Collection: Gather and parse test outputs
    4. Report Generation: Create HTML, JSON, and markdown reports
    5. Coverage Analysis: Track code coverage against targets
    
    This class orchestrates the entire testing pipeline, making it
    easy to run appropriate tests for different scenarios.
    """
    
    def __init__(self):
        self.test_categories = defaultdict(list)  # For organizing tests by category
        
        # Initialize enhanced reporter if available
        self.enhanced_reporter = None
        if ENHANCED_REPORTER_AVAILABLE:
            try:
                self.enhanced_reporter = EnhancedTestReporter()
                print("[INFO] Enhanced Test Reporter enabled")
            except Exception as e:
                print(f"[WARNING] Could not initialize Enhanced Reporter: {e}")
        
        self.results = {
            "backend": {
                "status": "pending", 
                "duration": 0, 
                "exit_code": None, 
                "output": "",
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
                "coverage": None
            },
            "frontend": {
                "status": "pending", 
                "duration": 0, 
                "exit_code": None, 
                "output": "",
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
                "coverage": None
            },
            "e2e": {
                "status": "pending",
                "duration": 0,
                "exit_code": None,
                "output": "",
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
                "coverage": None
            },
            "overall": {"status": "pending", "start_time": None, "end_time": None}
        }
        
        # Ensure test_reports directory and history subdirectory exist
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history_dir = self.reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        
        # For staging mode support
        self.staging_mode = False
    
    def run_backend_tests(self, args: List[str], timeout: int = 300, real_llm_config: Optional[Dict] = None) -> Tuple[int, str]:
        """Run backend tests and update results."""
        exit_code, output = run_backend_tests(args, timeout, real_llm_config, self.results)
        
        # Extract and update failing tests
        if exit_code != 0:
            failures = extract_failing_tests(output, "backend")
            if failures:
                update_failing_tests("backend", failures, None, self.reports_dir)
        
        return exit_code, output
    
    def run_frontend_tests(self, args: List[str], timeout: int = 300) -> Tuple[int, str]:
        """Run frontend tests and update results."""
        exit_code, output = run_frontend_tests(args, timeout, self.results)
        
        # Extract and update failing tests
        if exit_code != 0:
            failures = extract_failing_tests(output, "frontend")
            if failures:
                update_failing_tests("frontend", failures, None, self.reports_dir)
        
        return exit_code, output
    
    def run_e2e_tests(self, args: List[str], timeout: int = 600) -> Tuple[int, str]:
        """Run e2e tests and update results."""
        exit_code, output = run_e2e_tests(args, timeout, self.results)
        
        # Extract and update failing tests
        if exit_code != 0:
            failures = extract_failing_tests(output, "e2e")
            if failures:
                update_failing_tests("e2e", failures, None, self.reports_dir)
        
        return exit_code, output
    
    def run_simple_tests(self) -> Tuple[int, str]:
        """Run simple tests and update results."""
        return run_simple_tests(self.results)
    
    def run_failing_tests(self, max_fixes: int = None, backend_only: bool = False, frontend_only: bool = False) -> int:
        """Run only the currently failing tests."""
        failing_tests = load_failing_tests(self.reports_dir)
        return run_failing_tests(failing_tests, max_fixes, backend_only, frontend_only)
    
    def save_test_report(self, level: str, config: Dict, output: str, exit_code: int):
        """Save test report to test_reports directory with latest/history structure."""
        if self.enhanced_reporter:
            success = self._try_enhanced_report(level, config, exit_code)
            if success:
                return
        
        # Use standard reporter
        save_test_report(self.results, level, config, exit_code, self.reports_dir, self.staging_mode)
    
    def _try_enhanced_report(self, level: str, config: Dict, exit_code: int) -> bool:
        """Try to use enhanced reporter, return success status."""
        try:
            report_content = self._generate_enhanced_report(level, config, exit_code)
            metrics = self._calculate_test_metrics()
            self._save_enhanced_report(level, report_content, metrics)
            self._maybe_cleanup_reports()
            return True
        except Exception as e:
            self._handle_enhanced_reporter_error(e)
            return False
    
    def _generate_enhanced_report(self, level: str, config: Dict, exit_code: int) -> str:
        """Generate comprehensive report using enhanced reporter."""
        return self.enhanced_reporter.generate_comprehensive_report(
            level=level,
            results=self.results,
            config=config,
            exit_code=exit_code
        )
    
    def _calculate_test_metrics(self) -> Dict:
        """Calculate test metrics for enhanced reporter."""
        backend_counts = self.results["backend"]["test_counts"]
        frontend_counts = self.results["frontend"]["test_counts"]
        return {
            "total_tests": backend_counts["total"] + frontend_counts["total"],
            "passed": backend_counts["passed"] + frontend_counts["passed"],
            "failed": backend_counts["failed"] + frontend_counts["failed"],
            "coverage": self.results["backend"].get("coverage") or self.results["frontend"].get("coverage")
        }
    
    def _save_enhanced_report(self, level: str, report_content: str, metrics: Dict):
        """Save report using enhanced reporter."""
        self.enhanced_reporter.save_report(
            level=level,
            report_content=report_content,
            results=self.results,
            metrics=metrics
        )
    
    def _maybe_cleanup_reports(self):
        """Periodically cleanup old reports."""
        import random
        if random.random() < 0.1:  # 10% chance to run cleanup
            print("[INFO] Running report cleanup...")
            self.enhanced_reporter.cleanup_old_reports(keep_days=7)
    
    def _handle_enhanced_reporter_error(self, e: Exception):
        """Handle enhanced reporter errors gracefully."""
        error_msg = str(e)
        try:
            print(f"[WARNING] Enhanced reporter failed, using standard: {error_msg}")
        except UnicodeEncodeError:
            safe_msg = error_msg.encode('ascii', 'replace').decode('ascii')
            print(f"[WARNING] Enhanced reporter failed, using standard: {safe_msg}")
    
    def generate_json_report(self, level: str, config: Dict, exit_code: int) -> Dict:
        """Generate JSON report for CI/CD integration."""
        return generate_json_report(self.results, level, config, exit_code, self.staging_mode)
    
    def generate_text_report(self, level: str, config: Dict, exit_code: int) -> str:
        """Generate text report."""
        return generate_text_report(self.results, level, config, exit_code, self.staging_mode)
    
    def print_summary(self):
        """Print final test summary with test counts."""
        print_summary(self.results)
    
    def show_failing_tests(self):
        """Display currently failing tests."""
        show_failing_tests(self.reports_dir)
    
    def clear_failing_tests(self):
        """Clear the failing tests log."""
        clear_failing_tests(self.reports_dir)