#!/usr/bin/env python3
"""
Simple Emergency Cleanup Bug Proof Script

This standalone script proves the WebSocket Manager Emergency Cleanup Failure bug exists
by directly testing the factory without complex test infrastructure.

RUN: python test_emergency_cleanup_simple_proof.py

EXPECTED: Demonstration of the "HARD LIMIT: User still over limit after cleanup (20/20)" error
"""

import asyncio
import time
import sys
import os
from typing import List, Dict

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
    from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory, CleanupLevel
    from test_framework.ssot.mock_factory import SSotMockFactory
    print("✅ Successfully imported required modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def test_emergency_cleanup_failure():
    """Test that reproduces the emergency cleanup failure bug."""
    print("\n🔍 Testing Emergency Cleanup Failure Bug")
    print("=" * 50)

    # Get factory and configure for testing
    factory = get_websocket_manager_factory()
    original_limit = factory.max_managers_per_user
    factory.max_managers_per_user = 20  # Set to 20 like in the bug reports

    print(f"Factory max managers per user: {factory.max_managers_per_user}")

    # Create mock factory for user contexts
    mock_factory = SSotMockFactory()
    user_id = "emergency_test_user_12345"

    created_managers = []

    try:
        # Phase 1: Create exactly 20 managers (at the limit)
        print(f"\n📊 Phase 1: Creating 20 managers for user {user_id}")

        for i in range(20):
            user_context = mock_factory.create_mock_user_context(
                user_id=user_id,
                websocket_connection_id=f"emergency_test_conn_{i}",
                session_id=f"emergency_session_{i}"
            )

            try:
                manager = get_websocket_manager(user_context=user_context)
                created_managers.append(manager)
                print(f"  ✅ Created manager {i+1}/20")
            except Exception as e:
                print(f"  ❌ Failed to create manager {i+1}: {e}")
                break

        current_count = factory.get_user_manager_count(user_id)
        print(f"📈 Current manager count: {current_count}")

        if current_count != 20:
            print(f"⚠️  Expected 20 managers, but got {current_count}")
            return False

        # Phase 2: Simulate some managers becoming zombies
        print(f"\n🧟 Phase 2: Converting some managers to zombies")
        zombie_count = 8

        for i in range(zombie_count):
            manager = created_managers[i]

            # Clear connections to simulate closed WebSocket connections
            if hasattr(manager, '_connections'):
                manager._connections.clear()
                print(f"  🧟 Cleared connections for manager {i+1}")

            # Mark as inactive
            if hasattr(manager, '_is_active'):
                manager._is_active = False
                print(f"  🧟 Marked manager {i+1} as inactive")

            # Set old activity time
            if hasattr(manager, '_last_activity_time'):
                manager._last_activity_time = time.time() - 3600  # 1 hour ago
                print(f"  🧟 Set old activity time for manager {i+1}")

            # Zero connection count
            if hasattr(manager, '_connection_count'):
                manager._connection_count = 0

        print(f"🧟 Created {zombie_count} zombie managers")

        # Phase 3: Try to create the 21st manager - should trigger emergency cleanup
        print(f"\n🚨 Phase 3: Attempting to create 21st manager (should trigger emergency cleanup)")

        try:
            extra_user_context = mock_factory.create_mock_user_context(
                user_id=user_id,
                websocket_connection_id="emergency_test_conn_21",
                session_id="emergency_session_21"
            )

            # This should trigger emergency cleanup and either succeed or fail with HARD LIMIT
            extra_manager = get_websocket_manager(user_context=extra_user_context)
            created_managers.append(extra_manager)

            final_count = factory.get_user_manager_count(user_id)
            print(f"✅ 21st manager created successfully! Final count: {final_count}")
            print("💡 Emergency cleanup appears to be working correctly")
            return False  # Bug not reproduced

        except RuntimeError as e:
            error_message = str(e)
            print(f"🚨 RuntimeError caught: {error_message}")

            if "HARD LIMIT" in error_message and "still over limit after cleanup" in error_message:
                print("🎯 BUG CONFIRMED: Emergency cleanup failure reproduced!")
                print(f"   Error details: {error_message}")

                # Extract details
                final_count = factory.get_user_manager_count(user_id)
                print(f"   Final manager count: {final_count}")
                print(f"   Expected: Zombie managers should have been cleaned up")
                print(f"   Reality: Emergency cleanup failed to remove {zombie_count} zombie managers")

                return True  # Bug successfully reproduced
            else:
                print(f"❓ Different RuntimeError: {error_message}")
                return False

        except Exception as e:
            print(f"❓ Unexpected exception: {type(e).__name__}: {e}")
            return False

    finally:
        # Cleanup
        factory.max_managers_per_user = original_limit

        # Try to cleanup managers
        for manager in created_managers:
            try:
                if hasattr(manager, 'cleanup_all_connections'):
                    # Can't use await in non-async function, so skip detailed cleanup
                    pass
            except:
                pass

        # Clear factory state
        if hasattr(factory, '_active_managers'):
            factory._active_managers.clear()
        if hasattr(factory, '_user_manager_keys'):
            factory._user_manager_keys.clear()


async def test_emergency_cleanup_async():
    """Async version of the emergency cleanup test."""
    print("\n🔍 Testing Emergency Cleanup Failure Bug (Async)")
    print("=" * 55)

    # Get factory and configure
    factory = get_websocket_manager_factory()
    original_limit = factory.max_managers_per_user
    factory.max_managers_per_user = 20

    mock_factory = SSotMockFactory()
    user_id = "async_emergency_test_user"
    created_managers = []

    try:
        # Create 20 managers
        print("📊 Creating 20 managers at limit...")
        for i in range(20):
            user_context = mock_factory.create_mock_user_context(
                user_id=user_id,
                websocket_connection_id=f"async_conn_{i}",
                session_id=f"async_session_{i}"
            )

            manager = get_websocket_manager(user_context=user_context)
            created_managers.append(manager)

        current_count = factory.get_user_manager_count(user_id)
        print(f"📈 Created {current_count} managers")

        # Make zombies
        zombie_count = 10
        print(f"🧟 Creating {zombie_count} zombie managers...")

        for i in range(zombie_count):
            manager = created_managers[i]
            if hasattr(manager, '_connections'):
                manager._connections.clear()
            if hasattr(manager, '_is_active'):
                manager._is_active = False
            if hasattr(manager, '_last_activity_time'):
                manager._last_activity_time = time.time() - 7200  # 2 hours ago

        # Test emergency cleanup directly
        print("🧪 Testing emergency cleanup directly...")

        try:
            cleaned_count = await factory._emergency_cleanup_user_managers(
                user_id,
                CleanupLevel.AGGRESSIVE
            )

            post_cleanup_count = factory.get_user_manager_count(user_id)

            print(f"🧹 Cleanup completed: {cleaned_count} managers cleaned")
            print(f"📊 Post-cleanup count: {post_cleanup_count}")

            # If cleanup was effective, we should have removed most zombies
            if post_cleanup_count <= 20 - zombie_count + 2:  # Allow some margin
                print("✅ Emergency cleanup appears to be working")
                return False
            else:
                zombies_remaining = post_cleanup_count - (20 - zombie_count)
                print(f"🚨 BUG CONFIRMED: Emergency cleanup ineffective!")
                print(f"   Zombies that should have been cleaned: {zombie_count}")
                print(f"   Zombies actually cleaned: {max(0, zombie_count - zombies_remaining)}")
                print(f"   Zombies still remaining: {zombies_remaining}")
                return True

        except Exception as e:
            print(f"❌ Emergency cleanup failed with exception: {e}")
            return True

    finally:
        # Cleanup
        factory.max_managers_per_user = original_limit

        for manager in created_managers:
            try:
                if hasattr(manager, 'cleanup_all_connections'):
                    await manager.cleanup_all_connections()
            except:
                pass

        if hasattr(factory, '_active_managers'):
            factory._active_managers.clear()
        if hasattr(factory, '_user_manager_keys'):
            factory._user_manager_keys.clear()


def main():
    """Main function to run all tests."""
    print("🔬 WebSocket Manager Emergency Cleanup Bug Proof")
    print("=" * 60)
    print("This script tests for the emergency cleanup failure bug that causes:")
    print("- HARD LIMIT: User still over limit after cleanup (20/20) errors")
    print("- Users permanently blocked from new WebSocket connections")
    print("- Resource exhaustion cascading to other users")
    print()

    # Test 1: Synchronous version
    print("🧪 TEST 1: Synchronous Emergency Cleanup Test")
    sync_result = test_emergency_cleanup_failure()

    # Test 2: Asynchronous version
    print("\n🧪 TEST 2: Asynchronous Emergency Cleanup Test")
    async_result = asyncio.run(test_emergency_cleanup_async())

    # Summary
    print("\n📋 TEST RESULTS SUMMARY")
    print("=" * 30)

    if sync_result or async_result:
        print("🚨 BUG CONFIRMED: Emergency cleanup failure bug exists!")
        print("   The WebSocket manager emergency cleanup system is broken.")
        print("   This leads to users being permanently blocked from connections.")
        print("   Impact: $500K+ ARR at risk due to chat functionality failures.")
        print("\n✅ MISSION ACCOMPLISHED: Bug successfully reproduced.")
        return 1  # Exit code indicating bug found
    else:
        print("✅ Bug not reproduced: Emergency cleanup appears to be working.")
        print("   Either the bug has been fixed or test conditions are insufficient.")
        print("   Consider running integration tests with real WebSocket connections.")
        return 0  # Exit code indicating no bug found


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)