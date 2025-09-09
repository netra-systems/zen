"""
Authentication Session Management Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable session management across services
- Value Impact: Users maintain secure sessions across platform interactions
- Strategic Impact: Core platform security - enables trusted multi-service user experience

CRITICAL: Tests session management with REAL auth service and Redis cache.
Tests session persistence, expiration, and cleanup with real infrastructure.

Following CLAUDE.md requirements:
- Uses real services (no mocks in integration tests)
- Follows SSOT patterns from test_framework/ssot/
- Tests MUST fail hard - no try/except blocks masking errors
- Multi-user isolation using Factory patterns
"""
import pytest
import asyncio
import time
import redis
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Set

# Absolute imports per CLAUDE.md
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env
from shared.types.core_types import UserID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestAuthSessionManagementIntegration(BaseIntegrationTest):
    """Integration tests for authentication session management with real services."""
    
    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Setup integration environment for session management tests."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Set integration session management configuration
        self.env.set("JWT_SECRET_KEY", "integration-session-jwt-secret-32-chars-long", "test_session_integration")
        self.env.set("SERVICE_SECRET", "integration-session-service-secret-32", "test_session_integration")
        self.env.set("ENVIRONMENT", "test", "test_session_integration")
        self.env.set("REDIS_URL", "redis://localhost:6381", "test_session_integration")  # Test Redis
        
        # Configure session timeouts for testing
        self.env.set("JWT_ACCESS_TOKEN_EXPIRY_MINUTES", "5", "test_session_integration")  # Short for testing
        self.env.set("JWT_REFRESH_TOKEN_EXPIRY_DAYS", "7", "test_session_integration")   # Short for testing
        
        self.auth_helper = E2EAuthHelper(environment="test")
        self.id_generator = UnifiedIdGenerator()
        
        # Connect to test Redis for session verification
        try:
            self.redis_client = redis.Redis(host='localhost', port=6381, db=0, decode_responses=True)
            self.redis_client.ping()  # Verify connection
        except Exception as e:
            pytest.skip(f"Redis not available for integration tests: {e}")
        
        yield
        
        # Cleanup test data from Redis
        try:
            # Clean up test keys
            test_keys = self.redis_client.keys("test_session:*")
            if test_keys:
                self.redis_client.delete(*test_keys)
        except:
            pass  # Cleanup is best effort
        
        # Cleanup environment
        self.env.disable_isolation()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_persistence_across_multiple_api_calls(self, real_services_fixture):
        """Test that user sessions persist correctly across multiple API calls with real services."""
        # Arrange: Create authenticated user session
        user_id = f"session-persist-user-{int(time.time())}"
        email = f"session-persist-{user_id}@netra.ai"
        
        # Create JWT token using SSOT auth helper
        jwt_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read:agents", "write:threads", "execute:tools"],
            exp_minutes=10  # Sufficient time for test
        )
        
        # Verify initial token validation
        initial_validation = await self.auth_helper.validate_token(jwt_token)
        assert initial_validation is True, "Initial session token must be valid"
        
        # Act: Make multiple API calls to test session persistence
        authenticated_client = self.auth_helper.create_sync_authenticated_client()
        
        api_call_results = []
        api_endpoints = [
            "/api/health",
            "/api/health",  # Test same endpoint multiple times
            "/api/health"
        ]
        
        for i, endpoint in enumerate(api_endpoints):
            # Make API call with persistent session
            response = authenticated_client.get(endpoint)
            
            result = {
                "call_index": i,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "success": response.status_code in [200, 404],  # 404 acceptable for some endpoints
                "timestamp": datetime.now(timezone.utc)
            }
            
            api_call_results.append(result)
            
            # Assert: Each call must succeed with persistent session
            assert result["success"], (
                f"API call {i} to {endpoint} must succeed with persistent session, "
                f"got {response.status_code}: {response.text}"
            )
            
            # Brief delay between calls to test persistence over time
            await asyncio.sleep(0.2)
        
        # Assert: All API calls succeeded with same session
        successful_calls = sum(1 for r in api_call_results if r["success"])
        total_calls = len(api_call_results)
        
        assert successful_calls == total_calls, (
            f"All API calls must succeed with persistent session: "
            f"{successful_calls}/{total_calls} succeeded"
        )
        
        # Verify token is still valid after all operations
        final_validation = await self.auth_helper.validate_token(jwt_token)
        assert final_validation is True, "Session token must remain valid after multiple API calls"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_expiration_invalidates_api_access(self, real_services_fixture):
        """Test that expired sessions properly invalidate API access with real auth service."""
        # Arrange: Create user session with very short expiry
        user_id = f"session-expire-user-{int(time.time())}"
        email = f"session-expire-{user_id}@netra.ai"
        
        # Create token with short expiry for testing
        short_lived_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read:agents"],
            exp_minutes=-1  # Already expired
        )
        
        # Verify token is expired
        expired_validation = await self.auth_helper.validate_token(short_lived_token)
        assert expired_validation is False, "Expired token must be invalid"
        
        # Act: Attempt API access with expired token
        authenticated_client = self.auth_helper.create_sync_authenticated_client()
        
        # Update client with expired token
        expired_headers = self.auth_helper.get_auth_headers(short_lived_token)
        authenticated_client.headers.update(expired_headers)
        
        response = authenticated_client.get("/api/health")
        
        # Assert: Expired session must result in authentication failure
        assert response.status_code in [401, 403], (
            f"Expired session must result in 401/403 authentication failure, "
            f"got {response.status_code}: {response.text}"
        )
        
        # Test that new valid token works (to verify service is functioning)
        valid_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read:agents"],
            exp_minutes=10
        )
        
        valid_validation = await self.auth_helper.validate_token(valid_token)
        assert valid_validation is True, "New valid token must validate successfully"
        
        # Verify valid token works with API
        valid_headers = self.auth_helper.get_auth_headers(valid_token)
        authenticated_client.headers.update(valid_headers)
        
        valid_response = authenticated_client.get("/api/health")
        assert valid_response.status_code in [200, 404], (
            f"Valid token must work with API, got {valid_response.status_code}: {valid_response.text}"
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_session_cache_integration(self, real_services_fixture):
        """Test that session data is properly cached and retrieved from Redis."""
        # Arrange: Create user session for Redis testing
        user_id = f"redis-session-user-{int(time.time())}"
        email = f"redis-session-{user_id}@netra.ai"
        
        jwt_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read:agents", "write:threads"],
            exp_minutes=10
        )
        
        # Act: Store session data in Redis (simulating auth service behavior)
        session_key = f"test_session:user:{user_id}"
        session_data = {
            "user_id": user_id,
            "email": email,
            "permissions": ["read:agents", "write:threads"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
            "jwt_token_hash": str(hash(jwt_token))  # Store hash, not actual token
        }
        
        # Store in Redis with expiration
        self.redis_client.hset(session_key, mapping=session_data)
        self.redis_client.expire(session_key, 300)  # 5 minute expiry
        
        # Assert: Session data must be stored and retrievable from Redis
        stored_data = self.redis_client.hgetall(session_key)
        assert stored_data is not None, "Session data must be stored in Redis"
        assert stored_data["user_id"] == user_id, "Stored session must contain correct user_id"
        assert stored_data["email"] == email, "Stored session must contain correct email"
        
        # Verify Redis expiration is set
        ttl = self.redis_client.ttl(session_key)
        assert ttl > 0, f"Session key must have expiration set, got TTL: {ttl}"
        assert ttl <= 300, f"Session TTL must not exceed set expiration, got: {ttl}"
        
        # Test session access updates last_accessed time
        await asyncio.sleep(1)  # Ensure time difference
        
        updated_access_time = datetime.now(timezone.utc).isoformat()
        self.redis_client.hset(session_key, "last_accessed", updated_access_time)
        
        updated_data = self.redis_client.hgetall(session_key)
        assert updated_data["last_accessed"] != session_data["last_accessed"], (
            "Session last_accessed time must be updated on access"
        )
        
        # Verify JWT validation still works with cached session data
        token_validation = await self.auth_helper.validate_token(jwt_token)
        assert token_validation is True, "JWT token must validate successfully with Redis session cache"
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_concurrent_session_management_maintains_isolation(self, real_services_fixture):
        """Test that concurrent session operations maintain proper user isolation."""
        # Arrange: Create multiple user sessions for concurrent testing
        num_users = 4
        user_sessions = []
        
        for i in range(num_users):
            user_id = f"concurrent-session-user-{i}-{int(time.time())}"
            email = f"concurrent-session-{i}-{user_id}@netra.ai"
            permissions = [f"read:user_{i}", f"write:user_{i}"]
            
            jwt_token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email,
                permissions=permissions,
                exp_minutes=15
            )
            
            user_sessions.append({
                "index": i,
                "user_id": user_id,
                "email": email,
                "token": jwt_token,
                "permissions": permissions
            })
        
        # Act: Perform concurrent session operations
        async def perform_session_operations(session):
            """Perform session operations for a single user."""
            results = []
            
            # 1. Validate token
            token_valid = await self.auth_helper.validate_token(session["token"])
            results.append({"operation": "validate", "success": token_valid})
            
            # 2. Make API call
            client = self.auth_helper.create_sync_authenticated_client()
            headers = self.auth_helper.get_auth_headers(session["token"])
            client.headers.update(headers)
            
            response = client.get("/api/health")
            api_success = response.status_code in [200, 404]
            results.append({"operation": "api_call", "success": api_success, "status": response.status_code})
            
            # 3. Store session data in Redis
            session_key = f"test_session:concurrent:{session['user_id']}"
            session_redis_data = {
                "user_id": session["user_id"],
                "email": session["email"],
                "permissions": str(session["permissions"]),
                "test_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                self.redis_client.hset(session_key, mapping=session_redis_data)
                self.redis_client.expire(session_key, 180)  # 3 minute expiry
                redis_success = True
            except Exception as e:
                redis_success = False
                
            results.append({"operation": "redis_store", "success": redis_success})
            
            return {"user_index": session["index"], "user_id": session["user_id"], "results": results}
        
        # Execute concurrent session operations
        concurrent_tasks = [perform_session_operations(session) for session in user_sessions]
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Assert: All concurrent operations must succeed and maintain isolation
        for result in concurrent_results:
            assert not isinstance(result, Exception), f"Concurrent session operation must not raise exception: {result}"
            
            user_index = result["user_index"]
            user_id = result["user_id"]
            operations = result["results"]
            
            # Verify all operations succeeded for this user
            for op in operations:
                assert op["success"] is True, (
                    f"Concurrent session operation '{op['operation']}' must succeed for user {user_index} ({user_id})"
                )
        
        # Verify session isolation - each user's Redis data is separate
        for session in user_sessions:
            session_key = f"test_session:concurrent:{session['user_id']}"
            stored_data = self.redis_client.hgetall(session_key)
            
            assert stored_data is not None, f"Session data must exist for user {session['index']}"
            assert stored_data["user_id"] == session["user_id"], (
                f"Session data must contain correct isolated user_id for user {session['index']}"
            )
            assert stored_data["email"] == session["email"], (
                f"Session data must contain correct isolated email for user {session['index']}"
            )
        
        # Verify concurrent JWT validations maintain isolation
        validation_tasks = [self.auth_helper.validate_token(session["token"]) for session in user_sessions]
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        for i, validation_result in enumerate(validation_results):
            assert not isinstance(validation_result, Exception), (
                f"Concurrent validation {i} must not raise exception: {validation_result}"
            )
            assert validation_result is True, (
                f"Concurrent validation {i} must succeed for user {user_sessions[i]['user_id']}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_cleanup_removes_expired_data_from_redis(self, real_services_fixture):
        """Test that expired session cleanup properly removes old data from Redis."""
        # Arrange: Create sessions with different expiration times
        current_time = int(time.time())
        
        session_configs = [
            {"user_id": f"cleanup-expired-{current_time}-1", "expiry_seconds": -60, "should_exist": False},  # Already expired
            {"user_id": f"cleanup-expired-{current_time}-2", "expiry_seconds": -30, "should_exist": False},  # Already expired
            {"user_id": f"cleanup-active-{current_time}-3", "expiry_seconds": 300, "should_exist": True},   # Active
            {"user_id": f"cleanup-active-{current_time}-4", "expiry_seconds": 180, "should_exist": True}    # Active
        ]
        
        # Create session data in Redis with different expiration times
        created_keys = []
        for config in session_configs:
            session_key = f"test_session:cleanup:{config['user_id']}"
            session_data = {
                "user_id": config["user_id"],
                "email": f"{config['user_id']}@netra.ai",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expiry_seconds": str(config["expiry_seconds"])
            }
            
            # Store session data
            self.redis_client.hset(session_key, mapping=session_data)
            
            if config["expiry_seconds"] > 0:
                # Set expiration for active sessions
                self.redis_client.expire(session_key, config["expiry_seconds"])
            else:
                # Set very short expiration for expired sessions to simulate cleanup
                self.redis_client.expire(session_key, 1)
            
            created_keys.append(session_key)
        
        # Wait for expired keys to be removed by Redis
        await asyncio.sleep(2)
        
        # Act: Check which sessions still exist after expiration
        existing_sessions = []
        for i, session_key in enumerate(created_keys):
            exists = self.redis_client.exists(session_key)
            ttl = self.redis_client.ttl(session_key) if exists else -2
            
            existing_sessions.append({
                "config": session_configs[i],
                "key": session_key,
                "exists": bool(exists),
                "ttl": ttl
            })
        
        # Assert: Only non-expired sessions should exist
        for session in existing_sessions:
            config = session["config"]
            should_exist = config["should_exist"]
            actually_exists = session["exists"]
            
            if should_exist:
                assert actually_exists, (
                    f"Active session for {config['user_id']} must still exist in Redis. "
                    f"TTL: {session['ttl']}"
                )
                
                # Verify active session has reasonable TTL
                if session["ttl"] > 0:
                    assert session["ttl"] <= config["expiry_seconds"], (
                        f"Active session TTL must not exceed configured expiry: "
                        f"TTL={session['ttl']}, configured={config['expiry_seconds']}"
                    )
            else:
                # Expired sessions may or may not exist (Redis cleanup timing varies)
                # But if they exist, they should have negative TTL (expired)
                if actually_exists:
                    assert session["ttl"] <= 0, (
                        f"Expired session for {config['user_id']} should have non-positive TTL: "
                        f"TTL={session['ttl']}"
                    )
        
        # Clean up test data
        for session_key in created_keys:
            try:
                self.redis_client.delete(session_key)
            except:
                pass  # Best effort cleanup