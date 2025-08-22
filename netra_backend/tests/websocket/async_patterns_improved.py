"""
Improved WebSocket Async Testing Patterns
Demonstrates proper async patterns, resource management, and test isolation
Maximum 300 lines, functions ≤8 lines
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest


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


async def _test_connection_creation_and_messaging(manager: AsyncWebSocketTestManager) -> None:
    """Test connection creation and messaging functionality"""
    connection = await manager.create_connection("test_conn_1")
    assert connection.connection_id == "test_conn_1"
    
    await connection.send_json({"type": "test", "data": "hello"})
    connection.send_json.assert_called_once()


async def test_websocket_connection_lifecycle():
    """Test complete WebSocket connection lifecycle with proper cleanup"""
    async with websocket_test_context() as manager:
        await _test_connection_creation_and_messaging(manager)


async def _create_concurrent_connections(manager: AsyncWebSocketTestManager, count: int) -> List[AsyncMock]:
    """Create multiple WebSocket connections concurrently"""
    connection_tasks = [manager.create_connection(f"conn_{i}") for i in range(count)]
    connections = await asyncio.gather(*connection_tasks)
    assert len(connections) == count
    assert len(manager.connections) == count
    return connections


async def test_concurrent_websocket_operations():
    """Test concurrent WebSocket operations with proper async handling"""
    async with websocket_test_context() as manager:
        connections = await _create_concurrent_connections(manager, 10)
        await _test_concurrent_messaging(connections)


async def _send_concurrent_messages(connections: List[AsyncMock]) -> None:
    """Send messages concurrently to all connections"""
    message_tasks = [conn.send_json({"message": f"test_{i}"}) for i, conn in enumerate(connections)]
    await asyncio.gather(*message_tasks)


async def _verify_concurrent_messages(connections: List[AsyncMock]) -> None:
    """Verify all concurrent messages were sent"""
    for conn in connections:
        conn.send_json.assert_called_once()


async def _test_concurrent_messaging(connections: List[AsyncMock]) -> None:
    """Test concurrent messaging across multiple connections"""
    await _send_concurrent_messages(connections)
    await _verify_concurrent_messages(connections)


async def _setup_error_connection(manager: AsyncWebSocketTestManager) -> AsyncMock:
    """Setup connection that will raise ConnectionError"""
    connection = await manager.create_connection("error_test")
    connection.send_json.side_effect = ConnectionError("Connection lost")
    return connection


async def test_websocket_error_handling():
    """Test WebSocket error handling with proper async patterns"""
    async with websocket_test_context() as manager:
        connection = await _setup_error_connection(manager)
        with pytest.raises(ConnectionError):
            await connection.send_json({"test": "data"})


async def _slow_response(*args) -> str:
    """Simulate slow WebSocket response"""
    await asyncio.sleep(2.0)
    return "slow response"


async def _setup_timeout_connection(manager: AsyncWebSocketTestManager) -> AsyncMock:
    """Setup connection with slow response for timeout testing"""
    connection = await manager.create_connection("timeout_test")
    connection.send_json.side_effect = _slow_response
    return connection


async def test_websocket_timeout_handling():
    """Test WebSocket timeout handling with asyncio patterns"""
    async with websocket_test_context() as manager:
        connection = await _setup_timeout_connection(manager)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(connection.send_json({"test": "data"}), timeout=0.5)


async def _create_batch_connections(manager: AsyncWebSocketTestManager, count: int) -> List[AsyncMock]:
    """Create connections for batch operations"""
    return [await manager.create_connection(f"batch_{i}") for i in range(count)]


async def _verify_batch_messages_sent(connections: List[AsyncMock]) -> None:
    """Verify all connections sent messages"""
    for conn in connections:
        conn.send_json.assert_called_once()


async def test_websocket_batch_operations():
    """Test WebSocket batch operations with efficient async patterns"""
    async with websocket_test_context() as manager:
        connections = await _create_batch_connections(manager, 5)
        messages = [{"batch_id": i, "data": f"message_{i}"} for i in range(5)]
        await _send_batch_messages(connections, messages)
        await _verify_batch_messages_sent(connections)


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
    
    async def _execute_timed_operation(self, operation_coro, start_time: float) -> float:
        """Execute operation and calculate duration"""
        await operation_coro
        duration = time.time() - start_time
        self.connection_times.append(duration)
        return duration

    async def measure_connection_time(self, operation_coro) -> float:
        """Measure async operation timing"""
        start_time = time.time()
        try:
            return await self._execute_timed_operation(operation_coro, start_time)
        except Exception:
            self.error_count += 1
            raise
    
    def _get_basic_metrics(self) -> Dict:
        """Get basic timing metrics"""
        times = self.connection_times
        return {
            "avg_time": sum(times) / len(times),
            "max_time": max(times),
            "min_time": min(times)
        }

    def _calculate_timing_metrics(self) -> Dict:
        """Calculate timing metrics from connection data"""
        basic = self._get_basic_metrics()
        basic.update({"total_operations": len(self.connection_times), "error_count": self.error_count})
        return basic

    def get_performance_summary(self) -> Dict:
        """Get performance metrics summary"""
        if not self.connection_times:
            return {"error": "No timing data available"}
        return self._calculate_timing_metrics()


async def _measure_and_verify_performance(metrics: AsyncWebSocketMetrics, manager: AsyncWebSocketTestManager) -> None:
    """Measure performance and verify metrics"""
    await metrics.measure_connection_time(manager.create_connection("perf_test"))
    summary = metrics.get_performance_summary()
    assert summary["total_operations"] == 1
    assert summary["error_count"] == 0
    assert summary["avg_time"] >= 0


async def test_websocket_performance_metrics():
    """Test WebSocket performance measurement with async patterns"""
    metrics = AsyncWebSocketMetrics()
    async with websocket_test_context() as manager:
        await _measure_and_verify_performance(metrics, manager)


async def _test_resource_creation_and_cleanup(manager: AsyncWebSocketTestManager) -> None:
    """Test resource creation and cleanup"""
    await manager.create_connection("cleanup_test")
    assert len(manager.connections) == 1
    await manager.cleanup_all()
    assert len(manager.connections) == 0
    assert len(manager.cleanup_tasks) == 0


async def test_websocket_resource_cleanup():
    """Test proper resource cleanup in async WebSocket operations"""
    manager = AsyncWebSocketTestManager()
    try:
        await _test_resource_creation_and_cleanup(manager)
    finally:
        await manager.cleanup_all()


async def _create_shutdown_connections(manager: AsyncWebSocketTestManager, count: int) -> List[AsyncMock]:
    """Create connections for shutdown testing"""
    return [await manager.create_connection(f"shutdown_{i}") for i in range(count)]


async def _verify_connections_closed(connections: List[AsyncMock]) -> None:
    """Verify all connections were closed"""
    for conn in connections:
        conn.close.assert_called_once()


async def test_websocket_graceful_shutdown():
    """Test graceful shutdown patterns for WebSocket connections"""
    async with websocket_test_context() as manager:
        connections = await _create_shutdown_connections(manager, 3)
        await _graceful_shutdown(connections)
        await _verify_connections_closed(connections)


async def _wait_for_graceful_close(close_tasks: List) -> None:
    """Wait for graceful close with timeout"""
    await asyncio.wait_for(asyncio.gather(*close_tasks), timeout=5.0)


async def _force_close_connections(connections: List[AsyncMock]) -> None:
    """Force close connections if graceful timeout"""
    for conn in connections:
        await conn.close()


async def _graceful_shutdown(connections: List[AsyncMock]) -> None:
    """Perform graceful shutdown of WebSocket connections"""
    close_tasks = [conn.close() for conn in connections]
    try:
        await _wait_for_graceful_close(close_tasks)
    except asyncio.TimeoutError:
        await _force_close_connections(connections)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])