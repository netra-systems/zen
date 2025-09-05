#!/usr/bin/env python3
"""
Comprehensive Staging WebSocket Test Runner

This script provides comprehensive testing of WebSocket functionality in staging environment.
It validates all critical WebSocket features including authentication, SSL/TLS, event tracking,
and agent flow validation.

Business Value:
- Validates staging WebSocket before production deployment
- Prevents $50K+ MRR loss from WebSocket failures
- Ensures agent event tracking works correctly in production-like environment

Usage:
    python scripts/test_staging_websocket_comprehensive.py
    python scripts/test_staging_websocket_comprehensive.py --quick
    python scripts/test_staging_websocket_comprehensive.py --debug
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import staging test utilities
from test_framework.staging_websocket_utilities import (
    StagingWebSocketTester,
    staging_websocket_session,
    validate_staging_websocket_events,
    run_staging_websocket_smoke_test,
    debug_staging_websocket_connection
)
from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import StagingAuthClient


class StagingWebSocketTestRunner:
    """Comprehensive test runner for staging WebSocket functionality."""
    
    def __init__(self, config=None):
        """Initialize test runner."""
        self.config = config or get_staging_config()
        self.results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "warnings": [],
            "performance_metrics": {},
            "staging_ready": False
        }
        
    async def run_configuration_validation(self) -> bool:
        """Validate staging configuration."""
        logger.info("Validating staging configuration...")
        
        try:
            if not self.config.validate_configuration():
                self.results["errors"].append("Staging configuration validation failed")
                return False
            
            # Log configuration details
            self.config.log_configuration()
            
            # Test basic auth client
            auth_client = StagingAuthClient()
            tokens = await auth_client.get_auth_token()
            
            if not tokens.get("access_token"):
                self.results["errors"].append("Failed to get authentication token from staging")
                return False
            
            logger.info("Successfully validated staging configuration and authentication")
            return True
            
        except Exception as e:
            error_msg = f"Configuration validation failed: {e}"
            logger.error(error_msg)
            self.results["errors"].append(error_msg)
            return False
    
    async def run_connection_tests(self) -> bool:
        """Test WebSocket connection capabilities."""
        logger.info("Testing WebSocket connection capabilities...")
        
        self.results["tests_run"] += 1
        
        try:
            async with staging_websocket_session() as tester:
                # Test basic connectivity
                assert tester.is_connected, "Should be connected after session setup"
                
                # Test message sending
                success = await tester.send_test_message(
                    "connection_test",
                    {"test": "basic_connectivity"},
                    thread_id="conn-test"
                )
                assert success, "Should be able to send test message"
                
                # Wait briefly for any response
                await asyncio.sleep(1)
                
                # Get session report
                report = tester.get_session_report()
                self.results["performance_metrics"]["connection"] = {
                    "success_rate": report["success_rate"],
                    "average_connection_time": report["average_connection_time"],
                    "connection_attempts": report["connection_attempts"]
                }
                
                logger.info(f"Connection test passed (success rate: {report['success_rate']:.1%})")
                
                self.results["tests_passed"] += 1
                return True
                
        except Exception as e:
            error_msg = f"Connection test failed: {e}"
            logger.error(error_msg)
            self.results["errors"].append(error_msg)
            self.results["tests_failed"] += 1
            return False
    
    async def run_agent_flow_tests(self) -> bool:
        """Test agent flow through staging WebSocket."""
        logger.info("Testing agent flow through staging WebSocket...")
        
        self.results["tests_run"] += 1
        
        try:
            # Test comprehensive agent flow
            validation_result = await validate_staging_websocket_events(
                query="Comprehensive staging test: What is 2+2 and provide the calculation steps?",
                timeout=90.0
            )
            
            # Record performance metrics
            self.results["performance_metrics"]["agent_flow"] = {
                "duration": validation_result["flow_duration"],
                "events_count": validation_result["total_events"],
                "events_validated": validation_result["events_validated"]
            }
            
            # Validate results
            if not validation_result["staging_ready"]:
                error_msg = f"Agent flow validation failed: missing {validation_result['missing_events']}"
                logger.error(error_msg)
                self.results["errors"].append(error_msg)
                self.results["tests_failed"] += 1
                return False
            
            logger.info("Agent flow test passed")
            logger.info(f"  - Duration: {validation_result['flow_duration']:.2f}s")
            logger.info(f"  - Events: {validation_result['total_events']}")
            
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            error_msg = f"Agent flow test failed: {e}"
            logger.error(error_msg)
            self.results["errors"].append(error_msg)
            self.results["tests_failed"] += 1
            return False
    
    async def run_performance_tests(self) -> bool:
        """Test WebSocket performance in staging."""
        logger.info("Testing WebSocket performance in staging...")
        
        self.results["tests_run"] += 1
        
        try:
            async with staging_websocket_session() as tester:
                # Send burst of messages
                message_count = 20
                start_time = time.time()
                successful_sends = 0
                
                for i in range(message_count):
                    success = await tester.send_test_message(
                        "performance_test",
                        {"sequence": i, "test_data": f"message_{i}"},
                        thread_id=f"perf-{i}"
                    )
                    if success:
                        successful_sends += 1
                        
                    # Small delay to avoid overwhelming staging
                    await asyncio.sleep(0.1)
                
                duration = time.time() - start_time
                throughput = successful_sends / duration
                
                # Record performance metrics
                self.results["performance_metrics"]["performance"] = {
                    "messages_sent": successful_sends,
                    "total_attempted": message_count,
                    "success_rate": successful_sends / message_count,
                    "duration": duration,
                    "throughput": throughput
                }
                
                # Validate performance (lenient for staging)
                min_success_rate = 0.8
                min_throughput = 5.0  # messages per second
                
                if successful_sends / message_count < min_success_rate:
                    error_msg = f"Success rate too low: {successful_sends}/{message_count}"
                    self.results["errors"].append(error_msg)
                    self.results["tests_failed"] += 1
                    return False
                
                if throughput < min_throughput:
                    warning_msg = f"Throughput below target: {throughput:.1f} < {min_throughput} msg/s"
                    logger.warning(warning_msg)
                    self.results["warnings"].append(warning_msg)
                    # Don't fail test for low throughput in staging
                
                logger.info("Performance test passed")
                logger.info(f"  - Success rate: {successful_sends/message_count:.1%}")
                logger.info(f"  - Throughput: {throughput:.1f} msg/s")
                
                self.results["tests_passed"] += 1
                return True
                
        except Exception as e:
            error_msg = f"Performance test failed: {e}"
            logger.error(error_msg)
            self.results["errors"].append(error_msg)
            self.results["tests_failed"] += 1
            return False
    
    async def run_all_tests(self, quick_mode: bool = False) -> bool:
        """Run all staging WebSocket tests.
        
        Args:
            quick_mode: Run only essential tests for faster feedback
            
        Returns:
            True if all tests pass
        """
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE STAGING WEBSOCKET TEST SUITE")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Test configuration
        config_valid = await self.run_configuration_validation()
        if not config_valid:
            logger.error("Configuration validation failed - aborting tests")
            return False
        
        # Test connection capabilities
        connection_ok = await self.run_connection_tests()
        
        # Test agent flow
        agent_flow_ok = await self.run_agent_flow_tests()
        
        # Test performance (unless quick mode)
        performance_ok = True
        if not quick_mode:
            performance_ok = await self.run_performance_tests()
        
        # Calculate overall results
        total_duration = time.time() - start_time
        overall_success = config_valid and connection_ok and agent_flow_ok and performance_ok
        
        self.results["staging_ready"] = overall_success
        self.results["total_duration"] = total_duration
        
        # Generate summary report
        self._print_summary_report()
        
        return overall_success
    
    def _print_summary_report(self) -> None:
        """Print comprehensive test summary."""
        logger.info("\n" + "=" * 80)
        logger.info("STAGING WEBSOCKET TEST SUMMARY")
        logger.info("=" * 80)
        
        # Overall status
        status = "STAGING READY" if self.results["staging_ready"] else "STAGING ISSUES"
        logger.info(f"Status: {status}")
        logger.info(f"Duration: {self.results.get('total_duration', 0):.2f}s")
        logger.info(f"Tests: {self.results['tests_passed']}/{self.results['tests_run']} passed")
        
        # Performance metrics
        if self.results["performance_metrics"]:
            logger.info("\nPerformance Metrics:")
            for test_type, metrics in self.results["performance_metrics"].items():
                logger.info(f"  {test_type}:")
                for key, value in metrics.items():
                    if isinstance(value, float):
                        logger.info(f"    {key}: {value:.2f}")
                    else:
                        logger.info(f"    {key}: {value}")
        
        # Errors and warnings
        if self.results["errors"]:
            logger.info("\nErrors:")
            for error in self.results["errors"]:
                logger.info(f"  - {error}")
        
        if self.results["warnings"]:
            logger.info("\nWarnings:")
            for warning in self.results["warnings"]:
                logger.info(f"  - {warning}")
        
        # Recommendations
        if not self.results["staging_ready"]:
            logger.info("\nRecommended Actions:")
            logger.info("  1. Check staging service health and deployment status")
            logger.info("  2. Verify E2E_OAUTH_SIMULATION_KEY is set correctly")
            logger.info("  3. Ensure staging services are not in cold start state")
            logger.info("  4. Check network connectivity to staging endpoints")
        
        logger.info("=" * 80)


async def run_debug_mode() -> None:
    """Run debug mode to troubleshoot staging WebSocket issues."""
    logger.info("Running debug mode for staging WebSocket...")
    
    debug_info = await debug_staging_websocket_connection()
    
    print("\nDebug Results:")
    print("=" * 40)
    
    for key, value in debug_info.items():
        if key != "error_details":
            status = "PASS" if value else "FAIL"
            print(f"  {status} {key.replace('_', ' ').title()}: {value}")
    
    if debug_info["error_details"]:
        print("\nError Details:")
        for i, error in enumerate(debug_info["error_details"], 1):
            print(f"  {i}. {error}")
    
    # Recommendations based on debug results
    print("\nRecommendations:")
    
    if not debug_info["config_valid"]:
        print("  - Check E2E_OAUTH_SIMULATION_KEY environment variable")
        print("  - Verify staging URLs are correct")
    
    if not debug_info["auth_working"]:
        print("  - Check staging auth service is deployed and healthy")
        print("  - Verify E2E_OAUTH_SIMULATION_KEY matches staging deployment")
    
    if not debug_info["websocket_connectable"]:
        print("  - Check staging backend WebSocket endpoint is accessible")
        print("  - Verify SSL/TLS certificates are valid")
        print("  - Check that staging backend is deployed and healthy")
    
    if not debug_info["ssl_valid"]:
        print("  - Check SSL certificate chain for staging domain")
        print("  - Verify TLS configuration is correct")


async def run_quick_tests() -> bool:
    """Run quick tests for fast feedback."""
    logger.info("Running quick staging WebSocket tests...")
    
    try:
        # Run smoke test
        smoke_passed = await run_staging_websocket_smoke_test()
        
        if smoke_passed:
            logger.info("Quick tests PASSED - staging WebSocket is functional")
            return True
        else:
            logger.error("Quick tests FAILED - staging WebSocket has issues")
            return False
            
    except Exception as e:
        logger.error(f"Quick tests failed with exception: {e}")
        return False


async def run_comprehensive_tests() -> bool:
    """Run comprehensive test suite."""
    logger.info("Running comprehensive staging WebSocket tests...")
    
    runner = StagingWebSocketTestRunner()
    success = await runner.run_all_tests(quick_mode=False)
    
    return success


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive staging WebSocket test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run comprehensive tests
  python scripts/test_staging_websocket_comprehensive.py
  
  # Quick smoke test only
  python scripts/test_staging_websocket_comprehensive.py --quick
  
  # Debug connection issues
  python scripts/test_staging_websocket_comprehensive.py --debug
        """
    )
    
    parser.add_argument(
        "--quick", 
        action="store_true",
        help="Run only quick smoke tests for fast feedback"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Run debug mode to troubleshoot connection issues"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.debug:
            await run_debug_mode()
            return
        
        if args.quick:
            success = await run_quick_tests()
        else:
            success = await run_comprehensive_tests()
        
        exit_code = 0 if success else 1
        
        if success:
            print("\nAll staging WebSocket tests PASSED")
            print("Staging environment is ready for WebSocket functionality")
        else:
            print("\nStaging WebSocket tests FAILED")
            print("Fix issues before deploying to production")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"\nTest runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Set event loop policy for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())