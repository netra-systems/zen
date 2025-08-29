"""
WebSocket connection performance and scaling tests
Tests high volume connections, memory usage, recovery, and broadcast performance
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
from pathlib import Path
import sys

import asyncio
import time
import tracemalloc
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call, patch

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.websocket_core.connection_info import ConnectionInfo
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.tests.services.test_ws_connection_mocks import (

    MockConnectionPool,

    MockWebSocket,

    WebSocketTestHelpers,

)

class TestWebSocketManagerPerformanceAndScaling:

    """Test WebSocket manager performance and scaling capabilities"""
    
    @pytest.fixture

    def performance_websocket_manager(self):

        """Create WebSocket manager for performance testing"""

        WebSocketTestHelpers.reset_ws_manager_singleton()

        return WebSocketManager()
    
    @pytest.fixture

    def connection_pool(self):

        """Create mock connection pool for testing"""

        return MockConnectionPool(max_connections=50)
    
    @pytest.mark.asyncio
    async def test_high_volume_connection_handling(self, performance_websocket_manager):

        """Test handling high volume of connections"""

        num_connections = 100

        start_time = time.time()

        connection_tasks = self._create_volume_connection_tasks(performance_websocket_manager, num_connections)

        connections = await self._execute_volume_connections(connection_tasks)

        connection_time = time.time() - start_time

        self._verify_volume_performance(connections, num_connections, connection_time)

        await self._cleanup_volume_connections(performance_websocket_manager, connections)
        
    def _create_volume_connection_tasks(self, websocket_manager, num_connections):

        """Create high volume connection tasks"""

        tasks = []

        for i in range(num_connections):

            user_id = f"volume_user_{i}"

            websocket = MockWebSocket(user_id)

            task = websocket_manager.connect_user(user_id, websocket)

            tasks.append((user_id, websocket, task))

        return tasks
        
    async def _execute_volume_connections(self, connection_tasks):

        """Execute volume connection tasks"""

        connections = []

        for user_id, websocket, task in connection_tasks:

            conn_info = await task

            connections.append((user_id, websocket, conn_info))

        return connections
        
    def _verify_volume_performance(self, connections, expected_count, connection_time):

        """Verify volume connection performance"""

        assert len(connections) == expected_count

        assert connection_time < 5.0  # Complete within 5 seconds

        throughput = expected_count / connection_time

        assert throughput > 20  # At least 20 connections per second
        
    async def _cleanup_volume_connections(self, websocket_manager, connections):

        """Cleanup volume test connections"""

        for user_id, websocket, conn_info in connections:

            await websocket_manager.disconnect_user(user_id, websocket)
            
    @pytest.mark.asyncio
    async def test_connection_pool_utilization(self, connection_pool):

        """Test connection pool utilization and efficiency"""

        acquired_connections = await self._acquire_pool_connections(connection_pool)

        self._verify_pool_capacity_utilization(connection_pool)

        await self._test_pool_release_behavior(connection_pool, acquired_connections)
        
    async def _acquire_pool_connections(self, connection_pool):

        """Acquire connections up to pool limit"""

        acquired_connections = []

        for i in range(connection_pool.max_connections):

            connection = await connection_pool.acquire_connection()

            acquired_connections.append(connection)

        return acquired_connections
        
    def _verify_pool_capacity_utilization(self, connection_pool):

        """Verify pool is at full capacity"""

        pool_stats = connection_pool.get_pool_stats()

        assert pool_stats['active_connections'] == connection_pool.max_connections

        assert pool_stats['utilization_rate'] == 1.0
        
    async def _test_pool_release_behavior(self, connection_pool, acquired_connections):

        """Test pool connection release behavior"""

        half_count = len(acquired_connections) // 2

        for i in range(half_count):

            await connection_pool.release_connection(acquired_connections[i])

        updated_stats = connection_pool.get_pool_stats()

        assert updated_stats['active_connections'] < connection_pool.max_connections

        assert updated_stats['utilization_rate'] < 1.0
        
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_websocket_manager):

        """Test memory usage under connection load"""

        tracemalloc.start()

        connections = await self._create_memory_test_connections(performance_websocket_manager)

        memory_peak = self._measure_memory_usage()

        self._verify_memory_efficiency(memory_peak)

        await self._cleanup_memory_test_connections(performance_websocket_manager, connections)
        
    async def _create_memory_test_connections(self, websocket_manager):

        """Create connections for memory testing"""

        connections = []

        num_connections = 200

        for i in range(num_connections):

            user_id = f"memory_user_{i}"

            websocket = self._create_memory_loaded_websocket(user_id, i)

            conn_info = await websocket_manager.connect_user(user_id, websocket)

            connections.append((user_id, websocket, conn_info))

        return connections
        
    def _create_memory_loaded_websocket(self, user_id, index):

        """Create WebSocket with memory load simulation"""

        websocket = MockWebSocket(user_id)

        websocket.user_data = {

            'profile': f"Profile data for user {index}" * 10,

            'session_data': list(range(100)),

        }

        return websocket
        
    def _measure_memory_usage(self):

        """Measure current memory usage"""

        current, peak = tracemalloc.get_traced_memory()

        tracemalloc.stop()

        return peak
        
    def _verify_memory_efficiency(self, memory_peak):

        """Verify memory usage is reasonable"""

        max_memory_mb = 100 * 1024 * 1024  # 100MB

        assert memory_peak < max_memory_mb
        
    async def _cleanup_memory_test_connections(self, websocket_manager, connections):

        """Cleanup memory test connections"""

        for user_id, websocket, conn_info in connections:

            await websocket_manager.disconnect_user(user_id, websocket)
            
    @pytest.mark.asyncio
    async def test_connection_recovery_after_failure(self, performance_websocket_manager):

        """Test connection recovery after failures"""

        user_id = "recovery_user"

        websocket1 = MockWebSocket(user_id)

        conn_info1 = await performance_websocket_manager.connect_user(user_id, websocket1)

        await self._simulate_connection_failure(performance_websocket_manager, user_id, websocket1)

        self._verify_failure_cleanup(performance_websocket_manager, user_id)

        conn_info2 = await self._test_connection_recovery(performance_websocket_manager, user_id)

        self._verify_recovery_success(performance_websocket_manager, user_id, conn_info1, conn_info2)
        
    async def _simulate_connection_failure(self, websocket_manager, user_id, websocket):

        """Simulate connection failure scenario"""

        websocket.state = WebSocketState.DISCONNECTED

        await websocket_manager.disconnect_user(user_id, websocket, code=1006, reason="Connection lost")
        
    def _verify_failure_cleanup(self, websocket_manager, user_id):

        """Verify connection failure was cleaned up"""

        user_connections = websocket_manager.connection_manager.active_connections.get(user_id, [])

        assert len(user_connections) == 0
        
    async def _test_connection_recovery(self, websocket_manager, user_id):

        """Test connection recovery process"""

        websocket2 = MockWebSocket(user_id)

        conn_info2 = await websocket_manager.connect_user(user_id, websocket2)

        await websocket_manager.disconnect_user(user_id, websocket2)

        return conn_info2
        
    def _verify_recovery_success(self, websocket_manager, user_id, original_conn, recovered_conn):

        """Verify connection recovery was successful"""

        assert recovered_conn.connection_id != original_conn.connection_id
        
    @pytest.mark.asyncio
    async def test_heartbeat_performance_under_load(self, performance_websocket_manager):

        """Test heartbeat mechanism performance under load"""

        num_connections = 50

        connections = await self._create_heartbeat_load_connections(performance_websocket_manager, num_connections)

        self._verify_heartbeat_tasks_created(performance_websocket_manager, num_connections)

        await self._test_heartbeat_under_load(performance_websocket_manager, num_connections)

        await self._cleanup_heartbeat_load_connections(performance_websocket_manager, connections)

        await self._verify_heartbeat_cleanup(performance_websocket_manager)
        
    async def _create_heartbeat_load_connections(self, websocket_manager, num_connections):

        """Create connections for heartbeat load testing"""

        connections = []

        for i in range(num_connections):

            user_id = f"heartbeat_perf_user_{i}"

            websocket = MockWebSocket(user_id)

            conn_info = await websocket_manager.connect_user(user_id, websocket)

            connections.append((user_id, websocket, conn_info))

        return connections
        
    def _verify_heartbeat_tasks_created(self, websocket_manager, expected_count):

        """Verify heartbeat tasks were created"""

        assert len(websocket_manager.core.heartbeat_manager.heartbeat_tasks) == expected_count
        
    async def _test_heartbeat_under_load(self, websocket_manager, num_connections):

        """Test heartbeat performance under load"""

        await asyncio.sleep(0.5)

        active_heartbeats = self._count_active_heartbeats(websocket_manager)

        min_expected = int(num_connections * 0.8)  # Allow variation

        assert active_heartbeats >= min_expected
        
    def _count_active_heartbeats(self, websocket_manager):

        """Count active heartbeat tasks"""

        return sum(

            1 for task in websocket_manager.core.heartbeat_manager.heartbeat_tasks.values()

            if not task.done()

        )
        
    async def _cleanup_heartbeat_load_connections(self, websocket_manager, connections):

        """Cleanup heartbeat load test connections"""

        for user_id, websocket, conn_info in connections:

            await websocket_manager.disconnect_user(user_id, websocket)
            
    async def _verify_heartbeat_cleanup(self, websocket_manager):

        """Verify heartbeat tasks were cleaned up"""

        await asyncio.sleep(0.1)  # Allow cleanup time

        remaining_tasks = self._count_active_heartbeats(websocket_manager)

        assert remaining_tasks == 0
        
    @pytest.mark.asyncio
    async def test_broadcast_performance(self, performance_websocket_manager):

        """Test broadcast message performance"""

        num_users, connections_per_user = 20, 3

        all_connections = await self._setup_broadcast_performance_test(

            performance_websocket_manager, num_users, connections_per_user

        )

        broadcast_time = await self._measure_broadcast_performance(

            performance_websocket_manager, num_users

        )

        self._verify_broadcast_efficiency(num_users, connections_per_user, broadcast_time)

        await self._cleanup_broadcast_performance_connections(performance_websocket_manager, all_connections)
        
    async def _setup_broadcast_performance_test(self, websocket_manager, num_users, connections_per_user):

        """Setup connections for broadcast performance testing"""

        all_connections = []

        for user_idx in range(num_users):

            user_id = f"broadcast_perf_user_{user_idx}"

            for conn_idx in range(connections_per_user):

                websocket = MockWebSocket(f"{user_id}_{conn_idx}")

                conn_info = await websocket_manager.connect_user(user_id, websocket)

                all_connections.append((user_id, websocket, conn_info))

        return all_connections
        
    async def _measure_broadcast_performance(self, websocket_manager, num_users):

        """Measure broadcast performance timing"""

        start_time = time.time()

        broadcast_tasks = self._create_broadcast_tasks(websocket_manager, num_users)

        await asyncio.gather(*broadcast_tasks)

        return time.time() - start_time
        
    def _create_broadcast_tasks(self, websocket_manager, num_users):

        """Create broadcast tasks for performance testing"""

        broadcast_tasks = []

        for user_idx in range(num_users):

            user_id = f"broadcast_perf_user_{user_idx}"

            message = {"type": "performance_test", "user_idx": user_idx}

            task = websocket_manager.send_message_to_user(user_id, message)

            broadcast_tasks.append(task)

        return broadcast_tasks
        
    def _verify_broadcast_efficiency(self, num_users, connections_per_user, broadcast_time):

        """Verify broadcast performance meets requirements"""

        total_messages = num_users * connections_per_user

        message_throughput = total_messages / broadcast_time

        assert message_throughput > 100  # At least 100 messages per second
        
    async def _cleanup_broadcast_performance_connections(self, websocket_manager, all_connections):

        """Cleanup broadcast performance test connections"""

        for user_id, websocket, conn_info in all_connections:

            await websocket_manager.disconnect_user(user_id, websocket)
    
    def test_connection_statistics_accuracy(self, performance_websocket_manager):

        """Test accuracy of connection statistics"""

        self._reset_manager_statistics(performance_websocket_manager)

        asyncio.run(self._execute_statistics_test_operations(performance_websocket_manager))

        self._verify_statistics_accuracy(performance_websocket_manager)
        
    def _reset_manager_statistics(self, websocket_manager):

        """Reset WebSocket manager statistics"""

        websocket_manager._stats = {

            "total_connections": 0,

            "total_messages_sent": 0,

            "total_messages_received": 0,

            "total_errors": 0,

            "connection_failures": 0

        }
        
    async def _execute_statistics_test_operations(self, websocket_manager):

        """Execute known operations for statistics testing"""

        connections = await self._create_statistics_test_connections(websocket_manager)

        await self._send_statistics_test_messages(websocket_manager, connections)

        await self._cleanup_statistics_test_connections(websocket_manager, connections)
        
    async def _create_statistics_test_connections(self, websocket_manager):

        """Create connections for statistics testing"""

        connections = []

        for i in range(5):

            user_id = f"stats_test_user_{i}"

            websocket = MockWebSocket(user_id)

            conn_info = await websocket_manager.connect_user(user_id, websocket)

            connections.append((user_id, websocket))

        return connections
        
    async def _send_statistics_test_messages(self, websocket_manager, connections):

        """Send test messages for statistics verification"""

        for user_id, websocket in connections:

            for msg_idx in range(3):

                await websocket_manager.send_message_to_user(

                    user_id, 

                    {"test_message": f"message_{msg_idx}"}

                )
                
    async def _cleanup_statistics_test_connections(self, websocket_manager, connections):

        """Cleanup statistics test connections"""

        for user_id, websocket in connections:

            await websocket_manager.disconnect_user(user_id, websocket)
            
    def _verify_statistics_accuracy(self, websocket_manager):

        """Verify statistics match expected values"""

        stats = websocket_manager.get_stats()

        assert stats["total_connections"] == 5

        assert stats["total_messages_sent"] >= 15  # 5 users * 3 messages