"""
Focused WebSocket Coroutine Regression Integration Test

Simplified integration test focused specifically on the coroutine regression issue.
Tests the core WebSocket environment detection logic without complex authentication flows.

CRITICAL ISSUE: GitHub Issue #133
- Problem: 'coroutine' object has no attribute 'get' error in WebSocket endpoint
- Root Cause: get_env() returning coroutine instead of IsolatedEnvironment
- Business Impact: Blocking core chat functionality ($500K+ ARR impact)

CLAUDE.MD COMPLIANCE:
- Integration test with minimal dependencies
- Tests real environment detection logic
- No mocks for environment access
- Focuses on coroutine regression detection
"""

import inspect
import pytest
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestWebSocketCoroutineFocused(BaseIntegrationTest):
    """
    Focused integration test for WebSocket coroutine regression.
    
    Tests the core environment detection logic that was causing
    the 'coroutine' object has no attribute 'get' error.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.env = get_env()

    @pytest.mark.integration
    def test_websocket_get_env_returns_isolated_environment(self):
        """
        CRITICAL: Test that get_env() returns IsolatedEnvironment, not coroutine.
        
        This is the core test for the regression where get_env() was returning
        a coroutine object instead of the proper IsolatedEnvironment instance.
        """
        # CRITICAL: Test get_env() function behavior
        env_instance = get_env()
        
        # CRITICAL: Validate it's an IsolatedEnvironment instance
        assert isinstance(env_instance, IsolatedEnvironment), \
            f"get_env() must return IsolatedEnvironment, got {type(env_instance)}"
        
        # CRITICAL: Validate it's NOT a coroutine
        assert not inspect.iscoroutine(env_instance), \
            f"get_env() MUST NOT return coroutine, got: {env_instance}"
        
        # CRITICAL: Validate it has the required methods
        assert hasattr(env_instance, 'get'), \
            "IsolatedEnvironment must have 'get' method"
        assert callable(env_instance.get), \
            "IsolatedEnvironment.get must be callable"

    @pytest.mark.integration
    def test_websocket_environment_detection_calls(self):
        """
        Test the exact environment detection calls that were failing.
        
        This tests the specific calls from websocket.py that were causing
        the coroutine regression issue.
        """
        env = get_env()
        
        # CRITICAL: Test the exact calls from websocket.py lines 187-188
        environment = env.get("ENVIRONMENT", "development").lower()
        is_testing = env.get("TESTING", "0") == "1"
        
        # CRITICAL: Validate proper types, not coroutines
        assert isinstance(environment, str), \
            f"Environment should be string, got {type(environment)}"
        assert isinstance(is_testing, bool), \
            f"is_testing should be bool, got {type(is_testing)}"
        
        # CRITICAL: Test E2E detection calls (lines 213-217)
        e2e_testing = env.get("E2E_TESTING", "0") == "1"
        pytest_running = env.get("PYTEST_RUNNING", "0") == "1"
        staging_e2e = env.get("STAGING_E2E_TEST", "0") == "1"
        oauth_simulation = env.get("E2E_OAUTH_SIMULATION_KEY")
        e2e_test_env = env.get("E2E_TEST_ENV") == "staging"
        
        # CRITICAL: All should be proper types, not coroutines
        assert isinstance(e2e_testing, bool)
        assert isinstance(pytest_running, bool)
        assert isinstance(staging_e2e, bool)
        assert isinstance(oauth_simulation, (str, type(None)))
        assert isinstance(e2e_test_env, bool)
        
        # CRITICAL: None should be coroutines
        for value in [environment, is_testing, e2e_testing, pytest_running, 
                     staging_e2e, oauth_simulation, e2e_test_env]:
            assert not inspect.iscoroutine(value), \
                f"Value should not be coroutine: {value}"

    @pytest.mark.integration
    def test_websocket_conditional_logic_pattern(self):
        """
        Test the conditional logic pattern that was causing the regression.
        
        This tests the exact pattern from websocket.py around line 555 that
        was failing due to coroutine returns.
        """
        env = get_env()
        
        # CRITICAL: Test the staging/production conditional logic
        environment = env.get("ENVIRONMENT", "development").lower()
        
        if environment in ["staging", "production"]:
            # This is the exact logic that was failing
            is_e2e_testing = (
                env.get("E2E_TESTING", "0") == "1" or 
                env.get("PYTEST_RUNNING", "0") == "1" or
                env.get("STAGING_E2E_TEST", "0") == "1" or
                env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
                env.get("E2E_TEST_ENV") == "staging"
            )
            
            # CRITICAL: This should work without coroutine errors
            assert isinstance(is_e2e_testing, bool), \
                f"E2E testing flag should be bool, got {type(is_e2e_testing)}"
            assert not inspect.iscoroutine(is_e2e_testing), \
                "E2E testing flag should not be coroutine"

    @pytest.mark.integration  
    def test_websocket_singleton_consistency(self):
        """
        Test that get_env() singleton is consistent.
        
        The regression may have been caused by singleton inconsistency
        leading to coroutine returns.
        """
        # CRITICAL: Multiple calls should return same instance
        env1 = get_env()
        env2 = get_env()
        env3 = get_env()
        
        # Should be the same singleton instance
        assert env1 is env2, "get_env() should return singleton instance"
        assert env2 is env3, "get_env() should return consistent singleton"
        
        # All should be IsolatedEnvironment instances
        for env in [env1, env2, env3]:
            assert isinstance(env, IsolatedEnvironment)
            assert not inspect.iscoroutine(env)
            
        # Test that get() method works consistently
        for env in [env1, env2, env3]:
            test_value = env.get("ENVIRONMENT", "default")
            assert isinstance(test_value, str)
            assert not inspect.iscoroutine(test_value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])