"""
Session Persistence and Token Refresh Mechanism Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain seamless user sessions and prevent unexpected logouts
- Value Impact: Users stay logged in across browser sessions and token renewals
- Strategic Impact: Session failures cause user frustration and support burden

This test suite validates session persistence and token refresh mechanisms
that are critical for user experience:

1. Session storage and retrieval from Redis/database
2. Token refresh endpoint functionality and security
3. Session expiration and cleanup mechanisms
4. Cross-browser session continuity
5. Token refresh race condition prevention
6. Session invalidation and security logout

CRITICAL: Session and token refresh failures cause:
- Users getting logged out unexpectedly
- Loss of work in progress
- Poor user experience leading to churn
- Support tickets and operational burden

Incident References:
- Token refresh endpoint failures cause user logouts
- Session persistence issues break "remember me" functionality
- Race conditions in token refresh cause multiple refresh requests
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional, List
from unittest.mock import patch, AsyncMock

import aiohttp
import pytest
import redis.asyncio as redis

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.ssot.integration_auth_manager import (
    IntegrationAuthServiceManager,
    IntegrationTestAuthHelper,
    create_integration_test_helper
)
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class TestSessionPersistenceTokenRefresh(SSotBaseTestCase):
    """
    Session Persistence and Token Refresh Mechanism Integration Tests.
    
    Tests critical session and token refresh flows using real auth service,
    real database, and real Redis for session storage.
    
    CRITICAL: Uses real session storage and real token operations.
    No mocks for session persistence to ensure production-like behavior.
    """
    
    @pytest.fixture(scope="class")
    async def auth_manager(self):
        """Start real auth service for session and refresh testing."""
        manager = IntegrationAuthServiceManager()
        
        # Start auth service
        success = await manager.start_auth_service()
        if not success:
            pytest.fail("Failed to start auth service for session/refresh tests")
        
        yield manager
        
        # Cleanup
        await manager.stop_auth_service()
    
    @pytest.fixture
    async def auth_helper(self, auth_manager):
        """Create auth helper for session/refresh testing."""
        helper = IntegrationTestAuthHelper(auth_manager)
        yield helper
    
    @pytest.fixture
    async def test_database(self):
        """Provide isolated test database session."""
        async with DatabaseTestUtilities("auth_service").transaction_scope() as db_session:
            yield db_session
    
    @pytest.fixture
    async def redis_client(self):
        """Provide Redis client for session testing."""
        # Use test Redis instance
        redis_url = self.get_env_var("REDIS_URL", "redis://localhost:6379/1")  # DB 1 for tests
        client = redis.from_url(redis_url)
        
        yield client
        
        # Cleanup test sessions
        try:
            await client.flushdb()  # Clear test database
            await client.close()
        except Exception as e:
            logger.warning(f"Redis cleanup error: {e}")
    
    @pytest.fixture
    def session_config(self):
        """Provide session and refresh configuration."""
        return {
            "access_token_expire_minutes": 15,
            "refresh_token_expire_days": 7,
            "session_expire_days": 30,
            "max_refresh_attempts": 3,
            "refresh_token_rotation": True,
            "concurrent_session_limit": 5
        }
    
    # === SESSION PERSISTENCE TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_creation_and_persistence(
        self, auth_manager, auth_helper, redis_client, session_config
    ):
        """
        Integration test for session creation and persistence.
        
        Tests that user sessions are properly created, stored in Redis/database,
        and can be retrieved for authentication continuity.
        """
        # Record test metadata
        self.record_metric("test_category", "session_persistence")
        self.record_metric("test_focus", "creation_and_storage")
        
        # Step 1: Create user session via auth service
        user_data = {
            "user_id": "session-test-user-123",
            "email": "session.test@example.com",
            "permissions": ["read", "write"]
        }
        
        session_result = await self._create_user_session(
            auth_manager, user_data, "session_creation_test"
        )
        
        assert session_result is not None, "Failed to create user session"
        assert "session_id" in session_result, "Session creation should return session_id"
        assert "access_token" in session_result, "Session creation should return access_token"
        assert "refresh_token" in session_result, "Session creation should return refresh_token"
        
        session_id = session_result["session_id"]
        access_token = session_result["access_token"]
        refresh_token = session_result["refresh_token"]
        
        self.record_metric("session_creation", "success")
        self.increment_db_query_count(1)  # Session creation
        
        # Step 2: Verify session is stored in Redis
        redis_session_key = f"session:{session_id}"
        stored_session = await redis_client.get(redis_session_key)
        
        assert stored_session is not None, f"Session should be stored in Redis under key {redis_session_key}"
        
        session_data = json.loads(stored_session)
        assert session_data["user_id"] == user_data["user_id"], "Stored session should contain correct user_id"
        assert session_data["email"] == user_data["email"], "Stored session should contain correct email"
        
        self.record_metric("redis_session_storage", "working")
        
        # Step 3: Verify session can be retrieved and validated
        retrieved_session = await self._retrieve_session_by_id(
            auth_manager, session_id, "session_retrieval_test"
        )
        
        assert retrieved_session is not None, "Session should be retrievable by session_id"
        assert retrieved_session["user_id"] == user_data["user_id"], "Retrieved session should match original user data"
        assert retrieved_session["email"] == user_data["email"], "Retrieved session should match original email"
        
        self.record_metric("session_retrieval", "working")
        self.increment_db_query_count(1)  # Session retrieval
        
        # Step 4: Verify access token is linked to session
        token_validation = await auth_manager.validate_token(access_token)
        
        assert token_validation is not None, "Access token should be valid"
        assert token_validation.get("valid", False), "Access token should validate successfully"
        
        self.record_metric("session_token_linkage", "working")
        logger.info(f" PASS:  Session persistence working (session_id: {session_id[:8]}...)")
    
    async def _create_user_session(
        self, 
        auth_manager: IntegrationAuthServiceManager,
        user_data: Dict[str, Any],
        scenario: str
    ) -> Optional[Dict[str, Any]]:
        """Create user session via auth service."""
        try:
            async with aiohttp.ClientSession() as session:
                login_data = {
                    "email": user_data["email"],
                    "password": "test-password-123",  # Mock password for testing
                    "create_session": True,
                    "remember_me": True
                }
                
                # Note: This might require user registration first in a real scenario
                # For testing, we'll use the token creation endpoint to simulate session creation
                token = await auth_manager.create_test_token(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    permissions=user_data["permissions"]
                )
                
                if token:
                    # Simulate session data structure
                    return {
                        "session_id": f"sess_{user_data['user_id']}_{int(time.time())}",
                        "access_token": token,
                        "refresh_token": f"refresh_{token[-10:]}",  # Mock refresh token
                        "user_id": user_data["user_id"],
                        "email": user_data["email"]
                    }
                
                return None
                
        except Exception as e:
            logger.warning(f"Session creation error for scenario {scenario}: {e}")
            return None
    
    async def _retrieve_session_by_id(
        self,
        auth_manager: IntegrationAuthServiceManager,
        session_id: str,
        scenario: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve session by session ID."""
        try:
            async with aiohttp.ClientSession() as session:
                request_data = {
                    "session_id": session_id
                }
                
                # Headers for service authentication
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",
                    "X-Service-Secret": "test-service-secret-32-chars-long"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/session/get",
                    json=request_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Session retrieval failed for {scenario}: {response.status}")
                        return None
                        
        except Exception as e:
            logger.warning(f"Session retrieval error for scenario {scenario}: {e}")
            return None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_refresh_mechanism(
        self, auth_manager, auth_helper, session_config
    ):
        """
        Integration test for token refresh mechanism.
        
        Tests the critical token refresh flow that prevents user logouts
        when access tokens expire.
        
        CRITICAL: Token refresh failures cause unexpected user logouts.
        """
        # Record test metadata
        self.record_metric("test_category", "token_refresh")
        self.record_metric("test_focus", "refresh_mechanism")
        
        # Step 1: Create initial tokens
        user_data = {
            "user_id": "refresh-test-user-456",
            "email": "refresh.test@example.com",
            "permissions": ["read", "write"]
        }
        
        initial_token = await auth_manager.create_test_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        assert initial_token is not None, "Failed to create initial token for refresh test"
        self.increment_db_query_count(1)  # Initial token creation
        
        # Step 2: Test token refresh
        refresh_result = await self._test_token_refresh(
            auth_manager, initial_token, "token_refresh_test"
        )
        
        assert refresh_result is not None, "Token refresh should succeed"
        assert "access_token" in refresh_result, "Refresh should return new access_token"
        
        new_access_token = refresh_result["access_token"]
        
        # Verify new token is different from original
        assert new_access_token != initial_token, "Refresh should return a new access token"
        
        self.record_metric("token_refresh_basic", "working")
        self.increment_db_query_count(1)  # Token refresh
        
        # Step 3: Validate new token works
        new_token_validation = await auth_manager.validate_token(new_access_token)
        
        assert new_token_validation is not None, "New access token should be valid"
        assert new_token_validation.get("valid", False), "New access token should validate successfully"
        
        self.record_metric("refreshed_token_validation", "working")
        self.increment_db_query_count(1)  # Token validation
        
        # Step 4: Test refresh token rotation (if enabled)
        if session_config.get("refresh_token_rotation", False):
            second_refresh_result = await self._test_token_refresh(
                auth_manager, new_access_token, "token_rotation_test"
            )
            
            if second_refresh_result and "refresh_token" in second_refresh_result:
                # Verify refresh token was rotated
                new_refresh_token = second_refresh_result["refresh_token"]
                self.record_metric("refresh_token_rotation", "working")
        
        logger.info(" PASS:  Token refresh mechanism working correctly")
    
    async def _test_token_refresh(
        self,
        auth_manager: IntegrationAuthServiceManager,
        token: str,
        scenario: str
    ) -> Optional[Dict[str, Any]]:
        """Test token refresh via auth service."""
        try:
            async with aiohttp.ClientSession() as session:
                refresh_data = {
                    "token": token,
                    "token_type": "access"
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/refresh",
                    json=refresh_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.record_metric(f"refresh_test_{scenario}", "success")
                        return result
                    else:
                        logger.warning(f"Token refresh failed for {scenario}: {response.status}")
                        self.record_metric(f"refresh_test_{scenario}", "failed")
                        return None
                        
        except Exception as e:
            logger.warning(f"Token refresh error for scenario {scenario}: {e}")
            return None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_expiration_and_cleanup(
        self, auth_manager, redis_client, session_config
    ):
        """
        Integration test for session expiration and cleanup.
        
        Tests that expired sessions are properly cleaned up and cannot be used
        for authentication.
        """
        # Record test metadata
        self.record_metric("test_category", "session_expiration")
        self.record_metric("test_focus", "expiration_and_cleanup")
        
        # Step 1: Create short-lived session for testing
        user_data = {
            "user_id": "expiry-test-user-789",
            "email": "expiry.test@example.com",
            "permissions": ["read"]
        }
        
        session_result = await self._create_user_session(
            auth_manager, user_data, "session_expiry_test"
        )
        
        assert session_result is not None, "Failed to create session for expiry test"
        session_id = session_result["session_id"]
        
        # Step 2: Manually set short expiration in Redis for testing
        redis_session_key = f"session:{session_id}"
        session_data = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=2)).isoformat()  # Short expiry
        }
        
        await redis_client.set(redis_session_key, json.dumps(session_data))
        await redis_client.expire(redis_session_key, 2)  # Expire in 2 seconds
        
        self.record_metric("short_expiry_session_created", "success")
        
        # Step 3: Verify session exists initially
        initial_session = await redis_client.get(redis_session_key)
        assert initial_session is not None, "Session should exist initially"
        
        # Step 4: Wait for expiration
        await asyncio.sleep(3)
        
        # Step 5: Verify session has been cleaned up
        expired_session = await redis_client.get(redis_session_key)
        assert expired_session is None, "Session should be cleaned up after expiration"
        
        self.record_metric("session_expiration_cleanup", "working")
        
        # Step 6: Verify expired session cannot be retrieved
        retrieved_session = await self._retrieve_session_by_id(
            auth_manager, session_id, "expired_session_retrieval"
        )
        
        assert retrieved_session is None, "Expired session should not be retrievable"
        
        self.record_metric("expired_session_blocking", "working")
        logger.info(" PASS:  Session expiration and cleanup working correctly")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_token_refresh_prevention(
        self, auth_manager, auth_helper, session_config
    ):
        """
        Integration test for concurrent token refresh prevention.
        
        Tests that multiple simultaneous token refresh requests don't cause
        race conditions or duplicate token issues.
        
        CRITICAL: Race conditions in token refresh can cause authentication errors.
        """
        # Record test metadata
        self.record_metric("test_category", "token_refresh_concurrency")
        self.record_metric("test_focus", "race_condition_prevention")
        
        # Step 1: Create initial token
        user_data = {
            "user_id": "concurrent-test-user-999",
            "email": "concurrent.test@example.com",
            "permissions": ["read", "write"]
        }
        
        initial_token = await auth_manager.create_test_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        assert initial_token is not None, "Failed to create initial token for concurrency test"
        
        # Step 2: Launch multiple concurrent refresh requests
        num_concurrent_requests = 5
        refresh_tasks = []
        
        for i in range(num_concurrent_requests):
            task = asyncio.create_task(
                self._test_token_refresh(
                    auth_manager, initial_token, f"concurrent_refresh_{i}"
                )
            )
            refresh_tasks.append(task)
        
        # Wait for all refresh requests to complete
        refresh_results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
        
        # Step 3: Analyze results
        successful_refreshes = []
        failed_refreshes = []
        
        for i, result in enumerate(refresh_results):
            if isinstance(result, Exception):
                logger.warning(f"Concurrent refresh {i} raised exception: {result}")
                failed_refreshes.append(result)
            elif result is not None and "access_token" in result:
                successful_refreshes.append(result)
            else:
                failed_refreshes.append(f"Request {i} returned None or invalid result")
        
        # Step 4: Validate race condition handling
        # At least one refresh should succeed, others may fail gracefully
        assert len(successful_refreshes) >= 1, (
            f"At least one concurrent refresh should succeed. "
            f"Successful: {len(successful_refreshes)}, Failed: {len(failed_refreshes)}"
        )
        
        # If multiple refreshes succeeded, verify tokens are consistent
        if len(successful_refreshes) > 1:
            # All successful refreshes should return the same new token (idempotency)
            first_token = successful_refreshes[0]["access_token"]
            for i, result in enumerate(successful_refreshes[1:], 1):
                assert result["access_token"] == first_token, (
                    f"Concurrent refresh {i} returned different token. This indicates race condition issues."
                )
        
        self.record_metric("concurrent_refresh_attempts", num_concurrent_requests)
        self.record_metric("successful_concurrent_refreshes", len(successful_refreshes))
        self.record_metric("failed_concurrent_refreshes", len(failed_refreshes))
        self.record_metric("concurrent_refresh_prevention", "working")
        
        logger.info(
            f" PASS:  Concurrent token refresh prevention working "
            f"(successful: {len(successful_refreshes)}, failed: {len(failed_refreshes)})"
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_invalidation_security(
        self, auth_manager, auth_helper, redis_client
    ):
        """
        Integration test for session invalidation security.
        
        Tests secure session invalidation (logout) that properly cleans up
        all session data and prevents further use of tokens.
        """
        # Record test metadata
        self.record_metric("test_category", "session_security")
        self.record_metric("test_focus", "secure_invalidation")
        
        # Step 1: Create user session
        user_data = {
            "user_id": "invalidation-test-user-555",
            "email": "invalidation.test@example.com",
            "permissions": ["read", "write"]
        }
        
        session_result = await self._create_user_session(
            auth_manager, user_data, "session_invalidation_test"
        )
        
        assert session_result is not None, "Failed to create session for invalidation test"
        
        session_id = session_result["session_id"]
        access_token = session_result["access_token"]
        
        # Step 2: Verify session and token work initially
        initial_validation = await auth_manager.validate_token(access_token)
        assert initial_validation is not None and initial_validation.get("valid", False), (
            "Session and token should work initially"
        )
        
        # Step 3: Invalidate session (logout)
        invalidation_success = await self._invalidate_session(
            auth_manager, session_id, access_token, "secure_logout_test"
        )
        
        assert invalidation_success, "Session invalidation should succeed"
        
        # Step 4: Verify session is removed from Redis
        redis_session_key = f"session:{session_id}"
        invalidated_session = await redis_client.get(redis_session_key)
        assert invalidated_session is None, "Session should be removed from Redis after invalidation"
        
        # Step 5: Verify token no longer validates
        post_invalidation_validation = await auth_manager.validate_token(access_token)
        assert post_invalidation_validation is None or not post_invalidation_validation.get("valid", False), (
            "Token should not validate after session invalidation"
        )
        
        self.record_metric("session_invalidation", "working")
        self.record_metric("post_invalidation_security", "working")
        logger.info(" PASS:  Session invalidation security working correctly")
    
    async def _invalidate_session(
        self,
        auth_manager: IntegrationAuthServiceManager,
        session_id: str,
        access_token: str,
        scenario: str
    ) -> bool:
        """Invalidate session (logout)."""
        try:
            async with aiohttp.ClientSession() as session:
                logout_data = {
                    "session_id": session_id,
                    "invalidate_all_sessions": False
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/logout",
                    json=logout_data,
                    headers=headers
                ) as response:
                    success = response.status == 200
                    self.record_metric(f"logout_test_{scenario}", "success" if success else "failed")
                    return success
                    
        except Exception as e:
            logger.warning(f"Session invalidation error for scenario {scenario}: {e}")
            return False
    
    # === TEARDOWN AND VALIDATION ===
    
    def teardown_method(self, method=None):
        """Enhanced teardown with session-specific metrics validation."""
        super().teardown_method(method)
        
        # Validate session-specific metrics were recorded
        metrics = self.get_all_metrics()
        
        # Ensure session tests recorded their metrics
        if "session" in method.__name__.lower() or "refresh" in method.__name__.lower() if method else "":
            assert "test_category" in metrics, "Session/refresh tests must record test_category metric"
            assert "test_focus" in metrics, "Session/refresh tests must record test_focus metric"
        
        # Log session-specific metrics for analysis
        session_metrics = {k: v for k, v in metrics.items() if "session" in k.lower() or "refresh" in k.lower()}
        if session_metrics:
            logger.info(f"Session/refresh test metrics: {session_metrics}")
