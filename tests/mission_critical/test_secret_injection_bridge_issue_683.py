"""
Test Secret Injection Bridge for Issue #683

This test reproduces the secret injection bridge gaps between SecretConfig and GCP deployment
that cause staging environment configuration validation failures.

Business Impact: Protects $500K+ ARR staging validation pipeline
Priority: P0 - Mission Critical

Issue #683: Staging environment configuration validation failures
Root Cause: Secret injection bridge gaps between SecretConfig configuration and actual GCP secret values
Test Strategy: Reproduce the bridge failures between config definition and runtime secret injection
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestSecretInjectionBridgeIssue683(SSotBaseTestCase):
    """
    Unit tests to reproduce secret injection bridge failures between SecretConfig and GCP deployment.

    These tests identify specific gaps in the bridge between configuration definitions
    and actual secret value injection during staging deployment.
    """

    def setup_method(self, method):
        """Set up test environment for secret injection bridge testing."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        # Store original environment to restore after test
        self.original_env = self.env.copy()

    def teardown_method(self, method):
        """Clean up test environment."""
        # Restore original environment
        for key in list(self.env._env.keys()):
            if key not in self.original_env:
                del self.env._env[key]
        for key, value in self.original_env.items():
            self.env.set(key, value)
        super().teardown_method(method)

    def test_secret_reference_to_actual_value_bridge_failure(self):
        """
        REPRODUCER: Test bridge failure between SecretReference definition and actual secret values.

        This reproduces the issue where SECRET_CONFIG defines secret references correctly,
        but the bridge to actual secret values fails during staging deployment.
        """
        # Set up staging environment
        self.env.set('ENVIRONMENT', 'staging')
        self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '701982941522')

        from netra_backend.app.schemas.config import SECRET_CONFIG, SecretReference

        # Test the bridge between SecretReference and actual secret injection
        critical_secrets = ['jwt-secret-key', 'service-secret', 'gemini-api-key']

        for secret_ref in SECRET_CONFIG:
            if secret_ref.name in critical_secrets:
                # Test that SecretReference is properly defined
                assert secret_ref.name is not None
                assert secret_ref.target_field is not None

                # BRIDGE FAILURE REPRODUCTION: Test the gap between definition and injection
                # The secret reference exists but the bridge to actual values fails

                # Test project ID resolution in SecretReference
                project_id = secret_ref.project_id
                if not project_id or project_id.strip() == '':
                    pytest.fail(f"Secret injection bridge failure: SecretReference '{secret_ref.name}' "
                              f"has empty project_id. This breaks the bridge to GCP Secret Manager.")

                # Test that the secret name mapping to environment variable is correct
                expected_env_var_mapping = {
                    'jwt-secret-key': 'JWT_SECRET_KEY',
                    'service-secret': 'SERVICE_SECRET',
                    'gemini-api-key': 'GEMINI_API_KEY'
                }

                if secret_ref.name in expected_env_var_mapping:
                    expected_env_var = expected_env_var_mapping[secret_ref.name]

                    # BRIDGE FAILURE: Environment variable not set or bridge broken
                    actual_value = self.env.get(expected_env_var)
                    if not actual_value:
                        # This represents the bridge failure - config exists but injection fails
                        pytest.fail(f"Secret injection bridge failure: SecretReference '{secret_ref.name}' "
                                  f"maps to environment variable '{expected_env_var}' but no value "
                                  f"is injected. Bridge between config and runtime is broken.")

    def test_configuration_loader_secret_injection_bridge(self):
        """
        REPRODUCER: Test configuration loader secret injection bridge failure.

        This reproduces the failure where ConfigurationLoader can load base configuration
        but fails to properly inject secrets through the bridge mechanism.
        """
        # Set up staging environment with missing secrets
        self.env.set('ENVIRONMENT', 'staging')
        self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '701982941522')

        # Clear critical secrets to simulate bridge failure
        self.env.set('JWT_SECRET_KEY', '')
        self.env.set('SERVICE_SECRET', '')

        from netra_backend.app.core.configuration.loader import ConfigurationLoader

        loader = ConfigurationLoader()

        # Test that loader exists but secret injection bridge fails
        try:
            # This should fail because the bridge between loader and secret injection is broken
            config_data = loader.load_environment_config('staging')

            # BRIDGE FAILURE CHECK: Config loads but secrets are not injected
            if hasattr(config_data, 'jwt_secret_key'):
                jwt_secret = getattr(config_data, 'jwt_secret_key', None)
                if not jwt_secret or jwt_secret.strip() == '':
                    pytest.fail("Secret injection bridge failure: ConfigurationLoader loaded config "
                              "but JWT secret was not injected through the bridge mechanism.")

            if hasattr(config_data, 'service_secret'):
                service_secret = getattr(config_data, 'service_secret', None)
                if not service_secret or service_secret.strip() == '':
                    pytest.fail("Secret injection bridge failure: ConfigurationLoader loaded config "
                              "but service secret was not injected through the bridge mechanism.")

        except Exception as e:
            # This is expected - the bridge failure should cause an exception
            assert any(keyword in str(e).lower() for keyword in ['secret', 'missing', 'injection', 'bridge'])

    def test_unified_config_manager_secret_bridge_gap(self):
        """
        REPRODUCER: Test UnifiedConfigManager secret bridge gap.

        This reproduces the gap where UnifiedConfigManager creates configuration
        but the secret injection bridge fails to populate secret values.
        """
        # Set up staging environment
        self.env.set('ENVIRONMENT', 'staging')

        # Simulate partial secret configuration - some secrets available, others missing
        self.env.set('JWT_SECRET_KEY', 'test-jwt-key')  # This one works
        self.env.set('SERVICE_SECRET', '')  # This one fails bridge
        self.env.set('GEMINI_API_KEY', '')  # This one fails bridge

        from netra_backend.app.core.configuration.base import UnifiedConfigManager

        config_manager = UnifiedConfigManager()

        # Test the secret bridge gap
        try:
            config = config_manager.get_config()

            # BRIDGE GAP: Some secrets injected, others not
            # Test that partial injection creates inconsistent state
            if hasattr(config, 'jwt_secret_key') and hasattr(config, 'service_secret'):
                jwt_secret = getattr(config, 'jwt_secret_key', None)
                service_secret = getattr(config, 'service_secret', None)

                # JWT secret should be injected
                assert jwt_secret == 'test-jwt-key', "Bridge failed for available JWT secret"

                # Service secret should fail injection
                if not service_secret or service_secret.strip() == '':
                    pytest.fail("Secret injection bridge gap: UnifiedConfigManager created config "
                              "with partial secret injection. JWT secret bridged successfully "
                              "but service secret bridge failed, creating inconsistent configuration state.")

        except Exception as e:
            # Expected failure due to bridge gap
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in ['secret', 'validation', 'missing', 'configuration'])

    def test_app_config_schema_secret_bridge_validation(self):
        """
        REPRODUCER: Test AppConfig schema secret bridge validation failure.

        This reproduces the failure where AppConfig schema validates correctly
        but the secret bridge fails to populate required fields.
        """
        from netra_backend.app.schemas.config import AppConfig

        # Set up staging environment with missing secrets
        self.env.set('ENVIRONMENT', 'staging')

        # Try to create AppConfig directly to test schema validation vs secret bridge
        try:
            # This tests if AppConfig can be created without secrets (schema validation)
            config = AppConfig(environment='staging')

            # BRIDGE VALIDATION FAILURE: Schema allows creation but secrets not bridged
            # Test critical secret fields that should be populated by bridge
            critical_fields = ['jwt_secret_key', 'service_secret']

            for field in critical_fields:
                if hasattr(config, field):
                    field_value = getattr(config, field, None)
                    if not field_value or (isinstance(field_value, str) and field_value.strip() == ''):
                        pytest.fail(f"Secret bridge validation failure: AppConfig schema allows "
                                  f"creation with empty '{field}' but secret injection bridge "
                                  f"should have populated this field for staging environment.")

        except Exception as e:
            # Expected if schema validation prevents creation without secrets
            pass

    def test_secret_manager_factory_bridge_initialization(self):
        """
        REPRODUCER: Test secret manager factory bridge initialization failure.

        This reproduces the failure where secret manager factory initializes
        but the bridge to actual secret values fails.
        """
        # Set up staging environment
        self.env.set('ENVIRONMENT', 'staging')
        self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '701982941522')

        from netra_backend.app.core.configuration.unified_secrets import get_secrets_manager

        # Test secret manager factory bridge
        try:
            secrets_manager = get_secrets_manager()

            # BRIDGE INITIALIZATION FAILURE: Manager initializes but bridge fails
            # Test that manager can be created but secret retrieval through bridge fails

            critical_secrets = ['JWT_SECRET_KEY', 'SERVICE_SECRET', 'GEMINI_API_KEY']

            for secret_key in critical_secrets:
                secret_value = secrets_manager.get_secret(secret_key)

                if not secret_value or secret_value.strip() == '':
                    # This represents the bridge failure - manager exists but bridge to values fails
                    pytest.fail(f"Secret manager factory bridge failure: SecretsManager initialized "
                              f"successfully but bridge to secret value '{secret_key}' failed. "
                              f"Factory creation succeeded but secret injection bridge is broken.")

        except Exception as e:
            # Expected failure due to bridge initialization issues
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in ['secret', 'bridge', 'initialization', 'factory'])

    def test_gcp_secret_manager_bridge_connection(self):
        """
        REPRODUCER: Test GCP Secret Manager bridge connection failure.

        This reproduces the failure where local configuration points to GCP Secret Manager
        but the bridge connection to actually retrieve secrets fails.
        """
        # Set up staging environment with GCP Secret Manager configuration
        self.env.set('ENVIRONMENT', 'staging')
        self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '701982941522')
        self.env.set('USE_GCP_SECRETS', 'true')

        from netra_backend.app.core.configuration.unified_secrets import SecretConfig, UnifiedSecretsManager

        # Test GCP Secret Manager bridge
        config = SecretConfig(
            use_gcp_secrets=True,  # Enable GCP secrets
            fallback_to_env=True,
            cache_secrets=False
        )

        secrets_manager = UnifiedSecretsManager(config)

        # BRIDGE CONNECTION FAILURE: Configuration points to GCP but connection fails
        # Mock GCP Secret Manager to simulate connection failure
        with patch('google.cloud.secretmanager.SecretManagerServiceClient') as mock_client:
            # Simulate GCP Secret Manager connection failure
            mock_client.side_effect = Exception("GCP Secret Manager connection failed")

            # Test that bridge connection failure is handled
            with pytest.raises(Exception) as exc_info:
                secret_value = secrets_manager.get_secret('JWT_SECRET_KEY')

                # If no exception, check if fallback worked
                if secret_value is None or secret_value.strip() == '':
                    raise Exception("GCP Secret Manager bridge connection failed and fallback failed")

            # Verify the error indicates bridge connection failure
            error_message = str(exc_info.value)
            assert any(keyword in error_message for keyword in ['gcp', 'connection', 'failed', 'bridge'])

    def test_secret_injection_timing_bridge_failure(self):
        """
        REPRODUCER: Test secret injection timing bridge failure.

        This reproduces the failure where secret injection happens at the wrong time
        in the configuration loading process, causing bridge failures.
        """
        # Set up staging environment
        self.env.set('ENVIRONMENT', 'staging')

        # Simulate timing-sensitive secret injection
        secrets_injected = False

        def delayed_secret_injection():
            nonlocal secrets_injected
            if not secrets_injected:
                self.env.set('JWT_SECRET_KEY', 'delayed-jwt-secret')
                self.env.set('SERVICE_SECRET', 'delayed-service-secret')
                secrets_injected = True

        from netra_backend.app.core.configuration.base import UnifiedConfigManager

        config_manager = UnifiedConfigManager()

        # Test timing bridge failure - config loaded before secrets injected
        try:
            # First try to get config before secrets are injected
            config_before = config_manager.get_config()

            # Check if config has empty secrets due to timing
            if hasattr(config_before, 'jwt_secret_key'):
                jwt_before = getattr(config_before, 'jwt_secret_key', None)
                if not jwt_before or jwt_before.strip() == '':
                    # Now inject secrets (simulating delayed injection)
                    delayed_secret_injection()

                    # Try to get config again - this tests if bridge can handle timing issues
                    config_after = config_manager.reload_config(force=True)

                    if hasattr(config_after, 'jwt_secret_key'):
                        jwt_after = getattr(config_after, 'jwt_secret_key', None)
                        if not jwt_after or jwt_after.strip() == '':
                            pytest.fail("Secret injection timing bridge failure: "
                                      "Secrets were injected after initial config load "
                                      "but bridge failed to pick up delayed injection.")

        except Exception as e:
            # Expected failure due to timing bridge issues
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in ['timing', 'injection', 'bridge', 'reload'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])