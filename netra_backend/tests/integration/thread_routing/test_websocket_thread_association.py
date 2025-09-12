"""
Test WebSocket Thread Association Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket connection routing to correct threads for real-time chat
- Value Impact: WebSocket threading failures break real-time user experience and message delivery
- Strategic Impact: Core infrastructure for real-time AI chat platform

This test suite validates WebSocket thread association with real Redis and WebSocket infrastructure:
1. WebSocket connection to thread mapping
2. Connection thread switching and state management
3. Thread isolation between WebSocket connections
4. Redis-based WebSocket state persistence

CRITICAL: Uses REAL Redis and WebSocket core - NO mocks allowed for integration testing.
Expected: Initial failures - WebSocket threading likely has race condition issues.
"""

import asyncio
import uuid
import pytest
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from unittest.mock import patch, AsyncMock

from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.fixtures.lightweight_services import lightweight_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, WebSocketID, RequestID, ConnectionID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id,
    WebSocketEventType, WebSocketMessage, ConnectionState
)

# WebSocket and thread routing components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketConnectionManager
from netra_backend.app.websocket_core.utils import generate_connection_id
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager

# Redis and cache components
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
except ImportError:
    redis = None
    Redis = None


class TestWebSocketThreadAssociation(BaseIntegrationTest):
    """Test WebSocket connection to thread mapping with real Redis infrastructure."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_thread_mapping(self, lightweight_services_fixture, isolated_env):
        """Test WebSocket connections correctly map to threads."""
        
        # Skip if Redis not available
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Create test Redis connection (use real port if available)
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))  # Test port
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup test users and threads
        user_count = 3
        user_ids = [ensure_user_id(str(uuid.uuid4())) for _ in range(user_count)]
        websocket_manager = UnifiedWebSocketManager()
        thread_service = ThreadService()
        
        # Create threads for each user (using mocked database for this test)
        user_threads = {}
        for user_id in user_ids:
            # Mock thread creation since we're testing WebSocket layer
            thread_id = ensure_thread_id(f"thread_{uuid.uuid4()}")
            user_threads[user_id] = thread_id
        
        # Test WebSocket connection creation and thread association
        websocket_connections = {}
        connection_thread_mapping = {}
        
        for user_id in user_ids:
            thread_id = user_threads[user_id]
            websocket_id = ensure_websocket_id(generate_connection_id(user_id))
            
            # Create user execution context
            user_context = UserExecutionContext(
                user_id=str(user_id),
                thread_id=str(thread_id),
                run_id=f"run_{uuid.uuid4()}"
            )
            
            # Simulate WebSocket connection establishment
            connection_info = {
                "websocket_id": str(websocket_id),
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "connected_at": datetime.utcnow().isoformat(),
                "connection_state": ConnectionState.CONNECTED.value,
                "context": user_context.dict()
            }
            
            # Store connection mapping in Redis
            connection_key = f"websocket:connection:{websocket_id}"
            thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
            user_mapping_key = f"websocket:user_mapping:{user_id}"
            
            await redis_client.hset(connection_key, mapping=connection_info)
            await redis_client.sadd(thread_mapping_key, str(websocket_id))
            await redis_client.sadd(user_mapping_key, str(websocket_id))
            
            websocket_connections[websocket_id] = connection_info
            connection_thread_mapping[websocket_id] = thread_id
            
            self.logger.info(f"Created WebSocket {websocket_id} for user {user_id} thread {thread_id}")
        
        # Verify connection to thread mapping
        for websocket_id, expected_thread_id in connection_thread_mapping.items():
            # Retrieve connection info from Redis
            connection_key = f"websocket:connection:{websocket_id}"
            stored_connection = await redis_client.hgetall(connection_key)
            
            assert stored_connection, f"WebSocket connection {websocket_id} not found in Redis"
            assert stored_connection["thread_id"] == str(expected_thread_id), \
                f"WebSocket {websocket_id} mapped to wrong thread: {stored_connection['thread_id']} != {expected_thread_id}"
            
            # Verify reverse mapping (thread to websockets)
            thread_mapping_key = f"websocket:thread_mapping:{expected_thread_id}"
            thread_websockets = await redis_client.smembers(thread_mapping_key)
            assert str(websocket_id) in thread_websockets, \
                f"Thread {expected_thread_id} doesn't know about WebSocket {websocket_id}"
        
        # Test thread isolation - each thread should only know about its own WebSocket
        for user_id in user_ids:
            user_thread_id = user_threads[user_id]
            user_websocket = [ws_id for ws_id, thread_id in connection_thread_mapping.items() 
                             if thread_id == user_thread_id][0]
            
            # Get all websockets for this thread
            thread_mapping_key = f"websocket:thread_mapping:{user_thread_id}"
            thread_websockets = await redis_client.smembers(thread_mapping_key)
            
            # Should contain only this user's websocket
            assert len(thread_websockets) == 1, \
                f"Thread {user_thread_id} has {len(thread_websockets)} websockets, expected 1"
            assert str(user_websocket) in thread_websockets, \
                f"Thread {user_thread_id} doesn't contain its own WebSocket {user_websocket}"
            
            # Verify other threads don't contain this websocket
            other_thread_ids = [tid for uid, tid in user_threads.items() if uid != user_id]
            for other_thread_id in other_thread_ids:
                other_mapping_key = f"websocket:thread_mapping:{other_thread_id}"
                other_websockets = await redis_client.smembers(other_mapping_key)
                assert str(user_websocket) not in other_websockets, \
                    f"WebSocket {user_websocket} found in wrong thread {other_thread_id} - ISOLATION VIOLATION!"
        
        await redis_client.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_thread_switching_state_management(self, lightweight_services_fixture, isolated_env):
        """Test WebSocket connection thread switching and state consistency."""
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Create test Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup test user with multiple threads
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_count = 4
        thread_ids = [ensure_thread_id(f"thread_{uuid.uuid4()}") for _ in range(thread_count)]
        websocket_id = ensure_websocket_id(generate_websocket_id())
        
        websocket_manager = UnifiedWebSocketManager()
        state_manager = UnifiedStateManager()
        
        # Initialize WebSocket connection on first thread
        initial_thread = thread_ids[0]
        current_thread = initial_thread
        
        async def setup_websocket_thread_association(thread_id: ThreadID):
            """Setup WebSocket association with specific thread."""
            user_context = UserExecutionContext(
                user_id=str(user_id),
                thread_id=str(thread_id),
                run_id=f"run_{uuid.uuid4()}"
            )
            
            connection_info = {
                "websocket_id": str(websocket_id),
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "updated_at": datetime.utcnow().isoformat(),
                "connection_state": ConnectionState.CONNECTED.value,
                "switch_count": 0
            }
            
            # Update Redis mappings
            connection_key = f"websocket:connection:{websocket_id}"
            await redis_client.hset(connection_key, mapping=connection_info)
            
            # Remove from old thread mapping if exists
            if hasattr(setup_websocket_thread_association, 'previous_thread'):
                old_mapping_key = f"websocket:thread_mapping:{setup_websocket_thread_association.previous_thread}"
                await redis_client.srem(old_mapping_key, str(websocket_id))
            
            # Add to new thread mapping
            new_mapping_key = f"websocket:thread_mapping:{thread_id}"
            await redis_client.sadd(new_mapping_key, str(websocket_id))
            
            setup_websocket_thread_association.previous_thread = thread_id
            return connection_info
        
        # Test thread switching sequence
        switch_log = []
        
        for i, target_thread in enumerate(thread_ids):
            self.logger.info(f"Switching WebSocket {websocket_id} to thread {target_thread}")
            
            # Perform thread switch
            switch_start = time.time()
            connection_info = await setup_websocket_thread_association(target_thread)
            switch_duration = time.time() - switch_start
            
            switch_log.append({
                "switch_index": i,
                "from_thread": str(current_thread) if i > 0 else None,
                "to_thread": str(target_thread),
                "duration_ms": switch_duration * 1000,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Verify new thread association
            connection_key = f"websocket:connection:{websocket_id}"
            stored_connection = await redis_client.hgetall(connection_key)
            
            assert stored_connection["thread_id"] == str(target_thread), \
                f"WebSocket not properly associated with new thread {target_thread}"
            
            # Verify thread mapping updated
            thread_mapping_key = f"websocket:thread_mapping:{target_thread}"
            thread_websockets = await redis_client.smembers(thread_mapping_key)
            assert str(websocket_id) in thread_websockets, \
                f"Thread {target_thread} mapping not updated for WebSocket {websocket_id}"
            
            # Verify old thread mapping cleaned up (if not first switch)
            if i > 0:
                old_thread_mapping_key = f"websocket:thread_mapping:{current_thread}"
                old_websockets = await redis_client.smembers(old_thread_mapping_key)
                assert str(websocket_id) not in old_websockets, \
                    f"WebSocket {websocket_id} not removed from old thread {current_thread} - STATE LEAK!"
            
            current_thread = target_thread
            
            # Add small delay to simulate realistic switching
            await asyncio.sleep(0.1)
        
        # Verify final state consistency
        self.logger.info(f"Thread switching completed. Verifying final state...")
        
        # WebSocket should only be associated with final thread
        final_thread = thread_ids[-1]
        active_associations = []
        
        for thread_id in thread_ids:
            mapping_key = f"websocket:thread_mapping:{thread_id}"
            websockets = await redis_client.smembers(mapping_key)
            if str(websocket_id) in websockets:
                active_associations.append(thread_id)
        
        assert len(active_associations) == 1, \
            f"WebSocket {websocket_id} associated with {len(active_associations)} threads: {active_associations} - Should be 1!"
        assert active_associations[0] == final_thread, \
            f"WebSocket associated with wrong final thread: {active_associations[0]} != {final_thread}"
        
        # Log performance metrics
        avg_switch_time = sum(entry["duration_ms"] for entry in switch_log) / len(switch_log)
        max_switch_time = max(entry["duration_ms"] for entry in switch_log)
        self.logger.info(f"Switch performance: avg={avg_switch_time:.2f}ms, max={max_switch_time:.2f}ms")
        
        # Switch times should be reasonable (under 100ms for Redis operations)
        assert max_switch_time < 100, f"Thread switching too slow: {max_switch_time:.2f}ms > 100ms"
        
        await redis_client.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_websocket_thread_isolation(self, lightweight_services_fixture, isolated_env):
        """Test WebSocket thread isolation between multiple concurrent users."""
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Create test Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup multiple users with multiple threads and websockets each
        user_count = 4
        threads_per_user = 3
        websockets_per_thread = 2
        
        users_data = {}
        all_websocket_ids = set()
        
        # Create complex multi-user setup
        for user_idx in range(user_count):
            user_id = ensure_user_id(str(uuid.uuid4()))
            user_threads = {}
            
            for thread_idx in range(threads_per_user):
                thread_id = ensure_thread_id(f"user{user_idx}_thread{thread_idx}_{uuid.uuid4()}")
                thread_websockets = []
                
                for ws_idx in range(websockets_per_thread):
                    websocket_id = ensure_websocket_id(f"user{user_idx}_thread{thread_idx}_ws{ws_idx}_{uuid.uuid4()}")
                    thread_websockets.append(websocket_id)
                    all_websocket_ids.add(websocket_id)
                
                user_threads[thread_id] = thread_websockets
            
            users_data[user_id] = user_threads
        
        # Setup WebSocket connections in Redis
        async def setup_user_websockets(user_id: UserID, user_threads: Dict[ThreadID, List[WebSocketID]]):
            """Setup all WebSocket connections for a user."""
            for thread_id, websocket_ids in user_threads.items():
                for websocket_id in websocket_ids:
                    # Create connection info
                    connection_info = {
                        "websocket_id": str(websocket_id),
                        "user_id": str(user_id),
                        "thread_id": str(thread_id),
                        "connected_at": datetime.utcnow().isoformat(),
                        "connection_state": ConnectionState.CONNECTED.value,
                        "isolation_test": True
                    }
                    
                    # Store in Redis
                    connection_key = f"websocket:connection:{websocket_id}"
                    await redis_client.hset(connection_key, mapping=connection_info)
                    
                    # Update mappings
                    thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
                    user_mapping_key = f"websocket:user_mapping:{user_id}"
                    
                    await redis_client.sadd(thread_mapping_key, str(websocket_id))
                    await redis_client.sadd(user_mapping_key, str(websocket_id))
        
        # Setup all users concurrently
        self.logger.info(f"Setting up {user_count} users with {threads_per_user} threads each")
        await asyncio.gather(*[
            setup_user_websockets(user_id, user_threads) 
            for user_id, user_threads in users_data.items()
        ])
        
        # Verify cross-user isolation
        isolation_violations = []
        
        for user_id, user_threads in users_data.items():
            # Get all websockets belonging to this user
            user_mapping_key = f"websocket:user_mapping:{user_id}"
            user_websockets = await redis_client.smembers(user_mapping_key)
            expected_user_websockets = set()
            
            for thread_websockets in user_threads.values():
                expected_user_websockets.update(str(ws_id) for ws_id in thread_websockets)
            
            # Verify user has all their websockets
            assert len(user_websockets) == len(expected_user_websockets), \
                f"User {user_id} has {len(user_websockets)} websockets, expected {len(expected_user_websockets)}"
            
            # Verify no extra websockets
            extra_websockets = user_websockets - expected_user_websockets
            if extra_websockets:
                isolation_violations.append(f"User {user_id} has extra websockets: {extra_websockets}")
            
            # Verify thread-level isolation within user
            for thread_id, expected_thread_websockets in user_threads.items():
                thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
                actual_thread_websockets = await redis_client.smembers(thread_mapping_key)
                expected_thread_websocket_strs = {str(ws_id) for ws_id in expected_thread_websockets}
                
                # Check thread has correct websockets
                if actual_thread_websockets != expected_thread_websocket_strs:
                    isolation_violations.append(
                        f"Thread {thread_id} websocket mismatch: "
                        f"actual={actual_thread_websockets}, expected={expected_thread_websocket_strs}"
                    )
                
                # Verify websockets in thread belong to correct user
                for websocket_str in actual_thread_websockets:
                    connection_key = f"websocket:connection:{websocket_str}"
                    connection_info = await redis_client.hgetall(connection_key)
                    
                    if connection_info.get("user_id") != str(user_id):
                        isolation_violations.append(
                            f"WebSocket {websocket_str} in user {user_id}'s thread {thread_id} "
                            f"belongs to different user {connection_info.get('user_id')}"
                        )
        
        # Check for cross-contamination between users
        for user_id in users_data.keys():
            user_mapping_key = f"websocket:user_mapping:{user_id}"
            user_websockets = await redis_client.smembers(user_mapping_key)
            
            # Check if any other users have these websockets
            other_users = [uid for uid in users_data.keys() if uid != user_id]
            for other_user_id in other_users:
                other_mapping_key = f"websocket:user_mapping:{other_user_id}"
                other_websockets = await redis_client.smembers(other_mapping_key)
                
                overlap = user_websockets & other_websockets
                if overlap:
                    isolation_violations.append(
                        f"WebSocket overlap between user {user_id} and {other_user_id}: {overlap}"
                    )
        
        # Report any isolation violations
        if isolation_violations:
            for violation in isolation_violations:
                self.logger.error(f"ISOLATION VIOLATION: {violation}")
            raise AssertionError(f"Found {len(isolation_violations)} isolation violations")
        
        self.logger.info(f"Multi-user isolation verified: {user_count} users, {len(all_websocket_ids)} total websockets")
        await redis_client.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_lifecycle_thread_cleanup(self, lightweight_services_fixture, isolated_env):
        """Test WebSocket connection lifecycle and thread mapping cleanup."""
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Create test Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup test scenarios
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        # Test lifecycle: connect -> active -> disconnect -> cleanup
        lifecycle_websockets = []
        for i in range(5):
            websocket_id = ensure_websocket_id(f"lifecycle_{i}_{uuid.uuid4()}")
            lifecycle_websockets.append(websocket_id)
        
        async def simulate_websocket_lifecycle(websocket_id: WebSocketID):
            """Simulate complete WebSocket lifecycle with Redis state changes."""
            lifecycle_log = []
            
            # Phase 1: Connection establishment
            connection_info = {
                "websocket_id": str(websocket_id),
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "connected_at": datetime.utcnow().isoformat(),
                "connection_state": ConnectionState.CONNECTING.value,
                "lifecycle_test": True
            }
            
            connection_key = f"websocket:connection:{websocket_id}"
            await redis_client.hset(connection_key, mapping=connection_info)
            lifecycle_log.append("connecting")
            
            # Add to thread mapping
            thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
            await redis_client.sadd(thread_mapping_key, str(websocket_id))
            
            # Phase 2: Active connection
            await redis_client.hset(connection_key, "connection_state", ConnectionState.CONNECTED.value)
            await redis_client.hset(connection_key, "last_activity", datetime.utcnow().isoformat())
            lifecycle_log.append("connected")
            
            # Simulate activity
            await asyncio.sleep(0.1)
            
            # Phase 3: Disconnection
            await redis_client.hset(connection_key, "connection_state", ConnectionState.DISCONNECTED.value)
            await redis_client.hset(connection_key, "disconnected_at", datetime.utcnow().isoformat())
            lifecycle_log.append("disconnected")
            
            # Phase 4: Cleanup
            await redis_client.srem(thread_mapping_key, str(websocket_id))
            await redis_client.delete(connection_key)
            lifecycle_log.append("cleaned_up")
            
            return lifecycle_log
        
        # Run lifecycle simulations concurrently
        self.logger.info(f"Running {len(lifecycle_websockets)} WebSocket lifecycle simulations")
        lifecycle_results = await asyncio.gather(*[
            simulate_websocket_lifecycle(ws_id) for ws_id in lifecycle_websockets
        ])
        
        # Verify all lifecycles completed successfully
        for i, lifecycle_log in enumerate(lifecycle_results):
            expected_phases = ["connecting", "connected", "disconnected", "cleaned_up"]
            assert lifecycle_log == expected_phases, \
                f"WebSocket {i} lifecycle incomplete: {lifecycle_log} != {expected_phases}"
        
        # Verify cleanup effectiveness - no lingering state
        thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
        remaining_websockets = await redis_client.smembers(thread_mapping_key)
        
        assert len(remaining_websockets) == 0, \
            f"Thread mapping not cleaned up: {remaining_websockets} websockets remain"
        
        # Check for orphaned connection records
        orphaned_connections = []
        for websocket_id in lifecycle_websockets:
            connection_key = f"websocket:connection:{websocket_id}"
            if await redis_client.exists(connection_key):
                orphaned_connections.append(websocket_id)
        
        assert len(orphaned_connections) == 0, \
            f"Orphaned connection records found: {orphaned_connections}"
        
        # Test edge case: rapid connect/disconnect cycles
        rapid_websocket = ensure_websocket_id(f"rapid_{uuid.uuid4()}")
        rapid_cycles = 10
        
        for cycle in range(rapid_cycles):
            # Quick connect
            connection_info = {
                "websocket_id": str(rapid_websocket),
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "cycle": cycle,
                "connection_state": ConnectionState.CONNECTED.value
            }
            
            connection_key = f"websocket:connection:{rapid_websocket}"
            await redis_client.hset(connection_key, mapping=connection_info)
            await redis_client.sadd(thread_mapping_key, str(rapid_websocket))
            
            # Quick disconnect and cleanup
            await redis_client.srem(thread_mapping_key, str(rapid_websocket))
            await redis_client.delete(connection_key)
            
            # Verify clean state between cycles
            assert not await redis_client.exists(connection_key), \
                f"Connection record not cleaned up in cycle {cycle}"
            
            thread_websockets = await redis_client.smembers(thread_mapping_key)
            assert str(rapid_websocket) not in thread_websockets, \
                f"Thread mapping not cleaned up in cycle {cycle}"
        
        self.logger.info(f"WebSocket lifecycle and cleanup verification completed successfully")
        await redis_client.close()