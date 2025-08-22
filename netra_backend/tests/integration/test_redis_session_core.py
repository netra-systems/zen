"""
Redis Session State Core Tests

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) - Core session management functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from session state failures
- Value Impact: Ensures WebSocket connect → Redis state → multiple connections → state consistency
- Revenue Impact: Prevents customer session loss/desync that would cause immediate churn

Core Redis session state synchronization tests.
"""

# Add project root to path

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio

# Add project root to path
# Set testing environment
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

import pytest


os.environ["TESTING"] = "1"

os.environ["ENVIRONMENT"] = "testing"

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from logging_config import central_logger

from tests.redis_session_mocks import (

    MockRedisConnection,

    MockRedisSessionManager,

    MockWebSocketConnection,

    MockWebSocketManagerWithRedis,

)


logger = central_logger.get_logger(__name__)


class TestRedisSessionStateCore:

    """Core Redis session state synchronization tests."""


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

    async def test_websocket_connection_redis_state_creation(self, websocket_manager, session_manager):

        """BVJ: Validates WebSocket connection triggers Redis state creation."""

        user_id = "state_sync_user"

        connection_id = "conn_1"

        websocket = MockWebSocketConnection(user_id, connection_id)
        

        start_time = time.time()

        await websocket_manager.add_connection(user_id, websocket)

        connection_time = time.time() - start_time
        

        assert connection_id in websocket_manager.connections, "Connection not tracked"

        assert connection_id in websocket_manager.connection_sessions, "Session not mapped"
        

        connection_info = websocket_manager.connections[connection_id]

        session_id = connection_info["session_id"]
        

        assert session_id is not None, "Session ID not created"
        

        session_state = await session_manager.get_session_state(session_id)

        assert session_state is not None, "Session state not stored in Redis"

        assert session_state["user_id"] == user_id, "User ID mismatch in Redis"

        assert session_state["connection_id"] == connection_id, "Connection ID mismatch in Redis"
        

        user_sessions = await session_manager.get_user_sessions(user_id)

        assert connection_id in user_sessions, "Connection not in user sessions"

        assert user_sessions[connection_id] == session_id, "Session mapping incorrect"
        

        assert connection_time < 1.0, f"Connection state creation took {connection_time:.2f}s, exceeds 1s limit"
        

        metrics = session_manager.sync_metrics

        assert metrics["sessions_created"] == 1, "Session creation not counted"
        

        logger.info(f"WebSocket Redis state creation validated: {connection_time:.2f}s creation time")


    @pytest.mark.asyncio

    async def test_multiple_connection_state_consistency(self, websocket_manager, session_manager):

        """BVJ: Validates multiple connections share consistent state."""

        user_id = "multi_conn_user"

        connections = []
        

        for i in range(3):

            connection_id = f"conn_{i+1}"

            websocket = MockWebSocketConnection(user_id, connection_id)

            await websocket_manager.add_connection(user_id, websocket)

            connections.append((connection_id, websocket))
        

        state_updates = {"current_thread": "thread_123", "agent_mode": "optimization", "preferences": {"theme": "dark", "notifications": True}}
        

        start_time = time.time()

        synced_count = await websocket_manager.update_user_state(user_id, state_updates)

        sync_time = time.time() - start_time
        

        assert synced_count == 3, f"Expected 3 synced sessions, got {synced_count}"
        

        for connection_id, websocket in connections:

            connection_state = await websocket_manager.get_connection_state(connection_id)
            

            assert connection_state is not None, f"State not found for {connection_id}"
            

            state_data = connection_state["state"]

            assert state_data["current_thread"] == "thread_123", f"Thread mismatch in {connection_id}"

            assert state_data["agent_mode"] == "optimization", f"Agent mode mismatch in {connection_id}"

            assert state_data["preferences"]["theme"] == "dark", f"Theme mismatch in {connection_id}"
            

            sync_messages = [msg for msg in websocket.messages_sent if msg["content"].get("type") == "state_sync"]

            assert len(sync_messages) > 0, f"No sync messages sent to {connection_id}"
            

            last_sync = sync_messages[-1]["content"]

            assert last_sync["state_updates"] == state_updates, f"Sync data mismatch in {connection_id}"
        

        assert sync_time < 1.0, f"State sync took {sync_time:.2f}s, exceeds 1s limit"
        

        logger.info(f"Multiple connection consistency validated: {synced_count} connections in {sync_time:.2f}s")


    @pytest.mark.asyncio

    async def test_session_persistence_across_reconnections(self, websocket_manager, session_manager):

        """BVJ: Validates session persistence across connection drops and reconnections."""

        user_id = "persistence_user"

        connection_id = "persistence_conn"

        websocket = MockWebSocketConnection(user_id, connection_id)
        

        await websocket_manager.add_connection(user_id, websocket)
        

        session_state = {"conversation_history": ["Hello", "Hi there!", "Can you help with optimization?"], "current_context": {"topic": "gpu_optimization", "complexity": "intermediate", "user_preferences": {"detailed_analysis": True}}, "agent_memory": {"user_expertise": "intermediate", "previous_requests": ["memory_optimization", "cost_analysis"]}}
        

        await websocket_manager.update_user_state(user_id, session_state)
        

        original_session_id = websocket_manager.connection_sessions[connection_id]
        

        await websocket_manager.remove_connection(connection_id)
        

        assert connection_id not in websocket_manager.connections, "Connection not removed"
        

        persisted_state = await session_manager.get_session_state(original_session_id)

        assert persisted_state is not None, "Session state not persisted in Redis"
        

        new_websocket = MockWebSocketConnection(user_id, connection_id)

        await websocket_manager.add_connection(user_id, new_websocket)
        

        reconnection_state = await websocket_manager.get_connection_state(connection_id)
        

        assert reconnection_state is not None, "State not restored after reconnection"
        

        restored_history = reconnection_state["state"]["conversation_history"]

        assert restored_history == session_state["conversation_history"], "Conversation history not preserved"
        

        restored_context = reconnection_state["state"]["current_context"]

        assert restored_context["topic"] == "gpu_optimization", "Context topic not preserved"

        assert restored_context["complexity"] == "intermediate", "Context complexity not preserved"
        

        restored_memory = reconnection_state["state"]["agent_memory"]

        assert restored_memory["user_expertise"] == "intermediate", "Agent memory not preserved"
        

        continuation_update = {"new_message": "Continue where we left off"}

        synced_count = await websocket_manager.update_user_state(user_id, continuation_update)
        

        assert synced_count >= 1, "State updates not working after reconnection"
        

        final_state = await websocket_manager.get_connection_state(connection_id)

        assert final_state["state"]["new_message"] == "Continue where we left off", "Continuation failed"
        

        logger.info(f"Session persistence validated across reconnection")
