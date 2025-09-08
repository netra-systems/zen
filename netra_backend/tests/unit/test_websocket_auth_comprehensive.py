"""
Comprehensive Unit Tests for WebSocket Authentication Module

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Stability and Security - Enable secure multi-user WebSocket connections
- Value Impact: Protects $100K+ ARR by ensuring authenticated users can access real-time chat without security breaches
- Strategic Impact: MISSION CRITICAL - WebSocket auth failures = immediate revenue loss as users cannot access core AI chat value

CRITICAL: WebSocket authentication is the gateway to our core business value delivery.
Without secure, reliable WebSocket connections, users cannot:
1. Receive real-time agent responses (lost engagement)
2. Access multi-user isolated sessions (data leaks)
3. Trust the platform security (churn risk)

These tests validate that our authentication system delivers business value by:
- Preventing unauthorized access to premium AI features
- Ensuring multi-user isolation works correctly
- Validating that paying customers can always access their AI agents
- Protecting against security breaches that would damage our reputation

Test Coverage Target: 100% of critical authentication flows in unified_websocket_auth.py

SOOT COMPLIANCE UPDATE:
This test file has been updated to test the new UnifiedWebSocketAuthenticator instead of
the eliminated WebSocketAuthenticator. Many tests have been skipped because:

1. ConnectionSecurityManager - eliminated in SSOT consolidation
2. RateLimiter - moved to dedicated module  
3. Token extraction methods - moved to UnifiedAuthenticationService
4. authenticate_websocket() method - replaced with authenticate_websocket_connection()
5. secure_websocket_context() - eliminated, replaced with direct authentication

The remaining active tests focus on the core WebSocket authentication functionality
that is now provided by UnifiedWebSocketAuthenticator in SSOT-compliant manner.
"""

import asyncio
import base64
import json
import time
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional

import pytest
from fastapi import WebSocket, HTTPException

# SSOT test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.jwt_test_utils import JWTTestHelper, generate_test_jwt_token, generate_expired_token
from shared.isolated_environment import get_env

# Import the SSOT unified authentication module under test
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    get_websocket_authenticator
)

# Import supporting types and services
from netra_backend.app.websocket_core.types import AuthInfo
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.unified_authentication_service import AuthResult


class TestWebSocketAuthComprehensive(BaseIntegrationTest):
    """Comprehensive test suite for WebSocket authentication module."""
    
    def setup_method(self):
        """Setup test fixtures and clear global state."""
        super().setup_method()
        self.jwt_helper = JWTTestHelper()
        
        # Clear global instances for clean test state (SSOT unified auth)
        import netra_backend.app.websocket_core.unified_websocket_auth as unified_auth_module
        unified_auth_module._websocket_authenticator = None
        
        # Setup test tokens
        self.valid_token = self.jwt_helper.create_user_token(
            user_id="test-user-123",
            email="test@example.com",
            permissions=["read", "write"]
        )
        self.expired_token = self.jwt_helper.create_expired_token("test-user-123")
        self.invalid_token = "invalid.jwt.token"


@pytest.mark.unit
class TestAuthInfo:
    """Test AuthInfo dataclass."""
    
    def test_auth_info_creation(self):
        """Test AuthInfo dataclass creation and attributes."""
        auth_info = AuthInfo(
            user_id="user123",
            email="test@example.com",
            permissions=["read", "write"],
            authenticated=True
        )
        
        assert auth_info.user_id == "user123"
        assert auth_info.email == "test@example.com"
        assert auth_info.permissions == ["read", "write"]
        assert auth_info.authenticated is True
    
    def test_auth_info_default_authenticated(self):
        """Test AuthInfo default authenticated value."""
        auth_info = AuthInfo(
            user_id="user123",
            email="test@example.com",
            permissions=[]
        )
        
        # Should default to True
        assert auth_info.authenticated is True


@pytest.mark.unit
class TestUnifiedWebSocketAuthenticator(TestWebSocketAuthComprehensive):
    """Test UnifiedWebSocketAuthenticator class comprehensively (SSOT compliant)."""
    
    def test_authenticator_initialization(self):
        """Test UnifiedWebSocketAuthenticator initialization (SSOT compliant)."""
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_get_auth:
            # Create mock auth service
            mock_auth_service = Mock()
            mock_get_auth.return_value = mock_auth_service
            
            authenticator = UnifiedWebSocketAuthenticator()
            
            # Should get unified auth service instance
            mock_get_auth.assert_called_once()
            assert authenticator._websocket_auth_attempts == 0
            assert authenticator._websocket_auth_successes == 0
            assert authenticator._websocket_auth_failures == 0
            assert authenticator._auth_service == mock_auth_service
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self):
        """Test successful WebSocket authentication with SSOT unified auth service."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock WebSocket object
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        mock_websocket.client_state = "connected"
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8080
        
        # Mock unified auth service to return successful validation
        mock_auth_result = AuthResult(
            success=True,
            user_id="test-user-123",
            email="test@example.com",
            permissions=["read", "write"],
            validated_at=datetime.now(timezone.utc)
        )
        mock_user_context = UserExecutionContext(
            user_id="test-user-123",
            thread_id="thread-456",
            run_id="run-789",
            websocket_client_id="ws-client-123"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, mock_user_context)
        )
        
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Verify the auth result structure (SSOT WebSocketAuthResult)
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is True
        assert result.user_context is not None
        assert result.user_context.user_id == "test-user-123"
        assert result.auth_result is not None
        assert result.auth_result.email == "test@example.com"
        assert result.error_message is None
        
        # Stats should be updated
        assert authenticator._websocket_auth_attempts == 1
        assert authenticator._websocket_auth_successes == 1
        assert authenticator._websocket_auth_failures == 0
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self):
        """Test WebSocket authentication with no token (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock WebSocket object with no authorization header
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {}
        mock_websocket.client_state = "connected"
        # Create a proper mock client that won't break JSON serialization
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        mock_client.port = 8080
        mock_websocket.client = mock_client
        
        # Mock unified auth service to return failed validation (no token)
        mock_auth_result = AuthResult(
            success=False,
            error="No authentication token provided",
            error_code="NO_TOKEN"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, None)
        )
        
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Should return failure result
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is False
        assert result.error_code == "NO_TOKEN"
        assert result.user_context is None
        
        # Stats should reflect failures
        assert authenticator._websocket_auth_failures == 1
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_invalid_token(self):
        """Test WebSocket authentication with invalid token (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock WebSocket object with invalid token
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.invalid_token}"}
        mock_websocket.client_state = "connected"
        # Create a proper mock client that won't break JSON serialization
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        mock_client.port = 8080
        mock_websocket.client = mock_client
        
        # Mock unified auth service to return failed validation (invalid token)
        mock_auth_result = AuthResult(
            success=False,
            error="Invalid or expired authentication token",
            error_code="VALIDATION_FAILED"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, None)
        )
        
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Should return failure result
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert result.user_context is None
        
        # Stats should be updated
        assert authenticator._websocket_auth_attempts == 1
        assert authenticator._websocket_auth_failures == 1
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_auth_service_error(self):
        """Test WebSocket authentication when auth service has error (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock WebSocket object
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        mock_websocket.client_state = "connected"
        # Create a proper mock client that won't break JSON serialization
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        mock_client.port = 8080
        mock_websocket.client = mock_client
        
        # Mock unified auth service to return service error
        mock_auth_result = AuthResult(
            success=False,
            error="Authentication service temporarily unavailable",
            error_code="AUTH_SERVICE_ERROR"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, None)
        )
        
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Should return failure result
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is False
        assert result.error_code == "AUTH_SERVICE_ERROR"
        assert authenticator._websocket_auth_failures == 1
    
    @pytest.mark.skip(reason="Bearer token handling moved to UnifiedAuthenticationService - SSOT compliance")
    @pytest.mark.asyncio
    async def test_authenticate_bearer_token_cleaning(self):
        """Test Bearer token prefix cleaning - SKIPPED (SSOT compliance).
        
        Bearer token handling is now done internally by UnifiedAuthenticationService.
        """
        pass
    
    @pytest.mark.skip(reason="authenticate method eliminated - replaced with authenticate_websocket_connection")
    @pytest.mark.asyncio
    async def test_authenticate_exception_handling(self):
        """Test authentication exception handling - SKIPPED (SSOT compliance).
        
        Direct authenticate() method eliminated. Exception handling tested in authenticate_websocket_connection().
        """
        pass
    
    @pytest.mark.skip(reason="Token extraction moved to UnifiedAuthenticationService - SSOT compliance")
    def test_extract_token_from_websocket_authorization_header(self):
        """Test token extraction - SKIPPED (SSOT compliance).
        
        Token extraction is now handled internally by UnifiedAuthenticationService.
        """
        pass
    
    @pytest.mark.skip(reason="Token extraction moved to UnifiedAuthenticationService - SSOT compliance")
    def test_extract_token_from_websocket_subprotocol(self):
        """Test token extraction from subprotocol - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.skip(reason="Token extraction moved to UnifiedAuthenticationService - SSOT compliance")
    def test_extract_token_from_websocket_query_params(self):
        """Test token extraction from query params - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.skip(reason="Token extraction moved to UnifiedAuthenticationService - SSOT compliance")
    def test_extract_token_from_websocket_no_token(self):
        """Test token extraction with no token - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.skip(reason="Token extraction moved to UnifiedAuthenticationService - SSOT compliance")
    def test_extract_token_invalid_base64_subprotocol(self):
        """Test invalid base64 handling - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.skip(reason="authenticate_websocket method eliminated - replaced with authenticate_websocket_connection")
    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self):
        """Test WebSocket authentication - SKIPPED (replaced in SSOT consolidation).
        
        This method has been replaced with authenticate_websocket_connection() in the unified system.
        """
        pass
    
    @pytest.mark.skip(reason="authenticate_websocket method eliminated - replaced with authenticate_websocket_connection")
    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self):
        """Test WebSocket authentication with no token - SKIPPED (replaced in SSOT consolidation).
        
        This method has been replaced with authenticate_websocket_connection() in the unified system.
        """
        pass
    
    @pytest.mark.skip(reason="authenticate_websocket method eliminated - replaced with authenticate_websocket_connection")
    @pytest.mark.asyncio
    async def test_authenticate_websocket_auth_service_unavailable(self):
        """Test WebSocket auth service unavailable - SKIPPED (replaced in SSOT consolidation).
        
        This method has been replaced with authenticate_websocket_connection() in the unified system.
        """
        pass
    
    def test_get_websocket_auth_stats(self):
        """Test WebSocket authentication statistics retrieval (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Manually set stats for testing
        authenticator._websocket_auth_attempts = 10
        authenticator._websocket_auth_successes = 7
        authenticator._websocket_auth_failures = 3
        
        stats = authenticator.get_websocket_auth_stats()
        
        # Test authentication statistics calculation
        assert stats["websocket_auth_statistics"]["total_attempts"] == 10
        assert stats["websocket_auth_statistics"]["successful_authentications"] == 7
        assert stats["websocket_auth_statistics"]["failed_authentications"] == 3
        assert stats["websocket_auth_statistics"]["success_rate_percent"] == 70.0  # (7/10)*100
        assert stats["ssot_compliance"]["ssot_compliant"] is True
    
    def test_get_websocket_auth_stats_no_attempts(self):
        """Test WebSocket auth stats with no attempts (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        stats = authenticator.get_websocket_auth_stats()
        
        # Test zero attempts edge case - should handle division by zero
        assert stats["websocket_auth_statistics"]["total_attempts"] == 0
        assert stats["websocket_auth_statistics"]["success_rate_percent"] == 0.0  # Should handle division by zero


@pytest.mark.unit
@pytest.mark.skip(reason="ConnectionSecurityManager eliminated in SSOT consolidation - security handled by UnifiedWebSocketAuthenticator")
class TestConnectionSecurityManager(TestWebSocketAuthComprehensive):
    """Test ConnectionSecurityManager class - SKIPPED (SSOT compliance).
    
    This class has been eliminated as part of SSOT consolidation.
    Security management is now handled directly by UnifiedWebSocketAuthenticator.
    """
    
    def setup_method(self):
        """Setup security manager for each test."""
        super().setup_method()
        # ConnectionSecurityManager no longer exists in unified system
        pass
    
    def test_security_manager_initialization(self):
        """Test ConnectionSecurityManager initialization - SHOULD FAIL initially."""
        manager = ConnectionSecurityManager()
        
        # Test security manager initial state
        assert len(manager._secure_connections) == 0
        assert len(manager._registered_connections) == 0
        assert len(manager._security_violations) == 0
    
    def test_mark_secure_and_is_secure(self):
        """Test marking connections as secure - SHOULD FAIL initially.""" 
        connection_id = "conn-123"
        
        # Initially not secure
        assert not self.security_manager.is_secure(connection_id)
        
        # Mark as secure
        self.security_manager.mark_secure(connection_id)
        
        # Test connection security marking and checking
        assert self.security_manager.is_secure(connection_id) is True
    
    def test_register_connection(self):
        """Test connection registration - SHOULD FAIL initially."""
        connection_id = "conn-456"
        mock_websocket = Mock()
        auth_info = AuthInfo(
            user_id="user123",
            email="test@example.com", 
            permissions=["read"]
        )
        
        self.security_manager.register_connection(connection_id, auth_info, mock_websocket)
        
        # Test connection registration data structure
        assert connection_id in self.security_manager._registered_connections
        connection_info = self.security_manager._registered_connections[connection_id]
        assert connection_info["auth_info"] == auth_info
        assert connection_info["websocket"] == mock_websocket
        assert connection_info["user_id"] == "user123"
        assert "registered_at" in connection_info
        
        # Should also mark as secure
        assert self.security_manager.is_secure(connection_id) is True
    
    def test_unregister_connection(self):
        """Test connection unregistration - SHOULD FAIL initially."""
        connection_id = "conn-789"
        auth_info = AuthInfo(user_id="user123", email="test@example.com", permissions=[])
        
        # Register first
        self.security_manager.register_connection(connection_id, auth_info, Mock())
        
        # Add a security violation
        self.security_manager.report_security_violation(connection_id, "test_violation")
        
        # Unregister
        self.security_manager.unregister_connection(connection_id)
        
        # Test connection cleanup removes all data
        assert connection_id not in self.security_manager._registered_connections
        assert not self.security_manager.is_secure(connection_id)
        assert connection_id not in self.security_manager._security_violations
    
    def test_validate_connection_security_success(self):
        """Test successful connection security validation - SHOULD FAIL initially."""
        connection_id = "secure-conn"
        auth_info = AuthInfo(user_id="user123", email="test@example.com", permissions=[])
        
        self.security_manager.register_connection(connection_id, auth_info, Mock())
        
        result = self.security_manager.validate_connection_security(connection_id)
        
        # Test successful security validation
        assert result is True
    
    def test_validate_connection_security_not_registered(self):
        """Test security validation for unregistered connection - SHOULD FAIL initially."""
        result = self.security_manager.validate_connection_security("unknown-conn")
        
        # This might NOT fail as expected
        assert result is False
    
    def test_validate_connection_security_not_secure(self):
        """Test security validation for insecure connection - SHOULD FAIL initially."""
        connection_id = "insecure-conn"
        auth_info = AuthInfo(user_id="user123", email="test@example.com", permissions=[])
        
        # Register but don't mark secure (bypass normal registration)
        self.security_manager._registered_connections[connection_id] = {
            "auth_info": auth_info,
            "websocket": Mock(),
            "registered_at": time.time(),
            "user_id": "user123"
        }
        
        result = self.security_manager.validate_connection_security(connection_id)
        
        # Test security validation for insecure connection
        assert result is False
    
    def test_validate_connection_security_too_many_violations(self):
        """Test security validation with too many violations - SHOULD FAIL initially."""
        connection_id = "violation-conn"
        auth_info = AuthInfo(user_id="user123", email="test@example.com", permissions=[])
        
        self.security_manager.register_connection(connection_id, auth_info, Mock())
        
        # Add too many violations (more than 5)
        for i in range(6):
            self.security_manager.report_security_violation(
                connection_id, 
                f"violation_{i}",
                {"count": i}
            )
        
        result = self.security_manager.validate_connection_security(connection_id)
        
        # Test security validation with excessive violations (>5)
        assert result is False
    
    def test_report_security_violation(self):
        """Test security violation reporting - SHOULD FAIL initially."""
        connection_id = "violator-conn"
        violation_type = "unauthorized_access"
        details = {"ip": "192.168.1.1", "timestamp": "2024-01-01"}
        
        self.security_manager.report_security_violation(connection_id, violation_type, details)
        
        # Test security violation reporting and storage
        assert connection_id in self.security_manager._security_violations
        violations = self.security_manager._security_violations[connection_id]
        assert len(violations) == 1
        
        violation = violations[0]
        assert violation["type"] == violation_type
        assert violation["details"] == details
        assert "timestamp" in violation
    
    def test_get_security_summary(self):
        """Test security summary generation - SHOULD FAIL initially."""
        # Setup test data
        auth_info = AuthInfo(user_id="user123", email="test@example.com", permissions=[])
        
        self.security_manager.register_connection("conn1", auth_info, Mock())
        self.security_manager.register_connection("conn2", auth_info, Mock())
        
        self.security_manager.report_security_violation("conn1", "violation1")
        self.security_manager.report_security_violation("conn1", "violation2") 
        self.security_manager.report_security_violation("conn2", "violation3")
        
        summary = self.security_manager.get_security_summary()
        
        # Test security summary statistics compilation
        assert summary["secure_connections"] == 2
        assert summary["registered_connections"] == 2
        assert summary["total_violations"] == 3
        assert summary["connections_with_violations"] == 2


@pytest.mark.unit
@pytest.mark.skip(reason="RateLimiter extracted to separate module - not part of WebSocket auth testing scope")
class TestRateLimiter(TestWebSocketAuthComprehensive):
    """Test RateLimiter class - SKIPPED (moved to dedicated rate limiting module).
    
    Rate limiting functionality has been moved to dedicated modules and is
    tested separately from WebSocket authentication.
    """
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization with defaults - SHOULD FAIL initially."""
        rate_limiter = RateLimiter()
        
        # Test rate limiter default configuration values
        assert rate_limiter.max_requests == 100
        assert rate_limiter.window_seconds == 60
        assert len(rate_limiter._requests) == 0
    
    def test_rate_limiter_custom_initialization(self):
        """Test RateLimiter with custom parameters - SHOULD FAIL initially."""
        rate_limiter = RateLimiter(max_requests=50, window_seconds=30)
        
        # This might fail due to parameter handling
        assert rate_limiter.max_requests == 50
        assert rate_limiter.window_seconds == 30
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_always_true(self):
        """Test rate limit check always returns True - SHOULD FAIL initially."""
        rate_limiter = RateLimiter()
        
        result = await rate_limiter.check_rate_limit("user123")
        
        # Test simplified rate limiter always returns True
        assert result is True, "Rate limiter should always return True in current implementation"


@pytest.mark.unit
class TestGlobalFunctions(TestWebSocketAuthComprehensive):
    """Test global utility functions (SSOT unified auth)."""
    
    def test_get_websocket_authenticator_singleton(self):
        """Test WebSocket authenticator singleton pattern (SSOT unified auth)."""
        # Clear global state
        import netra_backend.app.websocket_core.unified_websocket_auth as unified_auth_module
        unified_auth_module._websocket_authenticator = None
        
        authenticator1 = get_websocket_authenticator()
        authenticator2 = get_websocket_authenticator()
        
        # Test singleton pattern ensures same instance returned
        assert authenticator1 is authenticator2
        assert isinstance(authenticator1, UnifiedWebSocketAuthenticator)
    
    @pytest.mark.skip(reason="ConnectionSecurityManager eliminated in SSOT consolidation")
    def test_get_connection_security_manager_singleton(self):
        """Test connection security manager singleton - SKIPPED (SSOT compliance).
        
        ConnectionSecurityManager has been eliminated as part of SSOT consolidation.
        Security is now handled directly by UnifiedWebSocketAuthenticator.
        """
        pass
    
    @pytest.mark.skip(reason="secure_websocket_context eliminated - replaced with direct authentication")
    @pytest.mark.asyncio
    async def test_secure_websocket_context_string_legacy(self):
        """Test secure WebSocket context - SKIPPED (SSOT compliance).
        
        secure_websocket_context has been eliminated. The unified system uses
        direct authentication through UnifiedWebSocketAuthenticator.
        """
        pass
    
    @pytest.mark.skip(reason="secure_websocket_context eliminated - replaced with direct authentication")
    @pytest.mark.asyncio
    async def test_secure_websocket_context_websocket_object(self):
        """Test secure WebSocket context with WebSocket object - SKIPPED (SSOT compliance).
        
        secure_websocket_context has been eliminated. The unified system uses
        direct authentication through UnifiedWebSocketAuthenticator.authenticate_websocket_connection().
        """
        pass


@pytest.mark.unit
class TestEdgeCasesAndFailureScenarios(TestWebSocketAuthComprehensive):
    """Test edge cases and failure scenarios (SSOT unified auth)."""
    
    def setup_method(self):
        """Setup for edge case tests."""
        super().setup_method()
        # No security manager needed in unified system
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_missing_user_id(self):
        """Test WebSocket auth failure when token missing user_id (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock WebSocket object
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        mock_websocket.client_state = "connected"
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        
        # Mock validation result without user_id
        mock_auth_result = AuthResult(
            success=False,
            error="Invalid token: missing user_id",
            error_code="VALIDATION_FAILED"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, None)
        )
        
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Test handling of token validation result missing user_id  
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert authenticator._websocket_auth_failures == 1
    
    @pytest.mark.asyncio 
    async def test_authenticate_websocket_token_expired(self):
        """Test WebSocket authentication when token expired (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock WebSocket object
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        mock_websocket.client_state = "connected"
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        
        mock_auth_result = AuthResult(
            success=False,
            error="Token expired",
            error_code="TOKEN_EXPIRED"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, None)
        )
        
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Test handling of validation result with expired token
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is False
        assert result.error_code == "TOKEN_EXPIRED"
        assert authenticator._websocket_auth_failures == 1
    
    @pytest.mark.skip(reason="Token extraction moved to UnifiedAuthenticationService - SSOT compliance")
    def test_extract_token_malformed_authorization_header(self):
        """Test malformed auth header - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.skip(reason="Token extraction moved to UnifiedAuthenticationService - SSOT compliance")
    def test_extract_token_multiple_subprotocols(self):
        """Test multiple subprotocols - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.skip(reason="ConnectionSecurityManager eliminated in SSOT consolidation")
    def test_security_manager_unregister_nonexistent_connection(self):
        """Test unregistering nonexistent connection - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.skip(reason="ConnectionSecurityManager eliminated in SSOT consolidation")
    def test_security_manager_report_violation_no_details(self):
        """Test security violation reporting - SKIPPED (SSOT compliance)."""
        pass
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_service_unavailable(self):
        """Test WebSocket auth with service unavailable (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock WebSocket object
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        mock_websocket.client_state = "connected"
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        
        # Mock service unavailable scenario
        mock_auth_result = AuthResult(
            success=False,
            error="Authentication service temporarily unavailable",
            error_code="AUTH_SERVICE_ERROR"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, None)
        )
        
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Service unavailable results in auth failure
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is False
        assert result.error_code == "AUTH_SERVICE_ERROR"
    
    def test_websocket_auth_stats_zero_attempts_edge_case(self):
        """Test WebSocket auth stats calculation edge case (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Verify zero attempts case
        stats = authenticator.get_websocket_auth_stats()
        
        # Test zero attempts case - verify division by zero handling
        assert stats["websocket_auth_statistics"]["total_attempts"] == 0
        assert stats["websocket_auth_statistics"]["success_rate_percent"] == 0.0


# Additional comprehensive coverage tests
@pytest.mark.unit
@pytest.mark.comprehensive
class TestComplexIntegrationScenarios(TestWebSocketAuthComprehensive):
    """Test complex integration scenarios (SSOT unified auth)."""
    
    @pytest.mark.asyncio
    async def test_full_websocket_auth_flow_unified(self):
        """Test complete WebSocket auth flow with SSOT unified authentication."""
        
        # Mock WebSocket object
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        mock_websocket.client_state = "connected"
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 8080
        
        # Step 1: Get authenticator and authenticate
        authenticator = get_websocket_authenticator()
        
        # Mock successful authentication response
        mock_auth_result = AuthResult(
            success=True,
            user_id="integration-user",
            email="integration@example.com",
            permissions=["read", "write"],
            validated_at=datetime.now(timezone.utc)
        )
        mock_user_context = UserExecutionContext(
            user_id="integration-user",
            thread_id="integration-thread",
            run_id="integration-run",
            websocket_client_id="integration-ws-client"
        )
        
        authenticator._auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_auth_result, mock_user_context)
        )
        
        # Execute authentication
        result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Step 2: Verify complete integration
        assert isinstance(result, WebSocketAuthResult)
        assert result.success is True
        assert result.user_context.user_id == "integration-user"
        assert result.auth_result.email == "integration@example.com"
        assert result.auth_result.permissions == ["read", "write"]
        
        # Step 3: Test statistics tracking
        stats = authenticator.get_websocket_auth_stats()
        assert stats["websocket_auth_statistics"]["total_attempts"] == 1
        assert stats["websocket_auth_statistics"]["successful_authentications"] == 1
        assert stats["ssot_compliance"]["ssot_compliant"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_authentication_race_condition(self):
        """Test concurrent WebSocket authentication requests (SSOT unified auth)."""
        authenticator = UnifiedWebSocketAuthenticator()
        
        async def auth_task(task_id):
            # Mock WebSocket object for each task
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
            mock_websocket.client_state = "connected"
            mock_websocket.client = Mock()
            mock_websocket.client.host = "127.0.0.1"
            
            # Mock successful auth response with unique user per task
            mock_auth_result = AuthResult(
                success=True,
                user_id=f"concurrent-user-{task_id}",
                email="test@example.com",
                permissions=[],
                validated_at=datetime.now(timezone.utc)
            )
            mock_user_context = UserExecutionContext(
                user_id=f"concurrent-user-{task_id}",
                thread_id=f"thread-{task_id}",
                run_id=f"run-{task_id}",
                websocket_client_id=f"ws-{task_id}"
            )
            
            authenticator._auth_service.authenticate_websocket = AsyncMock(
                return_value=(mock_auth_result, mock_user_context)
            )
            
            return await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Run multiple concurrent authentications
        tasks = [auth_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Test concurrent authentication requests for race conditions
        assert all(isinstance(result, WebSocketAuthResult) and result.success for result in results)
        assert authenticator._websocket_auth_attempts == 5
        assert authenticator._websocket_auth_successes == 5