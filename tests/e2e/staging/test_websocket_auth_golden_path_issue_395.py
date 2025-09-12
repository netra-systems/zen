"""
E2E Tests for Complete Golden Path with Authentication on Staging GCP

ISSUE #395 TEST PLAN (Step 3) - E2E Test Suite
Tests the complete Golden Path user journey with WebSocket authentication on staging GCP:

TARGET ISSUES:
1. Complete authentication failure preventing Golden Path execution
2. WebSocket handshake failures in GCP Cloud Run environment  
3. E2E environment detection failures in staging deployments
4. End-to-end user workflow broken due to authentication errors

CRITICAL: These tests run against staging GCP environment to validate real-world scenarios.
"""

import pytest
import asyncio
import logging
import time
from typing import Dict, Any, Optional
import json
import os

# SSOT imports for E2E testing
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from tests.e2e.staging_config import StagingTestConfig

logger = logging.getLogger(__name__)

# Mark as E2E staging test
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.websocket,
    pytest.mark.golden_path,
    pytest.mark.auth,
    pytest.mark.issue_395
]


class TestWebSocketAuthGoldenPathIssue395(SSotAsyncTestCase):
    """
    E2E test suite for Golden Path with WebSocket authentication on staging GCP.
    
    Business Impact:
    - Tests complete Golden Path user journey that protects $500K+ ARR
    - Validates WebSocket authentication in real GCP Cloud Run environment
    - Tests end-to-end chat functionality with real AI agent responses
    - Reproduces and validates fixes for production authentication issues
    
    EXPECTED BEHAVIOR:
    - Initial runs: Tests should FAIL (reproducing Golden Path failures)
    - After fixes: Tests should PASS (validating Golden Path restoration)
    """

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures for E2E testing."""
        super().setUpClass()
        cls.staging_config = StagingTestConfig()
        cls.e2e_auth_helper = E2EAuthHelper()
        cls.websocket_helper = E2EWebSocketAuthHelper()
        
        # Verify staging environment is available
        if not cls.staging_config.is_staging_environment_available():
            pytest.skip("Staging environment not available for E2E testing")

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Configure E2E environment for staging tests
        self.e2e_env_vars = {
            "E2E_TESTING": "1",
            "STAGING_E2E_TEST": "1", 
            "E2E_TEST_ENV": "staging",
            "ENVIRONMENT": "staging"
        }
        
        # Set environment variables for this test
        for key, value in self.e2e_env_vars.items():
            os.environ[key] = value

    def tearDown(self):
        """Clean up after test."""
        # Clean up E2E environment variables
        for key in self.e2e_env_vars:
            if key in os.environ:
                del os.environ[key]
        super().tearDown()

    @pytest.mark.timeout(300)  # 5 minute timeout for E2E test
    async def test_complete_golden_path_user_journey_e2e(self):
        """
        PRIMARY E2E TEST: Complete Golden Path user journey.
        
        Issue #395: Tests the complete user journey from login to AI response on staging.
        This test should FAIL initially if Golden Path is broken by authentication issues.
        
        Flow tested:
        1. User authentication/login
        2. WebSocket connection establishment  
        3. Chat interface loading
        4. Agent request submission
        5. Real-time agent events via WebSocket
        6. AI response delivery
        """
        logger.info("[U+1F9EA] E2E TEST: Complete Golden Path user journey on staging")
        
        # Step 1: Authenticate user for staging environment
        try:
            auth_result = await self.e2e_auth_helper.authenticate_test_user_staging()
            if not auth_result.success:
                self.fail(f"GOLDEN PATH AUTH BUG: User authentication failed: {auth_result.error_message}")
                
            logger.info(f" PASS:  Step 1: User authenticated successfully (user: {auth_result.user_id[:8]}...)")
            
        except Exception as e:
            self.fail(f"GOLDEN PATH AUTH BUG: Authentication error: {e}")
        
        # Step 2: Establish WebSocket connection with authentication
        try:
            websocket_client = await self.websocket_helper.connect_to_staging(
                auth_token=auth_result.token,
                user_id=auth_result.user_id
            )
            
            if not websocket_client.is_connected():
                self.fail("GOLDEN PATH WEBSOCKET BUG: WebSocket connection failed")
                
            logger.info(" PASS:  Step 2: WebSocket connection established successfully")
            
        except Exception as e:
            self.fail(f"GOLDEN PATH WEBSOCKET BUG: WebSocket connection error: {e}")
        
        # Step 3: Test chat interface loading (simulate frontend behavior)
        try:
            # Send initial handshake message
            handshake_message = {
                "type": "client_handshake",
                "user_id": auth_result.user_id,
                "client_version": "test-client-1.0",
                "timestamp": time.time()
            }
            
            await websocket_client.send_json(handshake_message)
            
            # Wait for handshake response
            response = await asyncio.wait_for(
                websocket_client.receive_json(), 
                timeout=10.0
            )
            
            if response.get("type") != "handshake_acknowledged":
                self.fail(f"GOLDEN PATH HANDSHAKE BUG: Unexpected handshake response: {response}")
                
            logger.info(" PASS:  Step 3: Chat interface handshake completed successfully")
            
        except asyncio.TimeoutError:
            self.fail("GOLDEN PATH HANDSHAKE BUG: Handshake timeout - no response from server")
        except Exception as e:
            self.fail(f"GOLDEN PATH HANDSHAKE BUG: Handshake error: {e}")
        
        # Step 4: Submit agent request (core Golden Path functionality)
        try:
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",  # Use simple triage agent for reliable testing
                "message": "Test message for Golden Path validation",
                "thread_id": f"test-thread-{int(time.time())}",
                "request_id": f"test-req-{int(time.time())}"
            }
            
            await websocket_client.send_json(agent_request)
            logger.info(" PASS:  Step 4: Agent request submitted successfully")
            
        except Exception as e:
            self.fail(f"GOLDEN PATH AGENT REQUEST BUG: Agent request error: {e}")
        
        # Step 5: Collect and validate WebSocket events (CRITICAL for Golden Path)
        try:
            events_collected = []
            required_events = ["agent_started", "agent_thinking", "agent_completed"]
            event_timeout = 60.0  # 1 minute timeout for agent execution
            
            start_time = time.time()
            
            while len(events_collected) < len(required_events) and (time.time() - start_time) < event_timeout:
                try:
                    event = await asyncio.wait_for(
                        websocket_client.receive_json(),
                        timeout=10.0
                    )
                    
                    events_collected.append(event)
                    event_type = event.get("type", "unknown")
                    
                    logger.info(f"[U+1F4E8] Received WebSocket event: {event_type}")
                    
                    # Check if we've received all required events
                    received_event_types = [e.get("type") for e in events_collected]
                    if all(req_event in received_event_types for req_event in required_events):
                        break
                        
                except asyncio.TimeoutError:
                    logger.warning("[U+23F0] Event collection timeout - continuing to wait for remaining events")
                    continue
                    
            # Validate required events were received
            received_event_types = [e.get("type") for e in events_collected]
            missing_events = [event for event in required_events if event not in received_event_types]
            
            if missing_events:
                self.fail(f"GOLDEN PATH WEBSOCKET EVENTS BUG: Missing required events: {missing_events}")
                
            logger.info(" PASS:  Step 5: All required WebSocket events received successfully")
            
        except Exception as e:
            self.fail(f"GOLDEN PATH WEBSOCKET EVENTS BUG: Event collection error: {e}")
        
        # Step 6: Validate AI response delivery (final Golden Path validation)
        try:
            # Find the agent_completed event with the AI response
            completed_event = None
            for event in events_collected:
                if event.get("type") == "agent_completed":
                    completed_event = event
                    break
            
            if not completed_event:
                self.fail("GOLDEN PATH AI RESPONSE BUG: No agent_completed event received")
            
            # Validate response structure
            response_data = completed_event.get("data", {})
            if not response_data.get("result"):
                self.fail("GOLDEN PATH AI RESPONSE BUG: No AI response data in completed event")
                
            ai_response = response_data["result"]
            
            # Validate AI response contains meaningful content
            if isinstance(ai_response, str) and len(ai_response.strip()) > 0:
                logger.info(" PASS:  Step 6: AI response delivered successfully")
            elif isinstance(ai_response, dict) and ai_response.get("content"):
                logger.info(" PASS:  Step 6: AI response delivered successfully (structured)")
            else:
                self.fail(f"GOLDEN PATH AI RESPONSE BUG: Invalid AI response format: {ai_response}")
                
        except Exception as e:
            self.fail(f"GOLDEN PATH AI RESPONSE BUG: Response validation error: {e}")
        
        finally:
            # Clean up WebSocket connection
            try:
                await websocket_client.close()
                logger.info("[U+1F9F9] WebSocket connection closed successfully")
            except Exception as e:
                logger.warning(f" WARNING: [U+FE0F] Error closing WebSocket connection: {e}")
        
        logger.info(" CELEBRATION:  GOLDEN PATH SUCCESS: Complete user journey validated successfully!")

    @pytest.mark.timeout(120)  # 2 minute timeout
    async def test_websocket_authentication_staging_gcp(self):
        """
        SECONDARY E2E TEST: WebSocket authentication in staging GCP environment.
        
        Issue #395: Tests WebSocket authentication specifically in GCP Cloud Run environment.
        This test should FAIL initially if GCP authentication is broken.
        """
        logger.info("[U+1F9EA] E2E TEST: WebSocket authentication in staging GCP")
        
        # Test authentication in GCP staging environment
        try:
            # Get staging endpoint configuration
            staging_ws_url = self.staging_config.get_websocket_url()
            if not staging_ws_url:
                self.fail("STAGING CONFIG BUG: No WebSocket URL configured for staging")
            
            # Authenticate test user
            auth_result = await self.e2e_auth_helper.authenticate_test_user_staging()
            if not auth_result.success:
                self.fail(f"STAGING AUTH BUG: Authentication failed: {auth_result.error_message}")
            
            # Test WebSocket connection with authentication
            websocket_client = await self.websocket_helper.connect_with_auth(
                url=staging_ws_url,
                token=auth_result.token,
                user_id=auth_result.user_id
            )
            
            # Validate connection is authenticated
            if not websocket_client.is_authenticated():
                self.fail("STAGING WEBSOCKET AUTH BUG: Connection not properly authenticated")
            
            # Test authenticated WebSocket operations
            ping_message = {
                "type": "ping", 
                "timestamp": time.time(),
                "authenticated": True
            }
            
            await websocket_client.send_json(ping_message)
            
            # Wait for pong response
            pong_response = await asyncio.wait_for(
                websocket_client.receive_json(),
                timeout=10.0
            )
            
            if pong_response.get("type") != "pong":
                self.fail(f"STAGING WEBSOCKET AUTH BUG: Expected pong, got: {pong_response}")
            
            logger.info(" PASS:  WebSocket authentication in staging GCP validated successfully")
            
        except Exception as e:
            self.fail(f"STAGING WEBSOCKET AUTH BUG: Authentication error: {e}")
        
        finally:
            try:
                await websocket_client.close()
            except:
                pass

    @pytest.mark.timeout(180)  # 3 minute timeout  
    async def test_e2e_environment_detection_staging(self):
        """
        TERTIARY E2E TEST: E2E environment detection in staging deployment.
        
        Issue #395: Tests that E2E environment detection works correctly in staging.
        This test should FAIL initially if environment detection is broken.
        """
        logger.info("[U+1F9EA] E2E TEST: E2E environment detection in staging")
        
        # Test environment detection in staging context
        try:
            # Import environment detection from actual deployment
            from netra_backend.app.websocket_core.unified_websocket_auth import extract_e2e_context_from_websocket
            from unittest.mock import Mock
            
            # Create mock WebSocket representing staging client
            mock_websocket = Mock()
            mock_websocket.headers = {
                "user-agent": "staging-e2e-test-client",
                "origin": self.staging_config.get_frontend_url()
            }
            mock_websocket.client = Mock()
            mock_websocket.client.host = "staging-client-ip"
            mock_websocket.client.port = 443
            
            # Test environment detection
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Validate E2E context detection
            if e2e_context is None:
                # Check if this is expected (no E2E variables set in staging)
                staging_has_e2e_vars = any(
                    os.environ.get(var) == "1" or os.environ.get(var) == "staging"
                    for var in ["E2E_TESTING", "STAGING_E2E_TEST", "E2E_TEST_ENV"]
                )
                
                if staging_has_e2e_vars:
                    self.fail("STAGING E2E DETECTION BUG: E2E variables set but context not detected")
                else:
                    logger.info(" PASS:  E2E context correctly not detected (no E2E variables)")
            else:
                # Validate context structure if detected
                self.assertIsInstance(e2e_context, dict, "E2E context should be dictionary")
                self.assertIn("is_e2e_testing", e2e_context, "Missing is_e2e_testing field")
                self.assertIn("environment", e2e_context, "Missing environment field")
                
                logger.info(f" PASS:  E2E context detected successfully: {e2e_context.get('environment')}")
                
        except Exception as e:
            self.fail(f"STAGING E2E DETECTION BUG: Environment detection error: {e}")

    @pytest.mark.timeout(240)  # 4 minute timeout
    async def test_golden_path_error_recovery_e2e(self):
        """
        QUATERNARY E2E TEST: Golden Path error recovery scenarios.
        
        Issue #395: Tests that Golden Path can recover from authentication errors.
        This test validates error handling and recovery mechanisms.
        """
        logger.info("[U+1F9EA] E2E TEST: Golden Path error recovery scenarios")
        
        # Test 1: Recovery from initial authentication failure
        try:
            # First attempt with invalid token (should fail)
            invalid_auth_result = await self.e2e_auth_helper.authenticate_with_invalid_token()
            
            if invalid_auth_result.success:
                self.fail("ERROR RECOVERY BUG: Invalid token authentication should fail")
            
            logger.info(" PASS:  Invalid token correctly rejected")
            
            # Second attempt with valid authentication (should succeed)
            valid_auth_result = await self.e2e_auth_helper.authenticate_test_user_staging()
            
            if not valid_auth_result.success:
                self.fail(f"ERROR RECOVERY BUG: Valid authentication failed after invalid attempt: {valid_auth_result.error_message}")
            
            logger.info(" PASS:  Valid authentication succeeded after invalid attempt")
            
        except Exception as e:
            self.fail(f"ERROR RECOVERY BUG: Authentication recovery error: {e}")
        
        # Test 2: Recovery from WebSocket connection failure
        try:
            # Attempt connection with invalid configuration (should fail gracefully)
            try:
                invalid_ws_client = await self.websocket_helper.connect_with_invalid_config()
                # If connection succeeds when it shouldn't, that's a bug
                if invalid_ws_client.is_connected():
                    self.fail("ERROR RECOVERY BUG: Invalid WebSocket config should not connect")
            except Exception:
                # Expected failure - this is good
                logger.info(" PASS:  Invalid WebSocket config correctly rejected")
            
            # Attempt connection with valid configuration (should succeed)
            valid_auth_result = await self.e2e_auth_helper.authenticate_test_user_staging()
            valid_ws_client = await self.websocket_helper.connect_to_staging(
                auth_token=valid_auth_result.token,
                user_id=valid_auth_result.user_id
            )
            
            if not valid_ws_client.is_connected():
                self.fail("ERROR RECOVERY BUG: Valid WebSocket connection failed after invalid attempt")
            
            logger.info(" PASS:  Valid WebSocket connection succeeded after invalid attempt")
            
            # Clean up
            await valid_ws_client.close()
            
        except Exception as e:
            self.fail(f"ERROR RECOVERY BUG: WebSocket recovery error: {e}")

    async def test_golden_path_performance_e2e(self):
        """
        PERFORMANCE E2E TEST: Golden Path performance validation.
        
        Issue #395: Tests that Golden Path performs within acceptable limits.
        This test validates that authentication fixes don't impact performance.
        """
        logger.info("[U+1F9EA] E2E TEST: Golden Path performance validation")
        
        # Performance benchmarks for Golden Path
        max_auth_time = 5.0  # 5 seconds max for authentication
        max_websocket_connect_time = 3.0  # 3 seconds max for WebSocket connection
        max_agent_response_time = 30.0  # 30 seconds max for agent response
        
        try:
            # Benchmark authentication time
            auth_start = time.time()
            auth_result = await self.e2e_auth_helper.authenticate_test_user_staging()
            auth_time = time.time() - auth_start
            
            if not auth_result.success:
                self.fail(f"GOLDEN PATH PERFORMANCE BUG: Authentication failed: {auth_result.error_message}")
            
            if auth_time > max_auth_time:
                self.fail(f"GOLDEN PATH PERFORMANCE BUG: Authentication too slow: {auth_time:.2f}s > {max_auth_time}s")
            
            logger.info(f" PASS:  Authentication performance: {auth_time:.2f}s")
            
            # Benchmark WebSocket connection time
            ws_start = time.time()
            websocket_client = await self.websocket_helper.connect_to_staging(
                auth_token=auth_result.token,
                user_id=auth_result.user_id
            )
            ws_time = time.time() - ws_start
            
            if not websocket_client.is_connected():
                self.fail("GOLDEN PATH PERFORMANCE BUG: WebSocket connection failed")
            
            if ws_time > max_websocket_connect_time:
                self.fail(f"GOLDEN PATH PERFORMANCE BUG: WebSocket connection too slow: {ws_time:.2f}s > {max_websocket_connect_time}s")
            
            logger.info(f" PASS:  WebSocket connection performance: {ws_time:.2f}s")
            
            # Benchmark agent response time
            agent_start = time.time()
            
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Quick test message",
                "thread_id": f"perf-test-{int(time.time())}"
            }
            
            await websocket_client.send_json(agent_request)
            
            # Wait for agent_completed event
            agent_completed = False
            while not agent_completed and (time.time() - agent_start) < max_agent_response_time:
                try:
                    event = await asyncio.wait_for(
                        websocket_client.receive_json(),
                        timeout=5.0
                    )
                    if event.get("type") == "agent_completed":
                        agent_completed = True
                        break
                except asyncio.TimeoutError:
                    continue
            
            agent_time = time.time() - agent_start
            
            if not agent_completed:
                self.fail(f"GOLDEN PATH PERFORMANCE BUG: Agent response timeout: {agent_time:.2f}s > {max_agent_response_time}s")
            
            if agent_time > max_agent_response_time:
                self.fail(f"GOLDEN PATH PERFORMANCE BUG: Agent response too slow: {agent_time:.2f}s > {max_agent_response_time}s")
            
            logger.info(f" PASS:  Agent response performance: {agent_time:.2f}s")
            
            # Clean up
            await websocket_client.close()
            
        except Exception as e:
            self.fail(f"GOLDEN PATH PERFORMANCE BUG: Performance test error: {e}")
        
        logger.info(" TARGET:  Golden Path performance validation completed successfully")


if __name__ == '__main__':
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])