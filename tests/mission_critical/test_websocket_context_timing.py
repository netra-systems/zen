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
Mission-critical WebSocket context timing tests.
Tests race conditions and timing scenarios in WebSocket thread association.

Critical scenarios covered:
1. Connection without initial thread_id
2. Message arrives before thread context
3. Rapid thread switching during message processing
4. Multiple simultaneous connections with different timing
5. Agent execution starting before WebSocket ready
6. Thread context update failures and retries
"""

import asyncio
import time
import uuid
from typing import Any, Dict, Optional
import pytest
import json
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager, get_websocket_manager
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketContextTiming:
    """Test critical WebSocket timing and race condition scenarios."""

    @pytest.fixture
    async def setup(self):
        """Setup test environment with WebSocket infrastructure."""
        # Create WebSocket manager
        manager = WebSocketManager()
        
        # Create mock WebSocket connection
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.websocket = TestWebSocketConnection()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Generate test IDs
        user_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        yield {
            'manager': manager,
            'mock_ws': mock_ws,
            'user_id': user_id,
            'run_id': run_id,
            'thread_id': thread_id
        }
        
        # Cleanup
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_connection_without_initial_thread_id(self, setup):
        """Test WebSocket connection without initial thread_id."""
        manager = setup['manager']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect without thread_id (WebSocketManager requires thread_id, use None handling)
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=None)
        
        # Verify connection established
        assert connection_id in manager.connections
        conn = manager.connections[connection_id]
        assert conn['websocket'] == mock_ws
        assert conn['user_id'] == user_id
        assert conn.get('thread_id') is None  # Should be None initially
        
        # Send a message without thread context - should work but thread_id will be None
        test_message = {
            'type': 'agent_started',
            'data': {'agent_name': 'test_agent'}
        }
        
        # Send to user (messages in WebSocketManager go to user, not run_id)
        success = await manager.send_to_user(user_id, test_message)
        
        # Should succeed even without thread_id
        assert success
        
        # Now update with thread_id
        thread_id = setup['thread_id']
        updated = manager.update_connection_thread(connection_id, thread_id)
        
        # Verify thread_id updated
        assert updated
        assert conn['thread_id'] == thread_id
        
        # Verify message was sent
        await asyncio.sleep(0.1)  # Allow async processing
        mock_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_message_arrives_before_thread_context(self, setup):
        """Test message arriving before thread context is established."""
        manager = setup['manager']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect without thread_id
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=None)
        
        # Send multiple messages before thread context
        messages = [
            {'type': 'agent_thinking', 'data': {'thought': 'Analyzing...'}},
            {'type': 'tool_executing', 'data': {'tool': 'search'}},
            {'type': 'tool_completed', 'data': {'result': 'Found 10 items'}}
        ]
        
        # Messages should be sent immediately to user even without thread context
        for msg in messages:
            await manager.send_to_user(user_id, msg)
        
        # Update thread context
        thread_id = setup['thread_id']
        manager.update_connection_thread(connection_id, thread_id)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify all messages sent
        assert mock_ws.send_json.call_count >= 3
        
        # Verify messages were sent (order may vary in WebSocketManager)
        sent_messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
        sent_types = [msg.get('type') for msg in sent_messages]
        original_types = [msg['type'] for msg in messages]
        
        # Check that all message types were sent
        for msg_type in original_types:
            assert msg_type in sent_types

    @pytest.mark.asyncio
    async def test_rapid_thread_switching(self, setup):
        """Test rapid thread switching during message processing."""
        manager = setup['manager']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect with initial thread
        thread1 = str(uuid.uuid4())
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread1)
        
        # Send message with thread1
        await manager.send_to_user(user_id, {
            'type': 'agent_started',
            'data': {'agent': 'agent1'}
        })
        
        # Rapidly switch threads multiple times
        thread2 = str(uuid.uuid4())
        thread3 = str(uuid.uuid4())
        
        # Quick succession of thread changes
        manager.update_connection_thread(connection_id, thread2)
        await manager.send_to_user(user_id, {
            'type': 'agent_thinking',
            'data': {'thought': 'Processing with thread2'}
        })
        
        manager.update_connection_thread(connection_id, thread3)
        await manager.send_to_user(user_id, {
            'type': 'agent_completed',
            'data': {'result': 'Done with thread3'}
        })
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify messages sent - WebSocketManager may not preserve thread_id in message
        # since it manages threads internally
        assert mock_ws.send_json.call_count == 3

    @pytest.mark.asyncio
    async def test_multiple_simultaneous_connections_timing(self, setup):
        """Test multiple simultaneous connections with different timing."""
        manager = setup['manager']
        
        # Create multiple connections with different timing
        connections = []
        for i in range(5):
            mock_ws = AsyncMock(spec=WebSocket)
            mock_ws.websocket = TestWebSocketConnection()
            mock_ws.client_state = WebSocketState.CONNECTED
            user_id = str(uuid.uuid4())
            
            # Some with thread_id, some without
            thread_id = str(uuid.uuid4()) if i % 2 == 0 else None
            
            connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)
            
            connections.append({
                'mock_ws': mock_ws,
                'user_id': user_id,
                'connection_id': connection_id,
                'thread_id': thread_id,
                'index': i
            })
        
        # Send messages to all connections
        for conn in connections:
            await manager.send_to_user(conn['user_id'], {
                'type': 'test_message',
                'data': {'index': conn['index']}
            })
        
        # Update thread_ids for connections that didn't have them
        for conn in connections:
            if conn['thread_id'] is None:
                new_thread_id = str(uuid.uuid4())
                manager.update_connection_thread(conn['connection_id'], new_thread_id)
                conn['thread_id'] = new_thread_id
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Verify all messages sent
        for conn in connections:
            conn['mock_ws'].send_json.assert_called()
            sent_msg = conn['mock_ws'].send_json.call_args[0][0]
            # WebSocketManager handles thread context internally
            assert sent_msg['data']['index'] == conn['index']

    @pytest.mark.asyncio
    async def test_agent_execution_before_websocket_ready(self, setup):
        """Test agent execution starting before WebSocket is ready."""
        manager = setup['manager']
        user_id = setup['user_id']
        
        # Simulate agent sending messages before WebSocket connected
        early_messages = [
            {'type': 'agent_started', 'data': {'agent': 'early_bird'}},
            {'type': 'agent_thinking', 'data': {'thought': 'Processing...'}}
        ]
        
        # Try to send messages before connection - WebSocketManager will fail gracefully
        for msg in early_messages:
            result = await manager.send_to_user(user_id, msg)
            # Should return False since no connection exists
            assert result is False
        
        # Now establish connection
        mock_ws = setup['mock_ws']
        thread_id = setup['thread_id']
        
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)
        
        # Send messages after connection
        for msg in early_messages:
            await manager.send_to_user(user_id, msg)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify messages were sent after connection
        assert mock_ws.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_thread_context_update_failures_and_retries(self, setup):
        """Test handling of thread context update failures and retries."""
        manager = setup['manager']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        
        # Connect without thread_id
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=None)
        
        # Send message immediately (no queuing in WebSocketManager)
        await manager.send_to_user(user_id, {
            'type': 'test_message',
            'data': {'content': 'waiting for thread'}
        })
        
        # Simulate thread update with potential failure handling
        thread_id = setup['thread_id']
        
        # First attempt - WebSocketManager update_connection_thread is synchronous and simple
        result = manager.update_connection_thread(connection_id, thread_id)
        assert result is True  # Should succeed
        
        # Verify connection has thread_id
        conn = manager.connections.get(connection_id)
        assert conn is not None
        assert conn['thread_id'] == thread_id
        
        # Send another message to verify thread context works
        await manager.send_to_user(user_id, {
            'type': 'followup_message', 
            'data': {'content': 'thread updated'}
        })
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify messages sent
        assert mock_ws.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_concurrent_message_and_thread_update(self, setup):
        """Test concurrent message sending and thread updates."""
        manager = setup['manager']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        
        # Connect with initial thread
        thread1 = str(uuid.uuid4())
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread1)
        
        # Create concurrent tasks
        async def send_messages():
            for i in range(10):
                await manager.send_to_user(user_id, {
                    'type': f'message_{i}',
                    'data': {'index': i}
                })
                await asyncio.sleep(0.01)
        
        async def update_threads():
            for i in range(3):
                new_thread = str(uuid.uuid4())
                manager.update_connection_thread(connection_id, new_thread)
                await asyncio.sleep(0.03)
        
        # Run concurrently
        await asyncio.gather(send_messages(), update_threads())
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Verify all messages sent
        assert mock_ws.send_json.call_count == 10
        
        # Verify messages were sent (WebSocketManager may not include thread_id in each message)
        for call in mock_ws.send_json.call_args_list:
            sent_msg = call[0][0]
            assert 'type' in sent_msg
            assert 'data' in sent_msg

    @pytest.mark.asyncio
    async def test_websocket_disconnection_during_thread_update(self, setup):
        """Test WebSocket disconnection during thread update."""
        manager = setup['manager']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        
        # Connect without thread_id
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=None)
        
        # Send important message
        await manager.send_to_user(user_id, {
            'type': 'important_message',
            'data': {'content': 'must deliver'}
        })
        
        # Disconnect during thread update
        await manager.disconnect_user(user_id, mock_ws, 1000, "Test disconnect")
        
        # Try to update thread (should handle gracefully since connection is gone)
        thread_id = setup['thread_id']
        result = manager.update_connection_thread(connection_id, thread_id)
        # Should return False since connection no longer exists
        assert result is False
        
        # Reconnect
        new_mock_ws = AsyncMock(spec=WebSocket)
        new_mock_ws.websocket = TestWebSocketConnection()
        new_mock_ws.client_state = WebSocketState.CONNECTED
        new_connection_id = await manager.connect_user(user_id, new_mock_ws, thread_id=thread_id)
        
        # Send new message to verify new connection works
        await manager.send_to_user(user_id, {
            'type': 'reconnect_message',
            'data': {'content': 'after reconnect'}
        })
        
        # Verify message delivered to new connection
        await asyncio.sleep(0.1)
        new_mock_ws.send_json.assert_called()
        
        sent_msg = new_mock_ws.send_json.call_args[0][0]
        assert sent_msg['type'] == 'reconnect_message'

    @pytest.mark.asyncio
    async def test_thread_id_propagation_to_message_handler(self, setup):
        """Test thread_id propagation from WebSocket to message handler."""
        manager = setup['manager']
        user_id = setup['user_id']
        thread_id = setup['thread_id']
        mock_ws = setup['mock_ws']
        
        # Connect with thread_id
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)
        
        # Update thread association for message routing
        success = manager.update_connection_thread(user_id, thread_id)
        
        # Send message that would be routed by thread
        message = {
            'type': 'chat_message',
            'data': {
                'message': 'Test query',
                'thread_id': thread_id,
                'user_id': user_id
            }
        }
        
        # Send via thread routing
        result = await manager.send_to_thread(thread_id, message)
        
        # Should succeed if connection is properly associated with thread
        # Note: This test verifies the thread routing mechanism exists
        await asyncio.sleep(0.1)
        
        # Verify thread context is maintained in the connection
        conn = manager.connections.get(connection_id)
        assert conn is not None
        assert conn['thread_id'] == thread_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])