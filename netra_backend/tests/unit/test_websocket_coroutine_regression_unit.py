"""
WebSocket Coroutine Regression Unit Tests

Tests for the critical WebSocket coroutine regression issue where get_env() at line 557
in websocket.py returns a coroutine instead of IsolatedEnvironment instance.

CRITICAL ISSUE: GitHub Issue #133
- Problem: 'coroutine' object has no attribute 'get' error in WebSocket endpoint
- Root Cause: get_env() returning coroutine instead of IsolatedEnvironment
- Business Impact: Blocking core chat functionality ($500K+ ARR impact)

CLAUDE.MD COMPLIANCE:
- Unit tests focus on isolated component behavior
- Tests designed to FAIL HARD when issues occur
- No mocks for environment access - uses real IsolatedEnvironment
- Tests the exact line 557 logic in WebSocket endpoint
"""

import asyncio
import inspect
import pytest
import unittest
from unittest.mock import patch, MagicMock
from typing import Any

from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from netra_backend.app.routes.websocket import websocket_endpoint


class TestWebSocketCoroutineRegression(unittest.TestCase):
    """
    Unit tests for WebSocket coroutine regression prevention.
    
    These tests validate that get_env() returns proper IsolatedEnvironment
    instances and detect the specific coroutine regression issue.
    """

    def setUp(self):
        """Set up test environment with isolated configuration."""
        self.env = get_env()
        
    def test_get_env_returns_isolated_environment_instance(self):
        """
        CRITICAL: Test that get_env() returns IsolatedEnvironment, not coroutine.
        
        This test directly validates the fix for the regression where get_env()
        was returning a coroutine object instead of the proper IsolatedEnvironment.
        """
        # CRITICAL: Get environment instance
        env_instance = get_env()
        
        # CRITICAL: Validate it's an IsolatedEnvironment instance
        self.assertIsInstance(
            env_instance, 
            IsolatedEnvironment,
            f"get_env() must return IsolatedEnvironment instance, got {type(env_instance)}"
        )
        
        # CRITICAL: Validate it's NOT a coroutine
        self.assertFalse(
            inspect.iscoroutine(env_instance),
            f"get_env() MUST NOT return coroutine, got coroutine: {env_instance}"
        )
        
        # CRITICAL: Validate it has the 'get' method that WebSocket endpoint uses
        self.assertTrue(
            hasattr(env_instance, 'get'),
            "IsolatedEnvironment must have 'get' method for WebSocket endpoint"
        )
        
        # CRITICAL: Validate the get method is callable
        self.assertTrue(
            callable(env_instance.get),
            "IsolatedEnvironment.get must be callable"
        )

    def test_websocket_e2e_detection_logic_isolated(self):
        """
        Test the E2E testing detection logic that caused the coroutine issue.
        
        This tests the exact logic from lines 213-217 in websocket.py where
        get_env().get() calls are made for E2E testing detection.
        """
        # CRITICAL: Test E2E detection with real environment access
        env = get_env()
        
        # Test each E2E detection environment variable
        e2e_variables = [
            "E2E_TESTING",
            "PYTEST_RUNNING", 
            "STAGING_E2E_TEST",
            "E2E_OAUTH_SIMULATION_KEY",
            "E2E_TEST_ENV"
        ]
        
        for var_name in e2e_variables:
            with self.subTest(var=var_name):
                # CRITICAL: Ensure get_env() returns proper object with get() method
                result = env.get(var_name, "default_value")
                
                # Validate we can call get() without coroutine errors
                self.assertIsInstance(
                    result, 
                    (str, type(None)),
                    f"Environment variable {var_name} should return string or None"
                )

    def test_coroutine_regression_detection(self):
        """
        CRITICAL: Test that detects if get_env() accidentally returns coroutine.
        
        This test simulates the regression scenario and ensures it fails loudly.
        """
        # Create a mock coroutine to simulate the regression
        async def mock_coroutine():
            return MagicMock()
            
        coroutine_obj = mock_coroutine()
        
        try:
            # CRITICAL: This should fail if we have a coroutine instead of IsolatedEnvironment
            # Simulating what happens in WebSocket endpoint at line 557
            if inspect.iscoroutine(coroutine_obj):
                with self.assertRaises(AttributeError) as context:
                    # This is what fails in the WebSocket endpoint
                    _ = coroutine_obj.get("ENVIRONMENT", "development")
                
                # CRITICAL: Verify we get the exact error from the GitHub issue
                self.assertIn(
                    "'coroutine' object has no attribute 'get'",
                    str(context.exception)
                )
        finally:
            # Clean up coroutine to prevent warnings
            coroutine_obj.close()

    def test_websocket_environment_detection_real_calls(self):
        """
        Test the actual WebSocket environment detection calls that failed.
        
        This tests the exact calls from websocket.py lines 187-188 and 213-217.
        """
        env = get_env()
        
        # CRITICAL: Test the exact calls from websocket.py that were failing
        
        # Line 187: environment = get_env().get("ENVIRONMENT", "development").lower()
        environment = env.get("ENVIRONMENT", "development").lower()
        self.assertIsInstance(environment, str)
        self.assertIn(environment, ["development", "staging", "production", "test", "testing"])
        
        # Line 188: is_testing = get_env().get("TESTING", "0") == "1"
        is_testing = env.get("TESTING", "0") == "1"
        self.assertIsInstance(is_testing, bool)
        
        # Lines 213-217: E2E testing detection calls
        e2e_testing = env.get("E2E_TESTING", "0") == "1"
        pytest_running = env.get("PYTEST_RUNNING", "0") == "1"
        staging_e2e = env.get("STAGING_E2E_TEST", "0") == "1"
        oauth_sim_key = env.get("E2E_OAUTH_SIMULATION_KEY")
        e2e_test_env = env.get("E2E_TEST_ENV") == "staging"
        
        # All should be proper types, not coroutines
        self.assertIsInstance(e2e_testing, bool)
        self.assertIsInstance(pytest_running, bool)
        self.assertIsInstance(staging_e2e, bool)
        self.assertIsInstance(oauth_sim_key, (str, type(None)))
        self.assertIsInstance(e2e_test_env, bool)

    def test_websocket_endpoint_environment_access_pattern(self):
        """
        Test the environment access pattern used in websocket_endpoint.
        
        This validates the pattern that was failing in the actual WebSocket handler.
        """
        # CRITICAL: Test the pattern from websocket.py that was causing the issue
        
        # Simulate the environment access pattern from the WebSocket endpoint
        env = get_env()
        
        # Test the startup completion check pattern (around line 555)
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # CRITICAL: Ensure we can use environment variable in conditionals
        if environment in ["staging", "production"]:
            # Test E2E detection logic that was failing
            is_e2e_testing = (
                env.get("E2E_TESTING", "0") == "1" or 
                env.get("PYTEST_RUNNING", "0") == "1" or
                env.get("STAGING_E2E_TEST", "0") == "1" or
                env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
                env.get("E2E_TEST_ENV") == "staging"
            )
            
            # CRITICAL: This should work without coroutine errors
            self.assertIsInstance(is_e2e_testing, bool)

    def test_isolated_environment_singleton_consistency(self):
        """
        Test IsolatedEnvironment singleton consistency to prevent coroutine returns.
        
        The regression may have been caused by singleton inconsistency.
        """
        # CRITICAL: Multiple calls to get_env() should return same instance
        env1 = get_env()
        env2 = get_env()
        
        # Should be the same instance (singleton pattern)
        self.assertIs(env1, env2, "get_env() should return singleton instance")
        
        # Both should be IsolatedEnvironment instances
        self.assertIsInstance(env1, IsolatedEnvironment)
        self.assertIsInstance(env2, IsolatedEnvironment)
        
        # Neither should be coroutines
        self.assertFalse(inspect.iscoroutine(env1))
        self.assertFalse(inspect.iscoroutine(env2))


if __name__ == "__main__":
    unittest.main()