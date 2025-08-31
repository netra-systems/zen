"""
Async tests for event_dispatcher
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
import asyncio
from netra_backend.app.websocket_core.handlers import MessageRouter

@pytest.mark.asyncio
class TestEventDispatcherAsync:
    """Async test suite for EventDispatcher"""
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        manager = EventDispatcher()
        connection = await manager.connect("test_client")
        assert connection is not None
        await manager.disconnect("test_client")
    
    async def test_message_handling(self):
        """Test message processing"""
        handler = EventDispatcher()
        result = await handler.process_message({"type": "test"})
        assert result["status"] == "processed"
    
    async def test_event_broadcasting(self):
        """Test event distribution"""
        dispatcher = EventDispatcher()
        await dispatcher.broadcast("test_event", {"data": "test"})
    
    async def test_concurrent_connections(self):
        """Test multiple connections"""
        manager = EventDispatcher()
        tasks = []
        for i in range(50):
            tasks.append(manager.connect(f"client_{i}"))
        connections = await asyncio.gather(*tasks)
        assert len(connections) == 50
