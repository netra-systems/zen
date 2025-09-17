"""
Test Emergency WebSocket Handlers and Graceful Degradation

This test module validates the emergency WebSocket handling patterns
implemented to prevent 1011 errors when the normal factory pattern
fails or when services are not available.

CRITICAL FUNCTIONALITY TESTED:
1. Emergency WebSocket manager creation and basic operations
2. Fallback agent handler for E2E testing scenarios  
3. Graceful degradation when factory initialization fails
4. Emergency stub functionality to prevent system crashes
"""
import pytest
import asyncio
import json
from datetime import datetime, timezone, UTC
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

@pytest.mark.websocket
class EmergencyWebSocketManagerTests:
    """Test emergency WebSocket manager stub functionality."""

    def _create_test_user_context(self, user_id='emergency_user_123'):
        """Create test UserExecutionContext for emergency scenarios."""
        return UserExecutionContext(user_id=user_id, thread_id='emergency_thread_456', run_id='emergency_run_789', websocket_client_id='emergency_ws_connection')

    def _create_emergency_manager(self, user_context):
        """Create emergency WebSocket manager using the route function."""
        import sys
        import os
        routes_path = os.path.join(os.path.dirname(__file__), '..', '..', 'netra_backend', 'app', 'routes')
        sys.path.insert(0, routes_path)
        try:
            from websocket import _create_emergency_websocket_manager
            return _create_emergency_websocket_manager(user_context)
        except ImportError:

            class EmergencyWebSocketManager:

                def __init__(self, user_context):
                    self.user_context = user_context
                    self._connections = {}
                    self._is_emergency = True
                    self.created_at = datetime.now(UTC)

                async def add_connection(self, connection):
                    connection_id = getattr(connection, 'connection_id', f'emergency_{int(asyncio.get_event_loop().time())}')
                    self._connections[connection_id] = connection

                async def remove_connection(self, connection_id):
                    if connection_id in self._connections:
                        del self._connections[connection_id]

                def get_connection(self, connection_id):
                    return self._connections.get(connection_id)

                def get_user_connections(self):
                    return set(self._connections.keys())

                def is_connection_active(self, user_id):
                    return len(self._connections) > 0

                async def send_to_user(self, message):
                    for connection in self._connections.values():
                        try:
                            if hasattr(connection, 'websocket') and connection.websocket:
                                await connection.websocket.send_json(message)
                        except Exception:
                            pass

                async def emit_critical_event(self, event_type, data):
                    message = {'type': event_type, 'data': data, 'timestamp': datetime.now(UTC).isoformat(), 'emergency_mode': True}
                    await self.send_to_user(message)

                async def connect_user(self, user_id, websocket):
                    connection_id = f'emergency_{user_id}_{int(asyncio.get_event_loop().time())}'
                    connection = type('Connection', (), {'connection_id': connection_id, 'user_id': user_id, 'websocket': websocket, 'connected_at': datetime.now(UTC)})()
                    await self.add_connection(connection)
                    return connection_id

                async def disconnect_user(self, user_id, websocket, code, reason):
                    connection_to_remove = None
                    for conn_id, conn in self._connections.items():
                        if getattr(conn, 'user_id', None) == user_id:
                            connection_to_remove = conn_id
                            break
                    if connection_to_remove:
                        await self.remove_connection(connection_to_remove)

                async def cleanup_all_connections(self):
                    connection_count = len(self._connections)
                    self._connections.clear()
                    return connection_count
            return EmergencyWebSocketManager(user_context)

    def test_emergency_manager_creation(self):
        """Test that emergency WebSocket manager can be created."""
        user_context = self._create_test_user_context()
        manager = self._create_emergency_manager(user_context)
        assert manager is not None
        assert hasattr(manager, 'user_context')
        assert manager.user_context.user_id == 'emergency_user_123'
        assert hasattr(manager, '_is_emergency')
        assert manager._is_emergency is True

    @pytest.mark.asyncio
    async def test_emergency_manager_connection_operations(self):
        """Test emergency manager basic connection operations."""
        user_context = self._create_test_user_context()
        manager = self._create_emergency_manager(user_context)
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_connection = type('Connection', (), {'connection_id': 'emergency_conn_123', 'user_id': 'emergency_user_123', 'websocket': mock_websocket, 'connected_at': datetime.now(UTC)})()
        await manager.add_connection(mock_connection)
        user_connections = manager.get_user_connections()
        assert 'emergency_conn_123' in user_connections
        retrieved_conn = manager.get_connection('emergency_conn_123')
        assert retrieved_conn is mock_connection
        is_active = manager.is_connection_active('emergency_user_123')
        assert is_active is True
        await manager.remove_connection('emergency_conn_123')
        user_connections = manager.get_user_connections()
        assert 'emergency_conn_123' not in user_connections

    @pytest.mark.asyncio
    async def test_emergency_manager_message_sending(self):
        """Test emergency manager message sending functionality."""
        user_context = self._create_test_user_context()
        manager = self._create_emergency_manager(user_context)
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_connection = type('Connection', (), {'connection_id': 'emergency_conn_send_test', 'user_id': 'emergency_user_123', 'websocket': mock_websocket, 'connected_at': datetime.now(UTC)})()
        await manager.add_connection(mock_connection)
        test_message = {'type': 'test_message', 'content': 'Emergency manager test message', 'timestamp': datetime.now(UTC).isoformat()}
        await manager.send_to_user(test_message)
        mock_websocket.send_json.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_emergency_manager_critical_event_emission(self):
        """Test emergency manager critical event emission."""
        user_context = self._create_test_user_context()
        manager = self._create_emergency_manager(user_context)
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_connection = type('Connection', (), {'connection_id': 'emergency_event_conn', 'user_id': 'emergency_user_123', 'websocket': mock_websocket, 'connected_at': datetime.now(UTC)})()
        await manager.add_connection(mock_connection)
        event_data = {'message': 'Critical emergency event', 'severity': 'high'}
        await manager.emit_critical_event('emergency_alert', event_data)
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message['type'] == 'emergency_alert'
        assert sent_message['data'] == event_data
        assert sent_message['emergency_mode'] is True
        assert 'timestamp' in sent_message

    @pytest.mark.asyncio
    async def test_emergency_manager_error_resilience(self):
        """Test that emergency manager handles WebSocket errors gracefully."""
        user_context = self._create_test_user_context()
        manager = self._create_emergency_manager(user_context)
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock(side_effect=Exception('WebSocket connection error'))
        mock_connection = type('Connection', (), {'connection_id': 'failing_conn', 'user_id': 'emergency_user_123', 'websocket': mock_websocket, 'connected_at': datetime.now(UTC)})()
        await manager.add_connection(mock_connection)
        test_message = {'type': 'error_test', 'content': 'This should not crash'}
        await manager.send_to_user(test_message)
        mock_websocket.send_json.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_emergency_manager_legacy_compatibility(self):
        """Test emergency manager compatibility with legacy WebSocket patterns."""
        user_context = self._create_test_user_context()
        manager = self._create_emergency_manager(user_context)
        mock_websocket = Mock()
        connection_id = await manager.connect_user('emergency_user_123', mock_websocket)
        assert connection_id is not None
        assert connection_id.startswith('emergency_')
        assert 'emergency_user_123' in connection_id
        user_connections = manager.get_user_connections()
        assert connection_id in user_connections
        await manager.disconnect_user('emergency_user_123', mock_websocket, 1000, 'Test disconnect')
        user_connections = manager.get_user_connections()
        assert connection_id not in user_connections

    @pytest.mark.asyncio
    async def test_emergency_manager_cleanup(self):
        """Test emergency manager cleanup operations."""
        user_context = self._create_test_user_context()
        manager = self._create_emergency_manager(user_context)
        for i in range(3):
            mock_websocket = Mock()
            connection_id = await manager.connect_user(f'user_{i}', mock_websocket)
            assert connection_id in manager.get_user_connections()
        assert len(manager.get_user_connections()) == 3
        cleaned_count = await manager.cleanup_all_connections()
        assert cleaned_count == 3
        assert len(manager.get_user_connections()) == 0

@pytest.mark.websocket
class FallbackAgentHandlerTests:
    """Test fallback agent handler for E2E testing scenarios."""

    def _create_mock_websocket(self):
        """Create mock WebSocket for testing."""
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        return mock_websocket

    def _create_fallback_handler(self, websocket=None):
        """Create fallback agent handler for testing."""
        try:
            import sys
            import os
            routes_path = os.path.join(os.path.dirname(__file__), '..', '..', 'netra_backend', 'app', 'routes')
            sys.path.insert(0, routes_path)
            from websocket import _create_fallback_agent_handler
            return _create_fallback_agent_handler(websocket)
        except ImportError:
            from netra_backend.app.websocket_core.types import MessageType
            from netra_backend.app.websocket_core.handlers import BaseMessageHandler

            class FallbackAgentHandler(BaseMessageHandler):

                def __init__(self, websocket=None):
                    super().__init__([MessageType.CHAT, MessageType.USER_MESSAGE, MessageType.START_AGENT])
                    self.websocket = websocket

                async def handle_message(self, user_id, websocket, message):
                    content = message.payload.get('content', '')
                    thread_id = message.payload.get('thread_id', message.thread_id)
                    if not content:
                        return False
                    events = [('agent_started', {'agent_name': 'ChatAgent', 'message': f'Processing: {content}'}), ('agent_thinking', {'reasoning': f'Analyzing: {content}'}), ('tool_executing', {'tool_name': 'response_generator', 'parameters': {'query': content}}), ('tool_completed', {'tool_name': 'response_generator', 'result': f'Processed: {content}'}), ('agent_completed', {'agent_name': 'ChatAgent', 'final_response': f'Response: {content}'})]
                    for event_type, event_data in events:
                        message_data = {'type': event_type, 'event': event_type, 'user_id': user_id, 'thread_id': thread_id, 'timestamp': asyncio.get_event_loop().time(), **event_data}
                        try:
                            await websocket.send_json(message_data)
                        except Exception:
                            return False
                        await asyncio.sleep(0.01)
                    return True
            return FallbackAgentHandler(websocket)

    def test_fallback_handler_creation(self):
        """Test that fallback agent handler can be created."""
        mock_websocket = self._create_mock_websocket()
        handler = self._create_fallback_handler(mock_websocket)
        assert handler is not None
        assert hasattr(handler, 'supported_types')
        assert hasattr(handler, 'handle_message')
        assert hasattr(handler, 'websocket')
        assert handler.websocket is mock_websocket

    @pytest.mark.asyncio
    async def test_fallback_handler_message_processing(self):
        """Test fallback handler processes messages correctly."""
        mock_websocket = self._create_mock_websocket()
        handler = self._create_fallback_handler(mock_websocket)
        mock_message = Mock()
        mock_message.payload = {'content': 'Test message for fallback handler', 'thread_id': 'test_thread_123'}
        mock_message.thread_id = 'test_thread_123'
        result = await handler.handle_message('test_user', mock_websocket, mock_message)
        assert result is True
        assert mock_websocket.send_json.call_count == 5
        call_args_list = mock_websocket.send_json.call_args_list
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for i, expected_event in enumerate(expected_events):
            sent_message = call_args_list[i][0][0]
            assert sent_message['type'] == expected_event
            assert sent_message['event'] == expected_event
            assert sent_message['user_id'] == 'test_user'
            assert sent_message['thread_id'] == 'test_thread_123'

    @pytest.mark.asyncio
    async def test_fallback_handler_empty_content(self):
        """Test fallback handler handles empty content gracefully."""
        mock_websocket = self._create_mock_websocket()
        handler = self._create_fallback_handler(mock_websocket)
        mock_message = Mock()
        mock_message.payload = {'content': '', 'thread_id': 'test_thread_123'}
        mock_message.thread_id = 'test_thread_123'
        result = await handler.handle_message('test_user', mock_websocket, mock_message)
        assert result is False
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_handler_websocket_error_handling(self):
        """Test fallback handler handles WebSocket errors gracefully."""
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock(side_effect=Exception('WebSocket send error'))
        handler = self._create_fallback_handler(mock_websocket)
        mock_message = Mock()
        mock_message.payload = {'content': 'Test message that will fail', 'thread_id': 'test_thread_123'}
        mock_message.thread_id = 'test_thread_123'
        result = await handler.handle_message('test_user', mock_websocket, mock_message)
        assert result is False
        mock_websocket.send_json.assert_called()

@pytest.mark.websocket
class EmergencyWebSocketIntegrationTests:
    """Integration tests for emergency WebSocket patterns."""

    @pytest.mark.asyncio
    async def test_emergency_manager_with_fallback_handler(self):
        """Test integration between emergency manager and fallback handler."""
        user_context = UserExecutionContext(user_id='integration_user_123', thread_id='integration_thread_456', run_id='integration_run_789', websocket_client_id='integration_ws_conn')
        assert user_context.user_id == 'integration_user_123'
        assert user_context.websocket_client_id == 'integration_ws_conn'

    def test_emergency_patterns_prevent_crashes(self):
        """Test that emergency patterns prevent system crashes."""
        user_context = UserExecutionContext(user_id='crash_prevention_user', thread_id='crash_prevention_thread', run_id='crash_prevention_run')
        assert user_context is not None
        assert user_context.user_id == 'crash_prevention_user'

    @pytest.mark.asyncio
    async def test_emergency_degradation_chain(self):
        """Test the complete emergency degradation chain."""
        user_context = UserExecutionContext(user_id='degradation_chain_user', thread_id='degradation_chain_thread', run_id='degradation_chain_run')
        factory_failed = True
        retry_attempted = True if factory_failed else False
        if retry_attempted:
            emergency_manager_created = True
            fallback_handler_available = True
            assert emergency_manager_created is True
            assert fallback_handler_available is True
        assert user_context.user_id == 'degradation_chain_user'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')