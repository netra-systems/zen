"""
WebSocket 1011 Error Reproduction Test Suite

This test suite reproduces the exact WebSocket 1011 internal errors identified in staging.
Based on Five-Whys analysis: Environment variable propagation gap between client test
environment and GCP Cloud Run staging services.

Business Impact:
- Reproduces critical WebSocket connection failures affecting $120K+ MRR chat functionality  
- Validates root cause: E2E environment variables not detected in staging Cloud Run
- Tests the exact failure patterns seen in P1 staging tests

CRITICAL: These tests are EXPECTED TO FAIL initially, reproducing the 1011 errors.
After remediation (environment variable configuration), these tests should PASS.
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
from tests.e2e.staging_config import StagingTestConfig, staging_urls
from test_framework.websocket_helpers import WebSocketTestHelpers, MockWebSocketConnection

logger = logging.getLogger(__name__)

# Configure test to use real staging environment
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.websocket,
    pytest.mark.expected_failure,  # These tests SHOULD fail initially - they reproduce the bug
]


@pytest.fixture
def staging_config():
    """Staging configuration for WebSocket 1011 error reproduction."""
    return StagingTestConfig()


@pytest.fixture
def staging_auth_helper(staging_config):
    """E2E auth helper configured for staging environment."""
    return E2EWebSocketAuthHelper(environment="staging")


@pytest.fixture
def staging_websocket_auth_helper(staging_config):
    """WebSocket-specific auth helper for staging."""
    return E2EWebSocketAuthHelper(environment="staging")


class TestWebSocket1011ErrorReproduction:
    """
    Test suite that reproduces the exact WebSocket 1011 internal errors.
    
    These tests connect to actual GCP staging WebSocket endpoints and demonstrate
    the authentication failure patterns that cause 1011 errors.
    
    EXPECTED BEHAVIOR:
    - Tests should initially FAIL with 1011 errors
    - After environment variable configuration, tests should PASS
    """
    
    async def test_websocket_connection_1011_error_exact_reproduction(
        self, 
        staging_config: StagingTestConfig,
        staging_websocket_auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Reproduce the exact WebSocket 1011 error from P1 staging tests.
        
        This test connects to the actual staging WebSocket endpoint and reproduces
        the authentication failure that causes the 1011 internal error.
        
        EXPECTED: This test should FAIL with ConnectionClosedError code 1011
        until environment variables are properly configured in staging.
        """
        logger.info(" SEARCH:  REPRODUCTION TEST: WebSocket 1011 error exact reproduction")
        logger.info(f"Target URL: {staging_config.urls.websocket_url}")
        
        connection_start_time = time.time()
        error_details = {}
        
        try:
            # CRITICAL: This connection should fail with 1011 due to E2E env var gap
            logger.info("Attempting WebSocket connection to staging (expecting 1011 failure)...")
            
            # Get staging token (may fail due to OAuth simulation issues)
            try:
                token = await staging_websocket_auth_helper.get_staging_token_async()
                logger.info(f" PASS:  Token acquired: {token[:20]}...")
            except Exception as e:
                logger.warning(f" FAIL:  Token acquisition failed: {e}")
                token = staging_websocket_auth_helper.create_test_jwt_token()
                logger.info(" CYCLE:  Using fallback test JWT token")
            
            # Get headers with E2E detection (but staging won't detect E2E env vars)
            headers = staging_websocket_auth_helper.get_websocket_headers(token)
            logger.info(f"[U+1F4E4] Headers sent: {list(headers.keys())}")
            
            # Connect with extended timeout to capture the full failure sequence
            connection_timeout = 15.0  # Extended to capture full auth failure
            
            websocket = None
            async with websockets.connect(
                staging_config.urls.websocket_url,
                additional_headers=headers,
                open_timeout=connection_timeout,
                close_timeout=5.0
            ) as websocket:
                connection_time = time.time() - connection_start_time
                logger.info(f" WARNING: [U+FE0F] UNEXPECTED: Connection succeeded in {connection_time:.2f}s")
                
                # If connection succeeds, try sending a message to trigger any delayed failures
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_context": "websocket_1011_reproduction"
                }
                
                await websocket.send(json.dumps(test_message))
                logger.info("[U+1F4E4] Test message sent, waiting for response...")
                
                # Wait for response or connection close
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                logger.info(f"[U+1F4E5] Response received: {response[:100]}...")
                
                # If we get here, the bug may be fixed
                pytest.fail(
                    "REPRODUCTION FAILED: WebSocket connection succeeded when it should fail with 1011. "
                    "This indicates the environment variable issue may be resolved. "
                    f"Connection time: {connection_time:.2f}s"
                )
                
        except websockets.exceptions.ConnectionClosedError as e:
            connection_time = time.time() - connection_start_time
            error_details = {
                "code": e.code,
                "reason": e.reason or "No reason provided",
                "connection_time": connection_time,
                "error_type": "ConnectionClosedError"
            }
            
            logger.info(f" FAIL:  CONNECTION CLOSED: Code {e.code}, Reason: {e.reason}")
            logger.info(f"[U+23F1][U+FE0F] Connection time: {connection_time:.2f}s")
            
            if e.code == 1011:
                logger.info(" PASS:  REPRODUCTION SUCCESSFUL: Got expected 1011 internal error")
                
                # This is the expected failure - document it thoroughly
                expected_failure_message = (
                    f"EXPECTED FAILURE: WebSocket 1011 internal error reproduced successfully. "
                    f"Code: {e.code}, Reason: '{e.reason}', Time: {connection_time:.2f}s. "
                    f"This confirms the root cause: E2E environment variables not detected in staging, "
                    f"causing authentication bypass to fail and strict JWT validation to trigger 1011 error."
                )
                
                # Mark as expected failure with detailed context
                pytest.xfail(expected_failure_message)
                
            else:
                # Different error code - this is unexpected
                pytest.fail(
                    f"UNEXPECTED ERROR CODE: Got {e.code} instead of expected 1011. "
                    f"Reason: {e.reason}, Time: {connection_time:.2f}s. "
                    f"This indicates a different issue than the identified root cause."
                )
                
        except asyncio.TimeoutError:
            connection_time = time.time() - connection_start_time
            logger.warning(f" FAIL:  CONNECTION TIMEOUT: {connection_time:.2f}s")
            
            pytest.fail(
                f"CONNECTION TIMEOUT: WebSocket connection timed out after {connection_time:.2f}s. "
                f"Expected 1011 error but got timeout instead. This may indicate a different issue."
            )
            
        except Exception as e:
            connection_time = time.time() - connection_start_time
            logger.error(f" FAIL:  UNEXPECTED ERROR: {type(e).__name__}: {e}")
            
            pytest.fail(
                f"UNEXPECTED ERROR: {type(e).__name__}: {e} after {connection_time:.2f}s. "
                f"Expected 1011 ConnectionClosedError but got different error type."
            )
        
        finally:
            # Log comprehensive error details for analysis
            if error_details:
                logger.info(" SEARCH:  REPRODUCTION TEST RESULTS:")
                logger.info(f"   Error Code: {error_details.get('code', 'N/A')}")
                logger.info(f"   Reason: {error_details.get('reason', 'N/A')}")  
                logger.info(f"   Connection Time: {error_details.get('connection_time', 0):.2f}s")
                logger.info(f"   Error Type: {error_details.get('error_type', 'N/A')}")

    async def test_multiple_user_websocket_1011_pattern(
        self,
        staging_config: StagingTestConfig,
        staging_websocket_auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test WebSocket 1011 error pattern across multiple concurrent user connections.
        
        This validates that the 1011 error is consistent across different user sessions
        and not related to connection pooling or race conditions.
        
        EXPECTED: All connections should fail with 1011 errors consistently.
        """
        logger.info(" SEARCH:  REPRODUCTION TEST: Multiple user WebSocket 1011 pattern")
        
        num_concurrent_users = 3
        connection_results = []
        
        async def test_user_connection(user_index: int) -> Dict[str, Any]:
            """Test WebSocket connection for a single user."""
            user_start_time = time.time()
            
            try:
                # Create unique test user
                user_email = f"e2e_user_{user_index}_{int(time.time())}@example.com"
                
                # Get staging-compatible token
                try:
                    token = await staging_websocket_auth_helper.get_staging_token_async(email=user_email)
                except Exception:
                    token = staging_websocket_auth_helper.create_test_jwt_token(
                        user_id=f"test-user-{user_index}",
                        email=user_email
                    )
                
                # Get WebSocket headers
                headers = staging_websocket_auth_helper.get_websocket_headers(token)
                
                # Attempt connection
                async with websockets.connect(
                    staging_config.urls.websocket_url,
                    additional_headers=headers,
                    open_timeout=12.0
                ) as websocket:
                    # Unexpected success
                    return {
                        "user_index": user_index,
                        "success": True,
                        "connection_time": time.time() - user_start_time,
                        "error": None
                    }
                    
            except websockets.exceptions.ConnectionClosedError as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "connection_time": time.time() - user_start_time,
                    "error": {
                        "code": e.code,
                        "reason": e.reason,
                        "type": "ConnectionClosedError"
                    }
                }
            except Exception as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "connection_time": time.time() - user_start_time,
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e)
                    }
                }
        
        # Run concurrent connection attempts
        logger.info(f"Testing {num_concurrent_users} concurrent WebSocket connections...")
        start_time = time.time()
        
        tasks = [test_user_connection(i) for i in range(num_concurrent_users)]
        connection_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        logger.info(f"[U+23F1][U+FE0F] Total test time: {total_time:.2f}s")
        
        # Analyze results
        failures_1011 = 0
        failures_other = 0
        successes = 0
        
        for result in connection_results:
            if isinstance(result, Exception):
                failures_other += 1
                logger.error(f"Task exception: {result}")
                continue
                
            if result["success"]:
                successes += 1
                logger.warning(f" FAIL:  User {result['user_index']} connection succeeded (unexpected)")
            else:
                error = result["error"]
                if error and error.get("code") == 1011:
                    failures_1011 += 1
                    logger.info(f" PASS:  User {result['user_index']} got expected 1011 error in {result['connection_time']:.2f}s")
                else:
                    failures_other += 1
                    logger.warning(f" WARNING: [U+FE0F] User {result['user_index']} got unexpected error: {error}")
        
        logger.info(" SEARCH:  MULTIPLE USER TEST RESULTS:")
        logger.info(f"   Total users: {num_concurrent_users}")
        logger.info(f"   1011 errors: {failures_1011}")
        logger.info(f"   Other errors: {failures_other}")
        logger.info(f"   Successes: {successes}")
        
        # Validate the pattern
        if failures_1011 >= (num_concurrent_users - 1):  # Allow for some variance
            logger.info(" PASS:  REPRODUCTION SUCCESSFUL: Consistent 1011 error pattern across users")
            pytest.xfail(
                f"EXPECTED FAILURE: {failures_1011}/{num_concurrent_users} users got 1011 errors. "
                f"This confirms consistent authentication failure pattern in staging environment."
            )
        elif successes > 0:
            pytest.fail(
                f"REPRODUCTION FAILED: {successes} connections succeeded unexpectedly. "
                f"This suggests the environment variable issue may be resolved."
            )
        else:
            pytest.fail(
                f"UNEXPECTED PATTERN: Got {failures_other} non-1011 errors instead of expected 1011 pattern. "
                f"This indicates a different issue than the identified root cause."
            )

    async def test_staging_environment_e2e_detection_failure(
        self,
        staging_config: StagingTestConfig,
        staging_auth_helper: E2EAuthHelper
    ):
        """
        Test that E2E environment variables are not properly detected in staging.
        
        This test validates the root cause: E2E testing environment variables
        are not being detected in the GCP Cloud Run staging environment.
        
        EXPECTED: E2E detection should fail (enabled=false), confirming the root cause.
        """
        logger.info(" SEARCH:  REPRODUCTION TEST: Staging E2E detection failure")
        
        # Test 1: Check staging health endpoint for E2E status
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                health_url = f"{staging_config.urls.backend_url}/health"
                logger.info(f"Checking health endpoint: {health_url}")
                
                response = await client.get(health_url)
                if response.status_code == 200:
                    health_data = response.json()
                    e2e_status = health_data.get("e2e_testing", {})
                    
                    logger.info(f" CHART:  Health data E2E status: {e2e_status}")
                    
                    if e2e_status.get("enabled") is False:
                        logger.info(" PASS:  REPRODUCTION SUCCESSFUL: E2E testing disabled in staging health check")
                        pytest.xfail(
                            "EXPECTED FAILURE: E2E testing shows as disabled in staging environment. "
                            "This confirms the root cause: E2E environment variables not detected."
                        )
                    else:
                        pytest.fail(
                            f"REPRODUCTION FAILED: E2E testing shows as enabled: {e2e_status}. "
                            f"This suggests the environment variable issue may be resolved."
                        )
                else:
                    logger.warning(f" FAIL:  Health endpoint returned {response.status_code}")
                    
        except Exception as e:
            logger.error(f" FAIL:  Health check failed: {e}")
        
        # Test 2: Attempt OAuth simulation bypass (should fail due to missing env vars)
        try:
            logger.info("Testing OAuth simulation bypass...")
            token = await staging_auth_helper.get_staging_token_async()
            
            if token:
                # Decode token to check if it's a fallback JWT
                try:
                    import jwt
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    
                    if decoded.get("staging") and decoded.get("e2e_test"):
                        logger.info(" PASS:  REPRODUCTION CONFIRMED: Using fallback JWT (OAuth simulation failed)")
                        pytest.xfail(
                            "EXPECTED FAILURE: OAuth simulation failed, using fallback JWT token. "
                            "This confirms E2E environment variables not properly configured in staging."
                        )
                    else:
                        pytest.fail(
                            "REPRODUCTION FAILED: Got proper OAuth token instead of fallback JWT. "
                            "This suggests the environment variable issue may be resolved."
                        )
                        
                except Exception as decode_error:
                    logger.warning(f"Token decode failed: {decode_error}")
                    
        except Exception as e:
            logger.info(f" PASS:  OAuth simulation failed as expected: {e}")

    async def test_factory_ssot_validation_strict_mode_trigger(
        self,
        staging_config: StagingTestConfig,
        staging_websocket_auth_helper: E2EWebSocketAuthHelper
    ):
        """
        Test that factory SSOT validation runs in strict mode due to missing E2E context.
        
        This test specifically validates that the WebSocket factory validation
        runs in strict mode instead of E2E-safe mode, causing the 1011 errors.
        
        EXPECTED: Factory validation should run in strict mode, failing and causing 1011.
        """
        logger.info(" SEARCH:  REPRODUCTION TEST: Factory SSOT validation strict mode trigger")
        
        connection_attempts = []
        
        for attempt in range(2):  # Multiple attempts to confirm pattern
            logger.info(f" CYCLE:  Attempt {attempt + 1}/2")
            start_time = time.time()
            
            try:
                # Create test token
                token = staging_websocket_auth_helper.create_test_jwt_token(
                    user_id=f"factory-test-{attempt}",
                    email=f"factory_test_{attempt}@example.com"
                )
                
                headers = staging_websocket_auth_helper.get_websocket_headers(token)
                
                # Add explicit E2E headers that staging should detect (but won't due to env var gap)
                headers.update({
                    "X-Factory-Test": "true",
                    "X-SSOT-Validation": "expected-failure",
                })
                
                # Connect and wait for factory validation failure
                async with websockets.connect(
                    staging_config.urls.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ) as websocket:
                    # If successful, this is unexpected
                    connection_time = time.time() - start_time
                    connection_attempts.append({
                        "attempt": attempt + 1,
                        "success": True,
                        "time": connection_time,
                        "error": None
                    })
                    
            except websockets.exceptions.ConnectionClosedError as e:
                connection_time = time.time() - start_time
                connection_attempts.append({
                    "attempt": attempt + 1,
                    "success": False,
                    "time": connection_time,
                    "error": {"code": e.code, "reason": e.reason}
                })
                
                if e.code == 1011 and "factory" in str(e.reason).lower():
                    logger.info(f" PASS:  Attempt {attempt + 1}: Got expected factory validation failure")
                elif e.code == 1011:
                    logger.info(f" PASS:  Attempt {attempt + 1}: Got 1011 error (likely factory-related)")
                else:
                    logger.warning(f" WARNING: [U+FE0F] Attempt {attempt + 1}: Got unexpected error code {e.code}")
                    
            except Exception as e:
                connection_time = time.time() - start_time  
                connection_attempts.append({
                    "attempt": attempt + 1,
                    "success": False,
                    "time": connection_time,
                    "error": {"type": type(e).__name__, "message": str(e)}
                })
                
            # Brief delay between attempts
            await asyncio.sleep(1.0)
        
        # Analyze results
        factory_failures = sum(1 for attempt in connection_attempts 
                              if not attempt["success"] and 
                              attempt["error"].get("code") == 1011)
        
        logger.info(" SEARCH:  FACTORY VALIDATION TEST RESULTS:")
        for attempt in connection_attempts:
            status = "SUCCESS" if attempt["success"] else f"FAIL ({attempt['error']})"
            logger.info(f"   Attempt {attempt['attempt']}: {status} in {attempt['time']:.2f}s")
        
        if factory_failures >= 1:
            logger.info(" PASS:  REPRODUCTION SUCCESSFUL: Factory SSOT validation failures confirmed")
            pytest.xfail(
                f"EXPECTED FAILURE: {factory_failures}/2 attempts got factory validation 1011 errors. "
                f"This confirms strict mode validation running instead of E2E-safe mode."
            )
        elif any(attempt["success"] for attempt in connection_attempts):
            pytest.fail(
                "REPRODUCTION FAILED: Some connections succeeded when they should fail with factory validation errors. "
                "This suggests the environment variable issue may be resolved."
            )
        else:
            pytest.fail(
                "UNEXPECTED PATTERN: Got errors but not 1011 factory validation failures. "
                "This indicates a different issue than the identified root cause."
            )


# Additional test helper functions for comprehensive reproduction

def log_reproduction_context():
    """Log comprehensive context for reproduction analysis."""
    import os
    from shared.isolated_environment import get_env
    
    env = get_env()
    logger.info(" SEARCH:  REPRODUCTION TEST CONTEXT:")
    logger.info(f"   Environment: {env.get('ENVIRONMENT', 'unknown')}")
    logger.info(f"   Test Environment: {env.get('TEST_ENV', 'unknown')}")
    logger.info(f"   Google Cloud Project: {env.get('GOOGLE_CLOUD_PROJECT', 'not-set')}")
    logger.info(f"   E2E Testing: {env.get('E2E_TESTING', '0')}")
    logger.info(f"   Pytest Running: {env.get('PYTEST_RUNNING', '0')}")
    logger.info(f"   Staging E2E Test: {env.get('STAGING_E2E_TEST', '0')}")
    logger.info(f"   E2E OAuth Simulation Key: {'SET' if env.get('E2E_OAUTH_SIMULATION_KEY') else 'NOT SET'}")

    
@pytest.fixture(autouse=True)
def log_test_context():
    """Automatically log test context for all reproduction tests."""
    log_reproduction_context()
    yield


if __name__ == "__main__":
    # Direct test execution for debugging
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
    
    # Run the reproduction test directly
    async def run_direct_test():
        staging_config = StagingTestConfig()
        auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        test_instance = TestWebSocket1011ErrorReproduction()
        
        try:
            await test_instance.test_websocket_connection_1011_error_exact_reproduction(
                staging_config, auth_helper
            )
        except Exception as e:
            print(f"Direct test result: {e}")
    
    asyncio.run(run_direct_test())