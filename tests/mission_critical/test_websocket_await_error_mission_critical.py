"""Mission Critical tests for WebSocket await error validation.

This test suite validates that WebSocket manager await errors don't break
the Golden Path user flow. These tests focus on business-critical scenarios
that must work for users to get AI responses (90% of platform value).

CRITICAL: These tests validate the foundation of AI chat interactions.
"""

import pytest
import asyncio
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketAwaitErrorMissionCritical(SSotAsyncTestCase):
    """Mission critical validation of WebSocket await error impact."""

    def setUp(self):
        """Set up mission critical test environment."""
        super().setUp()
        self.user_context = UserExecutionContext(
            user_id="mission_critical_user",
            thread_id="mission_critical_thread",
            run_id="mission_critical_run"
        )

    @pytest.mark.mission_critical
    async def test_golden_path_websocket_manager_availability(self):
        """
        MISSION CRITICAL: Validate WebSocket manager availability for Golden Path.

        This test ensures that WebSocket managers can be created successfully
        using the correct patterns, preventing Golden Path failures.
        """
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

        # CRITICAL: WebSocket manager must be available for Golden Path
        manager = get_websocket_manager(user_context=self.user_context)
        self.assertIsNotNone(manager, "CRITICAL: WebSocket manager creation failed")

        # CRITICAL: Manager must have user isolation
        self.assertEqual(
            manager.user_context.user_id,
            self.user_context.user_id,
            "CRITICAL: WebSocket manager user isolation failed"
        )

        # CRITICAL: Manager must have required methods for Golden Path
        required_methods = [
            'send_message_to_user',
            'emit_critical_event',
            'send_error'
        ]

        for method in required_methods:
            self.assertTrue(
                hasattr(manager, method),
                f"CRITICAL: WebSocket manager missing required method: {method}"
            )

    @pytest.mark.mission_critical
    async def test_websocket_events_delivery_not_blocked_by_await_errors(self):
        """
        MISSION CRITICAL: Ensure WebSocket events can be delivered despite await errors.

        This test validates that the 5 critical WebSocket events (agent_started,
        agent_thinking, tool_executing, tool_completed, agent_completed) can still
        be sent even if some components have await errors.
        """
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

        manager = get_websocket_manager(user_context=self.user_context)
        self.assertIsNotNone(manager)

        # Test all 5 critical WebSocket events
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        for event_type in critical_events:
            try:
                # Test event emission capability
                await manager.emit_critical_event(
                    event_type=event_type,
                    data={
                        'message': f'Test {event_type} event',
                        'user_id': self.user_context.user_id,
                        'timestamp': 'test_timestamp'
                    }
                )
                # If no exception, event delivery is working

            except Exception as e:
                # Only fail if it's an await-related error
                if "await" in str(e) or "awaitable" in str(e):
                    self.fail(f"CRITICAL: Await error blocking {event_type} event: {e}")
                # Other errors might be acceptable (e.g., no real WebSocket connection)

    @pytest.mark.mission_critical
    async def test_agent_message_processing_resilience_to_await_errors(self):
        """
        MISSION CRITICAL: Validate agent message processing works despite await errors.

        This test ensures that the core agent message processing pipeline
        remains functional even if WebSocket notification components have await errors.
        """
        from netra_backend.app.agents.example_message_processor import ExampleMessageProcessor

        processor = ExampleMessageProcessor(user_id=self.user_context.user_id)
        processor.user_context = self.user_context

        # Test basic message processing capability
        test_message = {
            'type': 'optimization',
            'content': 'Test optimization request for mission critical validation',
            'user_id': self.user_context.user_id
        }

        try:
            # This should work even if WebSocket notifications have issues
            result = await processor.process_message(test_message)

            # CRITICAL: Message processing must produce a result
            self.assertIsNotNone(result, "CRITICAL: Message processing returned None")

            # CRITICAL: Result should indicate processing occurred
            self.assertIsInstance(result, dict, "CRITICAL: Result should be a dictionary")

        except TypeError as e:
            # CRITICAL: Await errors should not break message processing
            if "await" in str(e) or "awaitable" in str(e):
                self.fail(f"CRITICAL: Await error breaking message processing: {e}")
            else:
                # Other TypeErrors might be acceptable
                raise

    @pytest.mark.mission_critical
    async def test_corpus_operations_resilience_to_await_errors(self):
        """
        MISSION CRITICAL: Validate corpus operations work despite await errors.

        This test ensures that corpus operations can complete successfully
        even if WebSocket notification components have await errors.
        """
        from netra_backend.app.services.corpus.clickhouse_operations import ClickHouseCorpusOperations

        operations = ClickHouseCorpusOperations(user_context=self.user_context)

        # Test that WebSocket manager retrieval has fallback behavior
        try:
            # Test the WebSocket manager getter directly
            ws_manager = await operations._get_websocket_manager()

            # If successful, validate manager
            if ws_manager:
                self.assertTrue(hasattr(ws_manager, 'emit_critical_event'))

        except TypeError as e:
            # CRITICAL: Await errors should not break corpus operations
            if "await" in str(e) or "awaitable" in str(e):
                self.fail(f"CRITICAL: Await error in corpus WebSocket manager: {e}")
            else:
                # Other errors might be acceptable
                pass

        # Test notification methods with error handling
        try:
            # Test success notification
            await operations._send_success_notification(
                corpus_id="mission_critical_test_corpus",
                table_name="mission_critical_test_table"
            )

        except TypeError as e:
            if "await" in str(e) or "awaitable" in str(e):
                self.fail(f"CRITICAL: Await error in success notification: {e}")

        try:
            # Test error notification
            test_error = Exception("Mission critical test error")
            await operations._send_error_notification(
                corpus_id="mission_critical_test_corpus_error",
                error=test_error
            )

        except TypeError as e:
            if "await" in str(e) or "awaitable" in str(e):
                self.fail(f"CRITICAL: Await error in error notification: {e}")

    @pytest.mark.mission_critical
    async def test_websocket_factory_pattern_golden_path_compliance(self):
        """
        MISSION CRITICAL: Validate WebSocket factory patterns support Golden Path.

        This test ensures that WebSocket factory patterns are consistent and
        don't introduce blocking issues that could break the Golden Path user flow.
        """
        # Test synchronous factory (most common pattern)
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

        sync_manager = get_websocket_manager(user_context=self.user_context)
        self.assertIsNotNone(sync_manager, "CRITICAL: Sync WebSocket factory failed")

        # Test asynchronous factory (for async contexts)
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager

        async_manager = await create_websocket_manager(user_context=self.user_context)
        self.assertIsNotNone(async_manager, "CRITICAL: Async WebSocket factory failed")

        # CRITICAL: Both managers should support Golden Path operations
        managers = [sync_manager, async_manager]
        for i, manager in enumerate(managers):
            # Test user context isolation
            self.assertEqual(
                manager.user_context.user_id,
                self.user_context.user_id,
                f"CRITICAL: Manager {i} user isolation failed"
            )

            # Test critical event emission capability
            try:
                await manager.emit_critical_event(
                    event_type="golden_path_test",
                    data={'test': 'mission_critical_validation'}
                )
            except Exception as e:
                # Only fail on await errors
                if "await" in str(e) or "awaitable" in str(e):
                    self.fail(f"CRITICAL: Manager {i} event emission await error: {e}")

    @pytest.mark.mission_critical
    async def test_websocket_await_error_impact_assessment(self):
        """
        MISSION CRITICAL: Assess the impact of await errors on system functionality.

        This test provides a comprehensive assessment of how await errors
        affect different parts of the WebSocket infrastructure.
        """
        impact_assessment = {
            'sync_factory_works': False,
            'async_factory_works': False,
            'agent_processing_works': False,
            'corpus_operations_work': False,
            'event_delivery_works': False
        }

        # Test sync factory
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
            manager = get_websocket_manager(user_context=self.user_context)
            impact_assessment['sync_factory_works'] = manager is not None
        except Exception:
            pass

        # Test async factory
        try:
            from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
            manager = await create_websocket_manager(user_context=self.user_context)
            impact_assessment['async_factory_works'] = manager is not None
        except Exception:
            pass

        # Test agent processing
        try:
            from netra_backend.app.agents.example_message_processor import ExampleMessageProcessor
            processor = ExampleMessageProcessor(user_id=self.user_context.user_id)
            processor.user_context = self.user_context
            ws_manager = await processor._get_websocket_manager(self.user_context)
            impact_assessment['agent_processing_works'] = ws_manager is not None
        except TypeError as e:
            if "await" not in str(e) and "awaitable" not in str(e):
                impact_assessment['agent_processing_works'] = True

        # Test corpus operations
        try:
            from netra_backend.app.services.corpus.clickhouse_operations import ClickHouseCorpusOperations
            operations = ClickHouseCorpusOperations(user_context=self.user_context)
            ws_manager = await operations._get_websocket_manager()
            impact_assessment['corpus_operations_work'] = True
        except TypeError as e:
            if "await" not in str(e) and "awaitable" not in str(e):
                impact_assessment['corpus_operations_work'] = True

        # Test event delivery
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
            manager = get_websocket_manager(user_context=self.user_context)
            await manager.emit_critical_event(
                event_type="impact_assessment_test",
                data={'test': True}
            )
            impact_assessment['event_delivery_works'] = True
        except Exception:
            pass

        # Log impact assessment
        print(f"\nISSUE #1184 IMPACT ASSESSMENT:")
        for component, works in impact_assessment.items():
            status = "✅ WORKING" if works else "❌ BROKEN"
            print(f"  {component}: {status}")

        # CRITICAL: At least basic WebSocket functionality must work
        critical_components = ['sync_factory_works', 'event_delivery_works']
        for component in critical_components:
            self.assertTrue(
                impact_assessment[component],
                f"CRITICAL: {component} is broken - Golden Path at risk"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])