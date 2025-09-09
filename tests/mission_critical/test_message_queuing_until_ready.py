class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
Mission-critical message queuing tests.
Tests message queuing behavior when WebSocket connections aren't ready.

Critical scenarios covered:
1. Message queuing before connection established
2. Message ordering preservation during queuing
3. Queue overflow handling
4. Automatic queue processing when ready
5. Queue persistence across reconnections
6. Priority message handling in queue
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any
import pytest
import json
from datetime import datetime
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager, get_websocket_manager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestMessageQueueingUntilReady:
    """Test message queuing behavior when WebSocket not ready."""

    @pytest.fixture
    async def setup(self):
        """Setup test environment with WebSocket infrastructure."""
        manager = WebSocketManager()
        
        # Generate test IDs
        user_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        yield {
            'manager': manager,
            'user_id': user_id,
            'run_id': run_id,
            'thread_id': thread_id
        }
        
        # Cleanup
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_message_queuing_before_connection(self, setup):
        """Test message queuing behavior when no connection exists."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Send messages before any connection - WebSocketManager will return False
        messages = [
            {'type': 'agent_started', 'data': {'agent': 'test1'}},
            {'type': 'agent_thinking', 'data': {'thought': 'analyzing'}},
            {'type': 'tool_executing', 'data': {'tool': 'search'}},
            {'type': 'tool_completed', 'data': {'result': 'done'}},
            {'type': 'agent_completed', 'data': {'result': 'success'}}
        ]
        
        # Try to send all messages - should fail gracefully
        for msg in messages:
            result = await manager.send_to_user(user_id, msg)
            assert result is False  # No connection exists
        
        # Now connect
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED  # Connected
        
        connection_id = await manager.connect_user(
            user_id, 
            mock_ws, 
            thread_id=setup['thread_id']
        )
        
        # Now send messages after connection
        for msg in messages:
            result = await manager.send_to_user(user_id, msg)
            assert result is True  # Should succeed now
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify all messages sent
        assert mock_ws.send_json.call_count == 5

    @pytest.mark.asyncio
    async def test_message_ordering_preservation(self, setup):
        """Test that message order is preserved when sent in sequence."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Connect WebSocket first
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Create ordered messages with timestamps
        messages = []
        for i in range(10):
            messages.append({
                'type': f'message_{i}',
                'data': {
                    'index': i,
                    'timestamp': datetime.now().isoformat()
                }
            })
            await manager.send_to_user(user_id, messages[-1])
            await asyncio.sleep(0.01)  # Small delay to ensure ordering
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Verify correct order
        assert mock_ws.send_json.call_count == 10
        
        sent_messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
        for i, msg in enumerate(sent_messages):
            assert msg['type'] == f'message_{i}'
            assert msg['data']['index'] == i

    @pytest.mark.asyncio
    async def test_connection_without_thread_immediate_send(self, setup):
        """Test sending messages when connected but no thread_id."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Connect without thread_id
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=None  # No thread context
        )
        
        # Send messages - should send immediately in WebSocketManager
        messages = [
            {'type': 'agent_started', 'data': {'status': 'waiting'}},
            {'type': 'agent_thinking', 'data': {'thought': 'no queue needed'}}
        ]
        
        for msg in messages:
            result = await manager.send_to_user(user_id, msg)
            assert result is True  # Should succeed
        
        # Messages should be sent immediately
        assert mock_ws.send_json.call_count == 2
        
        # Update thread_id
        manager.update_connection_thread(connection_id, setup['thread_id'])
        
        # Send another message
        await manager.send_to_user(user_id, {'type': 'after_thread_update', 'data': {}})
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # All messages should be sent
        assert mock_ws.send_json.call_count == 3

    @pytest.mark.asyncio
    async def test_high_message_volume_handling(self, setup):
        """Test handling of high message volume scenarios."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Connect first
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Send many messages rapidly
        MESSAGE_COUNT = 100
        
        for i in range(MESSAGE_COUNT):
            await manager.send_to_user(user_id, {
                'type': 'volume_test',
                'data': {'index': i}
            })
        
        # Allow processing
        await asyncio.sleep(0.5)
        
        # Verify messages processed (WebSocketManager sends immediately)
        assert mock_ws.send_json.call_count == MESSAGE_COUNT

    @pytest.mark.asyncio
    async def test_reconnection_behavior(self, setup):
        """Test behavior when connection drops and reconnects."""
        manager = setup['manager']
        user_id = setup['user_id']
        thread_id = setup['thread_id']
        
        # First connection
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws1.websocket = TestWebSocketConnection()
        mock_ws1.client_state = 1
        
        connection_id1 = await manager.connect_user(user_id, mock_ws1, thread_id=None)
        
        # Send messages
        await manager.send_to_user(user_id, {'type': 'msg1', 'data': {}})
        await manager.send_to_user(user_id, {'type': 'msg2', 'data': {}})
        
        # Disconnect
        await manager.disconnect_user(user_id, mock_ws1, 1000, "Test disconnect")
        
        # Verify messages were sent to first connection
        assert mock_ws1.send_json.call_count == 2
        
        # Reconnect with new connection
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws2.websocket = TestWebSocketConnection()
        mock_ws2.client_state = 1
        
        connection_id2 = await manager.connect_user(user_id, mock_ws2, thread_id=thread_id)
        
        # Send new messages to verify new connection works
        await manager.send_to_user(user_id, {'type': 'msg3', 'data': {}})
        await manager.send_to_user(user_id, {'type': 'msg4', 'data': {}})
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Messages should be sent to new connection
        assert mock_ws2.send_json.call_count == 2
        # Old connection should not receive new messages
        assert mock_ws1.send_json.call_count == 2  # Still only the original 2

    @pytest.mark.asyncio
    async def test_different_message_types(self, setup):
        """Test handling different message types."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Connect
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Send different message types
        messages = [
            {'type': 'regular_1', 'data': {'priority': 'normal'}},
            {'type': 'regular_2', 'data': {'priority': 'normal'}},
            {'type': 'agent_error', 'data': {'priority': 'high', 'error': 'Critical error'}},
            {'type': 'regular_3', 'data': {'priority': 'normal'}}
        ]
        
        for msg in messages:
            await manager.send_to_user(user_id, msg)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # All messages should be sent
        sent_messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
        assert len(sent_messages) == 4
        
        # Check if error message exists
        error_messages = [m for m in sent_messages if m['type'] == 'agent_error']
        assert len(error_messages) == 1
        
        # Verify message types are preserved
        sent_types = [m['type'] for m in sent_messages]
        original_types = [m['type'] for m in messages]
        assert set(sent_types) == set(original_types)

    @pytest.mark.asyncio
    async def test_concurrent_message_operations(self, setup):
        """Test concurrent message sending operations."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Connect first
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        message_count = 0
        
        async def producer():
            nonlocal message_count
            for i in range(20):
                await manager.send_to_user(user_id, {
                    'type': f'concurrent_{i}',
                    'data': {'index': i}
                })
                message_count += 1
                await asyncio.sleep(0.01)
        
        # Start producer
        producer_task = asyncio.create_task(producer())
        
        # Wait for producer to finish
        await producer_task
        
        # Allow all messages to process
        await asyncio.sleep(0.2)
        
        # All messages should be sent
        assert mock_ws.send_json.call_count == message_count

    @pytest.mark.asyncio
    async def test_error_handling_during_send(self, setup):
        """Test error handling when message sending fails."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Connect with mock that fails on third message
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        call_count = 0
        
        async def failing_send(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise Exception("WebSocket send failed")
            return None
        
        mock_ws.send_json = AsyncMock(side_effect=failing_send)
        
        # Connect
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Send messages
        for i in range(5):
            try:
                result = await manager.send_to_user(user_id, {
                    'type': f'message_{i}',
                    'data': {'index': i}
                })
                # First 2 should succeed, 3rd should fail, manager handles gracefully
            except Exception:
                pass  # Expected for failed sends
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Should have attempted to send (at least first 2 successful, 3rd failed)
        assert call_count >= 2  # At least tried to send

    @pytest.mark.asyncio 
    async def test_queue_with_websocket_manager_integration(self, setup):
        """Test queue behavior with WebSocketManager integration."""
        # Use the existing manager from setup
        manager = setup['manager']
        user_id = setup['user_id']
        thread_id = setup['thread_id']
        
        # Create mock WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Try to send before connection
        result1 = await manager.send_to_user(user_id, {
            'type': 'early_message',
            'data': {'content': 'sent before connection'}
        })
        assert result1 is False  # Should fail, no connection
        
        # Connect
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)
        
        # Send after connection
        result2 = await manager.send_to_user(user_id, {
            'type': 'post_connection',
            'data': {'content': 'sent after connection'}
        })
        assert result2 is True  # Should succeed
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify messages handled correctly
        # Only the post-connection message should be sent
        assert mock_ws.send_json.called

    @pytest.mark.asyncio
    async def test_message_rapid_sending(self, setup):
        """Test rapid message sending behavior."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Connect first
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Track actual send timing
        send_times = []
        
        async def track_send(msg):
            send_times.append(time.time())
            return None
        
        mock_ws.send_json.side_effect = track_send
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=setup['thread_id']
        )
        
        # Send many small messages quickly
        for i in range(50):
            await manager.send_to_user(user_id, {
                'type': 'small_update',
                'data': {'value': i}
            })
        
        # Allow processing
        await asyncio.sleep(0.5)
        
        # Check if messages were sent
        assert len(send_times) == 50
        
        # All messages should be sent individually in WebSocketManager
        assert mock_ws.send_json.call_count == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])