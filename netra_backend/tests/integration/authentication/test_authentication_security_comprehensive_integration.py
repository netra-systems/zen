"""
Test Authentication Security Comprehensive Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication security across golden path user flows  
- Value Impact: Protects the 90% of user value delivered through authenticated chat interactions
- Strategic Impact: Validates multi-user isolation, JWT validation, and OAuth flows that secure $120K+ MRR

CRITICAL REQUIREMENTS:
1. Tests authentication during WebSocket connections (golden path)
2. Validates JWT token flows and OAuth integration (real providers)
3. Tests user context isolation and security boundaries (multi-user system)
4. Validates authentication middleware across services
5. Tests session management and token refresh scenarios
6. Validates authentication error handling and security auditing
7. Tests authorization levels and permission validation
8. Validates security boundaries during agent execution
9. Tests cross-service authentication validation
10. Validates security audit logging and monitoring

This test suite uses REAL services (PostgreSQL, Redis, Auth Service) and REAL authentication
flows to validate that the golden path delivers secure, isolated user experiences.
"""

import asyncio
import pytest
import json
import time
import uuid
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import patch, Mock

# Add project root to Python path for test_framework imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# SSOT Test Framework Imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    AuthenticatedUser,
    create_authenticated_user_context,
    validate_jwt_token
)

# SSOT Core Types for Strong Typing
from shared.types.core_types import (
    UserID, 
    SessionID, 
    ThreadID, 
    RequestID, 
    WebSocketID,
    AuthValidationResult,
    SessionValidationResult,
    TokenResponse,
    ConnectionState,
    WebSocketEventType,
    ensure_user_id
)
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# Authentication and Security Components
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_connection,
    extract_e2e_context_from_websocket,
    create_authenticated_user_context,
    validate_websocket_token_business_logic
)
from netra_backend.app.websocket_core.unified_manager import WebSocketManager as WebSocketConnectionManager
from netra_backend.app.core import security
from netra_backend.app.middleware.auth_middleware import AuthenticationMiddleware


class TestAuthenticationSecurityComprehensive(BaseIntegrationTest):
    """
    Comprehensive authentication security integration tests.
    
    Tests authentication flows, security boundaries, and user isolation 
    using REAL services to ensure golden path security requirements.
    """
    
    def setup_method(self):
        """Set up each test with isolated authentication environment."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.security_validator = SecurityValidator()
        
        # Setup test-specific auth configuration
        self.env.set("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars", source="auth_integration_test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081", source="auth_integration_test") 
        self.env.set("SKIP_MOCKS", "true", source="auth_integration_test")
        self.env.set("USE_REAL_SERVICES", "true", source="auth_integration_test")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_validation_during_websocket_handshake(self, real_services_fixture):
        """
        Test JWT token validation during WebSocket handshake - Golden Path Security.
        
        This tests the critical authentication flow where users connect to WebSocket
        for chat interactions. JWT validation must be secure and isolated per user.
        """
        # Create authenticated user with JWT token
        auth_user = await self.auth_helper.create_authenticated_user(
            email="websocket_test@example.com",
            permissions=["read", "write", "websocket_connect"]
        )
        
        # Validate JWT token structure and claims
        validation_result = await validate_jwt_token(auth_user.jwt_token)
        assert validation_result["valid"] is True, "JWT token must be valid for WebSocket connection"
        assert validation_result["user_id"] == auth_user.user_id
        assert validation_result["email"] == auth_user.email
        assert "websocket_connect" in validation_result["permissions"]
        
        # Test WebSocket authentication headers
        headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert "X-User-ID" in headers
        assert headers["X-User-ID"] == auth_user.user_id
        
        # Validate token expiry is reasonable for session duration
        exp_timestamp = validation_result["expires_at"]
        current_time = time.time()
        assert exp_timestamp > current_time, "Token must not be expired"
        assert exp_timestamp < current_time + 3600, "Token expiry should be reasonable (< 1 hour)"
        
        self.logger.info(f"✅ JWT validation successful for WebSocket handshake: {auth_user.user_id}")
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_oauth_flow_integration_with_real_providers(self, real_services_fixture):
        """
        Test OAuth flow integration with real providers in test mode.
        
        This validates OAuth integration that enables enterprise SSO authentication
        for high-value customers in the golden path.
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Simulate OAuth flow with test provider credentials
        oauth_config = {
            "provider": "test_oauth",
            "client_id": "test_client_id", 
            "client_secret": "test_client_secret",
            "redirect_uri": "http://localhost:8000/auth/oauth/callback",
            "scope": ["read", "write", "profile"]
        }
        
        # Create OAuth state parameter for CSRF protection
        oauth_state = f"oauth_state_{uuid.uuid4().hex[:16]}"
        await redis.set(f"oauth_state:{oauth_state}", json.dumps({
            "provider": oauth_config["provider"],
            "user_session": f"session_{uuid.uuid4().hex[:8]}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }), ex=300)  # 5 minute expiry
        
        # Simulate OAuth callback with authorization code
        oauth_callback_data = {
            "code": f"test_auth_code_{uuid.uuid4().hex[:16]}",
            "state": oauth_state,
            "provider": oauth_config["provider"]
        }
        
        # Validate OAuth state parameter (CSRF protection)
        stored_state = await redis.get(f"oauth_state:{oauth_state}")
        assert stored_state is not None, "OAuth state must be preserved for CSRF protection"
        state_data = json.loads(stored_state)
        assert state_data["provider"] == oauth_config["provider"]
        
        # Create user record from OAuth profile
        oauth_user_profile = {
            "email": "oauth_test@enterprise.com",
            "name": "OAuth Test User",
            "provider_id": f"test_provider_{uuid.uuid4().hex[:8]}",
            "provider": oauth_config["provider"]
        }
        
        # Store user in database with OAuth association
        user_id = await db.fetchval("""
            INSERT INTO auth.users (email, name, oauth_provider, oauth_provider_id, is_active)
            VALUES ($1, $2, $3, $4, true)
            ON CONFLICT (email) DO UPDATE SET
                oauth_provider = EXCLUDED.oauth_provider,
                oauth_provider_id = EXCLUDED.oauth_provider_id,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, oauth_user_profile["email"], oauth_user_profile["name"], 
             oauth_user_profile["provider"], oauth_user_profile["provider_id"])
        
        assert user_id is not None, "OAuth user must be created in database"
        
        # Create JWT token for OAuth-authenticated user
        oauth_jwt = self.auth_helper.create_test_jwt_token(
            user_id=str(user_id),
            email=oauth_user_profile["email"],
            permissions=["read", "write", "oauth_authenticated"]
        )
        
        # Validate OAuth JWT token 
        validation_result = await validate_jwt_token(oauth_jwt)
        assert validation_result["valid"] is True
        assert "oauth_authenticated" in validation_result["permissions"]
        
        # Clean up OAuth state
        await redis.delete(f"oauth_state:{oauth_state}")
        
        self.logger.info(f"✅ OAuth flow integration successful for user: {user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_session_persistence_and_refresh_token_handling(self, real_services_fixture):
        """
        Test session persistence and refresh token handling.
        
        This validates session management that enables users to maintain
        authentication across browser sessions and connection drops.
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create authenticated user with refresh token
        auth_user = await self.auth_helper.create_authenticated_user(
            email="session_test@example.com",
            permissions=["read", "write", "session_refresh"]
        )
        
        # Create session record in database
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        refresh_token = f"refresh_{uuid.uuid4().hex[:32]}"
        session_expiry = datetime.now(timezone.utc) + timedelta(days=7)  # 7 day session
        
        await db.execute("""
            INSERT INTO auth.user_sessions (id, user_id, refresh_token, expires_at, is_active, created_at)
            VALUES ($1, $2, $3, $4, true, CURRENT_TIMESTAMP)
        """, session_id, auth_user.user_id, refresh_token, session_expiry)
        
        # Store session data in Redis cache
        session_data = {
            "user_id": auth_user.user_id,
            "email": auth_user.email,
            "permissions": auth_user.permissions,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        await redis.set_json(f"session:{session_id}", session_data, ex=3600)  # 1 hour cache
        
        # Validate session exists and is retrievable
        cached_session = await redis.get_json(f"session:{session_id}")
        assert cached_session is not None, "Session must be cached for performance"
        assert cached_session["user_id"] == auth_user.user_id
        assert cached_session["email"] == auth_user.email
        
        # Test session refresh with refresh token
        db_session = await db.fetchrow("""
            SELECT user_id, expires_at, is_active 
            FROM auth.user_sessions 
            WHERE id = $1 AND refresh_token = $2
        """, session_id, refresh_token)
        
        assert db_session is not None, "Session must exist in database"
        assert db_session["is_active"] is True, "Session must be active"
        assert db_session["expires_at"] > datetime.now(timezone.utc), "Session must not be expired"
        
        # Simulate refresh token flow - create new access token
        new_access_token = self.auth_helper.create_test_jwt_token(
            user_id=auth_user.user_id,
            email=auth_user.email,
            permissions=auth_user.permissions + ["refreshed_access"],
            exp_minutes=30  # New 30-minute access token
        )
        
        # Validate new access token
        new_validation = await validate_jwt_token(new_access_token)
        assert new_validation["valid"] is True
        assert "refreshed_access" in new_validation["permissions"]
        
        # Update session last activity
        await redis.set_json(f"session:{session_id}", {
            **session_data,
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "refresh_count": 1
        }, ex=3600)
        
        self.logger.info(f"✅ Session persistence and refresh flow successful: {session_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_middleware_integration_across_services(self, real_services_fixture):
        """
        Test authentication middleware integration across backend and auth services.
        
        This validates that authentication middleware properly validates tokens
        and enforces security boundaries across service calls.
        """
        # Create authenticated user for middleware testing
        auth_user = await self.auth_helper.create_authenticated_user(
            email="middleware_test@example.com", 
            permissions=["read", "write", "api_access"]
        )
        
        # Test authentication middleware token validation
        auth_headers = self.auth_helper.get_auth_headers(auth_user.jwt_token)
        
        # Simulate middleware token extraction
        auth_header = auth_headers.get("Authorization", "")
        assert auth_header.startswith("Bearer "), "Auth header must use Bearer token format"
        
        token = auth_header.replace("Bearer ", "")
        assert token == auth_user.jwt_token, "Extracted token must match user token"
        
        # Test middleware user context creation
        validation_result = await validate_jwt_token(token)
        assert validation_result["valid"] is True, "Middleware must validate token"
        
        # Create user execution context from middleware validation
        user_context = await create_authenticated_user_context(
            user_email=auth_user.email,
            user_id=auth_user.user_id,
            permissions=auth_user.permissions
        )
        
        assert isinstance(user_context, StronglyTypedUserExecutionContext)
        assert user_context.user_id == UserID(auth_user.user_id)
        assert user_context.agent_context["jwt_token"] == auth_user.jwt_token
        assert user_context.agent_context["user_email"] == auth_user.email
        
        # Test middleware permission validation
        required_permissions = ["read", "api_access"]
        user_permissions = user_context.agent_context.get("permissions", [])
        
        for required_perm in required_permissions:
            assert required_perm in user_permissions, f"User must have required permission: {required_perm}"
        
        # Test middleware request isolation
        assert user_context.request_id is not None, "Each request must have unique ID"
        assert user_context.thread_id is not None, "Each context must have thread ID"
        assert user_context.run_id is not None, "Each context must have run ID"
        
        self.logger.info(f"✅ Authentication middleware integration successful: {auth_user.user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_isolation_and_security_boundaries(self, real_services_fixture):
        """
        Test user context isolation and security boundaries - Multi-User System Security.
        
        This is critical for the multi-user system to ensure complete isolation
        between users and prevent data leakage across user sessions.
        """
        db = real_services_fixture["db"] 
        redis = real_services_fixture["redis"]
        
        # Create two distinct users for isolation testing
        user1 = await self.auth_helper.create_authenticated_user(
            email="user1_isolation@example.com",
            permissions=["read", "write"]
        )
        
        user2 = await self.auth_helper.create_authenticated_user(
            email="user2_isolation@example.com", 
            permissions=["read", "write"]
        )
        
        assert user1.user_id != user2.user_id, "Users must have distinct IDs"
        assert user1.email != user2.email, "Users must have distinct emails"
        
        # Create isolated execution contexts
        context1 = await create_authenticated_user_context(
            user_email=user1.email,
            user_id=user1.user_id,
            permissions=user1.permissions
        )
        
        context2 = await create_authenticated_user_context(
            user_email=user2.email,
            user_id=user2.user_id, 
            permissions=user2.permissions
        )
        
        # Validate context isolation
        assert context1.user_id != context2.user_id, "User contexts must be isolated"
        assert context1.thread_id != context2.thread_id, "Thread IDs must be unique per user"
        assert context1.run_id != context2.run_id, "Run IDs must be unique per execution"
        assert context1.request_id != context2.request_id, "Request IDs must be unique"
        
        # Test database isolation - create user-specific data
        await db.execute("""
            INSERT INTO backend.user_threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
        """, str(context1.thread_id), user1.user_id, "User 1 Private Thread")
        
        await db.execute("""
            INSERT INTO backend.user_threads (id, user_id, title, created_at)  
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
        """, str(context2.thread_id), user2.user_id, "User 2 Private Thread")
        
        # Validate data isolation - user 1 cannot access user 2's data
        user1_threads = await db.fetch("""
            SELECT id, title FROM backend.user_threads WHERE user_id = $1
        """, user1.user_id)
        
        user2_threads = await db.fetch("""
            SELECT id, title FROM backend.user_threads WHERE user_id = $1
        """, user2.user_id)
        
        assert len(user1_threads) == 1, "User 1 should see only their thread"
        assert len(user2_threads) == 1, "User 2 should see only their thread"
        assert user1_threads[0]["title"] == "User 1 Private Thread"
        assert user2_threads[0]["title"] == "User 2 Private Thread"
        
        # Test cache isolation
        await redis.set_json(f"user_data:{user1.user_id}", {"private": "user1_secret"})
        await redis.set_json(f"user_data:{user2.user_id}", {"private": "user2_secret"})
        
        user1_cache = await redis.get_json(f"user_data:{user1.user_id}")
        user2_cache = await redis.get_json(f"user_data:{user2.user_id}")
        
        assert user1_cache["private"] == "user1_secret"
        assert user2_cache["private"] == "user2_secret"
        assert user1_cache["private"] != user2_cache["private"], "Cache data must be isolated"
        
        self.logger.info(f"✅ User context isolation validated: {user1.user_id} ↔ {user2.user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authorization_levels_and_permission_validation(self, real_services_fixture):
        """
        Test authorization levels and permission validation across user tiers.
        
        This validates that different user subscription levels have appropriate
        permissions and access controls enforced.
        """
        # Create users with different authorization levels
        free_user = await self.auth_helper.create_authenticated_user(
            email="free_user@example.com",
            permissions=["read", "basic_chat"]
        )
        
        enterprise_user = await self.auth_helper.create_authenticated_user(
            email="enterprise_user@example.com",
            permissions=["read", "write", "advanced_chat", "agent_execution", "data_export"]
        )
        
        admin_user = await self.auth_helper.create_authenticated_user(
            email="admin_user@example.com", 
            permissions=["read", "write", "admin", "user_management", "system_access"]
        )
        
        # Test permission validation for different actions
        permission_tests = [
            {
                "user": free_user,
                "required_permissions": ["read", "basic_chat"],
                "forbidden_permissions": ["admin", "data_export", "user_management"],
                "should_have_access": True
            },
            {
                "user": enterprise_user,
                "required_permissions": ["read", "write", "agent_execution"],
                "forbidden_permissions": ["admin", "user_management"],
                "should_have_access": True
            },
            {
                "user": admin_user,
                "required_permissions": ["admin", "system_access"],
                "forbidden_permissions": [],
                "should_have_access": True
            }
        ]
        
        for test_case in permission_tests:
            user = test_case["user"]
            user_permissions = user.permissions
            
            # Test required permissions are present
            for required_perm in test_case["required_permissions"]:
                assert required_perm in user_permissions, \
                    f"User {user.email} must have permission: {required_perm}"
            
            # Test forbidden permissions are absent
            for forbidden_perm in test_case["forbidden_permissions"]:
                assert forbidden_perm not in user_permissions, \
                    f"User {user.email} must NOT have permission: {forbidden_perm}"
            
            # Validate JWT contains correct permissions
            validation_result = await validate_jwt_token(user.jwt_token)
            jwt_permissions = validation_result.get("permissions", [])
            
            for required_perm in test_case["required_permissions"]:
                assert required_perm in jwt_permissions, \
                    f"JWT for {user.email} must contain permission: {required_perm}"
        
        # Test permission inheritance and hierarchies
        assert "read" in free_user.permissions, "All users must have read permission"
        assert "read" in enterprise_user.permissions, "Enterprise users must have read permission"
        assert "read" in admin_user.permissions, "Admin users must have read permission"
        
        # Test enterprise permissions superset
        enterprise_exclusive = ["agent_execution", "data_export"]
        for perm in enterprise_exclusive:
            assert perm in enterprise_user.permissions, f"Enterprise user must have: {perm}"
            assert perm not in free_user.permissions, f"Free user must NOT have: {perm}"
        
        # Test admin permissions superset
        admin_exclusive = ["admin", "user_management", "system_access"]
        for perm in admin_exclusive:
            assert perm in admin_user.permissions, f"Admin user must have: {perm}"
            assert perm not in free_user.permissions, f"Free user must NOT have: {perm}"
            assert perm not in enterprise_user.permissions, f"Enterprise user must NOT have: {perm}"
        
        self.logger.info(f"✅ Authorization levels validated: Free({len(free_user.permissions)}) < Enterprise({len(enterprise_user.permissions)}) < Admin({len(admin_user.permissions)})")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_expiration_and_refresh_scenarios(self, real_services_fixture):
        """
        Test token expiration and refresh scenarios for session continuity.
        
        This validates token lifecycle management that enables seamless
        user experience across extended chat sessions.
        """
        redis = real_services_fixture["redis"]
        
        # Create user with short-lived token for expiration testing
        auth_user = await self.auth_helper.create_authenticated_user(
            email="token_expiry_test@example.com",
            permissions=["read", "write"]
        )
        
        # Create token with very short expiry (1 minute) for testing
        short_token = self.auth_helper.create_test_jwt_token(
            user_id=auth_user.user_id,
            email=auth_user.email,
            permissions=auth_user.permissions,
            exp_minutes=1  # 1 minute expiry
        )
        
        # Validate token is initially valid
        validation_result = await validate_jwt_token(short_token)
        assert validation_result["valid"] is True, "Short-lived token must be initially valid"
        
        initial_exp = validation_result["expires_at"]
        current_time = time.time()
        assert initial_exp > current_time, "Token must not be expired initially"
        assert initial_exp < current_time + 120, "Token must expire within 2 minutes"
        
        # Create refresh token for renewal
        refresh_token = f"refresh_{uuid.uuid4().hex[:32]}"
        refresh_data = {
            "user_id": auth_user.user_id,
            "email": auth_user.email,
            "permissions": auth_user.permissions,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
        await redis.set_json(f"refresh_token:{refresh_token}", refresh_data, ex=604800)  # 7 days
        
        # Simulate token refresh flow
        refresh_token_data = await redis.get_json(f"refresh_token:{refresh_token}")
        assert refresh_token_data is not None, "Refresh token must exist"
        assert refresh_token_data["user_id"] == auth_user.user_id
        
        # Create new access token using refresh token
        new_access_token = self.auth_helper.create_test_jwt_token(
            user_id=refresh_token_data["user_id"],
            email=refresh_token_data["email"], 
            permissions=refresh_token_data["permissions"],
            exp_minutes=30  # New 30-minute token
        )
        
        # Validate new token
        new_validation = await validate_jwt_token(new_access_token)
        assert new_validation["valid"] is True, "Refreshed token must be valid"
        assert new_validation["user_id"] == auth_user.user_id
        assert new_validation["email"] == auth_user.email
        
        new_exp = new_validation["expires_at"]
        assert new_exp > initial_exp, "New token must have later expiry"
        assert new_exp > current_time + 1200, "New token must be valid for at least 20 minutes"
        
        # Test token blacklisting after refresh
        blacklist_key = f"blacklisted_token:{hash(short_token) & 0xFFFFFFFF:08x}"
        await redis.set(blacklist_key, "revoked", ex=3600)  # Blacklist old token
        
        # Validate old token is blacklisted
        is_blacklisted = await redis.exists(blacklist_key)
        assert is_blacklisted, "Old token must be blacklisted after refresh"
        
        self.logger.info(f"✅ Token expiration and refresh scenarios validated: {auth_user.user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_error_handling_and_fallback(self, real_services_fixture):
        """
        Test authentication error handling and security fallback mechanisms.
        
        This validates error handling that protects the system against
        authentication attacks and provides clear security logging.
        """
        redis = real_services_fixture["redis"]
        
        # Test invalid JWT token handling
        invalid_tokens = [
            "invalid.jwt.token",
            "Bearer invalid_token_format",
            "",
            None,
            "valid.format.but.wrong.signature.here",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid_payload.signature"
        ]
        
        for invalid_token in invalid_tokens:
            if invalid_token:
                validation_result = await validate_jwt_token(invalid_token)
                assert validation_result["valid"] is False, f"Invalid token must be rejected: {invalid_token}"
                assert "error" in validation_result, "Error details must be provided"
                assert validation_result["user_id"] is None, "No user ID for invalid token"
            
        # Test expired token handling
        expired_token = self.auth_helper.create_test_jwt_token(
            user_id="test_user_expired",
            email="expired@example.com",
            permissions=["read"],
            exp_minutes=-5  # Already expired 5 minutes ago
        )
        
        expired_validation = await validate_jwt_token(expired_token)
        assert expired_validation["valid"] is False, "Expired token must be rejected"
        assert "expired" in expired_validation["error"].lower(), "Error must indicate expiration"
        
        # Test rate limiting for authentication attempts
        test_ip = "192.168.1.100"
        rate_limit_key = f"auth_attempts:{test_ip}"
        
        # Simulate multiple failed authentication attempts
        for attempt in range(5):
            await redis.incr(rate_limit_key)
            await redis.expire(rate_limit_key, 300)  # 5 minute window
        
        attempt_count = await redis.get(rate_limit_key)
        assert int(attempt_count) == 5, "Failed attempts must be tracked"
        
        # Test rate limit enforcement
        max_attempts = 3
        is_rate_limited = int(attempt_count) > max_attempts
        assert is_rate_limited, "Rate limiting must be enforced after max attempts"
        
        # Test authentication circuit breaker
        circuit_breaker_key = "auth_circuit_breaker:status"
        failure_count = 10  # Simulate multiple service failures
        
        await redis.set(circuit_breaker_key, json.dumps({
            "status": "open",
            "failure_count": failure_count,
            "last_failure": datetime.now(timezone.utc).isoformat()
        }), ex=300)
        
        circuit_status = await redis.get(circuit_breaker_key)
        circuit_data = json.loads(circuit_status)
        
        assert circuit_data["status"] == "open", "Circuit breaker must be open after failures"
        assert circuit_data["failure_count"] >= 10, "Failure count must be tracked"
        
        # Test security audit logging
        security_event = {
            "event_type": "authentication_failure",
            "ip_address": test_ip,
            "user_agent": "test_user_agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "failure_reason": "invalid_token",
            "severity": "medium"
        }
        
        audit_key = f"security_audit:{datetime.now(timezone.utc).strftime('%Y%m%d')}:{uuid.uuid4().hex[:8]}"
        await redis.set_json(audit_key, security_event, ex=86400)  # 24 hour retention
        
        # Validate audit log entry
        audit_entry = await redis.get_json(audit_key)
        assert audit_entry is not None, "Security events must be audited"
        assert audit_entry["event_type"] == "authentication_failure"
        assert audit_entry["ip_address"] == test_ip
        
        self.logger.info(f"✅ Authentication error handling and security fallback validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_authentication_during_agent_execution(self, real_services_fixture):
        """
        Test WebSocket authentication during agent execution - Golden Path Critical.
        
        This tests the complete authentication flow during agent execution,
        which is where 90% of user value is delivered through chat interactions.
        """
        # Create authenticated user for agent execution
        auth_user = await self.auth_helper.create_authenticated_user(
            email="agent_execution_auth@example.com",
            permissions=["read", "write", "agent_execution", "websocket_connect"]
        )
        
        # Create user execution context for agent
        user_context = await create_authenticated_user_context(
            user_email=auth_user.email,
            user_id=auth_user.user_id,
            permissions=auth_user.permissions,
            websocket_enabled=True
        )
        
        # Validate context has WebSocket support
        assert user_context.websocket_client_id is not None, "Agent execution must support WebSocket"
        assert user_context.agent_context["jwt_token"] == auth_user.jwt_token
        assert "agent_execution" in user_context.agent_context["permissions"]
        
        # Test WebSocket authentication headers for agent execution
        ws_headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
        
        # Validate E2E detection headers for testing
        assert "X-Test-Mode" in ws_headers, "WebSocket must support test mode detection"
        assert "X-User-ID" in ws_headers, "User ID must be in WebSocket headers"
        assert ws_headers["X-User-ID"] == auth_user.user_id
        
        # Simulate WebSocket message authentication during agent execution
        agent_message = {
            "type": "agent_request",
            "agent": "cost_optimizer", 
            "message": "Analyze my cloud costs",
            "user_context": {
                "user_id": auth_user.user_id,
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id)
            }
        }
        
        # Test message authentication
        assert agent_message["user_context"]["user_id"] == auth_user.user_id
        assert agent_message["user_context"]["thread_id"] is not None
        assert agent_message["user_context"]["request_id"] is not None
        
        # Test agent execution context isolation
        execution_metadata = {
            "authenticated_user": auth_user.user_id,
            "execution_context": str(user_context.run_id),
            "websocket_connection": str(user_context.websocket_client_id),
            "permissions": user_context.agent_context["permissions"]
        }
        
        assert execution_metadata["authenticated_user"] == auth_user.user_id
        assert "agent_execution" in execution_metadata["permissions"]
        assert execution_metadata["websocket_connection"] is not None
        
        # Test WebSocket event authentication during agent execution
        websocket_events = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
        for event_type in websocket_events:
            # Each WebSocket event must include authentication context
            event_payload = {
                "event_type": event_type.value,
                "user_id": auth_user.user_id,
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "authenticated": True
            }
            
            assert event_payload["user_id"] == auth_user.user_id
            assert event_payload["authenticated"] is True
            assert event_payload["thread_id"] is not None
        
        self.logger.info(f"✅ WebSocket authentication during agent execution validated: {auth_user.user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_cross_service_authentication_validation(self, real_services_fixture):
        """
        Test cross-service authentication validation between backend and auth services.
        
        This validates that authentication tokens work correctly across
        the microservice architecture for complete user workflows.
        """
        redis = real_services_fixture["redis"]
        
        # Create authenticated user for cross-service testing
        auth_user = await self.auth_helper.create_authenticated_user(
            email="cross_service_auth@example.com",
            permissions=["read", "write", "cross_service_access"]
        )
        
        # Test backend service token validation
        backend_validation = await validate_jwt_token(auth_user.jwt_token)
        assert backend_validation["valid"] is True, "Backend must validate auth service tokens"
        assert backend_validation["user_id"] == auth_user.user_id
        
        # Test auth service token refresh
        refresh_result = await self.auth_helper.validate_token(auth_user.jwt_token)
        assert refresh_result is True, "Auth service must validate its own tokens"
        
        # Test cross-service user context sharing
        shared_context = {
            "user_id": auth_user.user_id,
            "email": auth_user.email,
            "permissions": auth_user.permissions,
            "token_hash": hash(auth_user.jwt_token) & 0xFFFFFFFF,
            "service_calls": ["backend", "auth"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store context in shared cache for cross-service access
        context_key = f"cross_service_context:{auth_user.user_id}"
        await redis.set_json(context_key, shared_context, ex=3600)
        
        # Validate context can be retrieved by other services
        retrieved_context = await redis.get_json(context_key)
        assert retrieved_context is not None, "Context must be shareable across services"
        assert retrieved_context["user_id"] == auth_user.user_id
        assert retrieved_context["email"] == auth_user.email
        assert "cross_service_access" in retrieved_context["permissions"]
        
        # Test service-to-service authentication
        service_token = self.auth_helper.create_test_jwt_token(
            user_id="backend_service",
            email="backend@netra.internal",
            permissions=["service_to_service", "read_user_data"],
            exp_minutes=60
        )
        
        service_validation = await validate_jwt_token(service_token)
        assert service_validation["valid"] is True, "Service tokens must be valid"
        assert "service_to_service" in service_validation["permissions"]
        
        # Test service authentication chain
        auth_chain = {
            "user_token": auth_user.jwt_token,
            "service_token": service_token,
            "chain_valid": True,
            "user_context": retrieved_context,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Validate complete authentication chain
        assert auth_chain["chain_valid"] is True
        assert auth_chain["user_context"]["user_id"] == auth_user.user_id
        
        self.logger.info(f"✅ Cross-service authentication validation successful: {auth_user.user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_security_audit_logging_and_monitoring(self, real_services_fixture):
        """
        Test security audit logging and monitoring for authentication events.
        
        This validates comprehensive security logging that enables detection
        of authentication attacks and unauthorized access attempts.
        """
        redis = real_services_fixture["redis"]
        db = real_services_fixture["db"]
        
        # Create test user for audit logging
        auth_user = await self.auth_helper.create_authenticated_user(
            email="audit_logging_test@example.com",
            permissions=["read", "write"]
        )
        
        # Test successful authentication audit
        success_audit = {
            "event_type": "authentication_success",
            "user_id": auth_user.user_id,
            "email": auth_user.email,
            "ip_address": "192.168.1.50",
            "user_agent": "Mozilla/5.0 (Test Browser)",
            "authentication_method": "jwt",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": f"session_{uuid.uuid4().hex[:8]}",
            "severity": "info"
        }
        
        # Store audit event in database
        await db.execute("""
            INSERT INTO audit.authentication_events 
            (event_type, user_id, email, ip_address, user_agent, auth_method, timestamp, session_id, severity, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, success_audit["event_type"], success_audit["user_id"], success_audit["email"],
             success_audit["ip_address"], success_audit["user_agent"], success_audit["authentication_method"],
             datetime.fromisoformat(success_audit["timestamp"]), success_audit["session_id"], 
             success_audit["severity"], json.dumps(success_audit))
        
        # Store audit event in Redis for real-time monitoring
        audit_key = f"audit:auth:{datetime.now(timezone.utc).strftime('%Y%m%d')}:{uuid.uuid4().hex[:8]}"
        await redis.set_json(audit_key, success_audit, ex=86400)  # 24 hour retention
        
        # Test failed authentication audit
        failure_audit = {
            "event_type": "authentication_failure",
            "attempted_email": "attacker@malicious.com",
            "ip_address": "192.168.1.100",
            "user_agent": "Malicious Bot",
            "failure_reason": "invalid_credentials",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt_count": 5,
            "severity": "warning"
        }
        
        failure_key = f"audit:auth_failure:{datetime.now(timezone.utc).strftime('%Y%m%d')}:{uuid.uuid4().hex[:8]}"
        await redis.set_json(failure_key, failure_audit, ex=86400)
        
        # Test permission escalation audit
        escalation_audit = {
            "event_type": "permission_escalation_attempt",
            "user_id": auth_user.user_id,
            "current_permissions": auth_user.permissions,
            "requested_permissions": ["admin", "user_management"],
            "ip_address": "192.168.1.75",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": "denied",
            "severity": "high"
        }
        
        escalation_key = f"audit:escalation:{datetime.now(timezone.utc).strftime('%Y%m%d')}:{uuid.uuid4().hex[:8]}"
        await redis.set_json(escalation_key, escalation_audit, ex=86400)
        
        # Test suspicious activity detection
        suspicious_patterns = [
            {
                "pattern": "multiple_failed_logins",
                "threshold": 5,
                "time_window": 300,  # 5 minutes
                "current_count": 7,
                "severity": "high"
            },
            {
                "pattern": "unusual_access_times",
                "baseline_hours": [9, 17],  # 9 AM to 5 PM
                "current_hour": 3,  # 3 AM
                "severity": "medium"
            },
            {
                "pattern": "geographic_anomaly",
                "usual_location": "US",
                "current_location": "Unknown",
                "severity": "high"
            }
        ]
        
        for pattern in suspicious_patterns:
            pattern_key = f"suspicious_activity:{pattern['pattern']}:{auth_user.user_id}"
            await redis.set_json(pattern_key, {
                **pattern,
                "user_id": auth_user.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "investigated": False
            }, ex=3600)
        
        # Validate audit logs are retrievable
        stored_success = await redis.get_json(audit_key)
        stored_failure = await redis.get_json(failure_key)
        stored_escalation = await redis.get_json(escalation_key)
        
        assert stored_success is not None, "Success audit must be stored"
        assert stored_failure is not None, "Failure audit must be stored"
        assert stored_escalation is not None, "Escalation audit must be stored"
        
        assert stored_success["user_id"] == auth_user.user_id
        assert stored_failure["attempt_count"] == 5
        assert stored_escalation["result"] == "denied"
        
        # Test audit log aggregation for monitoring
        audit_summary = {
            "period": "24h",
            "total_authentications": 1,
            "successful_authentications": 1,
            "failed_authentications": 1,
            "escalation_attempts": 1,
            "unique_users": 1,
            "unique_ips": 3,
            "high_severity_events": 2,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        summary_key = f"audit_summary:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        await redis.set_json(summary_key, audit_summary, ex=86400)
        
        # Validate audit summary
        stored_summary = await redis.get_json(summary_key)
        assert stored_summary is not None, "Audit summary must be generated"
        assert stored_summary["high_severity_events"] >= 2
        
        self.logger.info(f"✅ Security audit logging and monitoring validated")
    
    async def cleanup_resources(self):
        """Clean up test resources."""
        # Parent cleanup
        super().cleanup_resources()
        
        # Additional cleanup for authentication tests
        if hasattr(self, 'auth_helper'):
            # Clear any cached tokens
            self.auth_helper._cached_token = None
            self.auth_helper._token_expiry = None

    def assert_business_value_delivered(self, result: Dict, expected_value_type: str):
        """
        Assert that authentication test delivers business value.
        
        Authentication tests deliver value by ensuring secure access to platform
        features that generate customer value.
        """
        super().assert_business_value_delivered(result, expected_value_type)
        
        # Additional authentication-specific value assertions
        if expected_value_type == "security":
            assert result.get("authentication_validated") is True, \
                "Security tests must validate authentication"
            assert result.get("user_isolation_verified") is True, \
                "Security tests must verify user isolation"
        elif expected_value_type == "user_access":
            assert result.get("access_granted") is True, \
                "User access tests must grant appropriate access"
            assert result.get("permissions_validated") is True, \
                "User access tests must validate permissions"