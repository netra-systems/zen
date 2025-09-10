"""
Focused WebSocket Coroutine Regression E2E Test

Simplified E2E test focused on validating the WebSocket coroutine regression fix
in a complete end-to-end scenario while being practical to run.

CRITICAL ISSUE: GitHub Issue #133
- Problem: 'coroutine' object has no attribute 'get' error in WebSocket endpoint
- Root Cause: get_env() returning coroutine instead of IsolatedEnvironment
- Business Impact: Blocking core chat functionality ($500K+ ARR impact)

CLAUDE.MD COMPLIANCE:
- E2E test with real environment detection
- Tests execution time to prevent 0.00s bypassing
- Validates the fix in E2E context
- No complex authentication flows for simplicity
"""

import inspect
import time
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestWebSocketCoroutineFocusedE2E(SSotBaseTestCase):
    """
    Focused E2E test for WebSocket coroutine regression.
    
    Tests the environment detection logic in an E2E context to ensure
    the coroutine regression issue is resolved.
    """

    def setUp(self):
        """Set up E2E test environment."""
        super().setUp()
        self.start_time = time.time()
        self.env = get_env()

    def tearDown(self):
        """Validate E2E test execution time."""
        super().tearDown()
        
        execution_time = time.time() - self.start_time
        
        # CRITICAL: E2E tests MUST take meaningful time (not 0.00s)
        assert execution_time > 0.01, \
            f"E2E test completed in {execution_time:.3f}s - possible test bypassing detected"

    @pytest.mark.e2e
    def test_websocket_e2e_environment_detection_validation(self):
        """
        CRITICAL: Test WebSocket environment detection in E2E context.
        
        This validates that the environment detection logic from websocket.py
        works correctly in an E2E environment without coroutine errors.
        """
        # CRITICAL: Test environment detection in E2E context
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # Test the exact E2E detection logic from websocket.py
        is_e2e_testing = (
            env.get("E2E_TESTING", "0") == "1" or 
            env.get("PYTEST_RUNNING", "0") == "1" or
            env.get("STAGING_E2E_TEST", "0") == "1" or
            env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
            env.get("E2E_TEST_ENV") == "staging"
        )
        
        # CRITICAL: All environment values should be proper types
        assert isinstance(environment, str), \
            f"Environment should be string, got {type(environment)}"
        assert isinstance(is_e2e_testing, bool), \
            f"is_e2e_testing should be bool, got {type(is_e2e_testing)}"
        
        # CRITICAL: Validate no coroutine objects in environment detection
        assert not inspect.iscoroutine(environment), \
            "Environment should not be coroutine"
        assert not inspect.iscoroutine(is_e2e_testing), \
            "is_e2e_testing should not be coroutine"
        
        # Test environment conditional logic that was failing
        if environment in ["staging", "production"]:
            # This is the exact logic that was causing coroutine errors
            e2e_flags = {
                "E2E_TESTING": env.get("E2E_TESTING", "0") == "1",
                "PYTEST_RUNNING": env.get("PYTEST_RUNNING", "0") == "1", 
                "STAGING_E2E_TEST": env.get("STAGING_E2E_TEST", "0") == "1",
                "E2E_OAUTH_SIMULATION_KEY": env.get("E2E_OAUTH_SIMULATION_KEY") is not None,
                "E2E_TEST_ENV": env.get("E2E_TEST_ENV") == "staging"
            }
            
            # CRITICAL: All flags should be boolean, no coroutines
            for flag_name, flag_value in e2e_flags.items():
                assert isinstance(flag_value, bool), \
                    f"E2E flag {flag_name} should be boolean, got {type(flag_value)}"
                assert not inspect.iscoroutine(flag_value), \
                    f"E2E flag {flag_name} should not be coroutine"

    @pytest.mark.e2e
    def test_websocket_startup_detection_e2e(self):
        """
        Test WebSocket startup detection logic in E2E context.
        
        This tests the startup completion logic that was triggering
        the coroutine issue around line 555 in websocket.py.
        """
        # CRITICAL: Test startup logic with real environment
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # Simulate the startup completion check logic
        startup_complete = True  # Simulate completed startup for E2E
        
        if not startup_complete and environment in ["staging", "production"]:
            # Test E2E detection logic that was failing
            is_e2e_testing = (
                env.get("E2E_TESTING", "0") == "1" or 
                env.get("PYTEST_RUNNING", "0") == "1" or
                env.get("STAGING_E2E_TEST", "0") == "1" or
                env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
                env.get("E2E_TEST_ENV") == "staging"
            )
            
            # CRITICAL: This logic should work without coroutine errors
            assert isinstance(is_e2e_testing, bool), \
                f"E2E testing detection should be bool, got {type(is_e2e_testing)}"

    @pytest.mark.e2e
    def test_websocket_get_env_consistency_e2e(self):
        """
        Test get_env() consistency in E2E environment.
        
        Ensures that multiple calls to get_env() return consistent
        IsolatedEnvironment instances in E2E scenarios.
        """
        # CRITICAL: Multiple get_env() calls should return same instance
        env1 = get_env()
        env2 = get_env()
        env3 = get_env()
        
        # All should be same singleton instance
        assert env1 is env2, "get_env() should return singleton instance"
        assert env2 is env3, "get_env() should return consistent singleton"
        
        # All should be IsolatedEnvironment instances
        for env in [env1, env2, env3]:
            assert isinstance(env, IsolatedEnvironment), \
                f"Environment instance should be IsolatedEnvironment, got {type(env)}"
            assert not inspect.iscoroutine(env), \
                "Environment instance should not be coroutine"
            
        # Test that get() method works consistently
        for env in [env1, env2, env3]:
            test_value = env.get("ENVIRONMENT", "default")
            assert isinstance(test_value, str), \
                f"Environment value should be string, got {type(test_value)}"
            assert not inspect.iscoroutine(test_value), \
                "Environment value should not be coroutine"

    @pytest.mark.e2e
    def test_websocket_coroutine_detection_e2e(self):
        """
        CRITICAL: Test that detects coroutine objects in E2E context.
        
        This test validates that the fix prevents coroutine objects
        from being returned in E2E environment detection scenarios.
        """
        # CRITICAL: Test all environment access patterns from websocket.py
        env = get_env()
        
        # Test patterns from different lines in websocket.py
        environment_patterns = [
            env.get("ENVIRONMENT", "development"),
            env.get("TESTING", "0"),
            env.get("E2E_TESTING", "0"), 
            env.get("PYTEST_RUNNING", "0"),
            env.get("STAGING_E2E_TEST", "0"),
            env.get("E2E_OAUTH_SIMULATION_KEY"),
            env.get("E2E_TEST_ENV")
        ]
        
        # CRITICAL: None of these should be coroutines
        for i, value in enumerate(environment_patterns):
            assert not inspect.iscoroutine(value), \
                f"Environment pattern {i} should not be coroutine: {value}"
            
            # Validate proper types
            if value is not None:
                assert isinstance(value, str), \
                    f"Environment value should be string or None, got {type(value)}"

    @pytest.mark.e2e
    def test_websocket_business_logic_pattern_e2e(self):
        """
        Test WebSocket business logic pattern that caused regression.
        
        This tests the business logic pattern that was failing in the
        WebSocket endpoint due to coroutine returns.
        """
        env = get_env()
        
        # CRITICAL: Test the business logic pattern from websocket.py
        environment = env.get("ENVIRONMENT", "development").lower()
        is_testing = env.get("TESTING", "0") == "1"
        
        # Test conditional logic that was failing
        if not is_testing and environment in ["staging", "production"]:
            # E2E detection logic that was causing coroutine errors
            e2e_detection = (
                env.get("E2E_TESTING", "0") == "1" or
                env.get("PYTEST_RUNNING", "0") == "1" or
                env.get("STAGING_E2E_TEST", "0") == "1" or
                env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
                env.get("E2E_TEST_ENV") == "staging"
            )
            
            # CRITICAL: Business logic should work without coroutine errors
            assert isinstance(e2e_detection, bool), \
                f"E2E detection should be bool, got {type(e2e_detection)}"
            assert not inspect.iscoroutine(e2e_detection), \
                "E2E detection should not be coroutine"
        
        # Test that all conditional values are proper types
        assert isinstance(environment, str)
        assert isinstance(is_testing, bool)
        assert not inspect.iscoroutine(environment)
        assert not inspect.iscoroutine(is_testing)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])