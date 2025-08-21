#!/usr/bin/env python3
"""
Test Runner for Authentication Race Condition Test Suite

This script provides a convenient way to run the comprehensive race condition tests
for the Netra Apex authentication system. It includes various execution modes for
different testing scenarios.

Usage:
    python run_auth_race_condition_tests.py [options]

Options:
    --quick          Run quick subset of tests (5 minutes)
    --comprehensive  Run full test suite (30+ minutes)
    --stress         Run stress tests only
    --benchmark      Run performance benchmarks only
    --report         Generate detailed race condition report
    --help          Show this help message

Examples:
    # Quick validation (CI/CD pipeline)
    python run_auth_race_condition_tests.py --quick

    # Full comprehensive testing (pre-release)
    python run_auth_race_condition_tests.py --comprehensive --report

    # Stress testing only
    python run_auth_race_condition_tests.py --stress
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class AuthRaceConditionTestRunner:
    """Test runner for authentication race condition tests"""
    
    def __init__(self):
        self.test_file = Path(__file__).parent / "test_auth_race_conditions.py"
        self.results = {}
        
    def run_quick_tests(self):
        """Run quick subset of race condition tests (~5 minutes)"""
        print("Running quick race condition validation tests...")
        
        quick_tests = [
            "TestConcurrentTokenRefreshRaceConditions::test_concurrent_token_refresh_race",
            "TestMultiDeviceLoginCollision::test_multi_device_login_collision",
            "test_race_condition_suite_performance_benchmark"
        ]
        
        return self._run_pytest_tests(quick_tests, timeout=300)  # 5 minutes
    
    def run_comprehensive_tests(self):
        """Run full comprehensive race condition test suite (~30 minutes)"""
        print("Running comprehensive race condition test suite...")
        
        # Run all tests in the file
        return self._run_pytest_tests([], timeout=1800)  # 30 minutes
    
    def run_stress_tests(self):
        """Run stress testing scenarios only"""
        print("Running race condition stress tests...")
        
        stress_tests = [
            "TestRaceConditionLoadStress::test_comprehensive_race_condition_stress"
        ]
        
        return self._run_pytest_tests(stress_tests, timeout=600)  # 10 minutes
    
    def run_benchmark_tests(self):
        """Run performance benchmark tests only"""
        print("Running race condition performance benchmarks...")
        
        benchmark_tests = [
            "test_race_condition_suite_performance_benchmark"
        ]
        
        return self._run_pytest_tests(benchmark_tests, timeout=300)  # 5 minutes
    
    def _run_pytest_tests(self, test_filters=None, timeout=300):
        """Execute pytest with specified test filters"""
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_file),
            "-v",
            "--tb=short",
            "--durations=10",
            "--capture=no"
        ]
        
        # Add specific test filters if provided
        if test_filters:
            for test_filter in test_filters:
                cmd.extend(["-k", test_filter])
        
        print(f"Executing command: {' '.join(cmd)}")
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=project_root,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            end_time = time.time()
            
            duration = end_time - start_time
            
            self.results = {
                "duration": duration,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            self._print_results()
            return self.results["success"]
            
        except subprocess.TimeoutExpired:
            print(f"ERROR: Tests timed out after {timeout} seconds")
            return False
        except Exception as e:
            print(f"ERROR: Failed to run tests: {e}")
            return False
    
    def _print_results(self):
        """Print formatted test results"""
        print("\n" + "="*80)
        print("RACE CONDITION TEST RESULTS")
        print("="*80)
        
        duration = self.results["duration"]
        success = self.results["success"]
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Status: {'PASSED' if success else 'FAILED'}")
        print(f"Return code: {self.results['returncode']}")
        
        if self.results["stdout"]:
            print("\nTest Output:")
            print("-" * 40)
            print(self.results["stdout"])
        
        if self.results["stderr"]:
            print("\nErrors/Warnings:")
            print("-" * 40)
            print(self.results["stderr"])
        
        print("="*80)
    
    def generate_report(self):
        """Generate detailed race condition test report"""
        if not self.results:
            print("No test results available for report generation")
            return
        
        report_file = project_root / "race_condition_test_report.txt"
        
        with open(report_file, "w") as f:
            f.write("AUTHENTICATION RACE CONDITION TEST REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {self.results['duration']:.2f} seconds\n")
            f.write(f"Status: {'PASSED' if self.results['success'] else 'FAILED'}\n\n")
            
            f.write("Test Output:\n")
            f.write("-" * 20 + "\n")
            f.write(self.results["stdout"])
            
            if self.results["stderr"]:
                f.write("\n\nErrors/Warnings:\n")
                f.write("-" * 20 + "\n")
                f.write(self.results["stderr"])
        
        print(f"Detailed report generated: {report_file}")


def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description="Run Authentication Race Condition Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("--quick", action="store_true",
                       help="Run quick subset of tests (5 minutes)")
    parser.add_argument("--comprehensive", action="store_true",
                       help="Run full test suite (30+ minutes)")
    parser.add_argument("--stress", action="store_true",
                       help="Run stress tests only")
    parser.add_argument("--benchmark", action="store_true",
                       help="Run performance benchmarks only")
    parser.add_argument("--report", action="store_true",
                       help="Generate detailed race condition report")
    
    args = parser.parse_args()
    
    # If no specific mode selected, default to quick tests
    if not any([args.quick, args.comprehensive, args.stress, args.benchmark]):
        args.quick = True
        print("No test mode specified, defaulting to --quick")
    
    runner = AuthRaceConditionTestRunner()
    success = True
    
    try:
        if args.quick:
            success &= runner.run_quick_tests()
        
        if args.comprehensive:
            success &= runner.run_comprehensive_tests()
        
        if args.stress:
            success &= runner.run_stress_tests()
        
        if args.benchmark:
            success &= runner.run_benchmark_tests()
        
        if args.report:
            runner.generate_report()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()