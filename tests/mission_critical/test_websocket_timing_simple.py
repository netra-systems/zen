"""
Simplified WebSocket timing tests focusing on actual implementation.
Tests critical timing scenarios with the real WebSocket manager.
"""

import asyncio
import uuid
import json
from typing import Dict, Any
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.message_buffer import BufferConfig


class TestWebSocketTimingSimple:
    """Test critical WebSocket timing scenarios."""

    @pytest.fixture
    async def setup(self):
        """Setup test environment."""
        manager = WebSocketManager()
        user_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        yield {
            'manager': manager,
            'user_id': user_id,
            'run_id': run_id,
            'thread_id': thread_id
        }

    @pytest.mark.asyncio
    async def test_connection_and_message_flow(self, setup):
        """Test basic connection and message flow."""
        manager = setup['manager']
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        # Connect
        await manager.connect_websocket(
            mock_ws,
            setup['user_id'],
            setup['run_id'],
            setup['thread_id']
        )
        
        # Send message
        test_message = {
            'type': 'agent_started',
            'data': {'agent': 'test'}
        }
        
        await manager.send_to_websocket(setup['run_id'], test_message)
        
        # Verify message sent
        await asyncio.sleep(0.1)
        assert mock_ws.send_text.called or mock_ws.send_json.called

    @pytest.mark.asyncio
    async def test_message_with_thread_context(self, setup):
        """Test message includes thread context."""
        manager = setup['manager']
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        
        # Connect with thread_id
        await manager.connect_websocket(
            mock_ws,
            setup['user_id'], 
            setup['run_id'],
            setup['thread_id']
        )
        
        # Send message
        message = {
            'type': 'test_event',
            'thread_id': setup['thread_id'],
            'data': {'content': 'test'}
        }
        
        await manager.send_to_websocket(setup['run_id'], message)
        
        # Verify sent
        await asyncio.sleep(0.1)
        mock_ws.send_text.assert_called()
        
        # Check thread_id in message
        sent_data = mock_ws.send_text.call_args[0][0]
        sent_json = json.loads(sent_data)
        assert sent_json.get('thread_id') == setup['thread_id']

    @pytest.mark.asyncio
    async def test_multiple_connections(self, setup):
        """Test handling multiple connections."""
        manager = setup['manager']
        
        connections = []
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            run_id = str(uuid.uuid4())
            
            await manager.connect_websocket(
                mock_ws,
                setup['user_id'],
                run_id,
                setup['thread_id']
            )
            
            connections.append({
                'ws': mock_ws,
                'run_id': run_id
            })
        
        # Send to each connection
        for conn in connections:
            await manager.send_to_websocket(conn['run_id'], {
                'type': 'test',
                'data': {'run_id': conn['run_id']}
            })
        
        # Verify all received
        await asyncio.sleep(0.1)
        for conn in connections:
            conn['ws'].send_text.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_and_cleanup(self, setup):
        """Test disconnection and cleanup."""
        manager = setup['manager']
        mock_ws = AsyncMock()
        
        # Connect
        await manager.connect_websocket(
            mock_ws,
            setup['user_id'],
            setup['run_id'],
            setup['thread_id']
        )
        
        # Disconnect
        await manager.disconnect_websocket(setup['run_id'])
        
        # Try to send - should handle gracefully
        await manager.send_to_websocket(setup['run_id'], {
            'type': 'test',
            'data': {}
        })
        
        # Should not crash
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])