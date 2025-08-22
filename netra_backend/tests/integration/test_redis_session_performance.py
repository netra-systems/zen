"""
Redis Session Performance Tests

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) - Core session management functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from session state failures
- Value Impact: Ensures Redis session state performs under load
- Revenue Impact: Prevents customer session loss/desync that would cause immediate churn

Performance and load testing for Redis session state synchronization.
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio

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

from netra_backend.tests.redis_session_mocks import (

    MockRedisConnection,

    MockRedisSessionManager,

    MockWebSocketConnection,

    MockWebSocketManagerWithRedis,

)

logger = central_logger.get_logger(__name__)

class TestRedisSessionPerformance:

    """Performance tests for Redis session state synchronization."""

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

    async def test_state_synchronization_real_time(self, websocket_manager, session_manager, redis_connection):

        """BVJ: Validates real-time state synchronization across connections."""

        user_id = "realtime_sync_user"

        connections = []
        
        for i in range(4):

            connection_id = f"realtime_conn_{i+1}"

            websocket = MockWebSocketConnection(user_id, connection_id)

            await websocket_manager.add_connection(user_id, websocket)

            connections.append((connection_id, websocket))
        
        rapid_updates = [{"message_input": "Hello agent", "timestamp": time.time()}, {"agent_thinking": True, "timestamp": time.time()}, {"agent_response": "Hello! How can I help?", "timestamp": time.time()}, {"conversation_state": "active", "timestamp": time.time()}, {"last_interaction": datetime.now(timezone.utc).isoformat(), "timestamp": time.time()}]
        
        sync_times = []
        
        for update in rapid_updates:

            start_time = time.time()
            
            synced_count = await websocket_manager.update_user_state(user_id, update)
            
            sync_time = time.time() - start_time

            sync_times.append(sync_time)
            
            assert synced_count == 4, f"Not all connections synced: {synced_count}/4"
            
            await asyncio.sleep(0.1)
        
        for connection_id, websocket in connections:

            connection_state = await websocket_manager.get_connection_state(connection_id)

            state_data = connection_state["state"]
            
            for update in rapid_updates:

                for key, value in update.items():

                    if key != "timestamp":

                        assert state_data.get(key) == value, f"Update {key} missing in {connection_id}"
        
        avg_sync_time = sum(sync_times) / len(sync_times)

        max_sync_time = max(sync_times)
        
        assert avg_sync_time < 0.5, f"Average sync time {avg_sync_time:.2f}s too slow"

        assert max_sync_time < 1.0, f"Max sync time {max_sync_time:.2f}s too slow"
        
        assert redis_connection.operation_count > 0, "No Redis operations recorded"
        
        sync_events = redis_connection.sync_events

        assert len(sync_events) >= len(rapid_updates), "Not all sync events recorded"
        
        logger.info(f"Real-time sync validated: {avg_sync_time:.2f}s avg, {max_sync_time:.2f}s max")

    @pytest.mark.asyncio

    async def test_concurrent_state_sync_load_testing(self, websocket_manager, session_manager):

        """BVJ: Validates state sync performance under concurrent load."""

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
        
        update_tasks = []
        
        async def rapid_state_updates(user_id: str, update_count: int):

            """Perform rapid state updates for a user."""

            update_times = []
            
            for i in range(update_count):

                update_data = {f"update_{i}": f"value_{i}", "update_timestamp": time.time(), "sequence": i}
                
                start_time = time.time()

                synced_count = await websocket_manager.update_user_state(user_id, update_data)

                update_time = time.time() - start_time
                
                update_times.append(update_time)
                
                await asyncio.sleep(0.05)
            
            return {"user_id": user_id, "updates_completed": update_count, "avg_update_time": sum(update_times) / len(update_times), "max_update_time": max(update_times), "final_sync_count": synced_count}
        
        updates_per_user = 10

        start_time = time.time()
        
        load_results = await asyncio.gather(*[rapid_state_updates(f"load_user_{i}", updates_per_user) for i in range(concurrent_users)])
        
        total_load_time = time.time() - start_time
        
        total_updates = concurrent_users * updates_per_user

        successful_updates = sum(result["updates_completed"] for result in load_results)
        
        assert successful_updates == total_updates, f"Not all updates completed: {successful_updates}/{total_updates}"
        
        avg_update_times = [result["avg_update_time"] for result in load_results]

        overall_avg_time = sum(avg_update_times) / len(avg_update_times)
        
        max_update_times = [result["max_update_time"] for result in load_results]

        overall_max_time = max(max_update_times)
        
        assert overall_avg_time < 1.0, f"Average update time {overall_avg_time:.2f}s too slow under load"

        assert overall_max_time < 2.0, f"Max update time {overall_max_time:.2f}s too slow under load"
        
        throughput = total_updates / total_load_time

        assert throughput >= 10.0, f"Update throughput {throughput:.1f} updates/sec too low"
        
        for result in load_results:

            user_id = result["user_id"]

            expected_connections = connections_per_user
            
            assert result["final_sync_count"] == expected_connections, f"Final sync count mismatch for {user_id}: {result['final_sync_count']}/{expected_connections}"
        
        logger.info(f"Concurrent load test validated: {throughput:.1f} updates/sec, {overall_avg_time:.2f}s avg time")

    @pytest.mark.asyncio

    async def test_state_conflict_resolution(self, websocket_manager, session_manager, redis_connection):

        """BVJ: Validates state conflict resolution when concurrent updates occur."""

        user_id = "conflict_user"

        connections = []
        
        for i in range(2):

            connection_id = f"conflict_conn_{i+1}"

            websocket = MockWebSocketConnection(user_id, connection_id)

            await websocket_manager.add_connection(user_id, websocket)

            connections.append((connection_id, websocket))
        
        conflicting_updates = [{"shared_field": "value_from_conn1", "conn1_field": "unique1", "timestamp": time.time()}, {"shared_field": "value_from_conn2", "conn2_field": "unique2", "timestamp": time.time() + 0.001}]
        
        update_tasks = []

        for i, update in enumerate(conflicting_updates):

            task = websocket_manager.update_user_state(user_id, update)

            update_tasks.append(task)
        
        start_time = time.time()

        update_results = await asyncio.gather(*update_tasks)

        conflict_resolution_time = time.time() - start_time
        
        for result in update_results:

            assert result >= 2, "Not all connections received updates"
        
        final_states = []

        for connection_id, websocket in connections:

            state = await websocket_manager.get_connection_state(connection_id)

            final_states.append(state["state"])
        
        first_state = final_states[0]

        for state in final_states[1:]:

            assert state == first_state, "State inconsistency after conflict resolution"
        
        final_state = first_state
        
        assert "conn1_field" in final_state, "Update 1 data lost"

        assert "conn2_field" in final_state, "Update 2 data lost"

        assert final_state["conn1_field"] == "unique1", "Update 1 value incorrect"

        assert final_state["conn2_field"] == "unique2", "Update 2 value incorrect"
        
        assert "shared_field" in final_state, "Shared field lost in conflict"
        
        assert conflict_resolution_time < 2.0, f"Conflict resolution took {conflict_resolution_time:.2f}s too long"
        
        metrics = session_manager.sync_metrics

        assert metrics["sync_operations"] >= 2, "Not all sync operations counted"
        
        logger.info(f"State conflict resolution validated: {conflict_resolution_time:.2f}s resolution time")
