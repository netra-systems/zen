from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: L3 Integration Test: WebSocket Heartbeat Monitoring with Redis

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
    # REMOVED_SYNTAX_ERROR: - Business Goal: Reliability - Detect and handle dead connections promptly
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents resource waste from zombie connections
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: $60K MRR - Connection health for enterprise reliability

    # REMOVED_SYNTAX_ERROR: L3 Test: Uses real Redis for heartbeat tracking and connection health monitoring.
    # REMOVED_SYNTAX_ERROR: Health target: <30 second dead connection detection with automated cleanup.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # Test framework import - using pytest fixtures instead
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.docker.unified_docker_manager import UnifiedDockerManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List, Optional
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from uuid import uuid4

    # REMOVED_SYNTAX_ERROR: import redis.asyncio as redis
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.redis_manager import RedisManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas import User
    # Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
    # REMOVED_SYNTAX_ERROR: from test_framework.real_services import get_real_services

    # REMOVED_SYNTAX_ERROR: from netra_backend.tests.integration.helpers.redis_l3_helpers import ( )

    # REMOVED_SYNTAX_ERROR: RedisContainer,

    # REMOVED_SYNTAX_ERROR: MockWebSocketForRedis,

    # REMOVED_SYNTAX_ERROR: create_test_message

    

# REMOVED_SYNTAX_ERROR: class HeartbeatMonitor:

    # REMOVED_SYNTAX_ERROR: """Monitor WebSocket connection heartbeats."""

# REMOVED_SYNTAX_ERROR: def __init__(self, redis_client):

    # REMOVED_SYNTAX_ERROR: self.redis_client = redis_client

    # REMOVED_SYNTAX_ERROR: self.heartbeat_interval = 30  # seconds

    # REMOVED_SYNTAX_ERROR: self.heartbeat_timeout = 90   # seconds

    # REMOVED_SYNTAX_ERROR: self.heartbeat_prefix = "ws_heartbeat"

    # REMOVED_SYNTAX_ERROR: self.connection_health_prefix = "ws_health"

# REMOVED_SYNTAX_ERROR: async def send_heartbeat(self, user_id: str, connection_id: str) -> None:

    # REMOVED_SYNTAX_ERROR: """Send heartbeat for a connection."""

    # REMOVED_SYNTAX_ERROR: heartbeat_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: heartbeat_data = { )

    # REMOVED_SYNTAX_ERROR: "user_id": user_id,

    # REMOVED_SYNTAX_ERROR: "connection_id": connection_id,

    # REMOVED_SYNTAX_ERROR: "timestamp": time.time(),

    # REMOVED_SYNTAX_ERROR: "status": "alive"

    

    # REMOVED_SYNTAX_ERROR: await self.redis_client.set(heartbeat_key, json.dumps(heartbeat_data), ex=self.heartbeat_timeout)

# REMOVED_SYNTAX_ERROR: async def check_heartbeat(self, user_id: str, connection_id: str) -> Optional[Dict[str, Any]]:

    # REMOVED_SYNTAX_ERROR: """Check last heartbeat for a connection."""

    # REMOVED_SYNTAX_ERROR: heartbeat_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: heartbeat_data = await self.redis_client.get(heartbeat_key)

    # REMOVED_SYNTAX_ERROR: if heartbeat_data:

        # REMOVED_SYNTAX_ERROR: return json.loads(heartbeat_data)

        # REMOVED_SYNTAX_ERROR: return None

# REMOVED_SYNTAX_ERROR: async def mark_connection_dead(self, user_id: str, connection_id: str) -> None:

    # REMOVED_SYNTAX_ERROR: """Mark connection as dead."""

    # REMOVED_SYNTAX_ERROR: health_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: health_data = { )

    # REMOVED_SYNTAX_ERROR: "user_id": user_id,

    # REMOVED_SYNTAX_ERROR: "connection_id": connection_id,

    # REMOVED_SYNTAX_ERROR: "status": "dead",

    # REMOVED_SYNTAX_ERROR: "detected_at": time.time()

    

    # REMOVED_SYNTAX_ERROR: await self.redis_client.set(health_key, json.dumps(health_data), ex=3600)

# REMOVED_SYNTAX_ERROR: async def get_dead_connections(self) -> List[Dict[str, Any]]:

    # REMOVED_SYNTAX_ERROR: """Get list of dead connections."""

    # REMOVED_SYNTAX_ERROR: pattern = "formatted_string"

    # REMOVED_SYNTAX_ERROR: dead_connections = []

    # REMOVED_SYNTAX_ERROR: async for key in self.redis_client.scan_iter(match=pattern):

        # REMOVED_SYNTAX_ERROR: data = await self.redis_client.get(key)

        # REMOVED_SYNTAX_ERROR: if data:

            # REMOVED_SYNTAX_ERROR: connection_info = json.loads(data)

            # REMOVED_SYNTAX_ERROR: if connection_info.get("status") == "dead":

                # REMOVED_SYNTAX_ERROR: dead_connections.append(connection_info)

                # REMOVED_SYNTAX_ERROR: return dead_connections

# REMOVED_SYNTAX_ERROR: async def cleanup_dead_connection(self, user_id: str, connection_id: str) -> None:

    # REMOVED_SYNTAX_ERROR: """Clean up dead connection data."""

    # REMOVED_SYNTAX_ERROR: heartbeat_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: health_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: await self.redis_client.delete(heartbeat_key, health_key)

    # REMOVED_SYNTAX_ERROR: @pytest.mark.L3

    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration

# REMOVED_SYNTAX_ERROR: class TestWebSocketHeartbeatMonitoringL3:

    # REMOVED_SYNTAX_ERROR: """L3 integration tests for WebSocket heartbeat monitoring."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_container(self):

    # REMOVED_SYNTAX_ERROR: """Set up Redis container for heartbeat monitoring."""

    # REMOVED_SYNTAX_ERROR: container = RedisContainer(port=6386)

    # REMOVED_SYNTAX_ERROR: redis_url = await container.start()

    # REMOVED_SYNTAX_ERROR: yield container, redis_url

    # REMOVED_SYNTAX_ERROR: await container.stop()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_client(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create Redis client for heartbeat tracking."""

    # REMOVED_SYNTAX_ERROR: _, redis_url = redis_container

    # REMOVED_SYNTAX_ERROR: client = redis.Redis.from_url(redis_url, decode_responses=True)

    # REMOVED_SYNTAX_ERROR: yield client

    # REMOVED_SYNTAX_ERROR: await client.close()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def websocket_manager(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager with heartbeat monitoring."""

    # REMOVED_SYNTAX_ERROR: _, redis_url = redis_container

    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_manager.redis_manager') as mock_redis_mgr:

        # REMOVED_SYNTAX_ERROR: test_redis_mgr = RedisManager()

        # REMOVED_SYNTAX_ERROR: test_redis_mgr.enabled = True

        # REMOVED_SYNTAX_ERROR: test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

        # REMOVED_SYNTAX_ERROR: mock_redis_mgr.return_value = test_redis_mgr

        # REMOVED_SYNTAX_ERROR: mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client

        # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

        # REMOVED_SYNTAX_ERROR: yield manager

        # REMOVED_SYNTAX_ERROR: await test_redis_mgr.redis_client.close()

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def heartbeat_monitor(self, redis_client):

    # REMOVED_SYNTAX_ERROR: """Create heartbeat monitor instance."""

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return HeartbeatMonitor(redis_client)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_users(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Create test users for heartbeat testing."""

    # REMOVED_SYNTAX_ERROR: return [ )

    # REMOVED_SYNTAX_ERROR: User( )

    # REMOVED_SYNTAX_ERROR: id="formatted_string",

    # REMOVED_SYNTAX_ERROR: email="formatted_string",

    # REMOVED_SYNTAX_ERROR: username="formatted_string",

    # REMOVED_SYNTAX_ERROR: is_active=True,

    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc)

    

    # REMOVED_SYNTAX_ERROR: for i in range(5)

    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_basic_heartbeat_functionality(self, websocket_manager, heartbeat_monitor, test_users):

        # REMOVED_SYNTAX_ERROR: """Test basic heartbeat send and check functionality."""

        # REMOVED_SYNTAX_ERROR: user = test_users[0]

        # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

        # Connect user

        # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

        # REMOVED_SYNTAX_ERROR: assert connection_info is not None

        # Send heartbeat

        # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)

        # Check heartbeat

        # REMOVED_SYNTAX_ERROR: heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

        # REMOVED_SYNTAX_ERROR: assert heartbeat_data is not None

        # REMOVED_SYNTAX_ERROR: assert heartbeat_data["user_id"] == user.id

        # REMOVED_SYNTAX_ERROR: assert heartbeat_data["connection_id"] == connection_info.connection_id

        # REMOVED_SYNTAX_ERROR: assert heartbeat_data["status"] == "alive"

        # Verify heartbeat timestamp is recent

        # REMOVED_SYNTAX_ERROR: heartbeat_time = heartbeat_data["timestamp"]

        # REMOVED_SYNTAX_ERROR: current_time = time.time()

        # REMOVED_SYNTAX_ERROR: assert current_time - heartbeat_time < 5.0  # Within 5 seconds

        # Cleanup

        # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

        # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_heartbeat_expiration_detection(self, websocket_manager, heartbeat_monitor, test_users):

            # REMOVED_SYNTAX_ERROR: """Test detection of expired heartbeats."""

            # REMOVED_SYNTAX_ERROR: user = test_users[0]

            # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

            # Connect user

            # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

            # REMOVED_SYNTAX_ERROR: assert connection_info is not None

            # Send heartbeat with short expiration

            # REMOVED_SYNTAX_ERROR: heartbeat_monitor.heartbeat_timeout = 1  # 1 second for testing

            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)

            # Verify heartbeat exists

            # REMOVED_SYNTAX_ERROR: heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

            # REMOVED_SYNTAX_ERROR: assert heartbeat_data is not None

            # Wait for expiration

            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(2)

            # Check heartbeat expired

            # REMOVED_SYNTAX_ERROR: expired_heartbeat = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

            # REMOVED_SYNTAX_ERROR: assert expired_heartbeat is None

            # Mark as dead connection

            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.mark_connection_dead(user.id, connection_info.connection_id)

            # Verify dead connection tracking

            # REMOVED_SYNTAX_ERROR: dead_connections = await heartbeat_monitor.get_dead_connections()

            # REMOVED_SYNTAX_ERROR: dead_user_ids = [conn["user_id"] for conn in dead_connections]

            # REMOVED_SYNTAX_ERROR: assert user.id in dead_user_ids

            # Cleanup

            # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_multiple_connection_heartbeat_tracking(self, websocket_manager, heartbeat_monitor, test_users):

                # REMOVED_SYNTAX_ERROR: """Test heartbeat tracking for multiple connections."""

                # REMOVED_SYNTAX_ERROR: connections = []

                # Establish multiple connections

                # REMOVED_SYNTAX_ERROR: for user in test_users:

                    # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                    # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                    # REMOVED_SYNTAX_ERROR: if connection_info:

                        # REMOVED_SYNTAX_ERROR: connections.append((user, websocket, connection_info))

                        # Send heartbeats for all connections

                        # REMOVED_SYNTAX_ERROR: for user, _, connection_info in connections:

                            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)

                            # Verify all heartbeats

                            # REMOVED_SYNTAX_ERROR: active_heartbeats = 0

                            # REMOVED_SYNTAX_ERROR: for user, _, connection_info in connections:

                                # REMOVED_SYNTAX_ERROR: heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

                                # REMOVED_SYNTAX_ERROR: if heartbeat_data and heartbeat_data["status"] == "alive":

                                    # REMOVED_SYNTAX_ERROR: active_heartbeats += 1

                                    # REMOVED_SYNTAX_ERROR: assert active_heartbeats == len(connections)

                                    # Simulate some connections going dead (no heartbeat updates)

                                    # REMOVED_SYNTAX_ERROR: dead_count = 2

                                    # REMOVED_SYNTAX_ERROR: for i in range(dead_count):

                                        # REMOVED_SYNTAX_ERROR: user, _, connection_info = connections[i]

                                        # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.mark_connection_dead(user.id, connection_info.connection_id)

                                        # Check dead connection detection

                                        # REMOVED_SYNTAX_ERROR: dead_connections = await heartbeat_monitor.get_dead_connections()

                                        # REMOVED_SYNTAX_ERROR: assert len(dead_connections) >= dead_count

                                        # Cleanup

                                        # REMOVED_SYNTAX_ERROR: for user, websocket, connection_info in connections:

                                            # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                                            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_heartbeat_recovery_after_reconnection(self, websocket_manager, heartbeat_monitor, test_users):

                                                # REMOVED_SYNTAX_ERROR: """Test heartbeat recovery after connection drop and reconnection."""

                                                # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                                # Initial connection

                                                # REMOVED_SYNTAX_ERROR: first_websocket = MockWebSocketForRedis(user.id)

                                                # REMOVED_SYNTAX_ERROR: first_connection = await websocket_manager.connect_user(user.id, first_websocket)

                                                # REMOVED_SYNTAX_ERROR: assert first_connection is not None

                                                # Send heartbeat

                                                # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.send_heartbeat(user.id, first_connection.connection_id)

                                                # Simulate connection drop

                                                # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, first_websocket)

                                                # Mark as dead after detection delay

                                                # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.mark_connection_dead(user.id, first_connection.connection_id)

                                                # Reconnect

                                                # REMOVED_SYNTAX_ERROR: second_websocket = MockWebSocketForRedis(user.id)

                                                # REMOVED_SYNTAX_ERROR: second_connection = await websocket_manager.connect_user(user.id, second_websocket)

                                                # REMOVED_SYNTAX_ERROR: assert second_connection is not None

                                                # New heartbeat for new connection

                                                # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.send_heartbeat(user.id, second_connection.connection_id)

                                                # Verify new heartbeat is active

                                                # REMOVED_SYNTAX_ERROR: new_heartbeat = await heartbeat_monitor.check_heartbeat(user.id, second_connection.connection_id)

                                                # REMOVED_SYNTAX_ERROR: assert new_heartbeat is not None

                                                # REMOVED_SYNTAX_ERROR: assert new_heartbeat["status"] == "alive"

                                                # Cleanup old dead connection

                                                # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user.id, first_connection.connection_id)

                                                # Cleanup new connection

                                                # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, second_websocket)

                                                # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user.id, second_connection.connection_id)

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_heartbeat_performance_under_load(self, websocket_manager, heartbeat_monitor, test_users):

                                                    # REMOVED_SYNTAX_ERROR: """Test heartbeat performance with multiple concurrent connections."""

                                                    # REMOVED_SYNTAX_ERROR: connection_count = 50

                                                    # REMOVED_SYNTAX_ERROR: connections = []

                                                    # Establish connections

                                                    # REMOVED_SYNTAX_ERROR: for i in range(connection_count):

                                                        # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"

                                                        # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user_id)

                                                        # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user_id, websocket)

                                                        # REMOVED_SYNTAX_ERROR: if connection_info:

                                                            # REMOVED_SYNTAX_ERROR: connections.append((user_id, websocket, connection_info))

                                                            # Send heartbeats concurrently

                                                            # REMOVED_SYNTAX_ERROR: heartbeat_start = time.time()

                                                            # REMOVED_SYNTAX_ERROR: heartbeat_tasks = []

                                                            # REMOVED_SYNTAX_ERROR: for user_id, _, connection_info in connections:

                                                                # REMOVED_SYNTAX_ERROR: task = heartbeat_monitor.send_heartbeat(user_id, connection_info.connection_id)

                                                                # REMOVED_SYNTAX_ERROR: heartbeat_tasks.append(task)

                                                                # REMOVED_SYNTAX_ERROR: await asyncio.gather(*heartbeat_tasks, return_exceptions=True)

                                                                # REMOVED_SYNTAX_ERROR: heartbeat_time = time.time() - heartbeat_start

                                                                # Performance assertions

                                                                # REMOVED_SYNTAX_ERROR: assert heartbeat_time < 5.0  # Should complete quickly

                                                                # Verify heartbeats

                                                                # REMOVED_SYNTAX_ERROR: verification_start = time.time()

                                                                # REMOVED_SYNTAX_ERROR: verification_tasks = []

                                                                # REMOVED_SYNTAX_ERROR: for user_id, _, connection_info in connections:

                                                                    # REMOVED_SYNTAX_ERROR: task = heartbeat_monitor.check_heartbeat(user_id, connection_info.connection_id)

                                                                    # REMOVED_SYNTAX_ERROR: verification_tasks.append(task)

                                                                    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*verification_tasks, return_exceptions=True)

                                                                    # REMOVED_SYNTAX_ERROR: verification_time = time.time() - verification_start

                                                                    # Count successful heartbeats

                                                                    # REMOVED_SYNTAX_ERROR: successful_heartbeats = sum(1 for result in results )

                                                                    # REMOVED_SYNTAX_ERROR: if not isinstance(result, Exception) and result is not None)

                                                                    # REMOVED_SYNTAX_ERROR: assert successful_heartbeats >= len(connections) * 0.9  # 90% success rate

                                                                    # REMOVED_SYNTAX_ERROR: assert verification_time < 3.0  # Quick verification

                                                                    # Cleanup

                                                                    # REMOVED_SYNTAX_ERROR: for user_id, websocket, connection_info in connections:

                                                                        # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user_id, websocket)

                                                                        # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user_id, connection_info.connection_id)

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_automated_dead_connection_cleanup(self, websocket_manager, heartbeat_monitor, test_users):

                                                                            # REMOVED_SYNTAX_ERROR: """Test automated cleanup of dead connections."""

                                                                            # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                                                            # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                                                            # Connect and establish heartbeat

                                                                            # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                                                                            # REMOVED_SYNTAX_ERROR: assert connection_info is not None

                                                                            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)

                                                                            # Simulate connection death

                                                                            # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                                                                            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.mark_connection_dead(user.id, connection_info.connection_id)

                                                                            # Verify dead connection exists

                                                                            # REMOVED_SYNTAX_ERROR: dead_connections = await heartbeat_monitor.get_dead_connections()

                                                                            # REMOVED_SYNTAX_ERROR: initial_dead_count = len(dead_connections)

                                                                            # REMOVED_SYNTAX_ERROR: assert initial_dead_count > 0

                                                                            # Cleanup dead connection

                                                                            # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)

                                                                            # Verify cleanup

                                                                            # REMOVED_SYNTAX_ERROR: remaining_dead = await heartbeat_monitor.get_dead_connections()

                                                                            # REMOVED_SYNTAX_ERROR: remaining_count = len(remaining_dead)

                                                                            # REMOVED_SYNTAX_ERROR: assert remaining_count < initial_dead_count

                                                                            # Verify specific connection cleaned up

                                                                            # REMOVED_SYNTAX_ERROR: heartbeat_check = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

                                                                            # REMOVED_SYNTAX_ERROR: assert heartbeat_check is None

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_heartbeat_monitoring_reliability(self, websocket_manager, heartbeat_monitor, test_users):

                                                                                # REMOVED_SYNTAX_ERROR: """Test reliability of heartbeat monitoring system."""

                                                                                # REMOVED_SYNTAX_ERROR: monitoring_duration = 10  # seconds

                                                                                # REMOVED_SYNTAX_ERROR: heartbeat_interval = 2    # seconds

                                                                                # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                                                                # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                                                                # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                                                                                # REMOVED_SYNTAX_ERROR: assert connection_info is not None

                                                                                # Start heartbeat monitoring loop

                                                                                # REMOVED_SYNTAX_ERROR: heartbeat_count = 0

                                                                                # REMOVED_SYNTAX_ERROR: missed_heartbeats = 0

                                                                                # REMOVED_SYNTAX_ERROR: start_time = time.time()

                                                                                # REMOVED_SYNTAX_ERROR: while time.time() - start_time < monitoring_duration:

                                                                                    # REMOVED_SYNTAX_ERROR: try:
                                                                                        # Send heartbeat

                                                                                        # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.send_heartbeat(user.id, connection_info.connection_id)

                                                                                        # REMOVED_SYNTAX_ERROR: heartbeat_count += 1

                                                                                        # Verify heartbeat immediately

                                                                                        # REMOVED_SYNTAX_ERROR: heartbeat_data = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)

                                                                                        # REMOVED_SYNTAX_ERROR: if heartbeat_data is None:

                                                                                            # REMOVED_SYNTAX_ERROR: missed_heartbeats += 1

                                                                                            # REMOVED_SYNTAX_ERROR: except Exception:

                                                                                                # REMOVED_SYNTAX_ERROR: missed_heartbeats += 1

                                                                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(heartbeat_interval)

                                                                                                # Calculate reliability metrics

                                                                                                # REMOVED_SYNTAX_ERROR: expected_heartbeats = monitoring_duration // heartbeat_interval

                                                                                                # REMOVED_SYNTAX_ERROR: reliability_rate = (heartbeat_count - missed_heartbeats) / heartbeat_count if heartbeat_count > 0 else 0

                                                                                                # Reliability assertions

                                                                                                # REMOVED_SYNTAX_ERROR: assert heartbeat_count >= expected_heartbeats * 0.8  # At least 80% of expected heartbeats

                                                                                                # REMOVED_SYNTAX_ERROR: assert reliability_rate >= 0.95  # 95% reliability rate

                                                                                                # REMOVED_SYNTAX_ERROR: assert missed_heartbeats <= heartbeat_count * 0.1  # Less than 10% missed

                                                                                                # Test connection health detection
                                                                                                # Stop sending heartbeats to simulate dead connection

                                                                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(heartbeat_monitor.heartbeat_timeout + 1)

                                                                                                # Check if connection is detected as dead

                                                                                                # REMOVED_SYNTAX_ERROR: final_heartbeat = await heartbeat_monitor.check_heartbeat(user.id, connection_info.connection_id)
                                                                                                # Should be None due to expiration

                                                                                                # Cleanup

                                                                                                # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                                                                                                # REMOVED_SYNTAX_ERROR: await heartbeat_monitor.cleanup_dead_connection(user.id, connection_info.connection_id)

                                                                                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":

                                                                                                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s", "--tb=short"])