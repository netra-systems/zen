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
        self.test_categories = defaultdict(list)
        self.enhanced_reporter = self._setup_enhanced_reporter()
        self.results = self._initialize_results_structure()
        self._setup_directories()
        self.staging_mode = False
    
    def run_backend_tests(self, args: List[str], timeout: int = 300, real_llm_config: Optional[Dict] = None) -> Tuple[int, str]:
        """Run backend tests and update results."""
        exit_code, output = run_backend_tests(args, timeout, real_llm_config, self.results)
        self._handle_test_failures(exit_code, output, "backend")
        return exit_code, output
    
    def run_frontend_tests(self, args: List[str], timeout: int = 300) -> Tuple[int, str]:
        """Run frontend tests and update results."""
        exit_code, output = run_frontend_tests(args, timeout, self.results)
        self._handle_test_failures(exit_code, output, "frontend")
        return exit_code, output
    
    def run_e2e_tests(self, args: List[str], timeout: int = 600) -> Tuple[int, str]:
        """Run e2e tests and update results."""
        exit_code, output = run_e2e_tests(args, timeout, self.results)
        self._handle_test_failures(exit_code, output, "e2e")
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
        if self._use_enhanced_reporter(level, config, exit_code):
            return
        save_test_report(self.results, level, config, exit_code, self.reports_dir, self.staging_mode)
    
    def _try_enhanced_report(self, level: str, config: Dict, exit_code: int) -> bool:
        """Try to use enhanced reporter, return success status."""
        return self._execute_safe_enhanced_report(level, config, exit_code)
    
    def _execute_safe_enhanced_report(self, level: str, config: Dict, exit_code: int) -> bool:
        """Execute enhanced report with error handling."""
        try:
            self._execute_enhanced_reporting_workflow(level, config, exit_code)
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
        backend_counts = self._get_backend_counts()
        frontend_counts = self._get_frontend_counts()
        totals = self._aggregate_test_counts(backend_counts, frontend_counts)
        coverage = self._get_coverage_data()
        return {**totals, "coverage": coverage}
    
    def _get_backend_counts(self) -> Dict:
        """Get backend test counts."""
        return self.results["backend"]["test_counts"]
    
    def _get_frontend_counts(self) -> Dict:
        """Get frontend test counts."""
        return self.results["frontend"]["test_counts"]
    
    def _aggregate_test_counts(self, backend_counts: Dict, frontend_counts: Dict) -> Dict:
        """Aggregate test counts from backend and frontend."""
        total_tests = backend_counts["total"] + frontend_counts["total"]
        passed = backend_counts["passed"] + frontend_counts["passed"]
        failed = backend_counts["failed"] + frontend_counts["failed"]
        return {"total_tests": total_tests, "passed": passed, "failed": failed}
    
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
    
    def _setup_enhanced_reporter(self) -> Optional['EnhancedTestReporter']:
        """Initialize enhanced reporter if available."""
        if not ENHANCED_REPORTER_AVAILABLE:
            return None
        return self._create_enhanced_reporter_instance()
    
    def _create_enhanced_reporter_instance(self) -> Optional['EnhancedTestReporter']:
        """Create enhanced reporter instance with error handling."""
        try:
            return self._build_enhanced_reporter()
        except Exception as e:
            self._log_enhanced_reporter_failure(e)
            return None
    
    def _build_enhanced_reporter(self) -> 'EnhancedTestReporter':
        """Build and configure enhanced reporter."""
        reporter = EnhancedTestReporter()
        self._log_enhanced_reporter_success()
        return reporter
    
    def _log_enhanced_reporter_success(self):
        """Log successful enhanced reporter initialization."""
        print("[INFO] Enhanced Test Reporter enabled")
    
    def _log_enhanced_reporter_failure(self, error: Exception):
        """Log enhanced reporter initialization failure."""
        print(f"[WARNING] Could not initialize Enhanced Reporter: {error}")
    
    def _initialize_results_structure(self) -> Dict:
        """Initialize results dictionary structure."""
        component_template = self._create_component_template()
        overall_template = self._create_overall_template()
        return self._build_results_structure(component_template, overall_template)
    
    def _create_component_template(self) -> Dict:
        """Create template for test component results."""
        return {
            "status": "pending", "duration": 0, "exit_code": None, "output": "",
            "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
            "coverage": None
        }
    
    def _create_overall_template(self) -> Dict:
        """Create template for overall test results."""
        return {"status": "pending", "start_time": None, "end_time": None}
    
    def _build_results_structure(self, component_template: Dict, overall_template: Dict) -> Dict:
        """Build complete results structure from templates."""
        return {
            "backend": component_template.copy(),
            "frontend": component_template.copy(),
            "e2e": component_template.copy(),
            "overall": overall_template
        }
    
    def _setup_directories(self):
        """Setup required directories for reports."""
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history_dir = self.reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
    
    def _handle_test_failures(self, exit_code: int, output: str, component: str):
        """Handle test failures by extracting and updating failing tests."""
        if exit_code != 0:
            failures = extract_failing_tests(output, component)
            if failures:
                update_failing_tests(component, failures, None, self.reports_dir)
    
    def _use_enhanced_reporter(self, level: str, config: Dict, exit_code: int) -> bool:
        """Use enhanced reporter if available and successful."""
        if self.enhanced_reporter:
            return self._try_enhanced_report(level, config, exit_code)
        return False
    
    def _execute_enhanced_reporting_workflow(self, level: str, config: Dict, exit_code: int):
        """Execute complete enhanced reporting workflow."""
        report_content = self._generate_enhanced_report(level, config, exit_code)
        metrics = self._calculate_test_metrics()
        self._save_enhanced_report(level, report_content, metrics)
        self._maybe_cleanup_reports()
    
    def _get_coverage_data(self) -> Optional[Dict]:
        """Get coverage data from results."""
        backend_coverage = self.results["backend"].get("coverage")
        frontend_coverage = self.results["frontend"].get("coverage")
        return backend_coverage or frontend_coverage