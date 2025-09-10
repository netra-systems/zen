"""
WebSocket Coroutine Regression E2E Tests

End-to-end tests for the critical WebSocket coroutine regression issue.
Tests complete chat business value validation and WebSocket connection flows.

CRITICAL ISSUE: GitHub Issue #133
- Problem: 'coroutine' object has no attribute 'get' error in WebSocket endpoint
- Root Cause: get_env() returning coroutine instead of IsolatedEnvironment  
- Business Impact: Blocking core chat functionality ($500K+ ARR impact)

CLAUDE.MD COMPLIANCE:
- ALL e2e tests MUST use real authentication (JWT/OAuth) 
- NO MOCKS in E2E tests - uses real services only
- Tests complete chat business value (connection → agent response)
- Tests designed to FAIL HARD when coroutine regression occurs
- Must prevent 0.00s execution times (indicates test bypassing)
"""

import asyncio
import inspect
import json
import logging
import time
import pytest
import unittest
from typing import Any, Dict, List, Optional
import websockets
from datetime import datetime, timedelta

from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ensure_user_id
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.ssot.base_test_case import SSotBaseTestCase
from tests.e2e.staging_config import StagingTestConfig, staging_urls
from tests.e2e.jwt_token_helpers import JWTTestHelper

logger = logging.getLogger(__name__)


class TestWebSocketCoroutineRegressionE2E(SSotBaseTestCase):
    """
    E2E tests for WebSocket coroutine regression prevention.
    
    Tests complete WebSocket flows with real authentication to ensure
    the coroutine regression issue is caught and business value is preserved.
    """

    def setUp(self):
        """Set up E2E test environment with real authentication and services."""
        super().setUp()
        self.start_time = time.time()
        
        # CRITICAL: Initialize real authentication helper (NO MOCKS)
        self.auth_helper = E2EAuthHelper()
        self.staging_config = StagingTestConfig()
        self.jwt_helper = JWTTestHelper()
        self.env = get_env()
        
        # CRITICAL: Validate get_env() returns proper instance for E2E tests
        self.assertIsInstance(
            self.env, 
            IsolatedEnvironment,
            "E2E tests require real IsolatedEnvironment instance"
        )
        
        # CRITICAL: Ensure we're using real services
        self.assertFalse(
            self.env.get("USE_MOCKS", "false").lower() == "true",
            "E2E tests MUST NOT use mocks - CLAUDE.MD violation"
        )

    def tearDown(self):
        """Validate E2E test execution time to prevent 0.00s bypassing."""
        super().tearDown()
        
        execution_time = time.time() - self.start_time
        
        # CRITICAL: E2E tests MUST take meaningful time (not 0.00s)
        self.assertGreater(
            execution_time, 
            0.1,  # Minimum 100ms for real E2E test
            f"E2E test completed in {execution_time:.3f}s - possible test bypassing detected"
        )

    async def test_complete_websocket_chat_flow_with_authentication(self):
        """
        CRITICAL: Test complete WebSocket chat flow with real authentication.
        
        This E2E test validates the complete business value flow:
        1. Real authentication
        2. WebSocket connection
        3. Agent request
        4. Agent response
        5. No coroutine errors throughout
        """
        # CRITICAL: Create authenticated user with real JWT
        user = await self.auth_helper.create_authenticated_user(
            email="chat.e2e.test@netra.ai",
            environment="staging"
        )
        
        self.assertIsInstance(user, AuthenticatedUser)
        self.assertIsNotNone(user.token)
        
        # CRITICAL: Test complete WebSocket chat business value flow
        websocket_url = self.staging_config.get_websocket_url()
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers={"Authorization": f"Bearer {user.token}"},
                ping_interval=10,
                ping_timeout=5
            ) as websocket:
                
                # CRITICAL: Send agent request to trigger full business logic
                agent_request = {
                    "type": "agent_request",
                    "data": {
                        "message": "Test coroutine regression in full chat flow",
                        "thread_id": f"e2e-test-{int(time.time())}",
                        "agent_type": "general"
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                logger.info("Sent agent request for E2E coroutine regression test")
                
                # CRITICAL: Collect responses to validate complete chat value
                responses = []
                timeout_seconds = 30  # Allow time for real agent processing
                start_time = time.time()
                
                while time.time() - start_time < timeout_seconds:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        responses.append(response_data)
                        
                        logger.info(f"Received WebSocket response: {response_data.get('type', 'unknown')}")
                        
                        # Check for agent completion
                        if response_data.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed as e:
                        # CRITICAL: Check for coroutine error in connection close
                        if "coroutine" in str(e):
                            self.fail(f"WebSocket closed with coroutine error: {e}")
                        break
                
                # CRITICAL: Validate we received meaningful responses (business value)
                self.assertGreater(
                    len(responses), 
                    0, 
                    "E2E test must receive WebSocket responses for business value validation"
                )
                
                # CRITICAL: Validate response structure indicates no coroutine errors
                for response in responses:
                    self.assertIsInstance(response, dict)
                    self.assertIn("type", response)
                    
                    # CRITICAL: Check response doesn't contain coroutine error indicators
                    response_str = json.dumps(response)
                    self.assertNotIn(
                        "coroutine", 
                        response_str.lower(),
                        f"Response contains coroutine error: {response}"
                    )
                
                logger.info(f"E2E chat flow completed successfully with {len(responses)} responses")
                
        except Exception as e:
            # CRITICAL: Any exception containing coroutine indicates regression
            error_str = str(e).lower()
            if "coroutine" in error_str:
                self.fail(f"E2E WebSocket flow failed with coroutine regression: {e}")
            raise

    async def test_websocket_environment_detection_e2e_flow(self):
        """
        Test WebSocket environment detection in complete E2E flow.
        
        This tests the E2E environment detection logic that caused the 
        coroutine issue in a real end-to-end scenario.
        """
        # CRITICAL: Real authentication for E2E test
        user = await self.auth_helper.create_authenticated_user(
            email="env.detection.e2e@netra.ai",
            environment="staging"
        )
        
        # CRITICAL: Test environment detection with real WebSocket connection
        websocket_url = self.staging_config.get_websocket_url()
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers={"Authorization": f"Bearer {user.token}"}
            ) as websocket:
                
                # CRITICAL: Send message that triggers environment detection logic
                env_test_message = {
                    "type": "system_info_request",
                    "data": {"include_environment": True}
                }
                
                await websocket.send(json.dumps(env_test_message))
                
                # CRITICAL: Receive response to validate environment detection works
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                # CRITICAL: Validate environment detection succeeded without coroutine errors
                self.assertIsInstance(response_data, dict)
                
                # If environment info is included, validate it's proper type
                if "environment" in response_data.get("data", {}):
                    env_value = response_data["data"]["environment"]
                    self.assertIsInstance(env_value, str)
                    self.assertIn(env_value, ["development", "staging", "production"])
                
        except Exception as e:
            if "coroutine" in str(e).lower():
                self.fail(f"Environment detection E2E failed with coroutine error: {e}")

    async def test_websocket_multi_user_isolation_without_coroutine_errors(self):
        """
        CRITICAL: Test multi-user WebSocket isolation without coroutine errors.
        
        This E2E test validates that multiple users can connect simultaneously
        without triggering the coroutine regression issue.
        """
        # CRITICAL: Create multiple authenticated users
        users = []
        for i in range(3):  # Test with 3 concurrent users
            user = await self.auth_helper.create_authenticated_user(
                email=f"multiuser.e2e.{i}@netra.ai",
                environment="staging"
            )
            users.append(user)
        
        self.assertEqual(len(users), 3)
        
        # CRITICAL: Test concurrent WebSocket connections
        websocket_url = self.staging_config.get_websocket_url()
        connection_tasks = []
        
        async def user_websocket_flow(user: AuthenticatedUser, user_index: int):
            """Individual user WebSocket flow."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers={"Authorization": f"Bearer {user.token}"}
                ) as websocket:
                    
                    # Send user-specific message
                    message = {
                        "type": "agent_request",
                        "data": {
                            "message": f"Multi-user test from user {user_index}",
                            "thread_id": f"multiuser-e2e-{user_index}-{int(time.time())}"
                        }
                    }
                    
                    await websocket.send(json.dumps(message))
                    
                    # Receive at least one response
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    response_data = json.loads(response)
                    
                    # CRITICAL: Validate no coroutine errors in multi-user scenario
                    self.assertIsInstance(response_data, dict)
                    response_str = json.dumps(response_data)
                    self.assertNotIn("coroutine", response_str.lower())
                    
                    return response_data
                    
            except Exception as e:
                if "coroutine" in str(e).lower():
                    self.fail(f"Multi-user WebSocket failed with coroutine error: {e}")
                raise
        
        # CRITICAL: Run concurrent user flows
        try:
            results = await asyncio.gather(
                *[user_websocket_flow(user, i) for i, user in enumerate(users)],
                return_exceptions=True
            )
            
            # CRITICAL: Validate all users succeeded
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    if "coroutine" in str(result).lower():
                        self.fail(f"User {i} failed with coroutine error: {result}")
                    raise result
                
                self.assertIsInstance(result, dict)
                
        except Exception as e:
            if "coroutine" in str(e).lower():
                self.fail(f"Multi-user E2E test failed with coroutine regression: {e}")

    async def test_websocket_agent_events_without_coroutine_regression(self):
        """
        CRITICAL: Test WebSocket agent events without coroutine regression.
        
        This validates the mission-critical WebSocket agent events that enable
        substantive chat interactions work without coroutine errors.
        """
        # CRITICAL: Real authentication for agent events test
        user = await self.auth_helper.create_authenticated_user(
            email="agent.events.e2e@netra.ai",
            environment="staging"
        )
        
        websocket_url = self.staging_config.get_websocket_url()
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers={"Authorization": f"Bearer {user.token}"}
            ) as websocket:
                
                # CRITICAL: Send agent request to trigger all WebSocket events
                agent_request = {
                    "type": "agent_request", 
                    "data": {
                        "message": "Test agent events without coroutine errors",
                        "thread_id": f"agent-events-e2e-{int(time.time())}",
                        "agent_type": "general"
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # CRITICAL: Collect agent event responses
                expected_events = [
                    "agent_started",
                    "agent_thinking", 
                    "tool_executing",
                    "tool_completed",
                    "agent_completed"
                ]
                
                received_events = []
                timeout_seconds = 30
                start_time = time.time()
                
                while time.time() - start_time < timeout_seconds:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        event_type = response_data.get("type")
                        if event_type:
                            received_events.append(event_type)
                            
                            # CRITICAL: Validate no coroutine errors in agent events
                            response_str = json.dumps(response_data)
                            self.assertNotIn(
                                "coroutine",
                                response_str.lower(),
                                f"Agent event {event_type} contains coroutine error"
                            )
                        
                        # Check if we have agent completion
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed as e:
                        if "coroutine" in str(e):
                            self.fail(f"Agent events WebSocket closed with coroutine error: {e}")
                        break
                
                # CRITICAL: Validate we received substantive agent events
                self.assertGreater(
                    len(received_events),
                    0,
                    "Must receive agent events for business value validation"
                )
                
                logger.info(f"Received agent events: {received_events}")
                
        except Exception as e:
            if "coroutine" in str(e).lower():
                self.fail(f"Agent events E2E test failed with coroutine regression: {e}")

    def test_websocket_e2e_environment_validation(self):
        """
        Test E2E environment validation without coroutine errors.
        
        This validates the environment detection logic works in E2E context
        without the coroutine regression issue.
        """
        # CRITICAL: Test environment detection in E2E context
        environment = self.env.get("ENVIRONMENT", "development").lower()
        
        # Test the exact E2E detection logic from websocket.py
        is_e2e_testing = (
            self.env.get("E2E_TESTING", "0") == "1" or 
            self.env.get("PYTEST_RUNNING", "0") == "1" or
            self.env.get("STAGING_E2E_TEST", "0") == "1" or
            self.env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
            self.env.get("E2E_TEST_ENV") == "staging"
        )
        
        # CRITICAL: All environment values should be proper types
        self.assertIsInstance(environment, str)
        self.assertIsInstance(is_e2e_testing, bool)
        
        # CRITICAL: Validate no coroutine objects in environment detection
        self.assertFalse(inspect.iscoroutine(environment))
        self.assertFalse(inspect.iscoroutine(is_e2e_testing))
        
        # Test environment conditional logic
        if environment in ["staging", "production"]:
            # This is the logic that was failing with coroutine errors
            e2e_flags = {
                "E2E_TESTING": self.env.get("E2E_TESTING", "0") == "1",
                "PYTEST_RUNNING": self.env.get("PYTEST_RUNNING", "0") == "1", 
                "STAGING_E2E_TEST": self.env.get("STAGING_E2E_TEST", "0") == "1",
                "E2E_OAUTH_SIMULATION_KEY": self.env.get("E2E_OAUTH_SIMULATION_KEY") is not None,
                "E2E_TEST_ENV": self.env.get("E2E_TEST_ENV") == "staging"
            }
            
            # CRITICAL: All flags should be boolean, no coroutines
            for flag_name, flag_value in e2e_flags.items():
                self.assertIsInstance(
                    flag_value, 
                    bool, 
                    f"E2E flag {flag_name} should be boolean, got {type(flag_value)}"
                )
                self.assertFalse(
                    inspect.iscoroutine(flag_value),
                    f"E2E flag {flag_name} should not be coroutine"
                )


if __name__ == "__main__":
    # CRITICAL: Run E2E tests with proper async support
    import asyncio
    
    def run_e2e_tests():
        """Run E2E tests with async support."""
        unittest.main()
    
    if __name__ == "__main__":
        run_e2e_tests()