#!/usr/bin/env python3
"""
Database API Compatibility Test Runner
Comprehensive runner for all database API compatibility test suites.

This script runs the 4 test suites created for GitHub issue #122:
1. Immediate Bug Reproduction (staging API compatibility)
2. SSOT Database Operations (consolidated patterns)
3. Golden Path E2E Database Flow (complete user journeys)
4. Dependency Regression Prevention (upgrade safety)

Usage:
    python scripts/run_database_api_compatibility_tests.py
    python scripts/run_database_api_compatibility_tests.py --suite staging
    python scripts/run_database_api_compatibility_tests.py --environment staging
    python scripts/run_database_api_compatibility_tests.py --real-services
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.unified_test_runner import UnifiedTestRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseAPICompatibilityTestRunner:
    """
    Comprehensive test runner for database API compatibility test suites.
    
    This runner orchestrates the execution of all 4 test suites created
    to address SQLAlchemy 2.0+ and Redis 6.4.0+ compatibility issues.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_suites = {
            "staging": {
                "path": "tests/integration/database/test_staging_api_compatibility.py",
                "description": "Immediate Bug Reproduction - Staging API Compatibility",
                "critical": True,
                "environment": "test"  # Can be overridden to staging
            },
            "ssot": {
                "path": "tests/integration/database/test_database_operations_ssot.py", 
                "description": "SSOT Database Operations - Consolidated Patterns",
                "critical": True,
                "environment": "test"
            },
            "golden_path": {
                "path": "tests/e2e/staging/test_golden_path_database_flow.py",
                "description": "Golden Path E2E Database Flow - Complete User Journeys",
                "critical": True,
                "environment": "test"  # Can be overridden to staging
            },
            "regression": {
                "path": "tests/integration/dependencies/test_api_compatibility_regression.py",
                "description": "Dependency Regression Prevention - Upgrade Safety",
                "critical": True,
                "environment": "test"
            }
        }
        
    def create_test_runner(self, environment: str = "test", real_services: bool = False) -> UnifiedTestRunner:
        """Create configured UnifiedTestRunner instance."""
        runner = UnifiedTestRunner()
        
        # Configure environment
        os.environ["TEST_ENV"] = environment
        if real_services:
            os.environ["USE_REAL_SERVICES"] = "1"
            
        return runner
    
    async def run_single_suite(self, suite_name: str, environment: str = "test", real_services: bool = False) -> Dict:
        """Run a single test suite and return results."""
        if suite_name not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite_name}. Available: {list(self.test_suites.keys())}")
        
        suite = self.test_suites[suite_name]
        test_path = self.project_root / suite["path"]
        
        if not test_path.exists():
            raise FileNotFoundError(f"Test file not found: {test_path}")
        
        logger.info(f"[U+1F680] Running {suite['description']}")
        logger.info(f"[U+1F4C1] Test path: {test_path}")
        logger.info(f"[U+1F30D] Environment: {environment}")
        logger.info(f"[U+1F527] Real services: {real_services}")
        
        # Create test runner
        runner = self.create_test_runner(environment, real_services)
        
        # Run the specific test file
        start_time = time.time()
        try:
            # Use pytest to run the specific test file
            import pytest
            
            # Build pytest arguments
            pytest_args = [
                str(test_path),
                "-v",
                "--tb=short",
                f"--junit-xml={self.project_root}/test-results/{suite_name}_results.xml"
            ]
            
            if environment == "staging":
                pytest_args.extend(["--slow", "--timeout=300"])
            
            # Run pytest
            exit_code = pytest.main(pytest_args)
            
            execution_time = time.time() - start_time
            
            result = {
                "suite": suite_name,
                "description": suite["description"],
                "path": str(test_path),
                "environment": environment,
                "real_services": real_services,
                "exit_code": exit_code,
                "execution_time": execution_time,
                "success": exit_code == 0,
                "critical": suite["critical"]
            }
            
            if result["success"]:
                logger.info(f" PASS:  {suite['description']} - PASSED ({execution_time:.2f}s)")
            else:
                logger.error(f" FAIL:  {suite['description']} - FAILED ({execution_time:.2f}s)")
                
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[U+1F4A5] {suite['description']} - ERROR: {e}")
            
            return {
                "suite": suite_name,
                "description": suite["description"],
                "path": str(test_path),
                "environment": environment,
                "real_services": real_services,
                "exit_code": 1,
                "execution_time": execution_time,
                "success": False,
                "critical": suite["critical"],
                "error": str(e)
            }
    
    async def run_all_suites(self, environment: str = "test", real_services: bool = False, fail_fast: bool = True) -> Dict:
        """Run all test suites and return comprehensive results."""
        logger.info("[U+1F9EA] Starting Database API Compatibility Test Suite")
        logger.info(f"[U+1F4CB] Running {len(self.test_suites)} test suites")
        logger.info(f"[U+1F30D] Environment: {environment}")
        logger.info(f"[U+1F527] Real services: {real_services}")
        logger.info(f" LIGHTNING:  Fail fast: {fail_fast}")
        
        overall_start_time = time.time()
        results = []
        critical_failures = []
        
        # Run each test suite
        for suite_name, suite_config in self.test_suites.items():
            logger.info(f"\n{'='*80}")
            logger.info(f" SEARCH:  Test Suite: {suite_name.upper()}")
            logger.info(f"{'='*80}")
            
            try:
                result = await self.run_single_suite(suite_name, environment, real_services)
                results.append(result)
                
                # Check for critical failures
                if not result["success"] and result["critical"]:
                    critical_failures.append(result)
                    
                    if fail_fast:
                        logger.error(f"[U+1F4A5] Critical test suite failed, stopping execution: {suite_name}")
                        break
                        
            except Exception as e:
                logger.error(f"[U+1F4A5] Failed to run test suite {suite_name}: {e}")
                
                error_result = {
                    "suite": suite_name,
                    "description": suite_config["description"],
                    "success": False,
                    "critical": suite_config["critical"],
                    "error": str(e),
                    "execution_time": 0
                }
                results.append(error_result)
                
                if suite_config["critical"] and fail_fast:
                    break
        
        overall_execution_time = time.time() - overall_start_time
        
        # Calculate summary statistics
        total_suites = len(results)
        passed_suites = sum(1 for r in results if r["success"])
        failed_suites = total_suites - passed_suites
        critical_failures_count = len(critical_failures)
        
        summary = {
            "total_suites": total_suites,
            "passed_suites": passed_suites,
            "failed_suites": failed_suites,
            "critical_failures": critical_failures_count,
            "overall_success": critical_failures_count == 0,
            "execution_time": overall_execution_time,
            "environment": environment,
            "real_services": real_services,
            "results": results
        }
        
        # Print summary
        self.print_summary(summary)
        
        return summary
    
    def print_summary(self, summary: Dict):
        """Print comprehensive test results summary."""
        logger.info(f"\n{'='*80}")
        logger.info(" CHART:  DATABASE API COMPATIBILITY TEST RESULTS SUMMARY")
        logger.info(f"{'='*80}")
        
        logger.info(f"[U+1F30D] Environment: {summary['environment']}")
        logger.info(f"[U+1F527] Real Services: {summary['real_services']}")
        logger.info(f"[U+23F1][U+FE0F] Total Execution Time: {summary['execution_time']:.2f}s")
        logger.info(f"[U+1F4CB] Total Suites: {summary['total_suites']}")
        logger.info(f" PASS:  Passed: {summary['passed_suites']}")
        logger.info(f" FAIL:  Failed: {summary['failed_suites']}")
        logger.info(f"[U+1F4A5] Critical Failures: {summary['critical_failures']}")
        
        overall_status = "SUCCESS" if summary["overall_success"] else "FAILURE"
        status_icon = " PASS: " if summary["overall_success"] else "[U+1F4A5]"
        logger.info(f"\n{status_icon} OVERALL STATUS: {overall_status}")
        
        # Detailed results
        logger.info(f"\n[U+1F4CB] DETAILED RESULTS:")
        for result in summary["results"]:
            status_icon = " PASS: " if result["success"] else " FAIL: "
            critical_marker = " FIRE: " if result["critical"] else "[U+1F538]"
            
            logger.info(f"{status_icon} {critical_marker} {result['suite'].upper()}: {result['description']}")
            logger.info(f"   [U+23F1][U+FE0F] Time: {result.get('execution_time', 0):.2f}s")
            
            if not result["success"] and "error" in result:
                logger.info(f"   [U+1F4AC] Error: {result['error']}")
        
        # GitHub issue context
        logger.info(f"\n TARGET:  GITHUB ISSUE #122 CONTEXT:")
        logger.info(f"   [U+1F4DD] Issue: Database API Compatibility (SQLAlchemy 2.0+ / Redis 6.4.0+)")
        logger.info(f"   [U+1F517] Root Cause: SSOT violations with 30+ files using scattered patterns") 
        logger.info(f"   [U+1F6E0][U+FE0F] Solution: Implement comprehensive test coverage for API changes")
        
        if summary["overall_success"]:
            logger.info(f"    PASS:  All critical compatibility tests PASSED")
            logger.info(f"   [U+1F680] Safe to deploy with modern dependency versions")
        else:
            logger.info(f"    FAIL:  Critical compatibility issues detected")
            logger.info(f"    WARNING: [U+FE0F] Deployment blocked until issues are resolved")
    
    def create_junit_xml_report(self, summary: Dict, output_path: Path):
        """Create JUnit XML report for CI/CD integration."""
        try:
            from xml.etree.ElementTree import Element, SubElement, tostring
            import xml.etree.ElementTree as ET
            
            # Create root testsuite element
            testsuite = Element("testsuite")
            testsuite.set("name", "Database API Compatibility Tests")
            testsuite.set("tests", str(summary["total_suites"]))
            testsuite.set("failures", str(summary["failed_suites"]))
            testsuite.set("time", str(summary["execution_time"]))
            testsuite.set("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
            
            # Add properties
            properties = SubElement(testsuite, "properties")
            
            prop_env = SubElement(properties, "property")
            prop_env.set("name", "environment")
            prop_env.set("value", summary["environment"])
            
            prop_services = SubElement(properties, "property") 
            prop_services.set("name", "real_services")
            prop_services.set("value", str(summary["real_services"]))
            
            # Add test cases
            for result in summary["results"]:
                testcase = SubElement(testsuite, "testcase")
                testcase.set("name", result["suite"])
                testcase.set("classname", f"DatabaseAPICompatibility.{result['suite']}")
                testcase.set("time", str(result.get("execution_time", 0)))
                
                if not result["success"]:
                    failure = SubElement(testcase, "failure")
                    failure.set("message", f"Test suite {result['suite']} failed")
                    failure.text = result.get("error", "Unknown error")
            
            # Write XML to file
            tree = ET.ElementTree(testsuite)
            tree.write(output_path, encoding="utf-8", xml_declaration=True)
            logger.info(f" CHART:  JUnit XML report written to: {output_path}")
            
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] Failed to create JUnit XML report: {e}")

async def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Database API Compatibility Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_database_api_compatibility_tests.py
  python scripts/run_database_api_compatibility_tests.py --suite staging
  python scripts/run_database_api_compatibility_tests.py --environment staging --real-services
  python scripts/run_database_api_compatibility_tests.py --suite golden_path --environment staging
        """
    )
    
    parser.add_argument(
        "--suite",
        choices=["staging", "ssot", "golden_path", "regression", "all"],
        default="all",
        help="Specific test suite to run (default: all)"
    )
    
    parser.add_argument(
        "--environment", 
        choices=["test", "staging", "production"],
        default="test",
        help="Test environment (default: test)"
    )
    
    parser.add_argument(
        "--real-services",
        action="store_true",
        help="Use real services instead of mocks"
    )
    
    parser.add_argument(
        "--no-fail-fast",
        action="store_true", 
        help="Continue running tests even after critical failures"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test-results"),
        help="Output directory for test results (default: test-results)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    args.output_dir.mkdir(exist_ok=True)
    
    # Create test runner
    runner = DatabaseAPICompatibilityTestRunner()
    
    try:
        if args.suite == "all":
            # Run all test suites
            summary = await runner.run_all_suites(
                environment=args.environment,
                real_services=args.real_services,
                fail_fast=not args.no_fail_fast
            )
            
            # Create JUnit XML report
            junit_path = args.output_dir / "database_api_compatibility_results.xml"
            runner.create_junit_xml_report(summary, junit_path)
            
            # Exit with appropriate code
            exit_code = 0 if summary["overall_success"] else 1
            
        else:
            # Run single test suite
            result = await runner.run_single_suite(
                args.suite,
                environment=args.environment,
                real_services=args.real_services
            )
            
            # Create simple summary for single suite
            summary = {
                "total_suites": 1,
                "passed_suites": 1 if result["success"] else 0,
                "failed_suites": 0 if result["success"] else 1,
                "critical_failures": 0 if result["success"] or not result["critical"] else 1,
                "overall_success": result["success"],
                "execution_time": result["execution_time"],
                "environment": args.environment,
                "real_services": args.real_services,
                "results": [result]
            }
            
            runner.print_summary(summary)
            exit_code = 0 if result["success"] else 1
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("\n WARNING: [U+FE0F] Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"[U+1F4A5] Fatal error running database API compatibility tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())