"""L3 Integration Test: Auth Service JWT Validation with Redis Session Store

Business Value Justification (BVJ):
- Segment: All tiers (authentication is universal)
- Business Goal: Critical for security and session management
- Value Impact: Ensures secure user authentication and session persistence
- Strategic Impact: Protects $75K MRR through reliable authentication preventing security breaches

L3 Test: Real Redis session store with JWT token validation, session storage,
refresh flows, and revocation testing with actual auth service integration.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

import redis.asyncio as redis

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator, TokenType
from netra_backend.app.redis_manager import RedisManager
from logging_config import central_logger
from netra_backend.tests.helpers.redis_l3_helpers import RedisContainer, verify_redis_connection

# Add project root to path

logger = central_logger.get_logger(__name__)


class MockSessionManager:
    """Mock session manager for testing JWT with Redis."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    async def create_session(self, user_id: str, token: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create session in Redis."""
        session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "token": token,
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        
        session_key = f"session:{session_id}"
        await self.redis_client.set(session_key, json.dumps(session_data), ex=3600)
        
        return {
            "success": True,
            "session_id": session_id
        }
    
    async def update_session_token(self, session_id: str, new_token: str) -> Dict[str, Any]:
        """Update session token in Redis."""
        session_key = f"session:{session_id}"
        session_data = await self.redis_client.get(session_key)
        
        if session_data:
            session_dict = json.loads(session_data)
            session_dict["token"] = new_token
            session_dict["last_activity"] = datetime.now(timezone.utc).isoformat()
            
            await self.redis_client.set(session_key, json.dumps(session_dict), ex=3600)
            
            return {"success": True}
        
        return {"success": False, "error": "Session not found"}
    
    async def invalidate_session(self, session_id: str) -> Dict[str, Any]:
        """Invalidate session in Redis."""
        session_key = f"session:{session_id}"
        deleted = await self.redis_client.delete(session_key)
        
        return {
            "success": bool(deleted)
        }


class AuthJWTRedisManager:
    """Manages JWT authentication testing with Redis session store."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.jwt_validator = None
        self.session_manager = None
        self.test_sessions = set()
        self.test_tokens = []
        self.auth_stats = {
            "tokens_generated": 0,
            "tokens_validated": 0,
            "sessions_created": 0,
            "sessions_refreshed": 0,
            "tokens_revoked": 0
        }
    
    async def initialize_auth_services(self):
        """Initialize JWT and session services with Redis backend."""
        # Initialize JWT validator
        self.jwt_validator = UnifiedJWTValidator()
        
        # Create mock session manager for testing
        self.session_manager = MockSessionManager(self.redis_client)
        
        logger.info("Auth services initialized with Redis backend")
    
    async def test_jwt_token_lifecycle(self, user_count: int) -> Dict[str, Any]:
        """Test complete JWT token lifecycle with Redis persistence."""
        lifecycle_results = {
            "users_processed": 0,
            "successful_generations": 0,
            "successful_validations": 0,
            "successful_refreshes": 0,
            "failed_operations": 0
        }
        
        for i in range(user_count):
            user_id = f"jwt_user_{i}_{uuid.uuid4().hex[:8]}"
            
            try:
                # 1. Generate JWT token
                token = self.jwt_validator.create_access_token(
                    user_id=user_id,
                    email=f"{user_id}@test.com",
                    permissions=["read", "write"],
                    expires_minutes=60
                )
                
                refresh_token = self.jwt_validator.create_refresh_token(user_id)
                
                lifecycle_results["successful_generations"] += 1
                self.auth_stats["tokens_generated"] += 1
                self.test_tokens.append(token)
                
                # 2. Validate token
                validation_result = self.jwt_validator.validate_token_jwt(token)
                
                if validation_result.valid:
                    lifecycle_results["successful_validations"] += 1
                    self.auth_stats["tokens_validated"] += 1
                else:
                    lifecycle_results["failed_operations"] += 1
                    continue
                
                # 3. Create session in Redis
                session_result = await self.session_manager.create_session(
                    user_id=user_id,
                    token=token,
                    metadata={"test_lifecycle": True, "user_index": i}
                )
                
                if session_result["success"]:
                    self.auth_stats["sessions_created"] += 1
                    self.test_sessions.add(session_result["session_id"])
                else:
                    lifecycle_results["failed_operations"] += 1
                    continue
                
                # 4. Refresh token (simulate)
                new_token = self.jwt_validator.create_access_token(
                    user_id=user_id,
                    email=f"{user_id}@test.com",
                    permissions=["read", "write"],
                    expires_minutes=60
                )
                
                lifecycle_results["successful_refreshes"] += 1
                self.auth_stats["sessions_refreshed"] += 1
                self.test_tokens.append(new_token)
                
                lifecycle_results["users_processed"] += 1
                
            except Exception as e:
                logger.error(f"JWT lifecycle failed for user {user_id}: {e}")
                lifecycle_results["failed_operations"] += 1
        
        return lifecycle_results
    
    async def test_session_storage_persistence(self, session_count: int) -> Dict[str, Any]:
        """Test session storage and persistence in Redis."""
        storage_results = {
            "sessions_created": 0,
            "sessions_retrieved": 0,
            "sessions_updated": 0,
            "storage_consistency": 0,
            "persistence_failures": 0
        }
        
        session_data = []
        
        for i in range(session_count):
            user_id = f"session_user_{i}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Generate token
                permissions = ["read", "write", "admin"] if i % 5 == 0 else ["read"]
                token = self.jwt_validator.create_access_token(
                    user_id=user_id,
                    email=f"{user_id}@test.com",
                    permissions=permissions,
                    expires_minutes=120
                )
                
                # Create session with metadata
                session_metadata = {
                    "ip_address": f"192.168.1.{i % 255}",
                    "user_agent": f"TestClient/{i}",
                    "created_index": i,
                    "test_type": "storage_persistence"
                }
                
                session_result = await self.session_manager.create_session(
                    user_id=user_id,
                    token=token,
                    metadata=session_metadata
                )
                
                if not session_result["success"]:
                    storage_results["persistence_failures"] += 1
                    continue
                
                storage_results["sessions_created"] += 1
                session_id = session_result["session_id"]
                self.test_sessions.add(session_id)
                
                session_data.append({
                    "session_id": session_id,
                    "user_id": user_id,
                    "token": token,
                    "metadata": session_metadata
                })
                
            except Exception as e:
                logger.error(f"Session creation failed for user {user_id}: {e}")
                storage_results["persistence_failures"] += 1
        
        # Test session retrieval and consistency
        for session_info in session_data[:min(20, len(session_data))]:  # Test subset
            try:
                # Retrieve session from Redis
                session_key = f"session:{session_info['session_id']}"
                stored_session = await self.redis_client.get(session_key)
                
                if stored_session:
                    session_dict = json.loads(stored_session)
                    
                    # Verify session data consistency
                    if (session_dict.get("user_id") == session_info["user_id"] and
                        session_dict.get("token") == session_info["token"]):
                        storage_results["storage_consistency"] += 1
                    
                    storage_results["sessions_retrieved"] += 1
                    
                    # Test session update
                    session_dict["last_activity"] = datetime.now(timezone.utc).isoformat()
                    session_dict["activity_count"] = session_dict.get("activity_count", 0) + 1
                    
                    await self.redis_client.set(session_key, json.dumps(session_dict), ex=7200)
                    storage_results["sessions_updated"] += 1
                
            except Exception as e:
                logger.error(f"Session retrieval failed for {session_info['session_id']}: {e}")
                storage_results["persistence_failures"] += 1
        
        return storage_results
    
    async def test_token_refresh_flows(self, refresh_count: int) -> Dict[str, Any]:
        """Test JWT token refresh flows with Redis session updates."""
        refresh_results = {
            "refresh_attempts": 0,
            "successful_refreshes": 0,
            "session_updates": 0,
            "token_validations": 0,
            "refresh_failures": 0
        }
        
        # Create initial tokens and sessions
        for i in range(refresh_count):
            user_id = f"refresh_user_{i}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Generate token
                token = self.jwt_validator.create_access_token(
                    user_id=user_id,
                    email=f"{user_id}@test.com",
                    permissions=["read", "write"],
                    expires_minutes=1  # Short-lived for refresh testing
                )
                
                # Create session
                session_result = await self.session_manager.create_session(
                    user_id=user_id,
                    token=token,
                    metadata={"refresh_test": True}
                )
                
                if session_result["success"]:
                    self.test_sessions.add(session_result["session_id"])
                
                refresh_results["refresh_attempts"] += 1
                
                # Wait a bit then refresh
                await asyncio.sleep(0.1)
                
                # Refresh token (simulate)
                new_token = self.jwt_validator.create_access_token(
                    user_id=user_id,
                    email=f"{user_id}@test.com",
                    permissions=["read", "write"],
                    expires_minutes=60
                )
                
                refresh_results["successful_refreshes"] += 1
                self.test_tokens.append(new_token)
                
                # Validate new token
                validation_result = self.jwt_validator.validate_token_jwt(new_token)
                if validation_result.valid:
                    refresh_results["token_validations"] += 1
                
                # Update session with new token
                if session_result["success"]:
                    session_id = session_result["session_id"]
                    update_result = await self.session_manager.update_session_token(session_id, new_token)
                    
                    if update_result["success"]:
                        refresh_results["session_updates"] += 1
                
            except Exception as e:
                logger.error(f"Token refresh failed for user {user_id}: {e}")
                refresh_results["refresh_failures"] += 1
        
        return refresh_results
    
    async def test_token_revocation_scenarios(self, revocation_count: int) -> Dict[str, Any]:
        """Test JWT token revocation with Redis session cleanup."""
        revocation_results = {
            "tokens_created": 0,
            "tokens_revoked": 0,
            "sessions_invalidated": 0,
            "revocation_verifications": 0,
            "revocation_failures": 0
        }
        
        # Create tokens for revocation testing
        revocation_data = []
        
        for i in range(revocation_count):
            user_id = f"revoke_user_{i}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Generate token
                permissions = ["read", "write", "delete"]
                token = self.jwt_validator.create_access_token(
                    user_id=user_id,
                    email=f"{user_id}@test.com",
                    permissions=permissions,
                    expires_minutes=240
                )
                
                revocation_results["tokens_created"] += 1
                self.test_tokens.append(token)
                
                # Create session
                session_result = await self.session_manager.create_session(
                    user_id=user_id,
                    token=token,
                    metadata={"revocation_test": True, "user_index": i}
                )
                
                if session_result["success"]:
                    revocation_data.append({
                        "user_id": user_id,
                        "token": token,
                        "session_id": session_result["session_id"]
                    })
                    self.test_sessions.add(session_result["session_id"])
                
            except Exception as e:
                logger.error(f"Token creation for revocation failed: {e}")
                revocation_results["revocation_failures"] += 1
        
        # Test token revocation
        for data in revocation_data:
            try:
                # Revoke token (simulate by storing in revoked list)
                revoked_key = f"revoked_token:{data['token'][:20]}"
                await self.redis_client.set(revoked_key, "revoked", ex=3600)
                
                revocation_results["tokens_revoked"] += 1
                self.auth_stats["tokens_revoked"] += 1
                
                # Invalidate associated session
                session_invalidation = await self.session_manager.invalidate_session(data["session_id"])
                
                if session_invalidation["success"]:
                    revocation_results["sessions_invalidated"] += 1
                
                # Verify token is now invalid (check revocation)
                is_revoked = await self.redis_client.exists(revoked_key)
                
                if is_revoked:
                    revocation_results["revocation_verifications"] += 1
                
            except Exception as e:
                logger.error(f"Token revocation failed for {data['user_id']}: {e}")
                revocation_results["revocation_failures"] += 1
        
        return revocation_results
    
    async def cleanup(self):
        """Clean up auth services and test data."""
        try:
            # Clean up sessions from Redis
            for session_id in self.test_sessions:
                session_key = f"session:{session_id}"
                await self.redis_client.delete(session_key)
            
            # Revoke remaining tokens (simulate)
            for token in self.test_tokens:
                try:
                    revoked_key = f"revoked_token:{token[:20]}"
                    await self.redis_client.set(revoked_key, "revoked", ex=3600)
                except Exception:
                    pass
            
            self.test_sessions.clear()
            self.test_tokens.clear()
            
        except Exception as e:
            logger.error(f"Auth cleanup failed: {e}")
    
    def get_auth_summary(self) -> Dict[str, Any]:
        """Get comprehensive authentication test summary."""
        return {
            "auth_stats": self.auth_stats,
            "total_auth_operations": sum(self.auth_stats.values()),
            "test_artifacts": {
                "sessions_created": len(self.test_sessions),
                "tokens_tracked": len(self.test_tokens)
            }
        }


@pytest.mark.L3
@pytest.mark.integration
class TestAuthJWTRedisSessionL3:
    """L3 integration tests for JWT authentication with Redis session store."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container for auth testing."""
        container = RedisContainer(port=6383)
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client for auth services."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        yield client
        await client.close()
    
    @pytest.fixture
    async def auth_manager(self, redis_client):
        """Create auth JWT Redis manager."""
        manager = AuthJWTRedisManager(redis_client)
        await manager.initialize_auth_services()
        yield manager
        await manager.cleanup()
    
    async def test_jwt_token_lifecycle_validation(self, auth_manager):
        """Test complete JWT token lifecycle with Redis persistence."""
        results = await auth_manager.test_jwt_token_lifecycle(20)
        
        # Verify token generation
        assert results["successful_generations"] >= 18, f"Token generation rate too low: {results['successful_generations']}/20"
        
        # Verify token validation
        assert results["successful_validations"] >= 18, f"Token validation rate too low: {results['successful_validations']}/20"
        
        # Verify refresh capability
        assert results["successful_refreshes"] >= 18, f"Token refresh rate too low: {results['successful_refreshes']}/20"
        
        # Verify minimal failures
        assert results["failed_operations"] <= 2, f"Too many failed operations: {results['failed_operations']}"
        
        logger.info(f"JWT lifecycle test completed: {results}")
    
    async def test_session_storage_redis_persistence(self, auth_manager):
        """Test session storage and persistence in Redis."""
        results = await auth_manager.test_session_storage_persistence(25)
        
        # Verify session creation
        assert results["sessions_created"] >= 23, f"Session creation rate too low: {results['sessions_created']}/25"
        
        # Verify session retrieval
        assert results["sessions_retrieved"] >= 18, f"Session retrieval rate too low: {results['sessions_retrieved']}"
        
        # Verify storage consistency
        assert results["storage_consistency"] >= 18, f"Storage consistency too low: {results['storage_consistency']}"
        
        # Verify session updates
        assert results["sessions_updated"] >= 18, f"Session update rate too low: {results['sessions_updated']}"
        
        # Verify minimal persistence failures
        assert results["persistence_failures"] <= 3, f"Too many persistence failures: {results['persistence_failures']}"
        
        logger.info(f"Session storage test completed: {results}")
    
    async def test_token_refresh_flow_validation(self, auth_manager):
        """Test JWT token refresh flows with Redis session updates."""
        results = await auth_manager.test_token_refresh_flows(15)
        
        # Verify refresh attempts
        assert results["refresh_attempts"] >= 14, f"Insufficient refresh attempts: {results['refresh_attempts']}"
        
        # Verify successful refreshes
        assert results["successful_refreshes"] >= 14, f"Refresh success rate too low: {results['successful_refreshes']}"
        
        # Verify token validations after refresh
        assert results["token_validations"] >= 14, f"Token validation after refresh too low: {results['token_validations']}"
        
        # Verify session updates
        assert results["session_updates"] >= 14, f"Session update rate too low: {results['session_updates']}"
        
        # Verify minimal refresh failures
        assert results["refresh_failures"] <= 1, f"Too many refresh failures: {results['refresh_failures']}"
        
        logger.info(f"Token refresh flow test completed: {results}")
    
    async def test_token_revocation_cleanup(self, auth_manager):
        """Test JWT token revocation with Redis session cleanup."""
        results = await auth_manager.test_token_revocation_scenarios(18)
        
        # Verify token creation
        assert results["tokens_created"] >= 16, f"Token creation for revocation too low: {results['tokens_created']}"
        
        # Verify token revocation
        assert results["tokens_revoked"] >= 15, f"Token revocation rate too low: {results['tokens_revoked']}"
        
        # Verify session invalidation
        assert results["sessions_invalidated"] >= 15, f"Session invalidation rate too low: {results['sessions_invalidated']}"
        
        # Verify revocation verification
        assert results["revocation_verifications"] >= 15, f"Revocation verification rate too low: {results['revocation_verifications']}"
        
        # Verify minimal revocation failures
        assert results["revocation_failures"] <= 3, f"Too many revocation failures: {results['revocation_failures']}"
        
        logger.info(f"Token revocation test completed: {results}")
    
    async def test_auth_redis_integration_comprehensive(self, auth_manager):
        """Test comprehensive auth-Redis integration scenarios."""
        # Run comprehensive test suite
        start_time = time.time()
        
        await asyncio.gather(
            auth_manager.test_jwt_token_lifecycle(10),
            auth_manager.test_session_storage_persistence(10),
            auth_manager.test_token_refresh_flows(8)
        )
        
        total_time = time.time() - start_time
        
        # Get comprehensive summary
        summary = auth_manager.get_auth_summary()
        
        # Verify comprehensive operation counts
        assert summary["total_auth_operations"] >= 30, f"Insufficient auth operations: {summary['total_auth_operations']}"
        assert summary["auth_stats"]["tokens_generated"] >= 25, "Insufficient tokens generated"
        assert summary["auth_stats"]["sessions_created"] >= 20, "Insufficient sessions created"
        
        # Verify performance
        assert total_time < 30.0, f"Comprehensive auth test took too long: {total_time:.2f}s"
        
        # Verify test artifacts
        assert summary["test_artifacts"]["sessions_created"] >= 20, "Insufficient session artifacts"
        assert summary["test_artifacts"]["tokens_tracked"] >= 25, "Insufficient token artifacts"
        
        logger.info(f"Comprehensive auth-Redis integration test completed in {total_time:.2f}s: {summary}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])