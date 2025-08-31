"""
Async tests for session_manager
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
import asyncio
from netra_backend.app.websocket_core.manager import WebSocketManager

@pytest.mark.asyncio
class TestSessionManagerAsync:
    """Async test suite for SessionManager"""
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        manager = SessionManager()
        connection = await manager.connect("test_client")
        assert connection is not None
        await manager.disconnect("test_client")
    
    async def test_message_handling(self):
        """Test message processing"""
        handler = SessionManager()
        result = await handler.process_message({"type": "test"})
        assert result["status"] == "processed"
    
    async def test_event_broadcasting(self):
        """Test event distribution"""
        dispatcher = SessionManager()
        await dispatcher.broadcast("test_event", {"data": "test"})
    
    async def test_concurrent_connections(self):
        """Test multiple connections"""
        manager = SessionManager()
        tasks = []
        for i in range(50):
            tasks.append(manager.connect(f"client_{i}"))
        connections = await asyncio.gather(*tasks)
        assert len(connections) == 50
