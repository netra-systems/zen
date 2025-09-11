#!/usr/bin/env python3
"""
Test script to validate the Redis property access fix for Issue #334.

This test reproduces the specific "'bool' object is not callable" error
and validates that the fix (removing parentheses from is_connected()) works.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import Mock, patch
import pytest


class TestRedisManagerPropertyAccess:
    """Test Redis manager property access fix for Issue #334."""
    
    def test_is_connected_property_call_fix(self):
        """
        Test that redis_manager.is_connected is accessed as property, not method.
        
        This test reproduces Issue #334 where calling is_connected() on a boolean
        property caused "'bool' object is not callable" error.
        """
        # Create a mock Redis manager with is_connected as a boolean property
        mock_redis_manager = Mock()
        mock_redis_manager.is_connected = True  # This is a property, not a method
        
        # Create a mock app_state with our redis_manager
        mock_app_state = Mock()
        mock_app_state.redis_manager = mock_redis_manager
        
        # Import the validator class
        from netra_backend.app.websocket_core.gcp_initialization_validator import GCPWebSocketInitializationValidator
        
        # Create validator instance and set the app_state
        validator = GCPWebSocketInitializationValidator()
        validator.app_state = mock_app_state
        
        # Test the actual method - this should work with the fix
        import asyncio
        async def run_test():
            result = await validator._validate_redis_readiness()
            return result
        
        # Run the async test
        result = asyncio.run(run_test())
        
        # The method should complete successfully without "'bool' object is not callable" error
        assert isinstance(result, bool), f"Expected bool result, got {type(result)}"
        print(f"✅ Redis readiness validation result: {result}")
    
    def test_is_connected_method_simulation(self):
        """
        Test simulating the old broken behavior to confirm the fix.
        
        This demonstrates what would happen with the old code.
        """
        # Create a mock Redis manager with is_connected as a boolean property
        mock_redis_manager = Mock()
        mock_redis_manager.is_connected = True  # Property, not method
        
        # Simulate the OLD behavior (calling as method)
        try:
            # This should fail with "'bool' object is not callable"
            broken_result = mock_redis_manager.is_connected()
            pytest.fail("Expected TypeError but got result: " + str(broken_result))
        except TypeError as e:
            assert "'bool' object is not callable" in str(e)
            print(f"✅ Confirmed old behavior fails: {e}")
        
        # Simulate the FIXED behavior (accessing as property)
        try:
            fixed_result = mock_redis_manager.is_connected
            assert fixed_result is True
            print(f"✅ Confirmed new behavior works: {fixed_result}")
        except Exception as e:
            pytest.fail(f"Property access should not fail: {e}")


def run_validation_tests():
    """Run the validation tests."""
    print("🔧 Testing Redis property access fix for Issue #334...")
    print("=" * 60)
    
    test_instance = TestRedisManagerPropertyAccess()
    
    try:
        test_instance.test_is_connected_property_call_fix()
        print("✅ Property access fix validated successfully")
    except Exception as e:
        print(f"❌ Property access fix test failed: {e}")
        return False
    
    try:
        test_instance.test_is_connected_method_simulation()  
        print("✅ Old vs new behavior comparison validated")
    except Exception as e:
        print(f"❌ Behavior comparison test failed: {e}")
        return False
    
    print("=" * 60)
    print("🎉 All Redis property access fix tests PASSED!")
    return True


if __name__ == "__main__":
    success = run_validation_tests()
    sys.exit(0 if success else 1)