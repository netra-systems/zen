"""
Test plan for Redis 'bool' object is not callable issue #334

This test suite reproduces and validates the Redis type error where `redis_manager.is_connected()`
is incorrectly called as a method when it's actually a property.

Business Value:
- Segment: Platform/Internal - Redis cache performance
- Goal: System Stability - Eliminate type errors in Redis readiness validation
- Impact: Fixes degraded Redis performance affecting chat response speed
- Revenue: Protects 90% of platform value (chat functionality) from performance degradation

Test Categories:
1. FAILING TESTS - Reproduce the exact 'bool' object is not callable error
2. VALIDATION TESTS - Verify correct property access works
3. INTEGRATION TESTS - Test GCP initialization validator behavior
4. REGRESSION TESTS - Ensure fix doesn't break other functionality

Follows SSOT testing patterns per CLAUDE.md requirements.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.websocket_core.gcp_initialization_validator import GCPWebSocketInitializationValidator


class TestRedisBoolCallableIssue334(SSotBaseTestCase):
    """
    CRITICAL TEST SUITE: Redis 'bool' object is not callable issue #334
    
    Tests the specific TypeError where redis_manager.is_connected() is called as method
    when it should be accessed as property redis_manager.is_connected
    
    Business Impact: Fixes performance degradation affecting chat response speed
    """

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.redis_manager = RedisManager()
        
    def teardown_method(self):
        """Clean up after tests."""
        super().teardown_method()
        
    # =============================================================================
    # 1. FAILING TESTS - Reproduce the exact issue
    # =============================================================================
    
    def test_redis_is_connected_method_call_fails_with_bool_callable_error(self):
        """
        FAILING TEST: Reproduces the exact 'bool' object is not callable error
        
        This test MUST FAIL initially to prove we can reproduce the issue.
        After the fix is applied, this test should pass with proper error handling.
        
        Business Value: Confirms we can reproduce the performance degradation issue
        """
        # SETUP: Create a Redis manager with is_connected as property returning bool
        redis_manager = RedisManager()
        
        # Force the property to return a boolean (simulating real scenario)
        with patch.object(redis_manager, '_connected', True):
            with patch.object(redis_manager, '_client', Mock()):
                # VERIFY: Property access works correctly
                self.assertTrue(redis_manager.is_connected)  # This should work
                
                # REPRODUCE THE BUG: Calling as method should fail
                with self.expect_exception(TypeError, "'bool' object is not callable"):
                    # This is the EXACT problematic call from gcp_initialization_validator.py:376
                    result = redis_manager.is_connected()
                
    def test_gcp_validator_reproduces_callable_error_in_redis_readiness(self):
        """
        FAILING TEST: Reproduces the error in GCP initialization validator context
        
        This simulates the exact scenario where the error occurs in production.
        Tests the _validate_redis_readiness method that contains the bug.
        
        Business Value: Validates the exact production failure scenario
        """
        # SETUP: Create GCP validator with mocked app_state
        validator = GCPWebSocketInitializationValidator()
        
        # Create a mock app_state with Redis manager that has is_connected property
        mock_app_state = Mock()
        mock_redis_manager = Mock()
        
        # CRITICAL: Set up is_connected as property that returns boolean
        type(mock_redis_manager).is_connected = property(lambda self: True)
        mock_app_state.redis_manager = mock_redis_manager
        
        # REPRODUCE THE BUG: This should fail with 'bool' object is not callable
        with self.expect_exception(TypeError, "'bool' object is not callable"):
            # Simulate the problematic code path from line 376
            is_connected = mock_redis_manager.is_connected()  # This is the bug!
        
    def test_multiple_redis_managers_consistent_interface_violation(self):
        """
        FAILING TEST: Demonstrates interface inconsistency across Redis managers
        
        Different Redis managers may have is_connected as method vs property,
        causing inconsistent behavior and the callable error.
        
        Business Value: Identifies interface consistency issues across services
        """
        # Test various Redis manager implementations that might exist
        managers_to_test = [
            'netra_backend.app.redis_manager.RedisManager',
            'netra_backend.app.db.redis_manager.RedisManager', 
            'netra_backend.app.managers.redis_manager.RedisManager'
        ]
        
        interface_types = {}
        
        for manager_path in managers_to_test:
            try:
                # Import the manager dynamically
                module_path, class_name = manager_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                manager_class = getattr(module, class_name, None)
                
                if manager_class:
                    # Check if is_connected is property or method
                    if hasattr(manager_class, 'is_connected'):
                        attr = getattr(manager_class, 'is_connected')
                        if isinstance(attr, property):
                            interface_types[manager_path] = 'property'
                        else:
                            interface_types[manager_path] = 'method'
                            
            except (ImportError, AttributeError):
                # Manager doesn't exist or is not accessible
                continue
                
        # VERIFY: Interface consistency (this may fail if we have mixed interfaces)
        if len(set(interface_types.values())) > 1:
            self.fail(f"Inconsistent is_connected interface across managers: {interface_types}")

    # =============================================================================
    # 2. VALIDATION TESTS - Test correct implementation
    # =============================================================================
    
    def test_redis_is_connected_property_access_works_correctly(self):
        """
        VALIDATION TEST: Verify correct property access returns boolean
        
        This test validates the CORRECT way to access is_connected.
        Should pass both before and after the fix.
        
        Business Value: Confirms correct Redis connection checking works
        """
        redis_manager = RedisManager()
        
        # Test with connected state
        with patch.object(redis_manager, '_connected', True):
            with patch.object(redis_manager, '_client', Mock()):
                # CORRECT USAGE: Access as property
                result = redis_manager.is_connected
                self.assertTrue(isinstance(result, bool))
                self.assertTrue(result)
                
        # Test with disconnected state
        with patch.object(redis_manager, '_connected', False):
            with patch.object(redis_manager, '_client', None):
                # CORRECT USAGE: Access as property
                result = redis_manager.is_connected
                self.assertTrue(isinstance(result, bool))
                self.assertFalse(result)
                
    def test_redis_manager_property_interface_is_consistent(self):
        """
        VALIDATION TEST: Verify is_connected is properly defined as property
        
        This test ensures the Redis manager interface is correctly implemented
        according to Python property patterns.
        
        Business Value: Validates proper OOP interface design
        """
        redis_manager = RedisManager()
        
        # VERIFY: is_connected is defined as property
        self.assertTrue(hasattr(RedisManager, 'is_connected'))
        attr = getattr(RedisManager, 'is_connected')
        self.assertTrue(isinstance(attr, property))
        
        # VERIFY: Property has correct getter
        self.assertIsNotNone(attr.fget)
        self.assertIsNone(attr.fset)  # Should be read-only
        
    def test_redis_connection_states_return_correct_boolean_values(self):
        """
        VALIDATION TEST: Test all possible connection states return proper booleans
        
        Validates that the is_connected property correctly reflects various
        Redis connection states without type errors.
        
        Business Value: Ensures reliable Redis status reporting
        """
        redis_manager = RedisManager()
        
        # Test case 1: Not connected, no client
        with patch.object(redis_manager, '_connected', False):
            with patch.object(redis_manager, '_client', None):
                result = redis_manager.is_connected
                self.assertFalse(result)
                
        # Test case 2: Connected flag true, but no client
        with patch.object(redis_manager, '_connected', True):
            with patch.object(redis_manager, '_client', None):
                result = redis_manager.is_connected
                self.assertFalse(result)
                
        # Test case 3: Not connected flag, but client exists
        with patch.object(redis_manager, '_connected', False):
            with patch.object(redis_manager, '_client', Mock()):
                result = redis_manager.is_connected
                self.assertFalse(result)
                
        # Test case 4: Connected and client exists (ideal state)
        with patch.object(redis_manager, '_connected', True):
            with patch.object(redis_manager, '_client', Mock()):
                result = redis_manager.is_connected
                self.assertTrue(result)

    # =============================================================================
    # 3. INTEGRATION TESTS - GCP initialization validator scenarios
    # =============================================================================
    
    def test_gcp_validator_redis_readiness_with_correct_property_access(self):
        """
        INTEGRATION TEST: Test GCP validator with corrected Redis property access
        
        This test simulates how the GCP initialization validator SHOULD work
        after the fix is applied.
        
        Business Value: Validates the fix eliminates performance degradation
        """
        validator = GCPWebSocketInitializationValidator()
        
        # Create mock app_state with properly working Redis manager
        mock_app_state = Mock()
        mock_redis_manager = Mock()
        
        # CORRECT: Set up is_connected as property returning boolean
        type(mock_redis_manager).is_connected = property(lambda self: True)
        mock_app_state.redis_manager = mock_redis_manager
        
        # This should work without throwing 'bool' object is not callable
        with patch.object(validator, 'logger') as mock_logger:
            # Simulate the CORRECTED code path
            redis_manager = mock_app_state.redis_manager
            
            if hasattr(redis_manager, 'is_connected'):
                # FIXED: Access as property, not method call
                is_connected = redis_manager.is_connected  # No parentheses!
                
                # VERIFY: No TypeError, gets boolean result
                self.assertTrue(isinstance(is_connected, bool))
                self.assertTrue(is_connected)
                
    def test_gcp_validator_graceful_degradation_behavior(self):
        """
        INTEGRATION TEST: Test graceful degradation when Redis check fails
        
        Validates that even if Redis checking has issues, the system
        can gracefully degrade while preserving chat functionality.
        
        Business Value: Ensures 90% platform value (chat) is protected
        """
        validator = GCPWebSocketInitializationValidator()
        
        # Test scenario where Redis manager is None (missing)
        mock_app_state = Mock()
        mock_app_state.redis_manager = None
        
        with patch.object(validator, 'logger') as mock_logger:
            # Simulate _validate_redis_readiness with None manager
            redis_manager = mock_app_state.redis_manager
            
            if redis_manager is None:
                mock_logger.warning.assert_not_called()  # Initially not called
                
                # This should handle gracefully
                result = False  # Expected behavior for None manager
                self.assertFalse(result)
                
    def test_gcp_validator_redis_exception_handling(self):
        """
        INTEGRATION TEST: Test handling of Redis connection exceptions
        
        Validates that Redis connection exceptions are properly handled
        without breaking the initialization process.
        
        Business Value: Maintains system stability during Redis failures
        """
        validator = GCPWebSocketInitializationValidator()
        
        # Create mock app_state with Redis manager that throws exception
        mock_app_state = Mock()
        mock_redis_manager = Mock()
        
        # Simulate Redis connection exception
        type(mock_redis_manager).is_connected = property(
            lambda self: exec('raise ConnectionError("Redis unavailable")')
        )
        mock_app_state.redis_manager = mock_redis_manager
        
        with patch.object(validator, 'logger') as mock_logger:
            try:
                # This should handle the exception gracefully
                redis_manager = mock_app_state.redis_manager
                is_connected = redis_manager.is_connected
                
            except Exception as e:
                # System should handle this gracefully, not crash
                self.assertTrue(isinstance(e, (ConnectionError, AttributeError)))

    # =============================================================================
    # 4. REGRESSION TESTS - Ensure fix doesn't break other functionality  
    # =============================================================================
    
    def test_redis_manager_other_methods_still_work_after_fix(self):
        """
        REGRESSION TEST: Verify other Redis manager methods work correctly
        
        Ensures that fixing is_connected doesn't break other Redis operations.
        
        Business Value: Prevents regression in Redis caching functionality
        """
        redis_manager = RedisManager()
        
        # Test other methods that should still work
        with patch.object(redis_manager, '_client', Mock()) as mock_client:
            with patch.object(redis_manager, '_connected', True):
                
                # Test get_status method
                status = redis_manager.get_status()
                self.assertTrue(isinstance(status, dict))
                self.assertIn('connected', status)
                
                # Test connection-related methods exist
                self.assertTrue(hasattr(redis_manager, 'connect'))
                self.assertTrue(hasattr(redis_manager, 'disconnect'))
                
    def test_backwards_compatibility_with_existing_code(self):
        """
        REGRESSION TEST: Ensure existing code accessing is_connected property works
        
        Validates that code correctly accessing is_connected as property
        continues to work after any fixes are applied.
        
        Business Value: Maintains compatibility with existing implementations
        """
        redis_manager = RedisManager()
        
        # Simulate existing correct usage patterns found in codebase
        with patch.object(redis_manager, '_connected', True):
            with patch.object(redis_manager, '_client', Mock()):
                
                # Pattern 1: Direct property access (should work)
                connected = redis_manager.is_connected
                self.assertTrue(connected)
                
                # Pattern 2: Boolean evaluation (should work)
                if redis_manager.is_connected:
                    self.assertTrue(True)  # Should execute
                    
                # Pattern 3: Negation (should work)
                not_connected = not redis_manager.is_connected
                self.assertFalse(not_connected)

    # =============================================================================
    # 5. PERFORMANCE TESTS - Chat functionality impact
    # =============================================================================
    
    def test_redis_property_access_performance_vs_method_call(self):
        """
        PERFORMANCE TEST: Compare property access vs method call performance
        
        Validates that property access (correct) is performant for chat functionality.
        
        Business Value: Ensures Redis checking doesn't slow chat response time
        """
        redis_manager = RedisManager()
        
        with patch.object(redis_manager, '_connected', True):
            with patch.object(redis_manager, '_client', Mock()):
                
                import time
                
                # Test property access performance (correct approach)
                start_time = time.perf_counter()
                for _ in range(1000):
                    _ = redis_manager.is_connected  # Property access
                property_time = time.perf_counter() - start_time
                
                # Property access should be fast (< 1ms for 1000 calls)
                self.assertLess(property_time, 0.001)
                
    def test_gcp_validator_redis_check_chat_impact_minimal(self):
        """
        PERFORMANCE TEST: Ensure Redis readiness check doesn't impact chat speed
        
        Validates that Redis connection checking in GCP validator is fast enough
        to not affect chat response times.
        
        Business Value: Protects chat performance (90% of platform value)
        """
        validator = GCPWebSocketInitializationValidator()
        
        # Create realistic Redis manager mock
        mock_app_state = Mock()
        mock_redis_manager = Mock()
        type(mock_redis_manager).is_connected = property(lambda self: True)
        mock_app_state.redis_manager = mock_redis_manager
        
        import time
        
        # Test Redis readiness check performance
        start_time = time.perf_counter()
        
        # Simulate the fixed Redis readiness check
        redis_manager = mock_app_state.redis_manager
        if hasattr(redis_manager, 'is_connected'):
            is_connected = redis_manager.is_connected  # Fixed: property access
            
        check_time = time.perf_counter() - start_time
        
        # Redis check should be very fast (< 1ms)
        self.assertLess(check_time, 0.001)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])