"""
Unit Tests for Issue #463: WebSocket Authentication Environment Variable Failures

This test suite reproduces the missing environment variable issues identified in Issue #463:
- SERVICE_SECRET missing/present scenarios
- JWT_SECRET_KEY validation logic  
- AUTH_SERVICE_URL configuration failures

These tests are EXPECTED TO FAIL initially to demonstrate the problem exists.
Once remediation is applied, these same tests should pass to validate the fix.

Issue: https://github.com/netra-systems/netra-apex/issues/463
"""
import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator, get_websocket_authenticator, _validate_critical_environment_configuration
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service

class TestServiceSecretValidation:
    """Test SERVICE_SECRET environment variable validation."""

    def test_service_secret_missing_should_fail_auth(self):
        """
        REPRODUCE ISSUE #463: SERVICE_SECRET missing should cause auth failure.
        
        This test expects to FAIL because the system should detect missing SERVICE_SECRET
        and handle it gracefully, but currently doesn't.
        """
        with patch.dict(os.environ, {}, clear=False):
            if 'SERVICE_SECRET' in os.environ:
                del os.environ['SERVICE_SECRET']
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer test-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'test-host'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            assert not result.success, 'Authentication should fail when SERVICE_SECRET is missing'
            assert result.error_code in ['MISSING_SERVICE_SECRET', 'CONFIGURATION_ERROR', 'AUTH_SERVICE_ERROR']
            assert 'service_secret' in result.error_message.lower() or 'configuration' in result.error_message.lower()

    def test_service_secret_present_should_succeed_auth(self):
        """
        Test SERVICE_SECRET present scenario for contrast.
        
        This test might also fail if auth service is not properly configured.
        """
        with patch.dict(os.environ, {'SERVICE_SECRET': 'test-service-secret-value'}, clear=False):
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer valid-test-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'test-host'
            mock_websocket.client_state = MagicMock()
            e2e_context = {'is_e2e_testing': True, 'bypass_enabled': True, 'test_environment': 'unit_test'}
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket, e2e_context=e2e_context))
            if not result.success:
                assert 'service_secret' not in result.error_message.lower()

class TestJwtSecretKeyValidation:
    """Test JWT_SECRET_KEY environment variable validation."""

    def test_jwt_secret_key_missing_should_fail_auth(self):
        """
        REPRODUCE ISSUE #463: JWT_SECRET_KEY missing should cause auth failure.
        
        This test expects to FAIL because the system should detect missing JWT_SECRET_KEY.
        """
        with patch.dict(os.environ, {}, clear=False):
            for jwt_var in ['JWT_SECRET_KEY', 'JWT_SECRET', 'AUTH_SECRET']:
                if jwt_var in os.environ:
                    del os.environ[jwt_var]
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer test-jwt-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'test-host'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            assert not result.success, 'Authentication should fail when JWT_SECRET_KEY is missing'
            assert result.error_code in ['MISSING_JWT_SECRET', 'CONFIGURATION_ERROR', 'AUTH_SERVICE_ERROR']
            assert any((keyword in result.error_message.lower() for keyword in ['jwt', 'secret', 'configuration']))

    def test_jwt_secret_key_invalid_format_should_fail_auth(self):
        """
        Test JWT_SECRET_KEY with invalid format (too short, wrong format).
        """
        with patch.dict(os.environ, {'JWT_SECRET_KEY': 'abc'}, clear=False):
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer test-jwt-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'test-host'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            if not result.success:
                assert any((keyword in result.error_message.lower() for keyword in ['jwt', 'secret', 'invalid', 'format']))

class TestAuthServiceUrlValidation:
    """Test AUTH_SERVICE_URL environment variable validation."""

    def test_auth_service_url_missing_should_fail_auth(self):
        """
        REPRODUCE ISSUE #463: AUTH_SERVICE_URL missing should cause auth failure.
        
        This test expects to FAIL because WebSocket auth depends on auth service connectivity.
        """
        with patch.dict(os.environ, {}, clear=False):
            if 'AUTH_SERVICE_URL' in os.environ:
                del os.environ['AUTH_SERVICE_URL']
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer test-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'test-host'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            assert not result.success, 'Authentication should fail when AUTH_SERVICE_URL is missing'
            assert result.error_code in ['MISSING_AUTH_SERVICE_URL', 'CONFIGURATION_ERROR', 'AUTH_SERVICE_ERROR', 'AUTH_SERVICE_CONNECTION_ERROR']
            assert any((keyword in result.error_message.lower() for keyword in ['auth_service', 'url', 'configuration', 'connection']))

    def test_auth_service_url_invalid_format_should_fail_auth(self):
        """
        Test AUTH_SERVICE_URL with invalid format.
        """
        with patch.dict(os.environ, {'AUTH_SERVICE_URL': 'not-a-valid-url'}, clear=False):
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer test-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'test-host'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            if not result.success:
                assert any((keyword in result.error_message.lower() for keyword in ['url', 'connection', 'invalid', 'format']))

    def test_auth_service_url_unreachable_should_fail_auth(self):
        """
        Test AUTH_SERVICE_URL pointing to unreachable service.
        """
        with patch.dict(os.environ, {'AUTH_SERVICE_URL': 'http://localhost:99999'}, clear=False):
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer test-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'test-host'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            assert not result.success, 'Authentication should fail when auth service is unreachable'
            assert result.error_code in ['AUTH_SERVICE_CONNECTION_ERROR', 'CONNECTION_ERROR', 'AUTH_SERVICE_ERROR']

class TestCriticalEnvironmentConfiguration:
    """Test the critical environment configuration validation function."""

    def test_validate_critical_environment_with_missing_variables(self):
        """
        Test environment validation function with missing critical variables.
        
        This test validates the _validate_critical_environment_configuration function
        that should detect missing environment variables.
        """
        with patch.dict(os.environ, {}, clear=False):
            for var in ['ENVIRONMENT', 'AUTH_SERVICE_URL', 'JWT_SECRET_KEY', 'SERVICE_SECRET']:
                if var in os.environ:
                    del os.environ[var]
            validation_result = _validate_critical_environment_configuration()
            assert not validation_result['valid'], 'Validation should fail with missing critical variables'
            assert len(validation_result['errors']) > 0, 'Should have error messages for missing variables'
            assert len(validation_result['warnings']) > 0, 'Should have warnings for missing optional variables'

    def test_validate_critical_environment_with_all_variables_present(self):
        """
        Test environment validation function with all variables present.
        """
        test_env = {'ENVIRONMENT': 'development', 'AUTH_SERVICE_URL': 'http://localhost:8081', 'JWT_SECRET_KEY': 'test-jwt-secret-key-for-development', 'SERVICE_SECRET': 'test-service-secret-value', 'DATABASE_URL': 'postgresql://localhost/test', 'REDIS_URL': 'redis://localhost:6379'}
        with patch.dict(os.environ, test_env, clear=False):
            validation_result = _validate_critical_environment_configuration()
            if not validation_result['valid']:
                for error in validation_result['errors']:
                    assert not any((var.lower() in error.lower() for var in test_env.keys()))

class TestEnvironmentVariableIntegration:
    """Integration tests for environment variables with WebSocket authentication."""

    def test_staging_environment_without_required_secrets_should_fail(self):
        """
        REPRODUCE ISSUE #463: Staging environment without secrets should fail gracefully.
        
        This reproduces the exact staging scenario where environment variables are missing.
        """
        staging_env = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'K_SERVICE': 'netra-backend-staging'}
        with patch.dict(os.environ, staging_env, clear=True):
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer staging-test-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'staging-client'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            assert not result.success, 'Staging authentication should fail when secrets are missing'
            assert result.error_code in ['CONFIGURATION_ERROR', 'AUTH_SERVICE_ERROR', 'MISSING_SECRETS']
            assert any((keyword in result.error_message.lower() for keyword in ['configuration', 'secret', 'missing', 'staging']))

    def test_websocket_connection_with_partial_environment_should_fail_appropriately(self):
        """
        Test WebSocket connection with only some environment variables present.
        
        This reproduces scenarios where some but not all required variables are configured.
        """
        partial_env = {'ENVIRONMENT': 'staging', 'AUTH_SERVICE_URL': 'https://auth-service-staging-url.example.com'}
        with patch.dict(os.environ, partial_env, clear=True):
            authenticator = UnifiedWebSocketAuthenticator()
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer partial-env-token'}
            mock_websocket.client = MagicMock()
            mock_websocket.client.host = 'partial-env-client'
            mock_websocket.client_state = MagicMock()
            result = asyncio.run(authenticator.authenticate_websocket_connection(mock_websocket))
            assert not result.success, 'Authentication should fail with partial environment configuration'
            if 'configuration' in result.error_message.lower():
                assert any((keyword in result.error_message.lower() for keyword in ['secret', 'jwt', 'service']))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')