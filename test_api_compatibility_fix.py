#!/usr/bin/env python3
"""
API Compatibility Fix Validation Test
Tests the two P0 API compatibility fixes implemented for Issue #872.
"""

import asyncio
import sys
import traceback


async def test_authentication_api_user_prefix():
    """Test that create_authenticated_user now supports user_prefix parameter."""
    print("[TEST] Testing authentication API enhancement...")

    try:
        from test_framework.ssot.e2e_auth_helper import create_authenticated_user

        # Test 1: Default user_prefix behavior
        token1, user_data1 = await create_authenticated_user(
            environment="test",
            user_prefix="testuser"
        )

        assert token1, "Token should not be empty"
        assert user_data1, "User data should not be empty"
        assert user_data1["id"].startswith("testuser-"), f"User ID should start with 'testuser-', got: {user_data1['id']}"

        print("[PASS] Test 1: user_prefix parameter works correctly")

        # Test 2: Backward compatibility (original behavior)
        token2, user_data2 = await create_authenticated_user(
            environment="test"
        )

        assert token2, "Token should not be empty for default behavior"
        assert user_data2, "User data should not be empty for default behavior"
        assert user_data2["id"].startswith("user-"), f"Default user ID should start with 'user-', got: {user_data2['id']}"

        print("[PASS] Test 2: Backward compatibility maintained")

        # Test 3: Custom user_prefix with existing user_id should be ignored
        token3, user_data3 = await create_authenticated_user(
            environment="test",
            user_id="custom-user-123",
            user_prefix="ignored"
        )

        assert user_data3["id"] == "custom-user-123", f"Custom user_id should be preserved, got: {user_data3['id']}"

        print("[PASS] Test 3: Custom user_id takes precedence over user_prefix")

        return True

    except Exception as e:
        print(f"❌ Authentication API test FAILED: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


def test_websocket_client_constructor_compatibility():
    """Test that WebSocketTestClient now supports legacy constructor patterns."""
    print("🔧 Testing WebSocket client API unification...")

    try:
        from test_framework.websocket_helpers import WebSocketTestClient

        # Test 1: Original pattern - WebSocketTestClient(url, user_id)
        client1 = WebSocketTestClient("ws://localhost:8002/ws", user_id="test-user-1")
        assert client1.url == "ws://localhost:8002/ws", f"URL not set correctly: {client1.url}"
        assert client1.user_id == "test-user-1", f"User ID not set correctly: {client1.user_id}"
        assert client1.headers == {}, f"Headers should be empty for original pattern: {client1.headers}"

        print("✅ Test 1 PASS: Original pattern WebSocketTestClient(url, user_id) works")

        # Test 2: Legacy pattern - WebSocketTestClient(url, headers)
        headers = {"Authorization": "Bearer test-token", "X-User-ID": "test-user-2"}
        client2 = WebSocketTestClient("ws://localhost:8002/ws", headers)

        assert client2.url == "ws://localhost:8002/ws", f"URL not set correctly: {client2.url}"
        assert client2.headers == headers, f"Headers not set correctly: {client2.headers}"
        assert client2.user_id.startswith("test_user_"), f"User ID should be auto-generated: {client2.user_id}"

        print("✅ Test 2 PASS: Legacy pattern WebSocketTestClient(url, headers) works")

        # Test 3: Named parameter pattern - WebSocketTestClient(url="...", headers={...})
        client3 = WebSocketTestClient(url="ws://localhost:8002/ws", headers=headers)
        assert client3.url == "ws://localhost:8002/ws", f"URL not set correctly: {client3.url}"
        assert client3.headers == headers, f"Headers not set correctly: {client3.headers}"

        print("✅ Test 3 PASS: Named parameter pattern works")

        # Test 4: Default URL behavior
        client4 = WebSocketTestClient(headers=headers)
        assert client4.url == "ws://localhost:8002/ws", f"Default URL not set: {client4.url}"

        print("✅ Test 4 PASS: Default URL behavior works")

        return True

    except Exception as e:
        print(f"❌ WebSocket client test FAILED: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


async def main():
    """Run all API compatibility tests."""
    print("🚀 Running API Compatibility Fix Validation for Issue #872")
    print("=" * 60)

    results = []

    # Test 1: Authentication API Enhancement
    auth_result = await test_authentication_api_user_prefix()
    results.append(("Authentication API Enhancement", auth_result))

    print()

    # Test 2: WebSocket Client API Unification
    websocket_result = test_websocket_client_constructor_compatibility()
    results.append(("WebSocket Client API Unification", websocket_result))

    print()
    print("=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 60)

    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED! API compatibility fixes are working correctly.")
        print("Ready to proceed with e2e test execution.")
        return 0
    else:
        print("💥 SOME TESTS FAILED! Review the fixes before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))