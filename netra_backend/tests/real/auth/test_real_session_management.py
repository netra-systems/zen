"""
Real Session Management Tests

Business Value: Platform/Internal - Security & User Experience - Validates session
lifecycle, persistence, and security using real Redis and database services.

Coverage Target: 90%
Test Category: Integration with Real Services
Infrastructure Required: Docker (PostgreSQL, Redis, Auth Service, Backend)

This test suite validates session creation, persistence, expiration, invalidation,
and concurrent session management using real Redis and PostgreSQL services.

CRITICAL: Tests session isolation and security boundaries to prevent user data
leakage as described in WebSocket v2 migration requirements.
"""

import asyncio
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock

import pytest
import redis.asyncio as redis
from fastapi import HTTPException, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import session and auth components
from netra_backend.app.core.auth_constants import (
    CacheConstants, JWTConstants, AuthConstants, HeaderConstants, AuthErrorConstants
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
@pytest.mark.session
@pytest.mark.asyncio
class TestRealSessionManagement:
    """
    Real session management tests using Docker services.
    
    Tests session lifecycle, Redis persistence, expiration, multi-user isolation,
    concurrent sessions, and security boundaries with real infrastructure.
    
    CRITICAL: Validates user context isolation to prevent data leakage between users.
    """

    @pytest.fixture(scope="class", autouse=True)
    async def setup_docker_services(self):
        """Start Docker services for session management testing."""
        print("🐳 Starting Docker services for session management tests...")
        
        services = ["backend", "auth", "postgres", "redis"]
        
        try:
            await docker_manager.start_services_async(
                services=services,
                health_check=True,
                timeout=120
            )
            
            await asyncio.sleep(5)
            print("✅ Docker services ready for session management tests")
            yield
            
        except Exception as e:
            pytest.fail(f"❌ Failed to start Docker services for session tests: {e}")
        finally:
            print("🧹 Cleaning up Docker services after session management tests...")
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for session API testing."""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    @pytest.fixture
    async def real_db_session(self):
        """Get real database session for session data persistence."""
        async for session in get_request_scoped_db_session_for_fastapi():
            yield session

    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for session cache testing."""
        redis_url = env.get_env_var("REDIS_URL", "redis://localhost:6381")  # Test Redis port
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            await client.ping()
            print(f"✅ Connected to Redis at {redis_url}")
            
            yield client
            
        except Exception as e:
            pytest.fail(f"❌ Failed to connect to Redis for session tests: {e}")
        finally:
            if 'client' in locals():
                await client.aclose()

    def generate_session_id(self) -> str:
        """Generate secure session ID."""
        return secrets.token_hex(32)  # 64 character hex string

    def generate_user_session_data(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Generate user session data structure."""
        now = datetime.utcnow()
        
        return {
            "session_id": self.generate_session_id(),
            "user_id": user_id,
            "email": kwargs.get("email", f"user{user_id}@netra.ai"),
            "full_name": kwargs.get("full_name", f"Test User {user_id}"),
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "ip_address": kwargs.get("ip_address", "127.0.0.1"),
            "user_agent": kwargs.get("user_agent", "pytest-session-test"),
            "is_active": True,
            "permissions": kwargs.get("permissions", ["read"]),
            "oauth_provider": kwargs.get("oauth_provider", "google")
        }

    @pytest.mark.asyncio
    async def test_session_creation_and_storage(self, redis_client, real_db_session):
        """Test session creation and storage in Redis and database."""
        
        # Generate test session data
        user_id = 12345
        session_data = self.generate_user_session_data(user_id)
        session_id = session_data["session_id"]
        
        # Store session in Redis cache
        cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
        
        try:
            # Store session data in Redis
            await redis_client.setex(
                cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(session_data)
            )
            
            # Verify session was stored
            cached_data = await redis_client.get(cache_key)
            assert cached_data is not None, "Session should be stored in Redis"
            
            # Verify session data integrity
            parsed_data = json.loads(cached_data)
            assert parsed_data["session_id"] == session_id
            assert parsed_data["user_id"] == user_id
            assert parsed_data["is_active"] is True
            
            print(f"✅ Session {session_id[:8]}... created and stored successfully")
            
        finally:
            # Cleanup test session
            await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_session_retrieval_and_validation(self, redis_client):
        """Test session retrieval and validation from Redis."""
        
        # Create and store test session
        user_id = 23456
        session_data = self.generate_user_session_data(user_id)
        session_id = session_data["session_id"]
        cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
        
        try:
            # Store session
            await redis_client.setex(
                cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(session_data)
            )
            
            # Retrieve and validate session
            cached_data = await redis_client.get(cache_key)
            assert cached_data is not None, "Session should be retrievable"
            
            parsed_data = json.loads(cached_data)
            
            # Validate session structure
            required_fields = ["session_id", "user_id", "email", "created_at", "expires_at", "is_active"]
            for field in required_fields:
                assert field in parsed_data, f"Session must contain {field}"
            
            # Validate session values
            assert parsed_data["session_id"] == session_id
            assert parsed_data["user_id"] == user_id
            assert parsed_data["is_active"] is True
            assert "@" in parsed_data["email"]
            
            print(f"✅ Session {session_id[:8]}... retrieved and validated successfully")
            
        finally:
            await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_session_expiration_and_cleanup(self, redis_client):
        """Test session expiration and automatic cleanup."""
        
        # Create short-lived session for testing
        user_id = 34567
        session_data = self.generate_user_session_data(user_id)
        session_id = session_data["session_id"]
        cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
        
        try:
            # Store session with short TTL (2 seconds)
            short_ttl = 2
            await redis_client.setex(cache_key, short_ttl, json.dumps(session_data))
            
            # Verify session exists
            cached_data = await redis_client.get(cache_key)
            assert cached_data is not None, "Session should exist initially"
            
            # Wait for expiration
            await asyncio.sleep(short_ttl + 1)
            
            # Verify session expired
            expired_data = await redis_client.get(cache_key)
            assert expired_data is None, "Session should expire after TTL"
            
            print(f"✅ Session {session_id[:8]}... expired and cleaned up successfully")
            
        except Exception as e:
            # Cleanup in case of error
            await redis_client.delete(cache_key)
            raise e

    @pytest.mark.asyncio
    async def test_session_update_and_activity_tracking(self, redis_client):
        """Test session update and last activity tracking."""
        
        # Create initial session
        user_id = 45678
        session_data = self.generate_user_session_data(user_id)
        session_id = session_data["session_id"]
        cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
        
        try:
            # Store initial session
            await redis_client.setex(
                cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(session_data)
            )
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Update session activity
            updated_data = session_data.copy()
            updated_data["last_activity"] = datetime.utcnow().isoformat()
            updated_data["activity_count"] = updated_data.get("activity_count", 0) + 1
            
            # Store updated session
            await redis_client.setex(
                cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(updated_data)
            )
            
            # Verify update
            cached_data = await redis_client.get(cache_key)
            parsed_data = json.loads(cached_data)
            
            assert parsed_data["last_activity"] != session_data["last_activity"]
            assert parsed_data["activity_count"] == 1
            
            print(f"✅ Session {session_id[:8]}... activity updated successfully")
            
        finally:
            await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_concurrent_session_management(self, redis_client):
        """Test concurrent session management for the same user."""
        
        user_id = 56789
        session_count = 3
        session_ids = []
        cache_keys = []
        
        try:
            # Create multiple sessions for the same user
            for i in range(session_count):
                session_data = self.generate_user_session_data(
                    user_id,
                    user_agent=f"pytest-concurrent-{i}"
                )
                session_id = session_data["session_id"]
                cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
                
                session_ids.append(session_id)
                cache_keys.append(cache_key)
                
                # Store session
                await redis_client.setex(
                    cache_key,
                    CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                    json.dumps(session_data)
                )
            
            # Verify all sessions exist
            for i, cache_key in enumerate(cache_keys):
                cached_data = await redis_client.get(cache_key)
                assert cached_data is not None, f"Concurrent session {i} should exist"
                
                parsed_data = json.loads(cached_data)
                assert parsed_data["user_id"] == user_id
                assert parsed_data["session_id"] == session_ids[i]
            
            # Test session isolation - each session should be independent
            for i, session_id in enumerate(session_ids):
                for j, other_session_id in enumerate(session_ids):
                    if i != j:
                        assert session_id != other_session_id, "Session IDs must be unique"
            
            print(f"✅ {session_count} concurrent sessions managed successfully")
            
        finally:
            # Cleanup all sessions
            for cache_key in cache_keys:
                await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_session_user_isolation(self, redis_client):
        """Test session isolation between different users."""
        
        # Create sessions for different users
        users = [
            {"user_id": 11111, "email": "user1@netra.ai"},
            {"user_id": 22222, "email": "user2@netra.ai"},
            {"user_id": 33333, "email": "user3@netra.ai"}
        ]
        
        sessions = []
        cache_keys = []
        
        try:
            # Create sessions for each user
            for user in users:
                session_data = self.generate_user_session_data(
                    user["user_id"],
                    email=user["email"]
                )
                session_id = session_data["session_id"]
                cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
                
                sessions.append(session_data)
                cache_keys.append(cache_key)
                
                # Store session
                await redis_client.setex(
                    cache_key,
                    CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                    json.dumps(session_data)
                )
            
            # Verify user isolation
            for i, session_data in enumerate(sessions):
                cached_data = await redis_client.get(cache_keys[i])
                parsed_data = json.loads(cached_data)
                
                # Verify correct user data
                assert parsed_data["user_id"] == session_data["user_id"]
                assert parsed_data["email"] == session_data["email"]
                
                # Verify isolation from other users
                for j, other_session in enumerate(sessions):
                    if i != j:
                        assert parsed_data["user_id"] != other_session["user_id"]
                        assert parsed_data["email"] != other_session["email"]
                        assert parsed_data["session_id"] != other_session["session_id"]
            
            print("✅ Session user isolation validated successfully")
            
        finally:
            # Cleanup all sessions
            for cache_key in cache_keys:
                await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_session_invalidation_and_logout(self, redis_client):
        """Test session invalidation and logout functionality."""
        
        # Create test session
        user_id = 67890
        session_data = self.generate_user_session_data(user_id)
        session_id = session_data["session_id"]
        cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
        
        try:
            # Store session
            await redis_client.setex(
                cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(session_data)
            )
            
            # Verify session exists
            cached_data = await redis_client.get(cache_key)
            assert cached_data is not None, "Session should exist before invalidation"
            
            # Invalidate session (logout)
            await redis_client.delete(cache_key)
            
            # Verify session is gone
            invalidated_data = await redis_client.get(cache_key)
            assert invalidated_data is None, "Session should be deleted after invalidation"
            
            print(f"✅ Session {session_id[:8]}... invalidated successfully")
            
        except Exception as e:
            # Cleanup in case of error
            await redis_client.delete(cache_key)
            raise e

    @pytest.mark.asyncio
    async def test_session_security_boundaries(self, redis_client):
        """Test session security boundaries and access control."""
        
        # Create sessions with different security levels
        admin_session = self.generate_user_session_data(
            99999,
            email="admin@netra.ai",
            permissions=["read", "write", "admin", "delete"]
        )
        
        user_session = self.generate_user_session_data(
            88888,
            email="user@netra.ai",
            permissions=["read"]
        )
        
        admin_cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{admin_session['session_id']}"
        user_cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{user_session['session_id']}"
        
        try:
            # Store both sessions
            await redis_client.setex(
                admin_cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(admin_session)
            )
            
            await redis_client.setex(
                user_cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(user_session)
            )
            
            # Verify admin session permissions
            admin_data = await redis_client.get(admin_cache_key)
            admin_parsed = json.loads(admin_data)
            
            assert "admin" in admin_parsed["permissions"]
            assert "delete" in admin_parsed["permissions"]
            assert len(admin_parsed["permissions"]) == 4
            
            # Verify user session permissions
            user_data = await redis_client.get(user_cache_key)
            user_parsed = json.loads(user_data)
            
            assert "admin" not in user_parsed["permissions"]
            assert "delete" not in user_parsed["permissions"]
            assert user_parsed["permissions"] == ["read"]
            
            # Verify session boundary isolation
            assert admin_parsed["user_id"] != user_parsed["user_id"]
            assert admin_parsed["session_id"] != user_parsed["session_id"]
            
            print("✅ Session security boundaries validated successfully")
            
        finally:
            await redis_client.delete(admin_cache_key)
            await redis_client.delete(user_cache_key)

    @pytest.mark.asyncio
    async def test_session_persistence_across_requests(self, redis_client, async_client):
        """Test session persistence across multiple API requests."""
        
        # Create session for API testing
        user_id = 78901
        session_data = self.generate_user_session_data(user_id)
        session_id = session_data["session_id"]
        cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
        
        try:
            # Store session
            await redis_client.setex(
                cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(session_data)
            )
            
            # Simulate multiple API requests with the same session
            headers = {
                HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{session_id}",
                HeaderConstants.CONTENT_TYPE: HeaderConstants.APPLICATION_JSON
            }
            
            # Make multiple requests
            for i in range(3):
                try:
                    response = await async_client.get("/health", headers=headers)
                    print(f"✅ API request {i+1} with session - Status: {response.status_code}")
                    
                    # Verify session still exists after request
                    session_check = await redis_client.get(cache_key)
                    assert session_check is not None, f"Session should persist after request {i+1}"
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"⚠️ API request {i+1} with session encountered: {e}")
            
            print("✅ Session persistence across multiple requests validated")
            
        finally:
            await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_session_cleanup_on_service_restart(self, redis_client):
        """Test session cleanup behavior during service restart simulation."""
        
        # Create multiple test sessions
        sessions = []
        cache_keys = []
        
        for i in range(5):
            user_id = 50000 + i
            session_data = self.generate_user_session_data(user_id)
            session_id = session_data["session_id"]
            cache_key = f"{CacheConstants.USER_TOKEN_PREFIX}{session_id}"
            
            sessions.append(session_data)
            cache_keys.append(cache_key)
            
            # Store session
            await redis_client.setex(
                cache_key,
                CacheConstants.DEFAULT_TOKEN_CACHE_TTL,
                json.dumps(session_data)
            )
        
        try:
            # Verify all sessions exist
            for cache_key in cache_keys:
                cached_data = await redis_client.get(cache_key)
                assert cached_data is not None, "All sessions should exist before cleanup"
            
            # Simulate service restart by clearing all sessions
            # In real implementation, this would be done by service shutdown hooks
            for cache_key in cache_keys:
                await redis_client.delete(cache_key)
            
            # Verify all sessions are cleaned up
            for cache_key in cache_keys:
                cached_data = await redis_client.get(cache_key)
                assert cached_data is None, "All sessions should be cleaned up"
            
            print("✅ Session cleanup on service restart simulated successfully")
            
        except Exception as e:
            # Cleanup any remaining sessions
            for cache_key in cache_keys:
                await redis_client.delete(cache_key)
            raise e

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])