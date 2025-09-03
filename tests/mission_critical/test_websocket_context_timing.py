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
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import json

from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.message_buffer import MessageBuffer
from netra_backend.app.services.message_handlers import handle_ai_backend_message
from netra_backend.app.core.agent_registry import AgentRegistry


class TestWebSocketContextTiming:
    """Test critical WebSocket timing and race condition scenarios."""

    @pytest.fixture
    async def setup(self):
        """Setup test environment with WebSocket infrastructure."""
        # Create WebSocket bridge
        bridge = WebSocketBridge()
        
        # Create mock WebSocket connection
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        # Generate test IDs
        user_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        yield {
            'bridge': bridge,
            'mock_ws': mock_ws,
            'user_id': user_id,
            'run_id': run_id,
            'thread_id': thread_id
        }
        
        # Cleanup
        await bridge.cleanup()

    @pytest.mark.asyncio
    async def test_connection_without_initial_thread_id(self, setup):
        """Test WebSocket connection without initial thread_id."""
        bridge = setup['bridge']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect without thread_id
        await bridge.connect(mock_ws, user_id, run_id, thread_id=None)
        
        # Verify connection established
        assert bridge._connections.get(run_id) is not None
        conn = bridge._connections[run_id]
        assert conn['websocket'] == mock_ws
        assert conn['user_id'] == user_id
        assert conn.get('thread_id') is None  # Should be None initially
        
        # Send a message without thread context
        test_message = {
            'type': 'agent_started',
            'data': {'agent_name': 'test_agent'}
        }
        
        # Should queue the message since no thread_id
        await bridge.send_message(run_id, test_message)
        
        # Verify message was queued
        assert len(bridge._pending_messages.get(run_id, [])) == 1
        
        # Now update with thread_id
        thread_id = setup['thread_id']
        await bridge.update_thread_id(run_id, thread_id)
        
        # Verify thread_id updated
        assert conn['thread_id'] == thread_id
        
        # Verify queued message was sent
        await asyncio.sleep(0.1)  # Allow async processing
        mock_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_message_arrives_before_thread_context(self, setup):
        """Test message arriving before thread context is established."""
        bridge = setup['bridge']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect without thread_id
        await bridge.connect(mock_ws, user_id, run_id, thread_id=None)
        
        # Send multiple messages before thread context
        messages = [
            {'type': 'agent_thinking', 'data': {'thought': 'Analyzing...'}},
            {'type': 'tool_executing', 'data': {'tool': 'search'}},
            {'type': 'tool_completed', 'data': {'result': 'Found 10 items'}}
        ]
        
        for msg in messages:
            await bridge.send_message(run_id, msg)
        
        # Verify all messages queued
        assert len(bridge._pending_messages.get(run_id, [])) == 3
        
        # Update thread context
        thread_id = setup['thread_id']
        await bridge.update_thread_id(run_id, thread_id)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify all messages sent in order
        assert mock_ws.send_json.call_count == 3
        
        # Verify message order preserved
        sent_messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
        for i, original_msg in enumerate(messages):
            assert sent_messages[i]['type'] == original_msg['type']
            assert sent_messages[i]['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_rapid_thread_switching(self, setup):
        """Test rapid thread switching during message processing."""
        bridge = setup['bridge']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect with initial thread
        thread1 = str(uuid.uuid4())
        await bridge.connect(mock_ws, user_id, run_id, thread_id=thread1)
        
        # Send message with thread1
        await bridge.send_message(run_id, {
            'type': 'agent_started',
            'data': {'agent': 'agent1'}
        })
        
        # Rapidly switch threads multiple times
        thread2 = str(uuid.uuid4())
        thread3 = str(uuid.uuid4())
        
        # Quick succession of thread changes
        await bridge.update_thread_id(run_id, thread2)
        await bridge.send_message(run_id, {
            'type': 'agent_thinking',
            'data': {'thought': 'Processing with thread2'}
        })
        
        await bridge.update_thread_id(run_id, thread3)
        await bridge.send_message(run_id, {
            'type': 'agent_completed',
            'data': {'result': 'Done with thread3'}
        })
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify messages sent with correct thread IDs
        sent_messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
        
        assert sent_messages[0]['thread_id'] == thread1
        assert sent_messages[1]['thread_id'] == thread2
        assert sent_messages[2]['thread_id'] == thread3

    @pytest.mark.asyncio
    async def test_multiple_simultaneous_connections_timing(self, setup):
        """Test multiple simultaneous connections with different timing."""
        bridge = setup['bridge']
        
        # Create multiple connections with different timing
        connections = []
        for i in range(5):
            mock_ws = AsyncMock()
            mock_ws.send_json = AsyncMock()
            user_id = str(uuid.uuid4())
            run_id = str(uuid.uuid4())
            
            # Some with thread_id, some without
            thread_id = str(uuid.uuid4()) if i % 2 == 0 else None
            
            await bridge.connect(mock_ws, user_id, run_id, thread_id=thread_id)
            
            connections.append({
                'mock_ws': mock_ws,
                'user_id': user_id,
                'run_id': run_id,
                'thread_id': thread_id,
                'index': i
            })
        
        # Send messages to all connections
        for conn in connections:
            await bridge.send_message(conn['run_id'], {
                'type': 'test_message',
                'data': {'index': conn['index']}
            })
        
        # Update thread_ids for connections that didn't have them
        for conn in connections:
            if conn['thread_id'] is None:
                new_thread_id = str(uuid.uuid4())
                await bridge.update_thread_id(conn['run_id'], new_thread_id)
                conn['thread_id'] = new_thread_id
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Verify all messages sent
        for conn in connections:
            conn['mock_ws'].send_json.assert_called()
            sent_msg = conn['mock_ws'].send_json.call_args[0][0]
            assert sent_msg['thread_id'] == conn['thread_id']
            assert sent_msg['data']['index'] == conn['index']

    @pytest.mark.asyncio
    async def test_agent_execution_before_websocket_ready(self, setup):
        """Test agent execution starting before WebSocket is ready."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Simulate agent sending messages before WebSocket connected
        early_messages = [
            {'type': 'agent_started', 'data': {'agent': 'early_bird'}},
            {'type': 'agent_thinking', 'data': {'thought': 'Processing...'}}
        ]
        
        # Try to send messages before connection
        for msg in early_messages:
            await bridge.send_message(run_id, msg)
        
        # Messages should be queued
        assert len(bridge._pending_messages.get(run_id, [])) >= 2
        
        # Now establish connection
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        thread_id = setup['thread_id']
        
        await bridge.connect(mock_ws, user_id, run_id, thread_id=thread_id)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify queued messages were sent
        assert mock_ws.send_json.call_count >= 2
        
        # Verify messages have correct thread_id
        for call in mock_ws.send_json.call_args_list:
            sent_msg = call[0][0]
            assert sent_msg['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_thread_context_update_failures_and_retries(self, setup):
        """Test handling of thread context update failures and retries."""
        bridge = setup['bridge']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect without thread_id
        await bridge.connect(mock_ws, user_id, run_id, thread_id=None)
        
        # Queue messages
        await bridge.send_message(run_id, {
            'type': 'test_message',
            'data': {'content': 'waiting for thread'}
        })
        
        # Simulate failed thread update attempts
        with patch.object(bridge, '_process_pending_messages', side_effect=Exception("Thread update failed")):
            thread_id = setup['thread_id']
            
            # First attempt - should fail
            with pytest.raises(Exception):
                await bridge.update_thread_id(run_id, thread_id)
        
        # Verify message still pending
        assert len(bridge._pending_messages.get(run_id, [])) == 1
        
        # Successful retry
        await bridge.update_thread_id(run_id, thread_id)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify message sent after successful retry
        mock_ws.send_json.assert_called()
        sent_msg = mock_ws.send_json.call_args[0][0]
        assert sent_msg['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_concurrent_message_and_thread_update(self, setup):
        """Test concurrent message sending and thread updates."""
        bridge = setup['bridge']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect with initial thread
        thread1 = str(uuid.uuid4())
        await bridge.connect(mock_ws, user_id, run_id, thread_id=thread1)
        
        # Create concurrent tasks
        async def send_messages():
            for i in range(10):
                await bridge.send_message(run_id, {
                    'type': f'message_{i}',
                    'data': {'index': i}
                })
                await asyncio.sleep(0.01)
        
        async def update_threads():
            for i in range(3):
                new_thread = str(uuid.uuid4())
                await bridge.update_thread_id(run_id, new_thread)
                await asyncio.sleep(0.03)
        
        # Run concurrently
        await asyncio.gather(send_messages(), update_threads())
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Verify all messages sent
        assert mock_ws.send_json.call_count == 10
        
        # Verify messages have valid thread_ids
        for call in mock_ws.send_json.call_args_list:
            sent_msg = call[0][0]
            assert 'thread_id' in sent_msg
            assert sent_msg['thread_id'] is not None

    @pytest.mark.asyncio
    async def test_websocket_disconnection_during_thread_update(self, setup):
        """Test WebSocket disconnection during thread update."""
        bridge = setup['bridge']
        mock_ws = setup['mock_ws']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect without thread_id
        await bridge.connect(mock_ws, user_id, run_id, thread_id=None)
        
        # Queue messages
        await bridge.send_message(run_id, {
            'type': 'important_message',
            'data': {'content': 'must deliver'}
        })
        
        # Disconnect during thread update
        await bridge.disconnect(run_id)
        
        # Try to update thread (should handle gracefully)
        thread_id = setup['thread_id']
        await bridge.update_thread_id(run_id, thread_id)
        
        # Reconnect
        new_mock_ws = AsyncMock()
        new_mock_ws.send_json = AsyncMock()
        await bridge.connect(new_mock_ws, user_id, run_id, thread_id=thread_id)
        
        # Verify pending message delivered to new connection
        await asyncio.sleep(0.1)
        new_mock_ws.send_json.assert_called()
        
        sent_msg = new_mock_ws.send_json.call_args[0][0]
        assert sent_msg['type'] == 'important_message'
        assert sent_msg['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_thread_id_propagation_to_message_handler(self, setup):
        """Test thread_id propagation from WebSocket to message handler."""
        user_id = setup['user_id']
        thread_id = setup['thread_id']
        
        # Mock the agent registry
        with patch('netra_backend.app.services.message_handlers.AgentRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.get_instance.return_value = mock_instance
            
            # Create test message
            test_message = {
                'message': 'Test query',
                'conversation_id': thread_id,
                'user_id': user_id
            }
            
            # Call message handler
            result = await handle_ai_backend_message(test_message)
            
            # Verify thread_id was passed correctly
            mock_instance.execute_agent.assert_called()
            call_args = mock_instance.execute_agent.call_args
            
            # Check context includes thread_id
            assert 'thread_id' in call_args[1] or thread_id in str(call_args)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])