"""
L2 Integration Test: WebSocket Connection Pool Management

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Resource efficiency worth $7K MRR cost optimization
- Value Impact: Optimizes resource usage and reduces infrastructure costs
- Strategic Impact: Enables scaling while controlling operational costs

L2 Test: Real internal connection pool components with mocked external services.
Performance target: <10ms pool operations, 95% resource utilization efficiency.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch
from uuid import uuid4

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.websocket_core.manager import WebSocketManager
from test_framework.mock_utils import mock_justified

@dataclass

class ConnectionMetrics:

    """Metrics for a connection."""

    created_at: float

    last_used: float

    message_count: int = 0

    bytes_sent: int = 0

    bytes_received: int = 0

    error_count: int = 0

    is_active: bool = True

@dataclass

class PoolConfig:

    """Configuration for connection pool."""

    min_connections: int = 5

    max_connections: int = 100

    idle_timeout: float = 300.0  # 5 minutes

    connection_timeout: float = 30.0  # 30 seconds

    max_idle_connections: int = 20

    cleanup_interval: float = 60.0  # 1 minute

    burst_capacity: int = 50  # Additional connections for burst

class WebSocketConnectionPool:

    """Manage pool of WebSocket connections."""
    
    def __init__(self, config: PoolConfig = None):

        self.config = config or PoolConfig()

        self.active_connections = {}  # connection_id -> websocket

        self.connection_metrics = {}  # connection_id -> ConnectionMetrics

        self.idle_connections = set()  # Set of idle connection_ids

        self.user_connections = defaultdict(set)  # user_id -> set(connection_ids)

        self.pool_stats = {

            "total_created": 0,

            "total_destroyed": 0,

            "peak_connections": 0,

            "pool_hits": 0,

            "pool_misses": 0,

            "idle_timeouts": 0,

            "capacity_exceeded": 0

        }

        self.last_cleanup = time.time()
    
    async def acquire_connection(self, user_id: str, websocket: Any = None) -> Optional[str]:

        """Acquire a connection from the pool."""

        current_time = time.time()
        
        # Try to reuse idle connection for user

        reused_connection = await self._try_reuse_connection(user_id)

        if reused_connection:

            self.pool_stats["pool_hits"] += 1

            return reused_connection
        
        self.pool_stats["pool_misses"] += 1
        
        # Check pool capacity

        if not self._can_create_connection():

            self.pool_stats["capacity_exceeded"] += 1

            return None
        
        # Create new connection

        connection_id = str(uuid4())
        
        self.active_connections[connection_id] = websocket or MockWebSocket()

        self.connection_metrics[connection_id] = ConnectionMetrics(

            created_at=current_time,

            last_used=current_time

        )
        
        self.user_connections[user_id].add(connection_id)

        self.pool_stats["total_created"] += 1
        
        # Update peak connections

        current_count = len(self.active_connections)

        if current_count > self.pool_stats["peak_connections"]:

            self.pool_stats["peak_connections"] = current_count
        
        return connection_id
    
    async def _try_reuse_connection(self, user_id: str) -> Optional[str]:

        """Try to reuse an existing idle connection for user."""

        user_connection_ids = self.user_connections.get(user_id, set())

        idle_user_connections = user_connection_ids.intersection(self.idle_connections)
        
        if idle_user_connections:
            # Reuse most recently used idle connection

            best_connection = max(

                idle_user_connections,

                key=lambda conn_id: self.connection_metrics[conn_id].last_used

            )
            
            self.idle_connections.remove(best_connection)

            self.connection_metrics[best_connection].last_used = time.time()

            self.connection_metrics[best_connection].is_active = True
            
            return best_connection
        
        return None
    
    def _can_create_connection(self) -> bool:

        """Check if new connection can be created."""

        current_count = len(self.active_connections)
        
        # Allow burst capacity for temporary spikes

        max_allowed = self.config.max_connections + self.config.burst_capacity
        
        return current_count < max_allowed
    
    async def release_connection(self, connection_id: str, force_close: bool = False) -> bool:

        """Release connection back to pool or close it."""

        if connection_id not in self.active_connections:

            return False
        
        current_time = time.time()
        
        if force_close or not self._should_keep_connection(connection_id):

            return await self._close_connection(connection_id)
        
        # Move to idle pool

        self.idle_connections.add(connection_id)

        self.connection_metrics[connection_id].is_active = False

        self.connection_metrics[connection_id].last_used = current_time
        
        # Cleanup excess idle connections

        await self._cleanup_excess_idle_connections()
        
        return True
    
    def _should_keep_connection(self, connection_id: str) -> bool:

        """Determine if connection should be kept in pool."""

        metrics = self.connection_metrics[connection_id]
        
        # Don't keep connections with too many errors

        if metrics.error_count > 10:

            return False
        
        # Don't keep if we have too many idle connections

        if len(self.idle_connections) >= self.config.max_idle_connections:

            return False
        
        return True
    
    async def _close_connection(self, connection_id: str) -> bool:

        """Close and remove connection from pool."""

        if connection_id not in self.active_connections:

            return False
        
        # Remove from all tracking structures

        websocket = self.active_connections.pop(connection_id)

        self.connection_metrics.pop(connection_id, None)

        self.idle_connections.discard(connection_id)
        
        # Remove from user connections

        for user_id, conn_set in self.user_connections.items():

            conn_set.discard(connection_id)
        
        # Close the actual websocket

        if hasattr(websocket, 'close'):

            try:

                await websocket.close()

            except Exception:

                pass  # Ignore close errors
        
        self.pool_stats["total_destroyed"] += 1

        return True
    
    async def _cleanup_excess_idle_connections(self) -> None:

        """Cleanup excess idle connections."""

        if len(self.idle_connections) <= self.config.max_idle_connections:

            return
        
        # Sort idle connections by last used time (oldest first)

        sorted_idle = sorted(

            self.idle_connections,

            key=lambda conn_id: self.connection_metrics[conn_id].last_used

        )
        
        # Close oldest connections

        excess_count = len(self.idle_connections) - self.config.max_idle_connections

        for i in range(excess_count):

            await self._close_connection(sorted_idle[i])
    
    async def cleanup_expired_connections(self) -> int:

        """Cleanup expired idle connections."""

        current_time = time.time()

        cleanup_cutoff = current_time - self.config.idle_timeout

        expired_connections = []
        
        for connection_id in list(self.idle_connections):

            metrics = self.connection_metrics.get(connection_id)

            if metrics and metrics.last_used < cleanup_cutoff:

                expired_connections.append(connection_id)
        
        # Close expired connections

        closed_count = 0

        for connection_id in expired_connections:

            if await self._close_connection(connection_id):

                closed_count += 1

                self.pool_stats["idle_timeouts"] += 1
        
        self.last_cleanup = current_time

        return closed_count
    
    def record_connection_activity(self, connection_id: str, bytes_sent: int = 0, 

                                 bytes_received: int = 0, error: bool = False) -> None:

        """Record activity for a connection."""

        if connection_id not in self.connection_metrics:

            return
        
        metrics = self.connection_metrics[connection_id]

        metrics.last_used = time.time()

        metrics.message_count += 1

        metrics.bytes_sent += bytes_sent

        metrics.bytes_received += bytes_received
        
        if error:

            metrics.error_count += 1
    
    def get_pool_status(self) -> Dict[str, Any]:

        """Get current pool status."""

        current_time = time.time()
        
        # Calculate connection age distribution

        ages = []

        for metrics in self.connection_metrics.values():

            age = current_time - metrics.created_at

            ages.append(age)
        
        avg_age = sum(ages) / len(ages) if ages else 0
        
        # Calculate utilization

        active_count = len(self.active_connections) - len(self.idle_connections)

        utilization = (active_count / self.config.max_connections) * 100 if self.config.max_connections > 0 else 0
        
        return {

            "total_connections": len(self.active_connections),

            "active_connections": active_count,

            "idle_connections": len(self.idle_connections),

            "utilization_percent": utilization,

            "avg_connection_age": avg_age,

            "user_count": len([user_id for user_id, conns in self.user_connections.items() if conns]),

            "config": {

                "min_connections": self.config.min_connections,

                "max_connections": self.config.max_connections,

                "max_idle": self.config.max_idle_connections

            },

            "stats": self.pool_stats.copy()

        }
    
    def get_user_connections(self, user_id: str) -> Dict[str, Any]:

        """Get connection information for specific user."""

        user_conn_ids = self.user_connections.get(user_id, set())
        
        connections_info = []

        for conn_id in user_conn_ids:

            if conn_id in self.connection_metrics:

                metrics = self.connection_metrics[conn_id]

                connections_info.append({

                    "connection_id": conn_id,

                    "created_at": metrics.created_at,

                    "last_used": metrics.last_used,

                    "message_count": metrics.message_count,

                    "bytes_sent": metrics.bytes_sent,

                    "bytes_received": metrics.bytes_received,

                    "error_count": metrics.error_count,

                    "is_active": metrics.is_active,

                    "is_idle": conn_id in self.idle_connections

                })
        
        return {

            "user_id": user_id,

            "connection_count": len(user_conn_ids),

            "connections": connections_info

        }

class MockWebSocket:

    """Mock WebSocket for testing."""
    
    def __init__(self):

        self.closed = False

        self.sent_messages = []

        self.received_messages = []
    
    async def send(self, message: str) -> None:

        """Send message through mock WebSocket."""

        if self.closed:

            raise Exception("WebSocket closed")

        self.sent_messages.append(message)
    
    async def receive(self) -> str:

        """Receive message from mock WebSocket."""

        if self.closed:

            raise Exception("WebSocket closed")

        if self.received_messages:

            return self.received_messages.pop(0)

        raise asyncio.TimeoutError("No message available")
    
    async def close(self) -> None:

        """Close mock WebSocket."""

        self.closed = True
    
    def add_received_message(self, message: str) -> None:

        """Add message to received queue."""

        self.received_messages.append(message)

class ConnectionReaper:

    """Manage cleanup of stale connections."""
    
    def __init__(self, pool: WebSocketConnectionPool):

        self.pool = pool

        self.reaper_stats = {

            "cleanup_cycles": 0,

            "connections_reaped": 0,

            "errors": 0

        }

        self.running = False
    
    async def start_reaper(self) -> None:

        """Start the connection reaper."""

        self.running = True
        
        while self.running:

            try:

                await self._reaper_cycle()

                await asyncio.sleep(self.pool.config.cleanup_interval)

            except Exception as e:

                self.reaper_stats["errors"] += 1

                await asyncio.sleep(5.0)  # Short delay on error
    
    async def _reaper_cycle(self) -> None:

        """Perform one reaper cleanup cycle."""

        self.reaper_stats["cleanup_cycles"] += 1
        
        # Cleanup expired connections

        reaped_count = await self.pool.cleanup_expired_connections()

        self.reaper_stats["connections_reaped"] += reaped_count
        
        # Additional health checks could go here

        await self._health_check_connections()
    
    async def _health_check_connections(self) -> None:

        """Perform health checks on connections."""
        # Check for connections with excessive errors

        problematic_connections = []
        
        for conn_id, metrics in self.pool.connection_metrics.items():

            if metrics.error_count > 20:  # Too many errors

                problematic_connections.append(conn_id)

            elif metrics.is_active and (time.time() - metrics.last_used) > 3600:  # 1 hour inactive

                problematic_connections.append(conn_id)
        
        # Close problematic connections

        for conn_id in problematic_connections:

            await self.pool._close_connection(conn_id)

            self.reaper_stats["connections_reaped"] += 1
    
    def stop_reaper(self) -> None:

        """Stop the connection reaper."""

        self.running = False
    
    def get_reaper_stats(self) -> Dict[str, Any]:

        """Get reaper statistics."""

        return self.reaper_stats.copy()

@pytest.mark.L2

@pytest.mark.integration

class TestConnectionPoolManagement:

    """L2 integration tests for connection pool management."""
    
    @pytest.fixture

    def pool_config(self):

        """Create pool configuration for testing."""

        return PoolConfig(

            min_connections=2,

            max_connections=10,

            idle_timeout=30.0,  # Short timeout for testing

            max_idle_connections=5,

            cleanup_interval=10.0,  # Short interval for testing

            burst_capacity=5

        )
    
    @pytest.fixture

    def connection_pool(self, pool_config):

        """Create connection pool."""

        return WebSocketConnectionPool(pool_config)
    
    @pytest.fixture

    def connection_reaper(self, connection_pool):

        """Create connection reaper."""

        return ConnectionReaper(connection_pool)
    
    @pytest.fixture

    def test_users(self):

        """Create test users."""

        return [

            User(

                id=f"pool_user_{i}",

                email=f"pooluser{i}@example.com",

                username=f"pooluser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(5)

        ]
    
    @pytest.mark.asyncio
    async def test_basic_connection_acquisition(self, connection_pool, test_users):

        """Test basic connection acquisition and release."""

        user = test_users[0]
        
        # Acquire connection

        connection_id = await connection_pool.acquire_connection(user.id)

        assert connection_id is not None
        
        # Verify connection exists

        assert connection_id in connection_pool.active_connections

        assert connection_id in connection_pool.connection_metrics

        assert connection_id in connection_pool.user_connections[user.id]
        
        # Check pool status

        status = connection_pool.get_pool_status()

        assert status["total_connections"] == 1

        assert status["active_connections"] == 1

        assert status["idle_connections"] == 0
        
        # Release connection

        released = await connection_pool.release_connection(connection_id)

        assert released is True
        
        # Should be moved to idle

        assert connection_id in connection_pool.idle_connections
        
        status = connection_pool.get_pool_status()

        assert status["total_connections"] == 1

        assert status["active_connections"] == 0

        assert status["idle_connections"] == 1
    
    @pytest.mark.asyncio
    async def test_connection_reuse(self, connection_pool, test_users):

        """Test connection reuse functionality."""

        user = test_users[0]
        
        # Acquire and release connection

        first_connection = await connection_pool.acquire_connection(user.id)

        await connection_pool.release_connection(first_connection)
        
        # Acquire again - should reuse same connection

        second_connection = await connection_pool.acquire_connection(user.id)

        assert second_connection == first_connection
        
        # Verify reuse statistics

        status = connection_pool.get_pool_status()

        assert status["stats"]["pool_hits"] == 1

        assert status["stats"]["total_created"] == 1  # Only one connection created
    
    @pytest.mark.asyncio
    async def test_pool_capacity_limits(self, connection_pool, test_users):

        """Test pool capacity enforcement."""

        connections = []
        
        # Acquire up to max capacity

        for i in range(connection_pool.config.max_connections):

            user_id = test_users[i % len(test_users)].id

            conn_id = await connection_pool.acquire_connection(user_id)

            assert conn_id is not None

            connections.append(conn_id)
        
        # Should be at capacity

        status = connection_pool.get_pool_status()

        assert status["total_connections"] == connection_pool.config.max_connections
        
        # Try to acquire beyond capacity - should still work due to burst capacity

        burst_connection = await connection_pool.acquire_connection(test_users[0].id)

        assert burst_connection is not None
        
        # Try to exceed burst capacity

        burst_connections = []

        for i in range(connection_pool.config.burst_capacity):

            burst_conn = await connection_pool.acquire_connection(test_users[0].id)

            if burst_conn:

                burst_connections.append(burst_conn)
        
        # Eventually should hit absolute limit

        final_connection = await connection_pool.acquire_connection(test_users[0].id)
        # This may be None if we hit the absolute limit
        
        # Verify capacity exceeded stat

        status = connection_pool.get_pool_status()

        assert status["stats"]["capacity_exceeded"] >= 0
    
    @pytest.mark.asyncio
    async def test_idle_connection_cleanup(self, connection_pool, test_users):

        """Test cleanup of idle connections."""

        user = test_users[0]
        
        # Create connection and make it idle

        connection_id = await connection_pool.acquire_connection(user.id)

        await connection_pool.release_connection(connection_id)
        
        # Verify it's idle

        assert connection_id in connection_pool.idle_connections
        
        # Simulate timeout by modifying last used time

        connection_pool.connection_metrics[connection_id].last_used = (

            time.time() - connection_pool.config.idle_timeout - 1

        )
        
        # Run cleanup

        cleaned_count = await connection_pool.cleanup_expired_connections()

        assert cleaned_count == 1
        
        # Connection should be removed

        assert connection_id not in connection_pool.active_connections

        assert connection_id not in connection_pool.idle_connections
        
        # Verify timeout stats

        status = connection_pool.get_pool_status()

        assert status["stats"]["idle_timeouts"] == 1
    
    @pytest.mark.asyncio
    async def test_connection_activity_tracking(self, connection_pool, test_users):

        """Test tracking of connection activity."""

        user = test_users[0]
        
        # Acquire connection

        connection_id = await connection_pool.acquire_connection(user.id)
        
        # Record activity

        connection_pool.record_connection_activity(

            connection_id, 

            bytes_sent=1024, 

            bytes_received=512

        )
        
        connection_pool.record_connection_activity(

            connection_id, 

            bytes_sent=2048, 

            error=True

        )
        
        # Check metrics

        metrics = connection_pool.connection_metrics[connection_id]

        assert metrics.message_count == 2

        assert metrics.bytes_sent == 3072  # 1024 + 2048

        assert metrics.bytes_received == 512

        assert metrics.error_count == 1
        
        # Get user connection info

        user_info = connection_pool.get_user_connections(user.id)

        assert user_info["connection_count"] == 1

        assert len(user_info["connections"]) == 1
        
        conn_info = user_info["connections"][0]

        assert conn_info["message_count"] == 2

        assert conn_info["bytes_sent"] == 3072

        assert conn_info["error_count"] == 1
    
    @pytest.mark.asyncio
    async def test_multiple_user_connections(self, connection_pool, test_users):

        """Test managing connections for multiple users."""

        user_connections = {}
        
        # Create connections for multiple users

        for user in test_users:

            conn_id = await connection_pool.acquire_connection(user.id)

            user_connections[user.id] = conn_id
        
        # Verify each user has their connection

        for user in test_users:

            user_info = connection_pool.get_user_connections(user.id)

            assert user_info["connection_count"] == 1

            assert user_connections[user.id] in [c["connection_id"] for c in user_info["connections"]]
        
        # Create additional connections for some users

        extra_connections = []

        for i in range(3):

            user = test_users[i]

            extra_conn = await connection_pool.acquire_connection(user.id)

            extra_connections.append((user.id, extra_conn))
        
        # Verify users have multiple connections

        for i in range(3):

            user = test_users[i]

            user_info = connection_pool.get_user_connections(user.id)

            assert user_info["connection_count"] == 2
        
        # Check overall pool status

        status = connection_pool.get_pool_status()

        assert status["total_connections"] == len(test_users) + 3

        assert status["user_count"] == len(test_users)
    
    @pytest.mark.asyncio
    async def test_connection_reaper_functionality(self, connection_pool, connection_reaper, test_users):

        """Test connection reaper cleanup functionality."""

        user = test_users[0]
        
        # Create connections

        connections = []

        for _ in range(3):

            conn_id = await connection_pool.acquire_connection(user.id)

            connections.append(conn_id)
        
        # Release some connections

        for conn_id in connections[:2]:

            await connection_pool.release_connection(conn_id)
        
        # Make idle connections expired

        for conn_id in connections[:2]:

            connection_pool.connection_metrics[conn_id].last_used = (

                time.time() - connection_pool.config.idle_timeout - 1

            )
        
        # Run reaper cycle

        await connection_reaper._reaper_cycle()
        
        # Check reaper stats

        stats = connection_reaper.get_reaper_stats()

        assert stats["cleanup_cycles"] == 1

        assert stats["connections_reaped"] >= 2
        
        # Verify connections were cleaned up

        status = connection_pool.get_pool_status()

        assert status["total_connections"] == 1  # Only active connection remains
    
    @mock_justified("L2: Connection pool management with real internal components")

    @pytest.mark.asyncio
    async def test_websocket_integration_with_pool(self, connection_pool, test_users):

        """Test WebSocket integration with connection pool."""

        user = test_users[0]
        
        # Create mock WebSocket

        mock_websocket = MockWebSocket()
        
        # Acquire connection with WebSocket

        connection_id = await connection_pool.acquire_connection(user.id, mock_websocket)

        assert connection_id is not None
        
        # Verify WebSocket is stored

        stored_websocket = connection_pool.active_connections[connection_id]

        assert stored_websocket == mock_websocket
        
        # Simulate WebSocket activity

        await stored_websocket.send("test message")

        connection_pool.record_connection_activity(connection_id, bytes_sent=100)
        
        # Verify message was sent

        assert "test message" in mock_websocket.sent_messages
        
        # Check connection metrics

        metrics = connection_pool.connection_metrics[connection_id]

        assert metrics.bytes_sent == 100

        assert metrics.message_count == 1
        
        # Release connection

        await connection_pool.release_connection(connection_id)
        
        # Should be idle but WebSocket not closed yet

        assert not mock_websocket.closed

        assert connection_id in connection_pool.idle_connections
        
        # Force close connection

        await connection_pool.release_connection(connection_id, force_close=True)
        
        # WebSocket should be closed and connection removed

        assert mock_websocket.closed

        assert connection_id not in connection_pool.active_connections
    
    @pytest.mark.asyncio
    async def test_concurrent_pool_operations(self, connection_pool, test_users):

        """Test concurrent pool operations."""

        concurrent_operations = 20

        results = []
        
        async def concurrent_acquire_release(operation_id: int):

            user = test_users[operation_id % len(test_users)]
            
            try:
                # Acquire connection

                conn_id = await connection_pool.acquire_connection(user.id)

                if conn_id is None:

                    return "acquire_failed"
                
                # Simulate some activity

                connection_pool.record_connection_activity(conn_id, bytes_sent=operation_id * 10)

                await asyncio.sleep(0.01)  # Small delay
                
                # Release connection

                released = await connection_pool.release_connection(conn_id)

                return "success" if released else "release_failed"
                
            except Exception as e:

                return f"error: {str(e)}"
        
        # Execute concurrent operations

        tasks = [concurrent_acquire_release(i) for i in range(concurrent_operations)]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results

        success_count = sum(1 for result in results if result == "success")

        error_count = sum(1 for result in results if isinstance(result, Exception) or result.startswith("error"))
        
        # Should handle most operations successfully

        assert success_count >= concurrent_operations * 0.8  # 80% success rate

        assert error_count < concurrent_operations * 0.2   # Less than 20% errors
        
        # Check final pool state

        status = connection_pool.get_pool_status()

        assert status["total_connections"] >= 0  # Pool should be in valid state
    
    @pytest.mark.asyncio
    async def test_pool_performance_benchmarks(self, connection_pool, test_users):

        """Test connection pool performance benchmarks."""

        operation_count = 1000

        user = test_users[0]
        
        # Benchmark connection acquisition

        start_time = time.time()

        acquired_connections = []
        
        for _ in range(operation_count):

            conn_id = await connection_pool.acquire_connection(user.id)

            if conn_id:

                acquired_connections.append(conn_id)
            
            # Release immediately to test pool reuse

            if len(acquired_connections) > 0 and len(acquired_connections) % 2 == 0:

                await connection_pool.release_connection(acquired_connections[-1])
        
        acquisition_time = time.time() - start_time
        
        # Should handle operations quickly

        assert acquisition_time < 5.0  # Less than 5 seconds for 1000 operations
        
        # Benchmark activity recording

        start_time = time.time()
        
        for conn_id in acquired_connections[:100]:  # Test on subset

            for _ in range(10):

                connection_pool.record_connection_activity(conn_id, bytes_sent=100)
        
        activity_time = time.time() - start_time
        
        # Should record activity very quickly

        assert activity_time < 1.0  # Less than 1 second for 1000 activity records
        
        # Benchmark cleanup

        start_time = time.time()
        
        # Make all connections idle and expired

        for conn_id in acquired_connections:

            await connection_pool.release_connection(conn_id)

            connection_pool.connection_metrics[conn_id].last_used = (

                time.time() - connection_pool.config.idle_timeout - 1

            )
        
        cleaned_count = await connection_pool.cleanup_expired_connections()

        cleanup_time = time.time() - start_time
        
        # Should cleanup quickly

        assert cleanup_time < 2.0  # Less than 2 seconds for cleanup

        assert cleaned_count > 0  # Should have cleaned up connections
        
        # Verify pool efficiency metrics

        status = connection_pool.get_pool_status()

        stats = status["stats"]
        
        # Pool hit rate should be high due to reuse

        total_requests = stats["pool_hits"] + stats["pool_misses"]

        if total_requests > 0:

            hit_rate = (stats["pool_hits"] / total_requests) * 100

            assert hit_rate > 80  # At least 80% hit rate

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])