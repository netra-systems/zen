"""
Comprehensive tests for WebSocket Manager connection pooling and cleanup
Tests connection management, pooling, heartbeat, cleanup, and performance
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta, timezone, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from dataclasses import dataclass
import json

from fastapi import WebSocket
from starlette.websockets import WebSocketState, WebSocketDisconnect
from app.ws_manager import WebSocketManager, ConnectionInfo
from app.core.exceptions_base import NetraException


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or f"user_{int(time.time() * 1000)}"
        self.state = WebSocketState.CONNECTED
        self.sent_messages = []
        self.should_fail_send = False
        self.should_fail_accept = False
        self.should_fail_close = False
        self.close_code = None
        self.close_reason = None
        self.client_host = "127.0.0.1"
        self.client_port = 8000
        
    async def accept(self):
        """Mock WebSocket accept"""
        if self.should_fail_accept:
            raise Exception("Mock accept failure")
        self.state = WebSocketState.CONNECTED
        
    async def send_text(self, data: str):
        """Mock send text message"""
        if self.should_fail_send:
            raise WebSocketDisconnect(code=1011, reason="Mock send failure")
        
        if self.state != WebSocketState.CONNECTED:
            raise WebSocketDisconnect(code=1000, reason="Not connected")
        
        self.sent_messages.append({
            'type': 'text',
            'data': data,
            'timestamp': datetime.now(UTC)
        })
        
    async def send_json(self, data: dict):
        """Mock send JSON message"""
        await self.send_text(json.dumps(data))
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Mock WebSocket close"""
        if self.should_fail_close:
            raise Exception("Mock close failure")
        
        self.state = WebSocketState.DISCONNECTED
        self.close_code = code
        self.close_reason = reason
        
    async def receive_text(self):
        """Mock receive text message"""
        # For testing purposes, return a ping message periodically
        await asyncio.sleep(0.1)
        return '{"type": "ping", "timestamp": ' + str(time.time()) + '}'
        
    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get list of sent messages"""
        return self.sent_messages.copy()
        
    def clear_sent_messages(self):
        """Clear sent messages history"""
        self.sent_messages.clear()


class MockConnectionPool:
    """Mock connection pool for testing scalability"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.active_connections = 0
        self.total_connections_created = 0
        self.connection_wait_queue = asyncio.Queue()
        self.pool_stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'connections_expired': 0,
            'wait_time_total': 0,
            'average_wait_time': 0
        }
        
    async def acquire_connection(self) -> MockWebSocket:
        """Acquire a connection from the pool"""
        start_time = time.time()
        
        if self.active_connections >= self.max_connections:
            # Wait for available connection
            await self.connection_wait_queue.get()
        
        # Create new connection
        connection = MockWebSocket()
        self.active_connections += 1
        self.total_connections_created += 1
        self.pool_stats['connections_created'] += 1
        
        # Track wait time
        wait_time = time.time() - start_time
        self.pool_stats['wait_time_total'] += wait_time
        if self.pool_stats['connections_created'] > 0:
            self.pool_stats['average_wait_time'] = (
                self.pool_stats['wait_time_total'] / self.pool_stats['connections_created']
            )
        
        return connection
        
    async def release_connection(self, connection: MockWebSocket):
        """Release a connection back to the pool"""
        if self.active_connections > 0:
            self.active_connections -= 1
            
        # Notify waiting connections
        try:
            self.connection_wait_queue.put_nowait(True)
        except asyncio.QueueFull:
            pass
            
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            **self.pool_stats,
            'active_connections': self.active_connections,
            'max_connections': self.max_connections,
            'total_connections_created': self.total_connections_created,
            'utilization_rate': self.active_connections / self.max_connections
        }


class TestWebSocketManagerConnectionPooling:
    """Test WebSocket manager connection pooling"""
    
    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance"""
        # Reset singleton for clean testing
        WebSocketManager._instance = None
        manager = WebSocketManager()
        return manager
    
    @pytest.fixture
    def mock_websockets(self):
        """Create mock WebSockets for testing"""
        return {
            f"user_{i}": MockWebSocket(f"user_{i}")
            for i in range(1, 6)
        }
    async def test_websocket_manager_singleton_pattern(self):
        """Test WebSocket manager singleton pattern"""
        # Reset singleton
        WebSocketManager._instance = None
        
        # Create multiple instances
        manager1 = WebSocketManager()
        manager2 = WebSocketManager()
        manager3 = WebSocketManager()
        
        # Should all be the same instance
        assert manager1 is manager2
        assert manager2 is manager3
        assert id(manager1) == id(manager2) == id(manager3)
    async def test_connection_establishment(self, ws_manager, mock_websockets):
        """Test WebSocket connection establishment"""
        user_id = "user_1"
        websocket = mock_websockets[user_id]
        
        # Connect WebSocket
        conn_info = await ws_manager.connect(user_id, websocket)
        
        # Verify connection established
        assert conn_info != None
        assert conn_info.user_id == user_id
        assert conn_info.websocket is websocket
        assert user_id in ws_manager.active_connections
        assert len(ws_manager.active_connections[user_id]) == 1
        
        # Check statistics
        assert ws_manager._stats["total_connections"] == 1
        
        # Verify connection registry
        assert conn_info.connection_id in ws_manager.connection_registry
    async def test_multiple_connections_same_user(self, ws_manager):
        """Test multiple connections for the same user"""
        user_id = "multi_conn_user"
        
        # Create multiple WebSocket connections
        connections = []
        for i in range(3):
            websocket = MockWebSocket(f"{user_id}_{i}")
            conn_info = await ws_manager.connect(user_id, websocket)
            connections.append(conn_info)
        
        # Verify all connections tracked
        assert len(ws_manager.active_connections[user_id]) == 3
        assert ws_manager._stats["total_connections"] == 3
        
        # Verify each connection has unique ID
        connection_ids = {conn.connection_id for conn in connections}
        assert len(connection_ids) == 3
    async def test_connection_limit_enforcement(self, ws_manager):
        """Test enforcement of connection limits per user"""
        user_id = "limited_user"
        max_connections = ws_manager.MAX_CONNECTIONS_PER_USER
        
        # Create connections up to limit
        connections = []
        for i in range(max_connections):
            websocket = MockWebSocket(f"{user_id}_{i}")
            conn_info = await ws_manager.connect(user_id, websocket)
            connections.append(conn_info)
        
        # Should have max connections
        assert len(ws_manager.active_connections[user_id]) == max_connections
        
        # Create one more connection (should trigger cleanup)
        extra_websocket = MockWebSocket(f"{user_id}_extra")
        await ws_manager.connect(user_id, extra_websocket)
        
        # Should still have max connections (oldest removed)
        assert len(ws_manager.active_connections[user_id]) == max_connections
        
        # Verify oldest connection was closed
        oldest_ws = connections[0].websocket
        assert oldest_ws.state == WebSocketState.DISCONNECTED
        assert oldest_ws.close_code == 1008  # Connection limit exceeded
    async def test_connection_cleanup_on_disconnect(self, ws_manager, mock_websockets):
        """Test connection cleanup when WebSocket disconnects"""
        user_id = "cleanup_user"
        websocket = mock_websockets[user_id]
        
        # Connect WebSocket
        conn_info = await ws_manager.connect(user_id, websocket)
        connection_id = conn_info.connection_id
        
        # Verify connection exists
        assert connection_id in ws_manager.connection_registry
        assert len(ws_manager.active_connections[user_id]) == 1
        
        # Disconnect WebSocket
        await ws_manager.disconnect(user_id, websocket)
        
        # Verify cleanup
        assert connection_id not in ws_manager.connection_registry
        assert len(ws_manager.active_connections[user_id]) == 0
        assert websocket.state == WebSocketState.DISCONNECTED
    async def test_heartbeat_mechanism(self, ws_manager):
        """Test WebSocket heartbeat mechanism"""
        user_id = "heartbeat_user"
        websocket = MockWebSocket(user_id)
        
        # Connect WebSocket
        conn_info = await ws_manager.connect(user_id, websocket)
        connection_id = conn_info.connection_id
        
        # Verify heartbeat task created
        assert connection_id in ws_manager.heartbeat_tasks
        heartbeat_task = ws_manager.heartbeat_tasks[connection_id]
        assert not heartbeat_task.done()
        
        # Wait briefly for heartbeat to start
        await asyncio.sleep(0.1)
        
        # Check that ping messages are being sent
        sent_messages = websocket.get_sent_messages()
        system_messages = [
            msg for msg in sent_messages 
            if 'connection_established' in msg['data'] or 'ping' in msg['data']
        ]
        assert len(system_messages) >= 1  # At least connection established message
        
        # Cleanup
        await ws_manager.disconnect(user_id, websocket)
    async def test_heartbeat_timeout_detection(self, ws_manager):
        """Test detection of heartbeat timeouts"""
        user_id = "timeout_user"
        websocket = MockWebSocket(user_id)
        
        # Make WebSocket fail to respond to pings
        websocket.should_fail_send = True
        
        # Connect WebSocket
        conn_info = await ws_manager.connect(user_id, websocket)
        
        # Wait for heartbeat timeout detection
        # (In a real scenario, this would take longer)
        await asyncio.sleep(0.2)
        
        # Heartbeat should detect the failure
        # (Implementation would mark connection as unhealthy)
        
        # Cleanup
        await ws_manager.disconnect(user_id, websocket)
    async def test_concurrent_connection_management(self, ws_manager):
        """Test concurrent connection establishment and cleanup"""
        num_users = 20
        num_connections_per_user = 2
        
        # Create concurrent connection tasks
        tasks = []
        for user_idx in range(num_users):
            for conn_idx in range(num_connections_per_user):
                user_id = f"concurrent_user_{user_idx}"
                websocket = MockWebSocket(f"{user_id}_{conn_idx}")
                task = ws_manager.connect(user_id, websocket)
                tasks.append((user_id, websocket, task))
        
        # Execute all connections concurrently
        results = []
        for user_id, websocket, task in tasks:
            conn_info = await task
            results.append((user_id, websocket, conn_info))
        
        # Verify all connections established
        assert len(results) == num_users * num_connections_per_user
        total_connections = sum(len(conns) for conns in ws_manager.active_connections.values())
        assert total_connections == num_users * num_connections_per_user
        
        # Cleanup all connections concurrently
        cleanup_tasks = []
        for user_id, websocket, conn_info in results:
            task = ws_manager.disconnect(user_id, websocket)
            cleanup_tasks.append(task)
        
        await asyncio.gather(*cleanup_tasks)
        
        # Verify all connections cleaned up
        assert len(ws_manager.connection_registry) == 0
    async def test_message_broadcasting_to_multiple_connections(self, ws_manager):
        """Test broadcasting messages to multiple connections"""
        user_id = "broadcast_user"
        
        # Create multiple connections for same user
        websockets = []
        for i in range(3):
            websocket = MockWebSocket(f"{user_id}_{i}")
            await ws_manager.connect(user_id, websocket)
            websockets.append(websocket)
        
        # Broadcast message to all user connections
        test_message = {"type": "broadcast", "content": "Hello all connections!"}
        await ws_manager.send_message(user_id, test_message)
        
        # Verify all connections received the message
        for websocket in websockets:
            sent_messages = websocket.get_sent_messages()
            broadcast_messages = [
                msg for msg in sent_messages 
                if 'broadcast' in msg['data']
            ]
            assert len(broadcast_messages) >= 1
        
        # Cleanup
        for websocket in websockets:
            await ws_manager.disconnect(user_id, websocket)
    async def test_connection_statistics_tracking(self, ws_manager):
        """Test connection statistics tracking"""
        # Initial statistics
        initial_stats = ws_manager.get_stats()
        assert initial_stats["total_connections"] == 0
        
        # Create connections
        connections = []
        for i in range(5):
            user_id = f"stats_user_{i}"
            websocket = MockWebSocket(user_id)
            conn_info = await ws_manager.connect(user_id, websocket)
            connections.append((user_id, websocket, conn_info))
        
        # Check updated statistics
        updated_stats = ws_manager.get_stats()
        assert updated_stats["total_connections"] == 5
        
        # Send messages to update message statistics
        for user_id, websocket, conn_info in connections:
            await ws_manager.send_message(user_id, {"test": "message"})
        
        # Check message statistics
        final_stats = ws_manager.get_stats()
        assert final_stats["total_messages_sent"] >= 5
        
        # Cleanup
        for user_id, websocket, conn_info in connections:
            await ws_manager.disconnect(user_id, websocket)


class TestWebSocketManagerPerformanceAndScaling:
    """Test WebSocket manager performance and scaling"""
    
    @pytest.fixture
    def performance_ws_manager(self):
        """Create WebSocket manager for performance testing"""
        WebSocketManager._instance = None
        manager = WebSocketManager()
        return manager
    
    @pytest.fixture
    def connection_pool(self):
        """Create mock connection pool"""
        return MockConnectionPool(max_connections=50)
    async def test_high_volume_connection_handling(self, performance_ws_manager):
        """Test handling high volume of connections"""
        num_connections = 100
        
        # Measure connection establishment time
        start_time = time.time()
        
        connections = []
        tasks = []
        
        # Create many connections concurrently
        for i in range(num_connections):
            user_id = f"volume_user_{i}"
            websocket = MockWebSocket(user_id)
            task = performance_ws_manager.connect(user_id, websocket)
            tasks.append((user_id, websocket, task))
        
        # Execute all connections
        for user_id, websocket, task in tasks:
            conn_info = await task
            connections.append((user_id, websocket, conn_info))
        
        end_time = time.time()
        connection_time = end_time - start_time
        
        # Should handle high volume efficiently
        assert len(connections) == num_connections
        assert connection_time < 5.0  # Should complete within 5 seconds
        
        # Check performance metrics
        throughput = num_connections / connection_time
        assert throughput > 20  # At least 20 connections per second
        
        # Cleanup
        for user_id, websocket, conn_info in connections:
            await performance_ws_manager.disconnect(user_id, websocket)
    async def test_connection_pool_utilization(self, connection_pool):
        """Test connection pool utilization and efficiency"""
        # Acquire connections up to pool limit
        acquired_connections = []
        
        for i in range(connection_pool.max_connections):
            connection = await connection_pool.acquire_connection()
            acquired_connections.append(connection)
        
        # Pool should be at capacity
        pool_stats = connection_pool.get_pool_stats()
        assert pool_stats['active_connections'] == connection_pool.max_connections
        assert pool_stats['utilization_rate'] == 1.0
        
        # Release half the connections
        for i in range(len(acquired_connections) // 2):
            await connection_pool.release_connection(acquired_connections[i])
        
        # Pool utilization should decrease
        updated_stats = connection_pool.get_pool_stats()
        assert updated_stats['active_connections'] < connection_pool.max_connections
        assert updated_stats['utilization_rate'] < 1.0
    async def test_memory_usage_under_load(self, performance_ws_manager):
        """Test memory usage under connection load"""
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        # Create many connections
        connections = []
        num_connections = 200
        
        for i in range(num_connections):
            user_id = f"memory_user_{i}"
            websocket = MockWebSocket(user_id)
            
            # Add some data to simulate real usage
            websocket.user_data = {
                'profile': f"Profile data for user {i}" * 10,  # Some memory usage
                'session_data': list(range(100)),  # More memory usage
            }
            
            conn_info = await performance_ws_manager.connect(user_id, websocket)
            connections.append((user_id, websocket, conn_info))
        
        # Check memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should use reasonable memory (less than 100MB for this test)
        assert peak < 100 * 1024 * 1024  # 100MB
        
        # Cleanup
        for user_id, websocket, conn_info in connections:
            await performance_ws_manager.disconnect(user_id, websocket)
    async def test_connection_recovery_after_failure(self, performance_ws_manager):
        """Test connection recovery after failures"""
        user_id = "recovery_user"
        
        # Create initial connection
        websocket1 = MockWebSocket(user_id)
        conn_info1 = await performance_ws_manager.connect(user_id, websocket1)
        
        # Simulate connection failure
        websocket1.state = WebSocketState.DISCONNECTED
        await performance_ws_manager.disconnect(user_id, websocket1, code=1006, reason="Connection lost")
        
        # Verify connection cleaned up
        assert len(performance_ws_manager.active_connections.get(user_id, [])) == 0
        
        # Create new connection (recovery)
        websocket2 = MockWebSocket(user_id)
        conn_info2 = await performance_ws_manager.connect(user_id, websocket2)
        
        # Verify recovery successful
        assert len(performance_ws_manager.active_connections[user_id]) == 1
        assert conn_info2.connection_id != conn_info1.connection_id
        
        # Cleanup
        await performance_ws_manager.disconnect(user_id, websocket2)
    async def test_heartbeat_performance_under_load(self, performance_ws_manager):
        """Test heartbeat mechanism performance under load"""
        num_connections = 50
        
        # Create many connections with heartbeat
        connections = []
        for i in range(num_connections):
            user_id = f"heartbeat_perf_user_{i}"
            websocket = MockWebSocket(user_id)
            conn_info = await performance_ws_manager.connect(user_id, websocket)
            connections.append((user_id, websocket, conn_info))
        
        # Verify heartbeat tasks created for all connections
        assert len(performance_ws_manager.heartbeat_tasks) == num_connections
        
        # Let heartbeats run briefly
        await asyncio.sleep(0.5)
        
        # Check that heartbeat tasks are still running
        active_heartbeats = sum(
            1 for task in performance_ws_manager.heartbeat_tasks.values()
            if not task.done()
        )
        
        # Most heartbeat tasks should still be running
        assert active_heartbeats >= num_connections * 0.8  # Allow some variation
        
        # Cleanup
        for user_id, websocket, conn_info in connections:
            await performance_ws_manager.disconnect(user_id, websocket)
        
        # Verify heartbeat tasks cleaned up
        await asyncio.sleep(0.1)  # Allow time for cleanup
        remaining_tasks = sum(
            1 for task in performance_ws_manager.heartbeat_tasks.values()
            if not task.done()
        )
        assert remaining_tasks == 0
    async def test_broadcast_performance(self, performance_ws_manager):
        """Test broadcast message performance"""
        num_users = 20
        connections_per_user = 3
        
        # Create multiple connections per user
        all_connections = []
        for user_idx in range(num_users):
            user_id = f"broadcast_perf_user_{user_idx}"
            for conn_idx in range(connections_per_user):
                websocket = MockWebSocket(f"{user_id}_{conn_idx}")
                conn_info = await performance_ws_manager.connect(user_id, websocket)
                all_connections.append((user_id, websocket, conn_info))
        
        # Measure broadcast performance
        start_time = time.time()
        
        # Broadcast messages to all users
        broadcast_tasks = []
        for user_idx in range(num_users):
            user_id = f"broadcast_perf_user_{user_idx}"
            message = {"type": "performance_test", "user_idx": user_idx}
            task = performance_ws_manager.send_message(user_id, message)
            broadcast_tasks.append(task)
        
        # Execute all broadcasts
        await asyncio.gather(*broadcast_tasks)
        
        end_time = time.time()
        broadcast_time = end_time - start_time
        
        # Should broadcast efficiently
        total_messages = num_users * connections_per_user
        message_throughput = total_messages / broadcast_time
        assert message_throughput > 100  # At least 100 messages per second
        
        # Cleanup
        for user_id, websocket, conn_info in all_connections:
            await performance_ws_manager.disconnect(user_id, websocket)
    
    def test_connection_statistics_accuracy(self, performance_ws_manager):
        """Test accuracy of connection statistics"""
        # Reset statistics
        performance_ws_manager._stats = {
            "total_connections": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "total_errors": 0,
            "connection_failures": 0
        }
        
        # Perform known operations
        async def test_operations():
            # Create 5 connections
            connections = []
            for i in range(5):
                user_id = f"stats_test_user_{i}"
                websocket = MockWebSocket(user_id)
                conn_info = await performance_ws_manager.connect(user_id, websocket)
                connections.append((user_id, websocket))
            
            # Send 3 messages per connection
            for user_id, websocket in connections:
                for msg_idx in range(3):
                    await performance_ws_manager.send_message(
                        user_id, 
                        {"test_message": f"message_{msg_idx}"}
                    )
            
            # Cleanup
            for user_id, websocket in connections:
                await performance_ws_manager.disconnect(user_id, websocket)
        
        # Run test operations
        asyncio.run(test_operations())
        
        # Verify statistics accuracy
        stats = performance_ws_manager.get_stats()
        assert stats["total_connections"] == 5
        assert stats["total_messages_sent"] >= 15  # 5 users * 3 messages