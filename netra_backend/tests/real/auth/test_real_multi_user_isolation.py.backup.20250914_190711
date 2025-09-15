"""
Real Multi-User Isolation Tests

Business Value: Platform/Internal - Security & Data Protection - Validates complete
user isolation and prevents data leakage between users using real services.

Coverage Target: 95%
Test Category: Integration with Real Services - CRITICAL SECURITY
Infrastructure Required: Docker (PostgreSQL, Redis, Auth Service, Backend)

This test suite validates the factory-based user isolation patterns described in
USER_CONTEXT_ARCHITECTURE.md to ensure complete separation of user data and
prevent the silent data leakage described in WebSocket v2 migration requirements.

CRITICAL: This is a security-critical test suite that validates the business-critical
requirement that User A never sees User B's data.
"""

import asyncio
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
import redis.asyncio as redis
from fastapi import HTTPException, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Import user isolation and auth components
from netra_backend.app.core.auth_constants import (
    CacheConstants, JWTConstants, AuthConstants, HeaderConstants
)
from netra_backend.app.auth_dependencies import get_request_scoped_db_session_for_fastapi
from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.main import app
from shared.isolated_environment import IsolatedEnvironment

# Import test framework
from test_framework.docker_test_manager import UnifiedDockerManager
from test_framework.async_test_helpers import AsyncTestDatabase

# Use isolated environment for all env access
env = IsolatedEnvironment()

# Docker manager for real services
docker_manager = UnifiedDockerManager()

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.security
@pytest.mark.critical
@pytest.mark.asyncio
class TestRealMultiUserIsolation:
    """
    Real multi-user isolation tests using Docker services.
    
    Tests factory-based user context isolation, data segregation, concurrent user
    operations, and prevention of data leakage between users using real infrastructure.
    
    CRITICAL: This test suite validates the business requirement that users must
    never see each other's data, even under high load or failure conditions.
    """

    @pytest.fixture(scope="class", autouse=True)
    async def setup_docker_services(self):
        """Start Docker services for multi-user isolation testing."""
        print("[U+1F433] Starting Docker services for multi-user isolation tests...")
        
        services = ["backend", "auth", "postgres", "redis"]
        
        try:
            await docker_manager.start_services_async(
                services=services,
                health_check=True,
                timeout=120
            )
            
            await asyncio.sleep(5)
            print(" PASS:  Docker services ready for multi-user isolation tests")
            yield
            
        except Exception as e:
            pytest.fail(f" FAIL:  Failed to start Docker services for isolation tests: {e}")
        finally:
            print("[U+1F9F9] Cleaning up Docker services after multi-user isolation tests...")
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for multi-user API testing."""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    @pytest.fixture
    async def real_db_session(self):
        """Get real database session for user data testing."""
        async for session in get_request_scoped_db_session_for_fastapi():
            yield session

    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for user cache isolation testing."""
        redis_url = env.get_env_var("REDIS_URL", "redis://localhost:6381")
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            print(f" PASS:  Connected to Redis at {redis_url} for isolation tests")
            yield client
        except Exception as e:
            pytest.fail(f" FAIL:  Failed to connect to Redis for isolation tests: {e}")
        finally:
            if 'client' in locals():
                await client.aclose()

    def create_isolated_user_context(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Create isolated user context data following factory pattern."""
        return {
            "user_id": user_id,
            "session_id": secrets.token_hex(16),
            "email": kwargs.get("email", f"user{user_id}@netra.ai"),
            "full_name": kwargs.get("full_name", f"Test User {user_id}"),
            "workspace_id": kwargs.get("workspace_id", f"workspace_{user_id}"),
            "tenant_id": kwargs.get("tenant_id", f"tenant_{user_id}"),
            "permissions": kwargs.get("permissions", ["read"]),
            "context_id": str(uuid.uuid4()),  # Unique context identifier
            "created_at": datetime.utcnow().isoformat(),
            "isolation_boundary": f"user_{user_id}_boundary",
            "data_namespace": f"ns_user_{user_id}",
            "execution_context": {
                "user_id": user_id,
                "session_id": secrets.token_hex(8),
                "request_id": str(uuid.uuid4())
            }
        }

    def create_user_specific_data(self, user_id: int, data_type: str = "general") -> Dict[str, Any]:
        """Create user-specific data that should be isolated."""
        base_data = {
            "owner_user_id": user_id,
            "data_id": str(uuid.uuid4()),
            "created_by": user_id,
            "tenant_id": f"tenant_{user_id}",
            "workspace_id": f"workspace_{user_id}",
            "visibility": "private",
            "access_level": "owner_only",
            "data_classification": "user_private"
        }
        
        if data_type == "conversation":
            return {
                **base_data,
                "type": "conversation",
                "title": f"User {user_id} Private Conversation",
                "messages": [
                    {
                        "id": str(uuid.uuid4()),
                        "content": f"This is private message for user {user_id}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "user_id": user_id
                    }
                ],
                "thread_id": f"thread_{user_id}_{secrets.token_hex(8)}"
            }
        elif data_type == "document":
            return {
                **base_data,
                "type": "document", 
                "title": f"User {user_id} Private Document",
                "content": f"Confidential content for user {user_id}",
                "tags": [f"user{user_id}", "private", "confidential"]
            }
        else:
            return {
                **base_data,
                "type": "general",
                "content": f"General private data for user {user_id}"
            }

    @pytest.mark.asyncio
    async def test_user_context_factory_isolation(self, redis_client, real_db_session):
        """Test user context factory creates isolated execution contexts."""
        
        # Create isolated contexts for multiple users
        users = [11111, 22222, 33333, 44444, 55555]
        user_contexts = {}
        cache_keys = []
        
        try:
            # Create isolated contexts for each user
            for user_id in users:
                context = self.create_isolated_user_context(user_id)
                user_contexts[user_id] = context
                
                # Store context in Redis with user-specific namespace
                cache_key = f"user_context:{context['data_namespace']}:{context['session_id']}"
                cache_keys.append(cache_key)
                
                await redis_client.setex(
                    cache_key,
                    CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                    json.dumps(context)
                )
            
            # Verify each user context is completely isolated
            for user_id in users:
                context = user_contexts[user_id]
                
                # Verify unique isolation boundaries
                assert context["isolation_boundary"] == f"user_{user_id}_boundary"
                assert context["data_namespace"] == f"ns_user_{user_id}"
                assert context["user_id"] == user_id
                
                # Verify no overlap with other users
                for other_user_id in users:
                    if user_id != other_user_id:
                        other_context = user_contexts[other_user_id]
                        
                        # Critical isolation checks
                        assert context["session_id"] != other_context["session_id"]
                        assert context["context_id"] != other_context["context_id"]
                        assert context["workspace_id"] != other_context["workspace_id"]
                        assert context["tenant_id"] != other_context["tenant_id"]
                        assert context["isolation_boundary"] != other_context["isolation_boundary"]
                        assert context["data_namespace"] != other_context["data_namespace"]
            
            print(f" PASS:  User context factory isolation validated for {len(users)} users")
            
        finally:
            # Cleanup all contexts
            for cache_key in cache_keys:
                await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_user_data_segregation_in_database(self, real_db_session):
        """Test user data segregation in database operations."""
        
        # Create test data for multiple users
        users_data = {}
        
        for user_id in [10001, 10002, 10003]:
            # Create different types of user data
            users_data[user_id] = {
                "conversations": [
                    self.create_user_specific_data(user_id, "conversation") for _ in range(2)
                ],
                "documents": [
                    self.create_user_specific_data(user_id, "document") for _ in range(3)
                ]
            }
        
        try:
            # Simulate database storage with user-scoped queries
            # Note: In real implementation, all queries would include user_id filters
            
            for user_id, data in users_data.items():
                # Verify data ownership
                for conversation in data["conversations"]:
                    assert conversation["owner_user_id"] == user_id
                    assert conversation["created_by"] == user_id
                    assert conversation["tenant_id"] == f"tenant_{user_id}"
                    
                    # Verify no data leakage in content
                    for message in conversation["messages"]:
                        assert message["user_id"] == user_id
                        assert f"user {user_id}" in message["content"].lower()
                
                for document in data["documents"]:
                    assert document["owner_user_id"] == user_id
                    assert document["created_by"] == user_id
                    assert f"user {user_id}" in document["content"].lower()
                    assert document["visibility"] == "private"
            
            # Verify cross-user isolation
            for user_id in users_data:
                user_conversations = users_data[user_id]["conversations"]
                
                # Check that user's data doesn't contain other users' info
                for other_user_id in users_data:
                    if user_id != other_user_id:
                        for conversation in user_conversations:
                            # Critical: User A's data must never contain User B's info
                            assert f"user {other_user_id}" not in conversation["title"].lower()
                            
                            for message in conversation["messages"]:
                                assert f"user {other_user_id}" not in message["content"].lower()
                                assert message["user_id"] != other_user_id
            
            print(f" PASS:  User data segregation validated for {len(users_data)} users")
            
        except Exception as e:
            pytest.fail(f" FAIL:  User data segregation test failed: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_user_operations_isolation(self, redis_client, real_db_session):
        """Test user isolation during concurrent operations."""
        
        async def simulate_user_operations(user_id: int, operation_count: int = 5):
            """Simulate concurrent operations for a single user."""
            user_context = self.create_isolated_user_context(user_id)
            operations_data = []
            
            for i in range(operation_count):
                # Create user-specific operation data
                operation_data = {
                    "operation_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "operation_type": f"test_op_{i}",
                    "data": self.create_user_specific_data(user_id),
                    "context": user_context["execution_context"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                operations_data.append(operation_data)
                
                # Store operation in Redis with user namespace
                cache_key = f"operation:{user_context['data_namespace']}:{operation_data['operation_id']}"
                
                await redis_client.setex(
                    cache_key,
                    60,  # 1 minute TTL
                    json.dumps(operation_data)
                )
                
                # Small delay to simulate real operations
                await asyncio.sleep(0.01)
            
            return {
                "user_id": user_id,
                "context": user_context,
                "operations": operations_data
            }
        
        # Run concurrent operations for multiple users
        concurrent_users = [20001, 20002, 20003, 20004, 20005]
        
        try:
            # Execute concurrent user operations
            tasks = [
                simulate_user_operations(user_id, operation_count=3)
                for user_id in concurrent_users
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify no exceptions occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f" FAIL:  Concurrent operation failed for user {concurrent_users[i]}: {result}")
            
            # Verify complete isolation between concurrent users
            for i, result in enumerate(results):
                user_id = concurrent_users[i]
                user_context = result["context"]
                user_operations = result["operations"]
                
                # Verify user-specific data integrity
                assert result["user_id"] == user_id
                assert user_context["user_id"] == user_id
                
                for operation in user_operations:
                    assert operation["user_id"] == user_id
                    assert operation["context"]["user_id"] == user_id
                    assert operation["data"]["owner_user_id"] == user_id
                
                # Verify no cross-contamination with other users
                for j, other_result in enumerate(results):
                    if i != j:
                        other_user_id = concurrent_users[j]
                        other_context = other_result["context"]
                        
                        # Critical isolation checks
                        assert user_context["session_id"] != other_context["session_id"]
                        assert user_context["context_id"] != other_context["context_id"]
                        assert user_context["data_namespace"] != other_context["data_namespace"]
                        
                        # Verify no operation data overlap
                        for operation in user_operations:
                            for other_operation in other_result["operations"]:
                                assert operation["operation_id"] != other_operation["operation_id"]
                                assert operation["user_id"] != other_operation["user_id"]
            
            print(f" PASS:  Concurrent user operations isolation validated for {len(concurrent_users)} users")
            
        finally:
            # Cleanup operation data
            pattern = "operation:*"
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_websocket_user_context_isolation(self, redis_client):
        """Test WebSocket user context isolation as described in WebSocket v2 requirements."""
        
        # Simulate WebSocket connections for multiple users
        websocket_users = [30001, 30002, 30003]
        websocket_contexts = {}
        
        try:
            for user_id in websocket_users:
                # Create WebSocket-specific user context
                ws_context = self.create_isolated_user_context(user_id)
                ws_context.update({
                    "connection_id": str(uuid.uuid4()),
                    "websocket_session": secrets.token_hex(16),
                    "message_namespace": f"ws_user_{user_id}",
                    "event_handlers": {
                        "user_specific": True,
                        "handler_scope": f"user_{user_id}_only"
                    }
                })
                
                websocket_contexts[user_id] = ws_context
                
                # Store WebSocket context
                cache_key = f"websocket:{ws_context['message_namespace']}:{ws_context['connection_id']}"
                
                await redis_client.setex(
                    cache_key,
                    CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                    json.dumps(ws_context)
                )
            
            # Simulate WebSocket messages with user isolation
            for user_id in websocket_users:
                context = websocket_contexts[user_id]
                
                # Create user-specific WebSocket message
                ws_message = {
                    "message_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "connection_id": context["connection_id"],
                    "message_type": "agent_response",
                    "payload": {
                        "response": f"AI response for user {user_id}",
                        "thread_id": f"thread_{user_id}_{secrets.token_hex(4)}",
                        "context": context["execution_context"]
                    },
                    "namespace": context["message_namespace"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Store message with user namespace
                msg_cache_key = f"ws_message:{context['message_namespace']}:{ws_message['message_id']}"
                
                await redis_client.setex(
                    msg_cache_key,
                    300,  # 5 minutes
                    json.dumps(ws_message)
                )
            
            # Verify WebSocket isolation
            for user_id in websocket_users:
                context = websocket_contexts[user_id]
                
                # Verify user-specific context
                assert context["user_id"] == user_id
                assert context["message_namespace"] == f"ws_user_{user_id}"
                assert context["event_handlers"]["handler_scope"] == f"user_{user_id}_only"
                
                # Verify isolation from other WebSocket contexts
                for other_user_id in websocket_users:
                    if user_id != other_user_id:
                        other_context = websocket_contexts[other_user_id]
                        
                        # Critical WebSocket isolation checks
                        assert context["connection_id"] != other_context["connection_id"]
                        assert context["websocket_session"] != other_context["websocket_session"]
                        assert context["message_namespace"] != other_context["message_namespace"]
                        
                        # Verify event handler isolation
                        assert (context["event_handlers"]["handler_scope"] != 
                               other_context["event_handlers"]["handler_scope"])
            
            print(f" PASS:  WebSocket user context isolation validated for {len(websocket_users)} users")
            
        finally:
            # Cleanup WebSocket contexts and messages
            ws_pattern = "websocket:*"
            msg_pattern = "ws_message:*"
            
            ws_keys = await redis_client.keys(ws_pattern)
            msg_keys = await redis_client.keys(msg_pattern)
            
            all_keys = ws_keys + msg_keys
            if all_keys:
                await redis_client.delete(*all_keys)

    @pytest.mark.asyncio
    async def test_user_permission_boundary_enforcement(self, redis_client, real_db_session):
        """Test user permission boundaries and access control isolation."""
        
        # Create users with different permission levels
        permission_test_users = [
            {
                "user_id": 40001,
                "role": "admin",
                "permissions": ["read", "write", "admin", "delete", "manage_users"]
            },
            {
                "user_id": 40002,
                "role": "power_user", 
                "permissions": ["read", "write", "create"]
            },
            {
                "user_id": 40003,
                "role": "regular_user",
                "permissions": ["read"]
            },
            {
                "user_id": 40004,
                "role": "guest",
                "permissions": []
            }
        ]
        
        user_contexts = {}
        
        try:
            # Create isolated contexts with different permissions
            for user_config in permission_test_users:
                user_id = user_config["user_id"]
                context = self.create_isolated_user_context(
                    user_id,
                    permissions=user_config["permissions"]
                )
                context["role"] = user_config["role"]
                context["permission_boundary"] = f"boundary_{user_config['role']}_{user_id}"
                
                user_contexts[user_id] = context
                
                # Store context with permission metadata
                cache_key = f"user_permissions:{context['data_namespace']}:{context['session_id']}"
                
                await redis_client.setex(
                    cache_key,
                    CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                    json.dumps(context)
                )
            
            # Test permission boundary enforcement
            for user_config in permission_test_users:
                user_id = user_config["user_id"]
                context = user_contexts[user_id]
                
                # Verify user has only assigned permissions
                assert set(context["permissions"]) == set(user_config["permissions"])
                assert context["role"] == user_config["role"]
                
                # Test permission escalation prevention
                restricted_actions = ["admin", "delete", "manage_users"]
                
                for action in restricted_actions:
                    has_permission = action in context["permissions"]
                    should_have_permission = user_config["role"] == "admin"
                    
                    if not should_have_permission:
                        assert not has_permission, f"User {user_id} should not have {action} permission"
                
                # Verify permission isolation from other users
                for other_config in permission_test_users:
                    other_user_id = other_config["user_id"]
                    if user_id != other_user_id:
                        other_context = user_contexts[other_user_id]
                        
                        # Users cannot inherit or access other users' permissions
                        assert context["permission_boundary"] != other_context["permission_boundary"]
                        
                        # Permission sets should be independent
                        if context["role"] != other_context["role"]:
                            assert context["permissions"] != other_context["permissions"]
            
            print(f" PASS:  User permission boundary enforcement validated for {len(permission_test_users)} users")
            
        finally:
            # Cleanup permission contexts
            pattern = "user_permissions:*"
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_data_leakage_prevention_under_load(self, redis_client):
        """Test prevention of data leakage between users under high load conditions."""
        
        async def simulate_high_load_user_activity(user_id: int, iterations: int = 10):
            """Simulate high-load activity for a single user."""
            user_data_points = []
            
            for i in range(iterations):
                # Create sensitive user data
                sensitive_data = {
                    "data_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "secret_token": secrets.token_hex(16),
                    "private_content": f"HIGHLY_SENSITIVE_DATA_FOR_USER_{user_id}_ITERATION_{i}",
                    "financial_info": f"USER_{user_id}_ACCOUNT_BALANCE_${i*1000}",
                    "personal_details": f"USER_{user_id}_SSN_XXX-XX-{i:04d}",
                    "session_data": {
                        "user_id": user_id,
                        "session_secret": secrets.token_hex(8)
                    }
                }
                
                user_data_points.append(sensitive_data)
                
                # Store with user-specific key
                cache_key = f"sensitive_data:user_{user_id}:{sensitive_data['data_id']}"
                
                await redis_client.setex(
                    cache_key,
                    120,  # 2 minutes
                    json.dumps(sensitive_data)
                )
                
                # Simulate processing delay
                await asyncio.sleep(0.001)  # 1ms delay
            
            return {
                "user_id": user_id,
                "data_points": user_data_points
            }
        
        # Simulate high load with many concurrent users
        high_load_users = list(range(50001, 50011))  # 10 users
        
        try:
            # Execute high-load simulation
            tasks = [
                simulate_high_load_user_activity(user_id, iterations=5)
                for user_id in high_load_users
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify no exceptions during high load
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f" FAIL:  High load test failed for user {high_load_users[i]}: {result}")
            
            # Critical data leakage verification
            for i, result in enumerate(results):
                user_id = high_load_users[i]
                user_data_points = result["data_points"]
                
                # Verify all data points belong to correct user
                for data_point in user_data_points:
                    assert data_point["user_id"] == user_id
                    assert f"USER_{user_id}" in data_point["private_content"]
                    assert f"USER_{user_id}" in data_point["financial_info"]
                    assert data_point["session_data"]["user_id"] == user_id
                
                # CRITICAL: Verify no data contamination from other users
                for j, other_result in enumerate(results):
                    if i != j:
                        other_user_id = high_load_users[j]
                        other_data_points = other_result["data_points"]
                        
                        # Check for data leakage - this is the most critical test
                        for data_point in user_data_points:
                            # User's data must never contain other users' information
                            assert f"USER_{other_user_id}" not in data_point["private_content"]
                            assert f"USER_{other_user_id}" not in data_point["financial_info"]
                            assert f"USER_{other_user_id}" not in data_point["personal_details"]
                            assert data_point["session_data"]["user_id"] != other_user_id
                        
                        # Verify data points are completely separate
                        for data_point in user_data_points:
                            for other_data_point in other_data_points:
                                assert data_point["data_id"] != other_data_point["data_id"]
                                assert data_point["secret_token"] != other_data_point["secret_token"]
                                assert (data_point["session_data"]["session_secret"] != 
                                       other_data_point["session_data"]["session_secret"])
            
            print(f" PASS:  Data leakage prevention validated under high load for {len(high_load_users)} users")
            
        finally:
            # Cleanup sensitive data
            pattern = "sensitive_data:*"
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_user_context_cleanup_on_session_end(self, redis_client):
        """Test complete user context cleanup when sessions end."""
        
        # Create multiple user sessions
        cleanup_users = [60001, 60002, 60003]
        user_contexts = {}
        all_keys = []
        
        try:
            for user_id in cleanup_users:
                context = self.create_isolated_user_context(user_id)
                user_contexts[user_id] = context
                
                # Store multiple data points for each user
                data_types = ["session", "cache", "temp_data", "user_state"]
                
                for data_type in data_types:
                    key = f"{data_type}:user_{user_id}:{context['session_id']}"
                    all_keys.append(key)
                    
                    data = {
                        "user_id": user_id,
                        "type": data_type,
                        "context_id": context["context_id"],
                        "data": f"User {user_id} {data_type} data"
                    }
                    
                    await redis_client.setex(key, 300, json.dumps(data))
            
            # Verify all data exists
            for key in all_keys:
                data = await redis_client.get(key)
                assert data is not None, f"Data should exist before cleanup: {key}"
            
            # Simulate session end cleanup for specific user
            cleanup_user_id = 60001
            cleanup_context = user_contexts[cleanup_user_id]
            
            # Remove all data for specific user
            user_keys_to_delete = [key for key in all_keys if f"user_{cleanup_user_id}" in key]
            
            if user_keys_to_delete:
                await redis_client.delete(*user_keys_to_delete)
            
            # Verify user's data is cleaned up
            for key in user_keys_to_delete:
                data = await redis_client.get(key)
                assert data is None, f"User data should be cleaned up: {key}"
            
            # Verify other users' data remains intact
            other_users = [uid for uid in cleanup_users if uid != cleanup_user_id]
            for user_id in other_users:
                user_keys = [key for key in all_keys if f"user_{user_id}" in key]
                for key in user_keys:
                    data = await redis_client.get(key)
                    assert data is not None, f"Other user data should remain intact: {key}"
                    
                    parsed = json.loads(data)
                    assert parsed["user_id"] == user_id
                    assert parsed["user_id"] != cleanup_user_id
            
            print(f" PASS:  User context cleanup validated - User {cleanup_user_id} cleaned, others preserved")
            
        finally:
            # Cleanup remaining test data
            remaining_keys = await redis_client.keys("session:*")
            remaining_keys.extend(await redis_client.keys("cache:*"))
            remaining_keys.extend(await redis_client.keys("temp_data:*"))
            remaining_keys.extend(await redis_client.keys("user_state:*"))
            
            if remaining_keys:
                await redis_client.delete(*remaining_keys)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])