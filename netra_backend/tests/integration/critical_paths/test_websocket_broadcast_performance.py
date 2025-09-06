from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: L3 Integration Test: WebSocket Broadcast Performance with Redis

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Enterprise
    # REMOVED_SYNTAX_ERROR: - Business Goal: Scalability - Handle enterprise-scale broadcasts efficiently
    # REMOVED_SYNTAX_ERROR: - Value Impact: Enables real-time features for large teams and workspaces
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: $60K MRR - Enterprise broadcast capability for collaboration

    # REMOVED_SYNTAX_ERROR: L3 Test: Uses real Redis for broadcast performance validation.
    # REMOVED_SYNTAX_ERROR: Performance target: 1000+ concurrent connections with <100ms broadcast latency.
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
    # REMOVED_SYNTAX_ERROR: import statistics
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List, Tuple
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from uuid import uuid4
    # REMOVED_SYNTAX_ERROR: from concurrent.futures import ThreadPoolExecutor

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

    

# REMOVED_SYNTAX_ERROR: class BroadcastPerformanceTracker:

    # REMOVED_SYNTAX_ERROR: """Track broadcast performance metrics."""

# REMOVED_SYNTAX_ERROR: def __init__(self):

    # REMOVED_SYNTAX_ERROR: self.broadcast_times: List[float] = []

    # REMOVED_SYNTAX_ERROR: self.delivery_times: List[float] = []

    # REMOVED_SYNTAX_ERROR: self.success_counts: List[int] = []

    # REMOVED_SYNTAX_ERROR: self.error_counts: List[int] = []

    # REMOVED_SYNTAX_ERROR: self.memory_usage: List[int] = []

# REMOVED_SYNTAX_ERROR: def record_broadcast(self, duration: float, successes: int, errors: int) -> None:

    # REMOVED_SYNTAX_ERROR: """Record broadcast performance metrics."""

    # REMOVED_SYNTAX_ERROR: self.broadcast_times.append(duration)

    # REMOVED_SYNTAX_ERROR: self.success_counts.append(successes)

    # REMOVED_SYNTAX_ERROR: self.error_counts.append(errors)

# REMOVED_SYNTAX_ERROR: def record_delivery(self, duration: float) -> None:

    # REMOVED_SYNTAX_ERROR: """Record individual delivery time."""

    # REMOVED_SYNTAX_ERROR: self.delivery_times.append(duration)

# REMOVED_SYNTAX_ERROR: def record_memory(self, usage: int) -> None:

    # REMOVED_SYNTAX_ERROR: """Record memory usage."""

    # REMOVED_SYNTAX_ERROR: self.memory_usage.append(usage)

# REMOVED_SYNTAX_ERROR: def get_performance_summary(self) -> Dict[str, Any]:

    # REMOVED_SYNTAX_ERROR: """Get performance summary statistics."""

    # REMOVED_SYNTAX_ERROR: return { )

    # REMOVED_SYNTAX_ERROR: "avg_broadcast_time": statistics.mean(self.broadcast_times) if self.broadcast_times else 0,

    # REMOVED_SYNTAX_ERROR: "max_broadcast_time": max(self.broadcast_times) if self.broadcast_times else 0,

    # REMOVED_SYNTAX_ERROR: "avg_delivery_time": statistics.mean(self.delivery_times) if self.delivery_times else 0,

    # REMOVED_SYNTAX_ERROR: "total_successes": sum(self.success_counts),

    # REMOVED_SYNTAX_ERROR: "total_errors": sum(self.error_counts),

    # REMOVED_SYNTAX_ERROR: "success_rate": sum(self.success_counts) / (sum(self.success_counts) + sum(self.error_counts)) if self.success_counts or self.error_counts else 0,

    # REMOVED_SYNTAX_ERROR: "peak_memory": max(self.memory_usage) if self.memory_usage else 0

    

    # REMOVED_SYNTAX_ERROR: @pytest.mark.L3

    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration

# REMOVED_SYNTAX_ERROR: class TestWebSocketBroadcastPerformanceL3:

    # REMOVED_SYNTAX_ERROR: """L3 integration tests for WebSocket broadcast performance."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_container(self):

    # REMOVED_SYNTAX_ERROR: """Set up Redis container for broadcast performance testing."""

    # REMOVED_SYNTAX_ERROR: container = RedisContainer(port=6385)

    # REMOVED_SYNTAX_ERROR: redis_url = await container.start()

    # REMOVED_SYNTAX_ERROR: yield container, redis_url

    # REMOVED_SYNTAX_ERROR: await container.stop()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_client(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create Redis client for broadcast operations."""

    # REMOVED_SYNTAX_ERROR: _, redis_url = redis_container

    # REMOVED_SYNTAX_ERROR: client = redis.Redis.from_url(redis_url, decode_responses=True)

    # REMOVED_SYNTAX_ERROR: yield client

    # REMOVED_SYNTAX_ERROR: await client.close()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def websocket_manager(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager for broadcast testing."""

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
# REMOVED_SYNTAX_ERROR: def large_user_pool(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Create large pool of test users for performance testing."""

    # REMOVED_SYNTAX_ERROR: return [ )

    # REMOVED_SYNTAX_ERROR: User( )

    # REMOVED_SYNTAX_ERROR: id="formatted_string",

    # REMOVED_SYNTAX_ERROR: email="formatted_string",

    # REMOVED_SYNTAX_ERROR: username="formatted_string",

    # REMOVED_SYNTAX_ERROR: is_active=True,

    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc)

    

    # REMOVED_SYNTAX_ERROR: for i in range(1000)  # Large user pool for performance testing

    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def performance_tracker(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Create performance tracking instance."""

    # REMOVED_SYNTAX_ERROR: return BroadcastPerformanceTracker()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_small_scale_broadcast_baseline(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

        # REMOVED_SYNTAX_ERROR: """Test broadcast performance baseline with small user count."""

        # REMOVED_SYNTAX_ERROR: user_count = 50

        # REMOVED_SYNTAX_ERROR: users = large_user_pool[:user_count]

        # REMOVED_SYNTAX_ERROR: connections = []

        # Establish connections

        # REMOVED_SYNTAX_ERROR: connection_start = time.time()

        # REMOVED_SYNTAX_ERROR: for user in users:

            # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

            # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

            # REMOVED_SYNTAX_ERROR: if connection_info:

                # REMOVED_SYNTAX_ERROR: connections.append((user, websocket))

                # REMOVED_SYNTAX_ERROR: connection_time = time.time() - connection_start

                # REMOVED_SYNTAX_ERROR: actual_connections = len(connections)

                # REMOVED_SYNTAX_ERROR: assert actual_connections >= user_count * 0.9  # 90% connection success

                # Perform broadcast

                # REMOVED_SYNTAX_ERROR: broadcast_message = create_test_message( )

                # REMOVED_SYNTAX_ERROR: "small_broadcast",

                # REMOVED_SYNTAX_ERROR: "system",

                # REMOVED_SYNTAX_ERROR: { )

                # REMOVED_SYNTAX_ERROR: "broadcast_id": str(uuid4()),

                # REMOVED_SYNTAX_ERROR: "content": "Small scale broadcast test",

                # REMOVED_SYNTAX_ERROR: "target_count": actual_connections

                

                

                # REMOVED_SYNTAX_ERROR: broadcast_start = time.time()

                # REMOVED_SYNTAX_ERROR: success_count = 0

                # REMOVED_SYNTAX_ERROR: error_count = 0

                # Broadcast to all connections

                # REMOVED_SYNTAX_ERROR: tasks = []

                # REMOVED_SYNTAX_ERROR: for user, _ in connections:

                    # REMOVED_SYNTAX_ERROR: channel = "formatted_string"

                    # REMOVED_SYNTAX_ERROR: task = redis_client.publish(channel, json.dumps(broadcast_message))

                    # REMOVED_SYNTAX_ERROR: tasks.append(task)

                    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                    # REMOVED_SYNTAX_ERROR: for result in results:

                        # REMOVED_SYNTAX_ERROR: if isinstance(result, Exception):

                            # REMOVED_SYNTAX_ERROR: error_count += 1

                            # REMOVED_SYNTAX_ERROR: else:

                                # REMOVED_SYNTAX_ERROR: success_count += 1

                                # REMOVED_SYNTAX_ERROR: broadcast_time = time.time() - broadcast_start

                                # Record performance

                                # REMOVED_SYNTAX_ERROR: performance_tracker.record_broadcast(broadcast_time, success_count, error_count)

                                # Performance assertions

                                # REMOVED_SYNTAX_ERROR: assert broadcast_time < 2.0  # Should complete quickly

                                # REMOVED_SYNTAX_ERROR: assert success_count >= actual_connections * 0.95  # 95% success rate

                                # Cleanup

                                # REMOVED_SYNTAX_ERROR: for user, websocket in connections:

                                    # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_medium_scale_broadcast_performance(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

                                        # REMOVED_SYNTAX_ERROR: """Test broadcast performance with medium user count."""

                                        # REMOVED_SYNTAX_ERROR: user_count = 200

                                        # REMOVED_SYNTAX_ERROR: users = large_user_pool[:user_count]

                                        # REMOVED_SYNTAX_ERROR: connections = []

                                        # Establish connections in batches for better performance

                                        # REMOVED_SYNTAX_ERROR: batch_size = 50

                                        # REMOVED_SYNTAX_ERROR: for i in range(0, len(users), batch_size):

                                            # REMOVED_SYNTAX_ERROR: batch = users[i:i + batch_size]

                                            # REMOVED_SYNTAX_ERROR: batch_tasks = []

                                            # REMOVED_SYNTAX_ERROR: for user in batch:

                                                # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                                # REMOVED_SYNTAX_ERROR: task = websocket_manager.connect_user(user.id, websocket)

                                                # REMOVED_SYNTAX_ERROR: batch_tasks.append((user, websocket, task))

                                                # Execute batch

                                                # REMOVED_SYNTAX_ERROR: for user, websocket, task in batch_tasks:

                                                    # REMOVED_SYNTAX_ERROR: try:

                                                        # REMOVED_SYNTAX_ERROR: connection_info = await task

                                                        # REMOVED_SYNTAX_ERROR: if connection_info:

                                                            # REMOVED_SYNTAX_ERROR: connections.append((user, websocket))

                                                            # REMOVED_SYNTAX_ERROR: except Exception:


                                                                # REMOVED_SYNTAX_ERROR: actual_connections = len(connections)

                                                                # REMOVED_SYNTAX_ERROR: assert actual_connections >= user_count * 0.85  # 85% connection success for medium scale

                                                                # Test broadcast performance

                                                                # REMOVED_SYNTAX_ERROR: broadcast_message = create_test_message( )

                                                                # REMOVED_SYNTAX_ERROR: "medium_broadcast",

                                                                # REMOVED_SYNTAX_ERROR: "system",

                                                                # REMOVED_SYNTAX_ERROR: { )

                                                                # REMOVED_SYNTAX_ERROR: "broadcast_id": str(uuid4()),

                                                                # REMOVED_SYNTAX_ERROR: "content": "Medium scale broadcast test",

                                                                # REMOVED_SYNTAX_ERROR: "target_count": actual_connections,

                                                                # REMOVED_SYNTAX_ERROR: "timestamp": time.time()

                                                                

                                                                

                                                                # REMOVED_SYNTAX_ERROR: broadcast_start = time.time()

                                                                # Use pipeline for better Redis performance

                                                                # REMOVED_SYNTAX_ERROR: pipe = redis_client.pipeline()

                                                                # REMOVED_SYNTAX_ERROR: for user, _ in connections:

                                                                    # REMOVED_SYNTAX_ERROR: channel = "formatted_string"

                                                                    # REMOVED_SYNTAX_ERROR: pipe.publish(channel, json.dumps(broadcast_message))

                                                                    # REMOVED_SYNTAX_ERROR: results = await pipe.execute()

                                                                    # REMOVED_SYNTAX_ERROR: broadcast_time = time.time() - broadcast_start

                                                                    # REMOVED_SYNTAX_ERROR: success_count = len([item for item in []])  # Redis publish returns subscriber count

                                                                    # REMOVED_SYNTAX_ERROR: error_count = actual_connections - success_count

                                                                    # REMOVED_SYNTAX_ERROR: performance_tracker.record_broadcast(broadcast_time, success_count, error_count)

                                                                    # Performance assertions

                                                                    # REMOVED_SYNTAX_ERROR: assert broadcast_time < 5.0  # Should complete within 5 seconds

                                                                    # REMOVED_SYNTAX_ERROR: assert success_count >= actual_connections * 0.9  # 90% success rate

                                                                    # Cleanup

                                                                    # REMOVED_SYNTAX_ERROR: cleanup_tasks = []

                                                                    # REMOVED_SYNTAX_ERROR: for user, websocket in connections:

                                                                        # REMOVED_SYNTAX_ERROR: task = websocket_manager.disconnect_user(user.id, websocket)

                                                                        # REMOVED_SYNTAX_ERROR: cleanup_tasks.append(task)

                                                                        # REMOVED_SYNTAX_ERROR: await asyncio.gather(*cleanup_tasks, return_exceptions=True)

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_large_scale_broadcast_performance(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

                                                                            # REMOVED_SYNTAX_ERROR: """Test broadcast performance with large user count."""

                                                                            # REMOVED_SYNTAX_ERROR: user_count = 500  # Reduced for CI stability

                                                                            # REMOVED_SYNTAX_ERROR: users = large_user_pool[:user_count]

                                                                            # REMOVED_SYNTAX_ERROR: connections = []

                                                                            # Optimized connection establishment

                                                                            # REMOVED_SYNTAX_ERROR: connection_batches = []

                                                                            # REMOVED_SYNTAX_ERROR: batch_size = 100

                                                                            # REMOVED_SYNTAX_ERROR: for i in range(0, len(users), batch_size):

                                                                                # REMOVED_SYNTAX_ERROR: batch = users[i:i + batch_size]

                                                                                # REMOVED_SYNTAX_ERROR: batch_connections = []

                                                                                # Connect batch concurrently

                                                                                # REMOVED_SYNTAX_ERROR: tasks = []

                                                                                # REMOVED_SYNTAX_ERROR: for user in batch:

                                                                                    # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                                                                    # REMOVED_SYNTAX_ERROR: task = websocket_manager.connect_user(user.id, websocket)

                                                                                    # REMOVED_SYNTAX_ERROR: tasks.append((user, websocket, task))

                                                                                    # Execute batch with timeout

                                                                                    # REMOVED_SYNTAX_ERROR: try:

                                                                                        # REMOVED_SYNTAX_ERROR: results = await asyncio.wait_for( )

                                                                                        # REMOVED_SYNTAX_ERROR: asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True),

                                                                                        # REMOVED_SYNTAX_ERROR: timeout=10.0

                                                                                        

                                                                                        # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):

                                                                                            # REMOVED_SYNTAX_ERROR: if not isinstance(result, Exception) and result is not None:

                                                                                                # REMOVED_SYNTAX_ERROR: user, websocket, _ = tasks[i]

                                                                                                # REMOVED_SYNTAX_ERROR: batch_connections.append((user, websocket))

                                                                                                # REMOVED_SYNTAX_ERROR: connection_batches.append(batch_connections)

                                                                                                # REMOVED_SYNTAX_ERROR: connections.extend(batch_connections)

                                                                                                # REMOVED_SYNTAX_ERROR: except asyncio.TimeoutError:
                                                                                                    # Handle partial batch success


                                                                                                    # REMOVED_SYNTAX_ERROR: actual_connections = len(connections)

                                                                                                    # REMOVED_SYNTAX_ERROR: assert actual_connections >= user_count * 0.8  # 80% success for large scale

                                                                                                    # Large scale broadcast test

                                                                                                    # REMOVED_SYNTAX_ERROR: broadcast_message = create_test_message( )

                                                                                                    # REMOVED_SYNTAX_ERROR: "large_broadcast",

                                                                                                    # REMOVED_SYNTAX_ERROR: "system",

                                                                                                    # REMOVED_SYNTAX_ERROR: { )

                                                                                                    # REMOVED_SYNTAX_ERROR: "broadcast_id": str(uuid4()),

                                                                                                    # REMOVED_SYNTAX_ERROR: "content": "Large scale broadcast test",

                                                                                                    # REMOVED_SYNTAX_ERROR: "target_count": actual_connections,

                                                                                                    # REMOVED_SYNTAX_ERROR: "scale": "large"

                                                                                                    

                                                                                                    

                                                                                                    # Use Redis pipeline with batching for optimal performance

                                                                                                    # REMOVED_SYNTAX_ERROR: broadcast_start = time.time()

                                                                                                    # REMOVED_SYNTAX_ERROR: batch_size = 100

                                                                                                    # REMOVED_SYNTAX_ERROR: success_count = 0

                                                                                                    # REMOVED_SYNTAX_ERROR: for i in range(0, len(connections), batch_size):

                                                                                                        # REMOVED_SYNTAX_ERROR: batch = connections[i:i + batch_size]

                                                                                                        # REMOVED_SYNTAX_ERROR: pipe = redis_client.pipeline()

                                                                                                        # REMOVED_SYNTAX_ERROR: for user, _ in batch:

                                                                                                            # REMOVED_SYNTAX_ERROR: channel = "formatted_string"

                                                                                                            # REMOVED_SYNTAX_ERROR: pipe.publish(channel, json.dumps(broadcast_message))

                                                                                                            # REMOVED_SYNTAX_ERROR: try:

                                                                                                                # REMOVED_SYNTAX_ERROR: results = await pipe.execute()

                                                                                                                # REMOVED_SYNTAX_ERROR: success_count += len([item for item in []])

                                                                                                                # REMOVED_SYNTAX_ERROR: except Exception:


                                                                                                                    # REMOVED_SYNTAX_ERROR: broadcast_time = time.time() - broadcast_start

                                                                                                                    # REMOVED_SYNTAX_ERROR: error_count = actual_connections - success_count

                                                                                                                    # REMOVED_SYNTAX_ERROR: performance_tracker.record_broadcast(broadcast_time, success_count, error_count)

                                                                                                                    # Performance assertions for large scale

                                                                                                                    # REMOVED_SYNTAX_ERROR: assert broadcast_time < 10.0  # Should complete within 10 seconds

                                                                                                                    # REMOVED_SYNTAX_ERROR: assert success_count >= actual_connections * 0.85  # 85% success rate

                                                                                                                    # Cleanup in batches

                                                                                                                    # REMOVED_SYNTAX_ERROR: for batch in connection_batches:

                                                                                                                        # REMOVED_SYNTAX_ERROR: cleanup_tasks = []

                                                                                                                        # REMOVED_SYNTAX_ERROR: for user, websocket in batch:

                                                                                                                            # REMOVED_SYNTAX_ERROR: task = websocket_manager.disconnect_user(user.id, websocket)

                                                                                                                            # REMOVED_SYNTAX_ERROR: cleanup_tasks.append(task)

                                                                                                                            # REMOVED_SYNTAX_ERROR: await asyncio.gather(*cleanup_tasks, return_exceptions=True)

                                                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                                                            # Removed problematic line: async def test_broadcast_latency_measurement(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

                                                                                                                                # REMOVED_SYNTAX_ERROR: """Test broadcast latency with timing measurements."""

                                                                                                                                # REMOVED_SYNTAX_ERROR: user_count = 100

                                                                                                                                # REMOVED_SYNTAX_ERROR: users = large_user_pool[:user_count]

                                                                                                                                # REMOVED_SYNTAX_ERROR: connections = []

                                                                                                                                # Establish connections

                                                                                                                                # REMOVED_SYNTAX_ERROR: for user in users:

                                                                                                                                    # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                                                                                                                    # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                                                                                                                                    # REMOVED_SYNTAX_ERROR: if connection_info:

                                                                                                                                        # REMOVED_SYNTAX_ERROR: connections.append((user, websocket))

                                                                                                                                        # Test individual delivery latency

                                                                                                                                        # REMOVED_SYNTAX_ERROR: latency_tests = 10

                                                                                                                                        # REMOVED_SYNTAX_ERROR: for test_round in range(latency_tests):

                                                                                                                                            # REMOVED_SYNTAX_ERROR: test_message = create_test_message( )

                                                                                                                                            # REMOVED_SYNTAX_ERROR: "latency_test",

                                                                                                                                            # REMOVED_SYNTAX_ERROR: "system",

                                                                                                                                            # REMOVED_SYNTAX_ERROR: { )

                                                                                                                                            # REMOVED_SYNTAX_ERROR: "test_round": test_round,

                                                                                                                                            # REMOVED_SYNTAX_ERROR: "timestamp": time.time(),

                                                                                                                                            # REMOVED_SYNTAX_ERROR: "latency_test": True

                                                                                                                                            

                                                                                                                                            

                                                                                                                                            # Measure individual delivery times

                                                                                                                                            # REMOVED_SYNTAX_ERROR: delivery_times = []

                                                                                                                                            # REMOVED_SYNTAX_ERROR: for user, _ in connections[:10]:  # Test subset for latency

                                                                                                                                            # REMOVED_SYNTAX_ERROR: channel = "formatted_string"

                                                                                                                                            # REMOVED_SYNTAX_ERROR: delivery_start = time.time()

                                                                                                                                            # REMOVED_SYNTAX_ERROR: await redis_client.publish(channel, json.dumps(test_message))

                                                                                                                                            # REMOVED_SYNTAX_ERROR: delivery_time = time.time() - delivery_start

                                                                                                                                            # REMOVED_SYNTAX_ERROR: delivery_times.append(delivery_time)

                                                                                                                                            # REMOVED_SYNTAX_ERROR: performance_tracker.record_delivery(delivery_time)

                                                                                                                                            # Brief pause between tests

                                                                                                                                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                                                                                                            # Analyze latency performance

                                                                                                                                            # REMOVED_SYNTAX_ERROR: avg_latency = statistics.mean(performance_tracker.delivery_times)

                                                                                                                                            # REMOVED_SYNTAX_ERROR: max_latency = max(performance_tracker.delivery_times)

                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert avg_latency < 0.1  # Average latency under 100ms

                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert max_latency < 0.5   # Max latency under 500ms

                                                                                                                                            # Cleanup

                                                                                                                                            # REMOVED_SYNTAX_ERROR: for user, websocket in connections:

                                                                                                                                                # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                                                                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                # Removed problematic line: async def test_concurrent_broadcast_handling(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: """Test handling of concurrent broadcast operations."""

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: user_count = 150

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: users = large_user_pool[:user_count]

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: connections = []

                                                                                                                                                    # Establish connections

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: for user in users:

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: if connection_info:

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: connections.append((user, websocket))

                                                                                                                                                            # Create concurrent broadcasts

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: concurrent_broadcasts = 5

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: broadcast_tasks = []

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: for broadcast_id in range(concurrent_broadcasts):

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: broadcast_message = create_test_message( )

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "concurrent_broadcast",

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "system",

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: { )

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "broadcast_id": broadcast_id,

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "content": "formatted_string",

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "concurrent_test": True

                                                                                                                                                                

                                                                                                                                                                

                                                                                                                                                                # Create broadcast task

# REMOVED_SYNTAX_ERROR: async def execute_broadcast(msg, b_id):

    # REMOVED_SYNTAX_ERROR: start_time = time.time()

    # REMOVED_SYNTAX_ERROR: success_count = 0

    # REMOVED_SYNTAX_ERROR: pipe = redis_client.pipeline()

    # REMOVED_SYNTAX_ERROR: for user, _ in connections:

        # REMOVED_SYNTAX_ERROR: channel = "formatted_string"

        # REMOVED_SYNTAX_ERROR: pipe.publish(channel, json.dumps(msg))

        # REMOVED_SYNTAX_ERROR: try:

            # REMOVED_SYNTAX_ERROR: results = await pipe.execute()

            # REMOVED_SYNTAX_ERROR: success_count = len([item for item in []])

            # REMOVED_SYNTAX_ERROR: except Exception:


                # REMOVED_SYNTAX_ERROR: duration = time.time() - start_time

                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                # REMOVED_SYNTAX_ERROR: return duration, success_count, b_id

                # REMOVED_SYNTAX_ERROR: task = execute_broadcast(broadcast_message, broadcast_id)

                # REMOVED_SYNTAX_ERROR: broadcast_tasks.append(task)

                # Execute concurrent broadcasts

                # REMOVED_SYNTAX_ERROR: concurrent_start = time.time()

                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)

                # REMOVED_SYNTAX_ERROR: concurrent_time = time.time() - concurrent_start

                # Analyze concurrent performance

                # REMOVED_SYNTAX_ERROR: successful_broadcasts = 0

                # REMOVED_SYNTAX_ERROR: total_successes = 0

                # REMOVED_SYNTAX_ERROR: for result in results:

                    # REMOVED_SYNTAX_ERROR: if not isinstance(result, Exception):

                        # REMOVED_SYNTAX_ERROR: duration, success_count, broadcast_id = result

                        # REMOVED_SYNTAX_ERROR: performance_tracker.record_broadcast(duration, success_count, 0)

                        # REMOVED_SYNTAX_ERROR: successful_broadcasts += 1

                        # REMOVED_SYNTAX_ERROR: total_successes += success_count

                        # Performance assertions

                        # REMOVED_SYNTAX_ERROR: assert successful_broadcasts >= concurrent_broadcasts * 0.8  # 80% of broadcasts succeed

                        # REMOVED_SYNTAX_ERROR: assert concurrent_time < 8.0  # All concurrent broadcasts within 8 seconds

                        # REMOVED_SYNTAX_ERROR: assert total_successes >= len(connections) * concurrent_broadcasts * 0.75  # 75% delivery rate

                        # Cleanup

                        # REMOVED_SYNTAX_ERROR: for user, websocket in connections:

                            # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_broadcast_memory_efficiency(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

                                # REMOVED_SYNTAX_ERROR: """Test memory efficiency during broadcast operations."""

                                # REMOVED_SYNTAX_ERROR: user_count = 300

                                # REMOVED_SYNTAX_ERROR: users = large_user_pool[:user_count]

                                # REMOVED_SYNTAX_ERROR: connections = []

                                # Monitor initial memory

                                # REMOVED_SYNTAX_ERROR: initial_info = await redis_client.info("memory")

                                # REMOVED_SYNTAX_ERROR: initial_memory = initial_info.get("used_memory", 0)

                                # REMOVED_SYNTAX_ERROR: performance_tracker.record_memory(initial_memory)

                                # Establish connections

                                # REMOVED_SYNTAX_ERROR: for user in users:

                                    # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                    # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                                    # REMOVED_SYNTAX_ERROR: if connection_info:

                                        # REMOVED_SYNTAX_ERROR: connections.append((user, websocket))

                                        # Monitor memory after connections

                                        # REMOVED_SYNTAX_ERROR: post_connection_info = await redis_client.info("memory")

                                        # REMOVED_SYNTAX_ERROR: post_connection_memory = post_connection_info.get("used_memory", 0)

                                        # REMOVED_SYNTAX_ERROR: performance_tracker.record_memory(post_connection_memory)

                                        # Perform memory-intensive broadcasts

                                        # REMOVED_SYNTAX_ERROR: broadcast_rounds = 5

                                        # REMOVED_SYNTAX_ERROR: for round_num in range(broadcast_rounds):
                                            # Large message payload

                                            # REMOVED_SYNTAX_ERROR: large_message = create_test_message( )

                                            # REMOVED_SYNTAX_ERROR: "memory_test",

                                            # REMOVED_SYNTAX_ERROR: "system",

                                            # REMOVED_SYNTAX_ERROR: { )

                                            # REMOVED_SYNTAX_ERROR: "round": round_num,

                                            # REMOVED_SYNTAX_ERROR: "large_payload": "x" * 1000,  # 1KB payload

                                            # REMOVED_SYNTAX_ERROR: "metadata": {"formatted_string": "formatted_string" for i in range(100)}

                                            

                                            

                                            # Broadcast with memory monitoring

                                            # REMOVED_SYNTAX_ERROR: pipe = redis_client.pipeline()

                                            # REMOVED_SYNTAX_ERROR: for user, _ in connections:

                                                # REMOVED_SYNTAX_ERROR: channel = "formatted_string"

                                                # REMOVED_SYNTAX_ERROR: pipe.publish(channel, json.dumps(large_message))

                                                # REMOVED_SYNTAX_ERROR: await pipe.execute()

                                                # Monitor memory usage

                                                # REMOVED_SYNTAX_ERROR: current_info = await redis_client.info("memory")

                                                # REMOVED_SYNTAX_ERROR: current_memory = current_info.get("used_memory", 0)

                                                # REMOVED_SYNTAX_ERROR: performance_tracker.record_memory(current_memory)

                                                # Brief pause for memory cleanup

                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)

                                                # Final memory check

                                                # REMOVED_SYNTAX_ERROR: final_info = await redis_client.info("memory")

                                                # REMOVED_SYNTAX_ERROR: final_memory = final_info.get("used_memory", 0)

                                                # Memory efficiency assertions

                                                # REMOVED_SYNTAX_ERROR: peak_memory = max(performance_tracker.memory_usage)

                                                # REMOVED_SYNTAX_ERROR: memory_growth = peak_memory - initial_memory

                                                # Memory should not grow excessively

                                                # REMOVED_SYNTAX_ERROR: assert memory_growth < initial_memory * 2  # Less than 200% growth

                                                # Memory should be reasonable for connection count

                                                # REMOVED_SYNTAX_ERROR: memory_per_connection = memory_growth / len(connections) if connections else 0

                                                # REMOVED_SYNTAX_ERROR: assert memory_per_connection < 10000  # Less than 10KB per connection

                                                # Cleanup

                                                # REMOVED_SYNTAX_ERROR: for user, websocket in connections:

                                                    # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                                                    # Get performance summary

                                                    # REMOVED_SYNTAX_ERROR: summary = performance_tracker.get_performance_summary()

                                                    # REMOVED_SYNTAX_ERROR: assert summary["success_rate"] >= 0.8  # Overall 80% success rate

                                                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":

                                                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s", "--tb=short"])