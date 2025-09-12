"""
Test WebSocket User-Specific State Isolation Across Events and Database Operations Integration (#23)

Business Value Justification (BVJ):
- Segment: All (Foundation of multi-user system integrity)
- Business Goal: Ensure user-specific state is never corrupted by WebSocket events or database operations
- Value Impact: Users see only their own data and state changes in real-time
- Strategic Impact: Core system reliability - prevents data corruption and enables user trust

CRITICAL REQUIREMENT: User-specific state must remain perfectly isolated across all layers:
WebSocket events, database transactions, cache operations, and real-time notifications.
Any state bleeding between users is a critical security and reliability violation.
"""

import asyncio
import pytest
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions
UserID = str
StateID = str
EventID = str
TransactionID = str


class UserStateEventType(Enum):
    """Types of user state events that can occur."""
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    THREAD_CREATED = "thread_created" 
    THREAD_UPDATED = "thread_updated"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_TERMINATED = "connection_terminated"
    STATE_SYNCHRONIZED = "state_synchronized"
    CACHE_UPDATED = "cache_updated"


@dataclass
class UserStateSnapshot:
    """Complete snapshot of user state across all layers."""
    user_id: UserID
    snapshot_timestamp: float
    database_state: Dict[str, Any] = field(default_factory=dict)
    cache_state: Dict[str, Any] = field(default_factory=dict)
    websocket_state: Dict[str, Any] = field(default_factory=dict)
    event_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "snapshot_timestamp": self.snapshot_timestamp,
            "database_state": self.database_state,
            "cache_state": self.cache_state,
            "websocket_state": self.websocket_state,
            "event_history": self.event_history
        }


@dataclass
class UserStateOperation:
    """Represents a state operation that should be isolated."""
    operation_id: str
    user_id: UserID
    operation_type: UserStateEventType
    operation_data: Dict[str, Any]
    expected_side_effects: List[str]
    forbidden_side_effects: List[str]  # Side effects that must NOT occur
    timestamp: float = field(default_factory=time.time)


class UserStateIsolationValidator:
    """Validates user-specific state isolation across WebSocket events and database operations."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.user_state_snapshots = {}
        self.operation_log = []
        self.isolation_violations = []
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_isolated_user_with_state(self, user_suffix: str) -> Tuple[UserID, Dict[str, Any]]:
        """Create user with initial isolated state across all layers."""
        user_id = f"state-test-user-{user_suffix}"
        
        # Create user in database with initial state
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@state-test.com", f"State Test User {user_suffix}", True)
        
        # Create user's threads and messages
        thread_ids = []
        message_ids = []
        
        for i in range(2):
            thread_id = f"thread-{user_suffix}-{i}"
            await self.real_services["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    title = EXCLUDED.title,
                    updated_at = NOW()
            """, thread_id, user_id, f"State Test Thread {i}")
            thread_ids.append(thread_id)
            
            # Add messages to thread
            for j in range(3):
                message_id = f"msg-{user_suffix}-{i}-{j}"
                await self.real_services["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                """, message_id, thread_id, user_id, f"State test message {j}", "user")
                message_ids.append(message_id)
        
        # Initialize user state in Redis cache
        user_cache_data = {
            "user_id": user_id,
            "thread_ids": thread_ids,
            "message_ids": message_ids,
            "last_activity": time.time(),
            "connection_count": 0,
            "state_version": 1,
            "isolated_namespace": f"user:{user_id}"
        }
        
        await self.redis_client.set(
            f"user_state:{user_id}",
            json.dumps(user_cache_data),
            ex=3600
        )
        
        # Initialize WebSocket connection state
        connection_id = f"ws-{user_id}-{uuid.uuid4().hex[:8]}"
        ws_state_data = {
            "user_id": user_id,
            "connection_id": connection_id,
            "state": WebSocketConnectionState.CONNECTED,
            "active_threads": thread_ids,
            "event_subscriptions": [
                UserStateEventType.MESSAGE_SENT.value,
                UserStateEventType.THREAD_UPDATED.value,
                UserStateEventType.AGENT_STARTED.value
            ]
        }
        
        await self.redis_client.set(
            f"ws_state:{connection_id}",
            json.dumps(ws_state_data),
            ex=3600
        )
        
        initial_state = {
            "user_id": user_id,
            "thread_ids": thread_ids,
            "message_ids": message_ids,
            "connection_id": connection_id,
            "cache_keys": [f"user_state:{user_id}", f"ws_state:{connection_id}"]
        }
        
        return user_id, initial_state
    
    async def capture_user_state_snapshot(self, user_id: UserID, label: str = None) -> UserStateSnapshot:
        """Capture complete user state snapshot across all layers."""
        snapshot = UserStateSnapshot(
            user_id=user_id,
            snapshot_timestamp=time.time()
        )
        
        # Capture database state
        threads = await self.real_services["db"].fetch("""
            SELECT id, title, created_at, updated_at FROM backend.threads
            WHERE user_id = $1 ORDER BY created_at
        """, user_id)
        
        messages = await self.real_services["db"].fetch("""
            SELECT id, thread_id, content, role, created_at FROM backend.messages
            WHERE user_id = $1 ORDER BY created_at
        """, user_id)
        
        snapshot.database_state = {
            "threads": [dict(t) for t in threads],
            "messages": [dict(m) for m in messages],
            "thread_count": len(threads),
            "message_count": len(messages)
        }
        
        # Capture cache state
        user_cache_key = f"user_state:{user_id}"
        cache_data = await self.redis_client.get(user_cache_key)
        if cache_data:
            snapshot.cache_state = json.loads(cache_data)
        
        # Capture WebSocket states for this user
        ws_keys = await self.redis_client.keys(f"ws_state:*{user_id}*")
        ws_states = {}
        for key in ws_keys:
            ws_data = await self.redis_client.get(key)
            if ws_data:
                ws_states[key.decode()] = json.loads(ws_data)
        
        snapshot.websocket_state = ws_states
        
        # Store snapshot
        snapshot_key = f"snapshot:{user_id}:{label or 'default'}:{int(time.time())}"
        self.user_state_snapshots[snapshot_key] = snapshot
        
        return snapshot
    
    async def execute_user_state_operation(self, operation: UserStateOperation) -> Dict[str, Any]:
        """Execute a user state operation and track its effects."""
        operation_start_time = time.time()
        
        # Capture pre-operation state
        pre_snapshot = await self.capture_user_state_snapshot(operation.user_id, f"pre_{operation.operation_id}")
        
        operation_result = {
            "operation_id": operation.operation_id,
            "user_id": operation.user_id,
            "operation_type": operation.operation_type.value,
            "success": False,
            "error": None,
            "duration_ms": 0,
            "side_effects_detected": [],
            "isolation_maintained": True
        }
        
        try:
            # Execute the operation based on type
            if operation.operation_type == UserStateEventType.MESSAGE_SENT:
                await self._execute_message_sent_operation(operation)
            elif operation.operation_type == UserStateEventType.THREAD_CREATED:
                await self._execute_thread_created_operation(operation)
            elif operation.operation_type == UserStateEventType.AGENT_STARTED:
                await self._execute_agent_started_operation(operation)
            elif operation.operation_type == UserStateEventType.STATE_SYNCHRONIZED:
                await self._execute_state_sync_operation(operation)
            else:
                raise ValueError(f"Unsupported operation type: {operation.operation_type}")
            
            operation_result["success"] = True
            
        except Exception as e:
            operation_result["error"] = str(e)
            
        operation_result["duration_ms"] = (time.time() - operation_start_time) * 1000
        
        # Capture post-operation state
        post_snapshot = await self.capture_user_state_snapshot(operation.user_id, f"post_{operation.operation_id}")
        
        # Analyze side effects and isolation
        isolation_analysis = await self._analyze_operation_isolation(operation, pre_snapshot, post_snapshot)
        operation_result.update(isolation_analysis)
        
        self.operation_log.append(operation_result)
        return operation_result
    
    async def _execute_message_sent_operation(self, operation: UserStateOperation):
        """Execute message sent operation."""
        message_data = operation.operation_data
        message_id = f"msg-{operation.operation_id}"
        
        # Insert message into database
        await self.real_services["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
        """, message_id, message_data["thread_id"], operation.user_id, message_data["content"], "user")
        
        # Update cache
        user_cache_key = f"user_state:{operation.user_id}"
        cache_data = await self.redis_client.get(user_cache_key)
        if cache_data:
            user_cache = json.loads(cache_data)
            user_cache["message_ids"].append(message_id)
            user_cache["last_activity"] = time.time()
            user_cache["state_version"] += 1
            await self.redis_client.set(user_cache_key, json.dumps(user_cache), ex=3600)
        
        # Simulate WebSocket event emission
        event_data = {
            "type": "message_sent",
            "user_id": operation.user_id,
            "message_id": message_id,
            "thread_id": message_data["thread_id"],
            "timestamp": time.time()
        }
        
        await self.redis_client.publish(f"user_events:{operation.user_id}", json.dumps(event_data))
    
    async def _execute_thread_created_operation(self, operation: UserStateOperation):
        """Execute thread created operation."""
        thread_data = operation.operation_data
        thread_id = f"thread-{operation.operation_id}"
        
        # Create thread in database
        await self.real_services["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, NOW())
        """, thread_id, operation.user_id, thread_data["title"])
        
        # Update user cache
        user_cache_key = f"user_state:{operation.user_id}"
        cache_data = await self.redis_client.get(user_cache_key)
        if cache_data:
            user_cache = json.loads(cache_data)
            user_cache["thread_ids"].append(thread_id)
            user_cache["state_version"] += 1
            await self.redis_client.set(user_cache_key, json.dumps(user_cache), ex=3600)
    
    async def _execute_agent_started_operation(self, operation: UserStateOperation):
        """Execute agent started operation."""
        agent_data = operation.operation_data
        
        # Update WebSocket state to reflect agent activity
        ws_keys = await self.redis_client.keys(f"ws_state:*{operation.user_id}*")
        for key in ws_keys:
            ws_data = await self.redis_client.get(key)
            if ws_data:
                ws_state = json.loads(ws_data)
                ws_state["active_agent"] = agent_data.get("agent_type", "unknown")
                ws_state["agent_started_at"] = time.time()
                await self.redis_client.set(key, json.dumps(ws_state), ex=3600)
    
    async def _execute_state_sync_operation(self, operation: UserStateOperation):
        """Execute state synchronization operation."""
        # Simulate comprehensive state sync across layers
        user_cache_key = f"user_state:{operation.user_id}"
        cache_data = await self.redis_client.get(user_cache_key)
        
        if cache_data:
            user_cache = json.loads(cache_data)
            user_cache["last_sync"] = time.time()
            user_cache["sync_version"] = user_cache.get("sync_version", 0) + 1
            await self.redis_client.set(user_cache_key, json.dumps(user_cache), ex=3600)
    
    async def _analyze_operation_isolation(self, operation: UserStateOperation, 
                                          pre_snapshot: UserStateSnapshot, 
                                          post_snapshot: UserStateSnapshot) -> Dict[str, Any]:
        """Analyze whether operation maintained proper user isolation."""
        isolation_analysis = {
            "isolation_maintained": True,
            "side_effects_detected": [],
            "isolation_violations": []
        }
        
        # Check if operation affected other users' data
        other_users = await self.real_services["db"].fetch("""
            SELECT DISTINCT user_id FROM auth.users WHERE user_id != $1 AND user_id LIKE 'state-test-user-%'
        """, operation.user_id)
        
        for other_user in other_users:
            other_user_id = other_user["user_id"]
            
            # Check if other user's cache was modified
            other_cache_key = f"user_state:{other_user_id}"
            other_cache_data = await self.redis_client.get(other_cache_key)
            
            if other_cache_data:
                other_cache = json.loads(other_cache_data)
                
                # If other user's cache was updated recently (within operation timeframe)
                if other_cache.get("last_activity", 0) > operation.timestamp:
                    violation = {
                        "type": "cross_user_cache_modification",
                        "affected_user": other_user_id,
                        "operation_user": operation.user_id,
                        "operation_type": operation.operation_type.value
                    }
                    isolation_analysis["isolation_violations"].append(violation)
                    isolation_analysis["isolation_maintained"] = False
        
        return isolation_analysis
    
    async def validate_multi_user_state_isolation(self, user_operations: List[List[UserStateOperation]]) -> Dict[str, Any]:
        """Validate state isolation across multiple users executing operations concurrently."""
        validation_results = {
            "total_users": len(user_operations),
            "total_operations": sum(len(ops) for ops in user_operations),
            "isolation_maintained": True,
            "violations": [],
            "user_results": {}
        }
        
        # Execute operations for all users concurrently
        async def execute_user_operations(user_ops: List[UserStateOperation]) -> List[Dict[str, Any]]:
            results = []
            for operation in user_ops:
                result = await self.execute_user_state_operation(operation)
                results.append(result)
                # Small delay between operations
                await asyncio.sleep(0.01)
            return results
        
        # Run all user operation sequences concurrently
        concurrent_tasks = [
            execute_user_operations(user_ops) for user_ops in user_operations
        ]
        
        user_results_list = await asyncio.gather(*concurrent_tasks)
        
        # Analyze results for isolation violations
        for i, user_results in enumerate(user_results_list):
            user_id = user_operations[i][0].user_id if user_operations[i] else f"user_{i}"
            validation_results["user_results"][user_id] = user_results
            
            # Check for isolation violations in this user's operations
            for result in user_results:
                if not result.get("isolation_maintained", True):
                    validation_results["violations"].extend(result.get("isolation_violations", []))
                    validation_results["isolation_maintained"] = False
        
        return validation_results


class TestWebSocketUserStateIsolation(BaseIntegrationTest):
    """
    Integration test for user-specific state isolation across WebSocket events and database operations.
    
    CRITICAL: Validates that user state remains isolated during concurrent operations
    across all system layers (database, cache, WebSocket).
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.isolation_critical
    async def test_user_state_isolation_across_websocket_database_operations(self, real_services_fixture):
        """
        Test user state isolation during concurrent WebSocket events and database operations.
        
        CRITICAL: User-specific state must never be corrupted or mixed between users.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = UserStateIsolationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple users with isolated state
            users_with_state = []
            for i in range(3):
                user_id, initial_state = await validator.create_isolated_user_with_state(f"isolation-{i}")
                users_with_state.append((user_id, initial_state))
            
            # Create concurrent operations for each user
            user_operations = []
            for i, (user_id, state) in enumerate(users_with_state):
                operations = [
                    UserStateOperation(
                        operation_id=f"msg_op_{i}_1",
                        user_id=user_id,
                        operation_type=UserStateEventType.MESSAGE_SENT,
                        operation_data={
                            "thread_id": state["thread_ids"][0],
                            "content": f"Isolated message from user {i}"
                        },
                        expected_side_effects=["message_created", "cache_updated"],
                        forbidden_side_effects=["other_user_cache_modified"]
                    ),
                    UserStateOperation(
                        operation_id=f"thread_op_{i}_1",
                        user_id=user_id,
                        operation_type=UserStateEventType.THREAD_CREATED,
                        operation_data={
                            "title": f"New isolated thread for user {i}"
                        },
                        expected_side_effects=["thread_created", "user_state_updated"],
                        forbidden_side_effects=["other_user_thread_created"]
                    ),
                    UserStateOperation(
                        operation_id=f"agent_op_{i}_1",
                        user_id=user_id,
                        operation_type=UserStateEventType.AGENT_STARTED,
                        operation_data={
                            "agent_type": "test_agent"
                        },
                        expected_side_effects=["websocket_state_updated"],
                        forbidden_side_effects=["other_user_agent_started"]
                    )
                ]
                user_operations.append(operations)
            
            # Execute all operations concurrently
            isolation_results = await validator.validate_multi_user_state_isolation(user_operations)
            
            # CRITICAL ASSERTIONS: State isolation must be maintained
            assert isolation_results["isolation_maintained"], \
                f"State isolation violated: {isolation_results['violations']}"
            assert len(isolation_results["violations"]) == 0, \
                f"Isolation violations detected: {isolation_results['violations']}"
            assert isolation_results["total_users"] == 3
            assert isolation_results["total_operations"] == 9
            
            # Verify each user's operations completed successfully
            for user_id, user_results in isolation_results["user_results"].items():
                assert len(user_results) == 3, f"User {user_id} should have 3 operations"
                for result in user_results:
                    assert result["success"], f"Operation failed for user {user_id}: {result}"
                    assert result["isolation_maintained"], f"Isolation violated for user {user_id}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrency
    async def test_concurrent_state_modifications_isolation(self, real_services_fixture):
        """Test state isolation during rapid concurrent state modifications."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = UserStateIsolationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users for concurrent state testing
            users_with_state = []
            for i in range(2):
                user_id, initial_state = await validator.create_isolated_user_with_state(f"concurrent-{i}")
                users_with_state.append((user_id, initial_state))
            
            # Create rapid state modification operations
            user_operations = []
            for i, (user_id, state) in enumerate(users_with_state):
                rapid_operations = []
                for j in range(5):  # 5 rapid operations per user
                    operations = [
                        UserStateOperation(
                            operation_id=f"rapid_msg_{i}_{j}",
                            user_id=user_id,
                            operation_type=UserStateEventType.MESSAGE_SENT,
                            operation_data={
                                "thread_id": state["thread_ids"][0],
                                "content": f"Rapid message {j} from user {i}"
                            },
                            expected_side_effects=["message_created"],
                            forbidden_side_effects=["other_user_affected"]
                        ),
                        UserStateOperation(
                            operation_id=f"rapid_sync_{i}_{j}",
                            user_id=user_id,
                            operation_type=UserStateEventType.STATE_SYNCHRONIZED,
                            operation_data={},
                            expected_side_effects=["state_synced"],
                            forbidden_side_effects=["other_user_sync_affected"]
                        )
                    ]
                    rapid_operations.extend(operations)
                user_operations.append(rapid_operations)
            
            # Execute rapid concurrent modifications
            rapid_results = await validator.validate_multi_user_state_isolation(user_operations)
            
            # Verify isolation maintained during rapid modifications
            assert rapid_results["isolation_maintained"], \
                f"Rapid modifications violated isolation: {rapid_results['violations']}"
            assert rapid_results["total_operations"] == 20  # 2 users  x  5 batches  x  2 operations
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.websocket_critical
    async def test_websocket_event_state_isolation(self, real_services_fixture):
        """Test that WebSocket events maintain user state isolation."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = UserStateIsolationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users for WebSocket event testing
            user_id_1, state_1 = await validator.create_isolated_user_with_state("ws-event-1")
            user_id_2, state_2 = await validator.create_isolated_user_with_state("ws-event-2")
            
            # Capture initial state snapshots
            initial_snapshot_1 = await validator.capture_user_state_snapshot(user_id_1, "initial")
            initial_snapshot_2 = await validator.capture_user_state_snapshot(user_id_2, "initial")
            
            # Execute WebSocket-related operations for both users simultaneously
            ws_operations = [
                [UserStateOperation(
                    operation_id="ws_msg_1",
                    user_id=user_id_1,
                    operation_type=UserStateEventType.MESSAGE_SENT,
                    operation_data={
                        "thread_id": state_1["thread_ids"][0],
                        "content": "WebSocket message from user 1"
                    },
                    expected_side_effects=["websocket_event_emitted"],
                    forbidden_side_effects=["user_2_affected"]
                )],
                [UserStateOperation(
                    operation_id="ws_msg_2",
                    user_id=user_id_2,
                    operation_type=UserStateEventType.MESSAGE_SENT,
                    operation_data={
                        "thread_id": state_2["thread_ids"][0],
                        "content": "WebSocket message from user 2"
                    },
                    expected_side_effects=["websocket_event_emitted"],
                    forbidden_side_effects=["user_1_affected"]
                )]
            ]
            
            # Execute WebSocket operations concurrently
            ws_results = await validator.validate_multi_user_state_isolation(ws_operations)
            
            # Verify WebSocket events maintained isolation
            assert ws_results["isolation_maintained"], \
                f"WebSocket events violated isolation: {ws_results['violations']}"
            
            # Capture final state snapshots and verify no cross-contamination
            final_snapshot_1 = await validator.capture_user_state_snapshot(user_id_1, "final")
            final_snapshot_2 = await validator.capture_user_state_snapshot(user_id_2, "final")
            
            # User 1's message count should increase by 1, user 2's should be unchanged by user 1's operation
            initial_msg_count_1 = len(initial_snapshot_1.database_state["messages"])
            final_msg_count_1 = len(final_snapshot_1.database_state["messages"])
            
            initial_msg_count_2 = len(initial_snapshot_2.database_state["messages"])
            final_msg_count_2 = len(final_snapshot_2.database_state["messages"])
            
            assert final_msg_count_1 == initial_msg_count_1 + 1, "User 1 should have 1 additional message"
            assert final_msg_count_2 == initial_msg_count_2 + 1, "User 2 should have 1 additional message"
            
            # Verify messages are in correct user contexts
            user_1_messages = [msg for msg in final_snapshot_1.database_state["messages"] 
                              if "user 1" in msg["content"]]
            user_2_messages = [msg for msg in final_snapshot_2.database_state["messages"] 
                              if "user 2" in msg["content"]]
            
            assert len(user_1_messages) == 1, "User 1 should have exactly 1 new message"
            assert len(user_2_messages) == 1, "User 2 should have exactly 1 new message"
            
        finally:
            await validator.cleanup()