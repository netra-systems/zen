"""
Test UnifiedAuthenticationService - SSOT Authentication

Business Value Justification:
- Segment: Platform/Internal - Security Infrastructure
- Business Goal: System Stability & Security Compliance  
- Value Impact: Ensures authentication security for $120K+ MRR WebSocket connections
- Revenue Impact: Prevents authentication failures that block user access

This test suite validates the SINGLE SOURCE OF TRUTH authentication service
that consolidates all authentication paths across the Netra system.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional

from test_framework.base import BaseTestCase, AsyncTestCase
from test_framework.isolated_environment_fixtures import isolated_env, test_env

from netra_backend.app.services.unified_authentication_service import (
    UnifiedAuthenticationService,
    AuthResult, 
    AuthenticationMethod,
    AuthenticationContext,
    get_unified_auth_service
)
from netra_backend.app.clients.auth_client_core import (
    AuthServiceError,
    AuthServiceConnectionError,
    AuthServiceNotAvailableError, 
    AuthServiceValidationError,
    CircuitBreakerError,
    validate_jwt_format
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAuthResult(BaseTestCase):
    """Test AuthResult class - constructor, to_dict(), all properties."""
    
    def test_auth_result_constructor_success(self):
        """Test AuthResult constructor with successful authentication."""
        result = AuthResult(
            success=True,
            user_id="user123",
            email="test@example.com", 
            permissions=["read", "write"],
            metadata={"context": "test"}
        )
        
        assert result.success is True
        assert result.user_id == "user123"
        assert result.email == "test@example.com"
        assert result.permissions == ["read", "write"]
        assert result.error is None
        assert result.error_code is None
        assert result.metadata == {"context": "test"}
        assert isinstance(result.validated_at, float)
        assert result.validated_at > 0
    
    def test_auth_result_constructor_failure(self):
        """Test AuthResult constructor with failed authentication."""
        result = AuthResult(
            success=False,
            error="Invalid token",
            error_code="INVALID_TOKEN",
            metadata={"debug": "token_length_0"}
        )
        
        assert result.success is False
        assert result.user_id is None
        assert result.email is None
        assert result.permissions == []  # Default empty list
        assert result.error == "Invalid token"
        assert result.error_code == "INVALID_TOKEN"
        assert result.metadata == {"debug": "token_length_0"}
        assert isinstance(result.validated_at, float)
    
    def test_auth_result_constructor_defaults(self):
        """Test AuthResult constructor with minimal parameters."""
        result = AuthResult(success=True)
        
        assert result.success is True
        assert result.user_id is None
        assert result.email is None
        assert result.permissions == []  # Default empty list
        assert result.error is None
        assert result.error_code is None
        assert result.metadata == {}  # Default empty dict
        assert isinstance(result.validated_at, float)
    
    def test_auth_result_to_dict_success(self):
        """Test AuthResult.to_dict() method for successful auth."""
        result = AuthResult(
            success=True,
            user_id="user456",
            email="user@test.com",
            permissions=["admin"],
            metadata={"source": "test"}
        )
        
        dict_result = result.to_dict()
        
        expected_keys = {
            "valid", "success", "user_id", "email", "permissions", 
            "error", "error_code", "metadata", "validated_at"
        }
        assert set(dict_result.keys()) == expected_keys
        
        # Test both valid and success for compatibility
        assert dict_result["valid"] is True
        assert dict_result["success"] is True
        assert dict_result["user_id"] == "user456"
        assert dict_result["email"] == "user@test.com"
        assert dict_result["permissions"] == ["admin"]
        assert dict_result["error"] is None
        assert dict_result["error_code"] is None
        assert dict_result["metadata"] == {"source": "test"}
        assert isinstance(dict_result["validated_at"], float)
    
    def test_auth_result_to_dict_failure(self):
        """Test AuthResult.to_dict() method for failed auth."""
        result = AuthResult(
            success=False,
            error="Service unavailable",
            error_code="SERVICE_ERROR"
        )
        
        dict_result = result.to_dict()
        
        # Test both valid and success for compatibility
        assert dict_result["valid"] is False
        assert dict_result["success"] is False
        assert dict_result["user_id"] is None
        assert dict_result["permissions"] == []
        assert dict_result["error"] == "Service unavailable"
        assert dict_result["error_code"] == "SERVICE_ERROR"


class TestUnifiedAuthenticationServiceInit(BaseTestCase):
    """Test UnifiedAuthenticationService initialization."""
    
    def test_unified_auth_service_init(self, test_env):
        """Test UnifiedAuthenticationService initialization."""
        service = UnifiedAuthenticationService()
        
        # Verify service is properly initialized
        assert service is not None
        assert hasattr(service, '_auth_client')
        assert service._auth_client is not None
        
        # Verify statistics are initialized
        assert service._auth_attempts == 0
        assert service._auth_successes == 0
        assert service._auth_failures == 0
        assert len(service._method_counts) == len(AuthenticationMethod)
        assert len(service._context_counts) == len(AuthenticationContext)
        
        # Verify all enum values are represented
        for method in AuthenticationMethod:
            assert method.value in service._method_counts
            assert service._method_counts[method.value] == 0
        
        for context in AuthenticationContext:
            assert context.value in service._context_counts
            assert service._context_counts[context.value] == 0


class TestAuthenticationEnums(BaseTestCase):
    """Test authentication enum values."""
    
    def test_authentication_method_enum_values(self):
        """Test all AuthenticationMethod enum values."""
        expected_methods = {
            "jwt_token", "basic_auth", "api_key", "service_account"
        }
        
        actual_methods = {method.value for method in AuthenticationMethod}
        assert actual_methods == expected_methods
        
        # Test individual enum values
        assert AuthenticationMethod.JWT_TOKEN.value == "jwt_token"
        assert AuthenticationMethod.BASIC_AUTH.value == "basic_auth"
        assert AuthenticationMethod.API_KEY.value == "api_key"
        assert AuthenticationMethod.SERVICE_ACCOUNT.value == "service_account"
    
    def test_authentication_context_enum_values(self):
        """Test all AuthenticationContext enum values."""
        expected_contexts = {
            "rest_api", "websocket", "graphql", "grpc", "internal_service"
        }
        
        actual_contexts = {context.value for context in AuthenticationContext}
        assert actual_contexts == expected_contexts
        
        # Test individual enum values
        assert AuthenticationContext.REST_API.value == "rest_api"
        assert AuthenticationContext.WEBSOCKET.value == "websocket"
        assert AuthenticationContext.GRAPHQL.value == "graphql"
        assert AuthenticationContext.GRPC.value == "grpc"
        assert AuthenticationContext.INTERNAL_SERVICE.value == "internal_service"


class TestAuthenticateToken(AsyncTestCase):
    """Test authenticate_token() method - all success/failure paths."""
    
    async def test_authenticate_token_jwt_success(self, test_env):
        """Test successful JWT token authentication."""
        service = UnifiedAuthenticationService()
        
        # Mock the auth client to return successful validation
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "user123",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "iat": 1234567890,
            "exp": 1234567999
        })
        
        # Mock validate_jwt_format to return True
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            result = await service.authenticate_token(
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature",
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )
        
        # Verify successful result
        assert result.success is True
        assert result.user_id == "user123"
        assert result.email == "test@example.com"
        assert result.permissions == ["read", "write"]
        assert result.error is None
        assert result.error_code is None
        assert result.metadata["context"] == "rest_api"
        assert result.metadata["method"] == "jwt_token"
        assert result.metadata["token_issued_at"] == 1234567890
        assert result.metadata["token_expires_at"] == 1234567999
        
        # Verify statistics updated
        assert service._auth_attempts == 1
        assert service._auth_successes == 1
        assert service._auth_failures == 0
        assert service._method_counts["jwt_token"] == 1
        assert service._context_counts["rest_api"] == 1
    
    async def test_authenticate_token_invalid_format(self, test_env):
        """Test authentication with invalid token format."""
        service = UnifiedAuthenticationService()
        
        # Mock validate_jwt_format to return False
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=False):
            result = await service.authenticate_token(
                "invalid-token",
                context=AuthenticationContext.WEBSOCKET,
                method=AuthenticationMethod.JWT_TOKEN
            )
        
        # Verify failure result
        assert result.success is False
        assert result.user_id is None
        assert result.error.startswith("Invalid token format:")
        assert result.error_code == "INVALID_FORMAT"
        assert result.metadata["context"] == "websocket"
        assert result.metadata["method"] == "jwt_token"
        assert "token_debug" in result.metadata
        
        # Verify token analysis in metadata
        token_debug = result.metadata["token_debug"]
        assert token_debug["length"] == 13
        assert token_debug["has_dots"] == 0
        assert token_debug["environment_context"] == "websocket"
        
        # Verify statistics updated
        assert service._auth_attempts == 1
        assert service._auth_successes == 0
        assert service._auth_failures == 1
    
    async def test_authenticate_token_validation_failed(self, test_env):
        """Test authentication when token validation fails."""
        service = UnifiedAuthenticationService()
        
        # Mock the auth client to return failed validation
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": False,
            "error": "Token expired",
            "details": {"exp": 1234567890, "current": 1234568000}
        })
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            result = await service.authenticate_token(
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.signature",
                context=AuthenticationContext.GRAPHQL,
                method=AuthenticationMethod.JWT_TOKEN
            )
        
        # Verify failure result
        assert result.success is False
        assert result.user_id is None
        assert result.error.startswith("Token expired")
        assert result.error_code == "VALIDATION_FAILED"
        assert result.metadata["context"] == "graphql"
        assert result.metadata["details"]["exp"] == 1234567890
        assert "failure_debug" in result.metadata
        
        # Verify statistics updated
        assert service._auth_failures == 1
        assert service._context_counts["graphql"] == 1
    
    async def test_authenticate_token_auth_service_error(self, test_env):
        """Test authentication when auth service throws error."""
        service = UnifiedAuthenticationService()
        
        # Mock the auth client to raise AuthServiceError
        service._auth_client.validate_token = AsyncMock(
            side_effect=AuthServiceConnectionError("Connection refused")
        )
        
        # Mock the enhanced resilience method to not interfere
        service._validate_token_with_enhanced_resilience = AsyncMock(
            side_effect=AuthServiceConnectionError("Connection refused")
        )
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            result = await service.authenticate_token(
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature",
                context=AuthenticationContext.GRPC,
                method=AuthenticationMethod.API_KEY
            )
        
        # Verify error result
        assert result.success is False
        assert result.error == "Authentication service error: Connection refused"
        assert result.error_code == "AUTH_SERVICE_ERROR"
        assert result.metadata["context"] == "grpc"
        assert result.metadata["method"] == "api_key"
        assert "service_error_debug" in result.metadata
        
        # Verify error debug information
        error_debug = result.metadata["service_error_debug"]
        assert error_debug["error_type"] == "AuthServiceConnectionError"
        assert error_debug["error_message"] == "Connection refused"
        
        # Verify statistics updated
        assert service._auth_failures == 1
        assert service._method_counts["api_key"] == 1
        assert service._context_counts["grpc"] == 1
    
    async def test_authenticate_token_unexpected_error(self, test_env):
        """Test authentication when unexpected error occurs."""
        service = UnifiedAuthenticationService()
        
        # Mock the auth client to raise unexpected error
        service._auth_client.validate_token = AsyncMock(
            side_effect=ValueError("Unexpected validation error")
        )
        
        # Mock the enhanced resilience method to not interfere
        service._validate_token_with_enhanced_resilience = AsyncMock(
            side_effect=ValueError("Unexpected validation error")
        )
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            result = await service.authenticate_token(
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature",
                context=AuthenticationContext.INTERNAL_SERVICE,
                method=AuthenticationMethod.SERVICE_ACCOUNT
            )
        
        # Verify error result
        assert result.success is False
        assert result.error == "Authentication error: Unexpected validation error"
        assert result.error_code == "UNEXPECTED_ERROR"
        assert result.metadata["context"] == "internal_service"
        assert "unexpected_error_debug" in result.metadata
        
        # Verify error debug information
        error_debug = result.metadata["unexpected_error_debug"]
        assert error_debug["error_type"] == "ValueError"
        assert error_debug["error_message"] == "Unexpected validation error"
        
        # Verify statistics updated
        assert service._auth_failures == 1
        assert service._method_counts["service_account"] == 1
        assert service._context_counts["internal_service"] == 1
    
    async def test_authenticate_token_no_validation_result(self, test_env):
        """Test authentication when auth client returns None."""
        service = UnifiedAuthenticationService()
        
        # Mock the auth client to return None
        service._auth_client.validate_token = AsyncMock(return_value=None)
        
        # Mock the enhanced resilience method to return None
        service._validate_token_with_enhanced_resilience = AsyncMock(return_value=None)
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            result = await service.authenticate_token(
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"
            )
        
        # Verify failure result
        assert result.success is False
        assert result.error.startswith("No validation result") or result.error.startswith("Token validation failed")
        assert result.error_code == "VALIDATION_FAILED"
        assert "failure_debug" in result.metadata
        
        # Verify failure debug information
        failure_debug = result.metadata["failure_debug"]
        assert failure_debug["validation_result_exists"] is False
        assert failure_debug["auth_service_response_status"] == "missing"


class TestWebSocketAuthentication(AsyncTestCase):
    """Test authenticate_websocket() method - WebSocket auth flows."""
    
    def create_mock_websocket(self, headers: Dict[str, str] = None, query_params: Dict[str, str] = None) -> Mock:
        """Create a mock WebSocket object with specified headers and query params."""
        websocket = Mock()
        websocket.headers = headers or {}
        websocket.query_params = query_params or {}
        
        # Mock client info
        client_mock = Mock()
        client_mock.host = "127.0.0.1"
        client_mock.port = 12345
        websocket.client = client_mock
        websocket.client_state = "connected"
        
        return websocket
    
    async def test_authenticate_websocket_authorization_header_success(self, test_env):
        """Test successful WebSocket authentication via Authorization header."""
        service = UnifiedAuthenticationService()
        
        # Create mock WebSocket with Authorization header
        websocket = self.create_mock_websocket({
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature",
            "sec-websocket-protocol": "chat"
        })
        
        # Mock the auth client and token validation
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "ws_user123",
            "email": "ws@example.com",
            "permissions": ["websocket", "chat"]
        })
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            auth_result, user_context = await service.authenticate_websocket(websocket)
        
        # Verify successful authentication
        assert auth_result.success is True
        assert auth_result.user_id == "ws_user123"
        assert auth_result.email == "ws@example.com"
        assert auth_result.permissions == ["websocket", "chat"]
        assert auth_result.metadata["context"] == "websocket"
        assert auth_result.metadata["method"] == "jwt_token"
        
        # Verify UserExecutionContext created
        assert user_context is not None
        assert isinstance(user_context, UserExecutionContext)
        assert user_context.user_id == "ws_user123"
        assert user_context.thread_id.startswith("ws_thread_")
        assert user_context.run_id.startswith("ws_run_")
        assert user_context.request_id.startswith("ws_req_")
        assert user_context.websocket_client_id.startswith("ws_ws_user1")
    
    async def test_authenticate_websocket_subprotocol_success(self, test_env):
        """Test successful WebSocket authentication via Sec-WebSocket-Protocol."""
        service = UnifiedAuthenticationService()
        
        # Create base64url encoded token for subprotocol
        import base64
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"
        encoded_token = base64.urlsafe_b64encode(test_token.encode()).decode().rstrip('=')
        
        websocket = self.create_mock_websocket({
            "sec-websocket-protocol": f"jwt.{encoded_token}, chat"
        })
        
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "subprotocol_user",
            "email": "sub@example.com",
            "permissions": ["read"]
        })
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            auth_result, user_context = await service.authenticate_websocket(websocket)
        
        # Verify successful authentication
        assert auth_result.success is True
        assert auth_result.user_id == "subprotocol_user"
        assert user_context is not None
        assert user_context.user_id == "subprotocol_user"
    
    async def test_authenticate_websocket_query_params_fallback(self, test_env):
        """Test WebSocket authentication via query parameters (fallback)."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket(
            headers={},
            query_params={"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.query.signature"}
        )
        
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "query_user",
            "email": "query@example.com",
            "permissions": []
        })
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            auth_result, user_context = await service.authenticate_websocket(websocket)
        
        # Verify successful authentication
        assert auth_result.success is True
        assert auth_result.user_id == "query_user"
        assert user_context.user_id == "query_user"
    
    async def test_authenticate_websocket_no_token(self, test_env):
        """Test WebSocket authentication when no token found."""
        service = UnifiedAuthenticationService()
        
        # WebSocket with no authentication information
        websocket = self.create_mock_websocket({
            "user-agent": "WebSocket Client",
            "sec-websocket-version": "13"
        })
        
        auth_result, user_context = await service.authenticate_websocket(websocket)
        
        # Verify authentication failure
        assert auth_result.success is False
        assert auth_result.error == "No JWT token found in WebSocket headers or subprotocols"
        assert auth_result.error_code == "NO_TOKEN"
        assert user_context is None
        assert auth_result.metadata["context"] == "websocket"
        assert "no_token_debug" in auth_result.metadata
        
        # Verify debug information
        no_token_debug = auth_result.metadata["no_token_debug"]
        assert no_token_debug["headers_checked"]["authorization"] == "[MISSING]"
        assert "user-agent" in no_token_debug["headers_checked"]["all_header_keys"]
    
    async def test_authenticate_websocket_token_validation_failed(self, test_env):
        """Test WebSocket authentication when token validation fails."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket({
            "authorization": "Bearer invalid.token.signature"
        })
        
        # Mock token validation failure
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": False,
            "error": "Invalid signature"
        })
        
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            auth_result, user_context = await service.authenticate_websocket(websocket)
        
        # Verify authentication failure
        assert auth_result.success is False
        assert auth_result.error.startswith("Invalid signature")
        assert user_context is None
    
    async def test_authenticate_websocket_exception_handling(self, test_env):
        """Test WebSocket authentication exception handling."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket({
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"
        })
        
        # Mock exception during token extraction
        with patch.object(service, '_extract_websocket_token', side_effect=Exception("Network error")):
            auth_result, user_context = await service.authenticate_websocket(websocket)
        
        # Verify error handling
        assert auth_result.success is False
        assert auth_result.error == "WebSocket authentication error: Network error"
        assert auth_result.error_code == "WEBSOCKET_AUTH_ERROR"
        assert user_context is None
        assert "websocket_error_debug" in auth_result.metadata
        
        # Verify error debug information
        error_debug = auth_result.metadata["websocket_error_debug"]
        assert error_debug["error_type"] == "Exception"
        assert error_debug["error_message"] == "Network error"


class TestExtractWebSocketToken(BaseTestCase):
    """Test _extract_websocket_token() method - all token extraction methods."""
    
    def create_mock_websocket(self, headers: Dict[str, str] = None, query_params: Dict[str, str] = None) -> Mock:
        """Create a mock WebSocket object."""
        websocket = Mock()
        websocket.headers = headers or {}
        websocket.query_params = query_params or {}
        return websocket
    
    def test_extract_websocket_token_authorization_header(self, test_env):
        """Test token extraction from Authorization header."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket({
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"
        })
        
        token = service._extract_websocket_token(websocket)
        
        assert token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"
    
    def test_extract_websocket_token_authorization_header_with_spaces(self, test_env):
        """Test token extraction from Authorization header with extra spaces."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket({
            "authorization": "Bearer   eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.spaced.signature   "
        })
        
        token = service._extract_websocket_token(websocket)
        
        assert token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.spaced.signature"
    
    def test_extract_websocket_token_subprotocol(self, test_env):
        """Test token extraction from Sec-WebSocket-Protocol header."""
        service = UnifiedAuthenticationService()
        
        # Create base64url encoded token
        import base64
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.subprotocol.signature"
        encoded_token = base64.urlsafe_b64encode(test_token.encode()).decode().rstrip('=')
        
        websocket = self.create_mock_websocket({
            "sec-websocket-protocol": f"jwt.{encoded_token}, chat, binary"
        })
        
        token = service._extract_websocket_token(websocket)
        
        assert token == test_token
    
    def test_extract_websocket_token_subprotocol_with_padding(self, test_env):
        """Test token extraction from subprotocol that requires base64 padding."""
        service = UnifiedAuthenticationService()
        
        # Create token that will need padding when decoded
        import base64
        test_token = "short.token"
        encoded_token = base64.urlsafe_b64encode(test_token.encode()).decode().rstrip('=')
        
        websocket = self.create_mock_websocket({
            "sec-websocket-protocol": f"jwt.{encoded_token}"
        })
        
        token = service._extract_websocket_token(websocket)
        
        assert token == test_token
    
    def test_extract_websocket_token_query_params(self, test_env):
        """Test token extraction from query parameters."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket(
            headers={},
            query_params={"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.query.signature"}
        )
        
        token = service._extract_websocket_token(websocket)
        
        assert token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.query.signature"
    
    def test_extract_websocket_token_priority_order(self, test_env):
        """Test token extraction priority order (Authorization > Subprotocol > Query)."""
        service = UnifiedAuthenticationService()
        
        # Set up WebSocket with all three methods
        import base64
        subprotocol_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.subprotocol.signature"
        encoded_token = base64.urlsafe_b64encode(subprotocol_token.encode()).decode().rstrip('=')
        
        websocket = self.create_mock_websocket(
            headers={
                "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.auth.signature",
                "sec-websocket-protocol": f"jwt.{encoded_token}"
            },
            query_params={"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.query.signature"}
        )
        
        token = service._extract_websocket_token(websocket)
        
        # Should prioritize Authorization header
        assert token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.auth.signature"
    
    def test_extract_websocket_token_no_bearer_prefix(self, test_env):
        """Test token extraction when Authorization header doesn't have Bearer prefix."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket({
            "authorization": "Basic dXNlcjpwYXNzd29yZA=="
        })
        
        token = service._extract_websocket_token(websocket)
        
        assert token is None
    
    def test_extract_websocket_token_invalid_subprotocol_encoding(self, test_env):
        """Test token extraction when subprotocol base64 decoding fails."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket({
            "sec-websocket-protocol": "jwt.invalid@base64!, chat"
        })
        
        token = service._extract_websocket_token(websocket)
        
        assert token is None
    
    def test_extract_websocket_token_no_token_anywhere(self, test_env):
        """Test token extraction when no token is found anywhere."""
        service = UnifiedAuthenticationService()
        
        websocket = self.create_mock_websocket({
            "user-agent": "WebSocket Client",
            "sec-websocket-version": "13"
        })
        
        token = service._extract_websocket_token(websocket)
        
        assert token is None
    
    def test_extract_websocket_token_exception_handling(self, test_env):
        """Test token extraction exception handling."""
        service = UnifiedAuthenticationService()
        
        # Mock websocket that raises exception when accessing headers
        websocket = Mock()
        websocket.headers = Mock(side_effect=Exception("Header access error"))
        
        token = service._extract_websocket_token(websocket)
        
        assert token is None


class TestServiceTokenValidation(AsyncTestCase):
    """Test validate_service_token() method - service authentication."""
    
    async def test_validate_service_token_success(self, test_env):
        """Test successful service token validation."""
        service = UnifiedAuthenticationService()
        
        # Mock the auth client service validation
        service._auth_client.validate_token_for_service = AsyncMock(return_value={
            "valid": True,
            "service_id": "backend-service",
            "permissions": ["read", "write", "admin"]
        })
        
        result = await service.validate_service_token(
            "service-token-12345",
            "backend-service"
        )
        
        # Verify successful result
        assert result.success is True
        assert result.user_id == "backend-service"  # service_id used as user_id
        assert result.permissions == ["read", "write", "admin"]
        assert result.metadata["context"] == "service_auth"
        assert result.metadata["service_name"] == "backend-service"
        assert result.metadata["service_id"] == "backend-service"
        
        # Verify auth client was called correctly
        service._auth_client.validate_token_for_service.assert_called_once_with(
            "service-token-12345", "backend-service"
        )
    
    async def test_validate_service_token_failed_validation(self, test_env):
        """Test service token validation failure."""
        service = UnifiedAuthenticationService()
        
        service._auth_client.validate_token_for_service = AsyncMock(return_value={
            "valid": False,
            "error": "Service not authorized"
        })
        
        result = await service.validate_service_token(
            "invalid-service-token",
            "unauthorized-service"
        )
        
        # Verify failure result
        assert result.success is False
        assert result.error == "Service not authorized"
        assert result.error_code == "SERVICE_VALIDATION_FAILED"
        assert result.metadata["service_name"] == "unauthorized-service"
    
    async def test_validate_service_token_no_result(self, test_env):
        """Test service token validation when auth client returns None."""
        service = UnifiedAuthenticationService()
        
        service._auth_client.validate_token_for_service = AsyncMock(return_value=None)
        
        result = await service.validate_service_token(
            "missing-token",
            "test-service"
        )
        
        # Verify failure result
        assert result.success is False
        assert result.error == "No validation result"
        assert result.error_code == "SERVICE_VALIDATION_FAILED"
        assert result.metadata["service_name"] == "test-service"
    
    async def test_validate_service_token_exception(self, test_env):
        """Test service token validation exception handling."""
        service = UnifiedAuthenticationService()
        
        service._auth_client.validate_token_for_service = AsyncMock(
            side_effect=Exception("Service validation error")
        )
        
        result = await service.validate_service_token(
            "error-token",
            "error-service"
        )
        
        # Verify error result
        assert result.success is False
        assert result.error == "Service authentication error: Service validation error"
        assert result.error_code == "SERVICE_AUTH_ERROR"
        assert result.metadata["service_name"] == "error-service"


class TestAuthenticationStats(BaseTestCase):
    """Test get_authentication_stats() method - statistics tracking."""
    
    async def test_get_authentication_stats_initial(self, test_env):
        """Test authentication statistics with initial state."""
        service = UnifiedAuthenticationService()
        
        stats = service.get_authentication_stats()
        
        # Verify SSOT enforcement information
        assert stats["ssot_enforcement"]["service"] == "UnifiedAuthenticationService"
        assert stats["ssot_enforcement"]["ssot_compliant"] is True
        assert stats["ssot_enforcement"]["duplicate_paths_eliminated"] == 4
        
        # Verify initial statistics
        assert stats["statistics"]["total_attempts"] == 0
        assert stats["statistics"]["successful_authentications"] == 0
        assert stats["statistics"]["failed_authentications"] == 0
        assert stats["statistics"]["success_rate_percent"] == 0.0
        
        # Verify all method and context counts are initialized
        assert len(stats["method_distribution"]) == len(AuthenticationMethod)
        assert len(stats["context_distribution"]) == len(AuthenticationContext)
        
        for method in AuthenticationMethod:
            assert stats["method_distribution"][method.value] == 0
        
        for context in AuthenticationContext:
            assert stats["context_distribution"][context.value] == 0
        
        # Verify timestamp is included
        assert "timestamp" in stats
        timestamp = datetime.fromisoformat(stats["timestamp"].replace('Z', '+00:00'))
        assert timestamp.tzinfo == timezone.utc
    
    async def test_get_authentication_stats_after_operations(self, test_env):
        """Test authentication statistics after performing operations."""
        service = UnifiedAuthenticationService()
        
        # Mock auth client
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "user1",
            "email": "user1@test.com"
        })
        
        # Perform some authentication operations
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=True):
            # Successful JWT authentication
            await service.authenticate_token(
                "valid-jwt-token",
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )
            
            # Successful API key authentication
            await service.authenticate_token(
                "valid-api-key",
                context=AuthenticationContext.WEBSOCKET,
                method=AuthenticationMethod.API_KEY
            )
        
        # Failed authentication (invalid format)
        with patch('netra_backend.app.services.unified_authentication_service.validate_jwt_format', return_value=False):
            await service.authenticate_token(
                "invalid-token",
                context=AuthenticationContext.GRAPHQL,
                method=AuthenticationMethod.JWT_TOKEN
            )
        
        stats = service.get_authentication_stats()
        
        # Verify updated statistics
        assert stats["statistics"]["total_attempts"] == 3
        assert stats["statistics"]["successful_authentications"] == 2
        assert stats["statistics"]["failed_authentications"] == 1
        assert stats["statistics"]["success_rate_percent"] == 66.67
        
        # Verify method distribution
        assert stats["method_distribution"]["jwt_token"] == 2
        assert stats["method_distribution"]["api_key"] == 1
        assert stats["method_distribution"]["basic_auth"] == 0
        assert stats["method_distribution"]["service_account"] == 0
        
        # Verify context distribution
        assert stats["context_distribution"]["rest_api"] == 1
        assert stats["context_distribution"]["websocket"] == 1
        assert stats["context_distribution"]["graphql"] == 1
        assert stats["context_distribution"]["grpc"] == 0
        assert stats["context_distribution"]["internal_service"] == 0


class TestHealthCheck(AsyncTestCase):
    """Test health_check() method - health monitoring."""
    
    async def test_health_check_healthy(self, test_env):
        """Test health check when service is healthy."""
        service = UnifiedAuthenticationService()
        
        # Mock auth client with circuit_breaker attribute
        service._auth_client.circuit_breaker = Mock()
        
        health = await service.health_check()
        
        # Verify healthy status
        assert health["status"] == "healthy"
        assert health["service"] == "UnifiedAuthenticationService"
        assert health["ssot_compliant"] is True
        assert health["auth_client_status"] == "available"
        assert "timestamp" in health
        
        # Verify timestamp format
        timestamp = datetime.fromisoformat(health["timestamp"].replace('Z', '+00:00'))
        assert timestamp.tzinfo == timezone.utc
    
    async def test_health_check_degraded(self, test_env):
        """Test health check when auth client is not available."""
        service = UnifiedAuthenticationService()
        
        # Mock auth client without circuit_breaker attribute
        service._auth_client = Mock()
        delattr(service._auth_client, 'circuit_breaker')
        
        health = await service.health_check()
        
        # Verify degraded status
        assert health["status"] == "degraded"
        assert health["service"] == "UnifiedAuthenticationService"
        assert health["ssot_compliant"] is True
        assert health["auth_client_status"] == "unavailable"
    
    async def test_health_check_exception(self, test_env):
        """Test health check exception handling."""
        service = UnifiedAuthenticationService()
        
        # Mock auth client to raise exception
        service._auth_client = Mock()
        # Make hasattr check raise exception
        with patch('builtins.hasattr', side_effect=Exception("Health check error")):
            health = await service.health_check()
        
        # Verify unhealthy status
        assert health["status"] == "unhealthy"
        assert health["service"] == "UnifiedAuthenticationService"
        assert health["error"] == "Health check error"
        assert "timestamp" in health


class TestUnifiedAuthServiceSingleton(BaseTestCase):
    """Test get_unified_auth_service() singleton behavior."""
    
    def test_get_unified_auth_service_singleton(self, test_env):
        """Test that get_unified_auth_service() returns singleton instance."""
        # Clear any existing instance
        import netra_backend.app.services.unified_authentication_service as auth_module
        auth_module._unified_auth_service = None
        
        # Get first instance
        service1 = get_unified_auth_service()
        
        # Get second instance
        service2 = get_unified_auth_service()
        
        # Verify they are the same instance
        assert service1 is service2
        assert isinstance(service1, UnifiedAuthenticationService)
        assert isinstance(service2, UnifiedAuthenticationService)
    
    def test_get_unified_auth_service_instance_creation(self, test_env):
        """Test that get_unified_auth_service() properly creates instance."""
        # Clear any existing instance
        import netra_backend.app.services.unified_authentication_service as auth_module
        auth_module._unified_auth_service = None
        
        # Verify instance is None initially
        assert auth_module._unified_auth_service is None
        
        # Get instance
        service = get_unified_auth_service()
        
        # Verify instance was created and stored
        assert auth_module._unified_auth_service is service
        assert isinstance(service, UnifiedAuthenticationService)
        
        # Verify instance has proper initialization
        assert hasattr(service, '_auth_client')
        assert hasattr(service, '_auth_attempts')
        assert hasattr(service, '_auth_successes')
        assert hasattr(service, '_auth_failures')
        assert hasattr(service, '_method_counts')
        assert hasattr(service, '_context_counts')


class TestEnhancedResilienceAndRetryLogic(AsyncTestCase):
    """Test enhanced resilience and retry logic with circuit breaker scenarios."""
    
    async def test_validate_token_with_enhanced_resilience_success_first_try(self, test_env):
        """Test enhanced resilience when validation succeeds on first try."""
        service = UnifiedAuthenticationService()
        
        # Mock successful validation
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "resilient_user",
            "email": "resilient@test.com"
        })
        
        # Mock circuit breaker status
        service._check_circuit_breaker_status = AsyncMock(return_value={
            "open": False,
            "state": "closed",
            "failure_count": 0,
            "reason": "Circuit breaker is closed"
        })
        
        result = await service._validate_token_with_enhanced_resilience(
            "test-token",
            AuthenticationContext.REST_API,
            AuthenticationMethod.JWT_TOKEN
        )
        
        # Verify successful result
        assert result is not None
        assert result["valid"] is True
        assert result["user_id"] == "resilient_user"
        assert "resilience_metadata" in result
        assert result["resilience_metadata"]["attempts_made"] == 1
        assert result["resilience_metadata"]["environment"] == "test"
    
    async def test_validate_token_with_enhanced_resilience_retry_success(self, test_env):
        """Test enhanced resilience with retry that eventually succeeds."""
        service = UnifiedAuthenticationService()
        
        # Mock circuit breaker status
        service._check_circuit_breaker_status = AsyncMock(return_value={
            "open": False,
            "state": "closed",
            "failure_count": 0,
            "reason": "Circuit breaker is closed"
        })
        
        # Mock validation that fails first, then succeeds
        call_count = 0
        async def mock_validate_token(token):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AuthServiceConnectionError("Temporary connection error")
            return {
                "valid": True,
                "user_id": "retry_user",
                "email": "retry@test.com"
            }
        
        service._auth_client.validate_token = mock_validate_token
        
        # Mock error classification to allow retry
        service._classify_auth_error = Mock(return_value={
            "category": "network",
            "retryable": True,
            "reason": "Network connectivity issue - likely transient"
        })
        
        result = await service._validate_token_with_enhanced_resilience(
            "retry-token",
            AuthenticationContext.WEBSOCKET,
            AuthenticationMethod.JWT_TOKEN,
            max_retries=2
        )
        
        # Verify successful result after retry
        assert result is not None
        assert result["valid"] is True
        assert result["user_id"] == "retry_user"
        assert result["resilience_metadata"]["attempts_made"] == 2
        assert len(result["resilience_metadata"]["attempt_details"]) == 2
        assert result["resilience_metadata"]["attempt_details"][0]["success"] is False
        assert result["resilience_metadata"]["attempt_details"][1]["success"] is True
    
    async def test_validate_token_with_enhanced_resilience_all_attempts_fail(self, test_env):
        """Test enhanced resilience when all retry attempts fail."""
        service = UnifiedAuthenticationService()
        
        # Mock circuit breaker status
        service._check_circuit_breaker_status = AsyncMock(return_value={
            "open": False,
            "state": "closed",
            "failure_count": 0,
            "reason": "Circuit breaker is closed"
        })
        
        # Mock validation that always fails
        service._auth_client.validate_token = AsyncMock(
            side_effect=AuthServiceConnectionError("Persistent connection error")
        )
        
        # Mock error classification to allow retry
        service._classify_auth_error = Mock(return_value={
            "category": "network",
            "retryable": True,
            "reason": "Network connectivity issue - likely transient"
        })
        
        result = await service._validate_token_with_enhanced_resilience(
            "fail-token",
            AuthenticationContext.GRPC,
            AuthenticationMethod.API_KEY,
            max_retries=2
        )
        
        # Verify failure result with retry metadata
        assert result is not None
        assert result["valid"] is False
        assert result["error"] == "All validation attempts failed"
        assert "details" in result
        assert result["resilience_metadata"]["attempts_made"] == 3  # max_retries + 1
        assert result["resilience_metadata"]["final_failure"] is True
    
    async def test_validate_token_with_enhanced_resilience_non_retryable_error(self, test_env):
        """Test enhanced resilience with non-retryable error."""
        service = UnifiedAuthenticationService()
        
        # Mock circuit breaker status
        service._check_circuit_breaker_status = AsyncMock(return_value={
            "open": False,
            "state": "closed",
            "failure_count": 0,
            "reason": "Circuit breaker is closed"
        })
        
        # Mock validation that fails with non-retryable error
        service._auth_client.validate_token = AsyncMock(
            side_effect=AuthServiceValidationError("Invalid token format")
        )
        
        # Mock error classification to NOT allow retry
        service._classify_auth_error = Mock(return_value={
            "category": "invalid_token",
            "retryable": False,
            "reason": "Token is invalid - retry won't help"
        })
        
        result = await service._validate_token_with_enhanced_resilience(
            "invalid-token",
            AuthenticationContext.INTERNAL_SERVICE,
            AuthenticationMethod.SERVICE_ACCOUNT,
            max_retries=3
        )
        
        # Verify failure result with only one attempt
        assert result is not None
        assert result["valid"] is False
        assert result["resilience_metadata"]["attempts_made"] == 1
        assert result["resilience_metadata"]["final_failure"] is True
    
    async def test_validate_token_with_enhanced_resilience_circuit_breaker_open(self, test_env):
        """Test enhanced resilience when circuit breaker is open."""
        service = UnifiedAuthenticationService()
        
        # Mock circuit breaker as open
        service._check_circuit_breaker_status = AsyncMock(return_value={
            "open": True,
            "state": "open",
            "failure_count": 5,
            "reason": "Too many failures - circuit breaker open"
        })
        
        # Mock successful validation (should still attempt despite circuit breaker)
        service._auth_client.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "breaker_user",
            "email": "breaker@test.com"
        })
        
        result = await service._validate_token_with_enhanced_resilience(
            "breaker-token",
            AuthenticationContext.REST_API,
            AuthenticationMethod.JWT_TOKEN
        )
        
        # Verify result includes circuit breaker status
        assert result is not None
        assert result["valid"] is True
        assert "resilience_metadata" in result
        assert result["resilience_metadata"]["circuit_breaker_status"]["open"] is True
        assert result["resilience_metadata"]["circuit_breaker_status"]["state"] == "open"
    
    def test_classify_auth_error_network_errors(self, test_env):
        """Test auth error classification for network errors."""
        service = UnifiedAuthenticationService()
        
        # Test connection error
        conn_error = AuthServiceConnectionError("Connection refused")
        classification = service._classify_auth_error(conn_error)
        assert classification["category"] == "network"
        assert classification["retryable"] is True
        
        # Test timeout error
        timeout_error = Exception("Request timeout occurred")
        classification = service._classify_auth_error(timeout_error)
        assert classification["category"] == "network"
        assert classification["retryable"] is True
    
    def test_classify_auth_error_server_errors(self, test_env):
        """Test auth error classification for server errors."""
        service = UnifiedAuthenticationService()
        
        # Test 500 error
        server_error = Exception("HTTP 500 Internal Server Error")
        classification = service._classify_auth_error(server_error)
        assert classification["category"] == "server_error"
        assert classification["retryable"] is True
        
        # Test 503 error
        unavailable_error = Exception("HTTP 503 Service Unavailable")
        classification = service._classify_auth_error(unavailable_error)
        assert classification["category"] == "server_error"
        assert classification["retryable"] is True
    
    def test_classify_auth_error_client_errors(self, test_env):
        """Test auth error classification for client errors."""
        service = UnifiedAuthenticationService()
        
        # Test 401 error
        auth_error = Exception("HTTP 401 Unauthorized")
        classification = service._classify_auth_error(auth_error)
        assert classification["category"] == "client_error"
        assert classification["retryable"] is False
        
        # Test 400 error  
        bad_request = Exception("HTTP 400 Bad Request")
        classification = service._classify_auth_error(bad_request)
        assert classification["category"] == "client_error"
        assert classification["retryable"] is False
    
    def test_classify_auth_error_invalid_token(self, test_env):
        """Test auth error classification for invalid token errors."""
        service = UnifiedAuthenticationService()
        
        # Test invalid token error
        invalid_token = AuthServiceValidationError("Invalid token signature")
        classification = service._classify_auth_error(invalid_token)
        assert classification["category"] == "invalid_token"
        assert classification["retryable"] is False
    
    def test_classify_auth_error_circuit_breaker(self, test_env):
        """Test auth error classification for circuit breaker errors."""
        service = UnifiedAuthenticationService()
        
        # Test circuit breaker error
        breaker_error = CircuitBreakerError("Circuit breaker is open")
        classification = service._classify_auth_error(breaker_error)
        assert classification["category"] == "circuit_breaker"
        assert classification["retryable"] is True
    
    def test_classify_auth_error_unknown(self, test_env):
        """Test auth error classification for unknown errors."""
        service = UnifiedAuthenticationService()
        
        # Test unknown error
        unknown_error = RuntimeError("Unknown runtime error")
        classification = service._classify_auth_error(unknown_error)
        assert classification["category"] == "unknown"
        assert classification["retryable"] is True
        assert "RuntimeError" in classification["reason"]
    
    async def test_check_circuit_breaker_status_available(self, test_env):
        """Test circuit breaker status check when available."""
        service = UnifiedAuthenticationService()
        
        # Mock circuit breaker components
        mock_breaker = Mock()
        mock_breaker.get_status.return_value = {
            "state": "closed",
            "failure_count": 2
        }
        
        mock_circuit_manager = Mock()
        mock_circuit_manager.breaker = mock_breaker
        
        service._auth_client.circuit_manager = mock_circuit_manager
        
        status = await service._check_circuit_breaker_status()
        
        assert status["open"] is False
        assert status["state"] == "closed"
        assert status["failure_count"] == 2
        assert status["reason"] == "Circuit breaker state: closed"
    
    async def test_check_circuit_breaker_status_unavailable(self, test_env):
        """Test circuit breaker status check when unavailable."""
        service = UnifiedAuthenticationService()
        
        # Mock auth client without circuit breaker components
        service._auth_client = Mock()
        # Remove the circuit_manager attribute if it exists
        if hasattr(service._auth_client, 'circuit_manager'):
            delattr(service._auth_client, 'circuit_manager')
        
        status = await service._check_circuit_breaker_status()
        
        assert status["open"] is False
        assert status["state"] == "unknown"
        assert status["failure_count"] == 0
        assert status["reason"] == "Circuit breaker status unavailable"
    
    async def test_check_circuit_breaker_status_exception(self, test_env):
        """Test circuit breaker status check exception handling."""
        service = UnifiedAuthenticationService()
        
        # Mock hasattr to raise exception
        with patch('builtins.hasattr', side_effect=Exception("Breaker status error")):
            status = await service._check_circuit_breaker_status()
        
        assert status["open"] is False
        assert status["state"] == "error"
        assert status["failure_count"] == 0
        assert "Error checking circuit breaker" in status["reason"]


# Additional integration point tests for UserExecutionContext creation
class TestUserExecutionContextCreation(BaseTestCase):
    """Test _create_user_execution_context method."""
    
    def test_create_user_execution_context_success(self, test_env):
        """Test successful UserExecutionContext creation."""
        service = UnifiedAuthenticationService()
        
        # Create auth result
        auth_result = AuthResult(
            success=True,
            user_id="context_user_12345",
            email="context@test.com",
            permissions=["read", "write"]
        )
        
        # Mock WebSocket
        websocket = Mock()
        websocket.client = Mock()
        websocket.client.host = "192.168.1.100"
        websocket.client.port = 54321
        
        # Create context
        context = service._create_user_execution_context(auth_result, websocket)
        
        # Verify UserExecutionContext created properly
        assert isinstance(context, UserExecutionContext)
        assert context.user_id == "context_user_12345"
        assert context.thread_id.startswith("ws_thread_")
        assert context.run_id.startswith("ws_run_")
        assert context.request_id.startswith("ws_req_")
        assert context.websocket_client_id.startswith("ws_context_")
        
        # Verify IDs are properly formatted
        assert len(context.thread_id.split("_")) == 3  # ws_thread_<uuid_prefix>
        assert len(context.run_id.split("_")) == 3     # ws_run_<uuid_prefix>
        assert len(context.request_id.split("_")) >= 3  # ws_req_<timestamp>_<uuid_prefix>
        assert len(context.websocket_client_id.split("_")) >= 3  # ws_<user_prefix>_<timestamp>_<uuid_prefix>


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])