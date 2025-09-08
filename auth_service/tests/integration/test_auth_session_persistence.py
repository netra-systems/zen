"""
Auth Session Persistence Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain user authentication state across chat sessions
- Value Impact: Users can continue conversations without re-authenticating, improving UX and engagement
- Strategic Impact: Core functionality for chat continuity and user retention

CRITICAL: These tests use REAL Redis service (no mocks).
Tests validate session persistence, expiry, cleanup, and multi-user isolation.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import uuid

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.auth_core.config import AuthConfig
from auth_service.services.redis_service import RedisService
from auth_service.services.session_service import SessionService
from auth_service.services.jwt_service import JWTService


class TestSessionPersistenceIntegration(BaseIntegrationTest):
    """Integration tests for session persistence with real Redis service."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real Redis service."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # Real service instances
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        self.session_service = SessionService(self.auth_config, self.redis_service, self.jwt_service)
        
        # Test user data for session creation
        self.test_users = [
            {
                "user_id": f"session-test-user-{i}",
                "email": f"session-test-{i}@example.com",
                "name": f"Session Test User {i}",
                "permissions": ["read", "write"]
            }
            for i in range(3)
        ]
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real Redis service."""
        try:
            # Clean all test sessions
            session_keys = await self.redis_service.keys("session:*session-test-*")
            if session_keys:
                await self.redis_service.delete(*session_keys)
            
            # Clean refresh tokens
            refresh_keys = await self.redis_service.keys("refresh:*session-test-*")
            if refresh_keys:
                await self.redis_service.delete(*refresh_keys)
            
            # Clean user activity logs
            activity_keys = await self.redis_service.keys("activity:*session-test-*")
            if activity_keys:
                await self.redis_service.delete(*activity_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_creation_and_retrieval(self):
        """
        Test session creation and retrieval with real Redis persistence.
        
        BVJ: Users must have persistent sessions to maintain chat continuity.
        """
        user_data = self.test_users[0]
        
        # Create JWT token
        access_token = await self.jwt_service.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        # Create session
        session_id = await self.session_service.create_session(
            user_id=user_data["user_id"],
            email=user_data["email"],
            access_token=access_token,
            session_data={
                "name": user_data["name"],
                "permissions": user_data["permissions"],
                "login_method": "standard",
                "user_agent": "integration-test-client",
                "ip_address": "127.0.0.1"
            }
        )
        
        assert session_id is not None
        assert len(session_id) >= 16  # Session ID should be sufficiently long
        
        # Verify session storage in Redis
        session_key = f"session:{session_id}"
        stored_session = await self.redis_service.get(session_key)
        assert stored_session is not None
        
        # Parse and validate stored session data
        session_data = json.loads(stored_session)
        assert session_data["user_id"] == user_data["user_id"]
        assert session_data["email"] == user_data["email"]
        assert session_data["access_token"] == access_token
        assert session_data["name"] == user_data["name"]
        assert session_data["permissions"] == user_data["permissions"]
        assert session_data["login_method"] == "standard"
        assert "created_at" in session_data
        assert "last_accessed" in session_data
        
        # Retrieve session using service
        retrieved_session = await self.session_service.get_session(session_id)
        assert retrieved_session is not None
        assert retrieved_session["user_id"] == user_data["user_id"]
        assert retrieved_session["email"] == user_data["email"]
        assert retrieved_session["access_token"] == access_token
        
        # Verify session TTL
        session_ttl = await self.redis_service.ttl(session_key)
        assert session_ttl > 0  # Should have expiry set
        assert session_ttl <= 3600  # Default 1 hour max
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_update_and_last_accessed(self):
        """
        Test session updates and last accessed timestamp tracking.
        
        BVJ: Enables tracking user activity for engagement analytics and session extension.
        """
        user_data = self.test_users[0]
        
        # Create session
        access_token = await self.jwt_service.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        session_id = await self.session_service.create_session(
            user_id=user_data["user_id"],
            email=user_data["email"],
            access_token=access_token
        )
        
        # Get initial session
        initial_session = await self.session_service.get_session(session_id)
        initial_last_accessed = initial_session["last_accessed"]
        
        # Wait to ensure timestamp difference
        await asyncio.sleep(1)
        
        # Update session with new activity
        await self.session_service.update_session_activity(
            session_id=session_id,
            activity_data={
                "last_action": "send_message",
                "message_count": 5,
                "thread_id": "test-thread-123",
                "user_agent": "updated-client"
            }
        )
        
        # Retrieve updated session
        updated_session = await self.session_service.get_session(session_id)
        assert updated_session is not None
        
        # Verify last_accessed was updated
        updated_last_accessed = updated_session["last_accessed"]
        assert updated_last_accessed != initial_last_accessed
        
        # Parse timestamps to ensure updated is later
        initial_time = datetime.fromisoformat(initial_last_accessed.replace('Z', '+00:00'))
        updated_time = datetime.fromisoformat(updated_last_accessed.replace('Z', '+00:00'))
        assert updated_time > initial_time
        
        # Verify activity data was stored
        assert updated_session["last_action"] == "send_message"
        assert updated_session["message_count"] == 5
        assert updated_session["thread_id"] == "test-thread-123"
        assert updated_session["user_agent"] == "updated-client"
        
        # Verify session TTL was extended (if policy requires it)
        session_key = f"session:{session_id}"
        session_ttl = await self.redis_service.ttl(session_key)
        assert session_ttl > 0  # Still has expiry
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_expiry_and_cleanup(self):
        """
        Test session expiry and automatic cleanup in Redis.
        
        BVJ: Prevents session accumulation and maintains system performance.
        """
        user_data = self.test_users[0]
        
        # Create session with short expiry
        access_token = await self.jwt_service.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        session_id = await self.session_service.create_session(
            user_id=user_data["user_id"],
            email=user_data["email"],
            access_token=access_token,
            expires_in=3  # 3 seconds expiry
        )
        
        # Session should exist initially
        session = await self.session_service.get_session(session_id)
        assert session is not None
        
        # Verify Redis TTL
        session_key = f"session:{session_id}"
        initial_ttl = await self.redis_service.ttl(session_key)
        assert 1 <= initial_ttl <= 3
        
        # Wait for expiry
        await asyncio.sleep(4)
        
        # Session should be expired and automatically removed by Redis
        expired_session = await self.session_service.get_session(session_id)
        assert expired_session is None
        
        # Verify key is removed from Redis
        expired_key = await self.redis_service.get(session_key)
        assert expired_key is None
        
        # Verify TTL returns -2 (key doesn't exist)
        expired_ttl = await self.redis_service.ttl(session_key)
        assert expired_ttl == -2
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_session_isolation(self):
        """
        Test session isolation between multiple users (critical for multi-user system).
        
        BVJ: Ensures users cannot access each other's sessions, maintaining security and privacy.
        """
        # Create sessions for multiple users
        sessions_data = []
        
        for i, user_data in enumerate(self.test_users):
            access_token = await self.jwt_service.create_access_token(
                user_id=user_data["user_id"],
                email=user_data["email"],
                permissions=user_data["permissions"]
            )
            
            session_id = await self.session_service.create_session(
                user_id=user_data["user_id"],
                email=user_data["email"],
                access_token=access_token,
                session_data={
                    "name": user_data["name"],
                    "user_index": i,
                    "secret_data": f"secret-{i}-{uuid.uuid4()}"
                }
            )
            
            sessions_data.append({
                "user_id": user_data["user_id"],
                "session_id": session_id,
                "access_token": access_token,
                "secret_data": f"secret-{i}-{uuid.uuid4()}"
            })
        
        # Verify each user can only access their own session
        for i, session_info in enumerate(sessions_data):
            retrieved_session = await self.session_service.get_session(session_info["session_id"])
            assert retrieved_session is not None
            assert retrieved_session["user_id"] == session_info["user_id"]
            assert retrieved_session["user_index"] == i
            
            # Verify other users' data is not accessible
            for j, other_session in enumerate(sessions_data):
                if i != j:
                    # Try to get another user's session (should return their own data, not others')
                    other_retrieved = await self.session_service.get_session(other_session["session_id"])
                    if other_retrieved:  # If session exists
                        assert other_retrieved["user_id"] != session_info["user_id"]
                        assert other_retrieved["user_id"] == other_session["user_id"]
        
        # Verify session keys are unique in Redis
        all_session_keys = []
        for session_info in sessions_data:
            session_key = f"session:{session_info['session_id']}"
            all_session_keys.append(session_key)
            
            # Verify key exists
            stored_data = await self.redis_service.get(session_key)
            assert stored_data is not None
            
            session_data = json.loads(stored_data)
            assert session_data["user_id"] == session_info["user_id"]
        
        # Ensure all session keys are unique
        assert len(all_session_keys) == len(set(all_session_keys))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_session_operations(self):
        """
        Test concurrent session operations for performance and consistency.
        
        BVJ: Ensures system can handle multiple simultaneous session operations without conflicts.
        """
        user_data = self.test_users[0]
        concurrent_operations = 10
        
        # Create base session
        access_token = await self.jwt_service.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        session_id = await self.session_service.create_session(
            user_id=user_data["user_id"],
            email=user_data["email"],
            access_token=access_token
        )
        
        async def concurrent_session_update(operation_id: int):
            """Perform concurrent session update operation."""
            await self.session_service.update_session_activity(
                session_id=session_id,
                activity_data={
                    "operation_id": operation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": f"concurrent_action_{operation_id}",
                    "data": f"concurrent_data_{operation_id}"
                }
            )
            
            # Retrieve session to verify update
            updated_session = await self.session_service.get_session(session_id)
            return {
                "operation_id": operation_id,
                "session_exists": updated_session is not None,
                "user_id": updated_session["user_id"] if updated_session else None,
                "operation_recorded": updated_session.get("operation_id") if updated_session else None
            }
        
        # Execute concurrent operations
        tasks = [concurrent_session_update(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        assert len(results) == concurrent_operations
        
        for result in results:
            assert result["session_exists"] is True
            assert result["user_id"] == user_data["user_id"]
            assert result["operation_recorded"] is not None
        
        # Verify final session state is consistent
        final_session = await self.session_service.get_session(session_id)
        assert final_session is not None
        assert final_session["user_id"] == user_data["user_id"]
        
        # One of the concurrent operations should be recorded (last writer wins in Redis)
        assert "operation_id" in final_session
        assert 0 <= final_session["operation_id"] < concurrent_operations
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_refresh_token_integration(self):
        """
        Test session integration with refresh tokens in Redis.
        
        BVJ: Enables long-lived sessions through refresh token mechanism.
        """
        user_data = self.test_users[0]
        
        # Create access and refresh tokens
        access_token = await self.jwt_service.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"],
            expires_delta=timedelta(minutes=5)  # Short access token
        )
        
        refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        
        # Create session with both tokens
        session_id = await self.session_service.create_session(
            user_id=user_data["user_id"],
            email=user_data["email"],
            access_token=access_token,
            session_data={
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
        )
        
        # Store refresh token separately in Redis
        refresh_key = f"refresh:{user_data['user_id']}:{refresh_token[-8:]}"
        await self.redis_service.set(
            refresh_key,
            json.dumps({
                "user_id": user_data["user_id"],
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }),
            ex=2592000  # 30 days
        )
        
        # Verify session has refresh token
        session = await self.session_service.get_session(session_id)
        assert session is not None
        assert session["refresh_token"] == refresh_token
        assert session["access_token"] == access_token
        
        # Simulate refresh token usage
        new_access_token = await self.jwt_service.refresh_access_token(
            refresh_token,
            user_data["user_id"],
            user_data["permissions"]
        )
        
        # Update session with new access token
        await self.session_service.update_session_activity(
            session_id=session_id,
            activity_data={
                "access_token": new_access_token,
                "token_refreshed_at": datetime.now(timezone.utc).isoformat(),
                "refresh_count": 1
            }
        )
        
        # Verify session has new access token
        refreshed_session = await self.session_service.get_session(session_id)
        assert refreshed_session is not None
        assert refreshed_session["access_token"] == new_access_token
        assert refreshed_session["refresh_token"] == refresh_token  # Refresh token unchanged
        assert refreshed_session["refresh_count"] == 1
        assert "token_refreshed_at" in refreshed_session
        
        # Verify refresh token record still exists
        refresh_data = await self.redis_service.get(refresh_key)
        assert refresh_data is not None
        
        refresh_info = json.loads(refresh_data)
        assert refresh_info["user_id"] == user_data["user_id"]
        assert refresh_info["session_id"] == session_id
        assert refresh_info["is_active"] is True
        
        # Cleanup
        await self.redis_service.delete(refresh_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_bulk_session_cleanup_operations(self):
        """
        Test bulk session cleanup operations for maintenance.
        
        BVJ: Enables efficient session management and system cleanup for operational health.
        """
        # Create multiple sessions for the same user
        user_data = self.test_users[0]
        session_ids = []
        
        for i in range(5):
            access_token = await self.jwt_service.create_access_token(
                user_id=user_data["user_id"],
                email=user_data["email"],
                permissions=user_data["permissions"]
            )
            
            session_id = await self.session_service.create_session(
                user_id=user_data["user_id"],
                email=user_data["email"],
                access_token=access_token,
                session_data={"session_index": i},
                expires_in=3600  # 1 hour
            )
            
            session_ids.append(session_id)
        
        # Verify all sessions exist
        for session_id in session_ids:
            session = await self.session_service.get_session(session_id)
            assert session is not None
            assert session["user_id"] == user_data["user_id"]
        
        # Find all sessions for user using Redis pattern matching
        user_session_pattern = f"session:*"
        all_session_keys = await self.redis_service.keys(user_session_pattern)
        
        # Filter to find this user's sessions
        user_session_keys = []
        for key in all_session_keys:
            stored_data = await self.redis_service.get(key)
            if stored_data:
                session_data = json.loads(stored_data)
                if session_data.get("user_id") == user_data["user_id"]:
                    user_session_keys.append(key)
        
        assert len(user_session_keys) >= len(session_ids)  # May have sessions from other tests
        
        # Bulk cleanup: expire half the sessions
        sessions_to_expire = session_ids[:3]
        
        for session_id in sessions_to_expire:
            session_key = f"session:{session_id}"
            await self.redis_service.expire(session_key, 1)  # Expire in 1 second
        
        # Wait for expiry
        await asyncio.sleep(2)
        
        # Verify expired sessions are gone
        for session_id in sessions_to_expire:
            expired_session = await self.session_service.get_session(session_id)
            assert expired_session is None
        
        # Verify remaining sessions still exist
        remaining_sessions = session_ids[3:]
        for session_id in remaining_sessions:
            remaining_session = await self.session_service.get_session(session_id)
            assert remaining_session is not None
            assert remaining_session["user_id"] == user_data["user_id"]
        
        # Bulk delete remaining sessions
        remaining_keys = [f"session:{sid}" for sid in remaining_sessions]
        if remaining_keys:
            deleted_count = await self.redis_service.delete(*remaining_keys)
            assert deleted_count == len(remaining_keys)
        
        # Verify all user sessions are cleaned up
        for session_id in session_ids:
            final_session = await self.session_service.get_session(session_id)
            assert final_session is None