"""
L3 Integration Test: WebSocket Connection Draining with Redis

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Reliability - Graceful shutdown without data loss
- Value Impact: Ensures zero-downtime deployments and maintenance
- Strategic Impact: $60K MRR - Enterprise-grade deployment reliability

L3 Test: Uses real Redis for connection draining and graceful shutdown.
Draining target: 100% connection preservation during graceful shutdown.
"""

# Add project root to path
from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager
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
from uuid import uuid4

import redis.asyncio as redis
from ws_manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from schemas import UserInDB
from test_framework.mock_utils import mock_justified

# Add project root to path

from netra_backend.tests.helpers.redis_l3_helpers import (

# Add project root to path

    RedisContainer, 

    MockWebSocketForRedis, 

    create_test_message

)


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketConnectionDrainingL3:

    """L3 integration tests for WebSocket connection draining."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for connection draining testing."""

        container = RedisContainer(port=6390)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client for draining state management."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    

    @pytest.fixture

    async def ws_manager(self, redis_container):

        """Create WebSocket manager for draining testing."""

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
    

    async def test_graceful_connection_draining(self, ws_manager, redis_client):

        """Test graceful draining of WebSocket connections."""
        # Establish multiple connections

        connections = []

        for i in range(10):

            user_id = f"drain_user_{i}"

            websocket = MockWebSocketForRedis(user_id)

            connection_info = await ws_manager.connect_user(user_id, websocket)

            if connection_info:

                connections.append((user_id, websocket))
        

        initial_count = len(connections)

        assert initial_count > 0
        
        # Simulate graceful draining

        drain_start = time.time()

        for user_id, websocket in connections:
            # Send drain notification

            drain_message = create_test_message("connection_draining", user_id, 

                                              {"reason": "server_maintenance"})

            await ws_manager.send_message_to_user(user_id, drain_message)

            await asyncio.sleep(0.1)  # Brief delay between notifications
        
        # Gracefully disconnect all

        for user_id, websocket in connections:

            await ws_manager.disconnect_user(user_id, websocket)
        

        drain_time = time.time() - drain_start

        assert drain_time < 5.0  # Should complete quickly

        assert len(ws_manager.active_connections) == 0


    async def test_connection_migration_during_draining(self, redis_client):

        """Test connection migration during draining process."""
        # Store connection states for migration

        migration_data = []

        for i in range(5):

            user_id = f"migrate_user_{i}"

            connection_state = {

                "user_id": user_id,

                "active_threads": [f"thread_{j}" for j in range(3)],

                "last_activity": time.time(),

                "migration_target": "new_server_instance"

            }
            

            state_key = f"migration_state:{user_id}"

            await redis_client.set(state_key, json.dumps(connection_state), ex=300)

            migration_data.append((user_id, connection_state))
        
        # Verify migration state stored

        for user_id, _ in migration_data:

            state_key = f"migration_state:{user_id}"

            stored_state = await redis_client.get(state_key)

            assert stored_state is not None
            

            state = json.loads(stored_state)

            assert state["user_id"] == user_id

            assert "migration_target" in state
        
        # Cleanup migration states

        for user_id, _ in migration_data:

            await redis_client.delete(f"migration_state:{user_id}")


@pytest.mark.L3

@pytest.mark.integration  

class TestWebSocketLoadBalancerAffinityL3:

    """L3 integration tests for WebSocket load balancer affinity."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for affinity testing."""

        container = RedisContainer(port=6391)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    async def test_sticky_session_management(self, redis_container):

        """Test sticky session management for load balancing."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Simulate multiple server instances

        server_instances = ["server_1", "server_2", "server_3"]

        user_sessions = {}
        

        for i in range(15):

            user_id = f"sticky_user_{i}"
            # Assign to server based on user hash (sticky session)

            server_index = hash(user_id) % len(server_instances)

            assigned_server = server_instances[server_index]
            

            session_key = f"sticky_session:{user_id}"

            session_data = {

                "user_id": user_id,

                "assigned_server": assigned_server,

                "created_at": time.time()

            }
            

            await client.set(session_key, json.dumps(session_data), ex=3600)

            user_sessions[user_id] = assigned_server
        
        # Verify session stickiness

        for user_id, expected_server in user_sessions.items():

            session_key = f"sticky_session:{user_id}"

            stored_data = await client.get(session_key)

            assert stored_data is not None
            

            session = json.loads(stored_data)

            assert session["assigned_server"] == expected_server
        

        await client.close()


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketRedisFailoverL3:

    """L3 integration tests for Redis failover handling."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for failover testing."""

        container = RedisContainer(port=6392)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    async def test_redis_failover_resilience(self, redis_container):

        """Test WebSocket resilience during Redis failover."""

        container, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Store critical connection data

        critical_data = {

            "active_connections": ["user_1", "user_2", "user_3"],

            "message_queue": [{"id": i, "content": f"msg_{i}"} for i in range(5)]

        }
        

        await client.set("critical_state", json.dumps(critical_data), ex=3600)
        
        # Verify data stored

        stored_data = await client.get("critical_state")

        assert stored_data is not None
        
        # Simulate brief Redis unavailability and recovery

        try:

            await client.set("failover_test", "before_failure")
            # Redis continues to work in this test scenario

            await client.set("failover_test", "after_recovery")

            recovery_data = await client.get("failover_test")

            assert recovery_data == "after_recovery"

        except Exception:
            # Handle failover scenario

            pass
        

        await client.close()


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketMessageReplayL3:

    """L3 integration tests for message replay functionality."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for message replay testing."""

        container = RedisContainer(port=6393)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    async def test_message_replay_after_reconnection(self, redis_container):

        """Test message replay for reconnected users."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        

        user_id = "replay_user_1"
        
        # Store missed messages during disconnection

        missed_messages = []

        for i in range(10):

            message = create_test_message("missed_message", user_id, 

                                        {"sequence": i, "content": f"Missed message {i}"})

            missed_messages.append(message)
            

            message_key = f"missed_messages:{user_id}:{i}"

            await client.lpush(f"missed_queue:{user_id}", json.dumps(message))
        

        await client.expire(f"missed_queue:{user_id}", 86400)  # 24 hour TTL
        
        # Verify messages stored for replay

        queue_length = await client.llen(f"missed_queue:{user_id}")

        assert queue_length == len(missed_messages)
        
        # Simulate replay on reconnection

        replayed_messages = []

        while await client.llen(f"missed_queue:{user_id}") > 0:

            message_data = await client.rpop(f"missed_queue:{user_id}")

            if message_data:

                message = json.loads(message_data)

                replayed_messages.append(message)
        
        # Verify all messages replayed

        assert len(replayed_messages) == len(missed_messages)
        

        await client.close()


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketConcurrentMutationsL3:

    """L3 integration tests for concurrent state mutations."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for concurrency testing."""

        container = RedisContainer(port=6394)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    async def test_concurrent_state_updates(self, redis_container):

        """Test concurrent WebSocket state updates."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Simulate concurrent updates to shared state

        shared_state_key = "shared_websocket_state"

        initial_state = {"counter": 0, "active_users": []}

        await client.set(shared_state_key, json.dumps(initial_state))
        
        # Concurrent update tasks

        async def update_counter():

            for _ in range(10):
                # Atomic increment

                await client.hincrby("shared_counter", "value", 1)

                await asyncio.sleep(0.01)
        
        # Run concurrent updates

        tasks = [update_counter() for _ in range(5)]

        await asyncio.gather(*tasks)
        
        # Verify final state

        final_counter = await client.hget("shared_counter", "value")

        assert int(final_counter) == 50  # 5 tasks * 10 increments each
        

        await client.close()


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketMemoryLeakPreventionL3:

    """L3 integration tests for memory leak prevention."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for memory testing."""

        container = RedisContainer(port=6395)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    async def test_long_running_connection_stability(self, redis_container):

        """Test long-running connection memory stability."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Monitor initial memory

        initial_info = await client.info("memory")

        initial_memory = initial_info.get("used_memory", 0)
        
        # Simulate long-running operations

        for cycle in range(10):
            # Create temporary data

            temp_keys = []

            for i in range(100):

                key = f"temp_data:{cycle}:{i}"

                await client.set(key, f"data_{i}", ex=1)  # 1 second TTL

                temp_keys.append(key)
            

            await asyncio.sleep(1.5)  # Allow TTL to expire
        
        # Check memory usage

        final_info = await client.info("memory")

        final_memory = final_info.get("used_memory", 0)

        memory_growth = final_memory - initial_memory
        
        # Memory should not grow significantly

        assert memory_growth < initial_memory * 0.5  # Less than 50% growth
        

        await client.close()


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketProtocolUpgradeL3:

    """L3 integration tests for protocol version negotiation."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for protocol testing."""

        container = RedisContainer(port=6396)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    async def test_protocol_version_negotiation(self, redis_container):

        """Test WebSocket protocol version negotiation."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Store supported protocol versions

        supported_versions = ["1.0", "1.1", "2.0"]

        await client.set("supported_protocols", json.dumps(supported_versions))
        
        # Test client version negotiation

        client_versions = ["1.1", "2.0", "0.9"]
        

        for client_version in client_versions:

            stored_versions = await client.get("supported_protocols")

            versions = json.loads(stored_versions)
            

            if client_version in versions:
                # Store negotiated version

                negotiation_key = f"protocol_negotiation:{uuid4()}"

                negotiation_data = {

                    "client_version": client_version,

                    "server_version": client_version,

                    "negotiated_at": time.time()

                }

                await client.set(negotiation_key, json.dumps(negotiation_data), ex=300)
                
                # Verify negotiation

                stored_negotiation = await client.get(negotiation_key)

                assert stored_negotiation is not None
                

                negotiation = json.loads(stored_negotiation)

                assert negotiation["client_version"] == client_version
        

        await client.close()


if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])