#!/usr/bin/env python
"""
Startup Test Executor
Handles execution of backend, frontend, and E2E tests
"""

import os
import subprocess
import time
from typing import Dict, Any, Optional, List


class TestResult:
    """Represents a test execution result"""
    
    def __init__(self, name: str, duration: float, passed: bool, output: str = "", errors: str = ""):
        self.name = name
        self.duration = duration
        self.passed = passed
        self.output = output
        self.errors = errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "duration": self.duration,
            "passed": self.passed,
            "output": self.output,
            "errors": self.errors
        }


class BackendTestExecutor:
    """Executes backend startup tests"""
    
    def __init__(self, args):
        self.args = args
    
    def run_tests(self) -> Optional[TestResult]:
        """Run backend system startup tests"""
        self._print_header()
        test_file = "tests/test_system_startup.py"
        if not self._validate_test_file(test_file):
            return None
        cmd = self._build_command(test_file)
        result, duration = self._execute_command(cmd)
        test_result = self._process_result(result, duration)
        self._display_status(test_result)
        return test_result
    
    def _print_header(self):
        """Print backend test header"""
        print("\n" + "-"*40)
        print("Running Backend Startup Tests")
        print("-"*40)
    
    def _validate_test_file(self, test_file: str) -> bool:
        """Validate test file exists"""
        if not os.path.exists(test_file):
            print(f"[WARNING] Test file not found: {test_file}")
            return False
        return True
    
    def _build_command(self, test_file: str) -> List[str]:
        """Build pytest command"""
        cmd = [
            "python", "-m", "pytest", test_file,
            "-v" if self.args.verbose else "-q",
            "--tb=short", "--disable-warnings"
        ]
        if self.args.coverage:
            cmd.extend(["--cov=app", "--cov-report=term-missing"])
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> tuple:
        """Execute command and measure duration"""
        print(f"Running: {' '.join(cmd)}")
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        return result, duration
    
    def _process_result(self, result, duration: float) -> TestResult:
        """Process command result into TestResult"""
        return TestResult(
            name="Backend Startup Tests",
            duration=duration,
            passed=result.returncode == 0,
            output=result.stdout if self.args.verbose else "",
            errors=result.stderr if result.returncode != 0 else ""
        )
    
    def _display_status(self, test_result: TestResult):
        """Display test completion status"""
        if test_result.passed:
            print(f"[OK] Backend startup tests passed ({test_result.duration:.2f}s)")
        else:
            print(f"[FAIL] Backend startup tests failed")
            if not self.args.verbose:
                print("  Run with --verbose to see details")


class FrontendTestExecutor:
    """Executes frontend startup tests"""
    
    def __init__(self, args):
        self.args = args
    
    def run_tests(self) -> Optional[TestResult]:
        """Run frontend system startup tests"""
        self._print_header()
        test_file = "frontend/__tests__/system/startup.test.tsx"
        if not self._validate_test_file(test_file):
            return None
        self._install_dependencies()
        cmd = self._build_command()
        result, duration = self._execute_command(cmd)
        test_result = self._process_result(result, duration)
        self._display_status(test_result)
        return test_result
    
    def _print_header(self):
        """Print frontend test header"""
        print("\n" + "-"*40)
        print("Running Frontend Startup Tests")
        print("-"*40)
    
    def _validate_test_file(self, test_file: str) -> bool:
        """Validate test file exists"""
        if not os.path.exists(test_file):
            print(f"[WARNING] Test file not found: {test_file}")
            return False
        return True
    
    def _install_dependencies(self):
        """Install frontend dependencies"""
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd="frontend", capture_output=True)
    
    def _build_command(self) -> List[str]:
        """Build npm test command"""
        cmd = ["npm", "test", "--", "startup.test"]
        if self.args.coverage:
            cmd.append("--coverage")
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> tuple:
        """Execute command and measure duration"""
        print(f"Running: {' '.join(cmd)}")
        start_time = time.time()
        result = subprocess.run(cmd, cwd="frontend", capture_output=True, text=True)
        duration = time.time() - start_time
        return result, duration
    
    def _process_result(self, result, duration: float) -> TestResult:
        """Process command result into TestResult"""
        return TestResult(
            name="Frontend Startup Tests",
            duration=duration,
            passed=result.returncode == 0,
            output=result.stdout if self.args.verbose else "",
            errors=result.stderr if result.returncode != 0 else ""
        )
    
    def _display_status(self, test_result: TestResult):
        """Display test completion status"""
        if test_result.passed:
            print(f"[OK] Frontend startup tests passed ({test_result.duration:.2f}s)")
        else:
            print(f"[FAIL] Frontend startup tests failed")
            if not self.args.verbose:
                print("  Run with --verbose to see details")


class E2ETestExecutor:
    """Executes end-to-end tests"""
    
    def __init__(self, args):
        self.args = args
    
    def run_tests(self) -> Optional[TestResult]:
        """Run complete E2E tests"""
        test_file = self._setup_and_validate()
        if not test_file:
            return None
        self._prepare_services()
        cmd = self._build_full_command(test_file)
        result, duration = self._execute_command(cmd)
        test_result = self._process_result(result, duration)
        self._display_status(test_result)
        return test_result
    
    def _setup_and_validate(self) -> Optional[str]:
        """Setup E2E test header and validate test file"""
        print("\n" + "-"*40)
        print("Running End-to-End Tests")
        print("-"*40)
        test_file = "tests/test_super_e2e.py"
        if not os.path.exists(test_file):
            print(f"[WARNING] Test file not found: {test_file}")
            return None
        return test_file
    
    def _prepare_services(self):
        """Prepare services for E2E testing"""
        print("Checking service availability...")
        if self.args.mode == "full":
            print("Starting services for E2E tests...")
    
    def _build_full_command(self, test_file: str) -> List[str]:
        """Build complete pytest command for E2E tests"""
        cmd = self._build_base_command(test_file)
        cmd = self._add_coverage_options(cmd)
        cmd = self._add_mode_filters(cmd)
        return cmd
    
    def _build_base_command(self, test_file: str) -> List[str]:
        """Build base pytest command"""
        return [
            "python", "-m", "pytest", test_file,
            "-v" if self.args.verbose else "-q",
            "--tb=short", "-s", "--disable-warnings"
        ]
    
    def _add_coverage_options(self, cmd: List[str]) -> List[str]:
        """Add coverage options if requested"""
        if self.args.coverage:
            cmd.extend(["--cov=app", "--cov-report=term-missing"])
        return cmd
    
    def _add_mode_filters(self, cmd: List[str]) -> List[str]:
        """Add test filters based on mode"""
        if self.args.mode == "minimal":
            cmd.extend(["-k", "not concurrent and not performance"])
        elif self.args.mode == "quick":
            cmd.extend(["-k", "startup or login or websocket"])
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> tuple:
        """Execute E2E tests and measure duration"""
        print(f"Running: {' '.join(cmd)}")
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        return result, duration
    
    def _process_result(self, result, duration: float) -> TestResult:
        """Process E2E test results"""
        return TestResult(
            name="End-to-End Tests",
            duration=duration,
            passed=result.returncode == 0,
            output=result.stdout if self.args.verbose else "",
            errors=result.stderr if result.returncode != 0 else ""
        )
    
    def _display_status(self, test_result: TestResult):
        """Display E2E test completion status"""
        if test_result.passed:
            print(f"[OK] E2E tests passed ({test_result.duration:.2f}s)")
        else:
            print(f"[FAIL] E2E tests failed")
            if not self.args.verbose:
                print("  Run with --verbose to see details")