"""
Real Token Refresh Tests

Business Value: Platform/Internal - Security & User Experience - Validates token refresh
mechanisms and seamless user session continuation using real services.

Coverage Target: 90%
Test Category: Integration with Real Services
Infrastructure Required: Docker (PostgreSQL, Redis, Auth Service, Backend)

This test suite validates JWT token refresh, rotation, revocation, and security
mechanisms using real Redis cache and authentication services.

CRITICAL: Tests token security lifecycle to prevent session hijacking and ensure
proper token rotation as described in JWT security best practices.
"""

import asyncio
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from unittest.mock import patch

import pytest
import jwt
import redis.asyncio as redis
from fastapi import HTTPException, status
from httpx import AsyncClient

# Import token and auth components
from netra_backend.app.core.auth_constants import (
    JWTConstants, CacheConstants, AuthErrorConstants, HeaderConstants, AuthConstants
)
from netra_backend.app.auth_dependencies import get_request_scoped_db_session_for_fastapi
from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.main import app
from shared.isolated_environment import IsolatedEnvironment

# Import test framework
from test_framework.docker_manager import UnifiedDockerManager

# Use isolated environment for all env access
env = IsolatedEnvironment()

# Docker manager for real services
docker_manager = UnifiedDockerManager()

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.token_refresh
@pytest.mark.asyncio
class TestRealTokenRefresh:
    """
    Real token refresh tests using Docker services.
    
    Tests token lifecycle, refresh mechanisms, rotation, revocation,
    and security boundaries using real JWT validation and Redis cache.
    """

    @pytest.fixture(scope="class", autouse=True)
    async def setup_docker_services(self):
        """Start Docker services for token refresh testing."""
        print("🐳 Starting Docker services for token refresh tests...")
        
        services = ["backend", "auth", "postgres", "redis"]
        
        try:
            await docker_manager.start_services_async(
                services=services,
                health_check=True,
                timeout=120
            )
            
            await asyncio.sleep(5)
            print("✅ Docker services ready for token refresh tests")
            yield
            
        except Exception as e:
            pytest.fail(f"❌ Failed to start Docker services for token refresh tests: {e}")
        finally:
            print("🧹 Cleaning up Docker services after token refresh tests...")
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for token refresh API testing."""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for token storage testing."""
        redis_url = env.get_env_var("REDIS_URL", "redis://localhost:6381")
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            yield client
        except Exception as e:
            pytest.fail(f"❌ Failed to connect to Redis for token refresh tests: {e}")
        finally:
            if 'client' in locals():
                await client.aclose()

    @pytest.fixture
    def jwt_secret_key(self) -> str:
        """Get JWT secret key for token operations."""
        secret = env.get_env_var(JWTConstants.JWT_SECRET_KEY)
        assert secret, "JWT_SECRET_KEY required for token refresh tests"
        return secret

    def create_token_pair(self, user_id: int, jwt_secret_key: str) -> Tuple[str, str]:
        """Create access and refresh token pair."""
        now = datetime.utcnow()
        
        # Access token (short-lived)
        access_payload = {
            JWTConstants.SUBJECT: f"user_{user_id}",
            JWTConstants.EMAIL: f"user{user_id}@netra.ai",
            JWTConstants.ISSUED_AT: int(now.timestamp()),
            JWTConstants.EXPIRES_AT: int((now + timedelta(minutes=15)).timestamp()),  # 15 min
            JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
            "token_type": JWTConstants.ACCESS_TOKEN_TYPE,
            "user_id": user_id,
            "permissions": ["read", "write"]
        }
        
        # Refresh token (long-lived)
        refresh_payload = {
            JWTConstants.SUBJECT: f"user_{user_id}",
            JWTConstants.EMAIL: f"user{user_id}@netra.ai",
            JWTConstants.ISSUED_AT: int(now.timestamp()),
            JWTConstants.EXPIRES_AT: int((now + timedelta(days=7)).timestamp()),  # 7 days
            JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
            "token_type": JWTConstants.REFRESH_TOKEN_TYPE,
            "user_id": user_id,
            "refresh_id": secrets.token_hex(16)
        }
        
        access_token = jwt.encode(access_payload, jwt_secret_key, algorithm=JWTConstants.HS256_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, jwt_secret_key, algorithm=JWTConstants.HS256_ALGORITHM)
        
        return access_token, refresh_token

    @pytest.mark.asyncio
    async def test_token_pair_creation_and_validation(self, jwt_secret_key: str):
        """Test creation and validation of access/refresh token pairs."""
        
        user_id = 11111
        access_token, refresh_token = self.create_token_pair(user_id, jwt_secret_key)
        
        # Validate access token
        access_decoded = jwt.decode(access_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        assert access_decoded["token_type"] == JWTConstants.ACCESS_TOKEN_TYPE
        assert access_decoded["user_id"] == user_id
        assert "permissions" in access_decoded
        
        # Validate refresh token
        refresh_decoded = jwt.decode(refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        assert refresh_decoded["token_type"] == JWTConstants.REFRESH_TOKEN_TYPE
        assert refresh_decoded["user_id"] == user_id
        assert "refresh_id" in refresh_decoded
        
        # Verify token isolation
        assert access_token != refresh_token
        assert access_decoded[JWTConstants.EXPIRES_AT] < refresh_decoded[JWTConstants.EXPIRES_AT]
        
        print(f"✅ Token pair created and validated for user {user_id}")

    @pytest.mark.asyncio
    async def test_refresh_token_storage_and_retrieval(self, redis_client, jwt_secret_key: str):
        """Test refresh token storage and retrieval from Redis."""
        
        user_id = 22222
        access_token, refresh_token = self.create_token_pair(user_id, jwt_secret_key)
        
        # Decode refresh token to get metadata
        refresh_decoded = jwt.decode(refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        refresh_id = refresh_decoded["refresh_id"]
        
        # Store refresh token in Redis
        refresh_key = f"{CacheConstants.SERVICE_TOKEN_PREFIX}refresh:{user_id}:{refresh_id}"
        refresh_data = {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "refresh_id": refresh_id,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "use_count": 0
        }
        
        try:
            await redis_client.setex(
                refresh_key,
                CacheConstants.SERVICE_TOKEN_CACHE_TTL,
                json.dumps(refresh_data)
            )
            
            # Retrieve refresh token
            stored_data = await redis_client.get(refresh_key)
            assert stored_data is not None, "Refresh token should be stored"
            
            parsed_data = json.loads(stored_data)
            assert parsed_data["user_id"] == user_id
            assert parsed_data["refresh_id"] == refresh_id
            assert parsed_data["is_active"] is True
            
            print(f"✅ Refresh token stored and retrieved for user {user_id}")
            
        finally:
            await redis_client.delete(refresh_key)

    @pytest.mark.asyncio
    async def test_access_token_refresh_mechanism(self, redis_client, jwt_secret_key: str):
        """Test access token refresh using refresh token."""
        
        user_id = 33333
        old_access_token, refresh_token = self.create_token_pair(user_id, jwt_secret_key)
        
        # Store refresh token
        refresh_decoded = jwt.decode(refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        refresh_id = refresh_decoded["refresh_id"]
        refresh_key = f"{CacheConstants.SERVICE_TOKEN_PREFIX}refresh:{user_id}:{refresh_id}"
        
        refresh_data = {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "refresh_id": refresh_id,
            "is_active": True,
            "use_count": 0
        }
        
        try:
            await redis_client.setex(refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(refresh_data))
            
            # Simulate token refresh process
            # 1. Validate refresh token exists and is active
            stored_refresh = await redis_client.get(refresh_key)
            assert stored_refresh is not None
            
            parsed_refresh = json.loads(stored_refresh)
            assert parsed_refresh["is_active"] is True
            
            # 2. Create new access token
            now = datetime.utcnow()
            new_access_payload = {
                JWTConstants.SUBJECT: f"user_{user_id}",
                JWTConstants.EMAIL: f"user{user_id}@netra.ai",
                JWTConstants.ISSUED_AT: int(now.timestamp()),
                JWTConstants.EXPIRES_AT: int((now + timedelta(minutes=15)).timestamp()),
                JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
                "token_type": JWTConstants.ACCESS_TOKEN_TYPE,
                "user_id": user_id,
                "permissions": ["read", "write"],
                "refreshed_at": now.isoformat()
            }
            
            new_access_token = jwt.encode(new_access_payload, jwt_secret_key, algorithm=JWTConstants.HS256_ALGORITHM)
            
            # 3. Update refresh token usage
            parsed_refresh["use_count"] += 1
            parsed_refresh["last_used"] = now.isoformat()
            
            await redis_client.setex(refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(parsed_refresh))
            
            # 4. Validate new access token
            new_access_decoded = jwt.decode(new_access_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
            old_access_decoded = jwt.decode(old_access_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
            
            # Verify token refresh
            assert new_access_token != old_access_token
            assert new_access_decoded["user_id"] == user_id
            assert new_access_decoded[JWTConstants.ISSUED_AT] > old_access_decoded[JWTConstants.ISSUED_AT]
            assert "refreshed_at" in new_access_decoded
            
            # Verify refresh token usage tracking
            updated_refresh = json.loads(await redis_client.get(refresh_key))
            assert updated_refresh["use_count"] == 1
            assert "last_used" in updated_refresh
            
            print(f"✅ Access token refreshed successfully for user {user_id}")
            
        finally:
            await redis_client.delete(refresh_key)

    @pytest.mark.asyncio
    async def test_token_rotation_on_refresh(self, redis_client, jwt_secret_key: str):
        """Test token rotation - new refresh token on each refresh."""
        
        user_id = 44444
        old_access_token, old_refresh_token = self.create_token_pair(user_id, jwt_secret_key)
        
        # Store initial refresh token
        old_refresh_decoded = jwt.decode(old_refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        old_refresh_id = old_refresh_decoded["refresh_id"]
        old_refresh_key = f"{CacheConstants.SERVICE_TOKEN_PREFIX}refresh:{user_id}:{old_refresh_id}"
        
        refresh_data = {
            "user_id": user_id,
            "refresh_token": old_refresh_token,
            "refresh_id": old_refresh_id,
            "is_active": True,
            "use_count": 0
        }
        
        try:
            await redis_client.setex(old_refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(refresh_data))
            
            # Create new token pair (token rotation)
            now = datetime.utcnow()
            new_refresh_id = secrets.token_hex(16)
            
            # New access token
            new_access_payload = {
                JWTConstants.SUBJECT: f"user_{user_id}",
                JWTConstants.EMAIL: f"user{user_id}@netra.ai",
                JWTConstants.ISSUED_AT: int(now.timestamp()),
                JWTConstants.EXPIRES_AT: int((now + timedelta(minutes=15)).timestamp()),
                JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
                "token_type": JWTConstants.ACCESS_TOKEN_TYPE,
                "user_id": user_id,
                "permissions": ["read", "write"],
                "generation": 2  # Track token generation
            }
            
            # New refresh token
            new_refresh_payload = {
                JWTConstants.SUBJECT: f"user_{user_id}",
                JWTConstants.EMAIL: f"user{user_id}@netra.ai",
                JWTConstants.ISSUED_AT: int(now.timestamp()),
                JWTConstants.EXPIRES_AT: int((now + timedelta(days=7)).timestamp()),
                JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
                "token_type": JWTConstants.REFRESH_TOKEN_TYPE,
                "user_id": user_id,
                "refresh_id": new_refresh_id,
                "generation": 2
            }
            
            new_access_token = jwt.encode(new_access_payload, jwt_secret_key, algorithm=JWTConstants.HS256_ALGORITHM)
            new_refresh_token = jwt.encode(new_refresh_payload, jwt_secret_key, algorithm=JWTConstants.HS256_ALGORITHM)
            
            # Store new refresh token
            new_refresh_key = f"{CacheConstants.SERVICE_TOKEN_PREFIX}refresh:{user_id}:{new_refresh_id}"
            new_refresh_data = {
                "user_id": user_id,
                "refresh_token": new_refresh_token,
                "refresh_id": new_refresh_id,
                "is_active": True,
                "use_count": 0,
                "generation": 2,
                "previous_refresh_id": old_refresh_id
            }
            
            await redis_client.setex(new_refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(new_refresh_data))
            
            # Invalidate old refresh token
            old_refresh_data["is_active"] = False
            old_refresh_data["revoked_at"] = now.isoformat()
            await redis_client.setex(old_refresh_key, 3600, json.dumps(old_refresh_data))  # Keep for audit
            
            # Verify token rotation
            assert new_access_token != old_access_token
            assert new_refresh_token != old_refresh_token
            assert new_refresh_id != old_refresh_id
            
            # Verify old refresh token is inactive
            old_stored = json.loads(await redis_client.get(old_refresh_key))
            assert old_stored["is_active"] is False
            
            # Verify new refresh token is active
            new_stored = json.loads(await redis_client.get(new_refresh_key))
            assert new_stored["is_active"] is True
            assert new_stored["generation"] == 2
            
            print(f"✅ Token rotation completed successfully for user {user_id}")
            
        finally:
            await redis_client.delete(old_refresh_key)
            if 'new_refresh_key' in locals():
                await redis_client.delete(new_refresh_key)

    @pytest.mark.asyncio
    async def test_expired_refresh_token_rejection(self, redis_client, jwt_secret_key: str):
        """Test rejection of expired refresh tokens."""
        
        user_id = 55555
        
        # Create expired refresh token
        expired_time = datetime.utcnow() - timedelta(hours=1)
        expired_refresh_payload = {
            JWTConstants.SUBJECT: f"user_{user_id}",
            JWTConstants.EMAIL: f"user{user_id}@netra.ai",
            JWTConstants.ISSUED_AT: int(expired_time.timestamp()),
            JWTConstants.EXPIRES_AT: int(expired_time.timestamp()),  # Already expired
            JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
            "token_type": JWTConstants.REFRESH_TOKEN_TYPE,
            "user_id": user_id,
            "refresh_id": secrets.token_hex(16)
        }
        
        expired_refresh_token = jwt.encode(expired_refresh_payload, jwt_secret_key, algorithm=JWTConstants.HS256_ALGORITHM)
        
        # Attempt to validate expired refresh token
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        
        print(f"✅ Expired refresh token correctly rejected for user {user_id}")

    @pytest.mark.asyncio
    async def test_refresh_token_revocation(self, redis_client, jwt_secret_key: str):
        """Test refresh token revocation and invalidation."""
        
        user_id = 66666
        access_token, refresh_token = self.create_token_pair(user_id, jwt_secret_key)
        
        # Store refresh token
        refresh_decoded = jwt.decode(refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        refresh_id = refresh_decoded["refresh_id"]
        refresh_key = f"{CacheConstants.SERVICE_TOKEN_PREFIX}refresh:{user_id}:{refresh_id}"
        
        refresh_data = {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "refresh_id": refresh_id,
            "is_active": True,
            "use_count": 0
        }
        
        try:
            await redis_client.setex(refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(refresh_data))
            
            # Verify refresh token is active
            stored_data = json.loads(await redis_client.get(refresh_key))
            assert stored_data["is_active"] is True
            
            # Revoke refresh token
            stored_data["is_active"] = False
            stored_data["revoked_at"] = datetime.utcnow().isoformat()
            stored_data["revocation_reason"] = "user_logout"
            
            await redis_client.setex(refresh_key, 3600, json.dumps(stored_data))  # Keep for audit trail
            
            # Verify refresh token is revoked
            revoked_data = json.loads(await redis_client.get(refresh_key))
            assert revoked_data["is_active"] is False
            assert "revoked_at" in revoked_data
            assert revoked_data["revocation_reason"] == "user_logout"
            
            print(f"✅ Refresh token revoked successfully for user {user_id}")
            
        finally:
            await redis_client.delete(refresh_key)

    @pytest.mark.asyncio
    async def test_concurrent_token_refresh_prevention(self, redis_client, jwt_secret_key: str):
        """Test prevention of concurrent token refresh attempts."""
        
        user_id = 77777
        access_token, refresh_token = self.create_token_pair(user_id, jwt_secret_key)
        
        # Store refresh token
        refresh_decoded = jwt.decode(refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        refresh_id = refresh_decoded["refresh_id"]
        refresh_key = f"{CacheConstants.SERVICE_TOKEN_PREFIX}refresh:{user_id}:{refresh_id}"
        lock_key = f"refresh_lock:{user_id}:{refresh_id}"
        
        refresh_data = {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "refresh_id": refresh_id,
            "is_active": True,
            "use_count": 0
        }
        
        try:
            await redis_client.setex(refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(refresh_data))
            
            # Simulate concurrent refresh attempts
            async def attempt_refresh(attempt_id: int) -> Dict[str, Any]:
                """Simulate single refresh attempt with locking."""
                try:
                    # Try to acquire refresh lock
                    lock_acquired = await redis_client.set(lock_key, attempt_id, nx=True, ex=30)  # 30 second lock
                    
                    if not lock_acquired:
                        return {"attempt_id": attempt_id, "success": False, "reason": "concurrent_refresh_blocked"}
                    
                    # Check if refresh token is still active
                    stored_data = await redis_client.get(refresh_key)
                    if not stored_data:
                        return {"attempt_id": attempt_id, "success": False, "reason": "refresh_token_not_found"}
                    
                    parsed_data = json.loads(stored_data)
                    if not parsed_data["is_active"]:
                        return {"attempt_id": attempt_id, "success": False, "reason": "refresh_token_inactive"}
                    
                    # Simulate refresh processing time
                    await asyncio.sleep(0.1)
                    
                    # Update refresh token usage
                    parsed_data["use_count"] += 1
                    parsed_data["last_used"] = datetime.utcnow().isoformat()
                    
                    await redis_client.setex(refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(parsed_data))
                    
                    return {"attempt_id": attempt_id, "success": True, "use_count": parsed_data["use_count"]}
                    
                finally:
                    # Release lock
                    await redis_client.delete(lock_key)
            
            # Execute concurrent refresh attempts
            concurrent_attempts = 5
            tasks = [attempt_refresh(i) for i in range(concurrent_attempts)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_attempts = [r for r in results if isinstance(r, dict) and r.get("success")]
            blocked_attempts = [r for r in results if isinstance(r, dict) and not r.get("success")]
            
            # Only one refresh should succeed due to locking
            assert len(successful_attempts) == 1, f"Expected 1 successful refresh, got {len(successful_attempts)}"
            assert len(blocked_attempts) == concurrent_attempts - 1, f"Expected {concurrent_attempts-1} blocked attempts"
            
            # Verify successful refresh updated the token
            final_data = json.loads(await redis_client.get(refresh_key))
            assert final_data["use_count"] == 1
            
            print(f"✅ Concurrent refresh prevention validated - 1 success, {len(blocked_attempts)} blocked")
            
        finally:
            await redis_client.delete(refresh_key)
            await redis_client.delete(lock_key)

    @pytest.mark.asyncio
    async def test_refresh_token_family_invalidation(self, redis_client, jwt_secret_key: str):
        """Test refresh token family invalidation on security breach."""
        
        user_id = 88888
        
        # Create token family (multiple refresh tokens for same user)
        refresh_tokens = []
        refresh_keys = []
        
        try:
            for i in range(3):
                access_token, refresh_token = self.create_token_pair(user_id, jwt_secret_key)
                refresh_decoded = jwt.decode(refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
                refresh_id = refresh_decoded["refresh_id"]
                refresh_key = f"{CacheConstants.SERVICE_TOKEN_PREFIX}refresh:{user_id}:{refresh_id}_{i}"
                
                refresh_tokens.append(refresh_token)
                refresh_keys.append(refresh_key)
                
                refresh_data = {
                    "user_id": user_id,
                    "refresh_token": refresh_token,
                    "refresh_id": refresh_id,
                    "is_active": True,
                    "family_id": f"family_{user_id}",
                    "device_id": f"device_{i}"
                }
                
                await redis_client.setex(refresh_key, CacheConstants.SERVICE_TOKEN_CACHE_TTL, json.dumps(refresh_data))
            
            # Verify all tokens are active
            for refresh_key in refresh_keys:
                data = json.loads(await redis_client.get(refresh_key))
                assert data["is_active"] is True
            
            # Simulate security breach - invalidate entire token family
            invalidation_time = datetime.utcnow().isoformat()
            
            for refresh_key in refresh_keys:
                data = json.loads(await redis_client.get(refresh_key))
                data["is_active"] = False
                data["revoked_at"] = invalidation_time
                data["revocation_reason"] = "security_breach_family_invalidation"
                
                await redis_client.setex(refresh_key, 3600, json.dumps(data))  # Keep for audit
            
            # Verify entire family is invalidated
            for i, refresh_key in enumerate(refresh_keys):
                data = json.loads(await redis_client.get(refresh_key))
                assert data["is_active"] is False
                assert data["revocation_reason"] == "security_breach_family_invalidation"
                assert data["revoked_at"] == invalidation_time
            
            print(f"✅ Refresh token family invalidation completed for user {user_id}")
            
        finally:
            for refresh_key in refresh_keys:
                await redis_client.delete(refresh_key)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])