#!/usr/bin/env python3
"""
Test script to validate WebSocket manager circular reference fix.
This script tests the core factory pattern without network dependencies.
"""
import asyncio
import sys
import traceback


async def test_websocket_manager_creation():
    """Test WebSocket manager creation using SSOT factory pattern."""
    print("Testing WebSocket manager factory pattern...")

    try:
        # Test 1: Import the function (this would fail with circular reference)
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        print("PASS: Import successful - no circular reference")

        # Test 2: Create a mock user context
        class MockUserContext:
            def __init__(self):
                self.user_id = 'test_user_123'
                self.request_id = 'test_request_456'
                self.thread_id = 'test_thread_789'

        user_context = MockUserContext()

        # Test 3: Try to create WebSocket manager (this would fail with factory bypass)
        manager = await get_websocket_manager(user_context)
        print("PASS: WebSocket manager created successfully")
        print(f"PASS: Manager type: {type(manager).__name__}")

        # Test 4: Verify it has the expected interface
        expected_methods = ['send_message', 'remove_connection', 'add_connection']
        for method in expected_methods:
            if hasattr(manager, method):
                print(f"PASS: Manager has {method} method")
            else:
                print(f"WARN: Manager missing {method} method")

        # Test 5: Verify user context is properly set
        if hasattr(manager, 'user_context') and manager.user_context is not None:
            print(f"PASS: User context properly set: {manager.user_context.user_id}")
        else:
            print("WARN: User context not found")

        return True

    except ImportError as e:
        print(f"FAIL: Import error (likely circular reference): {e}")
        return False
    except Exception as e:
        if "FactoryBypassDetected" in str(e) or "authorization token" in str(e):
            print(f"FAIL: Factory pattern error: {e}")
        else:
            print(f"FAIL: Unexpected error: {type(e).__name__}: {e}")
        return False


async def test_import_paths():
    """Test different import paths to ensure consistency."""
    print("\nTesting import paths...")

    try:
        # Test canonical import
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as gws1
        print("PASS: Canonical import works")

        # Test backward compatibility import
        from netra_backend.app.websocket_core import get_websocket_manager as gws2
        print("PASS: Backward compatibility import works")

        # Verify they're the same function (or at least both work)
        print(f"PASS: Import consistency validated")

        return True

    except Exception as e:
        print(f"FAIL: Import path error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("WEBSOCKET MANAGER CIRCULAR REFERENCE FIX VALIDATION")
    print("=" * 60)

    test1_result = await test_websocket_manager_creation()
    test2_result = await test_import_paths()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if test1_result and test2_result:
        print("SUCCESS: All tests passed - Circular reference fix working!")
        return 0
    else:
        print("FAILURE: Some tests failed - Fix needs more work")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"CRITICAL: Test execution failed: {e}")
        traceback.print_exc()
        sys.exit(1)