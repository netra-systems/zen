"""Unified test runner class."""

import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import comprehensive reporter
from test_framework.comprehensive_reporter import ComprehensiveTestReporter
import subprocess
from test_framework.failing_tests_manager import (
    clear_failing_tests,
    load_failing_tests,
    organize_failures_by_category,
    show_failing_tests,
    update_failing_tests,
)
from test_framework.feature_flags import FeatureFlagManager, FeatureStatus
from test_framework.report_generators import (
    generate_json_report,
    generate_markdown_report,
    generate_text_report,
)
from test_framework.report_manager import print_summary, save_test_report
from test_framework.test_config import COMPONENT_MAPPINGS
from test_framework.test_parser import extract_failing_tests, parse_coverage, parse_test_counts

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
        self.feature_manager = FeatureFlagManager()
    
    def run_backend_tests(self, args: List[str], timeout: int = 300, real_llm_config: Optional[Dict] = None, speed_opts: Optional[Dict] = None) -> Tuple[int, str]:
        """Run backend tests and update results."""
        cmd = ["python", "-m", "pytest"] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            exit_code = result.returncode
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            exit_code = 1
            output = f"Tests timed out after {timeout} seconds"
        
        # Update results
        self.results["backend"]["exit_code"] = exit_code
        self.results["backend"]["output"] = output
        self.results["backend"]["status"] = "passed" if exit_code == 0 else "failed"
        
        # Parse test counts and coverage
        test_counts = parse_test_counts(output)
        if test_counts:
            self.results["backend"]["test_counts"] = test_counts
        coverage = parse_coverage(output)
        if coverage:
            self.results["backend"]["coverage"] = coverage
        
        self._handle_test_failures(exit_code, output, "backend")
        return exit_code, output
    
    def run_frontend_tests(self, args: List[str], timeout: int = 300, speed_opts: Optional[Dict] = None, test_level: str = None) -> Tuple[int, str]:
        """Run frontend tests and update results."""
        # Frontend tests use npm
        cmd = ["npm", "test", "--"] + args
        cwd = PROJECT_ROOT / "frontend"
        
        if not cwd.exists():
            return 0, "Frontend directory not found, skipping tests"
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd))
            exit_code = result.returncode
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired as e:
            exit_code = 1
            # Get partial output if available
            output = ""
            if e.stdout:
                output += e.stdout.decode() if isinstance(e.stdout, bytes) else str(e.stdout)
            if e.stderr:
                output += e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
            output += f"\n\nTests timed out after {timeout} seconds"
        except Exception as e:
            exit_code = 1
            output = f"Error running frontend tests: {str(e)}"
        
        # Update results
        self.results["frontend"]["exit_code"] = exit_code
        self.results["frontend"]["output"] = output
        self.results["frontend"]["status"] = "passed" if exit_code == 0 else "failed"
        
        # Parse test counts
        test_counts = parse_test_counts(output)
        if test_counts:
            self.results["frontend"]["test_counts"] = test_counts
        
        self._handle_test_failures(exit_code, output, "frontend")
        return exit_code, output
    
    def run_e2e_tests(self, args: List[str], timeout: int = 600) -> Tuple[int, str]:
        """Run e2e tests and update results."""
        # E2E tests are Python tests in tests/e2e or tests/unified/e2e
        test_paths = ["tests/e2e", "tests/unified/e2e"]
        cmd = ["python", "-m", "pytest"] + test_paths + args
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            exit_code = result.returncode
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            exit_code = 1
            output = f"Tests timed out after {timeout} seconds"
        
        # Update results
        self.results["e2e"]["exit_code"] = exit_code
        self.results["e2e"]["output"] = output
        self.results["e2e"]["status"] = "passed" if exit_code == 0 else "failed"
        
        # Parse test counts
        test_counts = parse_test_counts(output)
        if test_counts:
            self.results["e2e"]["test_counts"] = test_counts
        
        self._handle_test_failures(exit_code, output, "e2e")
        return exit_code, output
    
    def run_simple_tests(self) -> Tuple[int, str]:
        """Run simple smoke tests."""
        # Run basic smoke tests
        cmd = ["python", "-m", "pytest", "--category", "smoke", "--fail-fast"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            exit_code = result.returncode
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            exit_code = 1
            output = "Simple tests timed out after 60 seconds"
        
        return exit_code, output
    
    def run_failing_tests(self, max_fixes: int = None, backend_only: bool = False, frontend_only: bool = False) -> int:
        """Run only the currently failing tests."""
        failing_tests = load_failing_tests(self.reports_dir)
        if not failing_tests:
            print("No failing tests to run")
            return 0
        
        # Run failing tests with pytest
        test_files = []
        for component, tests in failing_tests.items():
            if backend_only and component != "backend":
                continue
            if frontend_only and component != "frontend":
                continue
            test_files.extend(tests)
        
        if not test_files:
            return 0
        
        if max_fixes:
            test_files = test_files[:max_fixes]
        
        cmd = ["python", "-m", "pytest"] + test_files + ["--fail-fast"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode
    
    def save_test_report(self, level: str, config: Dict, output: str, exit_code: int):
        """Save test report to test_reports directory with comprehensive reporting."""
        # Use comprehensive reporter ONLY - single source of truth
        self.comprehensive_reporter.generate_comprehensive_report(
            level=level,
            results=self.results,
            config=config,
            exit_code=exit_code
        )
    
    
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
    
    def get_feature_summary(self) -> Dict:
        """Get summary of feature flag status."""
        return {
            "enabled": list(self.feature_manager.get_enabled_features()),
            "in_development": list(self.feature_manager.get_in_development_features()),
            "disabled": list(self.feature_manager.get_disabled_features()),
            "total": len(self.feature_manager.flags)
        }
    
    def print_feature_summary(self):
        """Print feature flag summary."""
        summary = self.get_feature_summary()
        if summary["total"] > 0:
            print("\n" + "="*60)
            print("FEATURE FLAGS SUMMARY")
            print("="*60)
            if summary["enabled"]:
                print(f"✅ Enabled: {', '.join(summary['enabled'])}")
            if summary["in_development"]:
                print(f"🚧 In Development: {', '.join(summary['in_development'])}")
            if summary["disabled"]:
                print(f"❌ Disabled: {', '.join(summary['disabled'])}")
            print("="*60)