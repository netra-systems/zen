from shared.isolated_environment import get_env
#!/usr/bin/env python
"""
Comprehensive E2E Agent Orchestration Test Runner

This script provides an easy way to execute the comprehensive agent orchestration
test suite with various configurations and real service validations.

Usage:
    python scripts/run_comprehensive_orchestration_tests.py --help
    python scripts/run_comprehensive_orchestration_tests.py --run-all
    python scripts/run_comprehensive_orchestration_tests.py --test-class TestCompleteAgentWorkflow
    python scripts/run_comprehensive_orchestration_tests.py --performance-only
"""

import argparse
import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.service_availability import ensure_real_services_available
from loguru import logger


class ComprehensiveTestRunner:
    """Runner for comprehensive E2E agent orchestration tests."""
    
    def __init__(self):
        self.test_file = "tests/e2e/test_agent_orchestration_e2e_comprehensive.py"
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "execution_time": 0
        }
    
    def setup_environment(self, use_real_services: bool = True) -> None:
        """Set up test environment."""
        if use_real_services:
            os.environ["USE_REAL_SERVICES"] = "1"
            os.environ["USE_REAL_LLM"] = "true"
            os.environ["TEST_USE_REAL_LLM"] = "true"
            os.environ["ENABLE_REAL_LLM_TESTING"] = "true"
            logger.info("[U+1F527] Configured for real services testing")
            
            # Ensure services are available
            logger.info(" SEARCH:  Checking service availability...")
            ensure_real_services_available()
            logger.info(" PASS:  All required services are available")
        else:
            os.environ["USE_REAL_SERVICES"] = "0"
            os.environ["USE_REAL_LLM"] = "false"
            logger.info("[U+1F527] Configured for mock services testing")
    
    def run_single_test(self, test_name: str) -> int:
        """Run a single test method."""
        cmd = [
            "python", "-m", "pytest",
            f"{self.test_file}::{test_name}",
            "-v", "--tb=short", "--timeout=300"
        ]
        
        logger.info(f"[U+1F680] Running single test: {test_name}")
        start_time = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f" PASS:  Test passed in {execution_time:.2f}s")
            else:
                logger.error(f" FAIL:  Test failed in {execution_time:.2f}s")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
            
            return result.returncode
        except Exception as e:
            logger.error(f" FAIL:  Test execution failed: {e}")
            return 1
    
    def run_test_class(self, class_name: str) -> int:
        """Run all tests in a specific class."""
        cmd = [
            "python", "-m", "pytest",
            f"{self.test_file}::{class_name}",
            "-v", "--tb=short", "--timeout=300"
        ]
        
        logger.info(f"[U+1F680] Running test class: {class_name}")
        start_time = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            execution_time = time.time() - start_time
            
            # Parse results from pytest output
            self._parse_pytest_output(result.stdout)
            self.results["execution_time"] = execution_time
            
            if result.returncode == 0:
                logger.info(f" PASS:  Test class completed successfully in {execution_time:.2f}s")
                self._print_results()
            else:
                logger.error(f" FAIL:  Test class failed in {execution_time:.2f}s")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                self._print_results()
            
            return result.returncode
        except Exception as e:
            logger.error(f" FAIL:  Test class execution failed: {e}")
            return 1
    
    def run_all_tests(self) -> int:
        """Run all comprehensive orchestration tests."""
        cmd = [
            "python", "-m", "pytest",
            self.test_file,
            "-v", "--tb=short", "--timeout=600",  # Longer timeout for full suite
            "--maxfail=3"  # Stop after 3 failures
        ]
        
        logger.info("[U+1F680] Running complete comprehensive test suite")
        start_time = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            execution_time = time.time() - start_time
            
            # Parse results from pytest output
            self._parse_pytest_output(result.stdout)
            self.results["execution_time"] = execution_time
            
            if result.returncode == 0:
                logger.info(f" PASS:  Full test suite completed successfully in {execution_time:.2f}s")
                self._print_results()
            else:
                logger.error(f" FAIL:  Test suite failed in {execution_time:.2f}s")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                self._print_results()
            
            return result.returncode
        except Exception as e:
            logger.error(f" FAIL:  Full test suite execution failed: {e}")
            return 1
    
    def run_performance_tests(self) -> int:
        """Run only performance benchmark tests."""
        cmd = [
            "python", "-m", "pytest",
            f"{self.test_file}::TestPerformanceAndProductionReadiness",
            "-v", "--tb=short", "--timeout=300",
            "-m", "performance"
        ]
        
        logger.info("[U+1F680] Running performance benchmark tests")
        start_time = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f" PASS:  Performance tests completed in {execution_time:.2f}s")
            else:
                logger.error(f" FAIL:  Performance tests failed in {execution_time:.2f}s")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
            
            return result.returncode
        except Exception as e:
            logger.error(f" FAIL:  Performance test execution failed: {e}")
            return 1
    
    def _parse_pytest_output(self, output: str) -> None:
        """Parse pytest output to extract test results."""
        lines = output.split('\n')
        for line in lines:
            if "passed" in line and "failed" in line:
                # Example: "3 passed, 1 failed, 2 skipped in 45.67s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed,":
                        self.results["passed"] = int(parts[i-1])
                    elif part == "failed,":
                        self.results["failed"] = int(parts[i-1])
                    elif part == "skipped":
                        self.results["skipped"] = int(parts[i-1])
                break
        
        self.results["total_tests"] = (
            self.results["passed"] + 
            self.results["failed"] + 
            self.results["skipped"]
        )
    
    def _print_results(self) -> None:
        """Print test execution results."""
        print("\n" + "=" * 60)
        print(" TARGET:  COMPREHENSIVE ORCHESTRATION TEST RESULTS")
        print("=" * 60)
        print(f"Total Tests:    {self.results['total_tests']}")
        print(f"Passed:         {self.results['passed']}  PASS: ")
        print(f"Failed:         {self.results['failed']}  FAIL: ")
        print(f"Skipped:        {self.results['skipped']} [U+23ED][U+FE0F]")
        print(f"Execution Time: {self.results['execution_time']:.2f}s")
        
        if self.results["total_tests"] > 0:
            success_rate = self.results["passed"] / self.results["total_tests"] * 100
            print(f"Success Rate:   {success_rate:.1f}%")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive E2E agent orchestration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--run-all", 
        action="store_true",
        help="Run all comprehensive orchestration tests"
    )
    
    parser.add_argument(
        "--test-class",
        type=str,
        help="Run all tests in a specific class (e.g., TestCompleteAgentWorkflow)"
    )
    
    parser.add_argument(
        "--test-method",
        type=str,
        help="Run a specific test method (e.g., test_complex_multi_agent_orchestration_workflow)"
    )
    
    parser.add_argument(
        "--performance-only",
        action="store_true",
        help="Run only performance benchmark tests"
    )
    
    parser.add_argument(
        "--no-real-services",
        action="store_true",
        help="Use mock services instead of real services"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    
    runner = ComprehensiveTestRunner()
    
    # Configure environment
    use_real_services = not args.no_real_services
    runner.setup_environment(use_real_services)
    
    # Execute tests based on arguments
    exit_code = 0
    
    if args.run_all:
        exit_code = runner.run_all_tests()
    elif args.test_class:
        exit_code = runner.run_test_class(args.test_class)
    elif args.test_method:
        exit_code = runner.run_single_test(args.test_method)
    elif args.performance_only:
        exit_code = runner.run_performance_tests()
    else:
        # Default: run workflow test
        print("No specific test specified. Running complex workflow test...")
        exit_code = runner.run_single_test("TestCompleteAgentWorkflow::test_complex_multi_agent_orchestration_workflow")
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
