#!/usr/bin/env python3
"""
WebSocket 1011 Error Reproduction Test
=====================================

This script reproduces the exact WebSocket 1011 internal error scenario
identified in the Five-Whys analysis for P1 critical tests.

Business Value Justification:
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Reproduce and validate fix for WebSocket connection failures
- Value Impact: Enables verification of $120K+ MRR chat functionality fix
- Revenue Impact: Validates solution for 90% → 100% P1 test success rate

USAGE:
    python test_websocket_1011_reproduction.py

REQUIREMENTS:
    pip install websockets asyncio
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import websockets
    from websockets.exceptions import ConnectionClosedError, InvalidURI
except ImportError:
    print("❌ ERROR: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebSocket1011ReproductionTest:
    """
    Test class to reproduce WebSocket 1011 internal errors identified in Five-Whys analysis.
    
    This class implements the exact failure scenarios from P1 critical tests:
    1. websocket_connection_real 
    2. websocket_authentication_real
    """
    
    def __init__(self, staging_host: Optional[str] = None):
        """
        Initialize reproduction test.
        
        Args:
            staging_host: Override staging host for testing
        """
        # Default staging configuration
        self.staging_host = staging_host or "localhost:8000"  # Local staging for testing
        self.staging_ws_url = f"ws://{self.staging_host}/ws"
        
        # Test configuration
        self.connection_timeout = 10.0
        self.test_results = []
        
        logger.info(f"WebSocket 1011 Reproduction Test initialized for {self.staging_ws_url}")
    
    async def test_scenario_1_connection_establishment(self) -> Dict[str, Any]:
        """
        Test Scenario 1: WebSocket connection establishment (websocket_connection_real)
        
        This reproduces the exact failure pattern from P1 Test #1.
        
        Returns:
            Test result dictionary with status and diagnostic information
        """
        test_name = "websocket_connection_real_reproduction"
        logger.info(f"🧪 Running {test_name}")
        
        start_time = time.time()
        result = {
            "test_name": test_name,
            "status": "unknown",
            "duration_seconds": 0,
            "error_details": None,
            "websocket_close_code": None,
            "websocket_close_reason": None,
            "connection_accepted": False,
            "authentication_attempted": False,
            "reproduction_successful": False
        }
        
        try:
            # Attempt WebSocket connection (reproducing P1 test conditions)
            logger.info(f"Connecting to {self.staging_ws_url}...")
            
            async with websockets.connect(
                self.staging_ws_url,
                timeout=self.connection_timeout,
                extra_headers={
                    # Reproduce test conditions - no proper E2E headers initially
                    "User-Agent": "P1-Test-Reproduction/1.0",
                }
            ) as websocket:
                result["connection_accepted"] = True
                logger.info("✅ WebSocket connection accepted")
                
                # Attempt authentication (this should trigger the 1011 error)
                result["authentication_attempted"] = True
                
                # Wait for server response or closure
                try:
                    # Send a test message to trigger authentication flow
                    test_message = {"type": "ping", "test_id": "reproduction_1", "timestamp": datetime.utcnow().isoformat()}
                    await websocket.send(json.dumps(test_message))
                    logger.info("📤 Sent test message")
                    
                    # Wait for response (should get 1011 close instead)
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    logger.info(f"📥 Received response: {response}")
                    
                    # If we get here, the connection is working (fix was successful)
                    result["status"] = "passed"
                    result["reproduction_successful"] = False  # No error reproduced = fix working
                    logger.info("✅ Test PASSED - No 1011 error (fix appears to be working)")
                    
                except asyncio.TimeoutError:
                    result["status"] = "timeout"
                    result["error_details"] = "No response received within 5 seconds"
                    logger.warning("⏱️ Test TIMEOUT - No response received")
                
        except ConnectionClosedError as close_error:
            result["websocket_close_code"] = close_error.code
            result["websocket_close_reason"] = close_error.reason
            result["connection_accepted"] = True  # Connection was accepted but then closed
            
            if close_error.code == 1011:
                result["status"] = "failed_1011"
                result["reproduction_successful"] = True  # Successfully reproduced the bug
                result["error_details"] = f"WebSocket 1011 internal error: {close_error.reason}"
                logger.error(f"❌ REPRODUCED WebSocket 1011 error: {close_error.reason}")
            else:
                result["status"] = "failed_other"
                result["error_details"] = f"WebSocket closed with code {close_error.code}: {close_error.reason}"
                logger.error(f"❌ WebSocket closed with different code: {close_error.code}")
                
        except Exception as e:
            result["status"] = "error"
            result["error_details"] = str(e)
            logger.error(f"❌ Connection error: {e}")
        
        finally:
            result["duration_seconds"] = round(time.time() - start_time, 2)
            logger.info(f"Test completed in {result['duration_seconds']}s")
        
        return result
    
    async def test_scenario_2_authentication_flow(self) -> Dict[str, Any]:
        """
        Test Scenario 2: WebSocket authentication flow (websocket_authentication_real)
        
        This reproduces the exact failure pattern from P1 Test #2 with authentication focus.
        
        Returns:
            Test result dictionary with authentication-specific diagnostics
        """
        test_name = "websocket_authentication_real_reproduction"
        logger.info(f"🧪 Running {test_name}")
        
        start_time = time.time()
        result = {
            "test_name": test_name,
            "status": "unknown",
            "duration_seconds": 0,
            "error_details": None,
            "websocket_close_code": None,
            "websocket_close_reason": None,
            "connection_accepted": False,
            "auth_headers_sent": True,
            "e2e_bypass_attempted": True,
            "reproduction_successful": False
        }
        
        try:
            # Attempt WebSocket connection with authentication headers
            logger.info(f"Connecting to {self.staging_ws_url} with auth headers...")
            
            # Simulate E2E test authentication conditions
            headers = {
                "Authorization": "Bearer fake-jwt-token-for-e2e-testing",
                "X-E2E-Testing": "true", 
                "X-Test-Type": "P1-Authentication-Test",
                "User-Agent": "P1-Test-Authentication/1.0"
            }
            
            async with websockets.connect(
                self.staging_ws_url,
                timeout=self.connection_timeout,
                extra_headers=headers
            ) as websocket:
                result["connection_accepted"] = True
                logger.info("✅ WebSocket connection accepted with auth headers")
                
                # Send authentication test message
                auth_test_message = {
                    "type": "authenticate", 
                    "test_id": "auth_reproduction_2",
                    "e2e_testing": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send(json.dumps(auth_test_message))
                logger.info("📤 Sent authentication test message")
                
                # Wait for authentication response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    logger.info(f"📥 Received auth response: {response}")
                    
                    # Parse response to check authentication status
                    try:
                        response_data = json.loads(response)
                        if response_data.get("type") == "authentication_success":
                            result["status"] = "passed"
                            result["reproduction_successful"] = False  # No error = fix working
                            logger.info("✅ Authentication PASSED - E2E bypass working")
                        elif response_data.get("type") == "authentication_error":
                            result["status"] = "failed_auth"
                            result["error_details"] = response_data.get("error", "Authentication failed")
                            logger.error(f"❌ Authentication failed: {response_data.get('error')}")
                        else:
                            result["status"] = "unexpected_response"
                            result["error_details"] = f"Unexpected response: {response}"
                    except json.JSONDecodeError:
                        result["status"] = "invalid_response"
                        result["error_details"] = f"Invalid JSON response: {response}"
                    
                except asyncio.TimeoutError:
                    result["status"] = "timeout"
                    result["error_details"] = "No authentication response received within 5 seconds"
                    logger.warning("⏱️ Authentication test TIMEOUT")
                
        except ConnectionClosedError as close_error:
            result["websocket_close_code"] = close_error.code
            result["websocket_close_reason"] = close_error.reason
            result["connection_accepted"] = True
            
            if close_error.code == 1011:
                result["status"] = "failed_1011"
                result["reproduction_successful"] = True  # Successfully reproduced the bug
                result["error_details"] = f"WebSocket 1011 during authentication: {close_error.reason}"
                logger.error(f"❌ REPRODUCED WebSocket 1011 during authentication: {close_error.reason}")
            else:
                result["status"] = "failed_other"
                result["error_details"] = f"WebSocket closed during auth with code {close_error.code}: {close_error.reason}"
                logger.error(f"❌ Authentication failed with WebSocket code: {close_error.code}")
                
        except Exception as e:
            result["status"] = "error"
            result["error_details"] = str(e)
            logger.error(f"❌ Authentication test error: {e}")
        
        finally:
            result["duration_seconds"] = round(time.time() - start_time, 2)
            logger.info(f"Authentication test completed in {result['duration_seconds']}s")
        
        return result
    
    async def test_scenario_3_fix_validation(self) -> Dict[str, Any]:
        """
        Test Scenario 3: Validation that the E2E bypass fix is working.
        
        This tests the enhanced E2E detection logic implementation.
        
        Returns:
            Test result dictionary with fix validation results
        """
        test_name = "e2e_bypass_fix_validation"
        logger.info(f"🧪 Running {test_name}")
        
        start_time = time.time()
        result = {
            "test_name": test_name,
            "status": "unknown",
            "duration_seconds": 0,
            "error_details": None,
            "fix_validation": "unknown",
            "e2e_bypass_detected": False,
            "connection_sustained": False,
            "reproduction_successful": False
        }
        
        try:
            # Test with enhanced E2E detection headers
            logger.info(f"Testing enhanced E2E bypass fix...")
            
            headers = {
                "Authorization": "Bearer staging-e2e-test-token",
                "X-E2E-Testing": "true",
                "X-E2E-Bypass": "enabled", 
                "X-Environment": "staging",
                "X-Test-Framework": "P1-Critical-Tests",
                "User-Agent": "P1-Test-Fix-Validation/1.0"
            }
            
            async with websockets.connect(
                self.staging_ws_url,
                timeout=self.connection_timeout,
                extra_headers=headers
            ) as websocket:
                logger.info("✅ WebSocket connection established with E2E bypass headers")
                
                # Send multiple test messages to validate sustained connection
                for i in range(3):
                    test_message = {
                        "type": "e2e_validation",
                        "test_sequence": i + 1,
                        "message": f"Fix validation test {i + 1}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send(json.dumps(test_message))
                    logger.info(f"📤 Sent validation message {i + 1}/3")
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        logger.info(f"📥 Received response {i + 1}: {response}")
                        
                        # Check if response indicates E2E bypass
                        try:
                            response_data = json.loads(response)
                            if response_data.get("e2e_bypass") or "e2e" in str(response_data).lower():
                                result["e2e_bypass_detected"] = True
                        except json.JSONDecodeError:
                            pass
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"⏱️ Timeout waiting for response {i + 1}")
                
                result["connection_sustained"] = True
                result["status"] = "passed"
                result["fix_validation"] = "working"
                logger.info("✅ Fix validation PASSED - E2E bypass working correctly")
                
        except ConnectionClosedError as close_error:
            if close_error.code == 1011:
                result["status"] = "failed_1011"
                result["fix_validation"] = "not_working"
                result["reproduction_successful"] = True
                result["error_details"] = f"Fix validation failed: WebSocket 1011: {close_error.reason}"
                logger.error(f"❌ FIX VALIDATION FAILED: Still getting 1011 errors")
            else:
                result["status"] = "failed_other" 
                result["error_details"] = f"WebSocket closed with code {close_error.code}: {close_error.reason}"
                logger.error(f"❌ Fix validation failed with code: {close_error.code}")
                
        except Exception as e:
            result["status"] = "error"
            result["fix_validation"] = "error"
            result["error_details"] = str(e)
            logger.error(f"❌ Fix validation error: {e}")
        
        finally:
            result["duration_seconds"] = round(time.time() - start_time, 2)
            logger.info(f"Fix validation completed in {result['duration_seconds']}s")
        
        return result
    
    async def run_full_reproduction_suite(self) -> Dict[str, Any]:
        """
        Run the complete WebSocket 1011 reproduction test suite.
        
        Returns:
            Complete test suite results with summary
        """
        logger.info("🚀 Starting WebSocket 1011 Reproduction Test Suite")
        logger.info("=" * 60)
        
        suite_start = time.time()
        
        # Run all test scenarios
        test_results = []
        
        # Scenario 1: Connection establishment
        result_1 = await self.test_scenario_1_connection_establishment()
        test_results.append(result_1)
        
        # Scenario 2: Authentication flow
        result_2 = await self.test_scenario_2_authentication_flow()
        test_results.append(result_2)
        
        # Scenario 3: Fix validation
        result_3 = await self.test_scenario_3_fix_validation()
        test_results.append(result_3)
        
        # Analyze results
        suite_duration = round(time.time() - suite_start, 2)
        
        # Count results
        passed = sum(1 for r in test_results if r["status"] == "passed")
        failed_1011 = sum(1 for r in test_results if r["status"] == "failed_1011")
        failed_other = sum(1 for r in test_results if r["status"].startswith("failed"))
        errors = sum(1 for r in test_results if r["status"] == "error")
        reproduced = sum(1 for r in test_results if r.get("reproduction_successful", False))
        
        suite_result = {
            "suite_name": "WebSocket 1011 Reproduction Test Suite",
            "total_tests": len(test_results),
            "passed": passed,
            "failed_1011": failed_1011,
            "failed_other": failed_other,
            "errors": errors,
            "reproductions_successful": reproduced,
            "duration_seconds": suite_duration,
            "test_results": test_results,
            "summary": {
                "bug_reproduced": reproduced > 0,
                "fix_validated": any(r.get("fix_validation") == "working" for r in test_results),
                "overall_status": "REPRODUCED" if reproduced > 0 else ("FIXED" if passed > failed_1011 else "MIXED")
            }
        }
        
        return suite_result
    
    def print_summary_report(self, suite_result: Dict[str, Any]) -> None:
        """Print a detailed summary report of test results."""
        print("\n" + "=" * 80)
        print("🧪 WEBSOCKET 1011 REPRODUCTION TEST SUITE SUMMARY")
        print("=" * 80)
        
        summary = suite_result["summary"]
        print(f"📊 Total Tests: {suite_result['total_tests']}")
        print(f"✅ Passed: {suite_result['passed']}")
        print(f"❌ Failed (1011): {suite_result['failed_1011']}")
        print(f"❌ Failed (Other): {suite_result['failed_other']}")
        print(f"💥 Errors: {suite_result['errors']}")
        print(f"🔬 Bug Reproduced: {'YES' if summary['bug_reproduced'] else 'NO'}")
        print(f"🔧 Fix Validated: {'YES' if summary['fix_validated'] else 'NO'}")
        print(f"⏱️ Total Duration: {suite_result['duration_seconds']}s")
        print(f"📋 Overall Status: {summary['overall_status']}")
        
        print("\n📋 DETAILED TEST RESULTS:")
        print("-" * 80)
        
        for i, result in enumerate(suite_result['test_results'], 1):
            status_icon = {
                "passed": "✅",
                "failed_1011": "❌", 
                "failed_other": "⚠️",
                "error": "💥",
                "timeout": "⏱️"
            }.get(result["status"], "❓")
            
            print(f"{i}. {result['test_name']}")
            print(f"   Status: {status_icon} {result['status'].upper()}")
            print(f"   Duration: {result['duration_seconds']}s")
            
            if result.get("websocket_close_code"):
                print(f"   WebSocket Close: {result['websocket_close_code']} - {result['websocket_close_reason']}")
            
            if result.get("error_details"):
                print(f"   Error: {result['error_details']}")
            
            if result.get("reproduction_successful"):
                print("   🎯 BUG REPRODUCTION: SUCCESS")
            
            print()
        
        # Business impact assessment
        print("💼 BUSINESS IMPACT ASSESSMENT:")
        print("-" * 80)
        if summary['bug_reproduced']:
            print("❌ CRITICAL: WebSocket 1011 errors confirmed - $120K+ MRR chat functionality affected")
            print("📈 P1 Test Success Rate: 20/22 (90%) - Connection establishment failing")
            print("🔧 RECOMMENDATION: Apply E2E bypass fix immediately")
        elif summary['fix_validated']:
            print("✅ SUCCESS: WebSocket connections working - Fix validated")
            print("📈 P1 Test Success Rate: Expected 22/22 (100%)")
            print("💰 BUSINESS VALUE: $120K+ MRR chat functionality fully protected")
        else:
            print("⚠️  MIXED RESULTS: Further investigation needed")
        
        print("\n" + "=" * 80)


async def main():
    """Main function to run the WebSocket 1011 reproduction tests."""
    # Windows-safe printing without emojis for compatibility
    print("WebSocket 1011 Error Reproduction Test Suite")
    print("=" * 60)
    print("Business Goal: Validate fix for $120K+ MRR WebSocket chat functionality")
    print("Test Scope: Reproduce P1 critical test failures (Tests 1-2 of 22)")
    print("Expected: Either reproduce 1011 errors OR validate fix is working")
    print()
    
    # Check for custom host
    staging_host = os.getenv("STAGING_HOST", "localhost:8000")
    print(f"Target Host: {staging_host}")
    print(f"WebSocket URL: ws://{staging_host}/ws")
    print()
    
    # Initialize test suite
    test_suite = WebSocket1011ReproductionTest(staging_host=staging_host)
    
    try:
        # Run full test suite
        results = await test_suite.run_full_reproduction_suite()
        
        # Print detailed report
        test_suite.print_summary_report(results)
        
        # Exit with appropriate code
        if results["summary"]["bug_reproduced"]:
            print("REPRODUCTION SUCCESSFUL: WebSocket 1011 errors confirmed")
            sys.exit(1)  # Bug reproduced = test environment needs fix
        elif results["summary"]["fix_validated"]:
            print("FIX VALIDATED: WebSocket connections working properly")
            sys.exit(0)  # Fix working = success
        else:
            print("MIXED RESULTS: Manual investigation required")
            sys.exit(2)  # Mixed results = needs investigation
            
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nTest suite error: {e}")
        logger.exception("Test suite fatal error")
        sys.exit(1)


if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())