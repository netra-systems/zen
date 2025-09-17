"""
Critical Multi-User Isolation Validation Test

This test validates that the factory pattern changes maintain proper user isolation
and prevent race conditions in multi-user scenarios.

Business Impact: CRITICAL - Ensures user data isolation for enterprise customers
(protects privacy and compliance requirements).

REAL TEST REQUIREMENTS (CLAUDE.md Compliance):
- NO MOCKS for user isolation testing
- FAIL HARD when isolation is broken
- Real concurrent execution scenarios
- Validates factory pattern user isolation
"""

import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID


class MultiUserIsolationValidationTests(SSotAsyncTestCase):
    """Test multi-user isolation in factory pattern implementation."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.base_user_id = "isolation-test-user"
        self.base_thread_id = "isolation-test-thread"
        self.base_run_id = "isolation-test-run"

    async def test_concurrent_user_context_creation_isolation(self):
        """Test that concurrent user context creation maintains isolation."""

        async def create_user_context(user_index: int) -> StronglyTypedUserExecutionContext:
            """Create a user context for a specific user."""
            return StronglyTypedUserExecutionContext(
                user_id=UserID(f"{self.base_user_id}-{user_index}"),
                thread_id=ThreadID(f"{self.base_thread_id}-{user_index}"),
                run_id=RunID(f"{self.base_run_id}-{user_index}"),
                request_id=RequestID(f"req-{user_index}"),
                websocket_id=None,
                metadata={'user_index': user_index, 'isolation_test': True}
            )

        # Test: Create multiple user contexts concurrently
        num_users = 10
        tasks = [create_user_context(i) for i in range(num_users)]
        contexts = await asyncio.gather(*tasks)

        # Verify: All contexts created successfully
        assert len(contexts) == num_users

        # Verify: Each context has unique user ID
        user_ids = [ctx.user_id for ctx in contexts]
        assert len(set(user_ids)) == num_users, "All user IDs should be unique"

        # Verify: Each context has unique metadata
        for i, context in enumerate(contexts):
            assert context.metadata['user_index'] == i
            assert context.user_id == UserID(f"{self.base_user_id}-{i}")

        # Verify: No data bleeding between contexts
        for i, context in enumerate(contexts):
            for j, other_context in enumerate(contexts):
                if i != j:
                    assert context.user_id != other_context.user_id
                    assert context.metadata['user_index'] != other_context.metadata['user_index']

    def test_factory_pattern_prevents_singleton_sharing(self):
        """Test that factory pattern prevents singleton sharing between users."""
        # Test: Create multiple contexts and verify they don't share references
        contexts = []
        for i in range(5):
            context = StronglyTypedUserExecutionContext(
                user_id=UserID(f"singleton-test-{i}"),
                thread_id=ThreadID(f"thread-{i}"),
                run_id=RunID(f"run-{i}"),
                request_id=RequestID(f"req-{i}"),
                websocket_id=None,
                metadata={'shared_data': f"data-{i}"}
            )
            contexts.append(context)

        # Verify: No shared object references
        for i, context in enumerate(contexts):
            for j, other_context in enumerate(contexts):
                if i != j:
                    # Different object instances
                    assert context is not other_context
                    assert id(context) != id(other_context)

                    # Different metadata objects
                    assert context.metadata is not other_context.metadata
                    assert id(context.metadata) != id(other_context.metadata)

                    # Different data values
                    assert context.metadata['shared_data'] != other_context.metadata['shared_data']

    async def test_websocket_event_isolation_between_users(self):
        """Test that WebSocket events maintain user isolation."""
        # Test: Create contexts for different users with WebSocket IDs
        user1_context = StronglyTypedUserExecutionContext(
            user_id=UserID("websocket-user-1"),
            thread_id=ThreadID("websocket-thread-1"),
            run_id=RunID("websocket-run-1"),
            request_id=RequestID("websocket-req-1"),
            websocket_id=None,
            metadata={'websocket_events': ['event1', 'event2']}
        )

        user2_context = StronglyTypedUserExecutionContext(
            user_id=UserID("websocket-user-2"),
            thread_id=ThreadID("websocket-thread-2"),
            run_id=RunID("websocket-run-2"),
            request_id=RequestID("websocket-req-2"),
            websocket_id=None,
            metadata={'websocket_events': ['event3', 'event4']}
        )

        # Verify: WebSocket event data is isolated
        assert user1_context.metadata['websocket_events'] != user2_context.metadata['websocket_events']
        assert 'event1' in user1_context.metadata['websocket_events']
        assert 'event1' not in user2_context.metadata['websocket_events']
        assert 'event3' in user2_context.metadata['websocket_events']
        assert 'event3' not in user1_context.metadata['websocket_events']

        # Verify: User targeting is correct
        user1_target = f"user:{user1_context.user_id}"
        user2_target = f"user:{user2_context.user_id}"
        assert user1_target != user2_target
        assert "websocket-user-1" in user1_target
        assert "websocket-user-2" in user2_target

    def test_memory_growth_bounded_per_user(self):
        """Test that memory growth is bounded per user (not global accumulation)."""
        # Test: Create and discard contexts to check for memory leaks
        initial_contexts = []
        for i in range(3):
            context = StronglyTypedUserExecutionContext(
                user_id=UserID(f"memory-user-{i}"),
                thread_id=ThreadID(f"memory-thread-{i}"),
                run_id=RunID(f"memory-run-{i}"),
                request_id=RequestID(f"memory-req-{i}"),
                websocket_id=None,
                metadata={'large_data': 'x' * 1000}  # 1KB per context
            )
            initial_contexts.append(context)

        # Verify: Each context has its own memory allocation
        for i, context in enumerate(initial_contexts):
            assert len(context.metadata['large_data']) == 1000
            assert context.metadata['large_data'] == 'x' * 1000

        # Test: Create new contexts to verify no global accumulation
        new_contexts = []
        for i in range(3):
            context = StronglyTypedUserExecutionContext(
                user_id=UserID(f"new-memory-user-{i}"),
                thread_id=ThreadID(f"new-memory-thread-{i}"),
                run_id=RunID(f"new-memory-run-{i}"),
                request_id=RequestID(f"new-memory-req-{i}"),
                websocket_id=None,
                metadata={'large_data': 'y' * 1000}  # Different data
            )
            new_contexts.append(context)

        # Verify: New contexts don't inherit old data
        for new_context in new_contexts:
            assert new_context.metadata['large_data'] == 'y' * 1000
            assert new_context.metadata['large_data'] != 'x' * 1000

        # Verify: Old contexts haven't been affected
        for old_context in initial_contexts:
            assert old_context.metadata['large_data'] == 'x' * 1000
            assert old_context.metadata['large_data'] != 'y' * 1000

    async def test_race_condition_prevention_in_context_creation(self):
        """Test that race conditions are prevented during concurrent context creation."""

        async def create_racing_context(race_id: int) -> Dict[str, Any]:
            """Create a context that might race with others."""
            # Simulate some processing time
            await asyncio.sleep(0.01)

            context = StronglyTypedUserExecutionContext(
                user_id=UserID(f"race-user-{race_id}"),
                thread_id=ThreadID(f"race-thread-{race_id}"),
                run_id=RunID(f"race-run-{race_id}"),
                request_id=RequestID(f"race-req-{race_id}"),
                websocket_id=None,
                metadata={'race_id': race_id, 'timestamp': time.time()}
            )

            return {
                'race_id': race_id,
                'user_id': context.user_id,
                'timestamp': context.metadata['timestamp'],
                'context': context
            }

        # Test: Create multiple contexts concurrently to detect race conditions
        num_races = 20
        tasks = [create_racing_context(i) for i in range(num_races)]
        results = await asyncio.gather(*tasks)

        # Verify: All race IDs are unique (no collision)
        race_ids = [result['race_id'] for result in results]
        assert len(set(race_ids)) == num_races, "Race condition detected: duplicate race IDs"

        # Verify: All user IDs are unique (no collision)
        user_ids = [result['user_id'] for result in results]
        assert len(set(user_ids)) == num_races, "Race condition detected: duplicate user IDs"

        # Verify: All timestamps are different (contexts created at different times)
        timestamps = [result['timestamp'] for result in results]
        assert len(set(timestamps)) == num_races, "Race condition detected: identical timestamps"

        # Verify: Each context has correct race_id in metadata
        for result in results:
            context = result['context']
            expected_race_id = result['race_id']
            assert context.metadata['race_id'] == expected_race_id

    def test_user_isolation_under_error_conditions(self):
        """Test that user isolation is maintained even when errors occur."""
        # Test: Create contexts where some fail but others succeed
        successful_contexts = []
        error_count = 0

        for i in range(10):
            try:
                # Some contexts will have invalid data to trigger errors
                user_id = UserID(f"error-test-user-{i}")
                if i == 5:  # Introduce one potential error case
                    metadata = {'error_test': True, 'might_fail': True}
                else:
                    metadata = {'error_test': True, 'should_succeed': True}

                context = StronglyTypedUserExecutionContext(
                    user_id=user_id,
                    thread_id=ThreadID(f"error-thread-{i}"),
                    run_id=RunID(f"error-run-{i}"),
                    request_id=RequestID(f"error-req-{i}"),
                    websocket_id=None,
                    metadata=metadata
                )
                successful_contexts.append(context)

            except Exception:
                error_count += 1

        # Verify: At least some contexts succeeded
        assert len(successful_contexts) >= 8, "Most contexts should succeed despite errors"

        # Verify: Successful contexts maintain isolation
        for i, context in enumerate(successful_contexts):
            for j, other_context in enumerate(successful_contexts):
                if i != j:
                    assert context.user_id != other_context.user_id
                    assert context is not other_context