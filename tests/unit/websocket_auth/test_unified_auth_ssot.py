"""
Unit Tests: Unified WebSocket Authentication SSOT
ISSUE #1176 REMEDIATION: Validate the new single source of truth authentication pathway

Business Impact: $500K+ ARR - Ensures Golden Path authentication reliability
Technical Impact: Validates 4 authentication methods and comprehensive error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket
from netra_backend.app.websocket_core.unified_auth_ssot import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    authenticate_websocket
)


class TestUnifiedWebSocketAuthenticator:
    """Test the unified WebSocket authenticator implementation"""
    
    @pytest.fixture
    def auth_instance(self):
        """Create a test authenticator instance"""
        return UnifiedWebSocketAuthenticator()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket with test headers"""
        websocket = Mock(spec=WebSocket)
        websocket.headers = {}
        websocket.query_string = b""
        return websocket
    
    def test_extract_jwt_from_subprotocol_jwt_auth_format(self, auth_instance, mock_websocket):
        """Test JWT extraction from jwt-auth.TOKEN subprotocol format"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        mock_websocket.headers = {"sec-websocket-protocol": f"jwt-auth.{test_token}"}
        
        result = auth_instance._extract_jwt_from_subprotocol(mock_websocket)
        
        assert result == test_token
    
    def test_extract_jwt_from_subprotocol_jwt_format(self, auth_instance, mock_websocket):
        """Test JWT extraction from jwt.TOKEN subprotocol format (legacy)"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        mock_websocket.headers = {"sec-websocket-protocol": f"jwt.{test_token}"}
        
        result = auth_instance._extract_jwt_from_subprotocol(mock_websocket)
        
        assert result == test_token
    
    def test_extract_jwt_from_subprotocol_bearer_format(self, auth_instance, mock_websocket):
        """Test JWT extraction from bearer.TOKEN subprotocol format"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        mock_websocket.headers = {"sec-websocket-protocol": f"bearer.{test_token}"}
        
        result = auth_instance._extract_jwt_from_subprotocol(mock_websocket)
        
        assert result == test_token
    
    def test_extract_jwt_from_subprotocol_no_match(self, auth_instance, mock_websocket):
        """Test JWT extraction returns None when no matching subprotocol"""
        mock_websocket.headers = {"sec-websocket-protocol": "websocket"}
        
        result = auth_instance._extract_jwt_from_subprotocol(mock_websocket)
        
        assert result is None
    
    def test_extract_jwt_from_auth_header_success(self, auth_instance, mock_websocket):
        """Test JWT extraction from Authorization header"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        mock_websocket.headers = {"authorization": f"Bearer {test_token}"}
        
        result = auth_instance._extract_jwt_from_auth_header(mock_websocket)
        
        assert result == test_token
    
    def test_extract_jwt_from_auth_header_no_bearer(self, auth_instance, mock_websocket):
        """Test JWT extraction returns None when Authorization header has no Bearer prefix"""
        mock_websocket.headers = {"authorization": "Basic dGVzdDp0ZXN0"}
        
        result = auth_instance._extract_jwt_from_auth_header(mock_websocket)
        
        assert result is None
    
    def test_extract_jwt_from_query_params_token(self, auth_instance, mock_websocket):
        """Test JWT extraction from query parameter 'token'"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        mock_websocket.query_string = f"token={test_token}".encode()
        
        result = auth_instance._extract_jwt_from_query_params(mock_websocket)
        
        assert result == test_token
    
    def test_extract_jwt_from_query_params_jwt(self, auth_instance, mock_websocket):
        """Test JWT extraction from query parameter 'jwt'"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        mock_websocket.query_string = f"jwt={test_token}".encode()
        
        result = auth_instance._extract_jwt_from_query_params(mock_websocket)
        
        assert result == test_token
    
    def test_extract_jwt_from_query_params_no_match(self, auth_instance, mock_websocket):
        """Test JWT extraction returns None when no matching query parameters"""
        mock_websocket.query_string = b"foo=bar&baz=qux"
        
        result = auth_instance._extract_jwt_from_query_params(mock_websocket)
        
        assert result is None
    
    def test_is_e2e_test_environment_development(self, auth_instance):
        """Test E2E environment detection in development mode"""
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.return_value = 'development'
            mock_get_env.return_value = mock_env
            
            result = auth_instance._is_e2e_test_environment()
            
            assert result is True
    
    def test_is_e2e_test_environment_production(self, auth_instance):
        """Test E2E environment detection in production mode"""
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.return_value = 'production'
            mock_get_env.return_value = mock_env
            
            result = auth_instance._is_e2e_test_environment()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_e2e_bypass_success(self, auth_instance, mock_websocket):
        """Test successful E2E authentication bypass"""
        test_user_id = "test-user-123"
        mock_websocket.headers = {
            "x-e2e-user-id": test_user_id,
            "x-e2e-bypass": "true"
        }
        
        result = await auth_instance._handle_e2e_bypass(mock_websocket)
        
        assert result.success is True
        assert result.user_id == test_user_id
        assert result.email == f"{test_user_id}@e2e.test"
        assert "websocket" in result.permissions
        assert result.auth_method == "e2e-bypass"
    
    @pytest.mark.asyncio
    async def test_handle_e2e_bypass_missing_headers(self, auth_instance, mock_websocket):
        """Test E2E bypass failure when headers are missing"""
        mock_websocket.headers = {}
        
        result = await auth_instance._handle_e2e_bypass(mock_websocket)
        
        assert result.success is False
        assert result.auth_method == "e2e-bypass"
    
    @pytest.mark.asyncio
    async def test_fallback_jwt_validation_success(self, auth_instance):
        """Test fallback JWT validation when auth service is unavailable"""
        # Create a valid test JWT
        import jwt
        from shared.jwt_secret_manager import get_unified_jwt_secret
        
        test_payload = {
            'sub': 'test-user-123',
            'email': 'test@example.com',
            'permissions': ['read', 'write']
        }
        
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_secret:
            mock_secret.return_value = "test-secret"
            test_token = jwt.encode(test_payload, "test-secret", algorithm='HS256')
            
            result = await auth_instance._fallback_jwt_validation(test_token, "test-method")
            
            assert result.success is True
            assert result.user_id == "test-user-123"
            assert result.email == "test@example.com"
            assert result.permissions == ['read', 'write']
            assert result.auth_method == "test-method-fallback"
    
    @pytest.mark.asyncio
    async def test_fallback_jwt_validation_invalid_token(self, auth_instance):
        """Test fallback JWT validation with invalid token"""
        invalid_token = "invalid.jwt.token"
        
        result = await auth_instance._fallback_jwt_validation(invalid_token, "test-method")
        
        assert result.success is False
        assert "JWT validation failed" in result.error_message
        assert result.auth_method == "test-method"
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_connection_priority_order(self, auth_instance, mock_websocket):
        """Test that authentication methods are tried in correct priority order"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        
        # Set up mock websocket with multiple auth sources
        mock_websocket.headers = {
            "sec-websocket-protocol": f"jwt-auth.{test_token}",  # Should be tried first
            "authorization": f"Bearer {test_token}",             # Should be fallback
        }
        mock_websocket.query_string = f"token={test_token}".encode()  # Should be last fallback
        
        with patch.object(auth_instance, '_validate_jwt_token') as mock_validate:
            # Make first attempt succeed
            mock_validate.return_value = WebSocketAuthResult(
                success=True,
                user_id="test-user",
                auth_method="jwt-auth-subprotocol"
            )
            
            result = await auth_instance.authenticate_websocket_connection(mock_websocket)
            
            # Should only call validation once (for first method that found a token)
            assert mock_validate.call_count == 1
            # Should call with subprotocol method first
            mock_validate.assert_called_with(test_token, "jwt-auth-subprotocol")
            assert result.auth_method == "jwt-auth-subprotocol"


class TestSSotFunctionInterface:
    """Test the SSOT function interface"""
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_function(self):
        """Test the main SSOT function interface"""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"x-e2e-bypass": "true", "x-e2e-user-id": "test-user"}
        mock_websocket.query_string = b""
        
        with patch('netra_backend.app.websocket_core.unified_auth_ssot.websocket_authenticator') as mock_auth:
            mock_result = WebSocketAuthResult(success=True, user_id="test-user")
            # Make the mock return an awaitable
            mock_auth.authenticate_websocket_connection = AsyncMock(return_value=mock_result)
            
            result = await authenticate_websocket(mock_websocket)
            
            assert result == mock_result
            mock_auth.authenticate_websocket_connection.assert_called_once_with(mock_websocket)


class TestErrorHandling:
    """Test comprehensive error handling scenarios"""
    
    @pytest.fixture
    def auth_instance(self):
        return UnifiedWebSocketAuthenticator()
    
    @pytest.mark.asyncio
    async def test_authentication_all_methods_fail(self, auth_instance):
        """Test when all authentication methods fail"""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {}
        mock_websocket.query_string = b""
        
        with patch.object(auth_instance, '_is_e2e_test_environment', return_value=False):
            result = await auth_instance.authenticate_websocket_connection(mock_websocket)
            
            assert result.success is False
            assert "Authentication failed" in result.error_message
            assert result.auth_method == "none"
    
    @pytest.mark.asyncio
    async def test_jwt_validation_exception_handling(self, auth_instance):
        """Test JWT validation exception handling"""
        test_token = "malformed.jwt.token"
        
        # Force fallback by setting internal auth service to None
        auth_instance._auth_service = None
        
        with patch('jwt.decode', side_effect=Exception("JWT decode error")):
            result = await auth_instance._fallback_jwt_validation(test_token, "test-method")
            
            assert result.success is False
            assert "JWT decode error" in result.error_message


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world authentication scenarios"""
    
    @pytest.mark.asyncio
    async def test_gcp_load_balancer_header_stripping(self):
        """Test GCP load balancer scenario where Authorization header is stripped"""
        auth_instance = UnifiedWebSocketAuthenticator()
        
        # Simulate GCP environment where Authorization header is stripped
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {}  # No Authorization header
        mock_websocket.query_string = b"token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"
        
        with patch.object(auth_instance, '_validate_jwt_token') as mock_validate:
            mock_validate.return_value = WebSocketAuthResult(
                success=True,
                user_id="test-user",
                auth_method="query-param-fallback"
            )
            
            result = await auth_instance.authenticate_websocket_connection(mock_websocket)
            
            assert result.success is True
            assert result.auth_method == "query-param-fallback"
    
    @pytest.mark.asyncio 
    async def test_frontend_jwt_auth_subprotocol(self):
        """Test frontend using jwt-auth subprotocol format"""
        auth_instance = UnifiedWebSocketAuthenticator()
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {"sec-websocket-protocol": "jwt-auth.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"}
        mock_websocket.query_string = b""
        
        with patch.object(auth_instance, '_validate_jwt_token') as mock_validate:
            mock_validate.return_value = WebSocketAuthResult(
                success=True,
                user_id="frontend-user",
                auth_method="jwt-auth-subprotocol"
            )
            
            result = await auth_instance.authenticate_websocket_connection(mock_websocket)
            
            assert result.success is True
            assert result.auth_method == "jwt-auth-subprotocol"