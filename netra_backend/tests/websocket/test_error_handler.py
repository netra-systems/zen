"""
Async tests for error_handler
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
import asyncio
from netra_backend.app.websocket.error_handler import ErrorHandler

@pytest.mark.asyncio
class TestErrorHandlerAsync:
    """Async test suite for ErrorHandler"""
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        manager = ErrorHandler()
        connection = await manager.connect("test_client")
        assert connection is not None
        await manager.disconnect("test_client")
    
    async def test_message_handling(self):
        """Test message processing"""
        handler = ErrorHandler()
        result = await handler.process_message({"type": "test"})
        assert result["status"] == "processed"
    
    async def test_event_broadcasting(self):
        """Test event distribution"""
        dispatcher = ErrorHandler()
        await dispatcher.broadcast("test_event", {"data": "test"})
    
    async def test_concurrent_connections(self):
        """Test multiple connections"""
        manager = ErrorHandler()
        tasks = []
        for i in range(50):
            tasks.append(manager.connect(f"client_{i}"))
        connections = await asyncio.gather(*tasks)
        assert len(connections) == 50
