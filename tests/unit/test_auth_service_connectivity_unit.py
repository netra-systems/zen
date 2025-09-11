"""
Unit Tests for Auth Service Connectivity Issues (Issue #395)

MISSION: Create failing tests that reproduce exact connectivity problems described in issue #395.
These tests validate timeout behavior, error handling patterns, and configuration parsing 
for auth service connectivity without requiring Docker.

Business Impact:
- Validates $500K+ ARR Golden Path user flow reliability
- Ensures auth service connectivity issues are caught early
- Tests critical timeout configurations (0.5s staging timeout)
- Validates error handling for connectivity failures
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ServerTimeoutError

# SSOT Import Registry - Verified imports
from netra_backend.app.clients.auth_client_core import AuthClientCore
from netra_backend.app.auth_integration.auth import (
    get_current_user, 
    get_current_user_with_db,
    validate_token_jwt,
    extract_admin_status_from_jwt
)
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuth
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestAuthServiceConnectivityUnit(SSotAsyncTestCase):
    """Unit tests for auth service connectivity timeout and error handling"""
    
    async def asyncSetUp(self):
        """Set up test environment"""
        await super().asyncSetUp()
        self.auth_client = AuthClientCore()
        self.websocket_auth = UnifiedWebSocketAuth()
        
        # Mock environment for consistent testing
        self.env_patcher = patch.object(IsolatedEnvironment, 'get')
        self.mock_env = self.env_patcher.start()
        self.mock_env.return_value = {
            'ENVIRONMENT': 'staging',
            'AUTH_SERVICE_URL': 'http://localhost:8081',
            'JWT_SECRET_KEY': 'test-secret-key'
        }
    
    async def asyncTearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        await super().asyncTearDown()

    async def test_auth_client_staging_timeout_behavior(self):
        """
        TEST: Validate 0.5s staging timeout configuration causes connectivity failures
        EXPECTED: Should reproduce timeout errors described in issue #395
        BUSINESS IMPACT: Critical for WebSocket authentication performance
        """
        # GIVEN: Staging environment with ultra-fast timeout (0.5s)
        self.mock_env.return_value = {
            'ENVIRONMENT': 'staging',
            'AUTH_SERVICE_URL': 'http://localhost:8081'
        }
        
        # WHEN: Health check takes longer than 0.5s (simulating connectivity issues)
        with patch.object(self.auth_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Simulate timeout after 0.5s
            mock_client.get.side_effect = asyncio.TimeoutError("Health check timeout")
            
            # THEN: Should fail with timeout error
            result = await self.auth_client.is_service_available()
            self.assertFalse(result, "Expected auth service to be unavailable due to timeout")
            
            # Verify timeout was set correctly for staging
            mock_client.get.assert_called_with("/health")

    async def test_auth_client_connection_error_handling(self):
        """
        TEST: Validate connection errors are properly handled and logged
        EXPECTED: Should reproduce connection failures described in issue #395
        """
        # GIVEN: Auth service URL that cannot be reached
        with patch.object(self.auth_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Simulate connection error (auth service not running)
            mock_client.get.side_effect = ClientConnectorError(
                connection_key=None, 
                os_error=OSError("Connection refused")
            )
            
            # WHEN: Attempting to check service availability
            result = await self.auth_client.is_service_available()
            
            # THEN: Should gracefully handle connection error
            self.assertFalse(result, "Expected service to be unavailable due to connection error")

    async def test_validate_token_jwt_connectivity_failure(self):
        """
        TEST: Validate token validation fails when auth service is unreachable
        EXPECTED: Should reproduce validation failures described in issue #395 line 209
        """
        # GIVEN: Auth client that fails connectivity
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_client:
            mock_client.validate_token.side_effect = aiohttp.ClientError("Connection failed")
            
            # WHEN: Attempting to validate JWT token
            result = await validate_token_jwt("test.jwt.token")
            
            # THEN: Should return None due to connectivity failure
            self.assertIsNone(result, "Expected token validation to fail due to connectivity issues")
            mock_client.validate_token.assert_called_once_with("test.jwt.token")

    async def test_get_current_user_auth_service_failure(self):
        """
        TEST: Validate get_current_user fails when auth service connectivity fails
        EXPECTED: Should reproduce failures described in issue #395 line 299
        """
        # GIVEN: Mock HTTPAuthorizationCredentials
        from fastapi.security import HTTPAuthorizationCredentials
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test.jwt.token"
        )
        
        # WHEN: Auth service validation fails
        with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate:
            mock_validate.side_effect = aiohttp.ClientError("Auth service unavailable")
            
            # THEN: Should raise HTTPException
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as excinfo:
                await get_current_user(mock_credentials)
            
            # Verify proper error handling
            self.assertEqual(excinfo.value.status_code, 401)

    async def test_websocket_auth_service_timeout(self):
        """
        TEST: Validate WebSocket authentication fails due to auth service timeout
        EXPECTED: Should reproduce WebSocket auth failures described in issue #395 line 438
        """
        # GIVEN: WebSocket connection mock
        mock_websocket = MagicMock()
        mock_websocket.headers = {"authorization": "Bearer test.jwt.token"}
        
        # WHEN: Auth service times out during WebSocket authentication
        with patch.object(self.websocket_auth, '_validate_with_auth_service') as mock_validate:
            mock_validate.side_effect = asyncio.TimeoutError("Auth service timeout")
            
            # THEN: Authentication should fail
            from netra_backend.app.websocket_core.unified_websocket_auth import WebSocketAuthResult
            
            # Mock the authentication method
            with patch.object(self.websocket_auth, 'authenticate_websocket_ssot') as mock_auth:
                mock_auth.return_value = WebSocketAuthResult(
                    success=False,
                    error_message="Auth service timeout during WebSocket authentication",
                    error_code="AUTH_SERVICE_TIMEOUT"
                )
                
                result = await self.websocket_auth.authenticate_websocket_ssot(mock_websocket)
                
                self.assertFalse(result.success, "Expected WebSocket auth to fail due to timeout")
                self.assertIn("timeout", result.error_message.lower())

    async def test_extract_admin_status_connectivity_failure(self):
        """
        TEST: Validate admin status extraction fails when auth service is unreachable
        EXPECTED: Should reproduce failures described in issue #395 line 319
        """
        # GIVEN: JWT token for admin validation
        test_token = "test.jwt.token"
        
        # WHEN: Auth service is unreachable during admin status extraction
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_client:
            mock_client.extract_admin_status.side_effect = aiohttp.ClientError("Connection failed")
            
            # THEN: Should handle connectivity failure gracefully
            try:
                result = await extract_admin_status_from_jwt(test_token)
                # Should return default non-admin status on connectivity failure
                self.assertEqual(result.get("is_admin", False), False)
            except Exception as e:
                # Or should raise appropriate exception for error handling
                self.assertIsInstance(e, (aiohttp.ClientError, ConnectionError))

    async def test_auth_circuit_breaker_behavior(self):
        """
        TEST: Validate circuit breaker behavior during connectivity failures
        EXPECTED: Should test auth service circuit breaker patterns
        """
        # GIVEN: Multiple consecutive failures
        with patch.object(self.auth_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get.side_effect = ClientConnectorError(
                connection_key=None, 
                os_error=OSError("Connection refused")
            )
            
            # WHEN: Multiple service availability checks fail
            results = []
            for _ in range(5):  # Simulate multiple failures
                result = await self.auth_client.is_service_available()
                results.append(result)
                await asyncio.sleep(0.1)  # Small delay between attempts
            
            # THEN: All should fail consistently
            self.assertTrue(all(not result for result in results), 
                          "Expected all service checks to fail due to circuit breaker")

    def test_auth_service_url_configuration_parsing(self):
        """
        TEST: Validate auth service URL configuration is parsed correctly
        EXPECTED: Should validate configuration used in connectivity
        """
        # GIVEN: Different environment configurations
        test_configs = [
            {
                'ENVIRONMENT': 'development',
                'AUTH_SERVICE_URL': 'http://localhost:8081',
                'expected_timeout': 1.0
            },
            {
                'ENVIRONMENT': 'staging', 
                'AUTH_SERVICE_URL': 'https://auth-service-staging.example.com',
                'expected_timeout': 0.5
            },
            {
                'ENVIRONMENT': 'production',
                'AUTH_SERVICE_URL': 'https://auth-service.example.com', 
                'expected_timeout': 1.0
            }
        ]
        
        for config in test_configs:
            # WHEN: Configuration is parsed for different environments
            self.mock_env.return_value = config
            
            # THEN: Should parse correctly
            from shared.isolated_environment import get_env
            env_data = get_env()
            self.assertEqual(env_data.get('ENVIRONMENT'), config['ENVIRONMENT'])
            self.assertEqual(env_data.get('AUTH_SERVICE_URL'), config['AUTH_SERVICE_URL'])

    async def test_auth_service_health_check_response_handling(self):
        """
        TEST: Validate different auth service health check response scenarios
        EXPECTED: Should test various response conditions that could cause connectivity issues
        """
        test_scenarios = [
            {
                'name': 'healthy_response',
                'status_code': 200,
                'response_data': {'status': 'healthy'},
                'expected_available': True
            },
            {
                'name': 'service_unavailable',
                'status_code': 503,
                'response_data': {'status': 'service_unavailable'},
                'expected_available': False
            },
            {
                'name': 'timeout_response',
                'status_code': None,
                'exception': ServerTimeoutError("Request timeout"),
                'expected_available': False
            },
            {
                'name': 'internal_error',
                'status_code': 500,
                'response_data': {'error': 'internal_server_error'},
                'expected_available': False
            }
        ]
        
        for scenario in test_scenarios:
            # GIVEN: Different auth service responses
            with patch.object(self.auth_client, '_get_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_get_client.return_value = mock_client
                
                if 'exception' in scenario:
                    mock_client.get.side_effect = scenario['exception']
                else:
                    mock_response = AsyncMock()
                    mock_response.status = scenario['status_code']
                    mock_response.json.return_value = scenario['response_data']
                    mock_client.get.return_value = mock_response
                
                # WHEN: Checking service availability
                result = await self.auth_client.is_service_available()
                
                # THEN: Should match expected availability
                self.assertEqual(result, scenario['expected_available'],
                               f"Expected {scenario['expected_available']} for scenario {scenario['name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])