#!/usr/bin/env python3
"""
User Isolation Verification Test
Ensures that user isolation functionality is maintained after factory pattern cleanup
"""

import sys
from datetime import datetime

print("🔒 USER ISOLATION VERIFICATION TEST")
print("=" * 45)

# Add project to path
sys.path.insert(0, '/c/netra-apex')

def test_simple_user_context_isolation():
    """Test that SimpleUserContext properly isolates users"""

    print("\n🧪 SimpleUserContext Isolation Test:")

    try:
        from netra_backend.app.websocket_core.simple_websocket_creation import SimpleUserContext

        # Create two different user contexts
        user1_context = SimpleUserContext(
            user_id="user_1",
            thread_id="thread_1",
            run_id="run_1",
            request_id="request_1",
            websocket_client_id="client_1",
            created_at=datetime.now(),
            session_data={"user_data": "user1_specific"}
        )

        user2_context = SimpleUserContext(
            user_id="user_2",
            thread_id="thread_2",
            run_id="run_2",
            request_id="request_2",
            websocket_client_id="client_2",
            created_at=datetime.now(),
            session_data={"user_data": "user2_specific"}
        )

        # Test 1: Different objects
        if user1_context is not user2_context:
            print(f"  ✅ Different objects created: PASS")
        else:
            print(f"  ❌ Same object returned: FAIL")
            return False

        # Test 2: Different user IDs
        if user1_context.user_id != user2_context.user_id:
            print(f"  ✅ User ID isolation: PASS")
        else:
            print(f"  ❌ User ID isolation: FAIL")
            return False

        # Test 3: Different isolation keys
        if user1_context.isolation_key != user2_context.isolation_key:
            print(f"  ✅ Isolation key separation: PASS")
        else:
            print(f"  ❌ Isolation key separation: FAIL")
            return False

        # Test 4: Separate session data
        user1_context.set_state("test_key", "user1_value")
        user2_context.set_state("test_key", "user2_value")

        if (user1_context.get_state()["test_key"] != user2_context.get_state()["test_key"]):
            print(f"  ✅ Session data isolation: PASS")
        else:
            print(f"  ❌ Session data isolation: FAIL")
            return False

        # Test 5: State modification doesn't affect other users
        user1_context.set_state("unique_key", "user1_only")

        if ("unique_key" not in user2_context.get_state()):
            print(f"  ✅ State modification isolation: PASS")
        else:
            print(f"  ❌ State modification isolation: FAIL")
            return False

        print(f"  🎯 SimpleUserContext isolation: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"  ❌ SimpleUserContext isolation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_real_websocket_setup_isolation():
    """Test that RealWebSocketSetup maintains user isolation"""

    print("\n🌐 RealWebSocketSetup Isolation Test:")

    try:
        from test_framework.real_service_setup import RealWebSocketSetup

        # Create setups for different users
        user1_setup = RealWebSocketSetup(
            websocket_url="ws://test1.example.com",
            connection_timeout=30.0,
            auth_token="token_user1",
            user_context={"user_id": "user1", "role": "admin"}
        )

        user2_setup = RealWebSocketSetup(
            websocket_url="ws://test2.example.com",
            connection_timeout=60.0,
            auth_token="token_user2",
            user_context={"user_id": "user2", "role": "user"}
        )

        # Test 1: Different objects
        if user1_setup is not user2_setup:
            print(f"  ✅ Different RealWebSocketSetup objects: PASS")
        else:
            print(f"  ❌ Same RealWebSocketSetup object: FAIL")
            return False

        # Test 2: Different auth tokens
        if user1_setup.auth_token != user2_setup.auth_token:
            print(f"  ✅ Auth token isolation: PASS")
        else:
            print(f"  ❌ Auth token isolation: FAIL")
            return False

        # Test 3: Different user contexts
        if user1_setup.user_context != user2_setup.user_context:
            print(f"  ✅ User context isolation: PASS")
        else:
            print(f"  ❌ User context isolation: FAIL")
            return False

        # Test 4: Independent configuration
        if (user1_setup.websocket_url != user2_setup.websocket_url and
            user1_setup.connection_timeout != user2_setup.connection_timeout):
            print(f"  ✅ Independent configuration: PASS")
        else:
            print(f"  ❌ Independent configuration: FAIL")
            return False

        print(f"  🎯 RealWebSocketSetup isolation: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"  ❌ RealWebSocketSetup isolation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_concurrent_user_scenarios():
    """Test that concurrent user scenarios work correctly"""

    print("\n⚡ Concurrent User Scenario Test:")

    try:
        from netra_backend.app.websocket_core.simple_websocket_creation import SimpleUserContext
        from datetime import datetime

        # Simulate multiple concurrent users
        users = []
        for i in range(10):
            user_context = SimpleUserContext(
                user_id=f"concurrent_user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                request_id=f"request_{i}",
                websocket_client_id=f"client_{i}",
                created_at=datetime.now(),
                session_data={"sequence": i}
            )
            users.append(user_context)

        # Test 1: All users have unique isolation keys
        isolation_keys = [user.isolation_key for user in users]
        if len(set(isolation_keys)) == len(users):
            print(f"  ✅ Unique isolation keys for {len(users)} users: PASS")
        else:
            print(f"  ❌ Duplicate isolation keys found: FAIL")
            return False

        # Test 2: State changes don't affect other users
        for i, user in enumerate(users):
            user.set_state("user_specific_data", f"data_for_user_{i}")

        # Verify each user has their own data
        for i, user in enumerate(users):
            expected_data = f"data_for_user_{i}"
            actual_data = user.get_state().get("user_specific_data")
            if actual_data != expected_data:
                print(f"  ❌ User {i} data corruption: expected '{expected_data}', got '{actual_data}'")
                return False

        print(f"  ✅ State isolation for {len(users)} concurrent users: PASS")

        # Test 3: Memory efficiency (no shared references)
        user_data_objects = [id(user.session_data) for user in users]
        if len(set(user_data_objects)) == len(users):
            print(f"  ✅ Independent memory allocation: PASS")
        else:
            print(f"  ❌ Shared memory references found: FAIL")
            return False

        print(f"  🎯 Concurrent user scenarios: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"  ❌ Concurrent user test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all user isolation verification tests"""

    print(f"\n🔐 Running User Isolation Verification Tests...")

    test_results = [
        test_simple_user_context_isolation(),
        test_real_websocket_setup_isolation(),
        test_concurrent_user_scenarios()
    ]

    passed_tests = sum(test_results)
    total_tests = len(test_results)

    print(f"\n📊 USER ISOLATION TEST RESULTS:")
    print(f"  ✅ Passed: {passed_tests}")
    print(f"  ❌ Failed: {total_tests - passed_tests}")
    print(f"  📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    if all(test_results):
        print(f"\n🏆 USER ISOLATION VERIFICATION: PASSED")
        print(f"🛡️ Multi-user system isolation maintained after factory cleanup")
        return True
    else:
        print(f"\n⚠️ USER ISOLATION VERIFICATION: ISSUES FOUND")
        print(f"🚨 User isolation may be compromised")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)