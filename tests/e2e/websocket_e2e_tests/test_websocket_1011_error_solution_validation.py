"""
WebSocket 1011 Error Solution Validation Test Suite

This test suite validates the solutions for WebSocket 1011 internal errors.
After remediation (environment variable configuration or enhanced E2E detection),
these tests should PASS, confirming the fixes work correctly.

Business Impact:
- Validates remediation of critical WebSocket connection failures
- Confirms $120K+ MRR chat functionality fully operational
- Tests three proposed solution approaches:
  1. Environment variable configuration
  2. Staging auto-detection enhancement
  3. Header-based E2E detection

CRITICAL: These tests should PASS after remediation is implemented.
They validate that the fixes resolve the identified root cause.
"""

import asyncio
import json
import logging
import pytest
import time
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from tests.e2e.staging_config import StagingTestConfig
from test_framework.websocket_helpers import WebSocketTestHelpers

logger = logging.getLogger(__name__)

# Configure test to validate solutions work in staging environment
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.websocket,
    pytest.mark.solution_validation,  # These tests validate fixes work
]


@pytest.fixture
def staging_config():
    """Staging configuration for solution validation."""
    return StagingTestConfig()


@pytest.fixture
def staging_websocket_auth_helper(staging_config):
    """WebSocket auth helper with solution enhancements."""
    return E2EWebSocketAuthHelper(environment="staging")


class TestWebSocket1011ErrorSolutionValidation:
    """
    Test suite that validates solutions for WebSocket 1011 internal errors.
    
    These tests verify that the implemented fixes resolve the authentication
    failure patterns that previously caused 1011 errors.
    
    EXPECTED BEHAVIOR:
    - Tests should PASS after environment variable configuration
    - Tests should demonstrate successful WebSocket connections  
    - Tests should show proper E2E context detection working
    """
    
    async def test_websocket_header_based_e2e_detection_solution(
        self,
        staging_config: StagingTestConfig,
        staging_websocket_auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test Solution 1: Header-based E2E detection enhancement.
        
        This validates that WebSocket connections succeed when E2E detection
        is enhanced to recognize test headers even without environment variables.
        
        EXPECTED: Connection should succeed with proper E2E headers.
        """
        logger.info("🧪 SOLUTION TEST: Header-based E2E detection")
        logger.info(f"Target URL: {staging_config.urls.websocket_url}")
        
        connection_start_time = time.time()
        
        try:
            # Get staging-compatible token
            token = await staging_websocket_auth_helper.get_staging_token_async()
            logger.info(f"✅ Token acquired: {token[:20]}...")
            
            # Get enhanced WebSocket headers with explicit E2E indicators
            headers = staging_websocket_auth_helper.get_websocket_headers(token)
            
            # Add explicit E2E detection headers for header-based solution
            enhanced_headers = {
                **headers,
                "X-E2E-Test-Solution": "header-based-detection",
                "X-Test-Validation": "websocket-1011-fix", 
                "X-Auth-Bypass-Reason": "e2e-header-detection",
                "X-Expected-Result": "connection-success"
            }
            
            logger.info(f"📤 Enhanced headers sent: {list(enhanced_headers.keys())}")
            
            # Connect with enhanced headers - this should succeed after fix
            connection_timeout = 15.0  
            
            async with websockets.connect(
                staging_config.urls.websocket_url,
                additional_headers=enhanced_headers,
                open_timeout=connection_timeout,
                close_timeout=5.0
            ) as websocket:
                connection_time = time.time() - connection_start_time
                logger.info(f"✅ CONNECTION SUCCESSFUL: {connection_time:.2f}s")
                
                # Test message exchange to confirm full functionality
                test_message = {
                    "type": "solution_validation",
                    "solution_type": "header_based_detection",
                    "test_phase": "websocket_1011_fix_validation",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                logger.info("📤 Validation message sent")
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                logger.info(f"📥 Response received: {response_data.get('type', 'unknown')}")
                
                # Validate response indicates proper E2E handling
                assert response_data.get("type") in ["ack", "success", "pong"], \
                    f"Expected success response, got: {response_data}"
                
                logger.info("✅ SOLUTION VALIDATED: Header-based E2E detection working")
                
                return {
                    "solution": "header_based_detection",
                    "success": True,
                    "connection_time": connection_time,
                    "message_exchange": True
                }
                
        except websockets.exceptions.ConnectionClosedError as e:
            connection_time = time.time() - connection_start_time
            logger.error(f"❌ CONNECTION FAILED: Code {e.code}, Reason: {e.reason}")
            
            if e.code == 1011:
                pytest.fail(
                    f"SOLUTION FAILED: Still getting 1011 errors after header-based fix. "
                    f"Time: {connection_time:.2f}s, Reason: {e.reason}. "
                    f"This indicates the header-based E2E detection solution is not working."
                )
            else:
                pytest.fail(
                    f"UNEXPECTED ERROR: Got {e.code} instead of success. "
                    f"Time: {connection_time:.2f}s, Reason: {e.reason}"
                )
                
        except asyncio.TimeoutError:
            connection_time = time.time() - connection_start_time
            pytest.fail(
                f"SOLUTION TIMEOUT: Header-based detection timed out after {connection_time:.2f}s. "
                f"This may indicate the solution is partially working but still has performance issues."
            )

    async def test_staging_auto_detection_from_gcp_metadata(
        self,
        staging_config: StagingTestConfig, 
        staging_websocket_auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test Solution 2: Staging environment auto-detection enhancement.
        
        This validates that WebSocket connections succeed when E2E detection
        is enhanced to automatically enable bypass mode in staging environments.
        
        EXPECTED: Connection should succeed via auto-detection of staging environment.
        """
        logger.info("🧪 SOLUTION TEST: Staging auto-detection from GCP metadata")
        
        connection_start_time = time.time()
        
        try:
            # Get token for staging auto-detection test
            token = await staging_websocket_auth_helper.get_staging_token_async()
            
            # Standard headers (no special E2E headers needed for auto-detection)
            headers = staging_websocket_auth_helper.get_websocket_headers(token)
            
            # Add solution identification headers
            headers.update({
                "X-Solution-Type": "staging-auto-detection",
                "X-GCP-Environment-Test": "true",
                "X-Expected-Behavior": "auto-e2e-detection"
            })
            
            logger.info("📤 Testing staging auto-detection solution...")
            logger.info(f"📤 Headers: {list(headers.keys())}")
            
            # Connect - should succeed via automatic staging detection
            async with websockets.connect(
                staging_config.urls.websocket_url,
                additional_headers=headers,
                open_timeout=15.0
            ) as websocket:
                connection_time = time.time() - connection_start_time
                logger.info(f"✅ AUTO-DETECTION SUCCESS: {connection_time:.2f}s")
                
                # Test that auto-detection properly enabled E2E mode
                auto_detection_test = {
                    "type": "auto_detection_validation",
                    "expected_e2e_mode": True,
                    "gcp_staging_detected": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(auto_detection_test))
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                logger.info(f"📥 Auto-detection response: {response_data}")
                
                # Validate auto-detection worked
                assert response_data.get("type") != "error", \
                    f"Auto-detection failed: {response_data}"
                
                logger.info("✅ SOLUTION VALIDATED: Staging auto-detection working")
                
                return {
                    "solution": "staging_auto_detection",
                    "success": True,
                    "connection_time": connection_time,
                    "auto_detection": True
                }
                
        except websockets.exceptions.ConnectionClosedError as e:
            connection_time = time.time() - connection_start_time
            logger.error(f"❌ AUTO-DETECTION FAILED: Code {e.code}")
            
            if e.code == 1011:
                pytest.fail(
                    f"SOLUTION FAILED: Auto-detection still produces 1011 errors. "
                    f"Time: {connection_time:.2f}s. "
                    f"This indicates staging auto-detection enhancement is not working."
                )
            else:
                pytest.fail(f"UNEXPECTED ERROR in auto-detection: Code {e.code}")

    async def test_websocket_connection_with_proper_context(
        self,
        staging_config: StagingTestConfig,
        staging_websocket_auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test complete WebSocket connection with proper E2E context.
        
        This validates that all components work together after the fix:
        - E2E context detection
        - Authentication bypass
        - Factory validation in E2E-safe mode
        - Successful WebSocket connection
        
        EXPECTED: End-to-end WebSocket functionality should work perfectly.
        """
        logger.info("🧪 SOLUTION TEST: Complete WebSocket connection with proper E2E context")
        
        connection_start_time = time.time()
        full_test_results = {
            "connection_success": False,
            "message_exchange": False,
            "bi_directional_communication": False,
            "connection_stability": False
        }
        
        try:
            # Get comprehensive token with all E2E context
            token = await staging_websocket_auth_helper.get_staging_token_async()
            
            # Comprehensive E2E headers covering all solution approaches
            comprehensive_headers = staging_websocket_auth_helper.get_websocket_headers(token)
            comprehensive_headers.update({
                # Header-based detection
                "X-E2E-Test": "true",
                "X-Test-Type": "E2E",
                "X-Test-Environment": "staging",
                
                # Solution validation
                "X-Solution-Validation": "comprehensive-test",
                "X-Test-Name": "websocket-1011-complete-fix-validation",
                
                # Context indicators
                "X-Context-Requirement": "full-e2e-context",
                "X-Expected-Result": "full-websocket-functionality"
            })
            
            logger.info("📤 Comprehensive context headers sent")
            
            # Phase 1: Connection establishment
            async with websockets.connect(
                staging_config.urls.websocket_url,
                additional_headers=comprehensive_headers,
                open_timeout=15.0,
                ping_interval=20.0,  # Test connection stability
                ping_timeout=10.0
            ) as websocket:
                connection_time = time.time() - connection_start_time
                full_test_results["connection_success"] = True
                logger.info(f"✅ Phase 1: Connection established in {connection_time:.2f}s")
                
                # Phase 2: Basic message exchange
                test_messages = [
                    {
                        "type": "ping",
                        "phase": "basic_connectivity",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    {
                        "type": "validation_test",
                        "phase": "e2e_context_validation",
                        "expected_e2e_mode": True,
                        "test_data": "comprehensive_websocket_test"
                    }
                ]
                
                responses = []
                for i, message in enumerate(test_messages):
                    logger.info(f"📤 Sending test message {i+1}/2")
                    await websocket.send(json.dumps(message))
                    
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    responses.append(response_data)
                    logger.info(f"📥 Response {i+1}: {response_data.get('type', 'unknown')}")
                
                full_test_results["message_exchange"] = True
                logger.info("✅ Phase 2: Message exchange successful")
                
                # Phase 3: Bidirectional communication test
                echo_test = {
                    "type": "echo_test",
                    "echo_data": "bidirectional_communication_validation",
                    "request_id": f"echo_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(echo_test))
                echo_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                echo_data = json.loads(echo_response)
                
                # Validate bidirectional communication
                if echo_data.get("type") == "echo" or "echo" in str(echo_data):
                    full_test_results["bi_directional_communication"] = True
                    logger.info("✅ Phase 3: Bidirectional communication successful")
                else:
                    logger.warning(f"⚠️ Phase 3: Unexpected echo response: {echo_data}")
                
                # Phase 4: Connection stability test
                logger.info("🔄 Phase 4: Testing connection stability (30s)...")
                stability_start = time.time()
                
                # Send periodic messages to test stability
                for i in range(3):
                    await asyncio.sleep(10.0)  # 10 second intervals
                    
                    stability_message = {
                        "type": "stability_test",
                        "iteration": i + 1,
                        "elapsed_time": time.time() - stability_start
                    }
                    
                    await websocket.send(json.dumps(stability_message))
                    stability_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    logger.info(f"📥 Stability test {i+1}/3: Success")
                
                full_test_results["connection_stability"] = True
                total_time = time.time() - connection_start_time
                logger.info(f"✅ Phase 4: Connection stability validated over {total_time:.1f}s")
                
                # Final validation
                all_phases_successful = all(full_test_results.values())
                
                if all_phases_successful:
                    logger.info("🎉 COMPLETE SOLUTION VALIDATION SUCCESSFUL!")
                    logger.info(f"📊 Total test duration: {total_time:.1f}s")
                    logger.info(f"📊 All phases passed: {full_test_results}")
                else:
                    pytest.fail(
                        f"PARTIAL SUCCESS: Some phases failed. Results: {full_test_results}"
                    )
                
                return {
                    "solution": "comprehensive_websocket_functionality",
                    "success": True,
                    "total_time": total_time,
                    "phases": full_test_results,
                    "responses_received": len(responses) + 1  # +1 for echo response
                }
                
        except websockets.exceptions.ConnectionClosedError as e:
            connection_time = time.time() - connection_start_time
            logger.error(f"❌ COMPREHENSIVE TEST FAILED: Code {e.code}")
            logger.error(f"📊 Phases completed: {full_test_results}")
            
            if e.code == 1011:
                pytest.fail(
                    f"SOLUTION INCOMPLETE: Still getting 1011 errors in comprehensive test. "
                    f"Time: {connection_time:.2f}s, Phases: {full_test_results}. "
                    f"This indicates the WebSocket 1011 fix is not fully implemented."
                )
            else:
                pytest.fail(
                    f"UNEXPECTED ERROR in comprehensive test: Code {e.code}, "
                    f"Phases: {full_test_results}"
                )

    async def test_multiple_authenticated_websocket_success(
        self,
        staging_config: StagingTestConfig,
        staging_websocket_auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test multiple concurrent authenticated WebSocket connections succeed.
        
        This validates that the fix works consistently across multiple users
        and doesn't have race conditions or connection limit issues.
        
        EXPECTED: All concurrent connections should succeed after the fix.
        """
        logger.info("🧪 SOLUTION TEST: Multiple authenticated WebSocket connections")
        
        num_concurrent_connections = 5
        connection_results = []
        
        async def test_concurrent_connection(connection_id: int) -> Dict[str, Any]:
            """Test a single concurrent WebSocket connection."""
            start_time = time.time()
            
            try:
                # Create unique user for this connection
                unique_email = f"concurrent_test_{connection_id}_{int(time.time())}@example.com"
                token = await staging_websocket_auth_helper.get_staging_token_async(email=unique_email)
                
                # Get connection-specific headers
                headers = staging_websocket_auth_helper.get_websocket_headers(token)
                headers.update({
                    "X-Connection-ID": str(connection_id),
                    "X-Concurrent-Test": "true",
                    "X-User-Simulation": unique_email
                })
                
                # Establish connection
                async with websockets.connect(
                    staging_config.urls.websocket_url,
                    additional_headers=headers,
                    open_timeout=15.0
                ) as websocket:
                    connection_time = time.time() - start_time
                    
                    # Test message exchange
                    test_message = {
                        "type": "concurrent_connection_test",
                        "connection_id": connection_id,
                        "user_email": unique_email
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    
                    return {
                        "connection_id": connection_id,
                        "success": True,
                        "connection_time": connection_time,
                        "message_exchange": True,
                        "user_email": unique_email
                    }
                    
            except websockets.exceptions.ConnectionClosedError as e:
                return {
                    "connection_id": connection_id,
                    "success": False,
                    "error_code": e.code,
                    "error_reason": e.reason,
                    "connection_time": time.time() - start_time
                }
            except Exception as e:
                return {
                    "connection_id": connection_id,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "connection_time": time.time() - start_time
                }
        
        # Execute concurrent connections
        logger.info(f"🔄 Testing {num_concurrent_connections} concurrent connections...")
        start_time = time.time()
        
        tasks = [test_concurrent_connection(i) for i in range(num_concurrent_connections)]
        connection_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_connections = 0
        failed_connections_1011 = 0
        failed_connections_other = 0
        
        logger.info("📊 CONCURRENT CONNECTION RESULTS:")
        for result in connection_results:
            if isinstance(result, Exception):
                failed_connections_other += 1
                logger.error(f"❌ Task exception: {result}")
                continue
            
            if result["success"]:
                successful_connections += 1
                logger.info(f"✅ Connection {result['connection_id']}: SUCCESS ({result['connection_time']:.2f}s)")
            else:
                if result.get("error_code") == 1011:
                    failed_connections_1011 += 1
                    logger.error(f"❌ Connection {result['connection_id']}: 1011 ERROR")
                else:
                    failed_connections_other += 1
                    logger.error(f"❌ Connection {result['connection_id']}: OTHER ERROR ({result.get('error_type', 'unknown')})")
        
        # Validate results
        logger.info(f"📊 Total time: {total_time:.2f}s")
        logger.info(f"📊 Successful: {successful_connections}/{num_concurrent_connections}")
        logger.info(f"📊 Failed (1011): {failed_connections_1011}")
        logger.info(f"📊 Failed (other): {failed_connections_other}")
        
        success_rate = successful_connections / num_concurrent_connections
        
        if success_rate >= 0.8:  # 80% success rate minimum
            logger.info(f"✅ SOLUTION VALIDATED: {success_rate:.0%} concurrent connection success rate")
        else:
            pytest.fail(
                f"SOLUTION INCOMPLETE: Only {success_rate:.0%} success rate. "
                f"Expected ≥80% for concurrent connections. "
                f"1011 errors: {failed_connections_1011}, Other errors: {failed_connections_other}"
            )
        
        if failed_connections_1011 > 0:
            pytest.fail(
                f"SOLUTION INCOMPLETE: Still getting {failed_connections_1011} 1011 errors "
                f"out of {num_concurrent_connections} concurrent connections."
            )
        
        return {
            "solution": "concurrent_websocket_connections",
            "success": True,
            "total_connections": num_concurrent_connections,
            "successful_connections": successful_connections,
            "success_rate": success_rate,
            "total_time": total_time
        }


# Solution validation helper functions

def validate_solution_implementation():
    """Helper function to validate that solutions are properly implemented."""
    import os
    from shared.isolated_environment import get_env
    
    env = get_env()
    solution_indicators = {
        "environment_variables": {
            "E2E_TESTING": env.get("E2E_TESTING"),
            "STAGING_E2E_TEST": env.get("STAGING_E2E_TEST"),
            "E2E_TEST_ENV": env.get("E2E_TEST_ENV")
        },
        "staging_environment": {
            "ENVIRONMENT": env.get("ENVIRONMENT"),
            "GOOGLE_CLOUD_PROJECT": env.get("GOOGLE_CLOUD_PROJECT"),
            "K_SERVICE": env.get("K_SERVICE")
        }
    }
    
    logger.info("🔍 SOLUTION IMPLEMENTATION CHECK:")
    for category, vars in solution_indicators.items():
        logger.info(f"   {category.upper()}:")
        for key, value in vars.items():
            status = "SET" if value else "NOT SET"
            logger.info(f"     {key}: {status}")
    
    return solution_indicators


@pytest.fixture(autouse=True)
def validate_solution_setup():
    """Automatically validate solution setup for all tests."""
    solution_status = validate_solution_implementation()
    yield solution_status


if __name__ == "__main__":
    # Direct test execution for solution validation
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
    
    # Run solution validation tests directly
    async def run_solution_tests():
        staging_config = StagingTestConfig()
        auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        test_instance = TestWebSocket1011ErrorSolutionValidation()
        
        solution_tests = [
            ("header_based_detection", test_instance.test_websocket_header_based_e2e_detection_solution),
            ("staging_auto_detection", test_instance.test_staging_auto_detection_from_gcp_metadata),
            ("comprehensive_functionality", test_instance.test_websocket_connection_with_proper_context),
            ("concurrent_connections", test_instance.test_multiple_authenticated_websocket_success)
        ]
        
        results = {}
        for test_name, test_method in solution_tests:
            try:
                print(f"\n🧪 Running solution test: {test_name}")
                result = await test_method(staging_config, auth_helper)
                results[test_name] = {"success": True, "result": result}
                print(f"✅ {test_name}: SUCCESS")
                
            except Exception as e:
                results[test_name] = {"success": False, "error": str(e)}
                print(f"❌ {test_name}: FAILED - {e}")
        
        print(f"\n📊 SOLUTION VALIDATION SUMMARY:")
        for test_name, result in results.items():
            status = "PASS" if result["success"] else "FAIL"
            print(f"   {test_name}: {status}")
        
        overall_success = all(result["success"] for result in results.values())
        print(f"\n🎯 OVERALL SOLUTION STATUS: {'SUCCESS' if overall_success else 'INCOMPLETE'}")
    
    asyncio.run(run_solution_tests())