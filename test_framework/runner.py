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

# Import comprehensive reporter
from .comprehensive_reporter import ComprehensiveTestReporter

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
        self.results = self._initialize_results_structure()
        self._setup_directories()
        self.comprehensive_reporter = ComprehensiveTestReporter(self.reports_dir)
        self.staging_mode = False
    
    def run_backend_tests(self, args: List[str], timeout: int = 300, real_llm_config: Optional[Dict] = None, speed_opts: Optional[Dict] = None) -> Tuple[int, str]:
        """Run backend tests and update results."""
        exit_code, output = run_backend_tests(args, timeout, real_llm_config, self.results, speed_opts)
        self._handle_test_failures(exit_code, output, "backend")
        return exit_code, output
    
    def run_frontend_tests(self, args: List[str], timeout: int = 300, speed_opts: Optional[Dict] = None) -> Tuple[int, str]:
        """Run frontend tests and update results."""
        exit_code, output = run_frontend_tests(args, timeout, self.results, speed_opts)
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
        """Save test report to test_reports directory with comprehensive reporting."""
        # Use comprehensive reporter
        self.comprehensive_reporter.generate_comprehensive_report(
            level=level,
            results=self.results,
            config=config,
            exit_code=exit_code
        )
        # Also save traditional reports for backward compatibility
        save_test_report(self.results, level, config, exit_code, self.reports_dir, self.staging_mode)
    
    
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
    
    def _get_coverage_data(self) -> Optional[Dict]:
        """Get coverage data from results."""
        backend_coverage = self.results["backend"].get("coverage")
        frontend_coverage = self.results["frontend"].get("coverage")
        return backend_coverage or frontend_coverage