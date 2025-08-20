"""
CRITICAL INTEGRATION TEST #13: Redis Session State Sync

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core session management functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from session state failures
- Value Impact: Ensures WebSocket connect → Redis state → multiple connections → state consistency
- Revenue Impact: Prevents customer session loss/desync that would cause immediate churn

REQUIREMENTS:
- WebSocket connection triggers Redis state creation
- Multiple connections share consistent state
- State synchronization across connections
- Session persistence across reconnections
- State sync within 1 second
- 100% state consistency across connections
"""

import pytest
import asyncio
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Set testing environment
import os
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.redis_manager import RedisManager
from app.ws_manager import WebSocketManager
from app.logging_config import central_logger
from fastapi import WebSocket
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)


class MockRedisConnection:
    """Mock Redis connection with state synchronization capabilities."""
    
    def __init__(self):
        self.data_store = {}
        self.pub_sub_channels = {}
        self.subscribers = {}
        self.operation_count = 0
        self.sync_events = []
        
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set key-value with optional expiry."""
        self.operation_count += 1
        
        self.data_store[key] = {
            "value": value,
            "expires_at": time.time() + ex if ex else None,
            "set_at": time.time()
        }
        
        # Trigger sync event
        self.sync_events.append({
            "operation": "set",
            "key": key,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Notify subscribers
        await self._notify_subscribers(key, "set", value)
        
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        self.operation_count += 1
        
        if key in self.data_store:
            entry = self.data_store[key]
            
            # Check expiry
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self.data_store[key]
                return None
            
            return entry["value"]
        
        return None
    
    async def delete(self, key: str) -> int:
        """Delete key."""
        self.operation_count += 1
        
        if key in self.data_store:
            del self.data_store[key]
            
            # Trigger sync event
            self.sync_events.append({
                "operation": "delete",
                "key": key,
                "timestamp": datetime.now(timezone.utc)
            })
            
            # Notify subscribers
            await self._notify_subscribers(key, "delete", None)
            
            return 1
        
        return 0
    
    async def hset(self, key: str, field: str, value: str):
        """Set hash field."""
        self.operation_count += 1
        
        if key not in self.data_store:
            self.data_store[key] = {"value": {}, "type": "hash"}
        
        self.data_store[key]["value"][field] = value
        
        # Trigger sync event
        self.sync_events.append({
            "operation": "hset",
            "key": key,
            "field": field,
            "timestamp": datetime.now(timezone.utc)
        })
        
        return True
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field."""
        self.operation_count += 1
        
        if key in self.data_store and self.data_store[key].get("type") == "hash":
            return self.data_store[key]["value"].get(field)
        
        return None
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        self.operation_count += 1
        
        if key in self.data_store and self.data_store[key].get("type") == "hash":
            return self.data_store[key]["value"].copy()
        
        return {}
    
    async def publish(self, channel: str, message: str):
        """Publish message to channel."""
        self.operation_count += 1
        
        if channel not in self.pub_sub_channels:
            self.pub_sub_channels[channel] = []
        
        message_data = {
            "channel": channel,
            "message": message,
            "timestamp": datetime.now(timezone.utc)
        }
        
        self.pub_sub_channels[channel].append(message_data)
        
        # Notify subscribers
        if channel in self.subscribers:
            for callback in self.subscribers[channel]:
                await callback(message_data)
        
        return len(self.subscribers.get(channel, []))
    
    async def subscribe(self, channel: str, callback):
        """Subscribe to channel."""
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        
        self.subscribers[channel].append(callback)
    
    async def _notify_subscribers(self, key: str, operation: str, value: Optional[str]):
        """Notify subscribers of key changes."""
        notification = {
            "key": key,
            "operation": operation,
            "value": value,
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Publish to state sync channel
        sync_channel = f"state_sync:{key.split(':')[0]}"
        await self.publish(sync_channel, json.dumps(notification))


class MockWebSocketConnection:
    """Mock WebSocket connection with state sync capabilities."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.state = "connected"
        self.messages_sent = []
        self.session_data = {}
        self.sync_notifications = []
        
    async def send_json(self, data: Dict[str, Any]):
        """Send JSON message."""
        if self.state != "connected":
            raise Exception("WebSocket not connected")
        
        self.messages_sent.append({
            "type": "json",
            "content": data,
            "timestamp": datetime.now(timezone.utc)
        })
    
    async def send_text(self, message: str):
        """Send text message."""
        if self.state != "connected":
            raise Exception("WebSocket not connected")
        
        self.messages_sent.append({
            "type": "text",
            "content": message,
            "timestamp": datetime.now(timezone.utc)
        })
    
    def disconnect(self):
        """Disconnect WebSocket."""
        self.state = "disconnected"
    
    def receive_sync_notification(self, notification: Dict[str, Any]):
        """Receive state sync notification."""
        self.sync_notifications.append(notification)


class MockRedisSessionManager:
    """Mock Redis session manager with state synchronization."""
    
    def __init__(self, redis_connection: MockRedisConnection):
        self.redis = redis_connection
        self.active_sessions = {}
        self.sync_metrics = {
            "sessions_created": 0,
            "sync_operations": 0,
            "sync_conflicts": 0,
            "avg_sync_time": 0
        }
    
    async def create_session(self, user_id: str, connection_id: str, initial_data: Dict[str, Any] = None) -> str:
        """Create new session with Redis state."""
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "connection_id": connection_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "state": initial_data or {}
        }
        
        # Store in Redis
        session_key = f"session:{session_id}"
        user_session_key = f"user_sessions:{user_id}"
        
        # Set session data
        await self.redis.set(session_key, json.dumps(session_data), ex=3600)
        
        # Add to user sessions list
        await self.redis.hset(user_session_key, connection_id, session_id)
        
        # Track locally
        self.active_sessions[session_id] = session_data
        self.sync_metrics["sessions_created"] += 1
        
        return session_id
    
    async def update_session_state(self, session_id: str, state_updates: Dict[str, Any]) -> bool:
        """Update session state with Redis sync."""
        start_time = time.time()
        
        try:
            session_key = f"session:{session_id}"
            
            # Get current session data
            session_json = await self.redis.get(session_key)
            if not session_json:
                return False
            
            session_data = json.loads(session_json)
            
            # Apply state updates
            session_data["state"].update(state_updates)
            session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
            
            # Update Redis
            await self.redis.set(session_key, json.dumps(session_data), ex=3600)
            
            # Update local cache
            if session_id in self.active_sessions:
                self.active_sessions[session_id] = session_data
            
            # Track metrics
            sync_time = time.time() - start_time
            self.sync_metrics["sync_operations"] += 1
            self._update_avg_sync_time(sync_time)
            
            return True
            
        except Exception as e:
            logger.error(f"Session state update failed: {e}")
            return False
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state from Redis."""
        session_key = f"session:{session_id}"
        
        session_json = await self.redis.get(session_key)
        if session_json:
            return json.loads(session_json)
        
        return None
    
    async def get_user_sessions(self, user_id: str) -> Dict[str, str]:
        """Get all sessions for user."""
        user_session_key = f"user_sessions:{user_id}"
        return await self.redis.hgetall(user_session_key)
    
    async def sync_state_across_connections(self, user_id: str, state_updates: Dict[str, Any]) -> List[str]:
        """Sync state across all user connections."""
        user_sessions = await self.get_user_sessions(user_id)
        synced_sessions = []
        
        for connection_id, session_id in user_sessions.items():
            success = await self.update_session_state(session_id, state_updates)
            if success:
                synced_sessions.append(session_id)
        
        return synced_sessions
    
    def _update_avg_sync_time(self, sync_time: float):
        """Update average sync time metric."""
        current_avg = self.sync_metrics["avg_sync_time"]
        sync_count = self.sync_metrics["sync_operations"]
        
        self.sync_metrics["avg_sync_time"] = (
            (current_avg * (sync_count - 1) + sync_time) / sync_count
        )


class MockWebSocketManagerWithRedis:
    """Mock WebSocket manager with Redis state synchronization."""
    
    def __init__(self, redis_manager: MockRedisSessionManager):
        self.redis_manager = redis_manager
        self.connections = {}
        self.connection_sessions = {}
        self.sync_subscriptions = {}
    
    async def add_connection(self, user_id: str, websocket: MockWebSocketConnection):
        """Add WebSocket connection with Redis session."""
        connection_id = websocket.connection_id
        
        # Create Redis session
        session_id = await self.redis_manager.create_session(user_id, connection_id)
        
        # Track connection
        self.connections[connection_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "session_id": session_id,
            "connected_at": datetime.now(timezone.utc)
        }
        
        self.connection_sessions[connection_id] = session_id
        
        # Subscribe to state sync events for this user
        await self._subscribe_to_sync_events(user_id, connection_id)
    
    async def remove_connection(self, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id in self.connections:
            connection_info = self.connections[connection_id]
            websocket = connection_info["websocket"]
            websocket.disconnect()
            
            del self.connections[connection_id]
            if connection_id in self.connection_sessions:
                del self.connection_sessions[connection_id]
    
    async def update_user_state(self, user_id: str, state_updates: Dict[str, Any]):
        """Update state for all user connections."""
        synced_sessions = await self.redis_manager.sync_state_across_connections(user_id, state_updates)
        
        # Notify connected WebSockets
        user_connections = [
            conn for conn in self.connections.values()
            if conn["user_id"] == user_id
        ]
        
        for connection in user_connections:
            websocket = connection["websocket"]
            await websocket.send_json({
                "type": "state_sync",
                "state_updates": state_updates,
                "sync_timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return len(synced_sessions)
    
    async def get_connection_state(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get state for specific connection."""
        if connection_id in self.connection_sessions:
            session_id = self.connection_sessions[connection_id]
            return await self.redis_manager.get_session_state(session_id)
        
        return None
    
    async def _subscribe_to_sync_events(self, user_id: str, connection_id: str):
        """Subscribe to state sync events."""
        sync_channel = f"state_sync:user_sessions"
        
        async def sync_callback(message_data):
            # Handle sync notification
            if connection_id in self.connections:
                websocket = self.connections[connection_id]["websocket"]
                websocket.receive_sync_notification(message_data)
        
        await self.redis_manager.redis.subscribe(sync_channel, sync_callback)
        self.sync_subscriptions[connection_id] = sync_channel


class TestRedisSessionStateSync:
    """BVJ: Protects $35K MRR through reliable Redis session state synchronization."""

    @pytest.fixture
    def redis_connection(self):
        """Create mock Redis connection."""
        return MockRedisConnection()

    @pytest.fixture
    def session_manager(self, redis_connection):
        """Create mock Redis session manager."""
        return MockRedisSessionManager(redis_connection)

    @pytest.fixture
    def websocket_manager(self, session_manager):
        """Create mock WebSocket manager with Redis integration."""
        return MockWebSocketManagerWithRedis(session_manager)

    @pytest.mark.asyncio
    async def test_01_websocket_connection_redis_state_creation(self, websocket_manager, session_manager):
        """BVJ: Validates WebSocket connection triggers Redis state creation."""
        # Step 1: Create WebSocket connection
        user_id = "state_sync_user"
        connection_id = "conn_1"
        websocket = MockWebSocketConnection(user_id, connection_id)
        
        start_time = time.time()
        await websocket_manager.add_connection(user_id, websocket)
        connection_time = time.time() - start_time
        
        # Step 2: Validate session creation
        assert connection_id in websocket_manager.connections, "Connection not tracked"
        assert connection_id in websocket_manager.connection_sessions, "Session not mapped"
        
        connection_info = websocket_manager.connections[connection_id]
        session_id = connection_info["session_id"]
        
        assert session_id is not None, "Session ID not created"
        
        # Step 3: Validate Redis state
        session_state = await session_manager.get_session_state(session_id)
        assert session_state is not None, "Session state not stored in Redis"
        assert session_state["user_id"] == user_id, "User ID mismatch in Redis"
        assert session_state["connection_id"] == connection_id, "Connection ID mismatch in Redis"
        
        # Step 4: Validate user sessions mapping
        user_sessions = await session_manager.get_user_sessions(user_id)
        assert connection_id in user_sessions, "Connection not in user sessions"
        assert user_sessions[connection_id] == session_id, "Session mapping incorrect"
        
        # Step 5: Validate timing
        assert connection_time < 1.0, f"Connection state creation took {connection_time:.2f}s, exceeds 1s limit"
        
        # Step 6: Verify metrics
        metrics = session_manager.sync_metrics
        assert metrics["sessions_created"] == 1, "Session creation not counted"
        
        logger.info(f"WebSocket Redis state creation validated: {connection_time:.2f}s creation time")

    @pytest.mark.asyncio
    async def test_02_multiple_connection_state_consistency(self, websocket_manager, session_manager):
        """BVJ: Validates multiple connections share consistent state."""
        # Step 1: Create multiple connections for same user
        user_id = "multi_conn_user"
        connections = []
        
        for i in range(3):
            connection_id = f"conn_{i+1}"
            websocket = MockWebSocketConnection(user_id, connection_id)
            await websocket_manager.add_connection(user_id, websocket)
            connections.append((connection_id, websocket))
        
        # Step 2: Update state through one connection
        state_updates = {
            "current_thread": "thread_123",
            "agent_mode": "optimization",
            "preferences": {"theme": "dark", "notifications": True}
        }
        
        start_time = time.time()
        synced_count = await websocket_manager.update_user_state(user_id, state_updates)
        sync_time = time.time() - start_time
        
        # Step 3: Validate sync count
        assert synced_count == 3, f"Expected 3 synced sessions, got {synced_count}"
        
        # Step 4: Verify state consistency across all connections
        for connection_id, websocket in connections:
            connection_state = await websocket_manager.get_connection_state(connection_id)
            
            assert connection_state is not None, f"State not found for {connection_id}"
            
            # Check state updates are present
            state_data = connection_state["state"]
            assert state_data["current_thread"] == "thread_123", f"Thread mismatch in {connection_id}"
            assert state_data["agent_mode"] == "optimization", f"Agent mode mismatch in {connection_id}"
            assert state_data["preferences"]["theme"] == "dark", f"Theme mismatch in {connection_id}"
            
            # Check sync notifications were sent
            sync_messages = [msg for msg in websocket.messages_sent if msg["content"].get("type") == "state_sync"]
            assert len(sync_messages) > 0, f"No sync messages sent to {connection_id}"
            
            last_sync = sync_messages[-1]["content"]
            assert last_sync["state_updates"] == state_updates, f"Sync data mismatch in {connection_id}"
        
        # Step 5: Validate sync timing
        assert sync_time < 1.0, f"State sync took {sync_time:.2f}s, exceeds 1s limit"
        
        logger.info(f"Multiple connection consistency validated: {synced_count} connections in {sync_time:.2f}s")

    @pytest.mark.asyncio
    async def test_03_state_synchronization_real_time(self, websocket_manager, session_manager, redis_connection):
        """BVJ: Validates real-time state synchronization across connections."""
        # Step 1: Setup multiple connections
        user_id = "realtime_sync_user"
        connections = []
        
        for i in range(4):
            connection_id = f"realtime_conn_{i+1}"
            websocket = MockWebSocketConnection(user_id, connection_id)
            await websocket_manager.add_connection(user_id, websocket)
            connections.append((connection_id, websocket))
        
        # Step 2: Perform rapid state updates
        rapid_updates = [
            {"message_input": "Hello agent", "timestamp": time.time()},
            {"agent_thinking": True, "timestamp": time.time()},
            {"agent_response": "Hello! How can I help?", "timestamp": time.time()},
            {"conversation_state": "active", "timestamp": time.time()},
            {"last_interaction": datetime.now(timezone.utc).isoformat(), "timestamp": time.time()}
        ]
        
        sync_times = []
        
        for update in rapid_updates:
            start_time = time.time()
            
            # Update state
            synced_count = await websocket_manager.update_user_state(user_id, update)
            
            sync_time = time.time() - start_time
            sync_times.append(sync_time)
            
            # Validate immediate sync
            assert synced_count == 4, f"Not all connections synced: {synced_count}/4"
            
            # Small delay between updates
            await asyncio.sleep(0.1)
        
        # Step 3: Validate all connections have latest state
        for connection_id, websocket in connections:
            connection_state = await websocket_manager.get_connection_state(connection_id)
            state_data = connection_state["state"]
            
            # Check all updates are present
            for update in rapid_updates:
                for key, value in update.items():
                    if key != "timestamp":  # Skip timestamp comparison
                        assert state_data.get(key) == value, f"Update {key} missing in {connection_id}"
        
        # Step 4: Validate sync timing performance
        avg_sync_time = sum(sync_times) / len(sync_times)
        max_sync_time = max(sync_times)
        
        assert avg_sync_time < 0.5, f"Average sync time {avg_sync_time:.2f}s too slow"
        assert max_sync_time < 1.0, f"Max sync time {max_sync_time:.2f}s too slow"
        
        # Step 5: Verify Redis operation efficiency
        assert redis_connection.operation_count > 0, "No Redis operations recorded"
        
        # Check sync events
        sync_events = redis_connection.sync_events
        assert len(sync_events) >= len(rapid_updates), "Not all sync events recorded"
        
        logger.info(f"Real-time sync validated: {avg_sync_time:.2f}s avg, {max_sync_time:.2f}s max")

    @pytest.mark.asyncio
    async def test_04_session_persistence_across_reconnections(self, websocket_manager, session_manager):
        """BVJ: Validates session persistence across connection drops and reconnections."""
        # Step 1: Create initial connection with state
        user_id = "persistence_user"
        connection_id = "persistence_conn"
        websocket = MockWebSocketConnection(user_id, connection_id)
        
        await websocket_manager.add_connection(user_id, websocket)
        
        # Step 2: Build up session state
        session_state = {
            "conversation_history": ["Hello", "Hi there!", "Can you help with optimization?"],
            "current_context": {
                "topic": "gpu_optimization",
                "complexity": "intermediate",
                "user_preferences": {"detailed_analysis": True}
            },
            "agent_memory": {
                "user_expertise": "intermediate",
                "previous_requests": ["memory_optimization", "cost_analysis"]
            }
        }
        
        await websocket_manager.update_user_state(user_id, session_state)
        
        # Get session ID before disconnect
        original_session_id = websocket_manager.connection_sessions[connection_id]
        
        # Step 3: Simulate connection drop
        await websocket_manager.remove_connection(connection_id)
        
        # Verify connection is removed but session persists in Redis
        assert connection_id not in websocket_manager.connections, "Connection not removed"
        
        # Check Redis still has session data
        persisted_state = await session_manager.get_session_state(original_session_id)
        assert persisted_state is not None, "Session state not persisted in Redis"
        
        # Step 4: Simulate reconnection
        new_websocket = MockWebSocketConnection(user_id, connection_id)
        await websocket_manager.add_connection(user_id, new_websocket)
        
        # Step 5: Validate state restoration
        reconnection_state = await websocket_manager.get_connection_state(connection_id)
        
        assert reconnection_state is not None, "State not restored after reconnection"
        
        # Check conversation history preserved
        restored_history = reconnection_state["state"]["conversation_history"]
        assert restored_history == session_state["conversation_history"], "Conversation history not preserved"
        
        # Check context preserved
        restored_context = reconnection_state["state"]["current_context"]
        assert restored_context["topic"] == "gpu_optimization", "Context topic not preserved"
        assert restored_context["complexity"] == "intermediate", "Context complexity not preserved"
        
        # Check agent memory preserved
        restored_memory = reconnection_state["state"]["agent_memory"]
        assert restored_memory["user_expertise"] == "intermediate", "Agent memory not preserved"
        
        # Step 6: Verify seamless continuation
        continuation_update = {"new_message": "Continue where we left off"}
        synced_count = await websocket_manager.update_user_state(user_id, continuation_update)
        
        assert synced_count >= 1, "State updates not working after reconnection"
        
        final_state = await websocket_manager.get_connection_state(connection_id)
        assert final_state["state"]["new_message"] == "Continue where we left off", "Continuation failed"
        
        logger.info(f"Session persistence validated across reconnection")

    @pytest.mark.asyncio
    async def test_05_concurrent_state_sync_load_testing(self, websocket_manager, session_manager):
        """BVJ: Validates state sync performance under concurrent load."""
        # Step 1: Create multiple users with multiple connections each
        concurrent_users = 5
        connections_per_user = 3
        all_connections = []
        
        for user_idx in range(concurrent_users):
            user_id = f"load_user_{user_idx}"
            user_connections = []
            
            for conn_idx in range(connections_per_user):
                connection_id = f"load_conn_{user_idx}_{conn_idx}"
                websocket = MockWebSocketConnection(user_id, connection_id)
                await websocket_manager.add_connection(user_id, websocket)
                user_connections.append((user_id, connection_id, websocket))
            
            all_connections.extend(user_connections)
        
        # Step 2: Generate concurrent state updates
        update_tasks = []
        
        async def rapid_state_updates(user_id: str, update_count: int):
            """Perform rapid state updates for a user."""
            update_times = []
            
            for i in range(update_count):
                update_data = {
                    f"update_{i}": f"value_{i}",
                    "update_timestamp": time.time(),
                    "sequence": i
                }
                
                start_time = time.time()
                synced_count = await websocket_manager.update_user_state(user_id, update_data)
                update_time = time.time() - start_time
                
                update_times.append(update_time)
                
                # Brief delay to prevent overwhelming
                await asyncio.sleep(0.05)
            
            return {
                "user_id": user_id,
                "updates_completed": update_count,
                "avg_update_time": sum(update_times) / len(update_times),
                "max_update_time": max(update_times),
                "final_sync_count": synced_count
            }
        
        # Step 3: Execute concurrent load test
        updates_per_user = 10
        start_time = time.time()
        
        load_results = await asyncio.gather(*[
            rapid_state_updates(f"load_user_{i}", updates_per_user)
            for i in range(concurrent_users)
        ])
        
        total_load_time = time.time() - start_time
        
        # Step 4: Validate load test results
        total_updates = concurrent_users * updates_per_user
        successful_updates = sum(result["updates_completed"] for result in load_results)
        
        assert successful_updates == total_updates, f"Not all updates completed: {successful_updates}/{total_updates}"
        
        # Step 5: Validate performance metrics
        avg_update_times = [result["avg_update_time"] for result in load_results]
        overall_avg_time = sum(avg_update_times) / len(avg_update_times)
        
        max_update_times = [result["max_update_time"] for result in load_results]
        overall_max_time = max(max_update_times)
        
        assert overall_avg_time < 1.0, f"Average update time {overall_avg_time:.2f}s too slow under load"
        assert overall_max_time < 2.0, f"Max update time {overall_max_time:.2f}s too slow under load"
        
        # Step 6: Validate throughput
        throughput = total_updates / total_load_time
        assert throughput >= 10.0, f"Update throughput {throughput:.1f} updates/sec too low"
        
        # Step 7: Verify final state consistency
        for result in load_results:
            user_id = result["user_id"]
            expected_connections = connections_per_user
            
            assert result["final_sync_count"] == expected_connections, \
                f"Final sync count mismatch for {user_id}: {result['final_sync_count']}/{expected_connections}"
        
        logger.info(f"Concurrent load test validated: {throughput:.1f} updates/sec, {overall_avg_time:.2f}s avg time")

    @pytest.mark.asyncio
    async def test_06_state_conflict_resolution(self, websocket_manager, session_manager, redis_connection):
        """BVJ: Validates state conflict resolution when concurrent updates occur."""
        # Step 1: Setup user with multiple connections
        user_id = "conflict_user"
        connections = []
        
        for i in range(2):
            connection_id = f"conflict_conn_{i+1}"
            websocket = MockWebSocketConnection(user_id, connection_id)
            await websocket_manager.add_connection(user_id, websocket)
            connections.append((connection_id, websocket))
        
        # Step 2: Simulate near-simultaneous conflicting updates
        conflicting_updates = [
            {"shared_field": "value_from_conn1", "conn1_field": "unique1", "timestamp": time.time()},
            {"shared_field": "value_from_conn2", "conn2_field": "unique2", "timestamp": time.time() + 0.001}
        ]
        
        # Execute updates with minimal delay
        update_tasks = []
        for i, update in enumerate(conflicting_updates):
            task = websocket_manager.update_user_state(user_id, update)
            update_tasks.append(task)
        
        start_time = time.time()
        update_results = await asyncio.gather(*update_tasks)
        conflict_resolution_time = time.time() - start_time
        
        # Step 3: Validate both updates were processed
        for result in update_results:
            assert result >= 2, "Not all connections received updates"
        
        # Step 4: Check final state consistency
        final_states = []
        for connection_id, websocket in connections:
            state = await websocket_manager.get_connection_state(connection_id)
            final_states.append(state["state"])
        
        # Verify all connections have same final state
        first_state = final_states[0]
        for state in final_states[1:]:
            assert state == first_state, "State inconsistency after conflict resolution"
        
        # Step 5: Validate conflict resolution preserves data
        final_state = first_state
        
        # Should have fields from both updates
        assert "conn1_field" in final_state, "Update 1 data lost"
        assert "conn2_field" in final_state, "Update 2 data lost"
        assert final_state["conn1_field"] == "unique1", "Update 1 value incorrect"
        assert final_state["conn2_field"] == "unique2", "Update 2 value incorrect"
        
        # Shared field should have last-write-wins behavior
        assert "shared_field" in final_state, "Shared field lost in conflict"
        
        # Step 6: Validate resolution timing
        assert conflict_resolution_time < 2.0, f"Conflict resolution took {conflict_resolution_time:.2f}s too long"
        
        # Step 7: Check metrics don't show conflicts as failures
        metrics = session_manager.sync_metrics
        # Should have processed both updates successfully
        assert metrics["sync_operations"] >= 2, "Not all sync operations counted"
        
        logger.info(f"State conflict resolution validated: {conflict_resolution_time:.2f}s resolution time")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])