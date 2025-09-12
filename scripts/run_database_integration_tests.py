#!/usr/bin/env python3
"""DatabaseManager Integration Test Runner

CRITICAL: Comprehensive test runner for DatabaseManager integration tests.
Validates all test scenarios are deterministic and can run independently.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Ensure database integration tests provide reliable validation
- Value Impact: Prevents database-related production failures through comprehensive testing  
- Strategic Impact: Database layer is foundation - must be thoroughly validated

USAGE:
    python scripts/run_database_integration_tests.py --all
    python scripts/run_database_integration_tests.py --comprehensive
    python scripts/run_database_integration_tests.py --stress
    python scripts/run_database_integration_tests.py --business-scenarios
    python scripts/run_database_integration_tests.py --validate-independence

CRITICAL: Follows CLAUDE.md requirements for test execution and validation
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class DatabaseIntegrationTestRunner:
    """Comprehensive test runner for DatabaseManager integration tests."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_results = {
            "comprehensive": {},
            "stress": {},
            "business_scenarios": {},
            "independence_validation": {}
        }
        
        # Test file paths
        self.test_files = {
            "comprehensive": "netra_backend/tests/integration/test_database_manager_integration_comprehensive.py",
            "stress": "netra_backend/tests/integration/test_database_manager_stress_scenarios.py", 
            "business_scenarios": "netra_backend/tests/integration/test_database_manager_business_scenarios.py"
        }
    
    def setup_logging(self, verbose: bool = False):
        """Set up logging configuration."""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.project_root / "logs" / "database_integration_tests.log")
            ]
        )
        
        # Create logs directory if it doesn't exist
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
    
    def validate_test_environment(self) -> bool:
        """Validate that test environment is properly configured."""
        logger.info("Validating test environment configuration...")
        
        # Check that test files exist
        for test_name, test_path in self.test_files.items():
            full_path = self.project_root / test_path
            if not full_path.exists():
                logger.error(f"Test file not found: {full_path}")
                return False
        
        # Check test framework utilities exist
        utilities_path = self.project_root / "test_framework" / "database_test_utilities.py"
        if not utilities_path.exists():
            logger.error(f"Database test utilities not found: {utilities_path}")
            return False
        
        # Validate pytest is available
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode != 0:
                logger.error("pytest not available or not working")
                return False
        except Exception as e:
            logger.error(f"Failed to check pytest availability: {e}")
            return False
        
        logger.info("Test environment validation passed")
        return True
    
    def run_test_suite(self, test_name: str, additional_args: List[str] = None) -> Dict[str, Any]:
        """Run a specific test suite and return results."""
        if test_name not in self.test_files:
            raise ValueError(f"Unknown test suite: {test_name}")
        
        test_path = self.project_root / self.test_files[test_name]
        logger.info(f"Running {test_name} test suite: {test_path}")
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "-s",  # Don't capture output
            "--maxfail=5",  # Stop after 5 failures
            "--durations=10",  # Show 10 slowest tests
        ]
        
        # Add additional arguments
        if additional_args:
            cmd.extend(additional_args)
        
        # Run tests
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=1800  # 30 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            test_results = {
                "success": result.returncode == 0,
                "execution_time": execution_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
            # Extract test statistics from output
            stdout_lines = result.stdout.split('\n')
            for line in stdout_lines:
                if " passed" in line or " failed" in line or " error" in line:
                    test_results["summary_line"] = line.strip()
                    break
            
            logger.info(f"{test_name} test suite completed in {execution_time:.2f}s")
            if test_results["success"]:
                logger.info(f"{test_name} tests: PASSED")
            else:
                logger.error(f"{test_name} tests: FAILED (return code: {result.returncode})")
                logger.error(f"STDERR: {result.stderr}")
            
            return test_results
            
        except subprocess.TimeoutExpired:
            logger.error(f"{test_name} test suite timed out after 30 minutes")
            return {
                "success": False,
                "execution_time": 1800,
                "error": "Test suite timed out",
                "return_code": -1
            }
        
        except Exception as e:
            logger.error(f"Failed to run {test_name} test suite: {e}")
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "return_code": -1
            }
    
    def run_comprehensive_tests(self) -> bool:
        """Run comprehensive integration tests."""
        logger.info("=" * 60)
        logger.info("RUNNING COMPREHENSIVE INTEGRATION TESTS")
        logger.info("=" * 60)
        
        result = self.run_test_suite("comprehensive", [
            "--markers", "integration",
            "-k", "not stress"  # Exclude stress tests from comprehensive run
        ])
        
        self.test_results["comprehensive"] = result
        return result["success"]
    
    def run_stress_tests(self) -> bool:
        """Run stress testing scenarios."""
        logger.info("=" * 60)
        logger.info("RUNNING STRESS TEST SCENARIOS")
        logger.info("=" * 60)
        
        result = self.run_test_suite("stress", [
            "--markers", "integration",
            "-k", "stress"
        ])
        
        self.test_results["stress"] = result
        return result["success"]
    
    def run_business_scenario_tests(self) -> bool:
        """Run business scenario tests."""
        logger.info("=" * 60)
        logger.info("RUNNING BUSINESS SCENARIO TESTS")
        logger.info("=" * 60)
        
        result = self.run_test_suite("business_scenarios", [
            "--markers", "integration"
        ])
        
        self.test_results["business_scenarios"] = result
        return result["success"]
    
    def validate_test_independence(self) -> bool:
        """Validate that tests can run independently and are deterministic."""
        logger.info("=" * 60)
        logger.info("VALIDATING TEST INDEPENDENCE AND DETERMINISM")
        logger.info("=" * 60)
        
        # Run each test file multiple times to check for determinism
        independence_results = {}
        
        for test_name in ["comprehensive", "business_scenarios"]:  # Skip stress tests for independence check
            logger.info(f"Testing independence for {test_name}...")
            
            # Run the same test 3 times
            run_results = []
            for run_num in range(3):
                logger.info(f"  Independence run {run_num + 1}/3 for {test_name}")
                
                result = self.run_test_suite(test_name, [
                    "--markers", "integration",
                    "-q",  # Quiet mode for independence testing
                    "--tb=no"  # No traceback for independence testing
                ])
                
                run_results.append({
                    "success": result["success"],
                    "execution_time": result["execution_time"],
                    "return_code": result["return_code"]
                })
                
                # Add delay between runs to ensure cleanup
                time.sleep(2)
            
            # Analyze independence results
            all_successful = all(r["success"] for r in run_results)
            execution_times = [r["execution_time"] for r in run_results]
            avg_time = sum(execution_times) / len(execution_times)
            time_variance = sum((t - avg_time) ** 2 for t in execution_times) / len(execution_times)
            time_coefficient_of_variation = (time_variance ** 0.5) / avg_time if avg_time > 0 else 0
            
            independence_results[test_name] = {
                "all_runs_successful": all_successful,
                "run_results": run_results,
                "avg_execution_time": avg_time,
                "time_variance": time_variance,
                "time_coefficient_of_variation": time_coefficient_of_variation,
                "deterministic": time_coefficient_of_variation < 0.3  # Less than 30% variation
            }
            
            logger.info(f"  {test_name} independence results:")
            logger.info(f"    All runs successful: {all_successful}")
            logger.info(f"    Average time: {avg_time:.2f}s")
            logger.info(f"    Time variation: {time_coefficient_of_variation:.2%}")
            logger.info(f"    Deterministic: {independence_results[test_name]['deterministic']}")
        
        self.test_results["independence_validation"] = independence_results
        
        # Overall independence validation
        all_independent = all(
            result["all_runs_successful"] and result["deterministic"]
            for result in independence_results.values()
        )
        
        if all_independent:
            logger.info("[U+2713] All tests are independent and deterministic")
        else:
            logger.error("[U+2717] Some tests are not independent or deterministic")
        
        return all_independent
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""
        report_lines = [
            "=" * 80,
            "DATABASE MANAGER INTEGRATION TEST REPORT",
            "=" * 80,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        
        # Overall summary
        total_suites = len([r for r in self.test_results.values() if r])
        successful_suites = len([
            r for r in self.test_results.values() 
            if r and r.get("success", False)
        ])
        
        report_lines.extend([
            "OVERALL SUMMARY:",
            f"  Test Suites Run: {total_suites}",
            f"  Successful Suites: {successful_suites}",
            f"  Success Rate: {(successful_suites/total_suites*100) if total_suites > 0 else 0:.1f}%",
            ""
        ])
        
        # Individual suite results
        for suite_name, result in self.test_results.items():
            if not result:
                continue
                
            report_lines.extend([
                f"{suite_name.upper().replace('_', ' ')} TESTS:",
                f"  Status: {'[U+2713] PASSED' if result.get('success') else '[U+2717] FAILED'}",
                f"  Execution Time: {result.get('execution_time', 0):.2f}s",
            ])
            
            if "summary_line" in result:
                report_lines.append(f"  Summary: {result['summary_line']}")
            
            if not result.get('success') and result.get('error'):
                report_lines.append(f"  Error: {result['error']}")
            
            report_lines.append("")
        
        # Independence validation results
        if "independence_validation" in self.test_results and self.test_results["independence_validation"]:
            report_lines.extend([
                "TEST INDEPENDENCE VALIDATION:",
                ""
            ])
            
            for test_name, independence_data in self.test_results["independence_validation"].items():
                report_lines.extend([
                    f"  {test_name.upper()}:",
                    f"    All Runs Successful: {independence_data['all_runs_successful']}",
                    f"    Deterministic: {independence_data['deterministic']}",
                    f"    Average Execution Time: {independence_data['avg_execution_time']:.2f}s",
                    f"    Time Variation: {independence_data['time_coefficient_of_variation']:.2%}",
                    ""
                ])
        
        # Recommendations
        report_lines.extend([
            "RECOMMENDATIONS:",
        ])
        
        if successful_suites == total_suites:
            report_lines.append("  [U+2713] All database integration tests are passing")
            report_lines.append("  [U+2713] Database layer is ready for production deployment")
        else:
            report_lines.append("  [U+2717] Some tests failed - investigate and fix before deployment")
            report_lines.append("  [U+2717] Database layer may have reliability issues")
        
        if (self.test_results.get("independence_validation") and 
            all(r["deterministic"] for r in self.test_results["independence_validation"].values())):
            report_lines.append("  [U+2713] Tests are deterministic and can be run reliably in CI/CD")
        else:
            report_lines.append("   WARNING:  Some tests may have non-deterministic behavior")
        
        report_lines.extend([
            "",
            "=" * 80,
            "END OF REPORT",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def save_test_report(self, report: str, filename: str = None) -> str:
        """Save test report to file."""
        if filename is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"database_integration_test_report_{timestamp}.md"
        
        reports_dir = self.project_root / "reports" / "testing"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = reports_dir / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Test report saved to: {report_path}")
        return str(report_path)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run DatabaseManager integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Run all test suites (comprehensive, stress, business scenarios, independence validation)"
    )
    
    parser.add_argument(
        "--comprehensive",
        action="store_true", 
        help="Run comprehensive integration tests"
    )
    
    parser.add_argument(
        "--stress",
        action="store_true",
        help="Run stress testing scenarios"
    )
    
    parser.add_argument(
        "--business-scenarios", 
        action="store_true",
        help="Run business scenario tests"
    )
    
    parser.add_argument(
        "--validate-independence",
        action="store_true",
        help="Validate test independence and determinism"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true", 
        help="Generate report from previous test results (don't run tests)"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = DatabaseIntegrationTestRunner()
    runner.setup_logging(args.verbose)
    
    logger.info("Starting DatabaseManager Integration Test Runner")
    
    if not args.report_only:
        # Validate test environment
        if not runner.validate_test_environment():
            logger.error("Test environment validation failed")
            sys.exit(1)
        
        # Determine which tests to run
        run_comprehensive = args.all or args.comprehensive
        run_stress = args.all or args.stress
        run_business = args.all or args.business_scenarios
        run_independence = args.all or args.validate_independence
        
        # If no specific tests specified, run comprehensive by default
        if not any([run_comprehensive, run_stress, run_business, run_independence]):
            run_comprehensive = True
            logger.info("No specific test suite specified, running comprehensive tests")
        
        # Run selected test suites
        overall_success = True
        
        if run_comprehensive:
            success = runner.run_comprehensive_tests()
            overall_success = overall_success and success
        
        if run_stress:
            success = runner.run_stress_tests()
            overall_success = overall_success and success
        
        if run_business:
            success = runner.run_business_scenario_tests()
            overall_success = overall_success and success
        
        if run_independence:
            success = runner.validate_test_independence()
            overall_success = overall_success and success
        
        # Log overall results
        if overall_success:
            logger.info(" CELEBRATION:  All selected test suites PASSED!")
        else:
            logger.error(" FAIL:  Some test suites FAILED!")
    
    # Generate and save report
    report = runner.generate_test_report()
    report_path = runner.save_test_report(report)
    
    print("\n" + report)
    print(f"\nDetailed report saved to: {report_path}")
    
    # Exit with appropriate code
    if args.report_only:
        sys.exit(0)
    else:
        overall_success = all(
            result.get("success", True) 
            for result in runner.test_results.values() 
            if result
        )
        sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()