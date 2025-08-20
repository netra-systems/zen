"""L3 Integration Test: Auth Service JWT Validation with Redis Session Store

Business Value Justification (BVJ):
- Segment: All tiers (authentication is universal)
- Business Goal: Critical for security and session management
- Value Impact: Ensures secure user authentication and session persistence
- Strategic Impact: Protects $75K MRR through reliable authentication preventing security breaches

L3 Test: Real Redis session store with JWT token validation, session storage,
refresh flows, and revocation testing with actual auth service integration.
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

import redis.asyncio as redis
import jwt as jwt_lib
from app.services.auth.jwt_service import JWTService
from app.services.auth.session_manager import SessionManager
from app.redis_manager import RedisManager
from app.logging_config import central_logger
from .helpers.redis_l3_helpers import RedisContainer, verify_redis_connection

logger = central_logger.get_logger(__name__)


class AuthJWTRedisManager:
    """Manages JWT authentication testing with Redis session store."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.jwt_service = None
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
        # Initialize JWT service
        self.jwt_service = JWTService()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
            mock_redis.return_value = self.redis_client
            await self.jwt_service.initialize()
        
        # Initialize session manager
        self.session_manager = SessionManager()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
            mock_redis.return_value = self.redis_client
            await self.session_manager.initialize()
        
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
                token_result = await self.jwt_service.generate_token(
                    user_id=user_id,
                    permissions=["read", "write"],
                    tier="free",
                    expires_delta=timedelta(hours=1)
                )
                
                if not token_result["success"]:
                    lifecycle_results["failed_operations"] += 1
                    continue
                
                lifecycle_results["successful_generations"] += 1
                self.auth_stats["tokens_generated"] += 1
                self.test_tokens.append(token_result["token"])
                
                # 2. Validate token
                validation_result = await self.jwt_service.validate_token(token_result["token"])
                
                if validation_result["valid"]:
                    lifecycle_results["successful_validations"] += 1
                    self.auth_stats["tokens_validated"] += 1
                else:
                    lifecycle_results["failed_operations"] += 1
                    continue
                
                # 3. Create session in Redis
                session_result = await self.session_manager.create_session(
                    user_id=user_id,
                    token=token_result["token"],
                    metadata={"test_lifecycle": True, "user_index": i}
                )
                
                if session_result["success"]:
                    self.auth_stats["sessions_created"] += 1
                    self.test_sessions.add(session_result["session_id"])
                else:
                    lifecycle_results["failed_operations"] += 1
                    continue
                
                # 4. Refresh token
                if token_result.get("refresh_token"):
                    refresh_result = await self.jwt_service.refresh_token(token_result["refresh_token"])
                    
                    if refresh_result["success"]:
                        lifecycle_results["successful_refreshes"] += 1
                        self.auth_stats["sessions_refreshed"] += 1
                        self.test_tokens.append(refresh_result["token"])
                    else:
                        lifecycle_results["failed_operations"] += 1
                
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
                token_result = await self.jwt_service.generate_token(
                    user_id=user_id,
                    permissions=["read", "write", "admin"] if i % 5 == 0 else ["read"],
                    tier="enterprise" if i % 10 == 0 else "free",
                    expires_delta=timedelta(hours=2)
                )
                
                if not token_result["success"]:
                    storage_results["persistence_failures"] += 1
                    continue
                
                # Create session with metadata
                session_metadata = {
                    "ip_address": f"192.168.1.{i % 255}",
                    "user_agent": f"TestClient/{i}",
                    "created_index": i,
                    "test_type": "storage_persistence"
                }
                
                session_result = await self.session_manager.create_session(
                    user_id=user_id,
                    token=token_result["token"],
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
                    "token": token_result["token"],
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
        
        # Create initial tokens for refresh testing
        refresh_tokens = []
        initial_sessions = []
        
        for i in range(refresh_count):
            user_id = f"refresh_user_{i}_{uuid.uuid4().hex[:8]}"
            
            # Generate token with short expiry for refresh testing
            token_result = await self.jwt_service.generate_token(
                user_id=user_id,
                permissions=["read", "write"],
                tier="free",
                expires_delta=timedelta(seconds=30)  # Short-lived for testing
            )
            
            if token_result["success"] and token_result.get("refresh_token"):
                refresh_tokens.append({
                    "user_id": user_id,
                    "token": token_result["token"],
                    "refresh_token": token_result["refresh_token"]
                })
                
                # Create associated session
                session_result = await self.session_manager.create_session(
                    user_id=user_id,
                    token=token_result["token"],
                    metadata={"refresh_test": True}
                )
                
                if session_result["success"]:
                    initial_sessions.append(session_result["session_id"])
                    self.test_sessions.add(session_result["session_id"])
        
        # Wait for tokens to approach expiry
        await asyncio.sleep(15)
        
        # Test refresh flows
        for i, token_info in enumerate(refresh_tokens):
            try:
                refresh_results["refresh_attempts"] += 1
                
                # Refresh token
                refresh_result = await self.jwt_service.refresh_token(token_info["refresh_token"])
                
                if not refresh_result["success"]:
                    refresh_results["refresh_failures"] += 1
                    continue
                
                refresh_results["successful_refreshes"] += 1
                new_token = refresh_result["token"]
                self.test_tokens.append(new_token)
                
                # Validate new token
                validation_result = await self.jwt_service.validate_token(new_token)
                if validation_result["valid"]:
                    refresh_results["token_validations"] += 1
                
                # Update session with new token
                if i < len(initial_sessions):
                    session_id = initial_sessions[i]
                    update_result = await self.session_manager.update_session_token(session_id, new_token)
                    
                    if update_result["success"]:
                        refresh_results["session_updates"] += 1
                
            except Exception as e:
                logger.error(f"Token refresh failed for user {token_info['user_id']}: {e}")
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
                token_result = await self.jwt_service.generate_token(
                    user_id=user_id,
                    permissions=["read", "write", "delete"],
                    tier="enterprise" if i % 3 == 0 else "free",
                    expires_delta=timedelta(hours=4)
                )
                
                if not token_result["success"]:
                    revocation_results["revocation_failures"] += 1
                    continue
                
                revocation_results["tokens_created"] += 1
                token = token_result["token"]
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
                # Revoke token
                revocation_result = await self.jwt_service.revoke_token(data["token"])
                
                if revocation_result["success"]:
                    revocation_results["tokens_revoked"] += 1
                    self.auth_stats["tokens_revoked"] += 1
                    
                    # Invalidate associated session
                    session_invalidation = await self.session_manager.invalidate_session(data["session_id"])
                    
                    if session_invalidation["success"]:
                        revocation_results["sessions_invalidated"] += 1
                    
                    # Verify token is now invalid
                    validation_result = await self.jwt_service.validate_token(data["token"])
                    
                    if not validation_result["valid"]:
                        revocation_results["revocation_verifications"] += 1
                    
                else:
                    revocation_results["revocation_failures"] += 1
                
            except Exception as e:
                logger.error(f"Token revocation failed for {data['user_id']}: {e}")
                revocation_results["revocation_failures"] += 1
        
        return revocation_results
    
    async def test_concurrent_auth_operations(self, concurrent_count: int) -> Dict[str, Any]:
        """Test concurrent authentication operations with Redis."""
        # Create concurrent auth tasks
        tasks = []
        
        for i in range(concurrent_count):
            if i % 4 == 0:
                task = self._concurrent_token_generation(i)
            elif i % 4 == 1:
                task = self._concurrent_session_creation(i)
            elif i % 4 == 2:
                task = self._concurrent_token_validation(i)
            else:
                task = self._concurrent_token_refresh(i)
            
            tasks.append(task)
        
        # Execute concurrent operations
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_ops = len([r for r in results if not isinstance(r, Exception) and r.get("success", False)])
        failed_ops = len([r for r in results if isinstance(r, Exception) or not r.get("success", False)])
        
        return {
            "total_operations": concurrent_count,
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "total_time": total_time,
            "operations_per_second": concurrent_count / total_time if total_time > 0 else 0,
            "success_rate": (successful_ops / concurrent_count * 100) if concurrent_count > 0 else 0
        }
    
    async def _concurrent_token_generation(self, index: int) -> Dict[str, Any]:
        """Generate token concurrently."""
        user_id = f"concurrent_gen_{index}_{uuid.uuid4().hex[:8]}"
        
        try:
            result = await self.jwt_service.generate_token(
                user_id=user_id,
                permissions=["read"],
                tier="free",
                expires_delta=timedelta(hours=1)
            )
            
            if result["success"]:
                self.test_tokens.append(result["token"])
            
            return {"operation": "generation", "success": result["success"]}
            
        except Exception as e:
            logger.error(f"Concurrent token generation failed: {e}")
            return {"operation": "generation", "success": False}
    
    async def _concurrent_session_creation(self, index: int) -> Dict[str, Any]:
        """Create session concurrently."""
        user_id = f"concurrent_session_{index}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Generate token first
            token_result = await self.jwt_service.generate_token(
                user_id=user_id,
                permissions=["read"],
                tier="free",
                expires_delta=timedelta(hours=1)
            )
            
            if not token_result["success"]:
                return {"operation": "session_creation", "success": False}
            
            # Create session
            session_result = await self.session_manager.create_session(
                user_id=user_id,
                token=token_result["token"],
                metadata={"concurrent_test": True}
            )
            
            if session_result["success"]:
                self.test_sessions.add(session_result["session_id"])
                self.test_tokens.append(token_result["token"])
            
            return {"operation": "session_creation", "success": session_result["success"]}
            
        except Exception as e:
            logger.error(f"Concurrent session creation failed: {e}")
            return {"operation": "session_creation", "success": False}
    
    async def _concurrent_token_validation(self, index: int) -> Dict[str, Any]:
        """Validate token concurrently."""
        if not self.test_tokens:
            return {"operation": "validation", "success": False}
        
        try:
            # Use existing token for validation
            token = self.test_tokens[index % len(self.test_tokens)]
            result = await self.jwt_service.validate_token(token)
            
            return {"operation": "validation", "success": result["valid"]}
            
        except Exception as e:
            logger.error(f"Concurrent token validation failed: {e}")
            return {"operation": "validation", "success": False}
    
    async def _concurrent_token_refresh(self, index: int) -> Dict[str, Any]:
        """Refresh token concurrently."""
        user_id = f"concurrent_refresh_{index}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Generate token with refresh capability
            token_result = await self.jwt_service.generate_token(
                user_id=user_id,
                permissions=["read"],
                tier="free",
                expires_delta=timedelta(seconds=5)
            )
            
            if not token_result["success"] or not token_result.get("refresh_token"):
                return {"operation": "refresh", "success": False}
            
            # Wait a bit then refresh
            await asyncio.sleep(1)
            
            refresh_result = await self.jwt_service.refresh_token(token_result["refresh_token"])
            
            if refresh_result["success"]:
                self.test_tokens.append(refresh_result["token"])
            
            return {"operation": "refresh", "success": refresh_result["success"]}
            
        except Exception as e:
            logger.error(f"Concurrent token refresh failed: {e}")
            return {"operation": "refresh", "success": False}
    
    async def cleanup(self):
        """Clean up auth services and test data."""
        try:
            # Clean up sessions from Redis
            for session_id in self.test_sessions:
                session_key = f"session:{session_id}"
                await self.redis_client.delete(session_key)
            
            # Revoke remaining tokens
            for token in self.test_tokens:
                try:
                    await self.jwt_service.revoke_token(token)
                except Exception:
                    pass
            
            # Shutdown services
            if self.jwt_service:
                await self.jwt_service.shutdown()
            
            if self.session_manager:
                await self.session_manager.shutdown()
            
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
        assert results["successful_refreshes"] >= 15, f"Token refresh rate too low: {results['successful_refreshes']}/20"
        
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
        assert results["successful_refreshes"] >= 12, f"Refresh success rate too low: {results['successful_refreshes']}"
        
        # Verify token validations after refresh
        assert results["token_validations"] >= 12, f"Token validation after refresh too low: {results['token_validations']}"
        
        # Verify session updates
        assert results["session_updates"] >= 10, f"Session update rate too low: {results['session_updates']}"
        
        # Verify minimal refresh failures
        assert results["refresh_failures"] <= 3, f"Too many refresh failures: {results['refresh_failures']}"
        
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
    
    async def test_concurrent_auth_performance(self, auth_manager):
        """Test concurrent authentication operations performance."""
        results = await auth_manager.test_concurrent_auth_operations(80)
        
        # Verify performance
        assert results["success_rate"] >= 90.0, f"Concurrent auth success rate too low: {results['success_rate']:.1f}%"
        assert results["operations_per_second"] >= 20, f"Auth throughput too low: {results['operations_per_second']:.1f} ops/s"
        assert results["total_time"] < 15.0, f"Concurrent auth operations took too long: {results['total_time']:.2f}s"
        
        # Verify minimal failures
        assert results["failed_operations"] <= 8, f"Too many failed concurrent operations: {results['failed_operations']}"
        
        logger.info(f"Concurrent auth performance test completed: {results}")
    
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
        assert summary["total_auth_operations"] >= 40, f"Insufficient auth operations: {summary['total_auth_operations']}"
        assert summary["auth_stats"]["tokens_generated"] >= 25, "Insufficient tokens generated"
        assert summary["auth_stats"]["sessions_created"] >= 20, "Insufficient sessions created"
        
        # Verify performance
        assert total_time < 45.0, f"Comprehensive auth test took too long: {total_time:.2f}s"
        
        # Verify test artifacts
        assert summary["test_artifacts"]["sessions_created"] >= 20, "Insufficient session artifacts"
        assert summary["test_artifacts"]["tokens_tracked"] >= 25, "Insufficient token artifacts"
        
        logger.info(f"Comprehensive auth-Redis integration test completed in {total_time:.2f}s: {summary}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])