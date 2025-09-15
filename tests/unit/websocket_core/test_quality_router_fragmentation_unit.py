"""Unit tests for Quality Router fragmentation in Issue #1101.

Tests demonstrate fragmentation between standalone QualityMessageRouter
and embedded quality handlers in WebSocketHandler, proving SSOT violations.

Expected: 20-30% success rate due to fragmentation issues.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class QualityRouterFragmentationUnitTests(SSotBaseTestCase):
    """Unit tests demonstrating Quality Router fragmentation issues."""

    def setUp(self):
        """Set up test fixtures for fragmentation testing."""
        super().setUp()
        self.test_user_id = 'test_user_123'
        self.test_message = {'type': 'get_quality_metrics', 'thread_id': 'thread_123', 'run_id': 'run_456', 'payload': {'agent_name': 'test_agent'}}
        self.mock_quality_gate_service = MagicMock()
        self.mock_monitoring_service = MagicMock()
        self.mock_db_session_factory = MagicMock()
        self.mock_supervisor = MagicMock()

    @pytest.mark.asyncio
    async def test_standalone_quality_router_handler_initialization(self):
        """Test standalone QualityMessageRouter handler initialization.

        This should PASS - standalone router initializes correctly.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        self.assertIsNotNone(router.handlers)
        self.assertIn('get_quality_metrics', router.handlers)
        self.assertIn('subscribe_quality_alerts', router.handlers)
        self.assertIn('start_agent', router.handlers)
        self.assertIn('validate_content', router.handlers)
        self.assertIn('generate_quality_report', router.handlers)

    @pytest.mark.asyncio
    async def test_embedded_quality_handler_initialization(self):
        """Test embedded quality handler initialization in WebSocketHandler.

        This should FAIL initially - embedded handlers may not initialize properly.
        """
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        handler = WebSocketHandler()
        await handler._initialize_quality_handlers()
        self.assertTrue(hasattr(handler, '_quality_handlers'))
        self.assertIsInstance(handler._quality_handlers, dict)
        expected_handlers = {'get_quality_metrics', 'subscribe_quality_alerts', 'start_agent', 'validate_content', 'generate_quality_report'}
        actual_handlers = set(handler._quality_handlers.keys())
        self.assertEqual(expected_handlers, actual_handlers, 'Handler sets differ between standalone and embedded routers')

    @pytest.mark.asyncio
    async def test_quality_message_type_detection_consistency(self):
        """Test quality message type detection consistency between routers.

        This should FAIL - different routers may have different message type detection.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        embedded_handler = WebSocketHandler()
        await embedded_handler._initialize_quality_handlers()
        test_message_types = ['get_quality_metrics', 'subscribe_quality_alerts', 'validate_content', 'generate_quality_report', 'start_agent', 'unknown_quality_type']
        for message_type in test_message_types:
            standalone_valid = standalone_router._is_valid_message_type(message_type)
            embedded_valid = embedded_handler._is_quality_message_type(message_type)
            self.assertEqual(standalone_valid, embedded_valid, f"Message type '{message_type}' detection differs between routers")

    @pytest.mark.asyncio
    async def test_quality_handler_instance_isolation(self):
        """Test that quality handlers are properly isolated between router instances.

        This may FAIL - handlers might be shared incorrectly causing state issues.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        router1 = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        router2 = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        for handler_type in router1.handlers:
            handler1 = router1.handlers[handler_type]
            handler2 = router2.handlers[handler_type]
            self.assertIsNot(handler1, handler2, f"Handler '{handler_type}' instances are shared between routers")

    @pytest.mark.asyncio
    async def test_quality_message_routing_path_differences(self):
        """Test that quality message routing paths differ between implementations.

        This should FAIL - demonstrating routing inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        with patch('netra_backend.app.services.websocket.quality_metrics_handler.QualityMetricsHandler.handle', new_callable=AsyncMock) as mock_standalone_handle:
            with patch('netra_backend.app.websocket_core.handlers.WebSocketHandler._route_quality_message', new_callable=AsyncMock) as mock_embedded_route:
                standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
                embedded_handler = WebSocketHandler()
                await embedded_handler._initialize_quality_handlers()
                await standalone_router.handle_message(self.test_user_id, self.test_message)
                await embedded_handler.handle_quality_message(self.test_user_id, self.test_message)
                mock_standalone_handle.assert_called_once()
                mock_embedded_route.assert_called_once()
                standalone_call = mock_standalone_handle.call_args
                embedded_call = mock_embedded_route.call_args
                self.assertNotEqual(standalone_call, embedded_call, 'Quality message routing should be identical but differs between implementations')

    @pytest.mark.asyncio
    async def test_session_continuity_fragmentation(self):
        """Test session continuity handling differs between routers.

        This should FAIL - showing session handling inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        embedded_handler = WebSocketHandler()
        test_message_with_ids = {'type': 'get_quality_metrics', 'thread_id': 'thread_123', 'run_id': 'run_456', 'payload': {}}
        await standalone_router.handle_message(self.test_user_id, test_message_with_ids)
        await embedded_handler.handle_quality_message(self.test_user_id, test_message_with_ids)
        standalone_thread_id = getattr(standalone_router, '_current_thread_id', None)
        standalone_run_id = getattr(standalone_router, '_current_run_id', None)
        embedded_thread_id = getattr(embedded_handler, '_current_thread_id', None)
        embedded_run_id = getattr(embedded_handler, '_current_run_id', None)
        self.assertEqual(standalone_thread_id, embedded_thread_id, 'Thread ID storage differs between routers')
        self.assertEqual(standalone_run_id, embedded_run_id, 'Run ID storage differs between routers')

    @pytest.mark.asyncio
    async def test_error_handling_fragmentation(self):
        """Test error handling differs between quality router implementations.

        This should FAIL - showing error handling inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        embedded_handler = WebSocketHandler()
        await embedded_handler._initialize_quality_handlers()
        unknown_message = {'type': 'unknown_quality_type', 'thread_id': 'thread_123', 'run_id': 'run_456', 'payload': {}}
        with patch('netra_backend.app.services.user_execution_context.create_defensive_user_execution_context') as mock_manager:
            mock_ws_manager = AsyncMock()
            mock_manager.return_value = mock_ws_manager
            await standalone_router.handle_message(self.test_user_id, unknown_message)
            standalone_calls = mock_ws_manager.send_to_user.call_count
            mock_ws_manager.reset_mock()
            await embedded_handler.handle_quality_message(self.test_user_id, unknown_message)
            embedded_calls = mock_ws_manager.send_to_user.call_count
            self.assertEqual(standalone_calls, embedded_calls, 'Error handling call patterns differ between router implementations')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')