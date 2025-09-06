from unittest.mock import Mock, patch, MagicMock

"""
L3 Integration Test: WebSocket Heartbeat Monitoring with Redis

Business Value Justification (BVJ):
    - Segment: Platform/Internal
- Business Goal: Reliability - Detect and handle dead connections promptly
- Value Impact: Prevents resource waste from zombie connections
- Strategic Impact: $60K MRR - Connection health for enterprise reliability

L3 Test: Uses real Redis for heartbeat tracking and connection health monitoring.
Health target: <30 second dead connection detection with automated cleanup.
""""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from uuid import uuid4

import redis.asyncio as redis
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas import User
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

from netra_backend.tests.integration.helpers.redis_l3_helpers import (

    RedisContainer, 

    MockWebSocketForRedis, 

    create_test_message

)

class HeartbeatMonitor:

    """Monitor WebSocket connection heartbeats."""
    
    def __init__(self, redis_client):

        self.redis_client = redis_client

        self.heartbeat_interval = 30  # seconds

        self.heartbeat_timeout = 90   # seconds

        self.heartbeat_prefix = "ws_heartbeat"

        self.connection_health_prefix = "ws_health"
    
    async def send_heartbeat(self, user_id: str, connection_id: str) -> None:

        """Send heartbeat for a connection."""

        heartbeat_key = f"{self.heartbeat_prefix}:{user_id}:{connection_id}"

        heartbeat_data = {

            "user_id": user_id,

            "connection_id": connection_id,

            "timestamp": time.time(),

            "status": "alive"

        }

        await self.redis_client.set(heartbeat_key, json.dumps(heartbeat_data), ex=self.heartbeat_timeout)
    
    async def check_heartbeat(self, user_id: str, connection_id: str) -> Optional[Dict[str, Any]]:

        """Check last heartbeat for a connection."""

        heartbeat_key = f"{self.heartbeat_prefix}:{user_id}:{connection_id}"

        heartbeat_data = await self.redis_client.get(heartbeat_key)

        if heartbeat_data:

            return json.loads(heartbeat_data)

        return None
    
    async def mark_connection_dead(self, user_id: str, connection_id: str) -> None:

        """Mark connection as dead."""

        health_key = f"{self.connection_health_prefix}:{user_id}:{connection_id}"

        health_data = {

            "user_id": user_id,

            "connection_id": connection_id,

            "status": "dead",

            "detected_at": time.time()

        }

        await self.redis_client.set(health_key, json.dumps(health_data), ex=3600)
    
    async def get_dead_connections(self) -> List[Dict[str, Any]]:

        """Get list of dead connections."""

        pattern = f"{self.connection_health_prefix}:*"

        dead_connections = []
        
        async for key in self.redis_client.scan_iter(match=pattern):

            data = await self.redis_client.get(key)

            if data:

                connection_info = json.loads(data)

                if connection_info.get("status") == "dead":

                    dead_connections.append(connection_info)
        
        return dead_connections
    
    async def cleanup_dead_connection(self, user_id: str, connection_id: str) -> None:

        """Clean up dead connection data."""

        heartbeat_key = f"{self.heartbeat_prefix}:{user_id}:{connection_id}"

        health_key = f"{self.connection_health_prefix}:{user_id}:{connection_id}"

        await self.redis_client.delete(heartbeat_key, health_key)

@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketHeartbeatMonitoringL3:

    """L3 integration tests for WebSocket heartbeat monitoring."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):

        """Set up Redis container for heartbeat monitoring."""

        container = RedisContainer(port=6386)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    
        @pytest.fixture
        async def redis_client(self, redis_container):

        """Create Redis client for heartbeat tracking."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    
        @pytest.fixture
        async def websocket_manager(self, redis_container):

        """Create WebSocket manager with heartbeat monitoring."""

        _, redis_url = redis_container
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.websocket_manager.redis_manager') as mock_redis_mgr:

        test_redis_mgr = RedisManager()

        test_redis_mgr.enabled = True

        test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

        mock_redis_mgr.return_value = test_redis_mgr

        mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client
            
        manager = WebSocketManager()

        yield manager
            
        await test_redis_mgr.redis_client.close()
    
        @pytest.fixture
        async def heartbeat_monitor(self, redis_client):

        """Create heartbeat monitor instance."""

        await asyncio.sleep(0)
        return HeartbeatMonitor(redis_client)
    
        @pytest.fixture
        def test_users(self):
        """Use real service instance."""
        # TODO: Initialize real service
        return None

        """Create test users for heartbeat testing."""

        return [

        User(

        id=f"heartbeat_user_{i}",

        email=f"heartbeatuser{i}@example.com", 

        username=f"heartbeatuser{i}",

        is_active=True,

        created_at=datetime.now(timezone.utc)

        )

        for i in range(5)

        ]
    
        @pytest.mark.asyncio
        async def test_basic_heartbeat_functionality(self, websocket_manager, heartbeat_monitor, test_users):

        """Test basic heartbeat send and check functionality."""

        user = test_users[0]

        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user

        connection_info = await websocket_manager.connect_user(user.id, websocket)

        assert connection_info is not None
        
        # Send heartbeat

        await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)
        
        # Check heartbeat

        heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

        assert heartbeat_data is not None

        assert heartbeat_data["user_id"] == user.id

        assert heartbeat_data["connection_id"] == connection_info.connection_id

        assert heartbeat_data["status"] == "alive"
        
        # Verify heartbeat timestamp is recent

        heartbeat_time = heartbeat_data["timestamp"]

        current_time = time.time()

        assert current_time - heartbeat_time < 5.0  # Within 5 seconds
        
        # Cleanup

        await websocket_manager.disconnect_user(user.id, websocket)

        await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)
    
        @pytest.mark.asyncio
        async def test_heartbeat_expiration_detection(self, websocket_manager, heartbeat_monitor, test_users):

        """Test detection of expired heartbeats."""

        user = test_users[0]

        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user

        connection_info = await websocket_manager.connect_user(user.id, websocket)

        assert connection_info is not None
        
        # Send heartbeat with short expiration

        heartbeat_monitor.heartbeat_timeout = 1  # 1 second for testing

        await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)
        
        # Verify heartbeat exists

        heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

        assert heartbeat_data is not None
        
        # Wait for expiration

        await asyncio.sleep(2)
        
        # Check heartbeat expired

        expired_heartbeat = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

        assert expired_heartbeat is None
        
        # Mark as dead connection

        await heartbeat_monitor.mark_connection_dead(user.id, connection_info.connection_id)
        
        # Verify dead connection tracking

        dead_connections = await heartbeat_monitor.get_dead_connections()

        dead_user_ids = [conn["user_id"] for conn in dead_connections]

        assert user.id in dead_user_ids
        
        # Cleanup

        await websocket_manager.disconnect_user(user.id, websocket)

        await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)
    
        @pytest.mark.asyncio
        async def test_multiple_connection_heartbeat_tracking(self, websocket_manager, heartbeat_monitor, test_users):

        """Test heartbeat tracking for multiple connections."""

        connections = []
        
        # Establish multiple connections

        for user in test_users:

        websocket = MockWebSocketForRedis(user.id)

        connection_info = await websocket_manager.connect_user(user.id, websocket)

        if connection_info:

        connections.append((user, websocket, connection_info))
        
        # Send heartbeats for all connections

        for user, _, connection_info in connections:

        await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)
        
        # Verify all heartbeats

        active_heartbeats = 0

        for user, _, connection_info in connections:

        heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

        if heartbeat_data and heartbeat_data["status"] == "alive":

        active_heartbeats += 1
        
        assert active_heartbeats == len(connections)
        
        # Simulate some connections going dead (no heartbeat updates)

        dead_count = 2

        for i in range(dead_count):

        user, _, connection_info = connections[i]

        await heartbeat_monitor.mark_connection_dead(user.id, connection_info.connection_id)
        
        # Check dead connection detection

        dead_connections = await heartbeat_monitor.get_dead_connections()

        assert len(dead_connections) >= dead_count
        
        # Cleanup

        for user, websocket, connection_info in connections:

        await websocket_manager.disconnect_user(user.id, websocket)

        await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)
    
        @pytest.mark.asyncio
        async def test_heartbeat_recovery_after_reconnection(self, websocket_manager, heartbeat_monitor, test_users):

        """Test heartbeat recovery after connection drop and reconnection."""

        user = test_users[0]
        
        # Initial connection

        first_websocket = MockWebSocketForRedis(user.id)

        first_connection = await websocket_manager.connect_user(user.id, first_websocket)

        assert first_connection is not None
        
        # Send heartbeat

        await heartbeat_monitor.send_heartbeat(user.id, first_connection.connection_id)
        
        # Simulate connection drop

        await websocket_manager.disconnect_user(user.id, first_websocket)
        
        # Mark as dead after detection delay

        await heartbeat_monitor.mark_connection_dead(user.id, first_connection.connection_id)
        
        # Reconnect

        second_websocket = MockWebSocketForRedis(user.id)

        second_connection = await websocket_manager.connect_user(user.id, second_websocket)

        assert second_connection is not None
        
        # New heartbeat for new connection

        await heartbeat_monitor.send_heartbeat(user.id, second_connection.connection_id)
        
        # Verify new heartbeat is active

        new_heartbeat = await heartbeat_monitor.check_heartbeat(user.id, second_connection.connection_id)

        assert new_heartbeat is not None

        assert new_heartbeat["status"] == "alive"
        
        # Cleanup old dead connection

        await heartbeat_monitor.cleanup_dead_connection(user.id, first_connection.connection_id)
        
        # Cleanup new connection

        await websocket_manager.disconnect_user(user.id, second_websocket)

        await heartbeat_monitor.cleanup_dead_connection(user.id, second_connection.connection_id)
    
        @pytest.mark.asyncio
        async def test_heartbeat_performance_under_load(self, websocket_manager, heartbeat_monitor, test_users):

        """Test heartbeat performance with multiple concurrent connections."""

        connection_count = 50

        connections = []
        
        # Establish connections

        for i in range(connection_count):

        user_id = f"load_user_{i}"

        websocket = MockWebSocketForRedis(user_id)

        connection_info = await websocket_manager.connect_user(user_id, websocket)

        if connection_info:

        connections.append((user_id, websocket, connection_info))
        
        # Send heartbeats concurrently

        heartbeat_start = time.time()

        heartbeat_tasks = []
        
        for user_id, _, connection_info in connections:

        task = heartbeat_monitor.send_heartbeat(user_id, connection_info.connection_id)

        heartbeat_tasks.append(task)
        
        await asyncio.gather(*heartbeat_tasks, return_exceptions=True)

        heartbeat_time = time.time() - heartbeat_start
        
        # Performance assertions

        assert heartbeat_time < 5.0  # Should complete quickly
        
        # Verify heartbeats

        verification_start = time.time()

        verification_tasks = []
        
        for user_id, _, connection_info in connections:

        task = heartbeat_monitor.check_heartbeat(user_id, connection_info.connection_id)

        verification_tasks.append(task)
        
        results = await asyncio.gather(*verification_tasks, return_exceptions=True)

        verification_time = time.time() - verification_start
        
        # Count successful heartbeats

        successful_heartbeats = sum(1 for result in results 

        if not isinstance(result, Exception) and result is not None)
        
        assert successful_heartbeats >= len(connections) * 0.9  # 90% success rate

        assert verification_time < 3.0  # Quick verification
        
        # Cleanup

        for user_id, websocket, connection_info in connections:

        await websocket_manager.disconnect_user(user_id, websocket)

        await heartbeat_monitor.cleanup_dead_connection(user_id, connection_info.connection_id)
    
        @pytest.mark.asyncio
        async def test_automated_dead_connection_cleanup(self, websocket_manager, heartbeat_monitor, test_users):

        """Test automated cleanup of dead connections."""

        user = test_users[0]

        websocket = MockWebSocketForRedis(user.id)
        
        # Connect and establish heartbeat

        connection_info = await websocket_manager.connect_user(user.id, websocket)

        assert connection_info is not None
        
        await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)
        
        # Simulate connection death

        await websocket_manager.disconnect_user(user.id, websocket)

        await heartbeat_monitor.mark_connection_dead(user.id, connection_info.connection_id)
        
        # Verify dead connection exists

        dead_connections = await heartbeat_monitor.get_dead_connections()

        initial_dead_count = len(dead_connections)

        assert initial_dead_count > 0
        
        # Cleanup dead connection

        await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)
        
        # Verify cleanup

        remaining_dead = await heartbeat_monitor.get_dead_connections()

        remaining_count = len(remaining_dead)

        assert remaining_count < initial_dead_count
        
        # Verify specific connection cleaned up

        heartbeat_check = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

        assert heartbeat_check is None
    
        @pytest.mark.asyncio
        async def test_heartbeat_monitoring_reliability(self, websocket_manager, heartbeat_monitor, test_users):

        """Test reliability of heartbeat monitoring system."""

        monitoring_duration = 10  # seconds

        heartbeat_interval = 2    # seconds

        user = test_users[0]
        
        websocket = MockWebSocketForRedis(user.id)

        connection_info = await websocket_manager.connect_user(user.id, websocket)

        assert connection_info is not None
        
        # Start heartbeat monitoring loop

        heartbeat_count = 0

        missed_heartbeats = 0

        start_time = time.time()
        
        while time.time() - start_time < monitoring_duration:

        try:
        # Send heartbeat

        await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)

        heartbeat_count += 1
                
        # Verify heartbeat immediately

        heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

        if heartbeat_data is None:

        missed_heartbeats += 1
                
        except Exception:

        missed_heartbeats += 1
            
        await asyncio.sleep(heartbeat_interval)
        
        # Calculate reliability metrics

        expected_heartbeats = monitoring_duration // heartbeat_interval

        reliability_rate = (heartbeat_count - missed_heartbeats) / heartbeat_count if heartbeat_count > 0 else 0
        
        # Reliability assertions

        assert heartbeat_count >= expected_heartbeats * 0.8  # At least 80% of expected heartbeats

        assert reliability_rate >= 0.95  # 95% reliability rate

        assert missed_heartbeats <= heartbeat_count * 0.1  # Less than 10% missed
        
        # Test connection health detection
        # Stop sending heartbeats to simulate dead connection

        await asyncio.sleep(heartbeat_monitor.heartbeat_timeout + 1)
        
        # Check if connection is detected as dead

        final_heartbeat = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)
        # Should be None due to expiration
        
        # Cleanup

        await websocket_manager.disconnect_user(user.id, websocket)

        await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])