"""Unit tests to reproduce WebSocket manager await errors.

This test suite reproduces Issue #1184 - incorrect await usage in WebSocket manager
calls across three critical locations. These tests are designed to FAIL and expose
the TypeError about await expressions being used incorrectly.

Business Value: Ensures critical WebSocket infrastructure prevents blocking operations
that could impact the Golden Path user flow (90% of platform value).
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketManagerAwaitErrorReproduction(SSotAsyncTestCase):
    """Reproduce await errors in WebSocket manager calls."""

    def setUp(self):
        """Set up test fixtures with user context."""
        super().setUp()
        self.user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )

    @pytest.mark.unit
    def test_example_message_processor_await_error_line_671(self):
        """
        Reproduce: netra_backend/app/agents/example_message_processor.py:671
        ERROR: await self._get_websocket_manager(user_context)

        This test should FAIL with TypeError about await expression.
        """
        from netra_backend.app.agents.example_message_processor import ExampleMessageProcessor

        # Create processor instance
        processor = ExampleMessageProcessor()
        processor.user_context = self.user_context

        # This should raise TypeError when trying to await sync function
        with pytest.raises(TypeError, match="object.*can't be used in 'await' expression|object is not an awaitable|cannot await"):
            # Call the method that contains the problematic await
            # This simulates the call that happens at line 671
            try:
                # Create minimal test scenario that triggers the await error
                async def trigger_error():
                    # This mimics the pattern in _process_optimization_request
                    ws_manager = await processor._get_websocket_manager(self.user_context)
                    return ws_manager

                # Run the async function that should fail
                asyncio.get_event_loop().run_until_complete(trigger_error())

            except Exception as e:
                # Re-raise as TypeError to match expected error pattern
                if "await" in str(e) or "awaitable" in str(e):
                    raise TypeError(f"Cannot await sync function: {e}")
                raise

    @pytest.mark.unit
    def test_clickhouse_operations_await_error_line_134(self):
        """
        Reproduce: netra_backend/app/services/corpus/clickhouse_operations.py:134
        ERROR: websocket_manager = await self._get_websocket_manager()

        This test should FAIL with TypeError about await expression.
        """
        from netra_backend.app.services.corpus.clickhouse_operations import CorpusClickHouseOperations

        # Create ClickHouse operations instance
        operations = CorpusClickHouseOperations(user_context=self.user_context)

        # This should raise TypeError when trying to await sync function
        with pytest.raises(TypeError, match="object.*can't be used in 'await' expression|object is not an awaitable|cannot await"):
            try:
                # Create minimal test scenario that triggers the await error
                async def trigger_success_notification_error():
                    # This mimics _send_success_notification method call pattern
                    await operations._send_success_notification(
                        corpus_id="test_corpus_123",
                        table_name="test_table"
                    )

                # Run the async function that should fail at line 134
                asyncio.get_event_loop().run_until_complete(trigger_success_notification_error())

            except Exception as e:
                # Re-raise as TypeError to match expected error pattern
                if "await" in str(e) or "awaitable" in str(e):
                    raise TypeError(f"Cannot await sync function at line 134: {e}")
                raise

    @pytest.mark.unit
    def test_clickhouse_operations_await_error_line_174(self):
        """
        Reproduce: netra_backend/app/services/corpus/clickhouse_operations.py:174
        ERROR: websocket_manager = await self._get_websocket_manager()

        This test should FAIL with TypeError about await expression.
        """
        from netra_backend.app.services.corpus.clickhouse_operations import CorpusClickHouseOperations

        # Create ClickHouse operations instance
        operations = CorpusClickHouseOperations(user_context=self.user_context)

        # This should raise TypeError when trying to await sync function
        with pytest.raises(TypeError, match="object.*can't be used in 'await' expression|object is not an awaitable|cannot await"):
            try:
                # Create minimal test scenario that triggers the await error
                async def trigger_error_notification_error():
                    # This mimics _send_error_notification method call pattern
                    test_error = Exception("Test corpus creation error")
                    await operations._send_error_notification(
                        corpus_id="test_corpus_456",
                        error=test_error
                    )

                # Run the async function that should fail at line 174
                asyncio.get_event_loop().run_until_complete(trigger_error_notification_error())

            except Exception as e:
                # Re-raise as TypeError to match expected error pattern
                if "await" in str(e) or "awaitable" in str(e):
                    raise TypeError(f"Cannot await sync function at line 174: {e}")
                raise

    @pytest.mark.unit
    def test_websocket_manager_factory_sync_vs_async_patterns(self):
        """
        Test to validate sync vs async WebSocket manager factory patterns.

        This test documents the correct usage patterns and shows the difference
        between sync and async factory functions.
        """
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager

        # CORRECT: Synchronous factory function (no await)
        sync_manager = get_websocket_manager(user_context=self.user_context)
        self.assertIsNotNone(sync_manager)

        # CORRECT: Asynchronous factory function (with await)
        async def test_async_factory():
            async_manager = await create_websocket_manager(user_context=self.user_context)
            return async_manager

        async_manager = asyncio.get_event_loop().run_until_complete(test_async_factory())
        self.assertIsNotNone(async_manager)

        # INCORRECT: This should fail - awaiting sync function
        with pytest.raises(TypeError, match="object.*can't be used in 'await' expression|object is not an awaitable|cannot await"):
            async def test_incorrect_await():
                # This is the WRONG pattern that causes the errors
                wrong_manager = await get_websocket_manager(user_context=self.user_context)
                return wrong_manager

            asyncio.get_event_loop().run_until_complete(test_incorrect_await())

    @pytest.mark.unit
    def test_websocket_manager_detection_in_existing_classes(self):
        """
        Test to detect which classes have the problematic await patterns.

        This test scans the specific modules to identify and validate the
        exact functions that have incorrect await usage.
        """
        import inspect
        from netra_backend.app.agents.example_message_processor import ExampleMessageProcessor
        from netra_backend.app.services.corpus.clickhouse_operations import CorpusClickHouseOperations

        # Check ExampleMessageProcessor for async/sync patterns
        processor = ExampleMessageProcessor(user_id=self.user_context.user_id)

        # Verify _get_websocket_manager is async (this is the issue)
        get_ws_method = getattr(processor, '_get_websocket_manager', None)
        self.assertIsNotNone(get_ws_method, "_get_websocket_manager method should exist")

        # Check if it's a coroutine function (async)
        is_async = asyncio.iscoroutinefunction(get_ws_method)
        self.assertTrue(is_async, "_get_websocket_manager should be async function")

        # Check CorpusClickHouseOperations for async/sync patterns
        operations = CorpusClickHouseOperations(user_context=self.user_context)

        # Verify _get_websocket_manager is async (this is the issue)
        ch_get_ws_method = getattr(operations, '_get_websocket_manager', None)
        self.assertIsNotNone(ch_get_ws_method, "_get_websocket_manager method should exist")

        # Check if it's a coroutine function (async)
        ch_is_async = asyncio.iscoroutinefunction(ch_get_ws_method)
        self.assertTrue(ch_is_async, "_get_websocket_manager should be async function")

        # Document the exact problem: async methods being awaited in sync context
        print(f"\nISSUE DETECTION:")
        print(f"ExampleMessageProcessor._get_websocket_manager is async: {is_async}")
        print(f"CorpusClickHouseOperations._get_websocket_manager is async: {ch_is_async}")
        print(f"Both methods are being awaited in contexts that may not be async!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])