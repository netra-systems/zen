"""
Async tests for rate_limiter
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
import asyncio
from netra_backend.app.websocket_core.rate_limiter import WebSocketRateLimiter
from shared.isolated_environment import IsolatedEnvironment

@pytest.mark.asyncio
class TestRateLimiterAsync:
    """Async test suite for RateLimiter"""
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        manager = RateLimiter()
        connection = await manager.connect("test_client")
        assert connection is not None
        await manager.disconnect("test_client")
    
    async def test_message_handling(self):
        """Test message processing"""
        handler = RateLimiter()
        result = await handler.process_message({"type": "test"})
        assert result["status"] == "processed"
    
    async def test_event_broadcasting(self):
        """Test event distribution"""
        dispatcher = RateLimiter()
        await dispatcher.broadcast("test_event", {"data": "test"})
    
    async def test_concurrent_connections(self):
        """Test multiple connections"""
        manager = RateLimiter()
        tasks = []
        for i in range(50):
            tasks.append(manager.connect(f"client_{i}"))
        connections = await asyncio.gather(*tasks)
        assert len(connections) == 50
