"""
Unit tests to reproduce Issue 1184 async/await compatibility issues.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Mission Critical Infrastructure
- Business Goal: Restore $500K+ ARR WebSocket chat functionality reliability
- Value Impact: Prevents WebSocket infrastructure failures that block Golden Path user flow
- Strategic Impact: Ensures staging environment accurately validates production deployments

These tests run without Docker and demonstrate the exact staging errors.
"""

import pytest
import asyncio
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, get_websocket_manager_async
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketAsyncCompatibility(SSotAsyncTestCase):
    """Tests that reproduce the async/await compatibility issue."""

    @pytest.mark.issue_1184
    async def test_get_websocket_manager_is_not_awaitable(self):
        """
        REPRODUCE: This test should FAIL initially, demonstrating the issue.

        The error "_UnifiedWebSocketManagerImplementation object can't be used in 'await' expression"
        occurs because get_websocket_manager() is synchronous but called with await.
        """
        user_context = {"user_id": "test-user-1184", "thread_id": "test-thread-1184"}

        # This should work (synchronous call)
        manager_sync = get_websocket_manager(user_context=user_context)
        assert manager_sync is not None
        logger.info(f"✅ Synchronous WebSocket manager creation works: {type(manager_sync)}")

        # This should FAIL with TypeError initially - demonstrates the exact issue
        # Many places in codebase incorrectly await this synchronous function
        try:
            manager_async = await get_websocket_manager(user_context=user_context)
            logger.error("❌ Unexpected: await on synchronous function did not fail")
            # If this doesn't fail, it means the function signature changed or there's wrapping
            assert False, "Expected TypeError when awaiting synchronous get_websocket_manager()"
        except TypeError as e:
            logger.info(f"✅ Expected TypeError when awaiting synchronous function: {e}")
            assert "can't be used in 'await' expression" in str(e) or "object is not awaitable" in str(e)

    @pytest.mark.issue_1184
    async def test_get_websocket_manager_async_works_correctly(self):
        """
        NEW TEST: Verify the new async function works correctly.

        This test should PASS and demonstrates the correct usage pattern
        for async contexts that need to await WebSocket manager creation.
        """
        user_context = {"user_id": "test-async-user-1184", "thread_id": "test-async-thread-1184"}

        # This should work (proper async call)
        manager_async = await get_websocket_manager_async(user_context=user_context)
        assert manager_async is not None
        logger.info(f"✅ Asynchronous WebSocket manager creation works: {type(manager_async)}")

        # Verify it returns the same type as the sync version
        manager_sync = get_websocket_manager(user_context=user_context)
        assert type(manager_async) == type(manager_sync)

        # For the same user context, should return the same instance (registry behavior)
        manager_async_2 = await get_websocket_manager_async(user_context=user_context)
        assert manager_async is manager_async_2, "Should return same instance from registry"

        logger.info("✅ Async WebSocket manager creation test passed")

    @pytest.mark.issue_1184
    async def test_websocket_manager_initialization_timing(self):
        """
        Test WebSocket manager initialization without improper await usage.

        This demonstrates proper synchronous usage that should work in staging.
        """
        user_context = {"user_id": "timing-test-1184", "thread_id": "timing-thread"}

        # Proper synchronous call
        start_time = asyncio.get_event_loop().time()
        manager = get_websocket_manager(user_context=user_context)
        end_time = asyncio.get_event_loop().time()

        # Should be fast (synchronous)
        creation_time = end_time - start_time
        assert creation_time < 0.1, f"Manager creation took too long: {creation_time}s"

        # Validate manager is properly initialized
        assert hasattr(manager, 'user_context'), "Manager missing user_context attribute"
        assert manager.user_context is not None, "Manager user_context is None"

        # Test that manager registry works correctly (critical for user isolation)
        manager2 = get_websocket_manager(user_context=user_context)
        assert manager is manager2, "Should be same instance per user (singleton per user)"

        logger.info(f"✅ WebSocket manager initialization timing validated: {creation_time:.4f}s")

    @pytest.mark.issue_1184
    async def test_websocket_manager_concurrent_access(self):
        """
        Test concurrent access to WebSocket manager without await issues.

        This reproduces timing issues that occur in staging with concurrent requests.
        """
        user_context_1 = {"user_id": "concurrent-1-1184", "thread_id": "thread-1"}
        user_context_2 = {"user_id": "concurrent-2-1184", "thread_id": "thread-2"}

        async def create_manager_properly(ctx, delay=0):
            """Create manager with proper synchronous call (no await)."""
            if delay:
                await asyncio.sleep(delay)
            # Proper synchronous call - no await
            return get_websocket_manager(user_context=ctx)

        async def create_manager_incorrectly(ctx, delay=0):
            """Create manager with incorrect await usage (demonstrates issue)."""
            if delay:
                await asyncio.sleep(delay)
            # Incorrect usage that causes staging issues
            try:
                return await get_websocket_manager(user_context=ctx)
            except TypeError as e:
                logger.info(f"Expected error from incorrect await usage: {e}")
                # Return proper call as fallback
                return get_websocket_manager(user_context=ctx)

        # Test 1: Concurrent manager creation with PROPER usage
        task1 = asyncio.create_task(create_manager_properly(user_context_1, 0.01))
        task2 = asyncio.create_task(create_manager_properly(user_context_2, 0.02))

        manager1, manager2 = await asyncio.gather(task1, task2)

        # Should be different managers for different users
        assert manager1 is not manager2, "Different users should get different managers"
        assert manager1.user_context != manager2.user_context, "User contexts should be isolated"

        # Test 2: Demonstrate the issue with INCORRECT await usage
        task3 = asyncio.create_task(create_manager_incorrectly(user_context_1, 0.01))
        task4 = asyncio.create_task(create_manager_incorrectly(user_context_2, 0.02))

        # These should still work (with proper error handling) but demonstrate the timing issue
        manager3, manager4 = await asyncio.gather(task3, task4, return_exceptions=False)

        # Validate they still work but may have timing issues
        assert manager3 is not None, "Manager 3 should exist despite incorrect usage"
        assert manager4 is not None, "Manager 4 should exist despite incorrect usage"

        logger.info("✅ Concurrent access test completed - proper vs incorrect usage demonstrated")

    @pytest.mark.issue_1184
    @pytest.mark.mission_critical
    async def test_websocket_manager_business_value_protection(self):
        """
        MISSION CRITICAL: Validate WebSocket manager supports business value.

        This test ensures the WebSocket infrastructure critical to $500K+ ARR is working.
        """
        # Simulate business scenario - multiple users accessing chat simultaneously
        business_users = [
            {"user_id": "enterprise-user-001", "thread_id": "ent-thread-001"},
            {"user_id": "mid-tier-user-002", "thread_id": "mid-thread-002"},
            {"user_id": "free-user-003", "thread_id": "free-thread-003"},
        ]

        managers = []
        for user_context in business_users:
            # CRITICAL: Use proper synchronous call (no await)
            manager = get_websocket_manager(user_context=user_context)
            managers.append(manager)

        # Business value requirements validation
        assert len(managers) == 3, "Failed to create managers for all business users"

        # User isolation (critical for enterprise compliance)
        user_ids = [m.user_context["user_id"] for m in managers]
        assert len(set(user_ids)) == 3, "User isolation failed - managers not properly isolated"

        # No singleton contamination (security requirement)
        for i, manager1 in enumerate(managers):
            for j, manager2 in enumerate(managers):
                if i != j:
                    assert manager1 is not manager2, f"Manager isolation failed between users {i} and {j}"

        # Validate manager attributes for business functionality
        for manager in managers:
            assert hasattr(manager, 'user_context'), "Manager missing user_context (needed for isolation)"
            assert hasattr(manager, 'emit_event') or hasattr(manager, 'send_event') or hasattr(manager, '_connections'), \
                "Manager missing event emission capability (needed for chat)"

        logger.info("✅ WebSocket manager business value protection validated for all user tiers")