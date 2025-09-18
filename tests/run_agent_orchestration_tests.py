#!/usr/bin/env python3
"""
Agent Orchestration Test Runner - SSOT Implementation

Comprehensive test runner for agent performance metrics and error recovery tests.
Provides easy execution of critical agent orchestration test suites with SSOT compliance.

Business Value: Platform/Internal - Agent System Stability & Golden Path Validation
Enables validation of critical agent workflows that deliver 90% of platform value.

REQUIREMENTS per CLAUDE.md:
- Use IsolatedEnvironment instead of direct os.environ access
- Absolute imports only
- Integration with test_framework.ssot.base_test_case
- Proper error handling and reporting
- CLI functionality with multiple execution modes

Usage Examples:
    # Run all agent orchestration tests
    python tests/run_agent_orchestration_tests.py

    # Run only performance tests
    python tests/run_agent_orchestration_tests.py --performance-only

    # Run only error recovery tests
    python tests/run_agent_orchestration_tests.py --error-recovery-only

    # Run quick validation (default mode)
    python tests/run_agent_orchestration_tests.py --quick-validation

    # Run with specific concurrency level
    python tests/run_agent_orchestration_tests.py --concurrent-load 15

    # Run with detailed reporting
    python tests/run_agent_orchestration_tests.py --detailed-reports
"""

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase


class AgentOrchestrationTestRunner(SSotBaseTestCase):
    """
    SSOT Agent Orchestration Test Runner

    Provides unified execution of agent performance and error recovery test suites
    with proper environment isolation and comprehensive reporting.
    """

    def __init__(self):
        """Initialize the test runner with SSOT patterns."""
        super().__init__()
        self.env = IsolatedEnvironment()
        self.project_root = PROJECT_ROOT
        self.results: Dict[str, int] = {}
        self.test_files = {
            'performance': 'tests/performance/test_agent_performance_metrics.py',
            'error_recovery': 'tests/integration/test_agent_error_recovery.py'
        }
        self._pytest_available = self._check_pytest_availability()

    def _check_pytest_availability(self) -> bool:
        """Check if pytest is available in the current environment."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _validate_test_files(self) -> bool:
        """Validate that required test files exist."""
        # First check if pytest is available
        if not self._pytest_available:
            print("[ERROR] pytest is not available in the current environment")
            print("Please install pytest: pip install pytest pytest-asyncio")
            return False

        missing_files = []

        for test_type, file_path in self.test_files.items():
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(f"{test_type}: {file_path}")

        if missing_files:
            print("[ERROR] Missing test files:")
            for missing in missing_files:
                print(f"  - {missing}")
            return False

        return True

    def _build_pytest_command(self, test_file: str, test_marker: Optional[str] = None,
                             detailed_reports: bool = False,
                             specific_test: Optional[str] = None) -> List[str]:
        """Build pytest command with proper options."""
        if specific_test:
            # For specific tests, modify the file path to include the test name
            test_target = f"{test_file}::{specific_test}"
        else:
            test_target = test_file

        # Use sys.executable to ensure we use the correct Python interpreter
        cmd = [
            sys.executable, "-m", "pytest",
            test_target,
            "-v",
            "--asyncio-mode=auto",
            "--tb=short"
        ]

        if test_marker:
            cmd.extend(["-m", test_marker])

        if detailed_reports:
            cmd.extend(["--capture=no", "-s"])

        return cmd

    def run_performance_tests(self, concurrent_load: int = 10,
                             detailed_reports: bool = False) -> int:
        """Run comprehensive agent performance metrics tests."""
        print("=" * 80)
        print("RUNNING AGENT PERFORMANCE METRICS TESTS")
        print("=" * 80)

        test_file = self.test_files['performance']

        if not (self.project_root / test_file).exists():
            print(f"[ERROR] Performance test file not found: {test_file}")
            return 1

        cmd = self._build_pytest_command(
            test_file,
            test_marker="performance",
            detailed_reports=detailed_reports
        )

        print(f"Running performance tests with concurrent load: {concurrent_load}")
        print(f"Detailed reports: {detailed_reports}")
        print()

        # Set environment variable for concurrent load through IsolatedEnvironment
        env_vars = self.env.get_all()
        env_vars["AGENT_PERFORMANCE_CONCURRENT_LOAD"] = str(concurrent_load)

        try:
            result = subprocess.run(cmd, env=env_vars, capture_output=False, cwd=str(self.project_root))

            if result.returncode == 0:
                print("[SUCCESS] Performance tests completed successfully")
            else:
                print("[FAILED] Performance tests failed")

            self.results['performance'] = result.returncode
            return result.returncode

        except Exception as e:
            print(f"[ERROR] Failed to run performance tests: {e}")
            self.results['performance'] = 1
            return 1

    def run_error_recovery_tests(self, detailed_reports: bool = False) -> int:
        """Run comprehensive agent error recovery tests."""
        print("=" * 80)
        print("RUNNING AGENT ERROR RECOVERY TESTS")
        print("=" * 80)

        test_file = self.test_files['error_recovery']

        if not (self.project_root / test_file).exists():
            print(f"[ERROR] Error recovery test file not found: {test_file}")
            return 1

        cmd = self._build_pytest_command(
            test_file,
            test_marker="error_recovery",
            detailed_reports=detailed_reports
        )

        print("Running error recovery tests...")
        print()

        try:
            result = subprocess.run(cmd, capture_output=False, cwd=str(self.project_root))

            if result.returncode == 0:
                print("[SUCCESS] Error recovery tests completed successfully")
            else:
                print("[FAILED] Error recovery tests failed")

            self.results['error_recovery'] = result.returncode
            return result.returncode

        except Exception as e:
            print(f"[ERROR] Failed to run error recovery tests: {e}")
            self.results['error_recovery'] = 1
            return 1

    def run_all_tests(self, concurrent_load: int = 10,
                     detailed_reports: bool = False) -> int:
        """Run all agent orchestration tests (performance + error recovery)."""
        print("=" * 80)
        print("RUNNING COMPLETE AGENT ORCHESTRATION TEST SUITE")
        print("=" * 80)

        start_time = time.time()

        # Run performance tests
        perf_result = self.run_performance_tests(concurrent_load, detailed_reports)

        print("\n" + "-" * 40)
        print("SEPARATOR BETWEEN TEST PHASES")
        print("-" * 40 + "\n")

        # Run error recovery tests
        recovery_result = self.run_error_recovery_tests(detailed_reports)

        # Summary
        end_time = time.time()
        duration = end_time - start_time

        return self._generate_summary_report(perf_result, recovery_result, duration)

    def run_quick_validation(self) -> int:
        """Run quick validation tests to check basic functionality."""
        print("=" * 80)
        print("RUNNING QUICK AGENT ORCHESTRATION VALIDATION")
        print("=" * 80)

        results = []

        # Quick performance validation
        perf_test = "test_single_agent_execution_time_benchmarks"
        cmd_perf = self._build_pytest_command(
            self.test_files['performance'],
            specific_test=perf_test
        )
        cmd_perf.extend(["-x"])  # Stop on first failure

        print("Running quick performance validation...")
        try:
            perf_result = subprocess.run(cmd_perf, capture_output=False, cwd=str(self.project_root))
            results.append(('performance', perf_result.returncode))
        except Exception as e:
            print(f"[ERROR] Performance validation failed: {e}")
            results.append(('performance', 1))

        # Quick error recovery validation
        recovery_test = "test_individual_agent_timeout_recovery"
        cmd_recovery = self._build_pytest_command(
            self.test_files['error_recovery'],
            specific_test=recovery_test
        )
        cmd_recovery.extend(["-x"])  # Stop on first failure

        print("Running quick error recovery validation...")
        try:
            recovery_result = subprocess.run(cmd_recovery, capture_output=False, cwd=str(self.project_root))
            results.append(('error_recovery', recovery_result.returncode))
        except Exception as e:
            print(f"[ERROR] Error recovery validation failed: {e}")
            results.append(('error_recovery', 1))

        # Determine overall result
        overall_result = 0 if all(result[1] == 0 for result in results) else 1

        print("\n" + "=" * 80)
        print("QUICK VALIDATION SUMMARY")
        print("=" * 80)

        for test_type, result in results:
            status = "PASSED" if result == 0 else "FAILED"
            print(f"{test_type.replace('_', ' ').title()} validation: {status}")

        if overall_result == 0:
            print("[SUCCESS] Quick validation passed - full test suite should work")
        else:
            print("[FAILED] Quick validation failed - check environment setup")

        print("=" * 80)
        return overall_result

    def _generate_summary_report(self, perf_result: int, recovery_result: int,
                                duration: float) -> int:
        """Generate comprehensive summary report."""
        print("\n" + "=" * 80)
        print("TEST SUITE SUMMARY")
        print("=" * 80)

        print(f"Performance tests result: {'PASSED' if perf_result == 0 else 'FAILED'} ({perf_result})")
        print(f"Error recovery tests result: {'PASSED' if recovery_result == 0 else 'FAILED'} ({recovery_result})")
        print(f"Total duration: {duration:.2f} seconds")

        overall_result = 0 if (perf_result == 0 and recovery_result == 0) else 1

        if overall_result == 0:
            print("[SUCCESS] ALL AGENT ORCHESTRATION TESTS PASSED!")
        else:
            print("[WARNING] SOME TESTS FAILED - CHECK OUTPUT ABOVE")

        print("=" * 80)

        # Store results for potential future use
        self.results.update({
            'performance': perf_result,
            'error_recovery': recovery_result,
            'overall': overall_result,
            'duration': duration
        })

        return overall_result

    def generate_report(self) -> Dict[str, any]:
        """Generate detailed execution report."""
        return {
            'test_runner': 'AgentOrchestrationTestRunner',
            'execution_time': time.time(),
            'results': self.results.copy(),
            'test_files': self.test_files.copy(),
            'project_root': str(self.project_root)
        }


def main() -> int:
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Orchestration Test Runner - SSOT Implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Execution mode arguments
    parser.add_argument(
        "--performance-only",
        action="store_true",
        help="Run only performance metrics tests"
    )

    parser.add_argument(
        "--error-recovery-only",
        action="store_true",
        help="Run only error recovery tests"
    )

    parser.add_argument(
        "--quick-validation",
        action="store_true",
        help="Run quick validation tests only (default mode)"
    )

    # Configuration arguments
    parser.add_argument(
        "--concurrent-load",
        type=int,
        default=10,
        help="Concurrent load level for performance tests (default: 10)"
    )

    parser.add_argument(
        "--detailed-reports",
        action="store_true",
        help="Generate detailed test reports with console output"
    )

    args = parser.parse_args()

    print("Agent Orchestration Test Runner - SSOT Implementation")
    print("=" * 60)
    print()

    # Initialize test runner
    try:
        runner = AgentOrchestrationTestRunner()

        # Validate environment
        if not runner._validate_test_files():
            return 1

        # Execute based on arguments
        if args.performance_only:
            return runner.run_performance_tests(args.concurrent_load, args.detailed_reports)
        elif args.error_recovery_only:
            return runner.run_error_recovery_tests(args.detailed_reports)
        elif args.quick_validation:
            return runner.run_quick_validation()
        else:
            # Default: run quick validation if no specific mode specified
            return runner.run_quick_validation()

    except KeyboardInterrupt:
        print("\n[WARNING] Test execution interrupted by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Test runner failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())