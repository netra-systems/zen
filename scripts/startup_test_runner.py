#!/usr/bin/env python
"""
System Startup Test Runner - Main Orchestrator
Modular test runner for system startup and E2E tests
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from startup_environment import DependencyChecker, ProcessManager, StartupEnvironment
from startup_performance import PerformanceTestExecutor
from startup_reporter import StartupReporter
from startup_test_executor import (
    BackendTestExecutor,
    E2ETestExecutor,
    FrontendTestExecutor,
    TestResult,
)


class SystemStartupTestRunner:
    """Main orchestrator for system startup testing"""
    
    def __init__(self, args):
        self.args = args
        self.environment = StartupEnvironment(args)
        self.dependency_checker = DependencyChecker(args)
        self.process_manager = ProcessManager()
        self.reporter = None
        self.test_results: List[TestResult] = []
    
    def run(self):
        """Main test execution orchestrator"""
        try:
            self._setup_phase()
            self._execute_tests_by_mode()
            success = self._finalize_and_report()
            self._exit_with_status(success)
        except KeyboardInterrupt:
            self._handle_interruption()
        except Exception as e:
            self._handle_error(e)
    
    def _setup_phase(self):
        """Setup environment and validate dependencies"""
        env_data = self.environment.setup_environment()
        self.dependency_checker.check_all_dependencies()
        self.reporter = StartupReporter(self.args, env_data)
    
    def _execute_tests_by_mode(self):
        """Execute tests based on selected mode"""
        mode_handlers = {
            "minimal": self._run_minimal_tests,
            "quick": self._run_quick_tests,
            "standard": self._run_standard_tests,
            "full": self._run_full_tests,
            "performance": self._run_performance_only_tests
        }
        handler = mode_handlers.get(self.args.mode, self._run_standard_tests)
        handler()
    
    def _run_minimal_tests(self):
        """Run minimal test suite"""
        backend_executor = BackendTestExecutor(self.args)
        result = backend_executor.run_tests()
        if result:
            self.test_results.append(result)
    
    def _run_quick_tests(self):
        """Run quick test suite"""
        self._run_minimal_tests()
        frontend_executor = FrontendTestExecutor(self.args)
        result = frontend_executor.run_tests()
        if result:
            self.test_results.append(result)
    
    def _run_standard_tests(self):
        """Run standard test suite"""
        self._run_quick_tests()
        e2e_executor = E2ETestExecutor(self.args)
        result = e2e_executor.run_tests()
        if result:
            self.test_results.append(result)
    
    def _run_full_tests(self):
        """Run full test suite with performance"""
        self._run_standard_tests()
        performance_executor = PerformanceTestExecutor(self.args)
        result = performance_executor.run_tests()
        if result:
            self.test_results.append(result)
    
    def _run_performance_only_tests(self):
        """Run performance tests only"""
        performance_executor = PerformanceTestExecutor(self.args)
        result = performance_executor.run_tests()
        if result:
            self.test_results.append(result)
    
    def _finalize_and_report(self) -> bool:
        """Generate reports and cleanup"""
        success = self.reporter.generate_reports(self.test_results)
        self._cleanup()
        return success
    
    def _cleanup(self):
        """Cleanup test environment"""
        print("\n" + "-"*40)
        print("Cleaning up...")
        self.process_manager.cleanup_all()
        self.process_manager.remove_test_artifacts()
        print("Cleanup complete")
    
    def _exit_with_status(self, success: bool):
        """Exit with appropriate status code"""
        sys.exit(0 if success else 1)
    
    def _handle_interruption(self):
        """Handle keyboard interruption"""
        print("\n\n[WARNING] Tests interrupted by user")
        self._cleanup()
        sys.exit(130)
    
    def _handle_error(self, error: Exception):
        """Handle unexpected errors"""
        print(f"\n\n[ERROR] Test runner error: {error}")
        self._cleanup()
        sys.exit(1)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="System Startup Test Runner - Comprehensive testing for system initialization"
    )
    parser.add_argument(
        "--mode",
        choices=["minimal", "quick", "standard", "full", "performance"],
        default="standard",
        help="Test mode (default: standard)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage reports"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Continue even if dependencies are missing"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel where possible"
    )
    return parser


def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    runner = SystemStartupTestRunner(args)
    runner.run()


if __name__ == "__main__":
    main()