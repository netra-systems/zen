"Integration tests for WebSocket manager sync/async factory patterns.

This test suite validates proper WebSocket manager creation patterns and exposes
issues with mixed sync/async usage in integration scenarios. These tests use
real services (no Docker required) to validate the Golden Path user flow.

Business Value: Validates critical WebSocket infrastructure that enables
AI chat interactions (90% of platform value).
""

import pytest
import asyncio
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.configuration.base import get_config


class TestWebSocketManagerSyncAsyncIntegration(SSotAsyncTestCase):
    Integration tests for WebSocket manager factory patterns."

    def setUp(self):
        "Set up integration test environment.
        super().setUp()
        self.config = get_config()
        self.user_context = UserExecutionContext(
            user_id=integration_test_user","
            thread_id=integration_test_thread,
            run_id=integration_test_run"
        )

    @pytest.mark.integration
    async def test_websocket_manager_creation_patterns_integration(self):
    "
        Test WebSocket manager creation using different factory patterns.

        This test validates that both sync and async factory functions
        work correctly in an integration environment.
        "
        # Test synchronous factory pattern
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        sync_manager = get_websocket_manager(user_context=self.user_context)
        self.assertIsNotNone(sync_manager)
        self.assertEqual(sync_manager.user_context.user_id, self.user_context.user_id)

        # Test asynchronous factory pattern
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager

        async_manager = await create_websocket_manager(user_context=self.user_context)
        self.assertIsNotNone(async_manager)
        self.assertEqual(async_manager.user_context.user_id, self.user_context.user_id)

        # Verify both managers are functional
        self.assertTrue(hasattr(sync_manager, 'send_message_to_user'))
        self.assertTrue(hasattr(async_manager, 'send_message_to_user'))

    @pytest.mark.integration
    async def test_example_message_processor_websocket_integration(self):
        "
        Test ExampleMessageProcessor WebSocket integration to expose await errors.

        This test attempts to use ExampleMessageProcessor in a realistic scenario
        to trigger the await error at line 671.
"
        from netra_backend.app.agents.example_message_processor import ExampleMessageProcessor

        processor = ExampleMessageProcessor(user_id=self.user_context.user_id)
        processor.user_context = self.user_context

        # Test the websocket manager creation method directly
        try:
            # This should work if _get_websocket_manager is properly async
            ws_manager = await processor._get_websocket_manager(self.user_context)
            self.assertIsNotNone(ws_manager)

        except TypeError as e:
            # If we get TypeError about await, this confirms the issue
            if "await in str(e) or awaitable in str(e):
                self.fail(fISSUE #1184 CONFIRMED: {e})
            else:
                raise

        # Test a realistic optimization request scenario
        try:
            # Create a test message that would trigger WebSocket notifications
            test_request = {
                'type': 'optimization',
                'content': 'Test optimization request',
                'user_id': self.user_context.user_id
            }

            # This might trigger the await error in _process_optimization_request
            result = await processor.process_message(test_request)

            # If we reach here, the await issue might be fixed or bypassed
            self.assertIsNotNone(result)

        except TypeError as e:
            if await in str(e) or "awaitable in str(e):
                pytest.fail(fAWAIT ERROR IN PROCESS_MESSAGE: {e}")
            else:
                raise

    @pytest.mark.integration
    async def test_clickhouse_operations_websocket_integration(self):
    "
        Test ClickHouseCorpusOperations WebSocket integration to expose await errors.

        This test attempts to use ClickHouseCorpusOperations in realistic scenarios
        to trigger the await errors at lines 134 and 174.
        "
        from netra_backend.app.services.corpus.clickhouse_operations import ClickHouseCorpusOperations

        operations = ClickHouseCorpusOperations(user_context=self.user_context)

        # Test success notification scenario (line 134 error)
        try:
            await operations._send_success_notification(
                corpus_id=test_corpus_integration,
                table_name="test_table_integration"
            )
            # If we reach here, no await error occurred

        except TypeError as e:
            if await in str(e) or awaitable in str(e):
                pytest.fail(fAWAIT ERROR AT LINE 134: {e})"
            else:
                # Other errors are acceptable for this test
                pass

        # Test error notification scenario (line 174 error)
        try:
            test_error = Exception("Integration test corpus error)
            await operations._send_error_notification(
                corpus_id=test_corpus_error_integration,
                error=test_error
            )
            # If we reach here, no await error occurred

        except TypeError as e:
            if "await in str(e) or awaitable" in str(e):
                pytest.fail(fAWAIT ERROR AT LINE 174: {e})
            else:
                # Other errors are acceptable for this test
                pass

    @pytest.mark.integration
    async def test_websocket_manager_factory_consistency_integration(self):
        
        Test WebSocket manager factory consistency across integration scenarios.

        This test validates that different factory patterns create compatible
        managers and that sync/async usage is consistent.
""
        # Test all available factory functions
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as pattern_get

        # Create managers using different patterns
        sync_manager_1 = get_websocket_manager(user_context=self.user_context)
        sync_manager_2 = pattern_get(user_context=self.user_context)
        async_manager = await create_websocket_manager(user_context=self.user_context)

        # Verify all managers are created successfully
        managers = [sync_manager_1, sync_manager_2, async_manager]
        for i, manager in enumerate(managers):
            self.assertIsNotNone(manager, fManager {i} should not be None)
            self.assertTrue(hasattr(manager, 'user_context'), fManager {i} should have user_context)"
            self.assertEqual(
                manager.user_context.user_id,
                self.user_context.user_id,
                f"Manager {i} should have correct user_id
            )

        # Test that all managers have the same interface
        expected_methods = ['send_message_to_user', 'emit_critical_event']
        for i, manager in enumerate(managers):
            for method in expected_methods:
                self.assertTrue(
                    hasattr(manager, method),
                    fManager {i} should have method {method}
                )

    @pytest.mark.integration
    async def test_websocket_manager_user_isolation_integration(self):
    ""
        Test WebSocket manager user isolation in integration scenarios.

        This test validates that different users get isolated managers
        and that factory patterns maintain proper user separation.
        
        # Create multiple user contexts
        user_context_1 = UserExecutionContext(
            user_id=integration_user_1,"
            thread_id="integration_thread_1,
            run_id=integration_run_1
        )
        user_context_2 = UserExecutionContext(
            user_id="integration_user_2,"
            thread_id=integration_thread_2,
            run_id=integration_run_2"
        )

        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        # Create managers for different users
        manager_1 = get_websocket_manager(user_context=user_context_1)
        manager_2 = get_websocket_manager(user_context=user_context_2)

        # Verify isolation
        self.assertIsNotNone(manager_1)
        self.assertIsNotNone(manager_2)
        self.assertNotEqual(
            manager_1.user_context.user_id,
            manager_2.user_context.user_id,
            Managers should have different user IDs"
        )

        # Verify each manager has correct user context
        self.assertEqual(manager_1.user_context.user_id, integration_user_1)
        self.assertEqual(manager_2.user_context.user_id, integration_user_2")"


if __name__ == __main__:
    pytest.main([__file__, -v, "--tb=short"]"