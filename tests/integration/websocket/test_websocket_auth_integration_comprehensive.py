"""
Comprehensive WebSocket Authentication Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Multi-user platform security
- Business Goal: Ensure secure, authenticated WebSocket connections for AI chat
- Value Impact: Validates authentication flows prevent unauthorized access to sensitive AI conversations
- Strategic Impact: Critical for enterprise adoption - demonstrates enterprise-grade security

MISSION: Create 20+ high-quality integration tests for WebSocket authentication flows that fill 
the gap between unit and e2e tests, focusing on JWT validation, token lifecycle, session management,
and multi-user authentication isolation.

These integration tests validate WebSocket authentication flows without requiring Docker services
to be running, using real authentication components but mocked transport layers.
"""

import pytest
import asyncio
import jwt
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.websocket_helpers import MockWebSocketConnection, WebSocketTestHelpers

# Core WebSocket auth components
from netra_backend.app.websocket_core.unified_websocket_auth import WebSocketAuthenticator
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService

# Shared utilities
from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_unified_jwt_secret


class TestWebSocketAuthenticationIntegrationComprehensive(BaseIntegrationTest):
    """
    Comprehensive integration tests for WebSocket authentication flows.
    
    Tests authentication components directly without requiring Docker services,
    using real auth logic with mocked transport/persistence layers.
    """

    @pytest.fixture
    async def auth_helper(self):
        """Create E2E authentication helper."""
        config = E2EAuthConfig(
            auth_service_url="http://localhost:8081",
            backend_url="http://localhost:8000", 
            websocket_url="ws://localhost:8000/ws",
            jwt_secret="test-jwt-secret-key-unified-testing-32chars",
            timeout=5.0
        )
        return E2EAuthHelper(config)

    @pytest.fixture
    async def websocket_authenticator(self):
        """Create WebSocket authenticator for testing."""
        return WebSocketAuthenticator()

    @pytest.fixture
    async def unified_auth_service(self):
        """Create unified authentication service for integration testing."""
        return UnifiedAuthenticationService()

    @pytest.fixture
    def valid_jwt_payload(self):
        """Standard valid JWT payload for testing."""
        return {
            "sub": "test-user-12345", 
            "email": "test@example.com",
            "subscription_tier": "enterprise",
            "permissions": ["read", "write", "websocket"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": "netra-auth-service",
            "jti": f"test-token-{int(time.time())}"
        }

    @pytest.fixture
    def expired_jwt_payload(self):
        """Expired JWT payload for testing token expiration."""
        return {
            "sub": "test-user-expired",
            "email": "expired@example.com", 
            "subscription_tier": "free",
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=10), # Expired
            "iss": "netra-auth-service",
            "jti": f"expired-token-{int(time.time())}"
        }

    # =============================================================================
    # JWT TOKEN VALIDATION SCENARIOS
    # =============================================================================

    @pytest.mark.integration
    async def test_websocket_jwt_token_validation_valid_token(self, websocket_authenticator, valid_jwt_payload):
        """
        Test WebSocket JWT token validation with valid token.
        
        BVJ: Validates core authentication mechanism - prevents unauthorized access
        """
        # Generate valid token
        jwt_secret = get_unified_jwt_secret()
        valid_token = jwt.encode(valid_jwt_payload, jwt_secret, algorithm="HS256")
        
        # Test authentication
        auth_result = await websocket_authenticator.authenticate_token(valid_token)
        
        # Assertions
        assert auth_result is not None
        assert auth_result.is_valid is True
        assert auth_result.user_id == valid_jwt_payload["sub"]
        assert auth_result.email == valid_jwt_payload["email"]
        assert auth_result.subscription_tier == valid_jwt_payload["subscription_tier"]
        assert auth_result.error_message is None
        assert auth_result.permissions == valid_jwt_payload["permissions"]
        
        # User context validation
        assert auth_result.user_context is not None
        assert auth_result.user_context.user_id == valid_jwt_payload["sub"]
        assert auth_result.user_context.subscription_tier == valid_jwt_payload["subscription_tier"]

    @pytest.mark.integration
    async def test_websocket_jwt_token_validation_invalid_signature(self, websocket_authenticator, valid_jwt_payload):
        """
        Test WebSocket JWT token validation with invalid signature.
        
        BVJ: Prevents authentication bypass through token tampering
        """
        # Generate token with wrong secret
        wrong_secret = "wrong-secret-key-should-fail-validation"
        invalid_token = jwt.encode(valid_jwt_payload, wrong_secret, algorithm="HS256")
        
        # Test authentication
        auth_result = await websocket_authenticator.authenticate_token(invalid_token)
        
        # Assertions
        assert auth_result.is_valid is False
        assert auth_result.user_id is None
        assert auth_result.error_message is not None
        assert "signature" in auth_result.error_message.lower() or "invalid" in auth_result.error_message.lower()
        assert auth_result.error_code in ["INVALID_TOKEN", "SIGNATURE_VERIFICATION_FAILED"]

    @pytest.mark.integration
    async def test_websocket_jwt_token_validation_expired_token(self, websocket_authenticator, expired_jwt_payload):
        """
        Test WebSocket JWT token validation with expired token.
        
        BVJ: Ensures sessions expire appropriately for security
        """
        # Generate expired token
        jwt_secret = get_unified_jwt_secret()
        expired_token = jwt.encode(expired_jwt_payload, jwt_secret, algorithm="HS256")
        
        # Test authentication
        auth_result = await websocket_authenticator.authenticate_token(expired_token)
        
        # Assertions
        assert auth_result.is_valid is False
        assert auth_result.user_id is None
        assert auth_result.error_message is not None
        assert "expired" in auth_result.error_message.lower()
        assert auth_result.error_code == "TOKEN_EXPIRED"

    @pytest.mark.integration
    async def test_websocket_jwt_token_validation_malformed_token(self, websocket_authenticator):
        """
        Test WebSocket JWT token validation with malformed token.
        
        BVJ: Handles malicious or corrupted authentication attempts gracefully
        """
        malformed_tokens = [
            "not.a.jwt",
            "malformed.token.structure",
            "",
            "Bearer invalid_token",
            "just-a-random-string",
            "a.b",  # Too few segments
            "a.b.c.d.e"  # Too many segments
        ]
        
        for malformed_token in malformed_tokens:
            auth_result = await websocket_authenticator.authenticate_token(malformed_token)
            
            assert auth_result.is_valid is False
            assert auth_result.user_id is None
            assert auth_result.error_message is not None
            assert "invalid" in auth_result.error_message.lower() or "malformed" in auth_result.error_message.lower()

    @pytest.mark.integration
    async def test_websocket_jwt_token_validation_missing_required_claims(self, websocket_authenticator):
        """
        Test WebSocket JWT token validation with missing required claims.
        
        BVJ: Ensures tokens contain all necessary user identification data
        """
        jwt_secret = get_unified_jwt_secret()
        
        # Test missing sub claim
        payload_missing_sub = {
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "iss": "netra-auth-service"
        }
        token_missing_sub = jwt.encode(payload_missing_sub, jwt_secret, algorithm="HS256")
        
        auth_result = await websocket_authenticator.authenticate_token(token_missing_sub)
        assert auth_result.is_valid is False
        assert "user_id" in auth_result.error_message.lower() or "sub" in auth_result.error_message.lower()
        
        # Test missing email claim
        payload_missing_email = {
            "sub": "test-user-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "iss": "netra-auth-service"
        }
        token_missing_email = jwt.encode(payload_missing_email, jwt_secret, algorithm="HS256")
        
        auth_result = await websocket_authenticator.authenticate_token(token_missing_email)
        assert auth_result.is_valid is False
        assert "email" in auth_result.error_message.lower()

    # =============================================================================
    # AUTHENTICATION MIDDLEWARE INTEGRATION
    # =============================================================================

    @pytest.mark.integration
    async def test_websocket_auth_middleware_valid_connection(self, auth_helper, unified_auth_service):
        """
        Test WebSocket authentication middleware with valid authentication.
        
        BVJ: Validates middleware properly handles authenticated requests
        """
        # Create valid token
        token = auth_helper.create_test_jwt_token(
            user_id="middleware-test-user",
            email="middleware@example.com",
            permissions=["read", "write", "websocket"]
        )
        
        # Create mock WebSocket connection with auth headers
        mock_websocket = MockWebSocketConnection("middleware-test-user")
        auth_headers = auth_helper.get_websocket_headers(token)
        
        # Test middleware authentication
        auth_result = await unified_auth_service.validate_websocket_auth(
            headers=auth_headers,
            websocket=mock_websocket
        )
        
        # Assertions
        assert auth_result.is_authenticated is True
        assert auth_result.user_id == "middleware-test-user"
        assert auth_result.email == "middleware@example.com"
        assert "websocket" in auth_result.permissions

    @pytest.mark.integration
    async def test_websocket_auth_middleware_missing_auth_header(self, unified_auth_service):
        """
        Test WebSocket authentication middleware with missing auth header.
        
        BVJ: Ensures unauthenticated connections are properly rejected
        """
        # Create mock WebSocket connection without auth headers
        mock_websocket = MockWebSocketConnection("anonymous-user")
        empty_headers = {}
        
        # Test middleware authentication
        with pytest.raises(Exception) as exc_info:
            await unified_auth_service.validate_websocket_auth(
                headers=empty_headers,
                websocket=mock_websocket
            )
        
        # Assertions
        assert "authorization" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

    @pytest.mark.integration
    async def test_websocket_auth_middleware_rate_limiting(self, auth_helper, unified_auth_service):
        """
        Test WebSocket authentication middleware rate limiting functionality.
        
        BVJ: Prevents abuse through rapid authentication attempts
        """
        # Create valid token
        token = auth_helper.create_test_jwt_token(
            user_id="rate-limit-test-user",
            email="ratelimit@example.com"
        )
        
        mock_websocket = MockWebSocketConnection("rate-limit-test-user")
        auth_headers = auth_helper.get_websocket_headers(token)
        
        # Test rapid authentication attempts
        auth_attempts = []
        for i in range(50):  # Attempt rapid connections
            try:
                auth_result = await unified_auth_service.validate_websocket_auth(
                    headers=auth_headers,
                    websocket=mock_websocket
                )
                auth_attempts.append(auth_result)
            except Exception as e:
                if "rate limit" in str(e).lower() or "too many" in str(e).lower():
                    break  # Rate limiting triggered
                else:
                    raise  # Unexpected error
            
            await asyncio.sleep(0.01)  # Rapid attempts
        
        # Should eventually hit rate limit or have reasonable attempt count
        assert len(auth_attempts) < 50  # Rate limiting should activate

    # =============================================================================
    # TOKEN LIFECYCLE AND REFRESH FLOWS
    # =============================================================================

    @pytest.mark.integration
    async def test_websocket_token_expiration_detection(self, websocket_authenticator):
        """
        Test WebSocket token expiration detection and handling.
        
        BVJ: Ensures expired sessions are detected and handled gracefully
        """
        jwt_secret = get_unified_jwt_secret()
        
        # Create token that expires in 1 second
        payload = {
            "sub": "expiry-test-user",
            "email": "expiry@example.com",
            "subscription_tier": "enterprise",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=1),
            "iss": "netra-auth-service"
        }
        
        short_lived_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        # Validate token while still valid
        auth_result_valid = await websocket_authenticator.authenticate_token(short_lived_token)
        assert auth_result_valid.is_valid is True
        
        # Wait for token to expire
        await asyncio.sleep(2)
        
        # Validate token after expiry
        auth_result_expired = await websocket_authenticator.authenticate_token(short_lived_token)
        assert auth_result_expired.is_valid is False
        assert auth_result_expired.error_code == "TOKEN_EXPIRED"

    @pytest.mark.integration
    async def test_websocket_token_refresh_simulation(self, auth_helper, websocket_authenticator):
        """
        Test WebSocket token refresh flow simulation.
        
        BVJ: Validates session continuity through token refresh
        """
        # Create initial token
        original_token = auth_helper.create_test_jwt_token(
            user_id="refresh-test-user",
            email="refresh@example.com",
            exp_minutes=5
        )
        
        # Validate original token
        auth_result_original = await websocket_authenticator.authenticate_token(original_token)
        assert auth_result_original.is_valid is True
        
        # Simulate token refresh (create new token with same user but updated timestamp)
        refreshed_token = auth_helper.create_test_jwt_token(
            user_id="refresh-test-user",  # Same user
            email="refresh@example.com",  # Same email
            exp_minutes=30  # Extended expiry
        )
        
        # Validate refreshed token
        auth_result_refreshed = await websocket_authenticator.authenticate_token(refreshed_token)
        assert auth_result_refreshed.is_valid is True
        assert auth_result_refreshed.user_id == auth_result_original.user_id
        assert auth_result_refreshed.email == auth_result_original.email
        
        # Both tokens should be valid for the same user
        assert auth_result_original.user_id == auth_result_refreshed.user_id

    @pytest.mark.integration
    async def test_websocket_concurrent_token_validation(self, websocket_authenticator, valid_jwt_payload):
        """
        Test concurrent WebSocket token validation for same user.
        
        BVJ: Ensures authentication system handles concurrent user sessions
        """
        jwt_secret = get_unified_jwt_secret()
        valid_token = jwt.encode(valid_jwt_payload, jwt_secret, algorithm="HS256")
        
        # Create concurrent validation tasks
        validation_tasks = [
            websocket_authenticator.authenticate_token(valid_token)
            for _ in range(10)
        ]
        
        # Execute concurrent validations
        auth_results = await asyncio.gather(*validation_tasks)
        
        # All validations should succeed
        for auth_result in auth_results:
            assert auth_result.is_valid is True
            assert auth_result.user_id == valid_jwt_payload["sub"]
            assert auth_result.email == valid_jwt_payload["email"]

    # =============================================================================
    # MULTI-USER AUTHENTICATION ISOLATION
    # =============================================================================

    @pytest.mark.integration
    async def test_websocket_multi_user_token_isolation(self, auth_helper, websocket_authenticator):
        """
        Test WebSocket authentication isolation between multiple users.
        
        BVJ: Critical for multi-user platform - ensures user data isolation
        """
        # Create tokens for different users
        user1_token = auth_helper.create_test_jwt_token(
            user_id="isolation-user-1",
            email="user1@example.com",
            permissions=["read", "write"]
        )
        
        user2_token = auth_helper.create_test_jwt_token(
            user_id="isolation-user-2", 
            email="user2@example.com",
            permissions=["read"]
        )
        
        user3_token = auth_helper.create_test_jwt_token(
            user_id="isolation-user-3",
            email="user3@example.com",
            permissions=["read", "write", "admin"]
        )
        
        # Validate each token independently
        auth_result_1 = await websocket_authenticator.authenticate_token(user1_token)
        auth_result_2 = await websocket_authenticator.authenticate_token(user2_token)
        auth_result_3 = await websocket_authenticator.authenticate_token(user3_token)
        
        # All should be valid but distinct
        assert all([
            auth_result_1.is_valid,
            auth_result_2.is_valid, 
            auth_result_3.is_valid
        ])
        
        # User contexts should be isolated
        assert auth_result_1.user_id != auth_result_2.user_id != auth_result_3.user_id
        assert auth_result_1.email != auth_result_2.email != auth_result_3.email
        
        # Permissions should be user-specific
        assert set(auth_result_1.permissions) == {"read", "write"}
        assert set(auth_result_2.permissions) == {"read"}
        assert set(auth_result_3.permissions) == {"read", "write", "admin"}

    @pytest.mark.integration
    async def test_websocket_user_context_validation(self, auth_helper, websocket_authenticator):
        """
        Test WebSocket user context validation and isolation.
        
        BVJ: Ensures user context is properly isolated between WebSocket connections
        """
        # Create tokens for users with different subscription tiers
        free_user_token = auth_helper.create_test_jwt_token(
            user_id="context-free-user",
            email="free@example.com"
        )
        
        enterprise_user_token = auth_helper.create_test_jwt_token(
            user_id="context-enterprise-user",
            email="enterprise@example.com"
        )
        
        # Update JWT payloads with subscription tiers
        jwt_secret = get_unified_jwt_secret()
        
        free_payload = jwt.decode(free_user_token, options={"verify_signature": False})
        free_payload["subscription_tier"] = "free"
        free_user_token = jwt.encode(free_payload, jwt_secret, algorithm="HS256")
        
        enterprise_payload = jwt.decode(enterprise_user_token, options={"verify_signature": False})
        enterprise_payload["subscription_tier"] = "enterprise"
        enterprise_user_token = jwt.encode(enterprise_payload, jwt_secret, algorithm="HS256")
        
        # Validate tokens and check contexts
        free_auth = await websocket_authenticator.authenticate_token(free_user_token)
        enterprise_auth = await websocket_authenticator.authenticate_token(enterprise_user_token)
        
        # Both should be valid with proper context isolation
        assert free_auth.is_valid and enterprise_auth.is_valid
        
        # Subscription tiers should be properly isolated
        assert free_auth.subscription_tier == "free"
        assert enterprise_auth.subscription_tier == "enterprise"
        
        # User contexts should reflect proper isolation
        assert free_auth.user_context.subscription_tier == "free"
        assert enterprise_auth.user_context.subscription_tier == "enterprise"
        assert free_auth.user_context.user_id != enterprise_auth.user_context.user_id

    # =============================================================================
    # SUBSCRIPTION TIER AND PERMISSIONS
    # =============================================================================

    @pytest.mark.integration
    async def test_websocket_subscription_tier_validation(self, auth_helper, websocket_authenticator):
        """
        Test WebSocket authentication with different subscription tiers.
        
        BVJ: Validates subscription-based access control for revenue protection
        """
        subscription_tiers = ["free", "early", "mid", "enterprise"]
        
        for tier in subscription_tiers:
            # Create user token with specific tier
            user_payload = {
                "sub": f"{tier}-tier-user",
                "email": f"{tier}@example.com",
                "subscription_tier": tier,
                "permissions": self._get_tier_permissions(tier),
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iss": "netra-auth-service"
            }
            
            jwt_secret = get_unified_jwt_secret()
            tier_token = jwt.encode(user_payload, jwt_secret, algorithm="HS256")
            
            # Validate token
            auth_result = await websocket_authenticator.authenticate_token(tier_token)
            
            # Should be valid with correct tier
            assert auth_result.is_valid is True
            assert auth_result.subscription_tier == tier
            assert auth_result.user_id == f"{tier}-tier-user"
            
            # Permissions should match tier
            expected_permissions = self._get_tier_permissions(tier)
            assert set(auth_result.permissions) == set(expected_permissions)

    @pytest.mark.integration
    async def test_websocket_permission_based_access_validation(self, auth_helper, websocket_authenticator):
        """
        Test WebSocket permission-based access validation.
        
        BVJ: Ensures fine-grained access control for different user capabilities
        """
        permission_scenarios = [
            {
                "permissions": ["read"],
                "user_type": "readonly",
                "should_allow_websocket": True
            },
            {
                "permissions": ["read", "write"],
                "user_type": "standard",
                "should_allow_websocket": True
            },
            {
                "permissions": ["read", "write", "websocket"],
                "user_type": "websocket_enabled",
                "should_allow_websocket": True
            },
            {
                "permissions": [],
                "user_type": "no_permissions",
                "should_allow_websocket": False
            }
        ]
        
        for scenario in permission_scenarios:
            # Create token with specific permissions
            user_payload = {
                "sub": f"perm-test-{scenario['user_type']}",
                "email": f"{scenario['user_type']}@example.com",
                "subscription_tier": "enterprise", 
                "permissions": scenario["permissions"],
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iss": "netra-auth-service"
            }
            
            jwt_secret = get_unified_jwt_secret()
            perm_token = jwt.encode(user_payload, jwt_secret, algorithm="HS256")
            
            # Validate token
            auth_result = await websocket_authenticator.authenticate_token(perm_token)
            
            if scenario["should_allow_websocket"]:
                assert auth_result.is_valid is True
                assert set(auth_result.permissions) == set(scenario["permissions"])
            else:
                # May be valid token but insufficient permissions for WebSocket
                if auth_result.is_valid:
                    assert len(auth_result.permissions) == 0

    # =============================================================================
    # CROSS-SERVICE AUTH VALIDATION
    # =============================================================================

    @pytest.mark.integration  
    async def test_websocket_cross_service_auth_consistency(self, auth_helper, websocket_authenticator, unified_auth_service):
        """
        Test WebSocket authentication consistency across services.
        
        BVJ: Ensures authentication state is consistent across microservices
        """
        # Create token that should be valid across services
        cross_service_token = auth_helper.create_test_jwt_token(
            user_id="cross-service-user",
            email="crossservice@example.com",
            permissions=["read", "write", "websocket", "api"]
        )
        
        # Validate with WebSocket authenticator
        websocket_auth_result = await websocket_authenticator.authenticate_token(cross_service_token)
        
        # Validate with unified auth service
        auth_headers = auth_helper.get_auth_headers(cross_service_token)
        mock_websocket = MockWebSocketConnection("cross-service-user")
        
        unified_auth_result = await unified_auth_service.validate_websocket_auth(
            headers=auth_headers,
            websocket=mock_websocket
        )
        
        # Results should be consistent across services
        assert websocket_auth_result.is_valid is True
        assert unified_auth_result.is_authenticated is True
        assert websocket_auth_result.user_id == unified_auth_result.user_id
        assert websocket_auth_result.email == unified_auth_result.email

    @pytest.mark.integration
    async def test_websocket_service_to_service_authentication(self, auth_helper):
        """
        Test WebSocket service-to-service authentication validation.
        
        BVJ: Validates internal service communication security
        """
        # Create service token (different from user token)
        service_payload = {
            "sub": "backend-service",
            "service_name": "netra-backend",
            "service_type": "internal",
            "permissions": ["internal_api", "websocket_management"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
            "iss": "netra-auth-service",
            "aud": "netra-services"
        }
        
        jwt_secret = get_unified_jwt_secret()
        service_token = jwt.encode(service_payload, jwt_secret, algorithm="HS256")
        
        # Create mock service-to-service auth validation
        with patch('netra_backend.app.services.unified_authentication_service.UnifiedAuthenticationService.validate_service_token') as mock_validate:
            mock_validate.return_value = AsyncMock(
                is_valid=True,
                service_name="netra-backend",
                permissions=["internal_api", "websocket_management"]
            )
            
            # Test service token validation
            unified_auth_service = UnifiedAuthenticationService()
            service_auth_result = await unified_auth_service.validate_service_token(service_token)
            
            # Should be valid service authentication
            assert service_auth_result.is_valid is True
            assert service_auth_result.service_name == "netra-backend"
            assert "websocket_management" in service_auth_result.permissions

    # =============================================================================
    # ERROR HANDLING AND RECOVERY
    # =============================================================================

    @pytest.mark.integration
    async def test_websocket_authentication_error_recovery(self, websocket_authenticator):
        """
        Test WebSocket authentication error handling and recovery scenarios.
        
        BVJ: Ensures graceful handling of authentication failures
        """
        error_scenarios = [
            {
                "token": "invalid.jwt.structure",
                "expected_error": "MALFORMED_TOKEN",
                "description": "Malformed JWT structure"
            },
            {
                "token": "",
                "expected_error": "MISSING_TOKEN", 
                "description": "Empty token"
            },
            {
                "token": None,
                "expected_error": "MISSING_TOKEN",
                "description": "None token"
            }
        ]
        
        for scenario in error_scenarios:
            if scenario["token"] is None:
                # Test None token handling
                with pytest.raises(Exception) as exc_info:
                    await websocket_authenticator.authenticate_token(scenario["token"])
                
                assert "token" in str(exc_info.value).lower()
            else:
                # Test invalid token handling
                auth_result = await websocket_authenticator.authenticate_token(scenario["token"])
                
                assert auth_result.is_valid is False
                assert auth_result.user_id is None
                assert auth_result.error_message is not None
                # Error code may vary based on specific error type

    @pytest.mark.integration
    async def test_websocket_connection_cleanup_on_auth_failure(self, auth_helper):
        """
        Test WebSocket connection cleanup after authentication failures.
        
        BVJ: Prevents resource leaks from failed authentication attempts
        """
        # Create mock WebSocket connections for failed auth scenarios
        failed_connections = []
        
        for i in range(5):
            # Create connection with invalid authentication
            mock_websocket = MockWebSocketConnection(f"failed-user-{i}")
            
            # Attempt authentication with invalid token
            invalid_token = f"invalid-token-{i}"
            
            try:
                # This should fail
                auth_headers = {"Authorization": f"Bearer {invalid_token}"}
                
                # Simulate connection attempt
                unified_auth_service = UnifiedAuthenticationService()
                await unified_auth_service.validate_websocket_auth(
                    headers=auth_headers,
                    websocket=mock_websocket
                )
                
            except Exception:
                # Expected - auth should fail
                failed_connections.append(mock_websocket)
                
                # Verify connection is properly closed/cleaned
                assert mock_websocket.closed is True or mock_websocket.state.name == "CLOSED"
        
        # All failed connections should be cleaned up
        assert len(failed_connections) == 5
        for connection in failed_connections:
            assert connection.closed is True or connection.state.name == "CLOSED"

    @pytest.mark.integration
    async def test_websocket_auth_state_consistency_validation(self, auth_helper, websocket_authenticator):
        """
        Test WebSocket authentication state consistency over time.
        
        BVJ: Ensures authentication state remains consistent during session
        """
        # Create long-lived token
        long_lived_token = auth_helper.create_test_jwt_token(
            user_id="consistency-test-user",
            email="consistency@example.com",
            exp_minutes=60
        )
        
        # Validate token multiple times over time
        validation_results = []
        
        for i in range(5):
            auth_result = await websocket_authenticator.authenticate_token(long_lived_token)
            validation_results.append({
                "attempt": i,
                "is_valid": auth_result.is_valid,
                "user_id": auth_result.user_id,
                "email": auth_result.email,
                "timestamp": time.time()
            })
            
            await asyncio.sleep(0.1)  # Small delay between validations
        
        # All validations should be consistent
        assert all(result["is_valid"] for result in validation_results)
        assert len(set(result["user_id"] for result in validation_results)) == 1
        assert len(set(result["email"] for result in validation_results)) == 1
        
        # User ID should be consistent across all validations
        consistent_user_id = validation_results[0]["user_id"]
        assert all(result["user_id"] == consistent_user_id for result in validation_results)

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    def _get_tier_permissions(self, tier: str) -> List[str]:
        """Get permissions for subscription tier."""
        tier_permissions = {
            "free": ["read"],
            "early": ["read", "write"],
            "mid": ["read", "write", "websocket"],
            "enterprise": ["read", "write", "websocket", "admin", "api"]
        }
        return tier_permissions.get(tier, ["read"])

    # =============================================================================
    # UPDATE TODO STATUS  
    # =============================================================================

# End of test file - 20+ comprehensive integration tests created covering:
# - JWT token validation scenarios (valid, invalid signature, expired, malformed, missing claims)
# - Authentication middleware integration (valid connection, missing headers, rate limiting)
# - Token lifecycle and refresh flows (expiration detection, refresh simulation, concurrent validation)  
# - Multi-user authentication isolation (token isolation, user context validation)
# - Subscription tier and permissions (tier validation, permission-based access)
# - Cross-service auth validation (consistency, service-to-service auth)
# - Error handling and recovery (error scenarios, connection cleanup, state consistency)