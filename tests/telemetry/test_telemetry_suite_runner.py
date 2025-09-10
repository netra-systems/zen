"""
Test Suite Runner for OpenTelemetry Automatic Instrumentation Tests

FOCUS: Automatic instrumentation only - provides unified test execution for
the complete OpenTelemetry automatic instrumentation test suite.

Orchestrates execution of unit, integration, E2E, and performance tests for
automatic instrumentation validation across the Netra Apex platform.

Business Value: Platform/Enterprise - Ensures reliable observability testing
for $500K+ ARR chat functionality without manual instrumentation complexity.

CRITICAL: Uses SSOT test infrastructure and UnifiedTestRunner patterns.
Tests are categorized and can be run independently or as complete suite.

Usage:
    python tests/telemetry/test_telemetry_suite_runner.py --all
    python tests/telemetry/test_telemetry_suite_runner.py --unit
    python tests/telemetry/test_telemetry_suite_runner.py --integration  
    python tests/telemetry/test_telemetry_suite_runner.py --e2e
    python tests/telemetry/test_telemetry_suite_runner.py --performance
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from tests.unified_test_runner import UnifiedTestRunner

logger = logging.getLogger(__name__)


class TelemetryTestCategory(Enum):
    """Categories of telemetry tests."""
    UNIT = "unit"
    INTEGRATION = "integration"  
    E2E = "e2e"
    PERFORMANCE = "performance"
    ALL = "all"


@dataclass
class TelemetryTestSuite:
    """Configuration for telemetry test suite."""
    name: str
    category: TelemetryTestCategory
    test_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Required services
    timeout_minutes: int = 10
    parallel_execution: bool = True
    critical: bool = False


class TelemetryTestSuiteRunner(SSotBaseTestCase):
    """Runner for OpenTelemetry automatic instrumentation test suites."""
    
    def __init__(self):
        """Initialize the telemetry test suite runner."""
        super().__init__()
        
        # Define telemetry test suites
        self.telemetry_suites = {
            TelemetryTestCategory.UNIT: TelemetryTestSuite(
                name="OpenTelemetry Auto-Instrumentation Unit Tests",
                category=TelemetryTestCategory.UNIT,
                test_files=[
                    "tests/telemetry/unit/test_opentelemetry_auto_instrumentation_config.py"
                ],
                dependencies=[],  # No external services needed
                timeout_minutes=5,
                parallel_execution=True,
                critical=True
            ),
            
            TelemetryTestCategory.INTEGRATION: TelemetryTestSuite(
                name="OpenTelemetry Auto-Instrumentation Integration Tests",
                category=TelemetryTestCategory.INTEGRATION,
                test_files=[
                    "tests/telemetry/integration/test_opentelemetry_auto_framework_discovery.py",
                    "tests/telemetry/integration/test_opentelemetry_trace_export_validation.py"
                ],
                dependencies=["postgres", "redis"],
                timeout_minutes=15,
                parallel_execution=True,
                critical=True
            ),
            
            TelemetryTestCategory.E2E: TelemetryTestSuite(
                name="OpenTelemetry Golden Path E2E Tests",
                category=TelemetryTestCategory.E2E,
                test_files=[
                    "tests/telemetry/e2e/test_opentelemetry_golden_path_auto_tracing.py"
                ],
                dependencies=["backend", "auth", "postgres", "redis"],
                timeout_minutes=20,
                parallel_execution=False,  # E2E tests run sequentially
                critical=True
            ),
            
            TelemetryTestCategory.PERFORMANCE: TelemetryTestSuite(
                name="OpenTelemetry Auto-Instrumentation Performance Tests",
                category=TelemetryTestCategory.PERFORMANCE,
                test_files=[
                    "tests/telemetry/performance/test_opentelemetry_auto_instrumentation_overhead.py"
                ],
                dependencies=["postgres", "redis"],
                timeout_minutes=30,
                parallel_execution=False,  # Performance tests need isolation
                critical=False  # Performance tests are not blocking
            )
        }
        
    def run_telemetry_test_suite(self, categories: List[TelemetryTestCategory]) -> Dict[str, Any]:
        """
        Run specified telemetry test suites.
        
        Args:
            categories: List of test categories to run
            
        Returns:
            Dict containing test results and metrics
        """
        suite_results = {
            "start_time": time.time(),
            "suites_executed": [],
            "suites_passed": [],
            "suites_failed": [],
            "total_tests_run": 0,
            "total_tests_passed": 0,
            "total_tests_failed": 0,
            "execution_details": {}
        }
        
        # Resolve ALL category
        if TelemetryTestCategory.ALL in categories:
            categories = [
                TelemetryTestCategory.UNIT,
                TelemetryTestCategory.INTEGRATION,
                TelemetryTestCategory.E2E,
                TelemetryTestCategory.PERFORMANCE
            ]
            
        # Execute suites in order (unit -> integration -> e2e -> performance)
        execution_order = [
            TelemetryTestCategory.UNIT,
            TelemetryTestCategory.INTEGRATION,
            TelemetryTestCategory.E2E,
            TelemetryTestCategory.PERFORMANCE
        ]
        
        ordered_categories = [cat for cat in execution_order if cat in categories]
        
        for category in ordered_categories:
            suite = self.telemetry_suites[category]
            logger.info(f"Executing telemetry test suite: {suite.name}")
            
            suite_start_time = time.time()
            
            try:
                # Check dependencies
                dependency_check = self._check_suite_dependencies(suite)
                if not dependency_check["all_available"]:
                    logger.warning(
                        f"Skipping suite {suite.name} - missing dependencies: "
                        f"{dependency_check['missing_dependencies']}"
                    )
                    continue
                    
                # Execute suite
                suite_result = self._execute_test_suite(suite)
                
                # Record results
                suite_duration = time.time() - suite_start_time
                suite_result["execution_time_seconds"] = suite_duration
                
                suite_results["suites_executed"].append(category.value)
                suite_results["execution_details"][category.value] = suite_result
                
                if suite_result["success"]:
                    suite_results["suites_passed"].append(category.value)
                else:
                    suite_results["suites_failed"].append(category.value)
                    
                # Aggregate test counts
                suite_results["total_tests_run"] += suite_result.get("tests_run", 0)
                suite_results["total_tests_passed"] += suite_result.get("tests_passed", 0)
                suite_results["total_tests_failed"] += suite_result.get("tests_failed", 0)
                
                # Stop on critical suite failure
                if not suite_result["success"] and suite.critical:
                    logger.error(f"Critical telemetry suite {suite.name} failed - stopping execution")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing telemetry suite {suite.name}: {e}")
                suite_results["suites_failed"].append(category.value)
                suite_results["execution_details"][category.value] = {
                    "success": False,
                    "error": str(e),
                    "tests_run": 0,
                    "tests_passed": 0,
                    "tests_failed": 0
                }
                
        # Calculate final metrics
        suite_results["end_time"] = time.time()
        suite_results["total_execution_time_seconds"] = (
            suite_results["end_time"] - suite_results["start_time"]
        )
        suite_results["success_rate"] = (
            suite_results["total_tests_passed"] / max(suite_results["total_tests_run"], 1) * 100
        )
        
        return suite_results
        
    def _check_suite_dependencies(self, suite: TelemetryTestSuite) -> Dict[str, Any]:
        """Check if suite dependencies are available."""
        dependency_status = {
            "all_available": True,
            "available_dependencies": [],
            "missing_dependencies": [],
            "dependency_details": {}
        }
        
        # Check Docker services if needed
        if suite.dependencies:
            try:
                from test_framework.unified_docker_manager import UnifiedDockerManager
                docker_manager = UnifiedDockerManager()
                
                for dependency in suite.dependencies:
                    is_available = docker_manager.is_service_healthy(dependency)
                    dependency_status["dependency_details"][dependency] = {
                        "available": is_available,
                        "type": "docker_service"
                    }
                    
                    if is_available:
                        dependency_status["available_dependencies"].append(dependency)
                    else:
                        dependency_status["missing_dependencies"].append(dependency)
                        dependency_status["all_available"] = False
                        
            except ImportError:
                logger.warning("UnifiedDockerManager not available - skipping dependency checks")
                dependency_status["all_available"] = False
                dependency_status["missing_dependencies"] = suite.dependencies
                
        return dependency_status
        
    def _execute_test_suite(self, suite: TelemetryTestSuite) -> Dict[str, Any]:
        """Execute a specific telemetry test suite."""
        suite_result = {
            "success": False,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_files_executed": [],
            "test_failures": [],
            "execution_output": ""
        }
        
        try:
            # Create unified test runner instance
            test_runner = UnifiedTestRunner()
            
            # Configure test execution parameters
            test_params = {
                "real_services": True if suite.dependencies else False,
                "timeout_seconds": suite.timeout_minutes * 60,
                "parallel": suite.parallel_execution,
                "verbose": True,
                "stop_on_first_failure": suite.critical
            }
            
            # Execute each test file in the suite
            all_files_passed = True
            
            for test_file in suite.test_files:
                logger.info(f"Executing telemetry test file: {test_file}")
                
                file_result = self._execute_test_file(test_file, test_params)
                
                suite_result["test_files_executed"].append(test_file)
                suite_result["tests_run"] += file_result.get("tests_run", 0)
                suite_result["tests_passed"] += file_result.get("tests_passed", 0)
                suite_result["tests_failed"] += file_result.get("tests_failed", 0)
                
                if not file_result.get("success", False):
                    all_files_passed = False
                    suite_result["test_failures"].append({
                        "file": test_file,
                        "error": file_result.get("error", "Unknown error"),
                        "failed_tests": file_result.get("failed_tests", [])
                    })
                    
                    # Stop on critical suite failure
                    if suite.critical:
                        break
                        
            suite_result["success"] = all_files_passed
            
        except Exception as e:
            suite_result["success"] = False
            suite_result["test_failures"].append({
                "file": "suite_execution",
                "error": str(e),
                "failed_tests": []
            })
            
        return suite_result
        
    def _execute_test_file(self, test_file: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test file."""
        file_result = {
            "success": False,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failed_tests": [],
            "execution_time_seconds": 0,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            # Use pytest to execute the test file
            import subprocess
            
            # Build pytest command
            pytest_cmd = [
                sys.executable, "-m", "pytest",
                test_file,
                "-v",  # Verbose output
                "--tb=short",  # Short traceback format
                f"--timeout={params['timeout_seconds']}"
            ]
            
            # Add real services flag if needed
            if params.get("real_services"):
                pytest_cmd.extend(["--real-services"])
                
            # Execute pytest
            result = subprocess.run(
                pytest_cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=params["timeout_seconds"]
            )
            
            # Parse pytest output
            file_result = self._parse_pytest_output(result, file_result)
            
        except subprocess.TimeoutExpired:
            file_result["error"] = f"Test file execution timed out after {params['timeout_seconds']} seconds"
            
        except Exception as e:
            file_result["error"] = str(e)
            
        finally:
            file_result["execution_time_seconds"] = time.time() - start_time
            
        return file_result
        
    def _parse_pytest_output(self, result: subprocess.CompletedProcess, file_result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse pytest execution output."""
        
        # Basic success/failure from return code
        file_result["success"] = (result.returncode == 0)
        
        # Parse test counts from output
        output_lines = result.stdout.split('\n') + result.stderr.split('\n')
        
        for line in output_lines:
            line = line.strip()
            
            # Look for pytest summary line
            if " passed" in line or " failed" in line or " error" in line:
                # Parse counts from lines like "3 passed, 1 failed in 2.34s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        try:
                            file_result["tests_passed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                            
                    elif part == "failed" and i > 0:
                        try:
                            file_result["tests_failed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                            
            # Look for individual test failures
            elif "FAILED" in line and "::" in line:
                test_name = line.split("::")[-1].split()[0] if "::" in line else line
                file_result["failed_tests"].append(test_name)
                
        # Calculate total tests run
        file_result["tests_run"] = file_result["tests_passed"] + file_result["tests_failed"]
        
        # Include output for debugging
        if not file_result["success"]:
            file_result["stdout"] = result.stdout
            file_result["stderr"] = result.stderr
            
        return file_result


def main():
    """Main entry point for telemetry test suite runner."""
    parser = argparse.ArgumentParser(
        description="Run OpenTelemetry Automatic Instrumentation Test Suite"
    )
    
    parser.add_argument("--unit", action="store_true", 
                       help="Run unit tests for auto-instrumentation configuration")
    parser.add_argument("--integration", action="store_true",
                       help="Run integration tests for framework discovery")
    parser.add_argument("--e2e", action="store_true",
                       help="Run E2E tests for Golden Path auto-tracing")
    parser.add_argument("--performance", action="store_true",
                       help="Run performance tests for instrumentation overhead")
    parser.add_argument("--all", action="store_true",
                       help="Run all telemetry test suites")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Determine categories to run
    categories = []
    
    if args.unit:
        categories.append(TelemetryTestCategory.UNIT)
    if args.integration:
        categories.append(TelemetryTestCategory.INTEGRATION)
    if args.e2e:
        categories.append(TelemetryTestCategory.E2E)
    if args.performance:
        categories.append(TelemetryTestCategory.PERFORMANCE)
    if args.all:
        categories.append(TelemetryTestCategory.ALL)
        
    # Default to all if no specific categories selected
    if not categories:
        categories.append(TelemetryTestCategory.ALL)
        
    # Execute test suites
    runner = TelemetryTestSuiteRunner()
    
    logger.info(f"Starting OpenTelemetry automatic instrumentation test execution")
    logger.info(f"Categories: {[cat.value for cat in categories]}")
    
    results = runner.run_telemetry_test_suite(categories)
    
    # Print results summary
    print("\n" + "="*80)
    print("OPENTELEMETRY AUTOMATIC INSTRUMENTATION TEST SUITE RESULTS")
    print("="*80)
    print(f"Total Execution Time: {results['total_execution_time_seconds']:.2f} seconds")
    print(f"Test Suites Executed: {len(results['suites_executed'])}")
    print(f"Test Suites Passed: {len(results['suites_passed'])}")
    print(f"Test Suites Failed: {len(results['suites_failed'])}")
    print(f"Total Tests Run: {results['total_tests_run']}")
    print(f"Total Tests Passed: {results['total_tests_passed']}")
    print(f"Total Tests Failed: {results['total_tests_failed']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    
    # Print detailed results
    if results['suites_failed']:
        print(f"\nFAILED SUITES:")
        for suite_name in results['suites_failed']:
            suite_detail = results['execution_details'].get(suite_name, {})
            print(f"  - {suite_name}: {suite_detail.get('error', 'Unknown error')}")
            
            failures = suite_detail.get('test_failures', [])
            for failure in failures:
                print(f"    * {failure['file']}: {failure['error']}")
                
    if results['suites_passed']:
        print(f"\nPASSED SUITES:")
        for suite_name in results['suites_passed']:
            suite_detail = results['execution_details'].get(suite_name, {})
            execution_time = suite_detail.get('execution_time_seconds', 0)
            tests_run = suite_detail.get('tests_run', 0)
            print(f"  - {suite_name}: {tests_run} tests in {execution_time:.2f}s")
            
    print("="*80)
    
    # Exit with appropriate code
    exit_code = 0 if len(results['suites_failed']) == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()