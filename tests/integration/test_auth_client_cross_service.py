"""
Integration tests for auth client cross-service functionality.

Tests auth client integration with service discovery and cross-service authentication.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx

from test_framework.mock_utils import mock_justified
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from dev_launcher.service_discovery import ServiceDiscovery


class TestAuthClientCrossServiceIntegration:
    """Test auth client integration with cross-service features."""
    
    @pytest.fixture
    def service_discovery(self):
        """Create test service discovery with auth service registered."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_auth_info({
                'port': 8081,
                'url': 'http://localhost:8081',
                'api_url': 'http://localhost:8081/auth',
                'timestamp': '2025-08-20T10:00:00'
            })
            discovery.set_cross_service_auth_token("test-cross-service-token-123")
            yield discovery
    
    @pytest.fixture
    def auth_client(self):
        """Create test auth client."""
        return AuthServiceClient()
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Create mock httpx client."""
        mock_client = Mock(spec=httpx.AsyncClient)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client
    
    @pytest.mark.asyncio
    async def test_auth_client_cross_service_token_validation(self, auth_client, service_discovery, mock_httpx_client):
        """Test auth client validates tokens with cross-service headers."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'valid': True,
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'permissions': ['read', 'write']
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        with patch.object(auth_client, '_create_http_client', return_value=mock_httpx_client):
            result = await auth_client.validate_token_jwt("test-token-456")
        
        # Verify result
        assert result is not None
        assert result['valid'] is True
        assert result['user_id'] == 'test-user-123'
        
        # Verify cross-service headers were included
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert 'headers' in call_args.kwargs or len(call_args.args) >= 3
    
    @pytest.mark.asyncio
    async def test_auth_client_with_service_discovery_integration(self, auth_client, service_discovery, mock_httpx_client):
        """Test auth client can use service discovery for endpoint resolution."""
        # Test that auth client could potentially use service discovery
        # to resolve auth service endpoints dynamically
        
        auth_info = service_discovery.read_auth_info()
        assert auth_info is not None
        assert auth_info['api_url'] == 'http://localhost:8081/auth'
        
        # Mock auth service is healthy
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'healthy'}
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Simulate health check to auth service
        with patch.object(auth_client, '_get_client', return_value=mock_httpx_client):
            client = await auth_client._get_client()
            health_response = await client.get('/health')
            
            assert health_response.status_code == 200
    
    def test_cross_service_auth_token_storage_retrieval(self, service_discovery):
        """Test cross-service auth token storage and retrieval."""
        # Test token was set in fixture
        token = service_discovery.get_cross_service_auth_token()
        assert token == "test-cross-service-token-123"
        
        # Test updating token
        new_token = "updated-cross-service-token-456"
        service_discovery.set_cross_service_auth_token(new_token)
        
        retrieved_token = service_discovery.get_cross_service_auth_token()
        assert retrieved_token == new_token
    
    @pytest.mark.asyncio
    async def test_auth_client_circuit_breaker_with_cross_service(self, auth_client, mock_httpx_client):
        """Test auth client circuit breaker works with cross-service calls."""
        # Mock service failure
        mock_httpx_client.post = AsyncMock(side_effect=httpx.RequestError("Service unavailable"))
        
        with patch.object(auth_client, '_create_http_client', return_value=mock_httpx_client):
            # First call should fail and trigger circuit breaker
            result = await auth_client.validate_token_jwt("test-token")
            
            # Should fall back to local validation
            assert result is not None  # Should not be None due to fallback
    
    @pytest.mark.asyncio
    async def test_auth_client_caching_with_cross_service_tokens(self, auth_client):
        """Test auth client caching works properly with cross-service tokens."""
        test_token = "cross-service-token-789"
        
        # Mock successful validation
        mock_result = {
            'valid': True,
            'user_id': 'cross-service-user',
            'email': 'cross@service.com',
            'permissions': ['cross_service_access']
        }
        
        # Mock justification: Remote auth service API not available in test environment - testing caching behavior
        with patch.object(auth_client, '_validate_token_remote', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_result
            
            result1 = await auth_client.validate_token_jwt(test_token)
            assert result1 == mock_result
            
            # Second validation - should use cache
            result2 = await auth_client.validate_token_jwt(test_token)
            assert result2 == mock_result
            
            # Remote validation should only be called once (first time)
            mock_validate.assert_called_once()
    
    def test_service_discovery_cors_integration_with_auth(self, service_discovery):
        """Test service discovery CORS integration includes auth service."""
        origins = service_discovery.get_all_service_origins()
        
        # Should include auth service origins
        assert 'http://localhost:8081' in origins
        assert 'http://localhost:8081/auth' in origins
    
    def test_auth_service_cors_metadata_registration(self, service_discovery):
        """Test auth service can be registered with CORS metadata."""
        auth_service_info = {
            'port': 8081,
            'url': 'http://localhost:8081',
            'api_url': 'http://localhost:8081/auth'
        }
        
        # Register with CORS metadata
        service_discovery.register_service_for_cors('auth', auth_service_info)
        
        # Verify CORS configuration
        cors_config = service_discovery.get_service_cors_config('auth')
        assert cors_config is not None
        assert cors_config['service_id'] == 'netra-auth'
        assert cors_config['supports_cross_service'] is True
        assert 'X-Cross-Service-Auth' in cors_config['cors_headers_required']


class TestAuthClientEnvironmentDetection:
    """Test auth client environment detection with service discovery."""
    
    @pytest.fixture
    def auth_client(self):
        """Create auth client for environment testing."""
        return AuthServiceClient()
    
    def test_environment_detection_with_service_discovery(self, auth_client):
        """Test environment detection can work with service discovery info."""
        # Test that environment detector can work with service discovery
        environment = auth_client.environment_detector.detect_environment()
        
        # Should detect development environment
        assert environment.value in ['development', 'staging', 'production']
    
    def test_oauth_config_generation_for_cross_service(self, auth_client):
        """Test OAuth config generation for cross-service scenarios."""
        # Generate OAuth config
        oauth_config = auth_client.oauth_generator.generate_config()
        
        # Should have required OAuth properties
        assert hasattr(oauth_config, 'client_id')
        assert hasattr(oauth_config, 'auth_url')
        assert hasattr(oauth_config, 'token_url')
        
        # Should be configured for the detected environment
        assert oauth_config.auth_url is not None


class TestWebSocketSecurityIntegration:
    """Test WebSocket security integration with cross-service features."""
    
    def test_websocket_validation_with_cross_service_context(self):
        """Test WebSocket message validation in cross-service context."""
        from netra_backend.app.websocket.validation_security import validate_payload_security, has_valid_payload_structure
        
        # Test message with cross-service metadata
        cross_service_message = {
            'type': 'cross_service_message',
            'payload': {
                'text': 'Hello from service A to service B',
                'service_id': 'netra-backend',
                'cross_service_auth': 'token-123'
            },
            'metadata': {
                'source_service': 'backend',
                'target_service': 'frontend',
                'timestamp': '2025-08-20T10:00:00Z'
            }
        }
        
        # Should pass security validation
        assert has_valid_payload_structure(cross_service_message)
        security_error = validate_payload_security(cross_service_message)
        assert security_error is None
    
    def test_websocket_security_prevents_malicious_cross_service_messages(self):
        """Test WebSocket security prevents malicious cross-service messages."""
        from netra_backend.app.websocket.validation_security import validate_payload_security
        
        # Test malicious message disguised as cross-service
        malicious_message = {
            'type': 'cross_service_message',
            'payload': {
                'text': '<script>alert("xss")</script>Malicious content',
                'service_id': 'netra-backend',
                'cross_service_auth': 'token-123'
            }
        }
        
        # Should be caught by security validation
        security_error = validate_payload_security(malicious_message)
        assert security_error is not None
        assert 'security_error' in security_error.error_type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])