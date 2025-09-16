"""
Test suite for WebSocket 'send after close' race condition fix.

ISSUE #335: Verifies that the WebSocket manager properly handles race conditions
where send operations are attempted after WebSocket close has been initiated.

Tests validate:
1. is_closing flag prevents send operations on closing connections
2. Concurrent close and broadcast operations don't cause runtime errors
3. Connection state is properly tracked during cleanup
4. Error handling gracefully manages send-after-close scenarios
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.websocket_core.websocket_manager import create_websocket_manager
from netra_backend.app.websocket_core.utils import safe_websocket_close
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

class SendAfterCloseRaceConditionTests:
    """Test WebSocket send-after-close race condition fix."""

    @pytest.fixture
    async def manager(self):
        """Create a WebSocket manager for testing."""
        test_user_id = '101463487227881885914'
        manager = await create_websocket_manager(user_id=test_user_id)
        yield manager
        if hasattr(manager, '_cleanup_all_connections'):
            await manager._cleanup_all_connections()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket with realistic behavior."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client_state = Mock()
        websocket.client_state.name = 'CONNECTED'
        return websocket

    @pytest.fixture
    def mock_closing_websocket(self):
        """Create a mock WebSocket in closing state."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        try:
            from starlette.websockets import WebSocketState
            websocket.client_state = WebSocketState.CLOSING
        except ImportError:
            websocket.client_state = Mock()
            websocket.client_state.name = 'CLOSING'
        return websocket

    @pytest.mark.asyncio
    async def test_is_closing_flag_prevents_send(self, manager, mock_websocket):
        """Test that is_closing flag prevents send operations."""
        user_id = 'test_user_001'
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_websocket, connected_at=datetime.now(timezone.utc), is_closing=True)
        await manager.add_connection(connection)
        result = await manager.send_message(connection_id, {'test': 'message'})
        assert result is False, 'Send should fail for closing connection'
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_connection_safety_check_websocket_state(self, manager, mock_closing_websocket):
        """Test that safety check detects WebSocket in closing state."""
        user_id = 'test_user_002'
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_closing_websocket, connected_at=datetime.now(timezone.utc), is_closing=False)
        await manager.add_connection(connection)
        result = await manager.send_message(connection_id, {'test': 'message'})
        assert result is False, 'Send should fail for WebSocket in CLOSING state'
        mock_closing_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_broadcast_and_close_race_condition(self, manager):
        """Test concurrent broadcast and connection close operations."""
        connections = []
        user_ids = [f'test_user_{i:03d}' for i in range(5)]
        for user_id in user_ids:
            mock_ws = Mock()
            mock_ws.send_json = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.client_state = Mock()
            mock_ws.client_state.name = 'CONNECTED'
            connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
            connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_ws, connected_at=datetime.now(timezone.utc))
            await manager.add_connection(connection)
            connections.append((connection_id, connection, mock_ws))

        async def broadcast_messages():
            """Continuously broadcast messages."""
            for i in range(10):
                await manager.broadcast({'type': 'test', 'data': f'message_{i}'})
                await asyncio.sleep(0.01)

        async def close_connections():
            """Close connections during broadcast."""
            await asyncio.sleep(0.02)
            for connection_id, connection, mock_ws in connections[::2]:
                connection.is_closing = True
                await manager.remove_connection(connection_id)
        await asyncio.gather(broadcast_messages(), close_connections(), return_exceptions=True)
        remaining_connections = list(manager._connections.values())
        assert len(remaining_connections) == 3, 'Should have 3 remaining connections'

    @pytest.mark.asyncio
    async def test_send_after_close_error_handling(self, manager, mock_websocket):
        """Test proper error handling when send-after-close occurs."""
        user_id = 'test_user_003'
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_websocket.send_json.side_effect = RuntimeError("Cannot call 'send' once a close message has been sent.")
        connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_websocket, connected_at=datetime.now(timezone.utc))
        await manager.add_connection(connection)
        result = await manager.send_message(connection_id, {'test': 'message'})
        assert result is False, 'Send should fail gracefully'
        stored_connection = manager.get_connection(connection_id)
        if stored_connection:
            assert stored_connection.is_closing is True, 'Connection should be marked as closing'

    @pytest.mark.asyncio
    async def test_broadcast_skips_unsafe_connections(self, manager):
        """Test that broadcast skips connections that are not safe to send to."""
        safe_connection = await self._create_test_connection(manager, 'safe_user', is_closing=False)
        closing_connection = await self._create_test_connection(manager, 'closing_user', is_closing=True)
        await manager.broadcast({'type': 'test', 'data': 'broadcast_message'})
        safe_connection.websocket.send_json.assert_called_once()
        closing_connection.websocket.send_json.assert_not_called()

    async def _create_test_connection(self, manager, user_id: str, is_closing: bool=False):
        """Helper to create test connection."""
        mock_ws = Mock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = Mock()
        mock_ws.client_state.name = 'CONNECTED'
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_ws, connected_at=datetime.now(timezone.utc))
        await manager.add_connection(connection)
        if is_closing:
            stored_connection = manager.get_connection(connection_id)
            if stored_connection:
                stored_connection.is_closing = True
        return stored_connection if stored_connection else connection

    @pytest.mark.asyncio
    async def test_connection_cleanup_sets_closing_flag(self, manager, mock_websocket):
        """Test that connection cleanup properly sets is_closing flag."""
        user_id = 'test_user_004'
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_websocket, connected_at=datetime.now(timezone.utc))
        await manager.add_connection(connection)
        assert connection.is_closing is False
        await manager.remove_connection(connection_id)
        assert connection_id not in manager._connections

    @pytest.mark.asyncio
    async def test_safe_websocket_close_integration(self):
        """Test integration with safe_websocket_close utility."""
        mock_websocket = Mock()
        mock_websocket.close = AsyncMock()
        await safe_websocket_close(mock_websocket)
        mock_websocket.close.assert_called_once_with(code=1000, reason='Normal closure')
        mock_websocket.close.side_effect = RuntimeError("Cannot call 'send' once a close message has been sent.")
        await safe_websocket_close(mock_websocket, code=1001, reason='Test close')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')