"""
Test JWT Secret Synchronization Between Services

CRITICAL: This test validates that auth service and backend service
use IDENTICAL JWT secrets for cross-service authentication.

This test was created to reproduce and verify the fix for the
JWT secret mismatch issue that was causing authentication failures.
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from shared.jwt_secret_manager import SharedJWTSecretManager
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

class TestJWTSecretSynchronization:
    """Test JWT secret consistency across all services."""

    def setup_method(self):
        """Setup test environment."""
        SharedJWTSecretManager.clear_cache()

    def teardown_method(self):
        """Cleanup after tests."""
        SharedJWTSecretManager.clear_cache()

    def test_auth_service_uses_shared_jwt_manager(self):
        """Test that auth service correctly uses SharedJWTSecretManager."""
        test_secret = 'test-jwt-secret-for-sync-validation-32-chars'
        with patch.dict(os.environ, {'JWT_SECRET_KEY': test_secret, 'ENVIRONMENT': 'development'}):
            SharedJWTSecretManager.clear_cache()
            from auth_service.auth_core.config import AuthConfig
            auth_jwt_secret = AuthConfig.get_jwt_secret()
            shared_jwt_secret = SharedJWTSecretManager.get_jwt_secret()
            assert auth_jwt_secret == shared_jwt_secret, f'Auth service JWT secret mismatch: {auth_jwt_secret} != {shared_jwt_secret}'
            assert auth_jwt_secret == test_secret, f'Auth service not loading test secret: {auth_jwt_secret}'

    def test_backend_service_uses_shared_jwt_manager(self):
        """Test that backend service now uses SharedJWTSecretManager after fix."""
        test_secret = 'test-backend-jwt-secret-sync-32-chars'
        with patch.dict(os.environ, {'JWT_SECRET_KEY': test_secret, 'ENVIRONMENT': 'development'}):
            SharedJWTSecretManager.clear_cache()
            from netra_backend.app.core.configuration.secrets import SecretManager
            from netra_backend.app.schemas.config import DevelopmentConfig
            config = DevelopmentConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            backend_jwt_secret = config.jwt_secret_key
            shared_jwt_secret = SharedJWTSecretManager.get_jwt_secret()
            assert backend_jwt_secret == shared_jwt_secret, f'Backend JWT secret not using SharedJWTSecretManager: {backend_jwt_secret} != {shared_jwt_secret}'
            assert backend_jwt_secret == test_secret, f'Backend not loading test secret: {backend_jwt_secret}'

    def test_cross_service_jwt_secret_synchronization(self):
        """Test that both services use IDENTICAL JWT secrets."""
        test_secret = 'cross-service-sync-test-jwt-secret-32'
        with patch.dict(os.environ, {'JWT_SECRET_KEY': test_secret, 'ENVIRONMENT': 'development'}):
            SharedJWTSecretManager.clear_cache()
            from auth_service.auth_core.config import AuthConfig
            auth_jwt_secret = AuthConfig.get_jwt_secret()
            from netra_backend.app.core.configuration.secrets import SecretManager
            from netra_backend.app.schemas.config import DevelopmentConfig
            config = DevelopmentConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            backend_jwt_secret = config.jwt_secret_key
            assert auth_jwt_secret == backend_jwt_secret, f'JWT secret mismatch between services! Auth: {auth_jwt_secret}, Backend: {backend_jwt_secret}'
            assert auth_jwt_secret == test_secret
            assert backend_jwt_secret == test_secret
            shared_secret = SharedJWTSecretManager.get_jwt_secret()
            assert auth_jwt_secret == shared_secret
            assert backend_jwt_secret == shared_secret

    def test_jwt_secret_fallback_in_development(self):
        """Test JWT secret fallback behavior in development environment."""
        env_without_jwt = {k: v for k, v in os.environ.items() if not k.startswith('JWT_SECRET')}
        env_without_jwt['ENVIRONMENT'] = 'development'
        with patch.dict(os.environ, env_without_jwt, clear=True):
            SharedJWTSecretManager.clear_cache()
            from auth_service.auth_core.config import AuthConfig
            from netra_backend.app.core.configuration.secrets import SecretManager
            from netra_backend.app.schemas.config import DevelopmentConfig
            auth_jwt_secret = AuthConfig.get_jwt_secret()
            config = DevelopmentConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            backend_jwt_secret = config.jwt_secret_key
            assert auth_jwt_secret is not None
            assert backend_jwt_secret is not None
            assert len(auth_jwt_secret) >= 32
            assert len(backend_jwt_secret) >= 32
            assert auth_jwt_secret == backend_jwt_secret, f'JWT secret fallback mismatch! Auth: {auth_jwt_secret}, Backend: {backend_jwt_secret}'

    def test_jwt_secret_production_requirements(self):
        """Test that production environment enforces JWT secret requirements."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
            SharedJWTSecretManager.clear_cache()
            with pytest.raises(ValueError, match='JWT secret is REQUIRED in production'):
                SharedJWTSecretManager.get_jwt_secret()

    def test_jwt_secret_staging_requirements(self):
        """Test that staging environment enforces JWT secret requirements."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
            SharedJWTSecretManager.clear_cache()
            with pytest.raises(ValueError, match='JWT secret is REQUIRED in staging'):
                SharedJWTSecretManager.get_jwt_secret()

    def test_shared_jwt_manager_environment_precedence(self):
        """Test SharedJWTSecretManager environment-specific precedence."""
        staging_secret = 'staging-specific-jwt-secret-32chars'
        generic_secret = 'generic-jwt-secret-for-testing-32'
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging', 'JWT_SECRET_STAGING': staging_secret, 'JWT_SECRET_KEY': generic_secret}):
            SharedJWTSecretManager.clear_cache()
            secret = SharedJWTSecretManager.get_jwt_secret()
            assert secret == staging_secret, f'Expected staging secret, got: {secret}'

    def test_backend_unified_secrets_compatibility(self):
        """Test that backend UnifiedSecrets also uses SharedJWTSecretManager."""
        test_secret = 'unified-secrets-test-jwt-32-chars'
        with patch.dict(os.environ, {'JWT_SECRET_KEY': test_secret, 'ENVIRONMENT': 'development'}):
            SharedJWTSecretManager.clear_cache()
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            unified_jwt_secret = get_jwt_secret()
            shared_jwt_secret = SharedJWTSecretManager.get_jwt_secret()
            assert unified_jwt_secret == shared_jwt_secret, f'UnifiedSecrets not using SharedJWTSecretManager: {unified_jwt_secret} != {shared_jwt_secret}'
            assert unified_jwt_secret == test_secret

class TestJWTSecretValidation:
    """Test JWT secret validation and security requirements."""

    def test_jwt_secret_minimum_length_validation(self):
        """Test that JWT secrets are validated for minimum length."""
        short_secret = 'short'
        with patch.dict(os.environ, {'JWT_SECRET_KEY': short_secret, 'ENVIRONMENT': 'production'}):
            SharedJWTSecretManager.clear_cache()
            with pytest.raises(ValueError, match='must be at least 32 characters'):
                SharedJWTSecretManager.get_jwt_secret()

    def test_jwt_secret_whitespace_handling(self):
        """Test that JWT secrets handle whitespace correctly."""
        secret_with_whitespace = '  jwt-secret-with-whitespace-32chars  '
        expected_secret = 'jwt-secret-with-whitespace-32chars'
        with patch.dict(os.environ, {'JWT_SECRET_KEY': secret_with_whitespace, 'ENVIRONMENT': 'development'}):
            SharedJWTSecretManager.clear_cache()
            secret = SharedJWTSecretManager.get_jwt_secret()
            assert secret == expected_secret, f"Whitespace not stripped: '{secret}'"

    def test_jwt_secret_caching(self):
        """Test that JWT secrets are properly cached."""
        test_secret = 'caching-test-jwt-secret-32-chars'
        with patch.dict(os.environ, {'JWT_SECRET_KEY': test_secret, 'ENVIRONMENT': 'development'}):
            SharedJWTSecretManager.clear_cache()
            secret1 = SharedJWTSecretManager.get_jwt_secret()
            secret2 = SharedJWTSecretManager.get_jwt_secret()
            assert secret1 == secret2 == test_secret
            for _ in range(5):
                secret = SharedJWTSecretManager.get_jwt_secret()
                assert secret == test_secret
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')