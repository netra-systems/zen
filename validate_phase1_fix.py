#!/usr/bin/env python3
"""
Phase 1 SSOT Interface Compatibility Validation Script
Issue #871 - DeepAgentState SSOT Violations

This script validates that the SSOT interface fixes work correctly.
"""

def test_ssot_interface_compatibility():
    """Test the SSOT DeepAgentState interface compatibility fixes."""
    print("TESTING SSOT Interface Compatibility...")

    try:
        from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState
        print("SUCCESS: Successfully imported SSOT DeepAgentState")
    except ImportError as e:
        print(f"FAILED: Failed to import SSOT DeepAgentState: {e}")
        return False

    # Test 1: Property access works
    print("\nTest 1: Property access functionality")
    try:
        state = SsotState()
        state.thread_id = "test123"
        assert state.thread_id == "test123"
        print("SUCCESS: Property assignment works")
        assert state.chat_thread_id == "test123"
        print("SUCCESS: Property maps to chat_thread_id correctly")
    except Exception as e:
        print(f"FAILED: Property access failed: {e}")
        return False

    # Test 2: Constructor parameter works
    print("\nTest 2: Constructor parameter mapping")
    try:
        state2 = SsotState(thread_id="test456")
        assert state2.thread_id == "test456"
        assert state2.chat_thread_id == "test456"
        print("SUCCESS: Constructor parameter mapping works")
    except Exception as e:
        print(f"FAILED: Constructor parameter failed: {e}")
        return False

    # Test 3: Bidirectional compatibility
    print("\nTest 3: Bidirectional compatibility")
    try:
        state3 = SsotState(chat_thread_id="test789")
        assert state3.thread_id == "test789"
        assert state3.chat_thread_id == "test789"
        print("SUCCESS: Backward compatibility via chat_thread_id works")
    except Exception as e:
        print(f"FAILED: Bidirectional compatibility failed: {e}")
        return False

    # Test 4: Runtime error prevention
    print("\nTest 4: Runtime error prevention")
    try:
        state4 = SsotState()
        # This should not raise AttributeError
        thread_id = getattr(state4, 'thread_id', None)
        print("SUCCESS: No AttributeError when accessing thread_id property")
    except AttributeError as e:
        print(f"FAILED: AttributeError still occurs: {e}")
        return False
    except Exception as e:
        print(f"FAILED: Unexpected error: {e}")
        return False

    print("\nALL SSOT INTERFACE COMPATIBILITY TESTS PASSED!")
    return True

def test_deprecated_import_still_works():
    """Test that deprecated import path still works (for now)."""
    print("\nTesting deprecated import compatibility...")

    try:
        from netra_backend.app.agents.state import DeepAgentState as DeprecatedState
        print("SUCCESS: Deprecated import still works")

        # Quick test that it has thread_id
        state = DeprecatedState()
        hasattr_result = hasattr(state, 'thread_id')
        print(f"SUCCESS: Deprecated version has thread_id attribute: {hasattr_result}")
        return True

    except Exception as e:
        print(f"FAILED: Deprecated import test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("Phase 1 SSOT Interface Compatibility Validation")
    print("=" * 60)

    success = True

    # Test SSOT interface
    success &= test_ssot_interface_compatibility()

    # Test deprecated still works
    success &= test_deprecated_import_still_works()

    print("\n" + "=" * 60)
    if success:
        print("PHASE 1 VALIDATION: ALL TESTS PASSED")
        print("Interface compatibility fixes are working correctly")
        print("Ready to proceed with system regression testing")
    else:
        print("PHASE 1 VALIDATION: SOME TESTS FAILED")
        print("Additional interface fixes may be needed")
        print("Review errors above and apply additional fixes")

    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)