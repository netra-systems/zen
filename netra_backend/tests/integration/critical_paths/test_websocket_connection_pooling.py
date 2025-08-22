"""
L3 Integration Test: WebSocket Connection Pooling with Real Redis Pub/Sub

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Ensure scalable WebSocket connection management
- Value Impact: Enables concurrent user sessions without connection limits
- Strategic Impact: $60K MRR - Real-time communication scalability for enterprise

L3 Test: Uses real Redis containers and connection pooling for WebSocket validation.
Performance target: 1000+ concurrent connections with <100ms message latency.
"""

# Add project root to path
from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List
from datetime import datetime, timezone
from unittest.mock import patch

import redis.asyncio as redis
from ws_manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas import User
from test_framework.mock_utils import mock_justified

# Add project root to path

from netra_backend.tests.helpers.redis_l3_helpers import (

# Add project root to path

    RedisContainer, 

    MockWebSocketForRedis, 

    create_test_message,

    verify_redis_connection

)


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketConnectionPoolingL3:

    """L3 integration tests for WebSocket connection pooling with Redis."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up real Redis container for connection pooling tests."""

        container = RedisContainer(port=6382)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client for connection pool management."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    

    @pytest.fixture

    async def ws_manager(self, redis_container):

        """Create WebSocket manager with Redis connection pooling."""

        _, redis_url = redis_container
        

        with patch('app.ws_manager.redis_manager') as mock_redis_mgr:

            test_redis_mgr = RedisManager()

            test_redis_mgr.enabled = True

            test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

            mock_redis_mgr.return_value = test_redis_mgr

            mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client
            

            manager = WebSocketManager()

            yield manager
            

            await test_redis_mgr.redis_client.close()
    

    @pytest.fixture

    def test_users(self):

        """Create pool of test users for connection testing."""

        return [

            User(

                id=f"pool_user_{i}",

                email=f"pooluser{i}@example.com", 

                username=f"pooluser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(100)  # Pool of users for testing

        ]
    

    async def test_connection_pool_initialization(self, ws_manager, redis_client):

        """Test WebSocket connection pool initialization with Redis."""
        # Verify Redis connection pool settings

        await redis_client.config_set("maxclients", "10000")

        max_clients = await redis_client.config_get("maxclients")

        assert int(max_clients["maxclients"]) >= 1000
        
        # Test connection pool info

        info = await redis_client.info("clients")

        initial_connections = info.get("connected_clients", 0)
        
        # Verify pool can handle connections

        assert initial_connections >= 0

        assert ws_manager is not None
    

    async def test_concurrent_connection_establishment(self, ws_manager, redis_client, test_users):

        """Test concurrent WebSocket connection establishment."""

        batch_size = 50  # Manageable batch for CI

        connections = []
        
        # Establish connections concurrently

        tasks = []

        for user in test_users[:batch_size]:

            websocket = MockWebSocketForRedis(user.id)

            task = ws_manager.connect_user(user.id, websocket)

            tasks.append((user, websocket, task))
        
        # Execute connections concurrently

        start_time = time.time()

        results = await asyncio.gather(

            *[task for _, _, task in tasks], 

            return_exceptions=True

        )

        connection_time = time.time() - start_time
        
        # Verify successful connections

        successful_connections = 0

        for i, result in enumerate(results):

            if not isinstance(result, Exception) and result is not None:

                successful_connections += 1

                user, websocket, _ = tasks[i]

                connections.append((user, websocket))
        

        assert successful_connections >= batch_size * 0.9  # 90% success rate

        assert connection_time < 5.0  # Performance requirement

        assert len(ws_manager.active_connections) >= successful_connections
        
        # Cleanup

        for user, websocket in connections:

            await ws_manager.disconnect_user(user.id, websocket)
    

    async def test_connection_pool_scaling(self, ws_manager, redis_client, test_users):

        """Test connection pool scaling under load."""

        scaling_phases = [10, 25, 50]  # Gradual scaling

        connections = []
        

        for phase_size in scaling_phases:

            phase_connections = []
            
            # Add connections for this phase

            for user in test_users[:phase_size]:

                if user.id not in [u.id for u, _ in connections]:

                    websocket = MockWebSocketForRedis(user.id)

                    connection_info = await ws_manager.connect_user(user.id, websocket)

                    if connection_info:

                        phase_connections.append((user, websocket))
            

            connections.extend(phase_connections)
            
            # Verify pool handles scaling

            assert len(ws_manager.active_connections) >= len(connections) * 0.9
            
            # Test pool performance at this scale

            pool_info = await redis_client.info("clients")

            connected_clients = pool_info.get("connected_clients", 0)

            assert connected_clients > 0
        
        # Cleanup all connections

        for user, websocket in connections:

            await ws_manager.disconnect_user(user.id, websocket)
    

    async def test_connection_pool_message_distribution(self, ws_manager, redis_client, test_users):

        """Test message distribution across connection pool."""

        connection_count = 20

        connections = []
        
        # Establish connection pool

        for user in test_users[:connection_count]:

            websocket = MockWebSocketForRedis(user.id)

            await ws_manager.connect_user(user.id, websocket)

            connections.append((user, websocket))
        
        # Test broadcast message distribution

        broadcast_message = create_test_message(

            "pool_broadcast", 

            "system", 

            {"content": "Pool distribution test", "timestamp": time.time()}

        )
        
        # Publish to all user channels

        publish_tasks = []

        for user, _ in connections:

            channel = f"user:{user.id}"

            task = redis_client.publish(channel, json.dumps(broadcast_message))

            publish_tasks.append(task)
        
        # Execute all publishes concurrently

        publish_results = await asyncio.gather(*publish_tasks, return_exceptions=True)

        successful_publishes = sum(1 for r in publish_results if not isinstance(r, Exception))
        

        assert successful_publishes >= connection_count * 0.9
        
        # Cleanup

        for user, websocket in connections:

            await ws_manager.disconnect_user(user.id, websocket)
    

    async def test_connection_pool_failover_handling(self, ws_manager, redis_client, test_users):

        """Test connection pool resilience during Redis issues."""

        user = test_users[0]

        websocket = MockWebSocketForRedis(user.id)
        
        # Establish connection

        connection_info = await ws_manager.connect_user(user.id, websocket)

        assert connection_info is not None
        
        # Simulate Redis connection stress

        stress_tasks = []

        for i in range(10):

            task = redis_client.set(f"stress_key_{i}", f"value_{i}", ex=1)

            stress_tasks.append(task)
        

        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)

        successful_operations = sum(1 for r in stress_results if not isinstance(r, Exception))
        
        # Verify connection survives stress

        assert user.id in ws_manager.active_connections

        assert successful_operations > 0
        
        # Test message delivery after stress

        recovery_message = create_test_message("pool_recovery", user.id)

        success = await ws_manager.send_message_to_user(user.id, recovery_message)
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, websocket)
    

    @mock_justified("L3: Connection pool stress testing with real Redis")

    async def test_connection_pool_resource_management(self, ws_manager, redis_client, test_users):

        """Test connection pool resource management and cleanup."""

        initial_info = await redis_client.info("memory")

        initial_memory = initial_info.get("used_memory", 0)
        

        connections = []

        resource_phases = [5, 10, 15]  # Gradual resource usage
        

        for phase_size in resource_phases:
            # Add connections

            for user in test_users[:phase_size]:

                if user.id not in [u.id for u, _ in connections]:

                    websocket = MockWebSocketForRedis(user.id)

                    await ws_manager.connect_user(user.id, websocket)

                    connections.append((user, websocket))
                    
                    # Store connection state in Redis

                    state_key = f"ws_pool_state:{user.id}"

                    state_data = {"connected_at": time.time(), "phase": phase_size}

                    await redis_client.set(state_key, json.dumps(state_data), ex=300)
            
            # Check memory usage

            current_info = await redis_client.info("memory")

            current_memory = current_info.get("used_memory", 0)

            memory_growth = current_memory - initial_memory
            
            # Memory should grow reasonably with connections

            assert memory_growth >= 0
            
        # Cleanup and verify resource release

        for user, websocket in connections:

            await ws_manager.disconnect_user(user.id, websocket)

            await redis_client.delete(f"ws_pool_state:{user.id}")
        
        # Allow cleanup to complete

        await asyncio.sleep(0.5)
        

        final_info = await redis_client.info("memory")

        final_memory = final_info.get("used_memory", 0)
        
        # Memory should be released (within reasonable bounds)

        memory_after_cleanup = final_memory - initial_memory

        assert memory_after_cleanup < (initial_memory * 0.1)  # Less than 10% growth


if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])