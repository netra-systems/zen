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

Test Coverage Target: 100% of critical authentication flows in websocket_core/auth.py
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

# Import the module under test
from netra_backend.app.websocket_core.auth import (
    AuthInfo,
    WebSocketAuthenticator,
    ConnectionSecurityManager,
    RateLimiter,
    get_websocket_authenticator,
    get_connection_security_manager,
    secure_websocket_context
)


class TestWebSocketAuthComprehensive(BaseIntegrationTest):
    """Comprehensive test suite for WebSocket authentication module."""
    
    def setup_method(self):
        """Setup test fixtures and clear global state."""
        super().setup_method()
        self.jwt_helper = JWTTestHelper()
        
        # Clear global instances for clean test state
        import netra_backend.app.websocket_core.auth as auth_module
        auth_module._authenticator = None
        auth_module._security_manager = None
        
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
class TestWebSocketAuthenticator(TestWebSocketAuthComprehensive):
    """Test WebSocketAuthenticator class comprehensively."""
    
    def test_authenticator_initialization(self):
        """Test WebSocketAuthenticator initialization."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient') as mock_auth_client:
            authenticator = WebSocketAuthenticator()
            
            # Should create AuthServiceClient instance
            mock_auth_client.assert_called_once()
            assert authenticator._auth_attempts == 0
            assert authenticator._successful_auths == 0
            assert authenticator._failed_auths == 0
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful token authentication with controlled auth service response."""
        authenticator = WebSocketAuthenticator()
        
        # Mock auth client to return successful validation
        mock_validation_result = {
            "valid": True,
            "user_id": "test-user-123",
            "email": "test@example.com",
            "permissions": ["read", "write"]
        }
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation_result)
        
        result = await authenticator.authenticate(self.valid_token)
        
        # Verify the auth result structure
        assert result is not None, "Should return auth result for valid token"
        assert result["user_id"] == "test-user-123"
        assert result["email"] == "test@example.com" 
        assert result["permissions"] == ["read", "write"]
        assert result["authenticated"] is True
        assert result["source"] == "jwt_validation"
        
        # Stats should be updated
        assert authenticator._auth_attempts == 1
        assert authenticator._successful_auths == 1
        assert authenticator._failed_auths == 0
    
    @pytest.mark.asyncio
    async def test_authenticate_no_token(self):
        """Test authentication with no token returns None and updates failure stats."""
        authenticator = WebSocketAuthenticator()
        
        # Test empty token
        result = await authenticator.authenticate("")
        assert result is None, "Empty token should return None"
        
        # Test None token
        result = await authenticator.authenticate(None)
        assert result is None, "None token should return None"
        
        # Stats should reflect failures (no attempts since tokens were invalid)
        assert authenticator._auth_attempts == 0
        assert authenticator._failed_auths == 2
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self):
        """Test authentication with invalid token - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Mock auth client to return invalid validation
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=None)
        
        result = await authenticator.authenticate(self.invalid_token)
        
        # Test with controlled mock response to verify error path
        assert result is None, "Invalid token should return None"
        assert authenticator._auth_attempts == 1
        assert authenticator._failed_auths == 1
    
    @pytest.mark.asyncio
    async def test_authenticate_auth_service_unavailable(self):
        """Test authentication when auth service is unavailable - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Mock circuit breaker in OPEN state
        mock_circuit_breaker = Mock()
        mock_circuit_breaker.state = "OPEN"  # This will fail - need correct enum
        authenticator.auth_client.circuit_breaker = mock_circuit_breaker
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=None)
        
        result = await authenticator.authenticate(self.valid_token)
        
        # Test circuit breaker OPEN state handling
        assert result is None, "Should return None when auth service unavailable"
        assert authenticator._failed_auths == 1
    
    @pytest.mark.asyncio
    async def test_authenticate_bearer_token_cleaning(self):
        """Test Bearer token prefix cleaning - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        mock_validation_result = {
            "valid": True,
            "user_id": "test-user-123",
            "email": "test@example.com",
            "permissions": []
        }
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation_result)
        
        bearer_token = f"Bearer {self.valid_token}"
        result = await authenticator.authenticate(bearer_token)
        
        # Test Bearer token prefix cleaning
        assert result is not None, "Should handle Bearer prefix"
        authenticator.auth_client.validate_token_jwt.assert_called_once_with(self.valid_token)
    
    @pytest.mark.asyncio
    async def test_authenticate_exception_handling(self):
        """Test authentication exception handling - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Mock auth client to raise exception
        authenticator.auth_client.validate_token_jwt = AsyncMock(side_effect=Exception("Network error"))
        
        result = await authenticator.authenticate(self.valid_token)
        
        # This might NOT fail as expected due to exception handling
        assert result is None, "Exception should result in None"
        assert authenticator._failed_auths == 1
    
    def test_extract_token_from_websocket_authorization_header(self):
        """Test token extraction from Authorization header - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Mock WebSocket with Authorization header
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        
        token = authenticator.extract_token_from_websocket(mock_websocket)
        
        # Test token extraction from Authorization header
        assert token == self.valid_token, "Should extract token from Authorization header"
    
    def test_extract_token_from_websocket_subprotocol(self):
        """Test token extraction from Sec-WebSocket-Protocol - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Create base64 encoded token for subprotocol
        encoded_token = base64.urlsafe_b64encode(self.valid_token.encode('utf-8')).decode('utf-8')
        subprotocol_value = f"jwt.{encoded_token}"
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "",  # No auth header
            "sec-websocket-protocol": subprotocol_value
        }
        
        token = authenticator.extract_token_from_websocket(mock_websocket)
        
        # Test token extraction from subprotocol with base64 encoding
        assert token == self.valid_token, "Should extract token from subprotocol"
    
    def test_extract_token_from_websocket_query_params(self):
        """Test token extraction from query parameters - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": ""}  # No auth header or subprotocol
        mock_websocket.query_params = {"token": self.valid_token}
        
        token = authenticator.extract_token_from_websocket(mock_websocket)
        
        # Test token extraction from query parameters (when available)
        assert token == self.valid_token, "Should extract token from query parameters"
    
    def test_extract_token_from_websocket_no_token(self):
        """Test token extraction when no token present returns None."""
        authenticator = WebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {}
        # Remove query_params to simulate WebSocket without query parameters
        del mock_websocket.query_params
        
        token = authenticator.extract_token_from_websocket(mock_websocket)
        
        assert token is None, "Should return None when no token found"
    
    def test_extract_token_invalid_base64_subprotocol(self):
        """Test handling of invalid base64 in subprotocol returns None gracefully."""
        authenticator = WebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "",
            "sec-websocket-protocol": "jwt.invalid_base64!!!"
        }
        # Ensure query_params doesn't interfere
        del mock_websocket.query_params
        
        token = authenticator.extract_token_from_websocket(mock_websocket)
        
        assert token is None, "Should handle invalid base64 gracefully"
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self):
        """Test complete WebSocket authentication success - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Mock token extraction
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        
        # Mock successful authentication
        mock_validation_result = {
            "valid": True,
            "user_id": "test-user-123", 
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "authenticated": True
        }
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation_result)
        
        auth_info = await authenticator.authenticate_websocket(mock_websocket)
        
        # Test complete WebSocket authentication integration
        assert isinstance(auth_info, AuthInfo), "Should return AuthInfo object"
        assert auth_info.user_id == "test-user-123"
        assert auth_info.email == "test@example.com"
        assert auth_info.permissions == ["read", "write"]
        assert auth_info.authenticated is True
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self):
        """Test WebSocket authentication with no token raises 401 HTTPException."""
        authenticator = WebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {}
        # Ensure no query_params
        del mock_websocket.query_params
        
        with pytest.raises(HTTPException) as exc_info:
            await authenticator.authenticate_websocket(mock_websocket)
        
        assert exc_info.value.status_code == 401
        assert "No authentication token provided" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_auth_service_unavailable(self):
        """Test WebSocket auth when service unavailable returns 401 HTTPException.
        
        Note: The current implementation always returns 401 for auth failures,
        including service unavailable scenarios, because authenticate() returns None
        when validation fails, which triggers the 401 path in authenticate_websocket().
        """
        authenticator = WebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        
        # Mock auth service failure with service unavailable error
        mock_result = {
            "valid": False,
            "error": "service unavailable",
            "details": "Circuit breaker open"
        }
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=mock_result)
        
        with pytest.raises(HTTPException) as exc_info:
            await authenticator.authenticate_websocket(mock_websocket)
        
        # Verify current actual behavior - returns 401 even for service unavailable
        assert exc_info.value.status_code == 401, "Current implementation returns 401 for all auth failures"
        assert "Invalid or expired authentication token" in str(exc_info.value.detail)
    
    def test_get_auth_stats(self):
        """Test authentication statistics retrieval - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Manually set stats
        authenticator._auth_attempts = 10
        authenticator._successful_auths = 7
        authenticator._failed_auths = 3
        
        stats = authenticator.get_auth_stats()
        
        # Test authentication statistics calculation
        assert stats["total_attempts"] == 10
        assert stats["successful_auths"] == 7
        assert stats["failed_auths"] == 3
        assert stats["success_rate"] == 0.7  # 7/10
    
    def test_get_auth_stats_no_attempts(self):
        """Test auth stats with no attempts to avoid division by zero - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        stats = authenticator.get_auth_stats()
        
        # Test zero attempts edge case - should use 0.0 success rate
        assert stats["total_attempts"] == 0
        assert stats["success_rate"] == 0.0  # Should handle division by zero


@pytest.mark.unit
class TestConnectionSecurityManager(TestWebSocketAuthComprehensive):
    """Test ConnectionSecurityManager class comprehensively."""
    
    def setup_method(self):
        """Setup security manager for each test."""
        super().setup_method()
        self.security_manager = ConnectionSecurityManager()
    
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
class TestRateLimiter(TestWebSocketAuthComprehensive):
    """Test RateLimiter class."""
    
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
    """Test global utility functions."""
    
    def test_get_websocket_authenticator_singleton(self):
        """Test WebSocket authenticator singleton pattern - SHOULD FAIL initially."""
        # Clear global state
        import netra_backend.app.websocket_core.auth as auth_module
        auth_module._authenticator = None
        
        authenticator1 = get_websocket_authenticator()
        authenticator2 = get_websocket_authenticator()
        
        # Test singleton pattern ensures same instance returned
        assert authenticator1 is authenticator2
        assert isinstance(authenticator1, WebSocketAuthenticator)
    
    def test_get_connection_security_manager_singleton(self):
        """Test connection security manager singleton pattern - SHOULD FAIL initially."""
        # Clear global state
        import netra_backend.app.websocket_core.auth as auth_module
        auth_module._security_manager = None
        
        manager1 = get_connection_security_manager()
        manager2 = get_connection_security_manager()
        
        # Test singleton pattern ensures same instance returned
        assert manager1 is manager2
        assert isinstance(manager1, ConnectionSecurityManager)
    
    @pytest.mark.asyncio
    async def test_secure_websocket_context_string_legacy(self):
        """Test secure WebSocket context with string parameter (legacy) - SHOULD FAIL initially."""
        connection_id = "legacy-conn-123"
        
        async with secure_websocket_context(connection_id):
            # Should mark connection as secure  
            manager = get_connection_security_manager()
            # Test legacy string parameter mode compatibility
            assert manager.is_secure(connection_id) is True
    
    @pytest.mark.asyncio
    async def test_secure_websocket_context_websocket_object(self):
        """Test secure WebSocket context with WebSocket object - SHOULD FAIL initially."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        
        # Mock the authenticator
        with patch('netra_backend.app.websocket_core.auth.get_websocket_authenticator') as mock_get_auth:
            mock_authenticator = AsyncMock()
            mock_auth_info = AuthInfo(
                user_id="test-user",
                email="test@example.com", 
                permissions=["read"]
            )
            mock_authenticator.authenticate_websocket = AsyncMock(return_value=mock_auth_info)
            mock_get_auth.return_value = mock_authenticator
            
            async with secure_websocket_context(mock_websocket) as (auth_info, security_manager):
                # Test context manager authentication and security manager return
                assert isinstance(auth_info, AuthInfo)
                assert auth_info.user_id == "test-user"
                assert isinstance(security_manager, ConnectionSecurityManager)


@pytest.mark.unit
class TestEdgeCasesAndFailureScenarios(TestWebSocketAuthComprehensive):
    """Test edge cases and failure scenarios."""
    
    def setup_method(self):
        """Setup security manager for edge case tests."""
        super().setup_method()
        self.security_manager = ConnectionSecurityManager()
    
    @pytest.mark.asyncio
    async def test_authenticate_missing_user_id_in_valid_token(self):
        """Test auth failure when valid token missing user_id - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Mock validation result without user_id
        mock_result = {
            "valid": True,
            "email": "test@example.com",
            "permissions": ["read"]
            # Missing user_id field
        }
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=mock_result)
        
        result = await authenticator.authenticate(self.valid_token)
        
        # Test handling of token validation result missing user_id  
        assert result is None
        assert authenticator._failed_auths == 1
    
    @pytest.mark.asyncio 
    async def test_authenticate_validation_returns_invalid_false(self):
        """Test authentication when validation returns valid=False - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        mock_result = {
            "valid": False,
            "error": "Token expired",
            "details": "Token expired at 2024-01-01"
        }
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=mock_result)
        
        result = await authenticator.authenticate(self.valid_token)
        
        # Test handling of validation result with valid=False
        assert result is None
        assert authenticator._failed_auths == 1
    
    def test_extract_token_malformed_authorization_header(self):
        """Test token extraction with malformed Authorization header returns None."""
        authenticator = WebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": "Malformed header value"}
        # Ensure query_params doesn't interfere
        del mock_websocket.query_params
        
        token = authenticator.extract_token_from_websocket(mock_websocket)
        
        assert token is None, "Malformed authorization header should return None"
    
    def test_extract_token_multiple_subprotocols(self):
        """Test token extraction with multiple subprotocols - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        encoded_token = base64.urlsafe_b64encode(self.valid_token.encode('utf-8')).decode('utf-8')
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "",
            "sec-websocket-protocol": f"protocol1, jwt.{encoded_token}, protocol2"
        }
        
        token = authenticator.extract_token_from_websocket(mock_websocket)
        
        # Test subprotocol parsing with multiple comma-separated protocols
        assert token == self.valid_token
    
    def test_security_manager_unregister_nonexistent_connection(self):
        """Test unregistering connection that doesn't exist - SHOULD FAIL initially."""
        # This should not raise an exception
        security_manager = ConnectionSecurityManager()
        security_manager.unregister_connection("nonexistent-conn")
        
        # This might fail due to exception handling
        # Should pass silently
        assert True  # Just verify no exception raised
    
    def test_security_manager_report_violation_no_details(self):
        """Test reporting security violation without details - SHOULD FAIL initially."""
        connection_id = "no-details-conn"
        
        security_manager = ConnectionSecurityManager()
        security_manager.report_security_violation(connection_id, "basic_violation")
        
        # Test default details handling
        violations = security_manager._security_violations[connection_id]
        assert len(violations) == 1
        assert violations[0]["details"] == {}  # Should default to empty dict
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_circuit_breaker_scenario(self):
        """Test WebSocket auth with circuit breaker open returns 401 (auth failed)."""
        authenticator = WebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        
        # Mock circuit breaker scenario - when circuit breaker is open, validate_token_jwt returns None
        from netra_backend.app.clients.circuit_breaker import CircuitState
        mock_circuit_breaker = Mock()
        mock_circuit_breaker.state = CircuitState.OPEN
        authenticator.auth_client.circuit_breaker = mock_circuit_breaker
        authenticator.auth_client.validate_token_jwt = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await authenticator.authenticate_websocket(mock_websocket)
        
        # Circuit breaker open results in 401 (validation failure) not 503
        assert exc_info.value.status_code == 401
        assert "Invalid or expired authentication token" in str(exc_info.value.detail)
    
    def test_auth_stats_with_zero_attempts_edge_case(self):
        """Test auth stats calculation edge case - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        # Verify zero attempts case
        stats = authenticator.get_auth_stats()
        
        # Test zero attempts case - verify max(1, attempts) logic for success_rate
        assert stats["total_attempts"] == 0
        assert stats["success_rate"] == 0.0
        
        # The code uses max(1, attempts) to avoid division by zero, so this will fail
        # because it will calculate 0/1 = 0.0 but total_attempts will show 0


# Additional comprehensive coverage tests
@pytest.mark.unit
@pytest.mark.comprehensive
class TestComplexIntegrationScenarios(TestWebSocketAuthComprehensive):
    """Test complex integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_websocket_auth_flow_with_connection_management(self):
        """Test complete flow: auth -> register -> validate -> cleanup - SHOULD FAIL initially."""
        # This comprehensive test will definitely fail due to multiple integration points
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"authorization": f"Bearer {self.valid_token}"}
        
        # Step 1: Authenticate
        authenticator = get_websocket_authenticator()
        with patch.object(authenticator, 'auth_client') as mock_client:
            mock_client.validate_token_jwt = AsyncMock(return_value={
                "valid": True,
                "user_id": "integration-user",
                "email": "integration@example.com",
                "permissions": ["read", "write"]
            })
            
            auth_info = await authenticator.authenticate_websocket(mock_websocket)
        
        # Step 2: Register with security manager
        security_manager = get_connection_security_manager()
        connection_id = "integration-conn-456"
        security_manager.register_connection(connection_id, auth_info, mock_websocket)
        
        # Step 3: Validate security
        is_secure = security_manager.validate_connection_security(connection_id)
        
        # Step 4: Report violation and test threshold
        for i in range(3):
            security_manager.report_security_violation(connection_id, f"test_violation_{i}")
        
        still_valid = security_manager.validate_connection_security(connection_id)
        
        # Step 5: Cleanup
        security_manager.unregister_connection(connection_id)
        
        # Test integration between authenticator and security manager
        assert auth_info.user_id == "integration-user"
        assert is_secure is True
        assert still_valid is True  # Should still be valid with only 3 violations
        assert not security_manager.is_secure(connection_id)  # Should be cleaned up
    
    @pytest.mark.asyncio
    async def test_concurrent_authentication_race_condition(self):
        """Test concurrent authentication requests - SHOULD FAIL initially."""
        authenticator = WebSocketAuthenticator()
        
        async def auth_task():
            with patch.object(authenticator, 'auth_client') as mock_client:
                mock_client.validate_token_jwt = AsyncMock(return_value={
                    "valid": True,
                    "user_id": f"user-{asyncio.current_task().get_name()}",
                    "email": "test@example.com",
                    "permissions": []
                })
                return await authenticator.authenticate(self.valid_token)
        
        # Run multiple concurrent authentications
        tasks = [auth_task() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Test concurrent authentication requests for race conditions
        assert all(result is not None for result in results)
        assert authenticator._auth_attempts == 5
        assert authenticator._successful_auths == 5