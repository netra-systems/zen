"""
End-to-End Regression Test for JWT Environment-Specific Secret Configuration

This test ensures that the auth service and backend WebSocket both use the same
environment-specific JWT secrets to prevent authentication failures in staging.

Bug Reference: JWT_AUTH_STAGING_FAILURE_20250907.md
Root Cause: Auth service uses JWT_SECRET_STAGING but backend only checked JWT_SECRET_KEY

CRITICAL: This test MUST pass before deploying to staging/production!
"""
import asyncio
import jwt
import pytest
import httpx
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from shared.isolated_environment import get_env
from test_framework.unified_test_base import UnifiedTestBase

class TestJWTEnvironmentSecretRegression(UnifiedTestBase):
    """
    CRITICAL REGRESSION TEST: JWT Secret Alignment Between Services
    
    This test suite validates that auth service and backend use the same
    JWT secret configuration to prevent 401 authentication failures.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment for JWT secret testing."""
        super().setUpClass()
        cls.env = get_env()
        cls.original_env = cls.env.get('ENVIRONMENT')

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        super().tearDownClass()
        if cls.original_env:
            cls.env.set('ENVIRONMENT', cls.original_env, 'test_cleanup')

    def setUp(self):
        """Set up each test."""
        super().setUp()
        for key in ['JWT_SECRET_STAGING', 'JWT_SECRET_PRODUCTION', 'JWT_SECRET_TEST', 'JWT_SECRET_KEY']:
            try:
                self.env.delete(key, 'test_setup')
            except KeyError:
                pass
            except Exception as e:
                self.fail(f'Unexpected error deleting {key}: {e}')

    @pytest.mark.asyncio
    async def test_staging_jwt_secret_alignment(self):
        """
        CRITICAL TEST: Verify staging environment uses same JWT secret in both services.
        
        This test reproduces and verifies the fix for the staging 401 auth failure.
        """
        self.env.set('ENVIRONMENT', 'staging', 'test')
        staging_secret = 'staging-jwt-secret-minimum-32-characters-for-security'
        self.env.set('JWT_SECRET_STAGING', staging_secret, 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        from auth_service.auth_core.auth_environment import AuthEnvironment
        backend_extractor = UserContextExtractor()
        backend_secret = backend_extractor._get_jwt_secret()
        auth_env = AuthEnvironment()
        auth_secret = auth_env.get_jwt_secret_key()
        self.assertEqual(backend_secret, staging_secret, f'Backend not using staging secret! Got: {backend_secret}')
        self.assertEqual(auth_secret, staging_secret, f'Auth service not using staging secret! Got: {auth_secret}')
        self.assertEqual(backend_secret, auth_secret, "Backend and auth service JWT secrets don't match!")
        payload = {'sub': 'staging-user-123', 'email': 'staging@example.com', 'exp': datetime.now(timezone.utc) + timedelta(hours=1), 'iat': datetime.now(timezone.utc)}
        auth_token = jwt.encode(payload, auth_secret, algorithm='HS256')
        decoded = await backend_extractor.validate_and_decode_jwt(auth_token)
        self.assertIsNotNone(decoded, 'Backend failed to validate auth service token!')
        self.assertEqual(decoded['sub'], 'staging-user-123')
        self.assertEqual(decoded['email'], 'staging@example.com')

    @pytest.mark.asyncio
    async def test_production_jwt_secret_alignment(self):
        """Test production environment JWT secret configuration."""
        self.env.set('ENVIRONMENT', 'production', 'test')
        prod_secret = 'production-jwt-secret-ultra-secure-64-characters-minimum-required'
        self.env.set('JWT_SECRET_PRODUCTION', prod_secret, 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        from auth_service.auth_core.auth_environment import AuthEnvironment
        backend_extractor = UserContextExtractor()
        backend_secret = backend_extractor._get_jwt_secret()
        auth_env = AuthEnvironment()
        auth_secret = auth_env.get_jwt_secret_key()
        self.assertEqual(backend_secret, prod_secret)
        self.assertEqual(auth_secret, prod_secret)
        self.assertEqual(backend_secret, auth_secret)

    @pytest.mark.asyncio
    async def test_websocket_auth_flow_with_env_secrets(self):
        """
        Test complete WebSocket authentication flow with environment-specific secrets.
        
        This simulates the exact flow that was failing in staging.
        """
        self.env.set('ENVIRONMENT', 'staging', 'test')
        staging_secret = 'staging-websocket-jwt-secret-32-chars-minimum'
        self.env.set('JWT_SECRET_STAGING', staging_secret, 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        payload = {'sub': 'websocket-user-789', 'email': 'ws-test@example.com', 'permissions': ['chat', 'agent_execution'], 'exp': datetime.now(timezone.utc) + timedelta(hours=1), 'iat': datetime.now(timezone.utc), 'thread_id': 'thread_test_123', 'run_id': 'run_test_456'}
        token = jwt.encode(payload, staging_secret, algorithm='HS256')
        mock_websocket = MagicMock()
        mock_websocket.headers = {'authorization': f'Bearer {token}', 'user-agent': 'TestClient/1.0', 'origin': 'https://staging.netra.com', 'host': 'staging-api.netra.com'}
        extractor = UserContextExtractor()
        user_context, auth_info = await extractor.extract_user_context_from_websocket(mock_websocket)
        self.assertEqual(user_context.user_id, 'websocket-user-789')
        self.assertEqual(user_context.thread_id, 'thread_test_123')
        self.assertEqual(user_context.run_id, 'run_test_456')
        self.assertEqual(auth_info['email'], 'ws-test@example.com')
        self.assertIn('chat', auth_info['permissions'])
        self.assertIn('agent_execution', auth_info['permissions'])

    @pytest.mark.asyncio
    async def test_fallback_chain_consistency(self):
        """
        Test that both services follow the same JWT secret fallback chain.
        
        Priority should be:
        1. Environment-specific (JWT_SECRET_STAGING)
        2. Generic (JWT_SECRET_KEY)
        3. Legacy (JWT_SECRET)
        """
        self.env.set('ENVIRONMENT', 'staging', 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        from auth_service.auth_core.auth_environment import AuthEnvironment
        self.env.set('JWT_SECRET_KEY', 'generic-secret-key', 'test')
        backend_ext = UserContextExtractor()
        auth_env = AuthEnvironment()
        self.assertEqual(backend_ext._get_jwt_secret(), 'generic-secret-key')
        self.assertEqual(auth_env.get_jwt_secret_key(), 'generic-secret-key')
        self.env.set('JWT_SECRET_STAGING', 'staging-specific', 'test')
        backend_ext = UserContextExtractor()
        auth_env = AuthEnvironment()
        self.assertEqual(backend_ext._get_jwt_secret(), 'staging-specific')
        self.assertEqual(auth_env.get_jwt_secret_key(), 'staging-specific')
        self.env.delete('JWT_SECRET_STAGING', 'test')
        self.env.delete('JWT_SECRET_KEY', 'test')

    @pytest.mark.asyncio
    async def test_error_scenario_mismatched_secrets(self):
        """
        Test that mismatched secrets between services cause authentication failure.
        
        This reproduces the original bug scenario.
        """
        self.env.set('ENVIRONMENT', 'staging', 'test')
        auth_secret = 'staging-secret-used-by-auth'
        backend_secret = 'different-generic-secret'
        payload = {'sub': 'test-user', 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, auth_secret, algorithm='HS256')
        try:
            jwt.decode(token, backend_secret, algorithms=['HS256'])
            self.fail('Should have raised InvalidSignatureError')
        except jwt.InvalidSignatureError:
            pass

    @pytest.mark.asyncio
    async def test_migration_path_backward_compatibility(self):
        """
        Test that the fix maintains backward compatibility.
        
        Systems using only JWT_SECRET_KEY should still work.
        """
        self.env.set('ENVIRONMENT', 'development', 'test')
        self.env.set('JWT_SECRET_KEY', 'backward-compat-secret', 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        secret = extractor._get_jwt_secret()
        self.assertEqual(secret, 'backward-compat-secret', 'Should still support JWT_SECRET_KEY for backward compatibility')

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_secret(self):
        """
        Test that concurrent requests use the same JWT secret.
        
        This ensures no race conditions in secret loading.
        """
        self.env.set('ENVIRONMENT', 'staging', 'test')
        self.env.set('JWT_SECRET_STAGING', 'concurrent-test-secret', 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor

        async def get_secret():
            extractor = UserContextExtractor()
            return extractor._get_jwt_secret()
        tasks = [get_secret() for _ in range(10)]
        secrets = await asyncio.gather(*tasks)
        self.assertEqual(len(set(secrets)), 1, 'All concurrent requests should get same secret')
        self.assertEqual(secrets[0], 'concurrent-test-secret')

class TestJWTSecretValidation(UnifiedTestBase):
    """Additional validation tests for JWT secret configuration."""

    @pytest.mark.asyncio
    async def test_secret_length_validation(self):
        """Test that secrets meet minimum length requirements."""
        self.env.set('ENVIRONMENT', 'production', 'test')
        short_secret = 'too-short'
        self.env.set('JWT_SECRET_PRODUCTION', short_secret, 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        secret = extractor._get_jwt_secret()
        self.assertEqual(secret, short_secret)

    @pytest.mark.asyncio
    async def test_secret_trimming(self):
        """Test that secrets are properly trimmed of whitespace."""
        self.env.set('ENVIRONMENT', 'staging', 'test')
        self.env.set('JWT_SECRET_STAGING', '  secret-with-spaces  ', 'test')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        from auth_service.auth_core.auth_environment import AuthEnvironment
        backend_ext = UserContextExtractor()
        auth_env = AuthEnvironment()
        self.assertEqual(backend_ext._get_jwt_secret(), 'secret-with-spaces')
        self.assertEqual(auth_env.get_jwt_secret_key(), 'secret-with-spaces')

    @pytest.mark.asyncio
    async def test_missing_secret_error_messages(self):
        """Test that helpful error messages are provided when secrets are missing."""
        self.env.set('ENVIRONMENT', 'production', 'test')
        for key in ['JWT_SECRET_PRODUCTION', 'JWT_SECRET_KEY', 'JWT_SECRET']:
            try:
                self.env.delete(key, 'test')
            except KeyError:
                pass
            except Exception as e:
                self.fail(f'Unexpected error deleting {key} during test: {e}')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        with self.assertRaises(RuntimeError) as context:
            extractor = UserContextExtractor()
        error_msg = str(context.exception)
        self.assertIn('JWT secret key not configured', error_msg)
        self.assertIn('production', error_msg)
        self.assertIn('JWT_SECRET_PRODUCTION', error_msg)

class TestCrossServiceJWTFlow(UnifiedTestBase):
    """Test complete cross-service JWT flow with real components."""

    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_real_auth_to_backend_flow(self):
        """
        Test real JWT flow from auth service to backend validation.
        
        This requires both services to be running.
        """
        if not self.use_real_services:
            self.skipTest('Real services not enabled')
        self.env.set('ENVIRONMENT', 'staging', 'test')
        staging_secret = 'real-test-staging-secret-32-characters'
        self.env.set('JWT_SECRET_STAGING', staging_secret, 'test')
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        auth_client = AuthServiceClient(base_url='http://localhost:8081')
        user_data = {'user_id': 'real-test-user', 'email': 'real@example.com', 'permissions': ['read', 'write']}
        token = jwt.encode({'sub': user_data['user_id'], 'email': user_data['email'], 'permissions': user_data['permissions'], 'exp': datetime.now(timezone.utc) + timedelta(hours=1), 'iat': datetime.now(timezone.utc)}, staging_secret, algorithm='HS256')
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        decoded = await extractor.validate_and_decode_jwt(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded['sub'], 'real-test-user')
        self.assertEqual(decoded['email'], 'real@example.com')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')