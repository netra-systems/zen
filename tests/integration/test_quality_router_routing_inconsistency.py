"""Integration tests for Quality Router routing inconsistency in Issue #1101.

Tests demonstrate quality messages route differently depending on which
router implementation is used, proving SSOT violations in routing behavior.

Expected: FAILURES due to routing path differences between implementations.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.integration
class QualityRouterRoutingInconsistencyTests(SSotAsyncTestCase):
    """Integration tests demonstrating Quality Router routing inconsistency."""

    def setUp(self):
        """Set up test fixtures for routing inconsistency testing."""
        super().setUp()
        self.test_user_id = 'integration_user_123'
        self.test_messages = [{'type': 'get_quality_metrics', 'thread_id': 'thread_metrics_123', 'run_id': 'run_metrics_456', 'payload': {'agent_name': 'test_agent'}}, {'type': 'subscribe_quality_alerts', 'thread_id': 'thread_alerts_789', 'run_id': 'run_alerts_012', 'payload': {'alert_types': ['error', 'warning']}}, {'type': 'validate_content', 'thread_id': 'thread_validate_345', 'run_id': 'run_validate_678', 'payload': {'content': 'test content for validation'}}]
        self.mock_quality_gate_service = self._create_quality_gate_service_mock()
        self.mock_monitoring_service = self._create_monitoring_service_mock()
        self.mock_db_session_factory = MagicMock()
        self.mock_supervisor = MagicMock()

    def _create_quality_gate_service_mock(self) -> MagicMock:
        """Create realistic quality gate service mock."""
        service = MagicMock()
        service.validate_content = AsyncMock(return_value={'valid': True, 'score': 0.85, 'issues': []})
        return service

    def _create_monitoring_service_mock(self) -> MagicMock:
        """Create realistic monitoring service mock."""
        service = MagicMock()
        service.get_agent_report = AsyncMock(return_value={'agent_name': 'test_agent', 'quality_score': 0.92, 'execution_count': 15})
        service.get_dashboard_data = AsyncMock(return_value={'overall_score': 0.88, 'active_agents': 5})
        service.subscribers = ['user1', 'user2']
        return service

    @pytest.mark.asyncio
    async def test_quality_message_routing_behavioral_differences(self):
        """Test that quality message routing behavior differs between implementations.

        This should FAIL - demonstrating concrete routing behavioral differences.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        standalone_routing_behavior = {}
        embedded_routing_behavior = {}
        for test_message in self.test_messages:
            message_type = test_message['type']
            standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
            embedded_handler = WebSocketHandler()
            await embedded_handler._initialize_quality_handlers()
            with patch('netra_backend.app.services.user_execution_context.create_defensive_user_execution_context') as mock_manager:
                mock_ws_manager = AsyncMock()
                mock_manager.return_value = mock_ws_manager
                await standalone_router.handle_message(self.test_user_id, test_message)
                standalone_thread_id = getattr(standalone_router, '_current_thread_id', None)
                standalone_run_id = getattr(standalone_router, '_current_run_id', None)
                standalone_sends = mock_ws_manager.send_to_user.call_count
                mock_ws_manager.reset_mock()
                await embedded_handler.handle_quality_message(self.test_user_id, test_message)
                embedded_thread_id = getattr(embedded_handler, '_current_thread_id', None)
                embedded_run_id = getattr(embedded_handler, '_current_run_id', None)
                embedded_sends = mock_ws_manager.send_to_user.call_count
                standalone_routing_behavior[message_type] = {'thread_id': standalone_thread_id, 'run_id': standalone_run_id, 'send_calls': standalone_sends}
                embedded_routing_behavior[message_type] = {'thread_id': embedded_thread_id, 'run_id': embedded_run_id, 'send_calls': embedded_sends}
        for message_type in [msg['type'] for msg in self.test_messages]:
            standalone_behavior = standalone_routing_behavior[message_type]
            embedded_behavior = embedded_routing_behavior[message_type]
            self.assertEqual(standalone_behavior['thread_id'], embedded_behavior['thread_id'], f'Thread ID handling differs for {message_type}')
            self.assertEqual(standalone_behavior['run_id'], embedded_behavior['run_id'], f'Run ID handling differs for {message_type}')
            self.assertEqual(standalone_behavior['send_calls'], embedded_behavior['send_calls'], f'Message sending pattern differs for {message_type}')

    @pytest.mark.asyncio
    async def test_quality_handler_dependency_injection_inconsistency(self):
        """Test dependency injection patterns differ between router implementations.

        This should FAIL - showing dependency injection inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        embedded_handler = WebSocketHandler()
        await embedded_handler._initialize_quality_handlers()
        for handler_type in ['get_quality_metrics', 'subscribe_quality_alerts', 'validate_content']:
            if handler_type in standalone_router.handlers and handler_type in embedded_handler._quality_handlers:
                standalone_handler = standalone_router.handlers[handler_type]
                embedded_handler_instance = embedded_handler._quality_handlers[handler_type]
                self.assertEqual(type(standalone_handler), type(embedded_handler_instance), f'Handler types differ for {handler_type}')
                if hasattr(standalone_handler, 'monitoring_service'):
                    standalone_service = standalone_handler.monitoring_service
                    if hasattr(embedded_handler_instance, 'monitoring_service'):
                        embedded_service = embedded_handler_instance.monitoring_service
                        self.assertIs(standalone_service, embedded_service, f'Monitoring service instances differ for {handler_type}')

    @pytest.mark.asyncio
    async def test_concurrent_quality_message_routing_race_conditions(self):
        """Test concurrent routing exposes race conditions between implementations.

        This should FAIL - demonstrating race conditions in fragmented routing.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        standalone_routers = [QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service) for _ in range(3)]
        embedded_handlers = [WebSocketHandler() for _ in range(3)]
        for handler in embedded_handlers:
            await handler._initialize_quality_handlers()
        standalone_results = []
        embedded_results = []

        async def route_standalone(router, user_id, message):
            try:
                await router.handle_message(user_id, message)
                return 'success'
            except Exception as e:
                return f'error: {str(e)}'

        async def route_embedded(handler, user_id, message):
            try:
                await handler.handle_quality_message(user_id, message)
                return 'success'
            except Exception as e:
                return f'error: {str(e)}'
        with patch('netra_backend.app.services.user_execution_context.create_defensive_user_execution_context') as mock_manager:
            mock_ws_manager = AsyncMock()
            mock_manager.return_value = mock_ws_manager
            standalone_tasks = [route_standalone(router, f'user_{i}', self.test_messages[i % len(self.test_messages)]) for i, router in enumerate(standalone_routers)]
            standalone_results = await asyncio.gather(*standalone_tasks, return_exceptions=True)
            embedded_tasks = [route_embedded(handler, f'user_{i}', self.test_messages[i % len(self.test_messages)]) for i, handler in enumerate(embedded_handlers)]
            embedded_results = await asyncio.gather(*embedded_tasks, return_exceptions=True)
        standalone_success_rate = sum((1 for result in standalone_results if result == 'success')) / len(standalone_results)
        embedded_success_rate = sum((1 for result in embedded_results if result == 'success')) / len(embedded_results)
        self.assertEqual(standalone_success_rate, embedded_success_rate, f'Concurrent routing success rates differ: standalone={standalone_success_rate:.2f}, embedded={embedded_success_rate:.2f}')
        self.assertGreaterEqual(standalone_success_rate, 0.9, f'Standalone router success rate too low: {standalone_success_rate:.2f}')
        self.assertGreaterEqual(embedded_success_rate, 0.9, f'Embedded handler success rate too low: {embedded_success_rate:.2f}')

    @pytest.mark.asyncio
    async def test_quality_message_payload_transformation_differences(self):
        """Test payload transformation differs between router implementations.

        This should FAIL - showing payload handling inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        complex_message = {'type': 'get_quality_metrics', 'thread_id': 'thread_transform_123', 'run_id': 'run_transform_456', 'payload': {'agent_name': 'complex_agent', 'filters': {'time_range': {'start': '2024-01-01', 'end': '2024-01-31'}, 'severity': ['error', 'warning']}, 'options': {'include_raw_data': True, 'format': 'detailed'}}}
        standalone_payloads = []
        embedded_payloads = []
        with patch('netra_backend.app.services.websocket.quality_metrics_handler.QualityMetricsHandler.handle') as mock_standalone:
            with patch('netra_backend.app.websocket_core.handlers.WebSocketHandler._route_quality_message') as mock_embedded:

                async def capture_standalone_payload(user_id, payload):
                    standalone_payloads.append(payload.copy())
                mock_standalone.side_effect = capture_standalone_payload

                async def capture_embedded_payload(user_id, message, message_type):
                    embedded_payloads.append(message.get('payload', {}).copy())
                mock_embedded.side_effect = capture_embedded_payload
                standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
                embedded_handler = WebSocketHandler()
                await embedded_handler._initialize_quality_handlers()
                await standalone_router.handle_message(self.test_user_id, complex_message)
                await embedded_handler.handle_quality_message(self.test_user_id, complex_message)
        self.assertEqual(len(standalone_payloads), 1, 'Should have captured one standalone payload')
        self.assertEqual(len(embedded_payloads), 1, 'Should have captured one embedded payload')
        standalone_payload = standalone_payloads[0]
        embedded_payload = embedded_payloads[0]
        self.assertEqual(standalone_payload, embedded_payload, 'Payload transformations differ between router implementations')
        self.assertIn('thread_id', standalone_payload, 'Thread ID missing from standalone payload')
        self.assertIn('run_id', standalone_payload, 'Run ID missing from standalone payload')
        self.assertIn('thread_id', embedded_payload, 'Thread ID missing from embedded payload')
        self.assertIn('run_id', embedded_payload, 'Run ID missing from embedded payload')

    @pytest.mark.asyncio
    async def test_broadcast_functionality_fragmentation(self):
        """Test broadcast functionality differs between implementations.

        This should FAIL - showing broadcast handling inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler
        quality_update = {'type': 'system_quality_update', 'data': {'overall_score': 0.95, 'trending': 'up', 'alerts': 2}}
        standalone_router = QualityMessageRouter(supervisor=self.mock_supervisor, db_session_factory=self.mock_db_session_factory, quality_gate_service=self.mock_quality_gate_service, monitoring_service=self.mock_monitoring_service)
        embedded_handler = WebSocketHandler()
        with patch('netra_backend.app.services.user_execution_context.create_defensive_user_execution_context') as mock_manager:
            mock_ws_manager = AsyncMock()
            mock_manager.return_value = mock_ws_manager
            standalone_has_broadcast = hasattr(standalone_router, 'broadcast_quality_update')
            if standalone_has_broadcast:
                await standalone_router.broadcast_quality_update(quality_update)
                standalone_broadcast_calls = mock_ws_manager.send_to_user.call_count
            else:
                standalone_broadcast_calls = 0
            mock_ws_manager.reset_mock()
            embedded_has_broadcast = hasattr(embedded_handler, 'broadcast_quality_update')
            if embedded_has_broadcast:
                await embedded_handler.broadcast_quality_update(quality_update)
                embedded_broadcast_calls = mock_ws_manager.send_to_user.call_count
            else:
                embedded_broadcast_calls = 0
        self.assertEqual(standalone_has_broadcast, embedded_has_broadcast, 'Broadcast capability differs between implementations')
        if standalone_has_broadcast and embedded_has_broadcast:
            self.assertEqual(standalone_broadcast_calls, embedded_broadcast_calls, 'Broadcast call patterns differ between implementations')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')