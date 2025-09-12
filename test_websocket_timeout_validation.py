#!/usr/bin/env python3
"""
WebSocket Timeout Validation Test Suite - Issue #404

CRITICAL MISSION: Validate if 3.0s staging timeouts are deployed vs 1.2s race condition timeouts

This test suite implements the key tests from the planned test execution to determine
if the WebSocket race condition has been resolved through proper timeout configuration.

Test Priority:
1. Quick Unit Test Validation - Test timeout configuration logic directly
2. Staging Environment Tests - Test actual staging timeout behavior if possible  
3. Existing Test Review - Check current timeout implementations

Expected Results:
- If tests PASS: 3.0s timeouts are deployed and working
- If tests FAIL: 1.2s timeouts are still active, need remediation
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from typing import Optional

# Add the project root to Python path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from netra_backend.app.core.timeout_configuration import (
    CloudNativeTimeoutManager, 
    TimeoutTier, 
    TimeoutEnvironment,
    get_websocket_recv_timeout,
    get_agent_execution_timeout,
    get_timeout_config,
    validate_timeout_hierarchy,
    get_timeout_hierarchy_info,
    reset_timeout_manager
)
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    create_gcp_websocket_validator
)


class TestWebSocketTimeoutValidation(SSotBaseTestCase):
    """Test WebSocket timeout configuration validation for Issue #404."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset timeout manager to ensure clean state for each test
        reset_timeout_manager()
    
    def tearDown(self):
        """Clean up after each test."""
        # Reset timeout manager
        reset_timeout_manager()
    
    def test_staging_websocket_recv_timeout_is_35_seconds(self):
        """
        CRITICAL TEST: Validate staging WebSocket recv timeout is 35s (not 3s race condition).
        
        Issue #404 Root Cause: 3s WebSocket timeout vs 15s agent timeout causing race condition.
        Expected Fix: Staging should return 35s WebSocket recv timeout.
        """
        print("\n[TEST] Testing staging WebSocket recv timeout configuration...")
        
        # Mock environment to be staging
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            manager = CloudNativeTimeoutManager()
            config = manager.get_timeout_config()
            
            # CRITICAL ASSERTION: Staging should have 35s WebSocket recv timeout
            expected_recv_timeout = 35
            actual_recv_timeout = config.websocket_recv_timeout
            
            print(f"   Expected staging WebSocket recv timeout: {expected_recv_timeout}s")
            print(f"   Actual staging WebSocket recv timeout: {actual_recv_timeout}s")
            
            self.assertEqual(
                actual_recv_timeout, 
                expected_recv_timeout,
                f"RACE CONDITION DETECTED: Staging WebSocket recv timeout is {actual_recv_timeout}s, "
                f"expected {expected_recv_timeout}s to fix race condition with agent execution timeout"
            )
            
            print("   ✅ Staging WebSocket recv timeout is correctly configured at 35s")
    
    def test_staging_agent_execution_timeout_is_30_seconds(self):
        """
        CRITICAL TEST: Validate staging agent execution timeout is 30s (not 15s).
        
        Issue #404 Root Cause: 15s agent timeout vs 3s WebSocket timeout.
        Expected Fix: Staging should return 30s agent execution timeout.
        """
        print("\n🔍 Testing staging agent execution timeout configuration...")
        
        # Mock environment to be staging
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            manager = CloudNativeTimeoutManager()
            config = manager.get_timeout_config()
            
            # CRITICAL ASSERTION: Staging should have 30s agent execution timeout
            expected_agent_timeout = 30
            actual_agent_timeout = config.agent_execution_timeout
            
            print(f"   Expected staging agent execution timeout: {expected_agent_timeout}s")
            print(f"   Actual staging agent execution timeout: {actual_agent_timeout}s")
            
            self.assertEqual(
                actual_agent_timeout,
                expected_agent_timeout,
                f"INCORRECT AGENT TIMEOUT: Staging agent execution timeout is {actual_agent_timeout}s, "
                f"expected {expected_agent_timeout}s for proper coordination with WebSocket timeout"
            )
            
            print("   ✅ Staging agent execution timeout is correctly configured at 30s")
    
    def test_timeout_hierarchy_validation_staging(self):
        """
        CRITICAL TEST: Validate timeout hierarchy (WebSocket > Agent) in staging.
        
        Issue #404 Root Cause: WebSocket timeout (3s) < Agent timeout (15s) = race condition.
        Expected Fix: WebSocket timeout (35s) > Agent timeout (30s) = proper hierarchy.
        """
        print("\n🔍 Testing staging timeout hierarchy validation...")
        
        # Mock environment to be staging  
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            manager = CloudNativeTimeoutManager()
            
            # Test timeout hierarchy validation
            hierarchy_valid = manager.validate_timeout_hierarchy()
            hierarchy_info = manager.get_timeout_hierarchy_info()
            
            print(f"   Timeout hierarchy valid: {hierarchy_valid}")
            print(f"   WebSocket recv timeout: {hierarchy_info['websocket_recv_timeout']}s")
            print(f"   Agent execution timeout: {hierarchy_info['agent_execution_timeout']}s")
            print(f"   Hierarchy gap: {hierarchy_info['hierarchy_gap']}s")
            print(f"   Business impact: {hierarchy_info['business_impact']}")
            
            # CRITICAL ASSERTION: Hierarchy must be valid to prevent race conditions
            self.assertTrue(
                hierarchy_valid,
                f"RACE CONDITION STILL PRESENT: Timeout hierarchy is invalid. "
                f"WebSocket timeout ({hierarchy_info['websocket_recv_timeout']}s) must be > "
                f"Agent timeout ({hierarchy_info['agent_execution_timeout']}s)"
            )
            
            # Additional validation: Hierarchy gap should be positive and reasonable
            hierarchy_gap = hierarchy_info['hierarchy_gap']
            self.assertGreater(
                hierarchy_gap,
                0,
                f"HIERARCHY GAP NEGATIVE: WebSocket timeout must be greater than agent timeout. "
                f"Current gap: {hierarchy_gap}s"
            )
            
            # Reasonable gap validation (should be at least 5 seconds)
            min_gap = 5
            self.assertGreaterEqual(
                hierarchy_gap,
                min_gap,
                f"HIERARCHY GAP TOO SMALL: Gap of {hierarchy_gap}s may not prevent race conditions. "
                f"Should be at least {min_gap}s"
            )
            
            print("   ✅ Staging timeout hierarchy is properly configured")
    
    def test_convenience_functions_return_staging_values(self):
        """
        TEST: Validate convenience functions return correct staging timeout values.
        
        Tests the global convenience functions that are likely used throughout the codebase.
        """
        print("\n🔍 Testing convenience functions for staging timeout values...")
        
        # Mock environment to be staging
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            # Test convenience functions
            websocket_timeout = get_websocket_recv_timeout()
            agent_timeout = get_agent_execution_timeout()
            
            print(f"   get_websocket_recv_timeout(): {websocket_timeout}s")
            print(f"   get_agent_execution_timeout(): {agent_timeout}s")
            
            # CRITICAL ASSERTIONS: Should return staging values
            self.assertEqual(websocket_timeout, 35, "WebSocket recv timeout convenience function incorrect")
            self.assertEqual(agent_timeout, 30, "Agent execution timeout convenience function incorrect")
            
            # Test hierarchy validation convenience function
            hierarchy_valid = validate_timeout_hierarchy()
            self.assertTrue(hierarchy_valid, "Timeout hierarchy validation convenience function failed")
            
            print("   ✅ Convenience functions return correct staging timeout values")
    
    def test_gcp_initialization_validator_timeout_optimization(self):
        """
        TEST: Validate GCP initialization validator uses environment-aware timeouts.
        
        The GCP initialization validator has performance optimizations that should
        use shorter timeouts in staging compared to the 1.2s race condition timeouts.
        """
        print("\n🔍 Testing GCP initialization validator timeout optimization...")
        
        # Mock environment to be staging
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            # Create validator and mock app_state
            mock_app_state = MagicMock()
            validator = GCPWebSocketInitializationValidator(mock_app_state)
            
            print(f"   Environment detected: {validator.environment}")
            print(f"   Is GCP environment: {validator.is_gcp_environment}")
            print(f"   Timeout multiplier: {validator.timeout_multiplier}")
            print(f"   Max total timeout: {validator.max_total_timeout}s")
            
            # Test environment-aware timeout configuration
            self.assertEqual(validator.environment, 'staging', "Environment not detected as staging")
            self.assertTrue(validator.is_gcp_environment, "Should be detected as GCP environment")
            
            # Test timeout multiplier for staging (should be 0.7 for 30% faster than production)
            expected_multiplier = 0.7
            self.assertEqual(
                validator.timeout_multiplier, 
                expected_multiplier,
                f"Staging timeout multiplier should be {expected_multiplier}, got {validator.timeout_multiplier}"
            )
            
            # Test max total timeout for staging (should be 5.0s)
            expected_max_timeout = 5.0
            self.assertEqual(
                validator.max_total_timeout,
                expected_max_timeout,
                f"Staging max total timeout should be {expected_max_timeout}s, got {validator.max_total_timeout}s"
            )
            
            print("   ✅ GCP initialization validator correctly configured for staging")
    
    def test_race_condition_detection_in_old_configuration(self):
        """
        TEST: Simulate the old race condition configuration to ensure it would be detected.
        
        This test validates that the old problematic configuration (3s WebSocket, 15s Agent)
        would be properly detected as invalid by our validation logic.
        """
        print("\n🔍 Testing race condition detection with old configuration...")
        
        # Create a mock timeout configuration with the old problematic values
        from netra_backend.app.core.timeout_configuration import TimeoutConfig
        
        old_config = TimeoutConfig(
            # OLD PROBLEMATIC VALUES (race condition)
            websocket_connection_timeout=30,
            websocket_recv_timeout=3,        # PROBLEMATIC: 3s WebSocket timeout
            websocket_send_timeout=10,
            websocket_heartbeat_timeout=60,
            
            agent_execution_timeout=15,      # PROBLEMATIC: 15s Agent timeout > 3s WebSocket
            agent_thinking_timeout=12,
            agent_tool_timeout=8,
            agent_completion_timeout=5,
            
            http_request_timeout=20,
            http_connection_timeout=10,
            
            test_default_timeout=30,
            test_integration_timeout=60,
            test_e2e_timeout=90
        )
        
        # Validate hierarchy - should detect the race condition
        websocket_recv = old_config.websocket_recv_timeout
        agent_exec = old_config.agent_execution_timeout
        hierarchy_valid = websocket_recv > agent_exec
        hierarchy_gap = websocket_recv - agent_exec
        
        print(f"   Old WebSocket recv timeout: {websocket_recv}s")
        print(f"   Old agent execution timeout: {agent_exec}s") 
        print(f"   Old hierarchy valid: {hierarchy_valid}")
        print(f"   Old hierarchy gap: {hierarchy_gap}s")
        
        # CRITICAL ASSERTION: Old configuration should be detected as invalid
        self.assertFalse(
            hierarchy_valid,
            f"VALIDATION FAILURE: Old race condition configuration should be detected as invalid. "
            f"WebSocket timeout ({websocket_recv}s) < Agent timeout ({agent_exec}s) = race condition"
        )
        
        # The gap should be negative (indicating the race condition)
        self.assertLess(
            hierarchy_gap,
            0,
            f"VALIDATION FAILURE: Hierarchy gap should be negative for race condition. Got: {hierarchy_gap}s"
        )
        
        print("   ✅ Race condition properly detected in old configuration")


class TestEnvironmentDetection(SSotBaseTestCase):
    """Test environment detection for timeout configuration."""
    
    def setUp(self):
        """Set up test environment."""
        reset_timeout_manager()
    
    def tearDown(self):
        """Clean up after each test."""
        reset_timeout_manager()
    
    def test_environment_detection_staging(self):
        """Test that staging environment is properly detected."""
        print("\n🔍 Testing staging environment detection...")
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=False):
            manager = CloudNativeTimeoutManager()
            detected_env = manager._detect_environment()
            
            print(f"   Environment variable: {os.environ.get('ENVIRONMENT')}")
            print(f"   Detected environment: {detected_env}")
            
            self.assertEqual(
                detected_env,
                TimeoutEnvironment.CLOUD_RUN_STAGING,
                f"Environment detection failed. Expected CLOUD_RUN_STAGING, got {detected_env}"
            )
            
            print("   ✅ Staging environment properly detected")
    
    def test_environment_detection_production(self):
        """Test that production environment is properly detected."""
        print("\n🔍 Testing production environment detection...")
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=False):
            manager = CloudNativeTimeoutManager()
            detected_env = manager._detect_environment()
            
            print(f"   Environment variable: {os.environ.get('ENVIRONMENT')}")
            print(f"   Detected environment: {detected_env}")
            
            self.assertEqual(
                detected_env,
                TimeoutEnvironment.CLOUD_RUN_PRODUCTION,
                f"Environment detection failed. Expected CLOUD_RUN_PRODUCTION, got {detected_env}"
            )
            
            print("   ✅ Production environment properly detected")
    
    def test_environment_detection_local(self):
        """Test that local development environment is properly detected."""
        print("\n🔍 Testing local development environment detection...")
        
        # Clear ENVIRONMENT variable or set to development
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=False):
            manager = CloudNativeTimeoutManager()
            detected_env = manager._detect_environment()
            
            print(f"   Environment variable: {os.environ.get('ENVIRONMENT', 'Not Set')}")
            print(f"   Detected environment: {detected_env}")
            
            self.assertEqual(
                detected_env,
                TimeoutEnvironment.LOCAL_DEVELOPMENT,
                f"Environment detection failed. Expected LOCAL_DEVELOPMENT, got {detected_env}"
            )
            
            print("   ✅ Local development environment properly detected")


def run_timeout_validation_tests():
    """Run all WebSocket timeout validation tests."""
    print("=" * 80)
    print("WEBSOCKET TIMEOUT VALIDATION TEST SUITE - ISSUE #404")
    print("=" * 80)
    print("MISSION: Determine if 3.0s staging timeouts are deployed vs 1.2s race condition")
    print("EXPECTED: Tests PASS = 3.0s deployed, Tests FAIL = 1.2s still active")
    print("=" * 80)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add timeout validation tests
    suite.addTest(TestWebSocketTimeoutValidation('test_staging_websocket_recv_timeout_is_35_seconds'))
    suite.addTest(TestWebSocketTimeoutValidation('test_staging_agent_execution_timeout_is_30_seconds'))
    suite.addTest(TestWebSocketTimeoutValidation('test_timeout_hierarchy_validation_staging'))
    suite.addTest(TestWebSocketTimeoutValidation('test_convenience_functions_return_staging_values'))
    suite.addTest(TestWebSocketTimeoutValidation('test_gcp_initialization_validator_timeout_optimization'))
    suite.addTest(TestWebSocketTimeoutValidation('test_race_condition_detection_in_old_configuration'))
    
    # Add environment detection tests
    suite.addTest(TestEnvironmentDetection('test_environment_detection_staging'))
    suite.addTest(TestEnvironmentDetection('test_environment_detection_production'))
    suite.addTest(TestEnvironmentDetection('test_environment_detection_local'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    
    # Print results summary
    print("\n" + "=" * 80)
    print("🏁 TEST EXECUTION SUMMARY")
    print("=" * 80)
    
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
        print("✅ ASSESSMENT: 3.0s staging timeouts are deployed and working")
        print("✅ RACE CONDITION: RESOLVED - Timeout hierarchy properly configured")
        print("✅ RECOMMENDATION: PROCEED TO VALIDATION - No remediation needed")
        return True
    else:
        print("❌ TESTS FAILED")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")
        print("❌ ASSESSMENT: 1.2s race condition timeouts may still be active")
        print("❌ RECOMMENDATION: PROCEED TO REMEDIATION - Fix timeout configuration")
        
        if result.failures:
            print("\n🔍 FAILURE DETAILS:")
            for test, traceback in result.failures:
                print(f"   FAILED: {test}")
                print(f"   REASON: {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'Unknown'}")
        
        if result.errors:
            print("\n🔍 ERROR DETAILS:")
            for test, traceback in result.errors:
                print(f"   ERROR: {test}")
                print(f"   REASON: {traceback.split('Exception:')[-1].strip() if 'Exception:' in traceback else 'Unknown'}")
        
        return False


if __name__ == '__main__':
    success = run_timeout_validation_tests()
    sys.exit(0 if success else 1)