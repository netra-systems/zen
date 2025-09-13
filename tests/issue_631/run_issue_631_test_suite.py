#!/usr/bin/env python3
"""
Issue #631 Test Suite Runner

Executes comprehensive test suite for HTTP 403 WebSocket authentication failures.

Business Value:
- Validates $500K+ ARR chat functionality auth integration
- Reproduces and validates fix for WebSocket 403 errors
- Ensures AUTH_SERVICE_URL configuration is working

Usage:
    python tests/issue_631/run_issue_631_test_suite.py [--category unit|integration|e2e|all]
    python tests/issue_631/run_issue_631_test_suite.py --staging-only
    python tests/issue_631/run_issue_631_test_suite.py --failing-only
"""

import sys
import os
import subprocess
import argparse
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Issue631TestRunner:
    """Test runner for Issue #631 HTTP 403 WebSocket authentication failures."""

    def __init__(self):
        self.project_root = project_root
        self.test_base_path = self.project_root / "tests"
        
        # Test categories and their paths
        self.test_categories = {
            "unit": self.test_base_path / "unit" / "issue_631",
            "integration": self.test_base_path / "integration" / "issue_631", 
            "e2e": self.test_base_path / "e2e" / "staging" / "issue_631"
        }

    def run_unit_tests(self) -> bool:
        """
        Run unit tests for AUTH_SERVICE_URL configuration validation.
        
        Expected to FAIL until AUTH_SERVICE_URL configuration is implemented.
        """
        logger.info("Running Issue #631 Unit Tests - AUTH_SERVICE_URL Configuration")
        logger.warning("EXPECTED: These tests should FAIL until configuration is fixed")
        
        unit_test_path = self.test_categories["unit"]
        if not unit_test_path.exists():
            logger.error(f"Unit test path does not exist: {unit_test_path}")
            return False
        
        cmd = [
            "python", "-m", "pytest",
            str(unit_test_path),
            "-v",
            "--tb=short",
            "-x",  # Stop on first failure to see configuration issues clearly
            "--no-header",
            "--no-summary"
        ]
        
        return self._run_test_command(cmd, "Unit Tests")

    def run_integration_tests(self) -> bool:
        """
        Run integration tests for service-to-service authentication.
        
        Expected to FAIL until backend-auth service communication works.
        """
        logger.info("Running Issue #631 Integration Tests - Service Communication")
        logger.warning("EXPECTED: These tests should FAIL until service integration is fixed")
        
        integration_test_path = self.test_categories["integration"]
        if not integration_test_path.exists():
            logger.error(f"Integration test path does not exist: {integration_test_path}")
            return False
        
        cmd = [
            "python", "-m", "pytest",
            str(integration_test_path),
            "-v",
            "--tb=short",
            "-s",  # Show output for integration debugging
            "--no-header"
        ]
        
        return self._run_test_command(cmd, "Integration Tests")

    def run_e2e_staging_tests(self) -> bool:
        """
        Run E2E staging tests to reproduce HTTP 403 errors.
        
        These tests reproduce the actual issue in staging environment.
        """
        logger.info("Running Issue #631 E2E Staging Tests - HTTP 403 Reproduction")
        logger.warning("These tests reproduce actual HTTP 403 errors in staging")
        
        e2e_test_path = self.test_categories["e2e"]
        if not e2e_test_path.exists():
            logger.error(f"E2E test path does not exist: {e2e_test_path}")
            return False
        
        cmd = [
            "python", "-m", "pytest",
            str(e2e_test_path),
            "-v",
            "--tb=line",
            "-s",  # Show detailed output for staging reproduction
            "--no-header",
            "-m", "not slow"  # Skip slow tests unless explicitly requested
        ]
        
        return self._run_test_command(cmd, "E2E Staging Tests")

    def run_all_tests(self) -> dict:
        """Run all Issue #631 tests in sequence."""
        logger.info("Running Complete Issue #631 Test Suite")
        logger.info("=" * 60)
        
        results = {}
        
        # Run unit tests first (fastest failure feedback)
        logger.info("Phase 1: Unit Tests (Configuration Validation)")
        results["unit"] = self.run_unit_tests()
        
        # Run integration tests
        logger.info("\nPhase 2: Integration Tests (Service Communication)")
        results["integration"] = self.run_integration_tests()
        
        # Run E2E staging tests
        logger.info("\nPhase 3: E2E Staging Tests (Live Reproduction)")
        results["e2e"] = self.run_e2e_staging_tests()
        
        return results

    def run_failing_only_tests(self) -> bool:
        """
        Run tests expected to fail to demonstrate Issue #631.
        
        This focuses on tests that should fail until the issue is fixed.
        """
        logger.info("Running Issue #631 FAILING Tests Only")
        logger.warning("These tests are DESIGNED TO FAIL to demonstrate the issue")
        
        # Run specific failing test methods
        failing_tests = [
            "tests/unit/issue_631/test_auth_service_configuration_unit.py::TestAuthServiceConfigurationUnit::test_auth_service_url_configuration_loaded",
            "tests/integration/issue_631/test_websocket_auth_service_integration.py::TestWebSocketAuthServiceIntegration::test_backend_auth_service_communication",
            "tests/e2e/staging/issue_631/test_websocket_403_reproduction_staging.py::TestWebSocket403ReproductionStaging::test_reproduce_http_403_websocket_handshake"
        ]
        
        for test in failing_tests:
            logger.info(f"\nRunning FAILING TEST: {test}")
            cmd = [
                "python", "-m", "pytest",
                test,
                "-v",
                "--tb=short",
                "-s"
            ]
            
            result = self._run_test_command(cmd, f"Failing Test: {test.split('::')[-1]}")
            if result:
                logger.warning(f"Test passed unexpectedly - Issue #631 may be resolved: {test}")
            else:
                logger.info(f"Test failed as expected - Issue #631 still exists: {test}")
        
        return True

    def _run_test_command(self, cmd: list, test_name: str) -> bool:
        """Run a test command and return success status."""
        logger.info(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,  # Show output in real-time
                text=True
            )
            
            success = result.returncode == 0
            if success:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED (exit code: {result.returncode})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error running {test_name}: {e}")
            return False

    def print_summary(self, results: dict):
        """Print test execution summary."""
        logger.info("\n" + "=" * 60)
        logger.info("Issue #631 Test Suite Summary")
        logger.info("=" * 60)
        
        total_categories = len(results)
        passed_categories = sum(1 for success in results.values() if success)
        
        for category, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{category.upper()} Tests: {status}")
        
        logger.info(f"\nOverall: {passed_categories}/{total_categories} test categories passed")
        
        if passed_categories == total_categories:
            logger.info("🎉 All tests passed - Issue #631 appears to be RESOLVED!")
        else:
            logger.info("⚠️  Some tests failed - Issue #631 still exists and needs fixing")
            logger.info("\nNext Steps:")
            logger.info("1. Fix AUTH_SERVICE_URL configuration in backend")
            logger.info("2. Ensure backend can communicate with auth service")
            logger.info("3. Verify WebSocket middleware integrates with auth service")
            logger.info("4. Re-run this test suite to validate fixes")


def main():
    """Main entry point for Issue #631 test runner."""
    parser = argparse.ArgumentParser(
        description="Issue #631 Test Suite - HTTP 403 WebSocket Authentication Failures",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--category",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Test category to run (default: all)"
    )
    
    parser.add_argument(
        "--staging-only",
        action="store_true",
        help="Run only E2E staging tests for live reproduction"
    )
    
    parser.add_argument(
        "--failing-only",
        action="store_true", 
        help="Run only tests expected to fail (to demonstrate issue)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    runner = Issue631TestRunner()
    
    # Execute based on arguments
    if args.failing_only:
        success = runner.run_failing_only_tests()
    elif args.staging_only:
        success = runner.run_e2e_staging_tests()
    elif args.category == "unit":
        success = runner.run_unit_tests()
    elif args.category == "integration":
        success = runner.run_integration_tests()
    elif args.category == "e2e":
        success = runner.run_e2e_staging_tests()
    else:  # all
        results = runner.run_all_tests()
        runner.print_summary(results)
        success = all(results.values())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()