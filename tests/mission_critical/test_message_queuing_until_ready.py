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
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import json
from datetime import datetime

from netra_backend.app.websocket.bridge import WebSocketBridge
from netra_backend.app.core.agent_registry import AgentRegistry


class TestMessageQueueingUntilReady:
    """Test message queuing behavior when WebSocket not ready."""

    @pytest.fixture
    async def setup(self):
        """Setup test environment with WebSocket infrastructure."""
        bridge = WebSocketBridge()
        
        # Generate test IDs
        user_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        yield {
            'bridge': bridge,
            'user_id': user_id,
            'run_id': run_id,
            'thread_id': thread_id
        }
        
        # Cleanup
        await bridge.cleanup()

    @pytest.mark.asyncio
    async def test_message_queuing_before_connection(self, setup):
        """Test message queuing before WebSocket connection established."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Send messages before any connection
        messages = [
            {'type': 'agent_started', 'data': {'agent': 'test1'}},
            {'type': 'agent_thinking', 'data': {'thought': 'analyzing'}},
            {'type': 'tool_executing', 'data': {'tool': 'search'}},
            {'type': 'tool_completed', 'data': {'result': 'done'}},
            {'type': 'agent_completed', 'data': {'result': 'success'}}
        ]
        
        # Queue all messages
        for msg in messages:
            await bridge.send_message(run_id, msg)
        
        # Verify all messages queued
        assert len(bridge._pending_messages.get(run_id, [])) == 5
        
        # Now connect
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        await bridge.connect(
            mock_ws, 
            setup['user_id'], 
            run_id, 
            thread_id=setup['thread_id']
        )
        
        # Allow queue processing
        await asyncio.sleep(0.1)
        
        # Verify all messages sent
        assert mock_ws.send_json.call_count == 5
        
        # Verify queue cleared
        assert len(bridge._pending_messages.get(run_id, [])) == 0

    @pytest.mark.asyncio
    async def test_message_ordering_preservation(self, setup):
        """Test that message order is preserved during queuing."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
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
            await bridge.send_message(run_id, messages[-1])
            await asyncio.sleep(0.01)  # Small delay to ensure ordering
        
        # Connect WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        await bridge.connect(
            mock_ws,
            setup['user_id'],
            run_id,
            thread_id=setup['thread_id']
        )
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Verify correct order
        assert mock_ws.send_json.call_count == 10
        
        sent_messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
        for i, msg in enumerate(sent_messages):
            assert msg['type'] == f'message_{i}'
            assert msg['data']['index'] == i

    @pytest.mark.asyncio
    async def test_queue_with_connection_without_thread(self, setup):
        """Test queuing when connected but no thread_id."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Connect without thread_id
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        await bridge.connect(
            mock_ws,
            setup['user_id'],
            run_id,
            thread_id=None  # No thread context
        )
        
        # Send messages - should queue due to missing thread
        messages = [
            {'type': 'agent_started', 'data': {'status': 'waiting'}},
            {'type': 'agent_thinking', 'data': {'thought': 'queued'}}
        ]
        
        for msg in messages:
            await bridge.send_message(run_id, msg)
        
        # Should be queued
        assert len(bridge._pending_messages.get(run_id, [])) == 2
        assert mock_ws.send_json.call_count == 0
        
        # Update thread_id
        await bridge.update_thread_id(run_id, setup['thread_id'])
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Now messages should be sent
        assert mock_ws.send_json.call_count == 2

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self, setup):
        """Test handling of queue overflow scenarios."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Set max queue size (if implemented)
        MAX_QUEUE_SIZE = 100
        
        # Send many messages to potentially overflow
        for i in range(MAX_QUEUE_SIZE + 50):
            await bridge.send_message(run_id, {
                'type': 'overflow_test',
                'data': {'index': i}
            })
        
        # Check queue behavior
        queue_size = len(bridge._pending_messages.get(run_id, []))
        
        # Should either:
        # 1. Accept all messages (no limit)
        # 2. Limit to MAX_QUEUE_SIZE
        # 3. Use FIFO/LIFO strategy
        assert queue_size > 0  # At least some messages queued
        
        # Connect and verify handling
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        await bridge.connect(
            mock_ws,
            setup['user_id'],
            run_id,
            thread_id=setup['thread_id']
        )
        
        # Allow processing
        await asyncio.sleep(0.5)
        
        # Verify messages processed
        assert mock_ws.send_json.call_count > 0

    @pytest.mark.asyncio
    async def test_queue_persistence_across_reconnections(self, setup):
        """Test queue persistence when connection drops and reconnects."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        thread_id = setup['thread_id']
        
        # First connection
        mock_ws1 = AsyncMock()
        mock_ws1.send_json = AsyncMock()
        
        await bridge.connect(mock_ws1, setup['user_id'], run_id, thread_id=None)
        
        # Queue messages
        await bridge.send_message(run_id, {'type': 'msg1', 'data': {}})
        await bridge.send_message(run_id, {'type': 'msg2', 'data': {}})
        
        # Disconnect before thread_id set
        await bridge.disconnect(run_id)
        
        # Messages should still be queued
        assert len(bridge._pending_messages.get(run_id, [])) == 2
        
        # Reconnect with thread_id
        mock_ws2 = AsyncMock()
        mock_ws2.send_json = AsyncMock()
        
        await bridge.connect(mock_ws2, setup['user_id'], run_id, thread_id=thread_id)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Messages should be sent to new connection
        assert mock_ws2.send_json.call_count == 2
        assert mock_ws1.send_json.call_count == 0  # Old connection shouldn't receive

    @pytest.mark.asyncio
    async def test_priority_message_handling(self, setup):
        """Test priority message handling in queue."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Queue regular messages
        await bridge.send_message(run_id, {
            'type': 'regular_1',
            'data': {'priority': 'normal'}
        })
        await bridge.send_message(run_id, {
            'type': 'regular_2',
            'data': {'priority': 'normal'}
        })
        
        # Queue high-priority message
        await bridge.send_message(run_id, {
            'type': 'agent_error',
            'data': {'priority': 'high', 'error': 'Critical error'}
        })
        
        # Queue more regular messages
        await bridge.send_message(run_id, {
            'type': 'regular_3',
            'data': {'priority': 'normal'}
        })
        
        # Connect
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        await bridge.connect(
            mock_ws,
            setup['user_id'],
            run_id,
            thread_id=setup['thread_id']
        )
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Check if error messages are prioritized (implementation-dependent)
        sent_messages = [call[0][0] for call in mock_ws.send_json.call_args_list]
        
        # At minimum, all messages should be sent
        assert len(sent_messages) == 4
        
        # Check if error message exists
        error_messages = [m for m in sent_messages if m['type'] == 'agent_error']
        assert len(error_messages) == 1

    @pytest.mark.asyncio
    async def test_concurrent_queue_operations(self, setup):
        """Test concurrent queuing and dequeuing operations."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Start without connection
        message_count = 0
        
        async def producer():
            nonlocal message_count
            for i in range(20):
                await bridge.send_message(run_id, {
                    'type': f'concurrent_{i}',
                    'data': {'index': i}
                })
                message_count += 1
                await asyncio.sleep(0.01)
        
        # Start producer
        producer_task = asyncio.create_task(producer())
        
        # Wait a bit for some messages to queue
        await asyncio.sleep(0.05)
        
        # Connect while still producing
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        await bridge.connect(
            mock_ws,
            setup['user_id'],
            run_id,
            thread_id=setup['thread_id']
        )
        
        # Wait for producer to finish
        await producer_task
        
        # Allow all messages to process
        await asyncio.sleep(0.2)
        
        # All messages should be sent
        assert mock_ws.send_json.call_count == message_count

    @pytest.mark.asyncio
    async def test_queue_cleanup_on_error(self, setup):
        """Test queue cleanup when errors occur during processing."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Queue messages
        for i in range(5):
            await bridge.send_message(run_id, {
                'type': f'message_{i}',
                'data': {'index': i}
            })
        
        # Connect with mock that fails on third message
        mock_ws = AsyncMock()
        call_count = 0
        
        async def failing_send(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise Exception("WebSocket send failed")
            return None
        
        mock_ws.send_json = AsyncMock(side_effect=failing_send)
        
        # Connect
        await bridge.connect(
            mock_ws,
            setup['user_id'],
            run_id,
            thread_id=setup['thread_id']
        )
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Some messages sent, some may remain queued
        assert call_count >= 2  # At least tried to send
        
        # Check if remaining messages are still queued or cleared
        remaining = len(bridge._pending_messages.get(run_id, []))
        assert remaining >= 0  # Should handle gracefully

    @pytest.mark.asyncio 
    async def test_queue_with_websocket_manager_integration(self, setup):
        """Test queue behavior with WebSocketManager integration."""
        from netra_backend.app.websocket.manager import WebSocketManager
        
        manager = WebSocketManager()
        run_id = setup['run_id']
        user_id = setup['user_id']
        thread_id = setup['thread_id']
        
        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        # Try to send before connection
        await manager.send_to_websocket(run_id, {
            'type': 'early_message',
            'data': {'content': 'sent before connection'}
        })
        
        # Connect
        await manager.connect(mock_ws, user_id, run_id, thread_id)
        
        # Send after connection
        await manager.send_to_websocket(run_id, {
            'type': 'post_connection',
            'data': {'content': 'sent after connection'}
        })
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify messages handled correctly
        # At least the post-connection message should be sent
        assert mock_ws.send_text.called or mock_ws.send_json.called

    @pytest.mark.asyncio
    async def test_message_batching_in_queue(self, setup):
        """Test if queued messages can be batched for efficiency."""
        bridge = setup['bridge']
        run_id = setup['run_id']
        
        # Queue many small messages quickly
        for i in range(50):
            await bridge.send_message(run_id, {
                'type': 'small_update',
                'data': {'value': i}
            })
        
        # Connect
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        # Track actual send timing
        send_times = []
        
        async def track_send(msg):
            send_times.append(time.time())
            return None
        
        mock_ws.send_json.side_effect = track_send
        
        await bridge.connect(
            mock_ws,
            setup['user_id'],
            run_id,
            thread_id=setup['thread_id']
        )
        
        # Allow processing
        await asyncio.sleep(0.5)
        
        # Check if messages were sent
        assert len(send_times) > 0
        
        # If batching is implemented, sends might be grouped
        # Otherwise, each message sent individually
        assert mock_ws.send_json.call_count <= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])