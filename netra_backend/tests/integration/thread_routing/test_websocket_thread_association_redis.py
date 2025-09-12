"""
Test WebSocket Thread Association with Real Redis Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket-to-thread mapping for real-time AI chat delivery
- Value Impact: WebSocket routing failures break real-time user experience and message delivery precision
- Strategic Impact: Core infrastructure enabling scalable real-time multi-user AI conversations

This test suite validates WebSocket thread association with real Redis infrastructure:
1. WebSocket connection to thread mapping with user authentication
2. Real-time thread switching and connection state management
3. Multi-user WebSocket isolation and cross-contamination prevention
4. Redis-based state persistence and cleanup for connection lifecycle
5. Concurrent WebSocket operations and thread routing precision
6. WebSocket event routing validation with authentication context

CRITICAL: Uses REAL Redis (port 6381) and authentication - NO mocks allowed.
Expected: Initial failures - WebSocket threading may have race conditions and isolation issues.
Authentication REQUIRED: All tests use real JWT tokens for proper user context isolation.
"""

import asyncio
import uuid
import pytest
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
from unittest.mock import patch
from collections import defaultdict

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, WebSocketID, RequestID, ConnectionID, SessionID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id, ensure_request_id,
    WebSocketEventType, WebSocketMessage, ConnectionState,
    AuthValidationResult, SessionValidationResult
)

# Helper function for tests
def ensure_session_id(value: str) -> SessionID:
    """Helper to ensure SessionID type."""
    return SessionID(value)

# WebSocket and thread routing components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Helper function for tests
def generate_websocket_id() -> str:
    """Generate a unique WebSocket ID for testing."""
    return f"ws_{uuid.uuid4().hex[:16]}"
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager
from netra_backend.app.db.models_postgres import Thread, Message, User

# Redis and cache components
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
except ImportError:
    redis = None
    Redis = None


class TestWebSocketThreadAssociationRedis(BaseIntegrationTest):
    """Test WebSocket connection to thread mapping with real Redis infrastructure and authentication."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_websocket_thread_mapping_precision(self, real_services_fixture, isolated_env):
        """Test WebSocket connections map precisely to threads with authentication."""
        
        # Skip if Redis not available
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Setup Redis connection (test environment port)
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))  # Test port
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await await redis_client.ping()
            self.logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup authenticated users and threads
        auth_helper = E2EAuthHelper()
        user_count = 4
        threads_per_user = 3
        
        authenticated_users = []
        user_threads_mapping = {}
        websocket_connections = {}
        
        # Create authenticated users with thread contexts
        for user_idx in range(user_count):
            user_data = await auth_helper.create_authenticated_test_user(
                email=f"websocket.mapping.user.{user_idx}@test.com",
                name=f"WebSocket Mapping User {user_idx}",
                password="securepassword123"
            )
            authenticated_users.append(user_data)
            
            # Create multiple threads per user for mapping precision testing
            user_id = ensure_user_id(user_data["user_id"])
            user_threads = []
            
            for thread_idx in range(threads_per_user):
                thread_id = ensure_thread_id(f"user{user_idx}_thread{thread_idx}_{uuid.uuid4()}")
                user_threads.append(thread_id)
                
                # Create WebSocket connection for this specific thread
                websocket_id = ensure_websocket_id(f"ws{user_idx}t{thread_idx}_{generate_websocket_id()}")
                
                # Create authenticated user execution context
                user_context = UserExecutionContext(
                    user_id=str(user_id),
                    thread_id=str(thread_id),
                    run_id=f"run_{uuid.uuid4()}",
                    session_id=user_data["session_id"],
                    auth_token=user_data["access_token"],
                    permissions=user_data.get("permissions", [])
                )
                
                # Store connection mapping in Redis with authentication context
                connection_info = {
                    "websocket_id": str(websocket_id),
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "session_id": user_data["session_id"],
                    "auth_token_hash": hashlib.sha256(user_data["access_token"].encode()).hexdigest()[:16],
                    "connected_at": datetime.utcnow().isoformat(),
                    "connection_state": ConnectionState.CONNECTED.value,
                    "user_context": user_context.dict(),
                    "precision_test": True
                }
                
                # Redis storage keys for WebSocket-thread association
                connection_key = f"websocket:connection:{websocket_id}"
                thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
                user_mapping_key = f"websocket:user_mapping:{user_id}"
                auth_mapping_key = f"websocket:auth_mapping:{user_data['session_id']}"
                
                # Store in Redis with atomic operations
                pipe = await redis_client.pipeline()
                pipe.hset(connection_key, mapping=connection_info)
                pipe.sadd(thread_mapping_key, str(websocket_id))
                pipe.sadd(user_mapping_key, str(websocket_id))
                pipe.sadd(auth_mapping_key, str(websocket_id))
                pipe.expire(connection_key, 3600)  # 1 hour expiration
                await pipe.execute()
                
                websocket_connections[websocket_id] = {
                    "connection_info": connection_info,
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "expected_isolation": True
                }
                
                self.logger.info(f"Created authenticated WebSocket {websocket_id} for user {user_id} thread {thread_id}")
            
            user_threads_mapping[user_id] = user_threads
        
        # Verify WebSocket to thread mapping precision
        mapping_violations = []
        
        for websocket_id, ws_info in websocket_connections.items():
            expected_thread_id = ws_info["thread_id"]
            expected_user_id = ws_info["user_id"]
            
            # Retrieve connection info from Redis
            connection_key = f"websocket:connection:{websocket_id}"
            stored_connection = await await redis_client.hgetall(connection_key)
            
            # Verify connection exists and has correct mapping
            if not stored_connection:
                mapping_violations.append(f"WebSocket connection {websocket_id} not found in Redis")
                continue
            
            stored_thread_id = stored_connection.get("thread_id")
            stored_user_id = stored_connection.get("user_id")
            
            if stored_thread_id != str(expected_thread_id):
                mapping_violations.append(
                    f"WebSocket {websocket_id} mapped to wrong thread: {stored_thread_id} != {expected_thread_id}"
                )
            
            if stored_user_id != str(expected_user_id):
                mapping_violations.append(
                    f"WebSocket {websocket_id} mapped to wrong user: {stored_user_id} != {expected_user_id}"
                )
            
            # Verify reverse mapping (thread -> websockets)
            thread_mapping_key = f"websocket:thread_mapping:{expected_thread_id}"
            thread_websockets = await await redis_client.smembers(thread_mapping_key)
            
            if str(websocket_id) not in thread_websockets:
                mapping_violations.append(
                    f"Thread {expected_thread_id} doesn't know about WebSocket {websocket_id}"
                )
            
            # Verify user mapping (user -> websockets)
            user_mapping_key = f"websocket:user_mapping:{expected_user_id}"
            user_websockets = await await redis_client.smembers(user_mapping_key)
            
            if str(websocket_id) not in user_websockets:
                mapping_violations.append(
                    f"User {expected_user_id} doesn't know about WebSocket {websocket_id}"
                )
        
        # Test cross-user isolation - ensure no WebSocket appears in wrong user's context
        for user_id, user_threads in user_threads_mapping.items():
            user_mapping_key = f"websocket:user_mapping:{user_id}"
            user_websockets = await await redis_client.smembers(user_mapping_key)
            
            # Verify each WebSocket in user mapping actually belongs to this user
            for ws_id_str in user_websockets:
                ws_id = ensure_websocket_id(ws_id_str)
                if ws_id in websocket_connections:
                    actual_user_id = websocket_connections[ws_id]["user_id"]
                    if actual_user_id != user_id:
                        mapping_violations.append(
                            f"User {user_id} mapping contains WebSocket {ws_id} that belongs to user {actual_user_id} - ISOLATION VIOLATION!"
                        )
            
            # Verify thread isolation - each thread should only contain its own WebSocket
            for thread_id in user_threads:
                thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
                thread_websockets = await await redis_client.smembers(thread_mapping_key)
                
                # Should contain exactly one WebSocket for this thread
                if len(thread_websockets) != 1:
                    mapping_violations.append(
                        f"Thread {thread_id} has {len(thread_websockets)} websockets, expected 1: {thread_websockets}"
                    )
                else:
                    ws_id_str = list(thread_websockets)[0]
                    ws_id = ensure_websocket_id(ws_id_str)
                    if ws_id in websocket_connections:
                        actual_thread_id = websocket_connections[ws_id]["thread_id"]
                        if actual_thread_id != thread_id:
                            mapping_violations.append(
                                f"Thread {thread_id} contains WebSocket {ws_id} that belongs to thread {actual_thread_id}"
                            )
        
        # Check for cross-contamination between different users' threads
        for user_id in user_threads_mapping.keys():
            other_users = [uid for uid in user_threads_mapping.keys() if uid != user_id]
            
            for other_user_id in other_users:
                # Get all websockets for current user
                user_mapping_key = f"websocket:user_mapping:{user_id}"
                user_websockets = await await redis_client.smembers(user_mapping_key)
                
                # Check if any of these websockets appear in other user's threads
                for other_thread_id in user_threads_mapping[other_user_id]:
                    other_thread_mapping_key = f"websocket:thread_mapping:{other_thread_id}"
                    other_thread_websockets = await await redis_client.smembers(other_thread_mapping_key)
                    
                    contaminated_websockets = user_websockets & other_thread_websockets
                    if contaminated_websockets:
                        mapping_violations.append(
                            f"Cross-user contamination: WebSockets {contaminated_websockets} from user {user_id} found in user {other_user_id}'s thread {other_thread_id}"
                        )
        
        # Report mapping violations
        if mapping_violations:
            for violation in mapping_violations[:10]:  # Show first 10 violations
                self.logger.error(f"WEBSOCKET MAPPING VIOLATION: {violation}")
            
            if len(mapping_violations) > 10:
                self.logger.error(f"... and {len(mapping_violations) - 10} more violations")
            
            raise AssertionError(f"Found {len(mapping_violations)} WebSocket mapping violations")
        
        self.logger.info(f"WebSocket thread mapping precision verified: {len(websocket_connections)} connections correctly mapped")
        await await redis_client.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_websocket_thread_switching_state_consistency(self, real_services_fixture, isolated_env):
        """Test WebSocket connection thread switching with authentication state management."""
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Setup Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup authenticated user with multiple threads for switching
        auth_helper = E2EAuthHelper()
        user_data = await auth_helper.create_authenticated_test_user(
            email="thread.switching@test.com",
            name="Thread Switching Test User",
            password="securepassword123"
        )
        
        user_id = ensure_user_id(user_data["user_id"])
        websocket_id = ensure_websocket_id(generate_websocket_id())
        
        # Create multiple threads for switching between
        thread_count = 5
        thread_ids = [ensure_thread_id(f"switch_thread_{i}_{uuid.uuid4()}") for i in range(thread_count)]
        
        websocket_manager = UnifiedWebSocketManager()
        state_manager = UnifiedStateManager()
        
        # Initial thread association
        current_thread = thread_ids[0]
        switch_log = []
        
        async def setup_authenticated_websocket_thread_association(thread_id: ThreadID, switch_index: int):
            """Setup WebSocket association with specific thread using authentication."""
            user_context = UserExecutionContext(
                user_id=str(user_id),
                thread_id=str(thread_id),
                run_id=f"switch_run_{switch_index}_{uuid.uuid4()}",
                session_id=user_data["session_id"],
                auth_token=user_data["access_token"],
                permissions=user_data.get("permissions", [])
            )
            
            connection_info = {
                "websocket_id": str(websocket_id),
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "session_id": user_data["session_id"],
                "auth_token_hash": hashlib.sha256(user_data["access_token"].encode()).hexdigest()[:16],
                "updated_at": datetime.utcnow().isoformat(),
                "connection_state": ConnectionState.CONNECTED.value,
                "switch_index": switch_index,
                "user_context": user_context.dict(),
                "switch_test": True
            }
            
            # Atomic thread switching using Redis pipeline
            pipe = await redis_client.pipeline()
            
            # Update connection info
            connection_key = f"websocket:connection:{websocket_id}"
            pipe.hset(connection_key, mapping=connection_info)
            
            # Remove from old thread mapping if exists
            if hasattr(setup_authenticated_websocket_thread_association, 'previous_thread'):
                old_mapping_key = f"websocket:thread_mapping:{setup_authenticated_websocket_thread_association.previous_thread}"
                pipe.srem(old_mapping_key, str(websocket_id))
            
            # Add to new thread mapping
            new_mapping_key = f"websocket:thread_mapping:{thread_id}"
            pipe.sadd(new_mapping_key, str(websocket_id))
            
            # Update user-level mapping (should remain consistent)
            user_mapping_key = f"websocket:user_mapping:{user_id}"
            pipe.sadd(user_mapping_key, str(websocket_id))
            
            # Execute all operations atomically
            await pipe.execute()
            
            setup_authenticated_websocket_thread_association.previous_thread = thread_id
            return connection_info
        
        # Execute thread switching sequence
        switching_start = time.time()
        
        for i, target_thread in enumerate(thread_ids):
            self.logger.info(f"Switching authenticated WebSocket {websocket_id} to thread {target_thread} (switch {i+1}/{len(thread_ids)})")
            
            switch_start_time = time.time()
            connection_info = await setup_authenticated_websocket_thread_association(target_thread, i)
            switch_duration = time.time() - switch_start_time
            
            switch_record = {
                "switch_index": i,
                "from_thread": str(current_thread) if i > 0 else None,
                "to_thread": str(target_thread),
                "duration_ms": switch_duration * 1000,
                "timestamp": datetime.utcnow().isoformat(),
                "auth_context_preserved": True
            }
            switch_log.append(switch_record)
            
            # Verify new thread association
            connection_key = f"websocket:connection:{websocket_id}"
            stored_connection = await await redis_client.hgetall(connection_key)
            
            # Verify thread mapping updated correctly
            if stored_connection.get("thread_id") != str(target_thread):
                raise AssertionError(f"WebSocket not properly switched to thread {target_thread}: got {stored_connection.get('thread_id')}")
            
            # Verify authentication context preserved
            if stored_connection.get("session_id") != user_data["session_id"]:
                raise AssertionError(f"Authentication context lost during thread switch: session_id mismatch")
            
            # Verify thread mapping contains WebSocket
            thread_mapping_key = f"websocket:thread_mapping:{target_thread}"
            thread_websockets = await await redis_client.smembers(thread_mapping_key)
            
            if str(websocket_id) not in thread_websockets:
                raise AssertionError(f"Thread {target_thread} mapping not updated for WebSocket {websocket_id}")
            
            # Verify old thread mapping cleaned up (if not first switch)
            if i > 0:
                old_thread_mapping_key = f"websocket:thread_mapping:{current_thread}"
                old_websockets = await await redis_client.smembers(old_thread_mapping_key)
                if str(websocket_id) in old_websockets:
                    raise AssertionError(f"WebSocket {websocket_id} not removed from old thread {current_thread} - STATE LEAK!")
            
            # Update current thread for next iteration
            current_thread = target_thread
            
            # Small delay to simulate realistic switching patterns
            await asyncio.sleep(0.1)
        
        total_switching_duration = time.time() - switching_start
        
        # Verify final state consistency
        self.logger.info("Verifying final switching state consistency...")
        
        # WebSocket should only be associated with final thread
        final_thread = thread_ids[-1]
        active_associations = []
        
        for thread_id in thread_ids:
            mapping_key = f"websocket:thread_mapping:{thread_id}"
            websockets = await await redis_client.smembers(mapping_key)
            if str(websocket_id) in websockets:
                active_associations.append(thread_id)
        
        if len(active_associations) != 1:
            raise AssertionError(
                f"WebSocket {websocket_id} associated with {len(active_associations)} threads: {active_associations} - Should be exactly 1!"
            )
        
        if active_associations[0] != final_thread:
            raise AssertionError(
                f"WebSocket associated with wrong final thread: {active_associations[0]} != {final_thread}"
            )
        
        # Verify user mapping remained consistent throughout switching
        user_mapping_key = f"websocket:user_mapping:{user_id}"
        user_websockets = await await redis_client.smembers(user_mapping_key)
        
        if str(websocket_id) not in user_websockets:
            raise AssertionError(f"User mapping lost WebSocket {websocket_id} during thread switching")
        
        # Verify authentication context integrity
        connection_key = f"websocket:connection:{websocket_id}"
        final_connection = await await redis_client.hgetall(connection_key)
        
        if final_connection.get("session_id") != user_data["session_id"]:
            raise AssertionError("Authentication session lost during thread switching")
        
        if final_connection.get("user_id") != str(user_id):
            raise AssertionError("User ID corrupted during thread switching")
        
        # Performance analysis
        switch_times = [record["duration_ms"] for record in switch_log]
        avg_switch_time = sum(switch_times) / len(switch_times)
        max_switch_time = max(switch_times)
        p95_switch_time = sorted(switch_times)[int(0.95 * len(switch_times))]
        
        # Switch performance should be reasonable
        assert max_switch_time < 100, f"Thread switching too slow: max={max_switch_time:.2f}ms (need <100ms)"
        assert avg_switch_time < 50, f"Average switch time too slow: {avg_switch_time:.2f}ms (need <50ms)"
        
        self.logger.info(f"Thread switching performance:")
        self.logger.info(f"  Total switches: {len(switch_log)}")
        self.logger.info(f"  Average time: {avg_switch_time:.2f}ms")
        self.logger.info(f"  95th percentile: {p95_switch_time:.2f}ms")
        self.logger.info(f"  Max time: {max_switch_time:.2f}ms")
        self.logger.info(f"  Total duration: {total_switching_duration:.2f}s")
        
        await await redis_client.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_authenticated_websocket_operations_isolation(self, real_services_fixture, isolated_env):
        """Test concurrent WebSocket operations maintain proper user isolation with authentication."""
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Setup Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup complex concurrent scenario
        auth_helper = E2EAuthHelper()
        concurrent_users = 6
        websockets_per_user = 4
        operations_per_websocket = 3
        
        authenticated_users = []
        concurrent_operations = []
        
        # Create authenticated users for concurrent testing
        for user_idx in range(concurrent_users):
            user_data = await auth_helper.create_authenticated_test_user(
                email=f"concurrent.ws.user.{user_idx}@test.com",
                name=f"Concurrent WebSocket User {user_idx}",
                password="securepassword123"
            )
            authenticated_users.append(user_data)
        
        # Generate concurrent WebSocket operations
        operation_id = 0
        for user_idx, user_data in enumerate(authenticated_users):
            user_id = ensure_user_id(user_data["user_id"])
            
            for ws_idx in range(websockets_per_user):
                websocket_id = ensure_websocket_id(f"concurrent_u{user_idx}w{ws_idx}_{generate_websocket_id()}")
                thread_id = ensure_thread_id(f"concurrent_u{user_idx}w{ws_idx}_thread_{uuid.uuid4()}")
                
                for op_idx in range(operations_per_websocket):
                    operation = {
                        "operation_id": operation_id,
                        "user_data": user_data,
                        "user_id": user_id,
                        "websocket_id": websocket_id,
                        "thread_id": thread_id,
                        "operation_index": op_idx,
                        "operation_type": ["connect", "update", "message"][op_idx % 3]
                    }
                    concurrent_operations.append(operation)
                    operation_id += 1
        
        async def execute_concurrent_websocket_operation(operation: Dict):
            """Execute a single WebSocket operation concurrently."""
            op_start_time = time.time()
            
            try:
                user_data = operation["user_data"]
                user_id = operation["user_id"]
                websocket_id = operation["websocket_id"]
                thread_id = operation["thread_id"]
                op_type = operation["operation_type"]
                
                # Create authenticated user context
                user_context = UserExecutionContext(
                    user_id=str(user_id),
                    thread_id=str(thread_id),
                    run_id=f"concurrent_op_{operation['operation_id']}",
                    session_id=user_data["session_id"],
                    auth_token=user_data["access_token"],
                    permissions=user_data.get("permissions", [])
                )
                
                if op_type == "connect":
                    # Initial connection establishment
                    connection_info = {
                        "websocket_id": str(websocket_id),
                        "user_id": str(user_id),
                        "thread_id": str(thread_id),
                        "session_id": user_data["session_id"],
                        "auth_token_hash": hashlib.sha256(user_data["access_token"].encode()).hexdigest()[:16],
                        "connected_at": datetime.utcnow().isoformat(),
                        "connection_state": ConnectionState.CONNECTING.value,
                        "concurrent_test": True,
                        "operation_id": operation["operation_id"]
                    }
                    
                    # Store connection with atomic operations
                    pipe = await redis_client.pipeline()
                    connection_key = f"websocket:connection:{websocket_id}"
                    pipe.hset(connection_key, mapping=connection_info)
                    pipe.sadd(f"websocket:thread_mapping:{thread_id}", str(websocket_id))
                    pipe.sadd(f"websocket:user_mapping:{user_id}", str(websocket_id))
                    await pipe.execute()
                    
                elif op_type == "update":
                    # Update connection state
                    connection_key = f"websocket:connection:{websocket_id}"
                    await await redis_client.hset(connection_key, "connection_state", ConnectionState.CONNECTED.value)
                    await await redis_client.hset(connection_key, "last_activity", datetime.utcnow().isoformat())
                    
                elif op_type == "message":
                    # Simulate message routing operation
                    message_data = {
                        "message_id": str(uuid.uuid4()),
                        "websocket_id": str(websocket_id),
                        "thread_id": str(thread_id),
                        "user_id": str(user_id),
                        "content": f"Concurrent test message from operation {operation['operation_id']}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Store message routing info
                    message_key = f"websocket:pending_message:{websocket_id}"
                    await await redis_client.lpush(message_key, json.dumps(message_data))
                    await await redis_client.expire(message_key, 300)  # 5 minute expiration
                
                duration = time.time() - op_start_time
                return {
                    "operation_id": operation["operation_id"],
                    "status": "success",
                    "duration": duration,
                    "user_id": str(user_id),
                    "websocket_id": str(websocket_id),
                    "thread_id": str(thread_id),
                    "operation_type": op_type
                }
                
            except Exception as e:
                duration = time.time() - op_start_time
                return {
                    "operation_id": operation["operation_id"],
                    "status": "error",
                    "error": str(e),
                    "duration": duration,
                    "user_id": str(operation.get("user_id", "unknown")),
                    "operation_type": operation.get("operation_type", "unknown")
                }
        
        # Execute all concurrent operations
        self.logger.info(f"Executing {len(concurrent_operations)} concurrent WebSocket operations")
        concurrent_start = time.time()
        
        operation_results = await asyncio.gather(*[
            execute_concurrent_websocket_operation(op) for op in concurrent_operations
        ])
        
        concurrent_duration = time.time() - concurrent_start
        
        # Analyze concurrent operation results
        successful_operations = [r for r in operation_results if r["status"] == "success"]
        failed_operations = [r for r in operation_results if r["status"] == "error"]
        
        success_rate = len(successful_operations) / len(operation_results)
        operations_per_second = len(operation_results) / concurrent_duration
        
        # Require high success rate for concurrent operations
        assert success_rate >= 0.85, f"Concurrent operation success rate too low: {success_rate:.1%} (need 85%+)"
        
        self.logger.info(f"Concurrent operations performance:")
        self.logger.info(f"  Success rate: {success_rate:.1%} ({len(successful_operations)}/{len(operation_results)})")
        self.logger.info(f"  Operations/sec: {operations_per_second:.2f}")
        self.logger.info(f"  Total duration: {concurrent_duration:.2f}s")
        
        # Verify isolation integrity after concurrent operations
        isolation_violations = []
        
        # Group successful operations by user
        user_operations = defaultdict(list)
        for op_result in successful_operations:
            user_operations[op_result["user_id"]].append(op_result)
        
        # Verify each user's operations maintain isolation
        for user_id_str, user_ops in user_operations.items():
            user_id = ensure_user_id(user_id_str)
            
            # Get all websockets that should belong to this user
            expected_user_websockets = set(op["websocket_id"] for op in user_ops)
            
            # Check Redis user mapping
            user_mapping_key = f"websocket:user_mapping:{user_id}"
            actual_user_websockets = await await redis_client.smembers(user_mapping_key)
            
            # Verify user mapping contains expected websockets
            missing_websockets = expected_user_websockets - set(actual_user_websockets)
            if missing_websockets:
                isolation_violations.append(
                    f"User {user_id} missing WebSockets in mapping: {missing_websockets}"
                )
            
            # Verify no extra websockets in user mapping
            extra_websockets = set(actual_user_websockets) - expected_user_websockets
            if extra_websockets:
                isolation_violations.append(
                    f"User {user_id} has extra WebSockets in mapping: {extra_websockets}"
                )
            
            # Verify each websocket's connection info has correct user_id
            for websocket_id_str in actual_user_websockets:
                connection_key = f"websocket:connection:{websocket_id_str}"
                connection_info = await await redis_client.hgetall(connection_key)
                
                if connection_info.get("user_id") != user_id_str:
                    isolation_violations.append(
                        f"WebSocket {websocket_id_str} connection info has wrong user_id: {connection_info.get('user_id')} != {user_id_str}"
                    )
        
        # Check for cross-user contamination
        all_user_ids = list(user_operations.keys())
        for i, user_id_a in enumerate(all_user_ids):
            for user_id_b in all_user_ids[i+1:]:
                # Get websockets for both users
                mapping_key_a = f"websocket:user_mapping:{user_id_a}"
                mapping_key_b = f"websocket:user_mapping:{user_id_b}"
                
                websockets_a = await await redis_client.smembers(mapping_key_a)
                websockets_b = await await redis_client.smembers(mapping_key_b)
                
                # Check for overlap
                overlap = set(websockets_a) & set(websockets_b)
                if overlap:
                    isolation_violations.append(
                        f"WebSocket overlap between users {user_id_a} and {user_id_b}: {overlap}"
                    )
        
        # Report isolation violations
        if isolation_violations:
            for violation in isolation_violations[:10]:  # Show first 10
                self.logger.error(f"CONCURRENT ISOLATION VIOLATION: {violation}")
            
            if len(isolation_violations) > 10:
                self.logger.error(f"... and {len(isolation_violations) - 10} more violations")
            
            raise AssertionError(f"Found {len(isolation_violations)} isolation violations after concurrent operations")
        
        # Report error summary if there were failures
        if failed_operations:
            error_summary = defaultdict(int)
            for failed_op in failed_operations:
                error_type = failed_op.get("error", "unknown")[:50]  # First 50 chars
                error_summary[error_type] += 1
            
            self.logger.warning(f"Failed operation error summary:")
            for error_type, count in error_summary.items():
                self.logger.warning(f"  {error_type}: {count} occurrences")
        
        self.logger.info(f"Concurrent WebSocket operations isolation verified successfully")
        await await redis_client.close()

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_connection_lifecycle_with_authentication_cleanup(self, real_services_fixture, isolated_env):
        """Test complete WebSocket connection lifecycle with proper authentication and cleanup."""
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        # Setup Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup authenticated user for lifecycle testing
        auth_helper = E2EAuthHelper()
        user_data = await auth_helper.create_authenticated_test_user(
            email="lifecycle.cleanup@test.com",
            name="Lifecycle Cleanup Test User",
            password="securepassword123"
        )
        
        user_id = ensure_user_id(user_data["user_id"])
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        # Test multiple WebSocket lifecycles concurrently
        lifecycle_websockets = []
        lifecycle_count = 8
        
        for i in range(lifecycle_count):
            websocket_id = ensure_websocket_id(f"lifecycle_{i}_{generate_websocket_id()}")
            lifecycle_websockets.append(websocket_id)
        
        async def simulate_authenticated_websocket_lifecycle(websocket_id: WebSocketID, lifecycle_index: int):
            """Simulate complete authenticated WebSocket lifecycle with proper cleanup."""
            lifecycle_log = []
            
            try:
                # Phase 1: Connection establishment with authentication
                user_context = UserExecutionContext(
                    user_id=str(user_id),
                    thread_id=str(thread_id),
                    run_id=f"lifecycle_{lifecycle_index}_{uuid.uuid4()}",
                    session_id=user_data["session_id"],
                    auth_token=user_data["access_token"],
                    permissions=user_data.get("permissions", [])
                )
                
                connection_info = {
                    "websocket_id": str(websocket_id),
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "session_id": user_data["session_id"],
                    "auth_token_hash": hashlib.sha256(user_data["access_token"].encode()).hexdigest()[:16],
                    "connected_at": datetime.utcnow().isoformat(),
                    "connection_state": ConnectionState.CONNECTING.value,
                    "lifecycle_test": True,
                    "lifecycle_index": lifecycle_index
                }
                
                # Store connection with all mappings
                pipe = await redis_client.pipeline()
                connection_key = f"websocket:connection:{websocket_id}"
                pipe.hset(connection_key, mapping=connection_info)
                pipe.sadd(f"websocket:thread_mapping:{thread_id}", str(websocket_id))
                pipe.sadd(f"websocket:user_mapping:{user_id}", str(websocket_id))
                pipe.sadd(f"websocket:auth_mapping:{user_data['session_id']}", str(websocket_id))
                pipe.expire(connection_key, 3600)  # 1 hour expiration
                await pipe.execute()
                
                lifecycle_log.append("connecting")
                
                # Phase 2: Active connection with message activity
                await await redis_client.hset(connection_key, "connection_state", ConnectionState.CONNECTED.value)
                await await redis_client.hset(connection_key, "last_activity", datetime.utcnow().isoformat())
                lifecycle_log.append("connected")
                
                # Simulate message activity
                for msg_idx in range(3):
                    message_data = {
                        "message_id": str(uuid.uuid4()),
                        "websocket_id": str(websocket_id),
                        "content": f"Lifecycle message {msg_idx}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    message_key = f"websocket:pending_message:{websocket_id}"
                    await await redis_client.lpush(message_key, json.dumps(message_data))
                    await await redis_client.expire(message_key, 300)
                
                lifecycle_log.append("active_messaging")
                
                # Simulate connection activity time
                await asyncio.sleep(0.1)
                
                # Phase 3: Disconnection initiated
                await await redis_client.hset(connection_key, "connection_state", ConnectionState.DISCONNECTING.value)
                await await redis_client.hset(connection_key, "disconnect_initiated_at", datetime.utcnow().isoformat())
                lifecycle_log.append("disconnecting")
                
                # Phase 4: Complete cleanup
                # Remove from all mappings
                pipe = await redis_client.pipeline()
                pipe.srem(f"websocket:thread_mapping:{thread_id}", str(websocket_id))
                pipe.srem(f"websocket:user_mapping:{user_id}", str(websocket_id))
                pipe.srem(f"websocket:auth_mapping:{user_data['session_id']}", str(websocket_id))
                
                # Clean up connection record
                pipe.hset(connection_key, "connection_state", ConnectionState.DISCONNECTED.value)
                pipe.hset(connection_key, "disconnected_at", datetime.utcnow().isoformat())
                pipe.expire(connection_key, 60)  # Keep for 1 minute for audit, then auto-delete
                
                # Clean up message queues
                message_key = f"websocket:pending_message:{websocket_id}"
                pipe.delete(message_key)
                
                await pipe.execute()
                lifecycle_log.append("cleaned_up")
                
                return {
                    "websocket_id": str(websocket_id),
                    "lifecycle_index": lifecycle_index,
                    "status": "completed",
                    "lifecycle_log": lifecycle_log,
                    "phases_completed": len(lifecycle_log)
                }
                
            except Exception as e:
                return {
                    "websocket_id": str(websocket_id),
                    "lifecycle_index": lifecycle_index,
                    "status": "error",
                    "error": str(e),
                    "lifecycle_log": lifecycle_log,
                    "phases_completed": len(lifecycle_log)
                }
        
        # Run all lifecycle simulations concurrently
        self.logger.info(f"Running {lifecycle_count} concurrent WebSocket lifecycle simulations with authentication")
        lifecycle_start = time.time()
        
        lifecycle_results = await asyncio.gather(*[
            simulate_authenticated_websocket_lifecycle(ws_id, i) 
            for i, ws_id in enumerate(lifecycle_websockets)
        ])
        
        lifecycle_duration = time.time() - lifecycle_start
        
        # Analyze lifecycle results
        successful_lifecycles = [r for r in lifecycle_results if r["status"] == "completed"]
        failed_lifecycles = [r for r in lifecycle_results if r["status"] == "error"]
        
        success_rate = len(successful_lifecycles) / len(lifecycle_results)
        lifecycles_per_second = len(lifecycle_results) / lifecycle_duration
        
        # Require high success rate for lifecycle operations
        assert success_rate >= 0.90, f"Lifecycle success rate too low: {success_rate:.1%} (need 90%+)"
        
        # Verify all successful lifecycles completed all phases
        for result in successful_lifecycles:
            expected_phases = ["connecting", "connected", "active_messaging", "disconnecting", "cleaned_up"]
            actual_phases = result["lifecycle_log"]
            
            if actual_phases != expected_phases:
                raise AssertionError(
                    f"WebSocket {result['websocket_id']} lifecycle incomplete: {actual_phases} != {expected_phases}"
                )
        
        # Verify cleanup effectiveness - no lingering state
        cleanup_violations = []
        
        # Check thread mappings are clean
        thread_mapping_key = f"websocket:thread_mapping:{thread_id}"
        remaining_thread_websockets = await await redis_client.smembers(thread_mapping_key)
        
        successful_websocket_ids = {r["websocket_id"] for r in successful_lifecycles}
        lingering_in_thread = set(remaining_thread_websockets) & successful_websocket_ids
        
        if lingering_in_thread:
            cleanup_violations.append(f"Thread mapping not cleaned: {lingering_in_thread} websockets remain")
        
        # Check user mappings are clean
        user_mapping_key = f"websocket:user_mapping:{user_id}"
        remaining_user_websockets = await await redis_client.smembers(user_mapping_key)
        
        lingering_in_user = set(remaining_user_websockets) & successful_websocket_ids
        if lingering_in_user:
            cleanup_violations.append(f"User mapping not cleaned: {lingering_in_user} websockets remain")
        
        # Check auth mappings are clean
        auth_mapping_key = f"websocket:auth_mapping:{user_data['session_id']}"
        remaining_auth_websockets = await await redis_client.smembers(auth_mapping_key)
        
        lingering_in_auth = set(remaining_auth_websockets) & successful_websocket_ids
        if lingering_in_auth:
            cleanup_violations.append(f"Auth mapping not cleaned: {lingering_in_auth} websockets remain")
        
        # Check for orphaned message queues
        orphaned_message_queues = []
        for websocket_id in successful_websocket_ids:
            message_key = f"websocket:pending_message:{websocket_id}"
            if await await redis_client.exists(message_key):
                orphaned_message_queues.append(websocket_id)
        
        if orphaned_message_queues:
            cleanup_violations.append(f"Orphaned message queues: {orphaned_message_queues}")
        
        # Report cleanup violations
        if cleanup_violations:
            for violation in cleanup_violations:
                self.logger.error(f"CLEANUP VIOLATION: {violation}")
            raise AssertionError(f"Found {len(cleanup_violations)} cleanup violations")
        
        # Test rapid connect/disconnect cycles for stress testing
        rapid_cycle_websocket = ensure_websocket_id(f"rapid_{generate_websocket_id()}")
        rapid_cycles = 20
        rapid_cycle_violations = []
        
        for cycle in range(rapid_cycles):
            cycle_start = time.time()
            
            # Quick connect with authentication
            connection_info = {
                "websocket_id": str(rapid_cycle_websocket),
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "session_id": user_data["session_id"],
                "cycle": cycle,
                "connection_state": ConnectionState.CONNECTED.value,
                "rapid_cycle_test": True
            }
            
            # Atomic connect
            pipe = await redis_client.pipeline()
            connection_key = f"websocket:connection:{rapid_cycle_websocket}"
            pipe.hset(connection_key, mapping=connection_info)
            pipe.sadd(f"websocket:thread_mapping:{thread_id}", str(rapid_cycle_websocket))
            pipe.sadd(f"websocket:user_mapping:{user_id}", str(rapid_cycle_websocket))
            await pipe.execute()
            
            # Quick disconnect and cleanup
            pipe = await redis_client.pipeline()
            pipe.srem(f"websocket:thread_mapping:{thread_id}", str(rapid_cycle_websocket))
            pipe.srem(f"websocket:user_mapping:{user_id}", str(rapid_cycle_websocket))
            pipe.delete(connection_key)
            await pipe.execute()
            
            cycle_duration = time.time() - cycle_start
            
            # Verify clean state between cycles
            if await await redis_client.exists(connection_key):
                rapid_cycle_violations.append(f"Connection record not cleaned in cycle {cycle}")
            
            thread_websockets = await await redis_client.smembers(f"websocket:thread_mapping:{thread_id}")
            if str(rapid_cycle_websocket) in thread_websockets:
                rapid_cycle_violations.append(f"Thread mapping not cleaned in cycle {cycle}")
            
            user_websockets = await await redis_client.smembers(f"websocket:user_mapping:{user_id}")
            if str(rapid_cycle_websocket) in user_websockets:
                rapid_cycle_violations.append(f"User mapping not cleaned in cycle {cycle}")
            
            # Performance check - cycle should be fast
            if cycle_duration > 0.1:  # 100ms max per cycle
                rapid_cycle_violations.append(f"Cycle {cycle} too slow: {cycle_duration*1000:.2f}ms")
        
        if rapid_cycle_violations:
            for violation in rapid_cycle_violations[:5]:  # Show first 5
                self.logger.error(f"RAPID CYCLE VIOLATION: {violation}")
            raise AssertionError(f"Found {len(rapid_cycle_violations)} rapid cycle violations")
        
        # Log performance metrics
        self.logger.info(f"WebSocket lifecycle performance:")
        self.logger.info(f"  Success rate: {success_rate:.1%} ({len(successful_lifecycles)}/{len(lifecycle_results)})")
        self.logger.info(f"  Lifecycles/sec: {lifecycles_per_second:.2f}")
        self.logger.info(f"  Rapid cycles: {rapid_cycles} completed successfully")
        self.logger.info(f"  Total duration: {lifecycle_duration:.2f}s")
        
        # Report any failures
        if failed_lifecycles:
            self.logger.warning(f"Failed lifecycles ({len(failed_lifecycles)}):")
            for failed in failed_lifecycles:
                self.logger.warning(f"  WebSocket {failed['websocket_id']}: {failed.get('error', 'unknown error')}")
        
        self.logger.info("WebSocket connection lifecycle with authentication cleanup verified successfully")
        await await redis_client.close()


# Helper import for token hashing
import hashlib