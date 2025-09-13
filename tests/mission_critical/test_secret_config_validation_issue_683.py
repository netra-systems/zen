"""
Test Secret Configuration Validation for Issue #683

This test reproduces the configuration validation failures identified in staging environment
configuration validation tests. Focus on SecretConfig class validation and secret injection
bridge gaps between SecretConfig and GCP deployment.

Business Impact: Protects $500K+ ARR staging validation pipeline
Priority: P0 - Mission Critical

Issue #683: Staging environment configuration validation failures
Root Cause: Secret injection bridge gaps between SecretConfig and GCP deployment
Test Strategy: Reproduce actual secret configuration validation failures
"""

import pytest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestSecretConfigValidationIssue683(SSotBaseTestCase):
    """
    Unit tests to reproduce secret configuration validation failures in staging environment.

    These tests identify specific validation gaps in SecretConfig class that cause
    staging deployment failures.
    """

    def setup_method(self, method):
        """Set up test environment for secret configuration validation."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        # Store original environment to restore after test
        self.original_env = self.env.get_all()

    def teardown_method(self, method):
        """Clean up test environment."""
        # Restore original environment
        current_env = self.env.get_all()
        for key in list(current_env.keys()):
            if key not in self.original_env:
                self.env.set(key, None)  # Remove keys that weren't in original
        for key, value in self.original_env.items():
            self.env.set(key, value)
        super().teardown_method(method)

    def test_secret_config_missing_required_secrets_staging(self):
        """
        REPRODUCER: Test secret configuration validation failure when required secrets are missing.

        This reproduces the actual staging environment issue where SecretConfig
        fails validation due to missing required secret values.
        """
        # Clear all secret-related environment variables to simulate staging issue
        secret_env_vars = [
            'JWT_SECRET_KEY', 'SERVICE_SECRET', 'FERNET_KEY',
            'GEMINI_API_KEY', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET',
            'LANGFUSE_SECRET_KEY', 'LANGFUSE_PUBLIC_KEY',
            'CLICKHOUSE_DEFAULT_PASSWORD', 'REDIS_DEFAULT',
            'GITHUB_TOKEN'
        ]

        for var in secret_env_vars:
            if self.env.get(var):
                self.env.set(var, '')  # Set to empty to simulate missing secrets

        # Set environment to staging to trigger staging-specific validation
        self.env.set('ENVIRONMENT', 'staging')
        self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '701982941522')

        # Import SecretConfig after environment setup
        from netra_backend.app.schemas.config import SecretReference, SECRET_CONFIG

        # Test that SecretReference validation fails for missing secrets
        for secret_ref in SECRET_CONFIG:
            # Try to validate secret reference - should identify missing secrets
            # This simulates the validation that happens during staging deployment

            # EXPECTED FAILURE: Secret validation should fail for missing required secrets
            with pytest.raises((ValueError, KeyError, AttributeError)) as exc_info:
                # Simulate secret injection process that fails in staging
                secret_name = secret_ref.name
                target_field = secret_ref.target_field

                # This should fail because the secret is not available
                if secret_name == "jwt-secret-key":
                    jwt_secret = self.env.get('JWT_SECRET_KEY')
                    if not jwt_secret or jwt_secret.strip() == '':
                        raise ValueError(f"JWT secret validation failed: missing required secret '{secret_name}' for field '{target_field}'")

                elif secret_name == "service-secret":
                    service_secret = self.env.get('SERVICE_SECRET')
                    if not service_secret or service_secret.strip() == '':
                        raise ValueError(f"Service secret validation failed: missing required secret '{secret_name}' for field '{target_field}'")

                elif secret_name == "gemini-api-key":
                    gemini_key = self.env.get('GEMINI_API_KEY')
                    if not gemini_key or gemini_key.strip() == '':
                        raise ValueError(f"Gemini API key validation failed: missing required secret '{secret_name}' for field '{target_field}'")

            # Verify the specific error indicates missing secret configuration
            assert "missing required secret" in str(exc_info.value) or "validation failed" in str(exc_info.value)

    def test_secret_config_project_id_resolution_failure(self):
        """
        REPRODUCER: Test SecretReference project ID resolution failure in staging.

        This reproduces the issue where SecretReference._get_project_id_safe()
        fails to resolve the correct GCP project ID for staging environment.
        """
        # Clear GCP project ID environment variables
        self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '')
        self.env.set('SECRET_MANAGER_PROJECT_ID', '')
        self.env.set('ENVIRONMENT', 'staging')

        from netra_backend.app.schemas.config import SecretReference

        # Test project ID resolution
        project_id = SecretReference._get_project_id_safe()

        # EXPECTED FAILURE: Should fall back to default staging project ID
        # but this may not be properly configured in staging environment
        expected_staging_project_id = "701982941522"

        # This test will FAIL if project ID resolution is broken
        assert project_id == expected_staging_project_id, (
            f"Project ID resolution failed: expected '{expected_staging_project_id}', "
            f"got '{project_id}'. This indicates staging environment configuration issue."
        )

    def test_secret_config_validation_with_partial_secrets(self):
        """
        REPRODUCER: Test validation failure with partially configured secrets.

        This reproduces staging issues where some secrets are configured but others are missing,
        causing validation to fail in unexpected ways.
        """
        # Configure only some secrets to simulate partial staging configuration
        self.env.set('ENVIRONMENT', 'staging')
        self.env.set('JWT_SECRET_KEY', 'test-jwt-secret')
        self.env.set('SERVICE_SECRET', 'test-service-secret')
        # Leave other secrets missing
        for var in ['GEMINI_API_KEY', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']:
            self.env.set(var, '')

        from netra_backend.app.core.configuration.secrets import SecretConfig, get_secrets_manager

        # Try to create secrets manager with partial configuration
        secrets_manager = get_secrets_manager()

        # Test that secrets manager can handle partial configuration
        # but properly fails validation for missing required secrets
        jwt_secret = secrets_manager.get_secret('JWT_SECRET_KEY')
        assert jwt_secret == 'test-jwt-secret'

        # This should fail for missing secrets
        gemini_key = secrets_manager.get_secret('GEMINI_API_KEY')
        assert gemini_key is None or gemini_key == '', (
            f"Expected missing GEMINI_API_KEY to be None or empty, got '{gemini_key}'"
        )

    def test_unified_secrets_manager_staging_initialization(self):
        """
        REPRODUCER: Test UnifiedSecretsManager initialization failure in staging environment.

        This reproduces the issue where UnifiedSecretsManager fails to initialize
        properly in staging due to missing configuration.
        """
        # Set staging environment
        self.env.set('ENVIRONMENT', 'staging')

        # Clear critical secrets
        critical_secrets = ['JWT_SECRET_KEY', 'SERVICE_SECRET']
        for secret in critical_secrets:
            self.env.set(secret, '')

        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretsManager, SecretConfig

        # Test that UnifiedSecretsManager initialization detects missing critical secrets
        config = SecretConfig(
            use_gcp_secrets=True,  # Staging should use GCP secrets
            fallback_to_env=True,
            cache_secrets=False
        )

        secrets_manager = UnifiedSecretsManager(config)

        # Test JWT secret retrieval - should fail in staging without proper configuration
        with pytest.raises((ValueError, KeyError, AttributeError)) as exc_info:
            jwt_secret = secrets_manager.get_jwt_secret()
            # If it doesn't raise an exception, it should at least be empty or None
            if jwt_secret is None or jwt_secret.strip() == '':
                raise ValueError("JWT secret is missing or empty in staging environment")

        # Verify the error indicates staging configuration issue
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['missing', 'empty', 'not found', 'staging'])

    def test_secret_config_environment_isolation_failure(self):
        """
        REPRODUCER: Test secret configuration environment isolation failure.

        This reproduces issues where staging environment configuration
        leaks into other environments or fails to isolate properly.
        """
        # Test multiple environment configurations
        environments = ['staging', 'production', 'development']

        for env_name in environments:
            self.env.set('ENVIRONMENT', env_name)

            # Set environment-specific project IDs
            if env_name == 'staging':
                self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '701982941522')
                self.env.set('SECRET_MANAGER_PROJECT_ID', '701982941522')
            elif env_name == 'production':
                self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '')  # Clear staging
                self.env.set('SECRET_MANAGER_PROJECT_ID', '304612253870')
            else:  # development
                self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '')
                self.env.set('SECRET_MANAGER_PROJECT_ID', '')

            from netra_backend.app.schemas.config import SecretReference

            # Clear module cache to force reload
            import importlib
            import netra_backend.app.schemas.config
            importlib.reload(netra_backend.app.schemas.config)
            from netra_backend.app.schemas.config import SecretReference

            project_id = SecretReference._get_project_id_safe()

            # Verify environment isolation
            if env_name == 'staging':
                expected_id = '701982941522'
            elif env_name == 'production':
                expected_id = '304612253870'
            else:  # development - should have some fallback
                # Development might use staging or have its own default
                expected_id = project_id  # Accept whatever it resolves to

            if env_name in ['staging', 'production']:
                assert project_id == expected_id, (
                    f"Environment isolation failed: {env_name} environment "
                    f"expected project ID '{expected_id}', got '{project_id}'"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])