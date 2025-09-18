#!/usr/bin/env python3
"""
Test script for Issue #959 SSOT consolidation verification.

This script tests:
1. The Protocol interface still works for type hints
2. The concrete class (now WebSocketConnectionWrapper) still works
3. The backward compatibility alias works
4. No naming conflicts exist
"""

import asyncio
import sys
from typing import Dict, Any

# Test the imports
try:
    from netra_backend.app.websocket_core.protocols import (
        WebSocketProtocol,  # Should be the Protocol interface + backward compatibility alias
        WebSocketConnectionWrapper,  # New concrete class name
        WebSocketProtocolValidator
    )
    print("[PASS] All imports successful")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test 1: Protocol interface for type hints
def test_protocol_interface():
    """Test that WebSocketProtocol can be used as a Protocol for type hints."""
    try:
        # This should work - using as type hint
        def function_expecting_protocol(manager: WebSocketProtocol) -> str:
            return f"Manager type: {type(manager).__name__}"

        print("[PASS] Protocol interface works for type hints")
        return True
    except Exception as e:
        print(f"[FAIL] Protocol interface test failed: {e}")
        return False

# Test 2: Concrete class functionality
async def test_concrete_class():
    """Test that WebSocketConnectionWrapper works as expected."""
    try:
        # Create instance using new name
        wrapper = WebSocketConnectionWrapper(
            websocket=None,
            connection_id="test-conn-123",
            user_id="test-user-456"
        )

        # Test properties
        assert wrapper.connection_id == "test-conn-123"
        assert wrapper.user_id == "test-user-456"
        assert wrapper.is_active == True

        # Test close method
        await wrapper.close()
        assert wrapper.is_active == False

        print("[PASS] WebSocketConnectionWrapper works correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Concrete class test failed: {e}")
        return False

# Test 3: Backward compatibility alias
async def test_backward_compatibility():
    """Test that the backward compatibility alias works."""
    try:
        # This should still work due to the alias
        # WebSocketProtocol = WebSocketConnectionWrapper
        legacy_instance = WebSocketProtocol(
            websocket=None,
            connection_id="legacy-conn-789",
            user_id="legacy-user-101"
        )

        # Should have the same functionality
        assert legacy_instance.connection_id == "legacy-conn-789"
        assert legacy_instance.user_id == "legacy-user-101"
        assert legacy_instance.is_active == True

        await legacy_instance.close()
        assert legacy_instance.is_active == False

        print("[PASS] Backward compatibility alias works")
        return True
    except Exception as e:
        print(f"[FAIL] Backward compatibility test failed: {e}")
        return False

# Test 4: Type checking
def test_type_relationships():
    """Test that type relationships work correctly."""
    try:
        # Create instances
        wrapper = WebSocketConnectionWrapper()
        legacy = WebSocketProtocol()

        # Both should be the same type due to alias
        assert type(wrapper) == type(legacy)
        assert type(wrapper).__name__ == 'WebSocketConnectionWrapper'
        assert type(legacy).__name__ == 'WebSocketConnectionWrapper'

        print("[PASS] Type relationships work correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Type relationship test failed: {e}")
        return False

# Test 5: Protocol validator still works
def test_validator_functionality():
    """Test that the validator can distinguish protocols properly."""
    try:
        # Create a test instance
        wrapper = WebSocketConnectionWrapper()

        # The validator should be able to process it
        # Note: It may not be fully compliant since this is just a simple wrapper
        validation_result = WebSocketProtocolValidator.validate_manager_protocol(wrapper)

        # Should return a proper validation result
        assert isinstance(validation_result, dict)
        assert 'compliant' in validation_result
        assert 'manager_type' in validation_result
        assert validation_result['manager_type'] == 'WebSocketConnectionWrapper'

        print("[PASS] Protocol validator works with new class name")
        return True
    except Exception as e:
        print(f"[FAIL] Validator test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Testing Issue #959 SSOT consolidation...")
    print("=" * 50)

    tests_passed = 0
    total_tests = 5

    # Run tests
    if test_protocol_interface():
        tests_passed += 1

    if await test_concrete_class():
        tests_passed += 1

    if await test_backward_compatibility():
        tests_passed += 1

    if test_type_relationships():
        tests_passed += 1

    if test_validator_functionality():
        tests_passed += 1

    print("=" * 50)
    print(f"Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("[SUCCESS] All tests passed! SSOT consolidation successful.")
        return True
    else:
        print(f"[FAIL] {total_tests - tests_passed} tests failed. Review issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)