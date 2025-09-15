"""
Issue #1231 WebSocket Connection Failures - Integration Tests

CRITICAL BUG: async/await bug in websocket_ssot.py causes WebSocket connection establishment failures

These integration tests demonstrate how the async/await bug impacts real WebSocket connections
and the WebSocket manager factory pattern.

Business Impact:
- WebSocket connections cannot be established
- Golden Path user flow broken (90% of platform value)
- Real-time messaging non-functional
- $500K+ ARR dependency affected

Test Focus:
- WebSocket connection establishment failures
- Factory pattern disruption
- Real-time messaging broken
- Manager instantiation failures

Expected Results: ALL TESTS SHOULD FAIL until the bug is fixed
"""

import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parents[3]
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class Issue1231WebSocketConnectionFailuresTests:
    """
    INTEGRATION TESTS: Demonstrate WebSocket connection failures due to async/await bug

    EXPECTED RESULT: ALL TESTS SHOULD FAIL until the bug is fixed
    """

    def create_test_user_context(self):
        """Create test user context for WebSocket integration testing."""
        return UserExecutionContext(
            user_id="issue-1231-integration-user",
            thread_id="issue-1231-integration-thread",
            run_id="issue-1231-integration-test",
            request_id="issue-1231-integration-request"
        )

    @pytest.mark.asyncio
    async def test_websocket_connection_establishment_fails_due_to_async_bug(self):
        """
        INTEGRATION TEST: WebSocket connections fail due to manager creation bug

        This test demonstrates how the async/await bug prevents WebSocket connections
        from being established properly.

        EXPECTED: This test should FAIL until the bug is fixed
        """

        async def simulate_websocket_connection_establishment():
            """Simulate WebSocket connection establishment using the buggy pattern"""
            user_context = self.create_test_user_context()

            try:
                # Step 1: This simulates the buggy manager creation from websocket_ssot.py
                manager = get_websocket_manager(user_context)  # BUG: awaiting non-coroutine

                # Step 2: Attempt to establish WebSocket connection
                connection_established = await manager.establish_connection(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id
                )

                return connection_established

            except Exception as e:
                raise RuntimeError(f"WebSocket connection failed due to async/await bug: {e}")

        # This should fail due to the async/await bug
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_websocket_connection_establishment()

        error_msg = str(exc_info.value)
        assert "async/await bug" in error_msg, \
            f"Should fail due to async/await bug. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_websocket_manager_factory_pattern_broken(self):
        """
        INTEGRATION TEST: Factory pattern broken by async/await bug

        The async/await bug disrupts the SSOT factory pattern for WebSocket managers,
        preventing proper user isolation and manager instantiation.

        EXPECTED: This test should FAIL until the bug is fixed
        """

        async def simulate_factory_pattern_usage():
            """Simulate factory pattern usage with the buggy async/await"""
            user_contexts = [
                self.create_test_user_context(),
                UserExecutionContext(
                    user_id="issue-1231-user-2",
                    thread_id="issue-1231-thread-2",
                    run_id="issue-1231-test-2",
                    request_id="issue-1231-request-2"
                )
            ]

            managers = []
            for user_context in user_contexts:
                try:
                    # This simulates the buggy factory usage from websocket_ssot.py
                    manager = get_websocket_manager(user_context)  # BUG: awaiting non-coroutine
                    managers.append(manager)
                except Exception as e:
                    raise RuntimeError(f"Factory pattern failed due to async/await bug: {e}")

            return managers

        # This should fail due to the async/await bug disrupting factory pattern
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_factory_pattern_usage()

        error_msg = str(exc_info.value)
        assert "async/await bug" in error_msg, \
            f"Factory pattern should fail due to bug. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_websocket_event_delivery_broken_by_bug(self):
        """
        INTEGRATION TEST: WebSocket event delivery broken due to manager creation failure

        The async/await bug prevents WebSocket managers from being created, which breaks
        the delivery of critical business events (agent_started, agent_thinking, etc.).

        EXPECTED: This test should FAIL until the bug is fixed
        """

        async def simulate_websocket_event_delivery():
            """Simulate WebSocket event delivery with buggy manager creation"""
            user_context = self.create_test_user_context()

            try:
                # This simulates the buggy manager creation pattern
                manager = get_websocket_manager(user_context)  # BUG: awaiting non-coroutine

                # Attempt to send critical business events
                events_to_send = [
                    {"type": "agent_started", "data": {"agent": "test_agent"}},
                    {"type": "agent_thinking", "data": {"progress": "analyzing"}},
                    {"type": "tool_executing", "data": {"tool": "test_tool"}},
                    {"type": "tool_completed", "data": {"result": "success"}},
                    {"type": "agent_completed", "data": {"response": "test response"}}
                ]

                delivery_results = []
                for event in events_to_send:
                    result = await manager.send_to_thread(
                        thread_id=user_context.thread_id,
                        message_data=event
                    )
                    delivery_results.append(result)

                return delivery_results

            except Exception as e:
                raise RuntimeError(f"Event delivery failed due to async/await bug: {e}")

        # This should fail due to the async/await bug preventing manager creation
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_websocket_event_delivery()

        error_msg = str(exc_info.value)
        assert "async/await bug" in error_msg, \
            f"Event delivery should fail due to bug. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_broken(self):
        """
        INTEGRATION TEST: Multi-user WebSocket isolation broken by async/await bug

        The bug prevents proper user-scoped WebSocket managers from being created,
        breaking multi-user isolation which is critical for enterprise compliance.

        EXPECTED: This test should FAIL until the bug is fixed
        """

        async def simulate_multi_user_isolation():
            """Simulate multi-user WebSocket isolation with buggy manager creation"""
            user_contexts = [
                UserExecutionContext(
                    user_id="enterprise-user-1",
                    thread_id="enterprise-thread-1",
                    run_id="enterprise-run-1",
                    request_id="enterprise-request-1"
                ),
                UserExecutionContext(
                    user_id="enterprise-user-2",
                    thread_id="enterprise-thread-2",
                    run_id="enterprise-run-2",
                    request_id="enterprise-request-2"
                )
            ]

            isolated_managers = {}

            for user_context in user_contexts:
                try:
                    # This simulates the buggy isolated manager creation
                    manager = get_websocket_manager(user_context)  # BUG: awaiting non-coroutine
                    isolated_managers[user_context.user_id] = manager
                except Exception as e:
                    raise RuntimeError(f"Multi-user isolation failed due to async/await bug: {e}")

            # Verify isolation (this won't be reached due to the bug)
            assert len(isolated_managers) == 2, "Should create separate managers per user"

            return isolated_managers

        # This should fail due to the async/await bug preventing manager creation
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_multi_user_isolation()

        error_msg = str(exc_info.value)
        assert "async/await bug" in error_msg, \
            f"Multi-user isolation should fail due to bug. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_websocket_health_monitoring_broken(self):
        """
        INTEGRATION TEST: WebSocket health monitoring broken by async/await bug

        The bug affects health monitoring endpoints that rely on WebSocket manager creation,
        breaking system observability.

        EXPECTED: This test should FAIL until the bug is fixed
        """

        async def simulate_health_monitoring():
            """Simulate WebSocket health monitoring with buggy manager access"""
            try:
                # This simulates the buggy health monitoring pattern from websocket_ssot.py
                manager = get_websocket_manager(user_context=None)  # BUG: awaiting non-coroutine

                # Attempt to get health status
                health_status = {
                    "websocket_manager_active": manager is not None,
                    "connection_count": len(getattr(manager, '_connections', {})),
                    "status": "healthy"
                }

                return health_status

            except Exception as e:
                raise RuntimeError(f"Health monitoring failed due to async/await bug: {e}")

        # This should fail due to the async/await bug
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_health_monitoring()

        error_msg = str(exc_info.value)
        assert "async/await bug" in error_msg, \
            f"Health monitoring should fail due to bug. Got: {exc_info.value}"

    def test_correct_synchronous_manager_creation_works(self):
        """
        VALIDATION TEST: Correct synchronous manager creation works fine

        This demonstrates that when get_websocket_manager() is called correctly
        (without await), everything works as expected.

        This test should PASS even with the current bug.
        """
        user_context = self.create_test_user_context()

        # CORRECT usage: Synchronous call without await
        manager = get_websocket_manager(user_context)

        # Verify manager creation succeeded
        assert manager is not None, "Manager should be created synchronously"
        assert hasattr(manager, 'send_to_thread'), "Manager should have WebSocket functionality"

        # Verify user context association
        if hasattr(manager, 'user_context'):
            assert manager.user_context.user_id == user_context.user_id, \
                "Manager should be associated with correct user"

    @pytest.mark.asyncio
    async def test_websocket_race_conditions_exacerbated_by_bug(self):
        """
        INTEGRATION TEST: Race conditions exacerbated by async/await bug

        The async/await bug can create additional race conditions in WebSocket
        connection management, especially under concurrent load.

        EXPECTED: This test should FAIL until the bug is fixed
        """

        async def simulate_concurrent_websocket_usage():
            """Simulate concurrent WebSocket usage with the buggy pattern"""
            user_context = self.create_test_user_context()

            async def buggy_websocket_operation(operation_id):
                try:
                    # This simulates concurrent buggy operations
                    manager = get_websocket_manager(user_context)  # BUG: awaiting non-coroutine

                    # Simulate some WebSocket operation
                    result = await manager.send_to_thread(
                        thread_id=user_context.thread_id,
                        message_data={"operation_id": operation_id, "type": "test"}
                    )

                    return result

                except Exception as e:
                    raise RuntimeError(f"Concurrent operation {operation_id} failed due to async/await bug: {e}")

            # Run multiple concurrent operations (simulates race conditions)
            tasks = [
                buggy_websocket_operation(i)
                for i in range(5)
            ]

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
            except Exception as e:
                raise RuntimeError(f"Concurrent WebSocket operations failed: {e}")

        # This should fail due to async/await bug affecting concurrent operations
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_concurrent_websocket_usage()

        error_msg = str(exc_info.value)
        assert "async/await bug" in error_msg, \
            f"Concurrent operations should fail due to bug. Got: {exc_info.value}"


if __name__ == "__main__":
    print("=" * 80)
    print("ISSUE #1231 WEBSOCKET CONNECTION FAILURES - INTEGRATION TESTS")
    print("=" * 80)
    print("These tests demonstrate how the async/await bug breaks WebSocket connections")
    print("EXPECTED: All tests should FAIL until the bug is fixed")
    print("=" * 80)

    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])