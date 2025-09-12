"""
Integration Tests for Issue #463: WebSocket Authentication Service Integration Failures

This test suite reproduces service-to-service authentication failures and WebSocket 
middleware problems identified in Issue #463:
- Service-to-service authentication breakdowns
- WebSocket middleware authentication failures  
- 403 authentication errors in staging
- Service dependency misconfigurations

These tests are EXPECTED TO FAIL initially to demonstrate the integration problems exist.
Once remediation is applied, these same tests should pass to validate the fix.

Issue: https://github.com/netra-systems/netra-apex/issues/463
"""

import asyncio
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import logging

# Import test infrastructure 
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import authentication components to test
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    authenticate_websocket_ssot
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceConnectionError,
    AuthServiceNotAvailableError
)

logger = logging.getLogger(__name__)


class TestWebSocketServiceToServiceAuth(SSotAsyncTestCase):
    """Test service-to-service authentication integration failures."""
    
    async def setup_method(self, method):
        """Setup test environment."""
        await super().setup_method(method)
        self.env = get_env()
        self.authenticator = UnifiedWebSocketAuthenticator()
        
        # Create mock WebSocket for testing
        self.mock_websocket = MagicMock()
        self.mock_websocket.headers = {'authorization': 'Bearer test-token'}
        self.mock_websocket.client = MagicMock()
        self.mock_websocket.client.host = '127.0.0.1'
        self.mock_websocket.client.port = 12345
        self.mock_websocket.client_state = MagicMock()
    
    async def test_auth_service_connection_failure_should_fail_gracefully(self):
        """
        REPRODUCE ISSUE #463: Auth service connection failure should fail gracefully.
        
        This test simulates the auth service being unreachable, which should cause
        a graceful failure rather than hanging or throwing unhandled exceptions.
        """
        # Setup: Mock auth service to raise connection error
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient._make_request') as mock_request:
            mock_request.side_effect = AuthServiceConnectionError("Connection refused to auth service")
            
            # Attempt WebSocket authentication
            result = await self.authenticator.authenticate_websocket_connection(self.mock_websocket)
            
            # EXPECTED FAILURE: Should fail with connection error
            assert not result.success, "Authentication should fail when auth service is unreachable"
            assert result.error_code in ['AUTH_SERVICE_CONNECTION_ERROR', 'CONNECTION_ERROR', 'AUTH_SERVICE_ERROR']
            assert 'connection' in result.error_message.lower()
            
    async def test_auth_service_timeout_should_fail_with_timeout_error(self):
        """
        Test auth service timeout scenarios.
        
        This reproduces timeout issues that occur in staging environments.
        """
        # Setup: Mock auth service to timeout
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient._make_request') as mock_request:
            mock_request.side_effect = asyncio.TimeoutError("Auth service request timed out")
            
            # Attempt WebSocket authentication
            result = await self.authenticator.authenticate_websocket_connection(self.mock_websocket)
            
            # EXPECTED FAILURE: Should fail with timeout error
            assert not result.success, "Authentication should fail when auth service times out"
            assert result.error_code in ['AUTH_SERVICE_TIMEOUT', 'TIMEOUT_ERROR', 'AUTH_SERVICE_ERROR']
            assert any(keyword in result.error_message.lower() for keyword in ['timeout', 'time', 'slow'])
    
    async def test_auth_service_503_unavailable_should_fail_appropriately(self):
        """
        REPRODUCE ISSUE #463: Auth service returning 503 Service Unavailable.
        
        This test simulates the auth service being temporarily unavailable,
        which is a common issue in staging environments.
        """
        # Setup: Mock auth service to return 503
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient._make_request') as mock_request:
            mock_request.side_effect = AuthServiceNotAvailableError("Service temporarily unavailable", status_code=503)
            
            # Attempt WebSocket authentication
            result = await self.authenticator.authenticate_websocket_connection(self.mock_websocket)
            
            # EXPECTED FAILURE: Should fail with service unavailable error
            assert not result.success, "Authentication should fail when auth service is unavailable"
            assert result.error_code in ['AUTH_SERVICE_NOT_AVAILABLE', 'SERVICE_UNAVAILABLE', 'AUTH_SERVICE_ERROR']
            assert 'unavailable' in result.error_message.lower()
    
    async def test_auth_service_invalid_response_format_should_fail(self):
        """
        Test auth service returning invalid response format.
        
        This reproduces issues where auth service returns malformed responses.
        """
        # Setup: Mock auth service to return invalid JSON
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient._make_request') as mock_request:
            # Create mock response with invalid JSON
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON response")
            mock_response.text = "Invalid response format"
            mock_request.return_value = mock_response
            
            # Attempt WebSocket authentication
            result = await self.authenticator.authenticate_websocket_connection(self.mock_websocket)
            
            # EXPECTED FAILURE: Should fail with response format error
            assert not result.success, "Authentication should fail with invalid auth service response"
            assert result.error_code in ['INVALID_RESPONSE_FORMAT', 'RESPONSE_ERROR', 'AUTH_SERVICE_ERROR']
            assert any(keyword in result.error_message.lower() for keyword in ['format', 'invalid', 'response'])


class TestWebSocketMiddlewareAuthFailures(SSotAsyncTestCase):
    """Test WebSocket middleware authentication failures."""
    
    async def setup_method(self, method):
        """Setup test environment."""
        await super().setup_method(method)
        self.authenticator = UnifiedWebSocketAuthenticator()
    
    async def test_websocket_missing_authorization_header_should_fail(self):
        """
        REPRODUCE ISSUE #463: WebSocket without authorization header should fail.
        
        This test ensures that WebSocket connections without proper authorization
        headers are rejected with appropriate error messages.
        """
        # Setup: WebSocket without authorization header
        mock_websocket = MagicMock()
        mock_websocket.headers = {}  # No authorization header
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client_state = MagicMock()
        
        # Attempt WebSocket authentication
        result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
        
        # EXPECTED FAILURE: Should fail with missing authorization error
        assert not result.success, "Authentication should fail when authorization header is missing"
        assert result.error_code in ['NO_TOKEN', 'MISSING_AUTHORIZATION', 'AUTH_REQUIRED']
        assert any(keyword in result.error_message.lower() for keyword in ['authorization', 'token', 'missing'])
    
    async def test_websocket_invalid_authorization_format_should_fail(self):
        """
        Test WebSocket with invalid authorization header format.
        """
        # Setup: WebSocket with invalid authorization format
        mock_websocket = MagicMock()
        mock_websocket.headers = {'authorization': 'InvalidFormat token-here'}  # Not "Bearer token"
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client_state = MagicMock()
        
        # Attempt WebSocket authentication
        result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
        
        # EXPECTED FAILURE: Should fail with invalid format error
        assert not result.success, "Authentication should fail with invalid authorization format"
        assert result.error_code in ['INVALID_FORMAT', 'INVALID_AUTHORIZATION', 'TOKEN_FORMAT_ERROR']
        assert any(keyword in result.error_message.lower() for keyword in ['format', 'invalid', 'bearer'])
    
    async def test_websocket_expired_token_should_fail_with_403(self):
        """
        REPRODUCE ISSUE #463: WebSocket with expired token should return 403-equivalent.
        
        This test simulates the expired token scenario that causes authentication failures.
        """
        # Setup: Mock auth service to return token expired error
        with patch('netra_backend.app.services.unified_authentication_service.UnifiedAuthenticationService.authenticate') as mock_auth:
            mock_auth.return_value = AuthResult(
                success=False,
                error="Token has expired",
                error_code="TOKEN_EXPIRED"
            )
            
            # Setup WebSocket with expired token
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer expired-token-here'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = '127.0.0.1'
            mock_websocket.client_state = MagicMock()
            
            # Attempt WebSocket authentication
            result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
            
            # EXPECTED FAILURE: Should fail with token expired error (403-equivalent)
            assert not result.success, "Authentication should fail when token is expired"
            assert result.error_code == "TOKEN_EXPIRED"
            assert 'expired' in result.error_message.lower()
    
    async def test_websocket_invalid_token_should_fail_with_403(self):
        """
        REPRODUCE ISSUE #463: WebSocket with invalid token should return 403-equivalent.
        
        This test simulates invalid token scenarios that cause authentication failures.
        """
        # Setup: Mock auth service to return invalid token error
        with patch('netra_backend.app.services.unified_authentication_service.UnifiedAuthenticationService.authenticate') as mock_auth:
            mock_auth.return_value = AuthResult(
                success=False,
                error="Invalid token signature",
                error_code="VALIDATION_FAILED"
            )
            
            # Setup WebSocket with invalid token
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer invalid-token-signature'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = '127.0.0.1'
            mock_websocket.client_state = MagicMock()
            
            # Attempt WebSocket authentication
            result = await self.authenticator.authenticate_websocket_connection(mock_websocket)
            
            # EXPECTED FAILURE: Should fail with validation failed error (403-equivalent)
            assert not result.success, "Authentication should fail when token is invalid"
            assert result.error_code == "VALIDATION_FAILED"
            assert any(keyword in result.error_message.lower() for keyword in ['invalid', 'signature', 'validation'])


class TestStagingEnvironmentAuthIntegration(SSotAsyncTestCase):
    """Test staging environment authentication integration issues."""
    
    async def setup_method(self, method):
        """Setup test environment to simulate staging."""
        await super().setup_method(method)
        
        # Simulate staging environment
        self.staging_env = {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'K_SERVICE': 'netra-backend-staging',
            # Intentionally missing secrets to reproduce the issue
        }
    
    async def test_staging_websocket_auth_without_secrets_should_fail_gracefully(self):
        """
        REPRODUCE ISSUE #463: Staging WebSocket auth without secrets should fail gracefully.
        
        This test reproduces the exact staging scenario where environment variables
        are missing and causes the WebSocket 404/502 errors.
        """
        with patch.dict('os.environ', self.staging_env, clear=True):
            authenticator = UnifiedWebSocketAuthenticator()
            
            # Create staging-like WebSocket request
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer staging-user-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'staging-client.example.com'
            mock_websocket.client_state = MagicMock()
            
            # This should fail due to missing staging secrets
            # EXPECTED FAILURE: Should detect missing staging configuration
            result = await authenticator.authenticate_websocket_connection(mock_websocket)
            
            # ASSERTION: Should fail with configuration error specific to staging
            assert not result.success, "Staging authentication should fail when secrets are missing"
            assert result.error_code in ['CONFIGURATION_ERROR', 'MISSING_SECRETS', 'AUTH_SERVICE_ERROR']
            assert any(keyword in result.error_message.lower() for keyword in ['configuration', 'staging', 'secret'])
    
    async def test_staging_auth_service_url_misconfiguration_should_fail(self):
        """
        Test staging auth service URL misconfiguration scenarios.
        """
        # Add invalid auth service URL to staging environment
        staging_env_with_bad_url = self.staging_env.copy()
        staging_env_with_bad_url['AUTH_SERVICE_URL'] = 'http://invalid-staging-auth-service'
        
        with patch.dict('os.environ', staging_env_with_bad_url, clear=True):
            authenticator = UnifiedWebSocketAuthenticator()
            
            # Create staging WebSocket request
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer staging-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'staging-client'
            mock_websocket.client_state = MagicMock()
            
            # This should fail due to bad auth service URL
            result = await authenticator.authenticate_websocket_connection(mock_websocket)
            
            # ASSERTION: Should fail with connection error to auth service
            assert not result.success, "Should fail when auth service URL is misconfigured"
            assert result.error_code in ['AUTH_SERVICE_CONNECTION_ERROR', 'CONNECTION_ERROR', 'AUTH_SERVICE_ERROR']
    
    async def test_staging_circuit_breaker_behavior_under_auth_failures(self):
        """
        Test circuit breaker behavior under repeated authentication failures in staging.
        
        This test ensures the circuit breaker opens appropriately to prevent
        cascading failures in staging environments.
        """
        with patch.dict('os.environ', self.staging_env, clear=True):
            authenticator = UnifiedWebSocketAuthenticator()
            
            # Create multiple failing authentication attempts
            failed_attempts = []
            
            for i in range(5):  # More than failure_threshold of 3
                mock_websocket = MagicMock()
                mock_websocket.headers = {'authorization': f'Bearer failing-token-{i}'}
                mock_websocket.client = MagicMock()
                mock_websocket.client.host = f'client-{i}.staging.com'
                mock_websocket.client_state = MagicMock()
                
                result = await authenticator.authenticate_websocket_connection(mock_websocket)
                failed_attempts.append(result)
                
                # Small delay between attempts
                await asyncio.sleep(0.01)
            
            # EXPECTED FAILURE: All attempts should fail
            for i, result in enumerate(failed_attempts):
                assert not result.success, f"Authentication attempt {i+1} should fail"
                
                # Later attempts should show circuit breaker behavior
                if i >= 3:  # After failure threshold
                    assert result.error_code in ['AUTH_CIRCUIT_BREAKER_OPEN', 'CIRCUIT_BREAKER_OPEN']


class TestWebSocketAuthenticationServiceIntegration(SSotAsyncTestCase):
    """Test full service integration scenarios."""
    
    async def setup_method(self, method):
        """Setup test environment."""
        await super().setup_method(method)
        
    async def test_unified_auth_service_integration_failure_should_propagate(self):
        """
        Test that unified authentication service integration failures propagate correctly.
        
        This ensures that failures from the auth service are properly handled
        and communicated through the WebSocket authentication layer.
        """
        # Setup: Mock unified auth service to fail
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_get_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.authenticate_websocket.return_value = (
                AuthResult(success=False, error="Service integration failure", error_code="SERVICE_INTEGRATION_ERROR"),
                None
            )
            mock_get_service.return_value = mock_auth_service
            
            authenticator = UnifiedWebSocketAuthenticator()
            
            # Create WebSocket request
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer integration-test-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'integration-test-client'
            mock_websocket.client_state = MagicMock()
            
            # This should fail with service integration error
            result = await authenticator.authenticate_websocket_connection(mock_websocket)
            
            # ASSERTION: Should properly propagate service integration failure
            assert not result.success, "Should fail when unified auth service fails"
            assert result.error_code == "SERVICE_INTEGRATION_ERROR"
            assert 'integration' in result.error_message.lower()
    
    async def test_websocket_ssot_authentication_flow_failure(self):
        """
        Test the SSOT WebSocket authentication flow failure scenarios.
        
        This tests the authenticate_websocket_ssot function that should handle
        service integration failures gracefully.
        """
        # Create WebSocket with invalid configuration
        mock_websocket = MagicMock()
        mock_websocket.headers = {'authorization': 'Bearer ssot-test-token'}
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = 'ssot-test-client'
        mock_websocket.client_state = MagicMock()
        
        # Mock environment to cause failure
        with patch.dict('os.environ', {}, clear=True):
            # This should fail due to missing environment configuration
            # EXPECTED FAILURE: SSOT authentication should fail gracefully
            result = await authenticate_websocket_ssot(mock_websocket)
            
            # ASSERTION: Should fail with configuration or service error
            assert not result.success, "SSOT authentication should fail with missing configuration"
            assert result.error_code in ['CONFIGURATION_ERROR', 'AUTH_SERVICE_ERROR', 'SERVICE_INTEGRATION_ERROR']


if __name__ == '__main__':
    """
    Run these integration tests to reproduce Issue #463 WebSocket authentication failures.
    
    Expected outcome: MOST TESTS SHOULD FAIL
    This demonstrates that the service integration and middleware authentication 
    is not working correctly in various scenarios.
    
    Usage:
    python -m pytest tests/integration/auth/test_websocket_authentication_failures_issue_463.py -v
    """
    pytest.main([__file__, '-v', '--tb=short'])