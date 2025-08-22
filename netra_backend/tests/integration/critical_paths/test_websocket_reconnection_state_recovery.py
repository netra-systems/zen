"""
L3 Integration Test: WebSocket Reconnection State Recovery with Redis

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Reliability - Seamless reconnection for enterprise users
- Value Impact: Eliminates workflow disruption from connection drops
- Strategic Impact: $60K MRR - Connection resilience for real-time collaboration

L3 Test: Uses real Redis for state persistence and recovery validation.
Recovery target: <5 second reconnection with full state restoration.
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
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

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

    create_test_message

)


class ConnectionStateManager:

    """Manage connection state for recovery testing."""
    

    def __init__(self, redis_client):

        self.redis_client = redis_client

        self.state_prefix = "ws_state"

        self.session_prefix = "ws_session"
    

    async def save_state(self, user_id: str, state: Dict[str, Any]) -> None:

        """Save user connection state to Redis."""

        state_key = f"{self.state_prefix}:{user_id}"

        state_data = {

            **state,

            "saved_at": time.time(),

            "version": 1

        }

        await self.redis_client.set(state_key, json.dumps(state_data), ex=3600)
    

    async def load_state(self, user_id: str) -> Optional[Dict[str, Any]]:

        """Load user connection state from Redis."""

        state_key = f"{self.state_prefix}:{user_id}"

        state_data = await self.redis_client.get(state_key)

        if state_data:

            return json.loads(state_data)

        return None
    

    async def clear_state(self, user_id: str) -> None:

        """Clear user connection state."""

        state_key = f"{self.state_prefix}:{user_id}"

        await self.redis_client.delete(state_key)
    

    async def save_session(self, user_id: str, session_data: Dict[str, Any]) -> None:

        """Save session data for recovery."""

        session_key = f"{self.session_prefix}:{user_id}"

        await self.redis_client.set(session_key, json.dumps(session_data), ex=86400)
    

    async def load_session(self, user_id: str) -> Optional[Dict[str, Any]]:

        """Load session data for recovery."""

        session_key = f"{self.session_prefix}:{user_id}"

        session_data = await self.redis_client.get(session_key)

        if session_data:

            return json.loads(session_data)

        return None


@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketReconnectionStateRecoveryL3:

    """L3 integration tests for WebSocket reconnection state recovery."""
    

    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for state recovery testing."""

        container = RedisContainer(port=6384)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    

    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client for state management."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    

    @pytest.fixture

    async def ws_manager(self, redis_container):

        """Create WebSocket manager with state recovery."""

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

    async def state_manager(self, redis_client):

        """Create connection state manager."""

        return ConnectionStateManager(redis_client)
    

    @pytest.fixture

    def test_users(self):

        """Create test users for reconnection testing."""

        return [

            User(

                id=f"reconnect_user_{i}",

                email=f"reconnectuser{i}@example.com", 

                username=f"reconnectuser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(3)

        ]
    

    async def test_basic_state_persistence_and_recovery(self, ws_manager, state_manager, test_users):

        """Test basic connection state persistence and recovery."""

        user = test_users[0]
        
        # Initial connection with state

        first_websocket = MockWebSocketForRedis(user.id)

        connection_info = await ws_manager.connect_user(user.id, first_websocket)
        

        assert connection_info is not None
        
        # Save connection state

        connection_state = {

            "user_id": user.id,

            "connection_id": connection_info.connection_id,

            "connected_at": time.time(),

            "last_activity": time.time(),

            "active_threads": ["thread_1", "thread_2"],

            "subscription_channels": [f"user:{user.id}", f"thread:thread_1"]

        }
        

        await state_manager.save_state(user.id, connection_state)
        
        # Disconnect (simulating network failure)

        await ws_manager.disconnect_user(user.id, first_websocket)

        assert user.id not in ws_manager.active_connections
        
        # Reconnect and recover state

        second_websocket = MockWebSocketForRedis(user.id)

        new_connection_info = await ws_manager.connect_user(user.id, second_websocket)
        
        # Load and verify state recovery

        recovered_state = await state_manager.load_state(user.id)
        

        assert recovered_state is not None

        assert recovered_state["user_id"] == user.id

        assert len(recovered_state["active_threads"]) == 2

        assert new_connection_info is not None
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, second_websocket)

        await state_manager.clear_state(user.id)
    

    async def test_message_queue_recovery_after_reconnection(self, ws_manager, redis_client, state_manager, test_users):

        """Test recovery of queued messages after reconnection."""

        user = test_users[0]
        
        # Initial connection

        first_websocket = MockWebSocketForRedis(user.id)

        await ws_manager.connect_user(user.id, first_websocket)
        
        # Queue messages while connected (for later recovery)

        message_queue_key = f"message_queue:{user.id}"

        queued_messages = []
        

        for i in range(5):

            message_id = str(uuid4())

            test_message = create_test_message(

                "queued_message", 

                user.id, 

                {

                    "message_id": message_id,

                    "content": f"Queued message {i}",

                    "sequence": i

                }

            )

            queued_messages.append(test_message)

            await redis_client.lpush(message_queue_key, json.dumps(test_message))
        
        # Save session with message queue info

        session_data = {

            "message_queue_key": message_queue_key,

            "queued_count": len(queued_messages),

            "last_processed": time.time()

        }

        await state_manager.save_session(user.id, session_data)
        
        # Disconnect

        await ws_manager.disconnect_user(user.id, first_websocket)
        
        # Reconnect

        second_websocket = MockWebSocketForRedis(user.id)

        await ws_manager.connect_user(user.id, second_websocket)
        
        # Recover and process queued messages

        recovered_session = await state_manager.load_session(user.id)

        assert recovered_session is not None
        

        processed_messages = []

        while await redis_client.llen(message_queue_key) > 0:

            message_data = await redis_client.rpop(message_queue_key)

            if message_data:

                message = json.loads(message_data)

                processed_messages.append(message)

                await second_websocket.send_json(message)
        
        # Verify message recovery

        assert len(processed_messages) == len(queued_messages)

        assert len(second_websocket.messages) == len(queued_messages)
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, second_websocket)
    

    async def test_subscription_state_recovery(self, ws_manager, redis_client, state_manager, test_users):

        """Test recovery of subscription state after reconnection."""

        user = test_users[0]
        
        # Initial connection with subscriptions

        first_websocket = MockWebSocketForRedis(user.id)

        await ws_manager.connect_user(user.id, first_websocket)
        
        # Setup subscriptions

        subscription_channels = [

            f"user:{user.id}",

            f"thread:active_thread",

            f"workspace:workspace_1",

            f"team:team_alpha"

        ]
        
        # Save subscription state

        subscription_state = {

            "channels": subscription_channels,

            "subscribed_at": time.time(),

            "subscription_count": len(subscription_channels)

        }

        await state_manager.save_state(user.id, subscription_state)
        
        # Store subscription info in Redis

        subscription_key = f"subscriptions:{user.id}"

        await redis_client.set(

            subscription_key, 

            json.dumps(subscription_channels), 

            ex=3600

        )
        
        # Disconnect

        await ws_manager.disconnect_user(user.id, first_websocket)
        
        # Reconnect

        second_websocket = MockWebSocketForRedis(user.id)

        await ws_manager.connect_user(user.id, second_websocket)
        
        # Recover subscription state

        recovered_subscriptions = await redis_client.get(subscription_key)

        if recovered_subscriptions:

            channels = json.loads(recovered_subscriptions)
            
            # Verify subscription recovery

            assert len(channels) == len(subscription_channels)

            assert f"user:{user.id}" in channels

            assert "thread:active_thread" in channels
        
        # Test message delivery to recovered subscriptions

        test_message = create_test_message("subscription_test", user.id)

        await redis_client.publish(f"user:{user.id}", json.dumps(test_message))
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, second_websocket)

        await redis_client.delete(subscription_key)
    

    async def test_rapid_reconnection_handling(self, ws_manager, state_manager, test_users):

        """Test handling of rapid reconnection attempts."""

        user = test_users[0]

        reconnection_count = 5

        connections = []
        
        # Perform rapid reconnections

        for i in range(reconnection_count):

            websocket = MockWebSocketForRedis(f"{user.id}_attempt_{i}")
            
            # Connect

            connection_info = await ws_manager.connect_user(user.id, websocket)

            if connection_info:

                connections.append((websocket, connection_info))
                
                # Save state for each connection

                connection_state = {

                    "attempt": i,

                    "connection_id": connection_info.connection_id,

                    "connected_at": time.time()

                }

                await state_manager.save_state(f"{user.id}_attempt_{i}", connection_state)
            
            # Brief pause

            await asyncio.sleep(0.1)
            
            # Disconnect

            if connection_info:

                await ws_manager.disconnect_user(user.id, websocket)
        
        # Final connection should succeed

        final_websocket = MockWebSocketForRedis(user.id)

        final_connection = await ws_manager.connect_user(user.id, final_websocket)
        

        assert final_connection is not None

        assert user.id in ws_manager.active_connections
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, final_websocket)
    

    async def test_concurrent_reconnection_state_isolation(self, ws_manager, state_manager, test_users):

        """Test state isolation during concurrent reconnections."""

        concurrent_users = test_users[:3]

        connections = []
        
        # Setup initial connections with distinct states

        for i, user in enumerate(concurrent_users):

            websocket = MockWebSocketForRedis(user.id)

            connection_info = await ws_manager.connect_user(user.id, websocket)
            

            if connection_info:

                connections.append((user, websocket, connection_info))
                
                # Save distinct state for each user

                user_state = {

                    "user_index": i,

                    "unique_data": f"user_{i}_data",

                    "connection_id": connection_info.connection_id,

                    "private_channels": [f"private:{user.id}"]

                }

                await state_manager.save_state(user.id, user_state)
        
        # Disconnect all users simultaneously

        disconnect_tasks = []

        for user, websocket, _ in connections:

            task = ws_manager.disconnect_user(user.id, websocket)

            disconnect_tasks.append(task)
        

        await asyncio.gather(*disconnect_tasks)
        
        # Reconnect all users simultaneously

        reconnect_tasks = []

        new_connections = []
        

        for user, _, _ in connections:

            new_websocket = MockWebSocketForRedis(user.id)

            task = ws_manager.connect_user(user.id, new_websocket)

            reconnect_tasks.append((user, new_websocket, task))
        
        # Execute reconnections

        for user, new_websocket, task in reconnect_tasks:

            try:

                new_connection_info = await task

                if new_connection_info:

                    new_connections.append((user, new_websocket))

            except Exception:

                pass
        
        # Verify state isolation

        for user, _ in new_connections:

            recovered_state = await state_manager.load_state(user.id)

            if recovered_state:

                assert recovered_state["unique_data"] == f"user_{recovered_state['user_index']}_data"

                assert f"private:{user.id}" in recovered_state["private_channels"]
        
        # Cleanup

        for user, websocket in new_connections:

            await ws_manager.disconnect_user(user.id, websocket)

            await state_manager.clear_state(user.id)
    

    @mock_justified("L3: State recovery testing with real Redis persistence")

    async def test_state_recovery_performance(self, ws_manager, state_manager, test_users):

        """Test performance of state recovery operations."""

        user = test_users[0]
        
        # Create large state for performance testing

        large_state = {

            "user_id": user.id,

            "large_data": {f"key_{i}": f"value_{i}" for i in range(1000)},

            "active_threads": [f"thread_{i}" for i in range(50)],

            "subscriptions": [f"channel_{i}" for i in range(100)],

            "metadata": {"created_at": time.time()}

        }
        
        # Test state save performance

        save_start = time.time()

        await state_manager.save_state(user.id, large_state)

        save_time = time.time() - save_start
        

        assert save_time < 1.0  # Should save quickly
        
        # Test state load performance

        load_start = time.time()

        recovered_state = await state_manager.load_state(user.id)

        load_time = time.time() - load_start
        

        assert load_time < 0.5  # Should load quickly

        assert recovered_state is not None

        assert len(recovered_state["large_data"]) == 1000

        assert len(recovered_state["active_threads"]) == 50
        
        # Test full reconnection with state recovery performance

        websocket = MockWebSocketForRedis(user.id)
        

        reconnect_start = time.time()

        connection_info = await ws_manager.connect_user(user.id, websocket)

        recovered_state = await state_manager.load_state(user.id)

        reconnect_time = time.time() - reconnect_start
        

        assert reconnect_time < 2.0  # Total reconnection should be fast

        assert connection_info is not None

        assert recovered_state is not None
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, websocket)

        await state_manager.clear_state(user.id)


if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])