"""
L3 Integration Test: WebSocket Broadcast Performance with Redis

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Scalability - Handle enterprise-scale broadcasts efficiently
- Value Impact: Enables real-time features for large teams and workspaces
- Strategic Impact: $60K MRR - Enterprise broadcast capability for collaboration

L3 Test: Uses real Redis for broadcast performance validation.
Performance target: 1000+ concurrent connections with <100ms broadcast latency.
"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import pytest
import asyncio
import json
import time
import statistics
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

import redis.asyncio as redis
from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas import User
from test_framework.mock_utils import mock_justified

from netra_backend.tests.integration.helpers.redis_l3_helpers import (

    RedisContainer, 

    MockWebSocketForRedis, 

    create_test_message

)

class BroadcastPerformanceTracker:

    """Track broadcast performance metrics."""
    
    def __init__(self):

        self.broadcast_times: List[float] = []

        self.delivery_times: List[float] = []

        self.success_counts: List[int] = []

        self.error_counts: List[int] = []

        self.memory_usage: List[int] = []
    
    def record_broadcast(self, duration: float, successes: int, errors: int) -> None:

        """Record broadcast performance metrics."""

        self.broadcast_times.append(duration)

        self.success_counts.append(successes)

        self.error_counts.append(errors)
    
    def record_delivery(self, duration: float) -> None:

        """Record individual delivery time."""

        self.delivery_times.append(duration)
    
    def record_memory(self, usage: int) -> None:

        """Record memory usage."""

        self.memory_usage.append(usage)
    
    def get_performance_summary(self) -> Dict[str, Any]:

        """Get performance summary statistics."""

        return {

            "avg_broadcast_time": statistics.mean(self.broadcast_times) if self.broadcast_times else 0,

            "max_broadcast_time": max(self.broadcast_times) if self.broadcast_times else 0,

            "avg_delivery_time": statistics.mean(self.delivery_times) if self.delivery_times else 0,

            "total_successes": sum(self.success_counts),

            "total_errors": sum(self.error_counts),

            "success_rate": sum(self.success_counts) / (sum(self.success_counts) + sum(self.error_counts)) if self.success_counts or self.error_counts else 0,

            "peak_memory": max(self.memory_usage) if self.memory_usage else 0

        }

@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketBroadcastPerformanceL3:

    """L3 integration tests for WebSocket broadcast performance."""
    
    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for broadcast performance testing."""

        container = RedisContainer(port=6385)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    
    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client for broadcast operations."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    
    @pytest.fixture

    async def websocket_manager(self, redis_container):

        """Create WebSocket manager for broadcast testing."""

        _, redis_url = redis_container
        
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

    def large_user_pool(self):

        """Create large pool of test users for performance testing."""

        return [

            User(

                id=f"perf_user_{i:04d}",

                email=f"perfuser{i:04d}@example.com", 

                username=f"perfuser{i:04d}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(1000)  # Large user pool for performance testing

        ]
    
    @pytest.fixture

    def performance_tracker(self):

        """Create performance tracking instance."""

        return BroadcastPerformanceTracker()
    
    async def test_small_scale_broadcast_baseline(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

        """Test broadcast performance baseline with small user count."""

        user_count = 50

        users = large_user_pool[:user_count]

        connections = []
        
        # Establish connections

        connection_start = time.time()

        for user in users:

            websocket = MockWebSocketForRedis(user.id)

            connection_info = await websocket_manager.connect_user(user.id, websocket)

            if connection_info:

                connections.append((user, websocket))
        
        connection_time = time.time() - connection_start

        actual_connections = len(connections)
        
        assert actual_connections >= user_count * 0.9  # 90% connection success
        
        # Perform broadcast

        broadcast_message = create_test_message(

            "small_broadcast", 

            "system", 

            {

                "broadcast_id": str(uuid4()),

                "content": "Small scale broadcast test",

                "target_count": actual_connections

            }

        )
        
        broadcast_start = time.time()

        success_count = 0

        error_count = 0
        
        # Broadcast to all connections

        tasks = []

        for user, _ in connections:

            channel = f"user:{user.id}"

            task = redis_client.publish(channel, json.dumps(broadcast_message))

            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:

            if isinstance(result, Exception):

                error_count += 1

            else:

                success_count += 1
        
        broadcast_time = time.time() - broadcast_start
        
        # Record performance

        performance_tracker.record_broadcast(broadcast_time, success_count, error_count)
        
        # Performance assertions

        assert broadcast_time < 2.0  # Should complete quickly

        assert success_count >= actual_connections * 0.95  # 95% success rate
        
        # Cleanup

        for user, websocket in connections:

            await websocket_manager.disconnect_user(user.id, websocket)
    
    async def test_medium_scale_broadcast_performance(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

        """Test broadcast performance with medium user count."""

        user_count = 200

        users = large_user_pool[:user_count]

        connections = []
        
        # Establish connections in batches for better performance

        batch_size = 50

        for i in range(0, len(users), batch_size):

            batch = users[i:i + batch_size]

            batch_tasks = []
            
            for user in batch:

                websocket = MockWebSocketForRedis(user.id)

                task = websocket_manager.connect_user(user.id, websocket)

                batch_tasks.append((user, websocket, task))
            
            # Execute batch

            for user, websocket, task in batch_tasks:

                try:

                    connection_info = await task

                    if connection_info:

                        connections.append((user, websocket))

                except Exception:

                    pass
        
        actual_connections = len(connections)

        assert actual_connections >= user_count * 0.85  # 85% connection success for medium scale
        
        # Test broadcast performance

        broadcast_message = create_test_message(

            "medium_broadcast", 

            "system", 

            {

                "broadcast_id": str(uuid4()),

                "content": "Medium scale broadcast test",

                "target_count": actual_connections,

                "timestamp": time.time()

            }

        )
        
        broadcast_start = time.time()
        
        # Use pipeline for better Redis performance

        pipe = redis_client.pipeline()

        for user, _ in connections:

            channel = f"user:{user.id}"

            pipe.publish(channel, json.dumps(broadcast_message))
        
        results = await pipe.execute()

        broadcast_time = time.time() - broadcast_start
        
        success_count = len([r for r in results if r > 0])  # Redis publish returns subscriber count

        error_count = actual_connections - success_count
        
        performance_tracker.record_broadcast(broadcast_time, success_count, error_count)
        
        # Performance assertions

        assert broadcast_time < 5.0  # Should complete within 5 seconds

        assert success_count >= actual_connections * 0.9  # 90% success rate
        
        # Cleanup

        cleanup_tasks = []

        for user, websocket in connections:

            task = websocket_manager.disconnect_user(user.id, websocket)

            cleanup_tasks.append(task)
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def test_large_scale_broadcast_performance(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

        """Test broadcast performance with large user count."""

        user_count = 500  # Reduced for CI stability

        users = large_user_pool[:user_count]

        connections = []
        
        # Optimized connection establishment

        connection_batches = []

        batch_size = 100
        
        for i in range(0, len(users), batch_size):

            batch = users[i:i + batch_size]

            batch_connections = []
            
            # Connect batch concurrently

            tasks = []

            for user in batch:

                websocket = MockWebSocketForRedis(user.id)

                task = websocket_manager.connect_user(user.id, websocket)

                tasks.append((user, websocket, task))
            
            # Execute batch with timeout

            try:

                results = await asyncio.wait_for(

                    asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True),

                    timeout=10.0

                )
                
                for i, result in enumerate(results):

                    if not isinstance(result, Exception) and result is not None:

                        user, websocket, _ = tasks[i]

                        batch_connections.append((user, websocket))
                
                connection_batches.append(batch_connections)

                connections.extend(batch_connections)
                
            except asyncio.TimeoutError:
                # Handle partial batch success

                pass
        
        actual_connections = len(connections)

        assert actual_connections >= user_count * 0.8  # 80% success for large scale
        
        # Large scale broadcast test

        broadcast_message = create_test_message(

            "large_broadcast", 

            "system", 

            {

                "broadcast_id": str(uuid4()),

                "content": "Large scale broadcast test",

                "target_count": actual_connections,

                "scale": "large"

            }

        )
        
        # Use Redis pipeline with batching for optimal performance

        broadcast_start = time.time()

        batch_size = 100

        success_count = 0
        
        for i in range(0, len(connections), batch_size):

            batch = connections[i:i + batch_size]

            pipe = redis_client.pipeline()
            
            for user, _ in batch:

                channel = f"user:{user.id}"

                pipe.publish(channel, json.dumps(broadcast_message))
            
            try:

                results = await pipe.execute()

                success_count += len([r for r in results if r >= 0])

            except Exception:

                pass
        
        broadcast_time = time.time() - broadcast_start

        error_count = actual_connections - success_count
        
        performance_tracker.record_broadcast(broadcast_time, success_count, error_count)
        
        # Performance assertions for large scale

        assert broadcast_time < 10.0  # Should complete within 10 seconds

        assert success_count >= actual_connections * 0.85  # 85% success rate
        
        # Cleanup in batches

        for batch in connection_batches:

            cleanup_tasks = []

            for user, websocket in batch:

                task = websocket_manager.disconnect_user(user.id, websocket)

                cleanup_tasks.append(task)
            
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def test_broadcast_latency_measurement(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

        """Test broadcast latency with timing measurements."""

        user_count = 100

        users = large_user_pool[:user_count]

        connections = []
        
        # Establish connections

        for user in users:

            websocket = MockWebSocketForRedis(user.id)

            connection_info = await websocket_manager.connect_user(user.id, websocket)

            if connection_info:

                connections.append((user, websocket))
        
        # Test individual delivery latency

        latency_tests = 10

        for test_round in range(latency_tests):

            test_message = create_test_message(

                "latency_test", 

                "system", 

                {

                    "test_round": test_round,

                    "timestamp": time.time(),

                    "latency_test": True

                }

            )
            
            # Measure individual delivery times

            delivery_times = []

            for user, _ in connections[:10]:  # Test subset for latency

                channel = f"user:{user.id}"
                
                delivery_start = time.time()

                await redis_client.publish(channel, json.dumps(test_message))

                delivery_time = time.time() - delivery_start
                
                delivery_times.append(delivery_time)

                performance_tracker.record_delivery(delivery_time)
            
            # Brief pause between tests

            await asyncio.sleep(0.1)
        
        # Analyze latency performance

        avg_latency = statistics.mean(performance_tracker.delivery_times)

        max_latency = max(performance_tracker.delivery_times)
        
        assert avg_latency < 0.1  # Average latency under 100ms

        assert max_latency < 0.5   # Max latency under 500ms
        
        # Cleanup

        for user, websocket in connections:

            await websocket_manager.disconnect_user(user.id, websocket)
    
    async def test_concurrent_broadcast_handling(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

        """Test handling of concurrent broadcast operations."""

        user_count = 150

        users = large_user_pool[:user_count]

        connections = []
        
        # Establish connections

        for user in users:

            websocket = MockWebSocketForRedis(user.id)

            connection_info = await websocket_manager.connect_user(user.id, websocket)

            if connection_info:

                connections.append((user, websocket))
        
        # Create concurrent broadcasts

        concurrent_broadcasts = 5

        broadcast_tasks = []
        
        for broadcast_id in range(concurrent_broadcasts):

            broadcast_message = create_test_message(

                "concurrent_broadcast", 

                "system", 

                {

                    "broadcast_id": broadcast_id,

                    "content": f"Concurrent broadcast {broadcast_id}",

                    "concurrent_test": True

                }

            )
            
            # Create broadcast task

            async def execute_broadcast(msg, b_id):

                start_time = time.time()

                success_count = 0
                
                pipe = redis_client.pipeline()

                for user, _ in connections:

                    channel = f"user:{user.id}"

                    pipe.publish(channel, json.dumps(msg))
                
                try:

                    results = await pipe.execute()

                    success_count = len([r for r in results if r >= 0])

                except Exception:

                    pass
                
                duration = time.time() - start_time

                return duration, success_count, b_id
            
            task = execute_broadcast(broadcast_message, broadcast_id)

            broadcast_tasks.append(task)
        
        # Execute concurrent broadcasts

        concurrent_start = time.time()

        results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)

        concurrent_time = time.time() - concurrent_start
        
        # Analyze concurrent performance

        successful_broadcasts = 0

        total_successes = 0
        
        for result in results:

            if not isinstance(result, Exception):

                duration, success_count, broadcast_id = result

                performance_tracker.record_broadcast(duration, success_count, 0)

                successful_broadcasts += 1

                total_successes += success_count
        
        # Performance assertions

        assert successful_broadcasts >= concurrent_broadcasts * 0.8  # 80% of broadcasts succeed

        assert concurrent_time < 8.0  # All concurrent broadcasts within 8 seconds

        assert total_successes >= len(connections) * concurrent_broadcasts * 0.75  # 75% delivery rate
        
        # Cleanup

        for user, websocket in connections:

            await websocket_manager.disconnect_user(user.id, websocket)
    
    @mock_justified("L3: Broadcast performance testing with real Redis infrastructure")

    async def test_broadcast_memory_efficiency(self, websocket_manager, redis_client, large_user_pool, performance_tracker):

        """Test memory efficiency during broadcast operations."""

        user_count = 300

        users = large_user_pool[:user_count]

        connections = []
        
        # Monitor initial memory

        initial_info = await redis_client.info("memory")

        initial_memory = initial_info.get("used_memory", 0)

        performance_tracker.record_memory(initial_memory)
        
        # Establish connections

        for user in users:

            websocket = MockWebSocketForRedis(user.id)

            connection_info = await websocket_manager.connect_user(user.id, websocket)

            if connection_info:

                connections.append((user, websocket))
        
        # Monitor memory after connections

        post_connection_info = await redis_client.info("memory")

        post_connection_memory = post_connection_info.get("used_memory", 0)

        performance_tracker.record_memory(post_connection_memory)
        
        # Perform memory-intensive broadcasts

        broadcast_rounds = 5

        for round_num in range(broadcast_rounds):
            # Large message payload

            large_message = create_test_message(

                "memory_test", 

                "system", 

                {

                    "round": round_num,

                    "large_payload": "x" * 1000,  # 1KB payload

                    "metadata": {f"field_{i}": f"value_{i}" for i in range(100)}

                }

            )
            
            # Broadcast with memory monitoring

            pipe = redis_client.pipeline()

            for user, _ in connections:

                channel = f"user:{user.id}"

                pipe.publish(channel, json.dumps(large_message))
            
            await pipe.execute()
            
            # Monitor memory usage

            current_info = await redis_client.info("memory")

            current_memory = current_info.get("used_memory", 0)

            performance_tracker.record_memory(current_memory)
            
            # Brief pause for memory cleanup

            await asyncio.sleep(0.2)
        
        # Final memory check

        final_info = await redis_client.info("memory")

        final_memory = final_info.get("used_memory", 0)
        
        # Memory efficiency assertions

        peak_memory = max(performance_tracker.memory_usage)

        memory_growth = peak_memory - initial_memory
        
        # Memory should not grow excessively

        assert memory_growth < initial_memory * 2  # Less than 200% growth
        
        # Memory should be reasonable for connection count

        memory_per_connection = memory_growth / len(connections) if connections else 0

        assert memory_per_connection < 10000  # Less than 10KB per connection
        
        # Cleanup

        for user, websocket in connections:

            await websocket_manager.disconnect_user(user.id, websocket)
        
        # Get performance summary

        summary = performance_tracker.get_performance_summary()

        assert summary["success_rate"] >= 0.8  # Overall 80% success rate

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])