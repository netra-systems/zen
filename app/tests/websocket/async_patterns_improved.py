"""
Improved WebSocket Async Testing Patterns
Demonstrates proper async patterns, resource management, and test isolation
Maximum 300 lines, functions ≤8 lines
"""

import asyncio
import pytest
import time
from contextlib import asynccontextmanager
from typing import List, Dict, Optional, AsyncGenerator
from unittest.mock import AsyncMock


class AsyncWebSocketTestManager:
    """Enhanced WebSocket test manager with proper async resource management"""
    
    def __init__(self):
        self.connections: List[AsyncMock] = []
        self.cleanup_tasks: List[asyncio.Task] = []
    
    async def create_connection(self, connection_id: str) -> AsyncMock:
        """Create WebSocket connection with proper async setup"""
        mock_ws = self._setup_mock_websocket(connection_id)
        self.connections.append(mock_ws)
        return mock_ws
    
    def _setup_mock_websocket(self, connection_id: str) -> AsyncMock:
        """Setup mock WebSocket with consistent interface"""
        mock_ws = AsyncMock()
        mock_ws.connection_id = connection_id
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws
    
    async def cleanup_all(self) -> None:
        """Cleanup all connections and background tasks"""
        await self._cleanup_connections()
        await self._cleanup_tasks()
    
    async def _cleanup_connections(self) -> None:
        """Close all active connections"""
        for connection in self.connections:
            await connection.close()
        self.connections.clear()
    
    async def _cleanup_tasks(self) -> None:
        """Cancel and cleanup background tasks"""
        for task in self.cleanup_tasks:
            task.cancel()
        await asyncio.gather(*self.cleanup_tasks, return_exceptions=True)
        self.cleanup_tasks.clear()


@asynccontextmanager
async def websocket_test_context() -> AsyncGenerator[AsyncWebSocketTestManager, None]:
    """Async context manager for WebSocket test isolation"""
    manager = AsyncWebSocketTestManager()
    try:
        yield manager
    finally:
        await manager.cleanup_all()


async def test_websocket_connection_lifecycle():
    """Test complete WebSocket connection lifecycle with proper cleanup"""
    async with websocket_test_context() as manager:
        # Create connection
        connection = await manager.create_connection("test_conn_1")
        assert connection.connection_id == "test_conn_1"
        
        # Test messaging
        await connection.send_json({"type": "test", "data": "hello"})
        connection.send_json.assert_called_once()
        
        # Verify cleanup happens automatically


async def test_concurrent_websocket_operations():
    """Test concurrent WebSocket operations with proper async handling"""
    async with websocket_test_context() as manager:
        # Create multiple connections concurrently
        connection_tasks = [
            manager.create_connection(f"conn_{i}")
            for i in range(10)
        ]
        connections = await asyncio.gather(*connection_tasks)
        
        assert len(connections) == 10
        assert len(manager.connections) == 10
        
        # Test concurrent messaging
        await _test_concurrent_messaging(connections)


async def _test_concurrent_messaging(connections: List[AsyncMock]) -> None:
    """Test concurrent messaging across multiple connections"""
    message_tasks = [
        conn.send_json({"message": f"test_{i}"})
        for i, conn in enumerate(connections)
    ]
    await asyncio.gather(*message_tasks)
    
    # Verify all messages sent
    for conn in connections:
        conn.send_json.assert_called_once()


async def test_websocket_error_handling():
    """Test WebSocket error handling with proper async patterns"""
    async with websocket_test_context() as manager:
        connection = await manager.create_connection("error_test")
        
        # Setup error scenario
        connection.send_json.side_effect = ConnectionError("Connection lost")
        
        # Test error handling
        with pytest.raises(ConnectionError):
            await connection.send_json({"test": "data"})


async def test_websocket_timeout_handling():
    """Test WebSocket timeout handling with asyncio patterns"""
    async with websocket_test_context() as manager:
        connection = await manager.create_connection("timeout_test")
        
        # Setup slow response
        async def slow_response(*args):
            await asyncio.sleep(2.0)
            return "slow response"
        
        connection.send_json.side_effect = slow_response
        
        # Test timeout handling
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                connection.send_json({"test": "data"}),
                timeout=0.5
            )


async def test_websocket_batch_operations():
    """Test WebSocket batch operations with efficient async patterns"""
    async with websocket_test_context() as manager:
        connections = [
            await manager.create_connection(f"batch_{i}")
            for i in range(5)
        ]
        
        # Batch message sending
        messages = [{"batch_id": i, "data": f"message_{i}"} for i in range(5)]
        await _send_batch_messages(connections, messages)
        
        # Verify all sent
        for conn in connections:
            conn.send_json.assert_called_once()


async def _send_batch_messages(connections: List[AsyncMock], messages: List[Dict]) -> None:
    """Send messages in batches with proper async handling"""
    tasks = [
        conn.send_json(msg)
        for conn, msg in zip(connections, messages)
    ]
    await asyncio.gather(*tasks)


class AsyncWebSocketMetrics:
    """Async metrics collection for WebSocket performance testing"""
    
    def __init__(self):
        self.connection_times: List[float] = []
        self.message_times: List[float] = []
        self.error_count: int = 0
    
    async def measure_connection_time(self, operation_coro) -> float:
        """Measure async operation timing"""
        start_time = time.time()
        try:
            await operation_coro
            duration = time.time() - start_time
            self.connection_times.append(duration)
            return duration
        except Exception:
            self.error_count += 1
            raise
    
    def get_performance_summary(self) -> Dict:
        """Get performance metrics summary"""
        if not self.connection_times:
            return {"error": "No timing data available"}
        
        return {
            "avg_time": sum(self.connection_times) / len(self.connection_times),
            "max_time": max(self.connection_times),
            "min_time": min(self.connection_times),
            "total_operations": len(self.connection_times),
            "error_count": self.error_count
        }


async def test_websocket_performance_metrics():
    """Test WebSocket performance measurement with async patterns"""
    metrics = AsyncWebSocketMetrics()
    
    async with websocket_test_context() as manager:
        # Measure connection creation time
        await metrics.measure_connection_time(
            manager.create_connection("perf_test")
        )
        
        # Verify metrics collected
        summary = metrics.get_performance_summary()
        assert summary["total_operations"] == 1
        assert summary["error_count"] == 0
        assert summary["avg_time"] >= 0


async def test_websocket_resource_cleanup():
    """Test proper resource cleanup in async WebSocket operations"""
    manager = AsyncWebSocketTestManager()
    
    try:
        # Create resources
        await manager.create_connection("cleanup_test")
        assert len(manager.connections) == 1
        
        # Test cleanup
        await manager.cleanup_all()
        assert len(manager.connections) == 0
        assert len(manager.cleanup_tasks) == 0
    finally:
        # Ensure cleanup even if test fails
        await manager.cleanup_all()


async def test_websocket_graceful_shutdown():
    """Test graceful shutdown patterns for WebSocket connections"""
    async with websocket_test_context() as manager:
        connections = [
            await manager.create_connection(f"shutdown_{i}")
            for i in range(3)
        ]
        
        # Test graceful shutdown
        await _graceful_shutdown(connections)
        
        # Verify all connections closed
        for conn in connections:
            conn.close.assert_called_once()


async def _graceful_shutdown(connections: List[AsyncMock]) -> None:
    """Perform graceful shutdown of WebSocket connections"""
    # Send close messages
    close_tasks = [conn.close() for conn in connections]
    
    # Wait with timeout for graceful close
    try:
        await asyncio.wait_for(
            asyncio.gather(*close_tasks),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        # Force close if graceful timeout
        for conn in connections:
            await conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])