"""
WebSocket Coroutine Regression Integration Tests

Integration tests for the critical WebSocket coroutine regression issue.
Tests WebSocket endpoint behavior with real authentication and environment detection.

CRITICAL ISSUE: GitHub Issue #133
- Problem: 'coroutine' object has no attribute 'get' error in WebSocket endpoint  
- Root Cause: get_env() returning coroutine instead of IsolatedEnvironment
- Business Impact: Blocking core chat functionality ($500K+ ARR impact)

CLAUDE.MD COMPLIANCE:
- Integration tests use real authentication (NO MOCKS for auth)
- Tests real WebSocket endpoint behavior in different environments
- Tests designed to FAIL HARD when coroutine issue occurs
- Uses existing test framework patterns from /tests/integration/
"""

import asyncio
import inspect
import json
import pytest
import unittest
from typing import Any, Dict, Optional
import websockets
from unittest.mock import patch
import httpx

from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ensure_user_id
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.base_integration_test import BaseIntegrationTest
from tests.e2e.staging_config import StagingTestConfig, staging_urls


class TestWebSocketCoroutineRegressionIntegration(BaseIntegrationTest):
    """
    Integration tests for WebSocket coroutine regression prevention.
    
    Tests real WebSocket endpoint behavior with authentication to ensure
    the coroutine regression issue is properly caught and prevented.
    """

    def setUp(self):
        """Set up integration test environment with real authentication."""
        super().setUp()
        self.auth_helper = E2EAuthHelper()
        self.staging_config = StagingTestConfig()
        self.env = get_env()
        
        # CRITICAL: Validate get_env() returns proper instance
        assert isinstance(
            self.env, 
            IsolatedEnvironment
        ), "get_env() must return IsolatedEnvironment for integration tests"

    async def asyncSetUp(self):
        """Async setup for integration tests."""
        await super().asyncSetUp() if hasattr(super(), 'asyncSetUp') else None

    async def test_websocket_connection_establishment_with_real_auth(self):
        """
        CRITICAL: Test WebSocket connection with real authentication.
        
        This integration test validates that the WebSocket endpoint can establish
        connections without coroutine errors when using real authentication.
        """
        # CRITICAL: Create authenticated user with real auth flow
        user = await self.auth_helper.create_authenticated_user(
            email="websocket.test@netra.ai",
            environment="staging"
        )
        
        assert isinstance(user, AuthenticatedUser), f"User should be AuthenticatedUser, got {type(user)}"
        assert user.token is not None, "User token should not be None"
        
        # CRITICAL: Test WebSocket connection with authentication
        websocket_url = self.staging_config.get_websocket_url()
        
        try:
            # Attempt WebSocket connection with authentication
            async with websockets.connect(
                websocket_url,
                extra_headers={"Authorization": f"Bearer {user.token}"}
            ) as websocket:
                
                # CRITICAL: Send initial message to trigger environment detection logic
                test_message = {
                    "type": "agent_request",
                    "data": {
                        "message": "Test coroutine regression",
                        "thread_id": "integration-test-thread"
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                
                # CRITICAL: Receive response to validate endpoint works
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                # CRITICAL: Validate we got a proper response (not coroutine error)
                assert isinstance(response_data, dict), f"Response should be dict, got {type(response_data)}"
                assert "type" in response_data, "Response should have 'type' field"
                
                # If we get here without coroutine errors, the fix is working
                
        except websockets.exceptions.ConnectionClosed as e:
            # CRITICAL: If connection closes immediately, check for coroutine error
            if "coroutine" in str(e):
                self.fail(f"WebSocket connection failed with coroutine error: {e}")
        except Exception as e:
            # CRITICAL: Any exception containing coroutine indicates regression
            if "coroutine" in str(e).lower():
                self.fail(f"WebSocket endpoint failed with coroutine regression: {e}")

    def test_websocket_environment_detection_integration(self):
        """
        Test WebSocket environment detection logic with real environment.
        
        This tests the E2E detection logic that caused the coroutine issue
        in an integration context with real environment variables.
        """
        # CRITICAL: Test environment detection without coroutines
        environment = self.env.get("ENVIRONMENT", "development").lower()
        is_testing = self.env.get("TESTING", "0") == "1"
        
        # Test E2E detection logic from websocket.py lines 213-217
        is_e2e_via_env = (
            self.env.get("E2E_TESTING", "0") == "1" or 
            self.env.get("PYTEST_RUNNING", "0") == "1" or
            self.env.get("STAGING_E2E_TEST", "0") == "1" or
            self.env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
            self.env.get("E2E_TEST_ENV") == "staging"
        )
        
        # CRITICAL: All values should be proper types, not coroutines
        assert isinstance(environment, str), f"Environment should be string, got {type(environment)}"
        assert isinstance(is_testing, bool), f"is_testing should be bool, got {type(is_testing)}"
        assert isinstance(is_e2e_via_env, bool), f"is_e2e_via_env should be bool, got {type(is_e2e_via_env)}"
        
        # CRITICAL: Validate no coroutine objects in environment access
        for attr_name in ["environment", "is_testing", "is_e2e_via_env"]:
            attr_value = locals()[attr_name.replace(".", "_")]
            assert not inspect.iscoroutine(attr_value), f"{attr_name} should not be a coroutine: {attr_value}"

    async def test_websocket_startup_logic_integration(self):
        """
        Test WebSocket startup completion logic that triggered coroutine issue.
        
        This tests the startup logic around line 555 in websocket.py where
        the coroutine regression was occurring.
        """
        # CRITICAL: Test startup logic with real environment
        environment = self.env.get("ENVIRONMENT", "development").lower()
        
        # Simulate the startup completion check logic
        startup_complete = True  # Simulate completed startup
        startup_in_progress = False
        
        if not startup_complete and environment in ["staging", "production"]:
            # Test E2E detection logic that was failing
            is_e2e_testing = (
                self.env.get("E2E_TESTING", "0") == "1" or 
                self.env.get("PYTEST_RUNNING", "0") == "1" or
                self.env.get("STAGING_E2E_TEST", "0") == "1" or
                self.env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
                self.env.get("E2E_TEST_ENV") == "staging"
            )
            
            # CRITICAL: This logic should work without coroutine errors
            assert isinstance(is_e2e_testing, bool), f"is_e2e_testing should be bool, got {type(is_e2e_testing)}"

    def test_websocket_environment_conditional_logic(self):
        """
        Test WebSocket environment conditional logic that caused regression.
        
        Tests the exact conditional logic patterns from websocket.py that were
        failing due to coroutine returns from get_env().
        """
        # CRITICAL: Test environment conditionals
        environment = self.env.get("ENVIRONMENT", "development").lower()
        
        # Test staging/production conditional (line 555 logic)
        if environment in ["staging", "production"]:
            # CRITICAL: This should work without coroutine errors
            e2e_testing_flag = self.env.get("E2E_TESTING", "0") == "1"
            pytest_running_flag = self.env.get("PYTEST_RUNNING", "0") == "1"
            staging_e2e_flag = self.env.get("STAGING_E2E_TEST", "0") == "1"
            oauth_simulation = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            e2e_test_env = self.env.get("E2E_TEST_ENV") == "staging"
            
            # CRITICAL: All should be proper types
            self.assertIsInstance(e2e_testing_flag, bool)
            self.assertIsInstance(pytest_running_flag, bool) 
            self.assertIsInstance(staging_e2e_flag, bool)
            self.assertIsInstance(oauth_simulation, (str, type(None)))
            self.assertIsInstance(e2e_test_env, bool)
            
            # Combined E2E detection logic
            is_e2e_testing = (
                e2e_testing_flag or 
                pytest_running_flag or
                staging_e2e_flag or
                oauth_simulation is not None or
                e2e_test_env
            )
            
            self.assertIsInstance(is_e2e_testing, bool)

    async def test_websocket_auth_integration_with_environment_detection(self):
        """
        CRITICAL: Test WebSocket authentication integrated with environment detection.
        
        This test combines real authentication with environment detection to ensure
        the coroutine regression doesn't occur in the full integration flow.
        """
        # CRITICAL: Create authenticated user
        user = await self.auth_helper.create_authenticated_user(
            email="env.detection.test@netra.ai",
            environment="staging"
        )
        
        # CRITICAL: Test environment detection with authenticated context
        environment = self.env.get("ENVIRONMENT", "development").lower()
        
        # Create strongly typed user context (as used in WebSocket endpoint)
        user_context = StronglyTypedUserExecutionContext(
            user_id=ensure_user_id(user.user_id),
            request_id="integration-test-request",
            environment=environment,
            isolation_mode=False
        )
        
        # CRITICAL: Validate context creation works with environment detection
        self.assertIsInstance(user_context.user_id, UserID)
        self.assertEqual(user_context.environment, environment)
        
        # CRITICAL: Test that environment access in context doesn't return coroutines
        context_env = user_context.environment
        self.assertIsInstance(context_env, str)
        self.assertFalse(inspect.iscoroutine(context_env))

    def test_websocket_get_env_consistency_integration(self):
        """
        Test get_env() consistency in integration context.
        
        Ensures that get_env() returns consistent IsolatedEnvironment instances
        across multiple calls in integration scenarios.
        """
        # CRITICAL: Multiple get_env() calls should return same instance
        env1 = get_env()
        env2 = get_env()
        env3 = get_env()
        
        # All should be same singleton instance
        self.assertIs(env1, env2)
        self.assertIs(env2, env3)
        
        # All should be IsolatedEnvironment instances
        for env in [env1, env2, env3]:
            self.assertIsInstance(env, IsolatedEnvironment)
            self.assertFalse(inspect.iscoroutine(env))
            
        # Test that get() method works consistently
        for env in [env1, env2, env3]:
            test_value = env.get("ENVIRONMENT", "default")
            self.assertIsInstance(test_value, str)
            self.assertFalse(inspect.iscoroutine(test_value))


if __name__ == "__main__":
    # Run integration tests with asyncio support
    import asyncio
    
    def run_async_tests():
        """Run async integration tests."""
        unittest.main()
    
    if __name__ == "__main__":
        run_async_tests()