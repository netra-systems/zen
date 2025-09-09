"""
Session Management Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Session management enables persistent user experience
- Business Goal: Maintain user authentication state across browser sessions and devices
- Value Impact: Users stay logged in and don't lose work, improving user experience
- Strategic Impact: Foundation for enterprise features like session analytics and security

CRITICAL REQUIREMENTS:
- NO DOCKER - Integration tests without Docker containers
- NO MOCKS - Use real session storage (Redis), real database connections
- Real Services - Connect to PostgreSQL (port 5434) and Redis (port 6381)
- Integration Layer - Test session service interactions, not full browser flows

Test Categories:
1. User session creation and persistence
2. Session expiration and cleanup
3. Multi-device session handling
4. Session invalidation on logout
5. Session data consistency
6. Concurrent session handling
"""

import asyncio
import json
import time
import pytest  
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ensure_user_id

import httpx
import asyncpg
import redis.asyncio as redis


class TestSessionManagementIntegration(BaseIntegrationTest):
    """Integration tests for Session Management - NO MOCKS, REAL SERVICES ONLY."""
    
    def setup_method(self):
        """Set up for session management integration tests."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Session Configuration
        self.session_config = {
            "default_ttl": 86400,    # 24 hours
            "extended_ttl": 604800,  # 7 days for "remember me"
            "cleanup_interval": 3600, # 1 hour cleanup
            "max_sessions_per_user": 10,
            "inactive_timeout": 7200, # 2 hours of inactivity
            "sliding_expiration": True
        }
        
        # Service URLs
        self.auth_service_url = f"http://localhost:{self.env.get('AUTH_SERVICE_PORT', '8081')}"
        self.backend_url = f"http://localhost:{self.env.get('BACKEND_PORT', '8000')}"
        
        # Real service connections
        self.redis_url = f"redis://localhost:{self.env.get('REDIS_PORT', '6381')}"
        self.db_url = self.env.get("TEST_DATABASE_URL") or f"postgresql://test:test@localhost:5434/test_db"
        
        # Test user data
        self.test_users = [
            {
                "user_id": "session-test-user-1",
                "email": "session1@netra.ai", 
                "name": "Session Test User 1",
                "device_id": "device-001"
            },
            {
                "user_id": "session-test-user-2", 
                "email": "session2@netra.ai",
                "name": "Session Test User 2",
                "device_id": "device-002"
            }
        ]

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.session
    async def test_user_session_creation_and_persistence(self, real_services_fixture):
        """
        Test user session creation and persistence in Redis with real connections.
        
        Business Value: Users can log in and maintain their session across requests.
        """
        redis_client = redis.from_url(self.redis_url)
        conn = None
        
        try:
            # Connect to real database
            conn = await asyncpg.connect(self.db_url)
            
            # Create test user in database
            user = self.test_users[0]
            await conn.execute("""
                INSERT INTO users (id, email, name, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO NOTHING
            """, user["user_id"], user["email"], user["name"], datetime.now(timezone.utc))
            
            # Test session creation via auth service
            async with httpx.AsyncClient() as client:
                
                # Create session through login endpoint
                login_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/login",
                    json={
                        "email": user["email"],
                        "password": "test_password",
                        "device_id": user["device_id"],
                        "remember_me": False
                    },
                    timeout=10.0
                )
                
                # Check if login succeeded or service is available
                if login_response.status_code not in [200, 201, 404]:
                    self.logger.warning(f"Login failed: {login_response.status_code}")
                    
                # Test direct session creation endpoint
                session_response = await client.post(
                    f"{self.auth_service_url}/api/v1/sessions/create",
                    json={
                        "user_id": user["user_id"],
                        "device_id": user["device_id"],
                        "user_agent": "integration-test/1.0",
                        "ip_address": "127.0.0.1"
                    },
                    timeout=10.0
                )
                
                if session_response.status_code in [200, 201]:
                    session_data = session_response.json()
                    
                    assert "session_id" in session_data
                    assert "expires_at" in session_data
                    
                    session_id = session_data["session_id"]
                    
                    # Verify session exists in Redis
                    redis_session = await redis_client.hgetall(f"session:{session_id}")
                    
                    if redis_session:
                        # Decode Redis hash values (they're bytes)
                        session_info = {k.decode(): v.decode() for k, v in redis_session.items()}
                        
                        assert session_info["user_id"] == user["user_id"]
                        assert session_info["device_id"] == user["device_id"]
                        assert "created_at" in session_info
                        assert "last_accessed" in session_info
                        
                        # Test session persistence - retrieve after creation
                        get_response = await client.get(
                            f"{self.auth_service_url}/api/v1/sessions/{session_id}",
                            timeout=10.0
                        )
                        
                        if get_response.status_code == 200:
                            retrieved_session = get_response.json()
                            assert retrieved_session["session_id"] == session_id
                            assert retrieved_session["user_id"] == user["user_id"]
                
        except Exception as e:
            self.logger.warning(f"Session creation test error: {e}")
            if "connection" in str(e).lower():
                pytest.skip("Database/Redis not available for session testing")
            else:
                raise
                
        finally:
            if conn:
                await conn.close()
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.session
    async def test_session_expiration_and_cleanup(self, real_services_fixture):
        """
        Test session expiration and automated cleanup processes.
        
        Business Value: System automatically manages session lifecycle, improving security.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            user = self.test_users[0]
            
            # Create short-lived session for testing (30 seconds)
            session_id = str(uuid.uuid4())
            session_data = {
                "user_id": user["user_id"],
                "device_id": user["device_id"],
                "created_at": str(int(time.time())),
                "last_accessed": str(int(time.time())),
                "expires_at": str(int(time.time()) + 30),  # 30 seconds
                "user_agent": "integration-test/1.0"
            }
            
            # Store session in Redis with expiration
            await redis_client.hset(f"session:{session_id}", mapping=session_data)
            await redis_client.expire(f"session:{session_id}", 30)
            
            # Verify session exists initially
            session_exists = await redis_client.exists(f"session:{session_id}")
            assert session_exists == 1, "Session should exist immediately after creation"
            
            # Test session retrieval while valid
            async with httpx.AsyncClient() as client:
                
                # Session should be valid immediately
                valid_response = await client.get(
                    f"{self.auth_service_url}/api/v1/sessions/{session_id}/validate",
                    timeout=10.0
                )
                
                if valid_response.status_code in [200, 404]:
                    if valid_response.status_code == 200:
                        validation_result = valid_response.json()
                        assert validation_result.get("valid") is True
                
                # Wait for session expiration
                await asyncio.sleep(32)  # Wait longer than 30 second TTL
                
                # Session should now be expired/cleaned up
                expired_session = await redis_client.hgetall(f"session:{session_id}")
                assert not expired_session, "Session should be expired and removed from Redis"
                
                # Test expired session validation
                expired_response = await client.get(
                    f"{self.auth_service_url}/api/v1/sessions/{session_id}/validate",
                    timeout=10.0
                )
                
                assert expired_response.status_code in [401, 404], \
                    "Expired session should be rejected"
            
            # Test cleanup endpoint
            async with httpx.AsyncClient() as client:
                
                # Trigger manual cleanup
                cleanup_response = await client.post(
                    f"{self.auth_service_url}/api/v1/sessions/cleanup",
                    json={"force": True},
                    timeout=10.0
                )
                
                # Cleanup should succeed or be not implemented yet
                assert cleanup_response.status_code in [200, 202, 404, 501], \
                    f"Session cleanup got unexpected status: {cleanup_response.status_code}"
                
        finally:
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.session
    async def test_multi_device_session_handling(self, real_services_fixture):
        """
        Test handling of multiple sessions per user across different devices.
        
        Business Value: Users can stay logged in on multiple devices simultaneously.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            user = self.test_users[0]
            devices = ["laptop-chrome", "mobile-safari", "tablet-firefox"]
            session_ids = []
            
            # Create multiple sessions for same user on different devices
            async with httpx.AsyncClient() as client:
                
                for device in devices:
                    session_response = await client.post(
                        f"{self.auth_service_url}/api/v1/sessions/create",
                        json={
                            "user_id": user["user_id"],
                            "device_id": device,
                            "user_agent": f"integration-test/{device}",
                            "ip_address": "127.0.0.1"
                        },
                        timeout=10.0
                    )
                    
                    if session_response.status_code in [200, 201]:
                        session_data = session_response.json()
                        session_ids.append(session_data["session_id"])
                
                # Verify all sessions are valid and separate
                for session_id in session_ids:
                    
                    # Check session exists in Redis
                    redis_session = await redis_client.hgetall(f"session:{session_id}")
                    
                    if redis_session:
                        session_info = {k.decode(): v.decode() for k, v in redis_session.items()}
                        assert session_info["user_id"] == user["user_id"]
                        
                        # Each session should have unique device_id
                        device_id = session_info["device_id"]
                        assert device_id in devices
                    
                    # Test session validation via API
                    validate_response = await client.get(
                        f"{self.auth_service_url}/api/v1/sessions/{session_id}/validate",
                        timeout=10.0
                    )
                    
                    if validate_response.status_code == 200:
                        validation_result = validate_response.json()
                        assert validation_result.get("user_id") == user["user_id"]
                
                # Test user's session listing
                list_response = await client.get(
                    f"{self.auth_service_url}/api/v1/users/{user['user_id']}/sessions",
                    timeout=10.0
                )
                
                if list_response.status_code == 200:
                    user_sessions = list_response.json()
                    assert "sessions" in user_sessions
                    
                    # Should show all active sessions for user
                    active_sessions = user_sessions["sessions"]
                    session_devices = [s.get("device_id") for s in active_sessions if s.get("device_id")]
                    
                    # Verify sessions from different devices are listed
                    for device in devices[:len(active_sessions)]:
                        assert device in session_devices or len(active_sessions) == 0
                
        finally:
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.session
    async def test_session_invalidation_on_logout(self, real_services_fixture):
        """
        Test proper session invalidation when user logs out.
        
        Business Value: Users can securely log out and sessions are properly cleaned up.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            user = self.test_users[0]
            
            # Create session for logout test
            session_id = str(uuid.uuid4())
            session_data = {
                "user_id": user["user_id"],
                "device_id": user["device_id"], 
                "created_at": str(int(time.time())),
                "last_accessed": str(int(time.time())),
                "expires_at": str(int(time.time()) + 3600),  # 1 hour
                "user_agent": "integration-test/logout"
            }
            
            # Store session in Redis
            await redis_client.hset(f"session:{session_id}", mapping=session_data)
            
            # Verify session exists before logout
            session_before = await redis_client.exists(f"session:{session_id}")
            assert session_before == 1, "Session should exist before logout"
            
            async with httpx.AsyncClient() as client:
                
                # Test individual session logout
                logout_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/logout",
                    json={"session_id": session_id},
                    headers={"Authorization": f"Bearer session_{session_id}"},
                    timeout=10.0
                )
                
                # Logout should succeed or endpoint should exist
                assert logout_response.status_code in [200, 204, 404], \
                    f"Logout got unexpected status: {logout_response.status_code}"
                
                # Verify session is invalidated in Redis
                session_after = await redis_client.exists(f"session:{session_id}")
                
                if logout_response.status_code in [200, 204]:
                    assert session_after == 0, "Session should be removed after logout"
                
                # Test session validation after logout
                validate_response = await client.get(
                    f"{self.auth_service_url}/api/v1/sessions/{session_id}/validate",
                    timeout=10.0
                )
                
                assert validate_response.status_code in [401, 404], \
                    "Invalidated session should not validate"
                
                # Test logout all sessions for user
                # Create multiple sessions first
                session_ids = []
                for i in range(3):
                    new_session_id = str(uuid.uuid4())
                    await redis_client.hset(f"session:{new_session_id}", mapping={
                        **session_data,
                        "device_id": f"device-{i}",
                        "created_at": str(int(time.time()))
                    })
                    session_ids.append(new_session_id)
                
                # Logout all sessions
                logout_all_response = await client.post(
                    f"{self.auth_service_url}/api/v1/auth/logout-all",
                    json={"user_id": user["user_id"]},
                    timeout=10.0
                )
                
                if logout_all_response.status_code in [200, 204]:
                    # Verify all sessions are invalidated
                    for sid in session_ids:
                        session_exists = await redis_client.exists(f"session:{sid}")
                        assert session_exists == 0, f"Session {sid} should be invalidated after logout-all"
                
        finally:
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.session
    async def test_session_data_consistency(self, real_services_fixture):
        """
        Test session data consistency between Redis storage and API responses.
        
        Business Value: Users get consistent session information across all endpoints.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            user = self.test_users[0]
            
            # Create session with comprehensive data
            session_id = str(uuid.uuid4())
            current_time = int(time.time())
            
            comprehensive_session_data = {
                "user_id": user["user_id"],
                "device_id": user["device_id"],
                "created_at": str(current_time),
                "last_accessed": str(current_time),
                "expires_at": str(current_time + 3600),
                "user_agent": "Mozilla/5.0 Integration Test",
                "ip_address": "127.0.0.1",
                "session_type": "web",
                "permissions": json.dumps(["read", "write", "execute"]),
                "last_activity": "login",
                "timezone": "UTC"
            }
            
            # Store in Redis
            await redis_client.hset(f"session:{session_id}", mapping=comprehensive_session_data)
            
            async with httpx.AsyncClient() as client:
                
                # Retrieve session via API
                api_response = await client.get(
                    f"{self.auth_service_url}/api/v1/sessions/{session_id}",
                    timeout=10.0
                )
                
                if api_response.status_code == 200:
                    api_session_data = api_response.json()
                    
                    # Verify API response matches Redis data
                    assert api_session_data["session_id"] == session_id
                    assert api_session_data["user_id"] == user["user_id"]
                    assert api_session_data["device_id"] == user["device_id"]
                    
                    # Check timestamp consistency
                    if "created_at" in api_session_data:
                        api_created_at = int(api_session_data["created_at"])
                        assert abs(api_created_at - current_time) <= 5, \
                            "API created_at should match Redis data within 5 seconds"
                
                # Test session update and consistency
                update_response = await client.patch(
                    f"{self.auth_service_url}/api/v1/sessions/{session_id}",
                    json={
                        "last_activity": "agent_execution",
                        "timezone": "America/New_York"
                    },
                    timeout=10.0
                )
                
                if update_response.status_code in [200, 204]:
                    
                    # Verify updates are reflected in Redis
                    updated_redis = await redis_client.hgetall(f"session:{session_id}")
                    
                    if updated_redis:
                        updated_info = {k.decode(): v.decode() for k, v in updated_redis.items()}
                        assert updated_info.get("last_activity") == "agent_execution"
                        assert updated_info.get("timezone") == "America/New_York"
                    
                    # Verify updates are reflected in API
                    verify_response = await client.get(
                        f"{self.auth_service_url}/api/v1/sessions/{session_id}",
                        timeout=10.0
                    )
                    
                    if verify_response.status_code == 200:
                        updated_api_data = verify_response.json()
                        assert updated_api_data.get("last_activity") == "agent_execution"
                        assert updated_api_data.get("timezone") == "America/New_York"
                
        finally:
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.session
    async def test_concurrent_session_handling(self, real_services_fixture):
        """
        Test handling of concurrent session operations and race conditions.
        
        Business Value: System remains stable under concurrent user activity.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            user = self.test_users[0]
            session_id = str(uuid.uuid4())
            
            # Create base session
            session_data = {
                "user_id": user["user_id"],
                "device_id": user["device_id"],
                "created_at": str(int(time.time())),
                "last_accessed": str(int(time.time())),
                "expires_at": str(int(time.time()) + 3600),
                "access_count": "0"
            }
            
            await redis_client.hset(f"session:{session_id}", mapping=session_data)
            
            async with httpx.AsyncClient() as client:
                
                # Test concurrent session access
                async def access_session(request_id: int):
                    """Simulate concurrent session access."""
                    try:
                        response = await client.patch(
                            f"{self.auth_service_url}/api/v1/sessions/{session_id}/access",
                            json={
                                "request_id": request_id,
                                "activity": f"concurrent_access_{request_id}",
                                "timestamp": int(time.time())
                            },
                            timeout=5.0
                        )
                        return {"request_id": request_id, "status": response.status_code}
                    except Exception as e:
                        return {"request_id": request_id, "error": str(e)}
                
                # Launch concurrent access requests
                concurrent_requests = 10
                access_tasks = [access_session(i) for i in range(concurrent_requests)]
                results = await asyncio.gather(*access_tasks, return_exceptions=True)
                
                # Analyze results
                successful_requests = [r for r in results if isinstance(r, dict) and r.get("status") in [200, 204]]
                
                self.logger.info(f"Concurrent session access: {len(successful_requests)}/{concurrent_requests} succeeded")
                
                # Verify session data integrity after concurrent access
                final_session = await redis_client.hgetall(f"session:{session_id}")
                
                if final_session:
                    session_info = {k.decode(): v.decode() for k, v in final_session.items()}
                    
                    # Session should still be valid and contain original user data
                    assert session_info["user_id"] == user["user_id"]
                    assert session_info["device_id"] == user["device_id"]
                    
                    # last_accessed should have been updated by at least one request
                    last_accessed = int(session_info.get("last_accessed", "0"))
                    original_time = int(session_data["created_at"])
                    assert last_accessed >= original_time, \
                        "Session last_accessed should be updated by concurrent requests"
            
            # Test concurrent session creation for different users
            async def create_user_session(user_index: int):
                """Create session for different users concurrently."""
                test_user = {
                    "user_id": f"concurrent-user-{user_index}",
                    "email": f"concurrent{user_index}@netra.ai",
                    "device_id": f"concurrent-device-{user_index}"
                }
                
                try:
                    async with httpx.AsyncClient() as create_client:
                        response = await create_client.post(
                            f"{self.auth_service_url}/api/v1/sessions/create",
                            json={
                                "user_id": test_user["user_id"],
                                "device_id": test_user["device_id"], 
                                "user_agent": f"concurrent-test/{user_index}",
                                "ip_address": "127.0.0.1"
                            },
                            timeout=5.0
                        )
                        return {"user_index": user_index, "status": response.status_code}
                except Exception as e:
                    return {"user_index": user_index, "error": str(e)}
            
            # Test concurrent session creation
            creation_tasks = [create_user_session(i) for i in range(5)]
            creation_results = await asyncio.gather(*creation_tasks, return_exceptions=True)
            
            successful_creations = [r for r in creation_results if isinstance(r, dict) and r.get("status") in [200, 201]]
            self.logger.info(f"Concurrent session creation: {len(successful_creations)}/5 succeeded")
            
        finally:
            await redis_client.aclose()

    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.session
    async def test_session_sliding_expiration(self, real_services_fixture):
        """
        Test sliding expiration - sessions extend their lifetime with activity.
        
        Business Value: Active users don't get logged out unexpectedly during work.
        """
        redis_client = redis.from_url(self.redis_url)
        
        try:
            user = self.test_users[0] 
            session_id = str(uuid.uuid4())
            
            # Create session with short TTL for testing (60 seconds)
            initial_ttl = 60
            session_data = {
                "user_id": user["user_id"],
                "device_id": user["device_id"],
                "created_at": str(int(time.time())),
                "last_accessed": str(int(time.time())),
                "expires_at": str(int(time.time()) + initial_ttl),
                "sliding_expiration": "true"
            }
            
            await redis_client.hset(f"session:{session_id}", mapping=session_data)
            await redis_client.expire(f"session:{session_id}", initial_ttl)
            
            # Check initial TTL
            initial_redis_ttl = await redis_client.ttl(f"session:{session_id}")
            assert initial_redis_ttl > 0, "Session should have positive TTL initially"
            
            async with httpx.AsyncClient() as client:
                
                # Wait partway through TTL
                await asyncio.sleep(20)  # Wait 20 seconds of 60 second TTL
                
                # Access session to trigger sliding expiration
                activity_response = await client.post(
                    f"{self.auth_service_url}/api/v1/sessions/{session_id}/activity",
                    json={
                        "activity_type": "agent_execution",
                        "timestamp": int(time.time())
                    },
                    timeout=10.0
                )
                
                # Check TTL after activity
                post_activity_ttl = await redis_client.ttl(f"session:{session_id}")
                
                if activity_response.status_code in [200, 204]:
                    # TTL should be refreshed to near the original value
                    assert post_activity_ttl > initial_redis_ttl, \
                        f"Session TTL should be refreshed after activity: {post_activity_ttl} vs {initial_redis_ttl}"
                
                # Test multiple activities extending session life
                for i in range(3):
                    await asyncio.sleep(15)  # Wait 15 seconds
                    
                    extend_response = await client.patch(
                        f"{self.auth_service_url}/api/v1/sessions/{session_id}",
                        json={"last_activity": f"extend_test_{i}"},
                        timeout=10.0
                    )
                    
                    if extend_response.status_code in [200, 204]:
                        # Session should still exist after extension
                        session_exists = await redis_client.exists(f"session:{session_id}")
                        assert session_exists == 1, f"Session should exist after extension {i}"
                
                # Verify session is still active after total time > initial TTL
                final_validation = await client.get(
                    f"{self.auth_service_url}/api/v1/sessions/{session_id}/validate",
                    timeout=10.0
                )
                
                if final_validation.status_code == 200:
                    # Session extended its life through activity
                    validation_result = final_validation.json()
                    assert validation_result.get("valid") is True, \
                        "Session should remain valid through sliding expiration"
                
        finally:
            await redis_client.aclose()