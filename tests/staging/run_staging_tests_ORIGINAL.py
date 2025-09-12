from shared.isolated_environment import get_env
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
env = get_env()
Staging Test Suite Runner

This script runs the 10 most critical staging tests to validate the staging environment.
Designed to provide comprehensive staging environment validation with clear reporting.

Usage:
    python tests/staging/run_staging_tests.py [options]

Options:
    --test TEST_NAME    Run specific test only
    --parallel          Run tests in parallel (faster)
    --verbose           Verbose output
    --json              Output results in JSON format
    --fail-fast         Stop on first failure
    --timeout SECONDS   Set global timeout (default: 300)

Examples:
    # Run all staging tests
    python tests/staging/run_staging_tests.py
    
    # Run specific test
    python tests/staging/run_staging_tests.py --test jwt_cross_service_auth
    
    # Run with parallel execution
    python tests/staging/run_staging_tests.py --parallel --verbose
    
    # Generate JSON report
    python tests/staging/run_staging_tests.py --json > staging_test_results.json
"""

import sys
import os
import io
import asyncio
import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Set up UTF-8 encoding for Windows console output
if sys.platform == 'win32':
    # Force UTF-8 mode for Windows console
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    # Set environment variable for child processes
    env.set('PYTHONIOENCODING', 'utf-8', "test")

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Test Imports
from tests.staging.test_staging_jwt_cross_service_auth import StagingJWTTestRunner
from tests.staging.test_staging_websocket_agent_events import StagingWebSocketTestRunner
from tests.staging.test_staging_e2e_user_auth_flow import StagingE2EAuthFlowTestRunner
from tests.staging.test_staging_api_endpoints import StagingAPIEndpointsTestRunner
from tests.staging.test_staging_service_health import StagingServiceHealthTestRunner
from tests.staging.test_staging_database_connectivity import StagingDatabaseConnectivityTestRunner
from tests.staging.test_staging_token_validation import StagingTokenValidationTestRunner
from tests.staging.test_staging_configuration import StagingConfigurationTestRunner
from tests.staging.test_staging_agent_execution import StagingAgentExecutionTestRunner
from tests.staging.test_staging_frontend_backend_integration import StagingFrontendBackendIntegrationTestRunner

# Test Suite Configuration
STAGING_TESTS = {
    "jwt_cross_service_auth": {
        "name": "JWT Cross-Service Authentication",
        "runner_class": StagingJWTTestRunner,
        "description": "Validates JWT token synchronization between auth and backend services",
        "critical": True,
        "timeout": 60
    },
    "websocket_agent_events": {
        "name": "WebSocket Agent Events",
        "runner_class": StagingWebSocketTestRunner,
        "description": "Tests WebSocket agent communication flow and required events",
        "critical": True,
        "timeout": 120
    },
    "e2e_user_auth_flow": {
        "name": "E2E User Authentication Flow",
        "runner_class": StagingE2EAuthFlowTestRunner,
        "description": "Complete user registration, login, logout flow validation",
        "critical": True,
        "timeout": 90
    },
    "api_endpoints": {
        "name": "Critical API Endpoints",
        "runner_class": StagingAPIEndpointsTestRunner,
        "description": "Tests all critical API endpoints for functionality and performance",
        "critical": True,
        "timeout": 120
    },
    "service_health": {
        "name": "Service Health Validation",
        "runner_class": StagingServiceHealthTestRunner,
        "description": "Verifies all services are healthy and responding correctly",
        "critical": True,
        "timeout": 90
    },
    "database_connectivity": {
        "name": "Database Connectivity",
        "runner_class": StagingDatabaseConnectivityTestRunner,
        "description": "Tests database operations and connectivity",
        "critical": True,
        "timeout": 120
    },
    "token_validation": {
        "name": "Token Validation",
        "runner_class": StagingTokenValidationTestRunner,
        "description": "Verifies token generation and validation across services",
        "critical": True,
        "timeout": 90
    },
    "configuration": {
        "name": "Staging Configuration",
        "runner_class": StagingConfigurationTestRunner,
        "description": "Validates staging environment configuration",
        "critical": True,
        "timeout": 60
    },
    "agent_execution": {
        "name": "Agent Execution",
        "runner_class": StagingAgentExecutionTestRunner,
        "description": "Tests agent execution end-to-end functionality",
        "critical": True,
        "timeout": 180
    },
    "frontend_backend_integration": {
        "name": "Frontend-Backend Integration",
        "runner_class": StagingFrontendBackendIntegrationTestRunner,
        "description": "Tests frontend-backend communication and integration",
        "critical": True,
        "timeout": 120
    }
}

class StagingTestSuiteRunner:
    """Main test suite runner for staging validation."""
    
    def __init__(self, args):
        self.args = args
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()  # Now defaults to 'staging'
        self.results = {}
        self.start_time = None
        self.total_time = 0
        
    def safe_print(self, text: str, fallback: str = None):
        """Safely print text with Unicode fallback for Windows."""
        try:
            print(text)
        except UnicodeEncodeError:
            if fallback:
                print(fallback)
            else:
                # Remove emojis for fallback
                cleaned_text = text.encode('ascii', 'ignore').decode('ascii')
                print(cleaned_text)
        
    def print_header(self):
        """Print test suite header."""
        print("=" * 80)
        self.safe_print("[U+1F680] NETRA STAGING TEST SUITE", "[ROCKET] NETRA STAGING TEST SUITE")
        print("=" * 80)
        print(f"Environment: {self.environment}")
        print(f"Total Tests: {len(STAGING_TESTS) if not self.args.test else 1}")
        print(f"Mode: {'Parallel' if self.args.parallel else 'Sequential'}")
        print(f"Timeout: {self.args.timeout}s per test")
        print("=" * 80)
        print()
        
    def print_test_start(self, test_key: str, test_config: Dict[str, Any]):
        """Print test start information."""
        if not self.args.verbose:
            return
            
        self.safe_print(f"[U+1F9EA] Starting: {test_config['name']}", f"[TEST] Starting: {test_config['name']}")
        print(f"   Description: {test_config['description']}")
        print(f"   Critical: {'Yes' if test_config['critical'] else 'No'}")
        print(f"   Timeout: {test_config['timeout']}s")
        print()
        
    def print_test_result(self, test_key: str, test_config: Dict[str, Any], result: Dict[str, Any]):
        """Print test result information."""
        success = result.get("summary", {}).get("all_tests_passed", result.get("success", False))
        execution_time = result.get("execution_time", 0)
        
        if success:
            self.safe_print(f" PASS:  PASS {test_config['name']} ({execution_time:.2f}s)",
                          f"[PASS] {test_config['name']} ({execution_time:.2f}s)")
        else:
            self.safe_print(f" FAIL:  FAIL {test_config['name']} ({execution_time:.2f}s)",
                          f"[FAIL] {test_config['name']} ({execution_time:.2f}s)")
        
        if self.args.verbose or not success:
            summary = result.get("summary", {})
            if isinstance(summary, dict):
                passed = summary.get("passed_tests", 0)
                total = summary.get("total_tests", 0)
                print(f"     Sub-tests: {passed}/{total} passed")
                
                # Show critical issues
                if not success:
                    error_keys = [
                        "critical_issue", "critical_failure", "critical_chat_issue",
                        "critical_services_down", "critical_database_failure",
                        "critical_token_failure", "critical_config_issues",
                        "critical_agent_failure", "critical_integration_failure"
                    ]
                    
                    for error_key in error_keys:
                        if summary.get(error_key):
                            print(f"      ALERT:  {error_key.replace('_', ' ').title()}")
                            
        print()
        
    async def run_single_test(self, test_key: str, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test with timeout and error handling."""
        self.print_test_start(test_key, test_config)
        
        start_time = time.time()
        
        try:
            # Create test runner instance
            runner_class = test_config["runner_class"]
            runner = runner_class()
            
            # Run test with timeout
            test_timeout = min(test_config["timeout"], self.args.timeout)
            result = await asyncio.wait_for(
                runner.run_all_tests(),
                timeout=test_timeout
            )
            
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            result["test_key"] = test_key
            result["test_name"] = test_config["name"]
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "test_key": test_key,
                "test_name": test_config["name"],
                "execution_time": execution_time,
                "error": f"Test timed out after {test_timeout}s",
                "summary": {
                    "all_tests_passed": False,
                    "timeout_failure": True
                }
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "test_key": test_key,
                "test_name": test_config["name"],
                "execution_time": execution_time,
                "error": f"Test execution failed: {str(e)}",
                "summary": {
                    "all_tests_passed": False,
                    "execution_failure": True
                }
            }
            
    async def run_tests_sequential(self, tests_to_run: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests sequentially."""
        results = {}
        
        for test_key, test_config in tests_to_run.items():
            result = await self.run_single_test(test_key, test_config)
            results[test_key] = result
            
            self.print_test_result(test_key, test_config, result)
            
            # Stop on first failure if fail-fast is enabled
            if self.args.fail_fast and not result.get("summary", {}).get("all_tests_passed", result.get("success", False)):
                print(f"[U+1F6D1] Stopping due to failure in {test_config['name']} (--fail-fast enabled)")
                break
                
        return results
        
    async def run_tests_parallel(self, tests_to_run: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests in parallel."""
        if self.args.verbose:
            print(" CYCLE:  Running tests in parallel...")
            print()
            
        # Create tasks for all tests
        tasks = {}
        for test_key, test_config in tests_to_run.items():
            tasks[test_key] = asyncio.create_task(
                self.run_single_test(test_key, test_config)
            )
            
        # Wait for all tasks to complete
        results = {}
        completed_tasks = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Process results
        for i, (test_key, test_config) in enumerate(tests_to_run.items()):
            task_result = completed_tasks[i]
            
            if isinstance(task_result, Exception):
                result = {
                    "success": False,
                    "test_key": test_key,
                    "test_name": test_config["name"],
                    "execution_time": 0,
                    "error": f"Task execution failed: {str(task_result)}",
                    "summary": {"all_tests_passed": False, "task_failure": True}
                }
            else:
                result = task_result
                
            results[test_key] = result
            self.print_test_result(test_key, test_config, result)
            
        return results
        
    def generate_summary_report(self, results: Dict[str, Any]):
        """Generate and print summary report."""
        print("=" * 80)
        self.safe_print(" CHART:  STAGING TEST SUITE SUMMARY", "[SUMMARY] STAGING TEST SUITE SUMMARY")
        print("=" * 80)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() 
                          if result.get("summary", {}).get("all_tests_passed", result.get("success", False)))
        failed_tests = total_tests - passed_tests
        
        total_execution_time = sum(result.get("execution_time", 0) for result in results.values())
        
        print(f"Environment: {self.environment}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        print(f"Total Time: {total_execution_time:.2f}s")
        print(f"Suite Time: {self.total_time:.2f}s")
        print()
        
        # Show failed tests
        if failed_tests > 0:
            self.safe_print(" FAIL:  FAILED TESTS:", "[X] FAILED TESTS:")
            for test_key, result in results.items():
                if not result.get("summary", {}).get("all_tests_passed", result.get("success", False)):
                    test_name = result.get("test_name", test_key)
                    error = result.get("error", "Unknown failure")
                    self.safe_print(f"   [U+2022] {test_name}: {error}", f"   * {test_name}: {error}")
            print()
            
        # Critical system status
        critical_issues = []
        for test_key, result in results.items():
            summary = result.get("summary", {})
            if isinstance(summary, dict):
                # Check for critical failures
                critical_keys = [key for key in summary.keys() if "critical" in key and summary[key]]
                if critical_keys:
                    test_name = result.get("test_name", test_key)
                    critical_issues.extend([f"{test_name}: {key}" for key in critical_keys])
                    
        if critical_issues:
            self.safe_print(" ALERT:  CRITICAL ISSUES DETECTED:", "[!] CRITICAL ISSUES DETECTED:")
            for issue in critical_issues:
                self.safe_print(f"   [U+2022] {issue}", f"   * {issue}")
            print()
        else:
            self.safe_print(" PASS:  No critical issues detected", "[OK] No critical issues detected")
            print()
            
        # Overall system status
        system_operational = passed_tests == total_tests and not critical_issues
        if system_operational:
            self.safe_print(" TARGET:  STAGING SYSTEM STATUS:  PASS:  OPERATIONAL",
                          "[TARGET] STAGING SYSTEM STATUS: [OK] OPERATIONAL")
        else:
            self.safe_print(" TARGET:  STAGING SYSTEM STATUS:  FAIL:  ISSUES DETECTED",
                          "[TARGET] STAGING SYSTEM STATUS: [X] ISSUES DETECTED")
        
        if not system_operational:
            print()
            self.safe_print("[U+1F527] RECOMMENDED ACTIONS:", "[TOOLS] RECOMMENDED ACTIONS:")
            if failed_tests > 0:
                print("   1. Review failed test details above")
                print("   2. Check service logs for errors")
                print("   3. Verify staging environment configuration")
            if critical_issues:
                print("   4. Address critical issues immediately")
                print("   5. Re-run tests after fixes")
                
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests/total_tests*100,
            "total_execution_time": total_execution_time,
            "suite_execution_time": self.total_time,
            "system_operational": system_operational,
            "critical_issues": critical_issues
        }
        
    async def run(self):
        """Run the staging test suite."""
        self.start_time = time.time()
        self.print_header()
        
        # Determine tests to run
        if self.args.test:
            if self.args.test not in STAGING_TESTS:
                print(f" FAIL:  Test '{self.args.test}' not found.")
                print(f"Available tests: {', '.join(STAGING_TESTS.keys())}")
                return 1
            tests_to_run = {self.args.test: STAGING_TESTS[self.args.test]}
        else:
            tests_to_run = STAGING_TESTS
            
        # Run tests
        if self.args.parallel and len(tests_to_run) > 1:
            results = await self.run_tests_parallel(tests_to_run)
        else:
            results = await self.run_tests_sequential(tests_to_run)
            
        self.total_time = time.time() - self.start_time
        
        # Generate summary
        summary = self.generate_summary_report(results)
        
        # Output JSON if requested
        if self.args.json:
            output = {
                "environment": self.environment,
                "timestamp": time.time(),
                "summary": summary,
                "test_results": results
            }
            print("\n" + "=" * 80)
            print("[U+1F4C4] JSON OUTPUT:")
            print("=" * 80)
            print(json.dumps(output, indent=2, default=str))
            
        # Return exit code
        return 0 if summary["system_operational"] else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Netra staging validation test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--test",
        help="Run specific test only",
        choices=list(STAGING_TESTS.keys())
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (faster)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Global timeout per test in seconds (default: 300)"
    )
    
    args = parser.parse_args()
    
    # Run the test suite
    runner = StagingTestSuiteRunner(args)
    try:
        exit_code = asyncio.run(runner.run())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        try:
            print("\n[U+1F6D1] Test suite interrupted by user")
        except UnicodeEncodeError:
            print("\n[STOP] Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        try:
            print(f"\n FAIL:  Test suite runner failed: {e}")
        except UnicodeEncodeError:
            print(f"\n[ERROR] Test suite runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()