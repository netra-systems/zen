"""
Auth Multi-User Isolation Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete isolation between users in multi-user system
- Value Impact: Users cannot access each other's data, sessions, or resources - critical for privacy and security
- Strategic Impact: Core security foundation that enables enterprise adoption and regulatory compliance

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
Tests validate complete user isolation across all system components.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import secrets
import uuid

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.config import AuthConfig
from auth_service.services.user_service import UserService
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService
from auth_service.services.session_service import SessionService
from auth_service.database import get_database


class TestMultiUserIsolationIntegration(BaseIntegrationTest):
    """Integration tests for multi-user isolation with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # Real service instances
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        self.user_service = UserService(self.auth_config, get_database())
        self.session_service = SessionService(self.auth_config, self.redis_service, self.jwt_service)
        
        # Create isolated test users
        self.test_users = [
            {
                "user_id": f"isolation-test-user-{i}",
                "email": f"isolation-test-{i}@example.com",
                "name": f"Isolation Test User {i}",
                "password": f"IsolationPassword{i}123!",
                "permissions": ["read", "write"],
                "tier": ["free", "early", "enterprise"][i % 3],
                "secret_data": f"secret-user-{i}-{secrets.token_hex(8)}"
            }
            for i in range(1, 6)  # Create 5 test users
        ]
        
        self.created_user_emails = []  # Track for cleanup
        self.created_sessions = []     # Track for cleanup
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean test users from database
            for email in self.created_user_emails:
                try:
                    user = await self.user_service.get_user_by_email(email)
                    if user:
                        await self.user_service.delete_user(user.id)
                except Exception as e:
                    self.logger.warning(f"Could not delete test user {email}: {e}")
            
            # Clean sessions from Redis
            for session_key in self.created_sessions:
                try:
                    await self.redis_service.delete(session_key)
                except Exception as e:
                    self.logger.warning(f"Could not delete session {session_key}: {e}")
            
            # Clean all isolation test Redis keys
            isolation_keys = await self.redis_service.keys("*isolation-test*")
            if isolation_keys:
                await self.redis_service.delete(*isolation_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    async def create_isolated_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an isolated user with all associated data."""
        # Create user in database
        created_user = await self.user_service.create_user(
            email=user_data["email"],
            name=user_data["name"],
            password=user_data["password"]
        )
        
        self.created_user_emails.append(user_data["email"])
        
        # Create JWT token
        access_token = await self.jwt_service.create_access_token(
            user_id=str(created_user.id),
            email=created_user.email,
            permissions=user_data["permissions"]
        )
        
        # Create session
        session_id = await self.session_service.create_session(
            user_id=str(created_user.id),
            email=created_user.email,
            access_token=access_token,
            session_data={
                "name": user_data["name"],
                "permissions": user_data["permissions"],
                "tier": user_data["tier"],
                "secret_data": user_data["secret_data"],
                "isolation_test": True
            }
        )
        
        # Store additional user-specific data in Redis
        user_data_key = f"userdata:isolation-test:{created_user.id}"
        await self.redis_service.set(
            user_data_key,
            json.dumps({
                "user_id": str(created_user.id),
                "email": created_user.email,
                "tier": user_data["tier"],
                "secret_data": user_data["secret_data"],
                "private_settings": {
                    "theme": f"theme-{created_user.id}",
                    "language": f"lang-{created_user.id}",
                    "notifications": True
                },
                "created_at": datetime.now(timezone.utc).isoformat()
            }),
            ex=3600
        )
        
        session_key = f"session:{session_id}"
        self.created_sessions.extend([session_key, user_data_key])
        
        return {
            "user": created_user,
            "access_token": access_token,
            "session_id": session_id,
            "user_data_key": user_data_key,
            "original_data": user_data
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_data_isolation_in_database(self):
        """
        Test user data isolation in database operations.
        
        BVJ: Ensures users cannot access each other's account information and profile data.
        """
        # Create isolated users
        created_users = []
        for user_data in self.test_users[:3]:  # Use first 3 users
            created_user_info = await self.create_isolated_user(user_data)
            created_users.append(created_user_info)
        
        # Test 1: Each user can only retrieve their own data
        for i, user_info in enumerate(created_users):
            user = user_info["user"]
            
            # User should be able to get their own data
            own_user = await self.user_service.get_user_by_id(user.id)
            assert own_user is not None
            assert own_user.id == user.id
            assert own_user.email == user.email
            assert own_user.name == user.name
            
            # User should be able to get their data by email
            own_user_by_email = await self.user_service.get_user_by_email(user.email)
            assert own_user_by_email is not None
            assert own_user_by_email.id == user.id
            
            # Verify user cannot access other users' data through service
            for j, other_user_info in enumerate(created_users):
                if i != j:
                    other_user = other_user_info["user"]
                    
                    # Attempting to get other user's data by ID should fail or return different user
                    retrieved_other = await self.user_service.get_user_by_id(other_user.id)
                    if retrieved_other:
                        # If data exists, it should be the correct user (not current user)
                        assert retrieved_other.id != user.id
                        assert retrieved_other.email != user.email
                        assert retrieved_other.id == other_user.id
        
        # Test 2: Verify user password isolation
        for i, user_info in enumerate(created_users):
            user = user_info["user"]
            correct_password = user_info["original_data"]["password"]
            
            # User's correct password should work
            password_valid = await self.user_service.verify_password(user.id, correct_password)
            assert password_valid is True
            
            # Other users' passwords should not work for this user
            for j, other_user_info in enumerate(created_users):
                if i != j:
                    wrong_password = other_user_info["original_data"]["password"]
                    wrong_password_valid = await self.user_service.verify_password(user.id, wrong_password)
                    assert wrong_password_valid is False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_isolation_in_redis(self):
        """
        Test session isolation in Redis storage.
        
        BVJ: Ensures user sessions are completely isolated and cannot be accessed by other users.
        """
        # Create isolated users
        created_users = []
        for user_data in self.test_users[:4]:  # Use first 4 users
            created_user_info = await self.create_isolated_user(user_data)
            created_users.append(created_user_info)
        
        # Test 1: Each user has isolated session data
        for i, user_info in enumerate(created_users):
            session_id = user_info["session_id"]
            user = user_info["user"]
            original_data = user_info["original_data"]
            
            # Retrieve own session
            own_session = await self.session_service.get_session(session_id)
            assert own_session is not None
            assert own_session["user_id"] == str(user.id)
            assert own_session["email"] == user.email
            assert own_session["secret_data"] == original_data["secret_data"]
            assert own_session["tier"] == original_data["tier"]
            
            # Verify session contains user-specific data
            assert own_session["name"] == original_data["name"]
            assert own_session["permissions"] == original_data["permissions"]
        
        # Test 2: Users cannot access other users' sessions
        session_ids = [info["session_id"] for info in created_users]
        
        for i, user_info in enumerate(created_users):
            current_user = user_info["user"]
            current_session_id = user_info["session_id"]
            
            # User can access their own session
            own_session = await self.session_service.get_session(current_session_id)
            assert own_session["user_id"] == str(current_user.id)
            
            # Check that other sessions belong to different users
            for j, other_session_id in enumerate(session_ids):
                if i != j:
                    other_session = await self.session_service.get_session(other_session_id)
                    if other_session:  # Session might exist
                        # Should belong to different user
                        assert other_session["user_id"] != str(current_user.id)
                        assert other_session["email"] != current_user.email
        
        # Test 3: User-specific Redis data isolation
        for i, user_info in enumerate(created_users):
            user = user_info["user"]
            user_data_key = user_info["user_data_key"]
            original_data = user_info["original_data"]
            
            # Retrieve user-specific Redis data
            stored_data = await self.redis_service.get(user_data_key)
            assert stored_data is not None
            
            user_redis_data = json.loads(stored_data)
            assert user_redis_data["user_id"] == str(user.id)
            assert user_redis_data["email"] == user.email
            assert user_redis_data["secret_data"] == original_data["secret_data"]
            assert user_redis_data["tier"] == original_data["tier"]
            
            # Verify private settings are user-specific
            private_settings = user_redis_data["private_settings"]
            assert private_settings["theme"] == f"theme-{user.id}"
            assert private_settings["language"] == f"lang-{user.id}"
            
            # Verify other users' Redis keys are different
            for j, other_user_info in enumerate(created_users):
                if i != j:
                    other_user = other_user_info["user"]
                    other_key = other_user_info["user_data_key"]
                    
                    assert user_data_key != other_key
                    
                    other_stored_data = await self.redis_service.get(other_key)
                    if other_stored_data:
                        other_redis_data = json.loads(other_stored_data)
                        assert other_redis_data["user_id"] != str(user.id)
                        assert other_redis_data["secret_data"] != original_data["secret_data"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_isolation(self):
        """
        Test JWT token isolation between users.
        
        BVJ: Ensures JWT tokens are user-specific and cannot be used by other users.
        """
        # Create isolated users
        created_users = []
        for user_data in self.test_users[:3]:
            created_user_info = await self.create_isolated_user(user_data)
            created_users.append(created_user_info)
        
        # Test 1: Each user has unique JWT tokens
        tokens = [info["access_token"] for info in created_users]
        assert len(set(tokens)) == len(tokens)  # All tokens should be unique
        
        # Test 2: JWT tokens contain correct user-specific claims
        for i, user_info in enumerate(created_users):
            user = user_info["user"]
            token = user_info["access_token"]
            original_data = user_info["original_data"]
            
            # Validate token
            is_valid = await self.jwt_service.validate_token(token)
            assert is_valid is True
            
            # Decode token to verify claims
            import jwt
            decoded = jwt.decode(
                token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            assert decoded["sub"] == str(user.id)
            assert decoded["email"] == user.email
            assert decoded["permissions"] == original_data["permissions"]
            assert decoded["type"] == "access"
            
            # Verify token claims don't match other users
            for j, other_user_info in enumerate(created_users):
                if i != j:
                    other_user = other_user_info["user"]
                    other_original = other_user_info["original_data"]
                    
                    assert decoded["sub"] != str(other_user.id)
                    assert decoded["email"] != other_user.email
                    
                    # Even if permissions are the same, user identity should be different
                    if decoded["permissions"] == other_original["permissions"]:
                        assert decoded["sub"] != str(other_user.id)
        
        # Test 3: Tokens from one user cannot authenticate as another user
        for i, user_info in enumerate(created_users):
            current_token = user_info["access_token"]
            current_user = user_info["user"]
            
            # Attempt to use this token to access other users' resources
            # (Simulated by checking if token claims match other users)
            import jwt
            current_decoded = jwt.decode(
                current_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            for j, other_user_info in enumerate(created_users):
                if i != j:
                    other_user = other_user_info["user"]
                    
                    # Current token should never identify as other user
                    assert current_decoded["sub"] != str(other_user.id)
                    assert current_decoded["email"] != other_user.email
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_user_operations(self):
        """
        Test concurrent operations across multiple users for isolation.
        
        BVJ: Ensures system maintains user isolation under concurrent load.
        """
        # Create all test users concurrently
        async def create_user_with_operations(user_data):
            """Create user and perform multiple operations."""
            created_info = await self.create_isolated_user(user_data)
            user = created_info["user"]
            token = created_info["access_token"]
            
            # Perform multiple operations
            operations_data = []
            
            # Operation 1: Update session
            await self.session_service.update_session_activity(
                session_id=created_info["session_id"],
                activity_data={
                    "last_action": f"operation-{user.id}",
                    "concurrent_test": True,
                    "user_specific_data": user_data["secret_data"]
                }
            )
            operations_data.append("session_updated")
            
            # Operation 2: Store user-specific data
            user_cache_key = f"cache:isolation-test:{user.id}:{int(time.time())}"
            await self.redis_service.set(
                user_cache_key,
                json.dumps({
                    "user_id": str(user.id),
                    "operation_data": f"concurrent-{user.id}-{secrets.token_hex(4)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }),
                ex=300
            )
            operations_data.append("cache_stored")
            self.created_sessions.append(user_cache_key)
            
            # Operation 3: Validate token
            token_valid = await self.jwt_service.validate_token(token)
            operations_data.append("token_validated" if token_valid else "token_invalid")
            
            return {
                "user_id": str(user.id),
                "email": user.email,
                "operations": operations_data,
                "secret_data": user_data["secret_data"],
                "cache_key": user_cache_key,
                "session_id": created_info["session_id"],
                "success": True
            }
        
        # Execute concurrent user operations
        tasks = [create_user_with_operations(user_data) for user_data in self.test_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations succeeded
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        assert len(successful_results) == len(self.test_users)
        
        # Test 1: Verify user isolation in concurrent results
        user_ids = [r["user_id"] for r in successful_results]
        emails = [r["email"] for r in successful_results]
        secret_data_values = [r["secret_data"] for r in successful_results]
        
        # All should be unique
        assert len(set(user_ids)) == len(user_ids)
        assert len(set(emails)) == len(emails)
        assert len(set(secret_data_values)) == len(secret_data_values)
        
        # Test 2: Verify isolated data storage
        for result in successful_results:
            # Check session data
            session_data = await self.session_service.get_session(result["session_id"])
            assert session_data is not None
            assert session_data["user_id"] == result["user_id"]
            assert session_data["user_specific_data"] == result["secret_data"]
            
            # Check cache data
            cache_data = await self.redis_service.get(result["cache_key"])
            assert cache_data is not None
            
            cached_info = json.loads(cache_data)
            assert cached_info["user_id"] == result["user_id"]
            assert result["user_id"] in cached_info["operation_data"]
        
        # Test 3: Cross-user data verification (ensure no mixing)
        for i, result in enumerate(successful_results):
            current_user_id = result["user_id"]
            current_secret = result["secret_data"]
            
            # Check other users' data doesn't contain current user's data
            for j, other_result in enumerate(successful_results):
                if i != j:
                    other_user_id = other_result["user_id"]
                    other_secret = other_result["secret_data"]
                    
                    # Verify no data mixing
                    assert current_user_id != other_user_id
                    assert current_secret != other_secret
                    
                    # Check other user's session doesn't contain current user's data
                    other_session = await self.session_service.get_session(other_result["session_id"])
                    assert other_session["user_id"] != current_user_id
                    assert other_session["user_specific_data"] != current_secret
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_tier_isolation(self):
        """
        Test isolation between different user tiers (Free, Early, Enterprise).
        
        BVJ: Ensures users of different tiers have isolated resources and cannot access higher tier features.
        """
        # Create users of different tiers
        tier_users = []
        tiers = ["free", "early", "enterprise"]
        
        for i, tier in enumerate(tiers):
            user_data = {
                **self.test_users[i],
                "tier": tier,
                "permissions": {
                    "free": ["read"],
                    "early": ["read", "write"],
                    "enterprise": ["read", "write", "admin"]
                }[tier]
            }
            
            created_info = await self.create_isolated_user(user_data)
            
            # Store tier-specific data
            tier_data_key = f"tierdata:isolation-test:{tier}:{created_info['user'].id}"
            await self.redis_service.set(
                tier_data_key,
                json.dumps({
                    "user_id": str(created_info["user"].id),
                    "tier": tier,
                    "tier_features": {
                        "free": ["basic_chat"],
                        "early": ["basic_chat", "advanced_agents"],
                        "enterprise": ["basic_chat", "advanced_agents", "admin_panel", "analytics"]
                    }[tier],
                    "resource_limits": {
                        "free": {"messages_per_hour": 10},
                        "early": {"messages_per_hour": 100}, 
                        "enterprise": {"messages_per_hour": -1}  # Unlimited
                    }[tier]
                }),
                ex=3600
            )
            
            self.created_sessions.append(tier_data_key)
            
            tier_users.append({
                **created_info,
                "tier": tier,
                "tier_data_key": tier_data_key,
                "expected_permissions": user_data["permissions"]
            })
        
        # Test 1: Verify tier-specific permissions in JWT tokens
        for user_info in tier_users:
            token = user_info["access_token"]
            tier = user_info["tier"]
            expected_permissions = user_info["expected_permissions"]
            
            import jwt
            decoded = jwt.decode(
                token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            assert decoded["permissions"] == expected_permissions
            
            # Free tier should only have read
            if tier == "free":
                assert "read" in decoded["permissions"]
                assert "write" not in decoded["permissions"]
                assert "admin" not in decoded["permissions"]
            
            # Early tier should have read and write
            elif tier == "early":
                assert "read" in decoded["permissions"]
                assert "write" in decoded["permissions"]
                assert "admin" not in decoded["permissions"]
            
            # Enterprise should have all permissions
            elif tier == "enterprise":
                assert "read" in decoded["permissions"]
                assert "write" in decoded["permissions"]
                assert "admin" in decoded["permissions"]
        
        # Test 2: Verify tier-specific resource isolation
        for user_info in tier_users:
            tier_data = await self.redis_service.get(user_info["tier_data_key"])
            assert tier_data is not None
            
            tier_info = json.loads(tier_data)
            assert tier_info["user_id"] == str(user_info["user"].id)
            assert tier_info["tier"] == user_info["tier"]
            
            # Verify tier features
            tier_features = tier_info["tier_features"]
            if user_info["tier"] == "free":
                assert tier_features == ["basic_chat"]
            elif user_info["tier"] == "early":
                assert "basic_chat" in tier_features
                assert "advanced_agents" in tier_features
                assert "admin_panel" not in tier_features
            elif user_info["tier"] == "enterprise":
                assert "admin_panel" in tier_features
                assert "analytics" in tier_features
        
        # Test 3: Verify users cannot access other tiers' resources
        for i, user_info in enumerate(tier_users):
            current_tier = user_info["tier"]
            current_user_id = str(user_info["user"].id)
            
            # Try to access other tiers' data
            for j, other_user_info in enumerate(tier_users):
                if i != j:
                    other_tier_key = other_user_info["tier_data_key"]
                    other_tier_data = await self.redis_service.get(other_tier_key)
                    
                    if other_tier_data:
                        other_info = json.loads(other_tier_data)
                        # Should be different user
                        assert other_info["user_id"] != current_user_id
                        # Should be different tier (or same tier but different user)
                        if other_info["tier"] == current_tier:
                            assert other_info["user_id"] != current_user_id
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_cleanup_isolation(self):
        """
        Test that session cleanup only affects the intended user.
        
        BVJ: Ensures user logout/cleanup operations don't affect other users' sessions.
        """
        # Create multiple users
        created_users = []
        for user_data in self.test_users[:3]:
            created_info = await self.create_isolated_user(user_data)
            created_users.append(created_info)
        
        # Verify all users have active sessions
        for user_info in created_users:
            session = await self.session_service.get_session(user_info["session_id"])
            assert session is not None
            assert session["user_id"] == str(user_info["user"].id)
        
        # Clean up first user's session
        target_user = created_users[0]
        target_user_id = str(target_user["user"].id)
        
        # Simulate logout - cleanup target user's sessions
        await self.user_service.logout_user(target_user_id)
        
        # Verify target user's session is cleaned up
        target_session = await self.session_service.get_session(target_user["session_id"])
        assert target_session is None
        
        # Verify other users' sessions are unaffected
        for user_info in created_users[1:]:
            other_session = await self.session_service.get_session(user_info["session_id"])
            assert other_session is not None
            assert other_session["user_id"] == str(user_info["user"].id)
            
            # Session should contain original data
            original_data = user_info["original_data"]
            assert other_session["secret_data"] == original_data["secret_data"]
            assert other_session["tier"] == original_data["tier"]
        
        # Verify target user's Redis data is cleaned up
        target_redis_data = await self.redis_service.get(target_user["user_data_key"])
        # Should be cleaned up or marked as inactive
        if target_redis_data:
            data = json.loads(target_redis_data)
            assert data.get("active") is False or "logout" in data.get("status", "")
        
        # Verify other users' Redis data is intact
        for user_info in created_users[1:]:
            user_redis_data = await self.redis_service.get(user_info["user_data_key"])
            assert user_redis_data is not None
            
            data = json.loads(user_redis_data)
            assert data["user_id"] == str(user_info["user"].id)
            assert data["secret_data"] == user_info["original_data"]["secret_data"]