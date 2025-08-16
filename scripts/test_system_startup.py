#!/usr/bin/env python
"""
System Startup Test Runner
Comprehensive test runner for system startup and E2E tests
"""

import sys
import os
import subprocess
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import psutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class SystemStartupTestRunner:
    """Orchestrates system startup testing"""
    
    def __init__(self, args):
        self.args = args
        self.results = {
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "summary": {},
            "environment": {}
        }
        self.processes = []
        
    def setup_environment(self):
        """Setup test environment"""
        print("\n" + "="*60)
        print("SYSTEM STARTUP TEST RUNNER")
        print("="*60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test mode: {self.args.mode}")
        print(f"Verbose: {self.args.verbose}")
        
        # Record environment info
        self.results["environment"] = {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / (1024**3),  # GB
            "test_mode": self.args.mode
        }
        
        # Ensure test directories exist
        os.makedirs("reports/system-startup", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Set test environment variables
        os.environ["TESTING"] = "1"
        os.environ["LOG_LEVEL"] = "DEBUG" if self.args.verbose else "INFO"
        
        print("\nEnvironment setup complete")
        
    def _setup_dependency_check(self):
        """Setup dependency check header"""
        print("\n" + "-"*40)
        print("Checking Dependencies")
        print("-"*40)
        return []

    def _check_python_version(self, checks):
        """Check Python version requirement"""
        python_version = sys.version_info
        passed = python_version >= (3, 8)
        version_str = f"{python_version.major}.{python_version.minor}"
        checks.append(("Python 3.8+", passed, version_str))
        return checks

    def _check_nodejs(self, checks):
        """Check Node.js availability"""
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            checks.append(("Node.js", True, result.stdout.strip()))
        except FileNotFoundError:
            checks.append(("Node.js", False, "Not installed"))
        return checks

    def _check_npm(self, checks):
        """Check npm availability"""
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            checks.append(("npm", True, result.stdout.strip()))
        except FileNotFoundError:
            checks.append(("npm", False, "Not installed"))
        return checks

    def _check_redis(self, checks):
        """Check Redis availability if not minimal mode"""
        if self.args.mode == "minimal":
            return checks
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
            r.ping()
            checks.append(("Redis", True, "Connected"))
        except:
            checks.append(("Redis", False, "Not available"))
        return checks

    def _check_postgresql(self, checks):
        """Check PostgreSQL driver if not minimal mode"""
        if self.args.mode == "minimal":
            return checks
        try:
            import psycopg2
            checks.append(("PostgreSQL driver", True, "Available"))
        except ImportError:
            checks.append(("PostgreSQL driver", False, "Not installed"))
        return checks

    def _display_dependency_results(self, checks):
        """Display dependency check results"""
        all_passed = True
        for name, passed, version in checks:
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {name:20} {version}")
            if not passed and name not in ["Redis", "PostgreSQL driver"]:
                all_passed = False
        return all_passed

    def _handle_dependency_failures(self, all_passed):
        """Handle dependency check failures"""
        if not all_passed:
            print("\n[WARNING] Some required dependencies are missing!")
            if not self.args.force:
                print("Use --force to continue anyway")
                sys.exit(1)
        else:
            print("\n[OK] All dependencies satisfied")

    def check_dependencies(self):
        """Check that all required services are available"""
        checks = self._setup_dependency_check()
        checks = self._check_python_version(checks)
        checks = self._check_nodejs(checks)
        checks = self._check_npm(checks)
        checks = self._check_redis(checks)
        checks = self._check_postgresql(checks)
        all_passed = self._display_dependency_results(checks)
        self._handle_dependency_failures(all_passed)
        return checks
    
    def run_backend_startup_tests(self):
        """Run backend system startup tests"""
        print("\n" + "-"*40)
        print("Running Backend Startup Tests")
        print("-"*40)
        
        test_file = "tests/test_system_startup.py"
        
        if not os.path.exists(test_file):
            print(f"[WARNING] Test file not found: {test_file}")
            return None
        
        cmd = [
            "python", "-m", "pytest",
            test_file,
            "-v" if self.args.verbose else "-q",
            "--tb=short",
            "--disable-warnings"
        ]
        
        if self.args.coverage:
            cmd.extend(["--cov=app", "--cov-report=term-missing"])
        
        print(f"Running: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        
        # Parse results
        test_result = {
            "name": "Backend Startup Tests",
            "duration": duration,
            "passed": result.returncode == 0,
            "output": result.stdout if self.args.verbose else "",
            "errors": result.stderr if result.returncode != 0 else ""
        }
        
        self.results["tests"].append(test_result)
        
        if test_result["passed"]:
            print(f"[OK] Backend startup tests passed ({duration:.2f}s)")
        else:
            print(f"[FAIL] Backend startup tests failed")
            if not self.args.verbose:
                print("  Run with --verbose to see details")
        
        return test_result
    
    def run_frontend_startup_tests(self):
        """Run frontend system startup tests"""
        print("\n" + "-"*40)
        print("Running Frontend Startup Tests")
        print("-"*40)
        
        test_file = "frontend/__tests__/system/startup.test.tsx"
        
        if not os.path.exists(test_file):
            print(f"[WARNING] Test file not found: {test_file}")
            return None
        
        # First, ensure dependencies are installed
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd="frontend", capture_output=True)
        
        cmd = ["npm", "test", "--", "startup.test"]
        
        if self.args.coverage:
            cmd.append("--coverage")
        
        print(f"Running: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd="frontend", capture_output=True, text=True)
        duration = time.time() - start_time
        
        # Parse results
        test_result = {
            "name": "Frontend Startup Tests",
            "duration": duration,
            "passed": result.returncode == 0,
            "output": result.stdout if self.args.verbose else "",
            "errors": result.stderr if result.returncode != 0 else ""
        }
        
        self.results["tests"].append(test_result)
        
        if test_result["passed"]:
            print(f"[OK] Frontend startup tests passed ({duration:.2f}s)")
        else:
            print(f"[FAIL] Frontend startup tests failed")
            if not self.args.verbose:
                print("  Run with --verbose to see details")
        
        return test_result
    
    def _setup_e2e_test_header(self):
        """Setup E2E test header and validate test file"""
        print("\n" + "-"*40)
        print("Running End-to-End Tests")
        print("-"*40)
        test_file = "tests/test_super_e2e.py"
        if not os.path.exists(test_file):
            print(f"[WARNING] Test file not found: {test_file}")
            return None
        return test_file

    def _prepare_e2e_services(self):
        """Prepare services for E2E testing"""
        print("Checking service availability...")
        if self.args.mode == "full":
            print("Starting services for E2E tests...")
            # Services will be started by the E2E test itself

    def _build_e2e_command(self, test_file):
        """Build pytest command for E2E tests"""
        cmd = [
            "python", "-m", "pytest", test_file,
            "-v" if self.args.verbose else "-q",
            "--tb=short", "-s", "--disable-warnings"
        ]
        return cmd

    def _add_e2e_coverage_options(self, cmd):
        """Add coverage options if requested"""
        if self.args.coverage:
            cmd.extend(["--cov=app", "--cov-report=term-missing"])
        return cmd

    def _add_e2e_mode_filters(self, cmd):
        """Add test filters based on mode"""
        if self.args.mode == "minimal":
            cmd.extend(["-k", "not concurrent and not performance"])
        elif self.args.mode == "quick":
            cmd.extend(["-k", "startup or login or websocket"])
        return cmd

    def _execute_e2e_tests(self, cmd):
        """Execute E2E tests and measure duration"""
        print(f"Running: {' '.join(cmd)}")
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        return result, duration

    def _process_e2e_results(self, result, duration):
        """Process E2E test results and create result object"""
        test_result = {
            "name": "End-to-End Tests", "duration": duration,
            "passed": result.returncode == 0,
            "output": result.stdout if self.args.verbose else "",
            "errors": result.stderr if result.returncode != 0 else ""
        }
        return test_result

    def _display_e2e_status(self, test_result):
        """Display E2E test completion status"""
        self.results["tests"].append(test_result)
        if test_result["passed"]:
            print(f"[OK] E2E tests passed ({test_result['duration']:.2f}s)")
        else:
            print(f"[FAIL] E2E tests failed")
            if not self.args.verbose:
                print("  Run with --verbose to see details")

    def run_e2e_tests(self):
        """Run complete E2E tests"""
        print("\n" + "-"*40)
        print("Running End-to-End Tests")
        print("-"*40)
        
        test_file = "tests/test_super_e2e.py"
        
        if not os.path.exists(test_file):
            print(f"[WARNING] Test file not found: {test_file}")
            return None
        
        # Check if services are available
        print("Checking service availability...")
        
        # For E2E tests, we need actual services running
        if self.args.mode == "full":
            print("Starting services for E2E tests...")
            # Services will be started by the E2E test itself
        
        cmd = [
            "python", "-m", "pytest",
            test_file,
            "-v" if self.args.verbose else "-q",
            "--tb=short",
            "-s",  # Show print statements
            "--disable-warnings"
        ]
        
        if self.args.coverage:
            cmd.extend(["--cov=app", "--cov-report=term-missing"])
        
        # Select specific tests based on mode
        if self.args.mode == "minimal":
            cmd.extend(["-k", "not concurrent and not performance"])
        elif self.args.mode == "quick":
            cmd.extend(["-k", "startup or login or websocket"])
        
        print(f"Running: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        
        # Parse results
        test_result = {
            "name": "End-to-End Tests",
            "duration": duration,
            "passed": result.returncode == 0,
            "output": result.stdout if self.args.verbose else "",
            "errors": result.stderr if result.returncode != 0 else ""
        }
        
        self.results["tests"].append(test_result)
        
        if test_result["passed"]:
            print(f"[OK] E2E tests passed ({duration:.2f}s)")
        else:
            print(f"[FAIL] E2E tests failed")
            if not self.args.verbose:
                print("  Run with --verbose to see details")
        
        return test_result
    
    def _should_skip_performance_tests(self):
        """Check if performance tests should be skipped"""
        return self.args.mode not in ["full", "performance"]

    def _setup_performance_header_and_metrics(self):
        """Setup performance test header and initialize metrics"""
        print("\n" + "-"*40)
        print("Running Performance Tests")
        print("-"*40)
        return {"startup_time": 0, "memory_baseline": 0, "memory_after_startup": 0, "api_response_time": 0}

    def _setup_backend_environment(self):
        """Setup environment for backend process"""
        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
        env["TESTING"] = "1"
        return env

    def _start_backend_process(self, env):
        """Start backend process for performance testing"""
        return subprocess.Popen(
            ["python", "run_server.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def _measure_startup_time(self, start_time):
        """Measure and return startup time"""
        return time.time() - start_time

    def _measure_memory_usage(self, process):
        """Measure memory usage of process"""
        if process.poll() is None:
            try:
                p = psutil.Process(process.pid)
                return p.memory_info().rss / (1024**2)  # MB
            except:
                pass
        return 0

    def _cleanup_process(self, process):
        """Cleanup backend process"""
        process.terminate()
        process.wait(timeout=5)

    def _display_performance_results(self, metrics):
        """Display performance test results"""
        print(f"\nPerformance Metrics:")
        print(f"  Startup time: {metrics['startup_time']:.2f}s")
        print(f"  Memory usage: {metrics['memory_after_startup']:.2f} MB")

    def _check_performance_thresholds(self, metrics):
        """Check if metrics pass performance thresholds"""
        return (
            metrics["startup_time"] < 10 and  # Less than 10 seconds
            metrics["memory_after_startup"] < 500  # Less than 500MB
        )

    def _create_performance_test_result(self, metrics, passed):
        """Create performance test result object"""
        return {
            "name": "Performance Tests",
            "duration": metrics["startup_time"],
            "passed": passed,
            "metrics": metrics
        }

    def _finalize_performance_test(self, test_result):
        """Finalize performance test and display status"""
        self.results["tests"].append(test_result)
        status = "[OK] Performance tests passed" if test_result["passed"] else "[FAIL] Performance tests failed (exceeded thresholds)"
        print(status)
        return test_result

    def run_performance_tests(self):
        """Run performance benchmarks"""
        if self._should_skip_performance_tests():
            return None
        metrics = self._setup_performance_header_and_metrics()
        env = self._setup_backend_environment()
        print("Measuring startup time...")
        start_time = time.time()
        process = self._start_backend_process(env)
        metrics["startup_time"] = self._measure_startup_time(start_time)
        metrics["memory_after_startup"] = self._measure_memory_usage(process)
        self._cleanup_process(process)
        self._display_performance_results(metrics)
        passed = self._check_performance_thresholds(metrics)
        test_result = self._create_performance_test_result(metrics, passed)
        return self._finalize_performance_test(test_result)
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        
        # Calculate summary
        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for t in self.results["tests"] if t["passed"])
        failed_tests = total_tests - passed_tests
        total_duration = sum(t["duration"] for t in self.results["tests"])
        
        self.results["summary"] = {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "duration": total_duration,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        # Display summary
        print(f"\nTests Run: {total_tests}")
        print(f"Passed: {passed_tests} [OK]")
        print(f"Failed: {failed_tests} [FAIL]")
        print(f"Success Rate: {self.results['summary']['success_rate']:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Display individual results
        print("\nTest Results:")
        for test in self.results["tests"]:
            status = "[OK]" if test["passed"] else "[FAIL]"
            print(f"  {status} {test['name']:30} ({test['duration']:.2f}s)")
        
        # Save JSON report
        report_file = f"reports/system-startup/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nDetailed report saved to: {report_file}")
        
        # Save Markdown report
        self.generate_markdown_report()
        
        return self.results["summary"]["failed"] == 0
    
    def generate_markdown_report(self):
        """Generate Markdown report"""
        report = []
        report.append("# System Startup Test Report")
        report.append(f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Mode:** {self.args.mode}")
        report.append(f"**Platform:** {sys.platform}")
        
        # Summary
        summary = self.results["summary"]
        report.append("\n## Summary")
        report.append(f"- **Total Tests:** {summary['total']}")
        report.append(f"- **Passed:** {summary['passed']} [OK]")
        report.append(f"- **Failed:** {summary['failed']} [FAIL]")
        report.append(f"- **Success Rate:** {summary['success_rate']:.1f}%")
        report.append(f"- **Duration:** {summary['duration']:.2f}s")
        
        # Test Results
        report.append("\n## Test Results")
        report.append("\n| Test | Status | Duration |")
        report.append("|------|--------|----------|")
        
        for test in self.results["tests"]:
            status = "[OK] Pass" if test["passed"] else "[FAIL] Fail"
            report.append(f"| {test['name']} | {status} | {test['duration']:.2f}s |")
        
        # Environment
        report.append("\n## Environment")
        env = self.results["environment"]
        report.append(f"- **Python:** {env['python_version'].split()[0]}")
        report.append(f"- **Platform:** {env['platform']}")
        report.append(f"- **CPU Cores:** {env['cpu_count']}")
        report.append(f"- **Memory:** {env['memory_total']:.1f} GB")
        
        # Failed Tests Details
        failed = [t for t in self.results["tests"] if not t["passed"]]
        if failed:
            report.append("\n## Failed Test Details")
            for test in failed:
                report.append(f"\n### {test['name']}")
                if test.get("errors"):
                    report.append("```")
                    report.append(test["errors"][:1000])  # Limit error output
                    report.append("```")
        
        # Save report
        report_file = f"reports/system-startup/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, "w") as f:
            f.write("\n".join(report))
        print(f"Markdown report saved to: {report_file}")
    
    def cleanup(self):
        """Cleanup test environment"""
        print("\n" + "-"*40)
        print("Cleaning up...")
        
        # Terminate any remaining processes
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        
        # Clean test database
        test_db = "test_e2e.db"
        if os.path.exists(test_db):
            os.remove(test_db)
            print(f"Removed test database: {test_db}")
        
        print("Cleanup complete")
    
    def run(self):
        """Main test execution"""
        try:
            # Setup
            self.setup_environment()
            self.check_dependencies()
            
            # Run tests based on mode
            if self.args.mode == "minimal":
                self.run_backend_startup_tests()
                
            elif self.args.mode == "quick":
                self.run_backend_startup_tests()
                self.run_frontend_startup_tests()
                
            elif self.args.mode == "standard":
                self.run_backend_startup_tests()
                self.run_frontend_startup_tests()
                self.run_e2e_tests()
                
            elif self.args.mode == "full":
                self.run_backend_startup_tests()
                self.run_frontend_startup_tests()
                self.run_e2e_tests()
                self.run_performance_tests()
                
            elif self.args.mode == "performance":
                self.run_performance_tests()
            
            # Generate report
            success = self.generate_report()
            
            # Cleanup
            self.cleanup()
            
            # Exit code
            sys.exit(0 if success else 1)
            
        except KeyboardInterrupt:
            print("\n\n[WARNING] Tests interrupted by user")
            self.cleanup()
            sys.exit(130)
            
        except Exception as e:
            print(f"\n\n[ERROR] Test runner error: {e}")
            self.cleanup()
            sys.exit(1)


def main():
    """Main entry point"""
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
    
    args = parser.parse_args()
    
    # Run test runner
    runner = SystemStartupTestRunner(args)
    runner.run()


if __name__ == "__main__":
    main()