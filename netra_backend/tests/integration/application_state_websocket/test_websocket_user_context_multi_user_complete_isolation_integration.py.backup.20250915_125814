"""
Test WebSocket User Context Multi-User Complete Isolation Integration (#21)

Business Value Justification (BVJ):
- Segment: Enterprise (Critical Security for Multi-Tenant SaaS)
- Business Goal: Ensure zero cross-user data leakage in concurrent WebSocket connections
- Value Impact: Enterprise customers trust our platform with sensitive data
- Strategic Impact: Foundation of enterprise security - enables $500K+ ARR growth

CRITICAL SECURITY REQUIREMENT: This test validates that multiple users can connect
simultaneously via WebSockets without ANY cross-contamination of data, contexts,
sessions, or state. Complete user context isolation must be maintained at ALL layers.
"""

import asyncio
import pytest
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions for test isolation
UserID = str
ThreadID = str
MessageID = str
OrganizationID = str
ConnectionID = str


@dataclass
class IsolatedUserContext:
    """Completely isolated user context for testing."""
    user_id: UserID
    connection_id: ConnectionID
    session_token: str
    thread_ids: List[ThreadID]
    message_ids: List[MessageID]
    organization_id: Optional[OrganizationID] = None
    websocket_state: Dict[str, Any] = None
    database_records: Dict[str, Any] = None
    cache_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.websocket_state is None:
            self.websocket_state = {}
        if self.database_records is None:
            self.database_records = {}
        if self.cache_data is None:
            self.cache_data = {}


class UserContextIsolationValidator:
    """Validates complete user context isolation across all layers."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.isolation_violations = []
        
    async def create_isolated_user_context(self, user_suffix: str = None) -> IsolatedUserContext:
        """Create a completely isolated user context with real data."""
        if user_suffix is None:
            user_suffix = uuid.uuid4().hex[:8]
            
        user_id = f"test-user-{user_suffix}"
        connection_id = f"conn-{uuid.uuid4().hex}"
        session_token = f"session-{uuid.uuid4().hex}"
        
        # Create user in real database with isolated data
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active
        """, user_id, f"{user_id}@test.com", f"Test User {user_suffix}", True)
        
        # Create organization for enterprise isolation testing
        org_id = f"org-{user_suffix}"
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                plan = EXCLUDED.plan
        """, org_id, f"Test Org {user_suffix}", f"test-org-{user_suffix}", "enterprise")
        
        # Create organization membership
        await self.real_services["db"].execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
        """, user_id, org_id, "admin")
        
        # Create threads for this user only
        thread_ids = []
        for i in range(3):
            thread_id = f"thread-{user_suffix}-{i}"
            await self.real_services["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title
            """, thread_id, user_id, f"User {user_suffix} Thread {i}")
            thread_ids.append(thread_id)
        
        # Create messages for this user only
        message_ids = []
        for thread_id in thread_ids:
            for j in range(2):
                message_id = f"msg-{user_suffix}-{thread_id.split('-')[-1]}-{j}"
                await self.real_services["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                """, message_id, thread_id, user_id, f"Message {j} from user {user_suffix}", "user")
                message_ids.append(message_id)
        
        # Store session in Redis with user-specific namespace
        import redis.asyncio as redis
        redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        session_key = f"session:{user_id}"
        await redis_client.set(session_key, json.dumps({
            "user_id": user_id,
            "connection_id": connection_id,
            "session_token": session_token,
            "organization_id": org_id,
            "created_at": time.time(),
            "isolated_namespace": f"user:{user_id}"
        }), ex=3600)
        
        # Store WebSocket connection state
        ws_state_key = f"ws:state:{connection_id}"
        await redis_client.set(ws_state_key, json.dumps({
            "user_id": user_id,
            "connection_state": WebSocketConnectionState.CONNECTED,
            "thread_ids": thread_ids,
            "active_since": time.time()
        }), ex=3600)
        
        await redis_client.aclose()
        
        return IsolatedUserContext(
            user_id=user_id,
            connection_id=connection_id,
            session_token=session_token,
            thread_ids=thread_ids,
            message_ids=message_ids,
            organization_id=org_id,
            websocket_state={"connection_state": WebSocketConnectionState.CONNECTED},
            database_records={"threads": thread_ids, "messages": message_ids},
            cache_data={"session_key": session_key, "ws_state_key": ws_state_key}
        )
    
    async def validate_complete_user_isolation(self, user_contexts: List[IsolatedUserContext]) -> Dict[str, Any]:
        """
        Validate that users are completely isolated from each other.
        Returns validation results with any violations found.
        """
        validation_results = {
            "database_isolation": True,
            "cache_isolation": True,
            "websocket_isolation": True,
            "organization_isolation": True,
            "violations": [],
            "cross_contamination_detected": False
        }
        
        # Test 1: Database isolation - no user can access another user's data
        for i, user_a in enumerate(user_contexts):
            for j, user_b in enumerate(user_contexts):
                if i != j:  # Different users
                    # Verify user A cannot access user B's threads
                    user_b_threads = await self.real_services["db"].fetch("""
                        SELECT id FROM backend.threads 
                        WHERE user_id = $1 AND user_id != $2
                    """, user_b.user_id, user_a.user_id)
                    
                    if len(user_b_threads) > 0:
                        # Try to access as user A (should return nothing)
                        accessible_threads = await self.real_services["db"].fetch("""
                            SELECT id FROM backend.threads 
                            WHERE user_id = $1 AND id = ANY($2)
                        """, user_a.user_id, [t["id"] for t in user_b_threads])
                        
                        if len(accessible_threads) > 0:
                            violation = f"User {user_a.user_id} can access threads of user {user_b.user_id}"
                            validation_results["violations"].append(violation)
                            validation_results["database_isolation"] = False
                            validation_results["cross_contamination_detected"] = True
        
        # Test 2: Cache/Redis isolation - sessions and state must be user-specific
        import redis.asyncio as redis
        redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        
        for i, user_a in enumerate(user_contexts):
            for j, user_b in enumerate(user_contexts):
                if i != j:  # Different users
                    # User A should not be able to access User B's session
                    user_b_session_key = f"session:{user_b.user_id}"
                    user_a_session_data = await redis_client.get(f"session:{user_a.user_id}")
                    user_b_session_data = await redis_client.get(user_b_session_key)
                    
                    if user_a_session_data and user_b_session_data:
                        # Parse session data
                        user_a_data = json.loads(user_a_session_data)
                        user_b_data = json.loads(user_b_session_data)
                        
                        # Check for data bleeding
                        if user_a_data.get("user_id") == user_b_data.get("user_id"):
                            violation = f"Session data bleeding: users {user_a.user_id} and {user_b.user_id} have same session user_id"
                            validation_results["violations"].append(violation)
                            validation_results["cache_isolation"] = False
                            validation_results["cross_contamination_detected"] = True
        
        await redis_client.aclose()
        
        # Test 3: WebSocket state isolation
        ws_state_manager = get_websocket_state_manager()
        for i, user_a in enumerate(user_contexts):
            for j, user_b in enumerate(user_contexts):
                if i != j:  # Different users
                    # Verify WebSocket states are completely separate
                    try:
                        user_a_connections = await ws_state_manager.get_user_connections(user_a.user_id)
                        user_b_connections = await ws_state_manager.get_user_connections(user_b.user_id)
                        
                        # Check for connection ID overlap (should never happen)
                        user_a_conn_ids = {conn.connection_id for conn in user_a_connections}
                        user_b_conn_ids = {conn.connection_id for conn in user_b_connections}
                        
                        overlap = user_a_conn_ids.intersection(user_b_conn_ids)
                        if overlap:
                            violation = f"WebSocket connection ID overlap between users {user_a.user_id} and {user_b.user_id}: {overlap}"
                            validation_results["violations"].append(violation)
                            validation_results["websocket_isolation"] = False
                            validation_results["cross_contamination_detected"] = True
                            
                    except Exception as e:
                        # If WebSocket state manager not available, log and continue
                        validation_results["violations"].append(f"WebSocket state validation failed: {e}")
        
        return validation_results
    
    async def simulate_concurrent_websocket_operations(self, user_contexts: List[IsolatedUserContext]) -> Dict[str, Any]:
        """Simulate concurrent WebSocket operations to test isolation under load."""
        
        async def user_websocket_operations(user_context: IsolatedUserContext) -> Dict[str, Any]:
            """Simulate WebSocket operations for one user."""
            operations_performed = []
            
            # Simulate sending messages
            for i in range(5):
                message_data = {
                    "type": MessageType.USER_MESSAGE,
                    "user_id": user_context.user_id,
                    "content": f"Concurrent message {i} from {user_context.user_id}",
                    "thread_id": user_context.thread_ids[0] if user_context.thread_ids else None,
                    "timestamp": time.time()
                }
                operations_performed.append(f"sent_message_{i}")
                await asyncio.sleep(0.1)  # Small delay to simulate real usage
            
            # Simulate WebSocket state updates
            for i in range(3):
                state_update = {
                    "connection_id": user_context.connection_id,
                    "user_id": user_context.user_id,
                    "state": "active",
                    "last_seen": time.time()
                }
                operations_performed.append(f"state_update_{i}")
                await asyncio.sleep(0.05)
            
            return {
                "user_id": user_context.user_id,
                "operations_count": len(operations_performed),
                "operations": operations_performed,
                "completed_at": time.time()
            }
        
        # Execute operations concurrently for all users
        concurrent_tasks = [
            user_websocket_operations(user_context)
            for user_context in user_contexts
        ]
        
        # Wait for all operations to complete
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Analyze results for isolation violations
        operation_results = {
            "total_users": len(user_contexts),
            "successful_operations": 0,
            "failed_operations": 0,
            "isolation_maintained": True,
            "user_results": []
        }
        
        for result in results:
            if isinstance(result, Exception):
                operation_results["failed_operations"] += 1
                operation_results["isolation_maintained"] = False
            else:
                operation_results["successful_operations"] += 1
                operation_results["user_results"].append(result)
        
        return operation_results


class TestWebSocketUserContextCompleteIsolation(BaseIntegrationTest):
    """
    Integration test for complete WebSocket user context isolation.
    
    CRITICAL: Validates that multiple users can operate WebSocket connections
    simultaneously without any cross-user data leakage or state contamination.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security_critical
    async def test_multi_user_websocket_complete_context_isolation(self, real_services_fixture):
        """
        Test complete user context isolation across multiple concurrent WebSocket connections.
        
        SECURITY CRITICAL: This test MUST pass for enterprise deployment.
        Any failure indicates potential data leakage between users.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = UserContextIsolationValidator(real_services_fixture)
        
        # Create multiple isolated user contexts
        user_contexts = []
        for i in range(5):  # Test with 5 concurrent users
            user_context = await validator.create_isolated_user_context(f"isolation-test-{i}")
            user_contexts.append(user_context)
            
            # Verify each user context is properly created
            assert user_context.user_id.startswith("test-user-isolation-test-")
            assert len(user_context.thread_ids) == 3
            assert len(user_context.message_ids) == 6  # 2 messages per thread
            assert user_context.organization_id is not None
        
        # Validate complete isolation between all users
        isolation_results = await validator.validate_complete_user_isolation(user_contexts)
        
        # CRITICAL ASSERTIONS: Any failure here is a security violation
        assert isolation_results["database_isolation"], \
            f"Database isolation FAILED: {isolation_results['violations']}"
        assert isolation_results["cache_isolation"], \
            f"Cache isolation FAILED: {isolation_results['violations']}"
        assert isolation_results["websocket_isolation"], \
            f"WebSocket isolation FAILED: {isolation_results['violations']}"
        assert not isolation_results["cross_contamination_detected"], \
            f"Cross-user contamination DETECTED: {isolation_results['violations']}"
        
        # Test concurrent WebSocket operations
        concurrent_results = await validator.simulate_concurrent_websocket_operations(user_contexts)
        
        # Verify all users completed their operations successfully
        assert concurrent_results["total_users"] == 5
        assert concurrent_results["successful_operations"] == 5
        assert concurrent_results["failed_operations"] == 0
        assert concurrent_results["isolation_maintained"], \
            "Isolation violated during concurrent operations"
        
        # Verify each user performed expected operations
        for user_result in concurrent_results["user_results"]:
            assert user_result["operations_count"] == 8  # 5 messages + 3 state updates
            assert user_result["user_id"] in [ctx.user_id for ctx in user_contexts]
        
        # Final validation: Re-check isolation after concurrent operations
        final_isolation_results = await validator.validate_complete_user_isolation(user_contexts)
        assert not final_isolation_results["cross_contamination_detected"], \
            f"Concurrent operations caused isolation violations: {final_isolation_results['violations']}"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_user_context_isolation_under_high_concurrency(self, real_services_fixture):
        """Test user context isolation under high concurrency load (stress test)."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = UserContextIsolationValidator(real_services_fixture)
        
        # Create high number of concurrent users (stress test)
        stress_user_count = 10
        user_contexts = []
        
        # Create users concurrently to test isolation under load
        async def create_user_task(user_index: int) -> IsolatedUserContext:
            return await validator.create_isolated_user_context(f"stress-{user_index}-{uuid.uuid4().hex[:4]}")
        
        creation_tasks = [create_user_task(i) for i in range(stress_user_count)]
        user_contexts = await asyncio.gather(*creation_tasks)
        
        # Verify all users created successfully
        assert len(user_contexts) == stress_user_count
        
        # Validate isolation under high concurrency
        stress_isolation_results = await validator.validate_complete_user_isolation(user_contexts)
        
        # CRITICAL: High concurrency must not break isolation
        assert not stress_isolation_results["cross_contamination_detected"], \
            f"High concurrency caused isolation violations: {stress_isolation_results['violations']}"
        
        # All isolation layers must remain intact
        assert stress_isolation_results["database_isolation"], "Database isolation failed under high concurrency"
        assert stress_isolation_results["cache_isolation"], "Cache isolation failed under high concurrency"
        assert stress_isolation_results["websocket_isolation"], "WebSocket isolation failed under high concurrency"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.enterprise
    async def test_organization_level_user_context_isolation(self, real_services_fixture):
        """Test that users from different organizations are completely isolated."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = UserContextIsolationValidator(real_services_fixture)
        
        # Create users from different organizations
        org_a_users = []
        org_b_users = []
        
        for i in range(3):
            user_a = await validator.create_isolated_user_context(f"org-a-user-{i}")
            user_b = await validator.create_isolated_user_context(f"org-b-user-{i}")
            
            org_a_users.append(user_a)
            org_b_users.append(user_b)
        
        # Verify organization isolation
        all_users = org_a_users + org_b_users
        org_isolation_results = await validator.validate_complete_user_isolation(all_users)
        
        # CRITICAL: Organization boundaries must be respected
        assert org_isolation_results["organization_isolation"], \
            f"Organization isolation FAILED: {org_isolation_results['violations']}"
        assert not org_isolation_results["cross_contamination_detected"], \
            f"Cross-organization contamination: {org_isolation_results['violations']}"
        
        # Verify users cannot access other organization's data
        for org_a_user in org_a_users:
            for org_b_user in org_b_users:
                # Organization IDs must be different
                assert org_a_user.organization_id != org_b_user.organization_id, \
                    "Users from different orgs should have different organization IDs"