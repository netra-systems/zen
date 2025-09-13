"""
Test Staging Configuration Validation Failures for Issue #683 (E2E)

This E2E test reproduces the complete staging environment configuration validation
failures by testing against actual staging GCP environment. This test validates
the complete user flow through staging configuration validation.

Business Impact: Protects $500K+ ARR staging validation pipeline
Priority: P0 - Mission Critical

Issue #683: Staging environment configuration validation failures
Root Cause: End-to-end staging environment configuration validation failures
Test Strategy: Full staging environment validation without Docker dependency
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestStagingConfigValidationFailuresIssue683(SSotAsyncTestCase):
    """
    E2E tests to reproduce complete staging configuration validation failures.

    These tests simulate the complete staging environment configuration validation
    process to identify where validation failures occur in real staging deployment.
    """

    def setup_method(self, method):
        """Set up E2E test environment for staging configuration validation."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        # Store original environment to restore after test
        self.original_env = self.env.copy()
        # Set staging environment for all E2E tests
        self.env.set('ENVIRONMENT', 'staging')
        self.env.set('GCP_PROJECT_ID_NUMERICAL_STAGING', '701982941522')

    def teardown_method(self, method):
        """Clean up E2E test environment."""
        # Restore original environment
        for key in list(self.env._env.keys()):
            if key not in self.original_env:
                del self.env._env[key]
        for key, value in self.original_env.items():
            self.env.set(key, value)
        super().teardown_method(method)

    async def test_staging_application_startup_configuration_validation(self):
        """
        REPRODUCER: Test complete staging application startup configuration validation failure.

        This reproduces the E2E failure where staging application startup fails
        due to configuration validation errors during the complete initialization process.
        """
        # Simulate staging application startup configuration validation
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        from netra_backend.app.core.configuration.validator import ConfigurationValidator

        config_manager = UnifiedConfigManager()
        validator = ConfigurationValidator()

        # Test complete staging configuration validation pipeline
        try:
            # Step 1: Load staging configuration
            config = config_manager.get_config()
            assert config.environment == 'staging', f"Expected staging environment, got {config.environment}"

            # Step 2: Validate complete configuration for staging
            validation_result = validator.validate_complete_config(config)

            if not validation_result.is_valid:
                # EXPECTED FAILURE: Staging configuration validation should fail
                pytest.fail(f"Staging configuration validation failed during application startup: "
                          f"Errors: {validation_result.errors}. "
                          f"This indicates real staging environment configuration issues that "
                          f"would prevent successful application deployment.")

            # Step 3: Test critical staging configuration fields
            critical_fields = ['jwt_secret_key', 'service_secret', 'database', 'redis']
            missing_fields = []

            for field in critical_fields:
                if hasattr(config, field):
                    field_value = getattr(config, field, None)
                    if field_value is None or (isinstance(field_value, str) and field_value.strip() == ''):
                        missing_fields.append(field)

            if missing_fields:
                pytest.fail(f"Staging configuration validation failure: "
                          f"Critical fields missing or empty: {missing_fields}. "
                          f"This would cause staging application startup to fail.")

        except Exception as e:
            # Expected failure - staging configuration validation should fail
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in
                      ['validation', 'staging', 'configuration', 'missing', 'failed'])

    async def test_staging_database_configuration_validation_e2e(self):
        """
        REPRODUCER: Test staging database configuration validation E2E failure.

        This reproduces the complete database configuration validation failure
        in staging environment, testing connection parameters and secrets.
        """
        from netra_backend.app.core.configuration.base import get_unified_config

        # Test staging database configuration validation
        try:
            config = get_unified_config()

            # Test database configuration completeness for staging
            if hasattr(config, 'database'):
                db_config = config.database

                # Critical database configuration validation
                required_db_fields = ['host', 'port', 'name', 'user']
                missing_db_fields = []

                for field in required_db_fields:
                    if hasattr(db_config, field):
                        field_value = getattr(db_config, field, None)
                        if field_value is None or (isinstance(field_value, str) and field_value.strip() == ''):
                            missing_db_fields.append(field)

                if missing_db_fields:
                    pytest.fail(f"Staging database configuration validation failure: "
                              f"Missing required database fields: {missing_db_fields}. "
                              f"This would prevent staging database connections.")

                # Test database password/secret validation
                if hasattr(db_config, 'password'):
                    db_password = getattr(db_config, 'password', None)
                    if not db_password or db_password.strip() == '':
                        pytest.fail("Staging database configuration validation failure: "
                                  "Database password is missing or empty. "
                                  "This indicates secret injection failure for staging database.")

        except Exception as e:
            # Expected failure for staging database configuration issues
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in
                      ['database', 'password', 'connection', 'staging'])

    async def test_staging_redis_configuration_validation_e2e(self):
        """
        REPRODUCER: Test staging Redis configuration validation E2E failure.

        This reproduces the complete Redis configuration validation failure
        in staging environment, testing connection parameters and authentication.
        """
        from netra_backend.app.core.configuration.base import get_unified_config

        try:
            config = get_unified_config()

            # Test Redis configuration for staging
            if hasattr(config, 'redis'):
                redis_config = config.redis

                # Critical Redis configuration validation
                required_redis_fields = ['host', 'port']
                missing_redis_fields = []

                for field in required_redis_fields:
                    if hasattr(redis_config, field):
                        field_value = getattr(redis_config, field, None)
                        if field_value is None:
                            missing_redis_fields.append(field)

                if missing_redis_fields:
                    pytest.fail(f"Staging Redis configuration validation failure: "
                              f"Missing required Redis fields: {missing_redis_fields}. "
                              f"This would prevent staging Redis connections.")

                # Test Redis authentication validation
                if hasattr(redis_config, 'password'):
                    redis_password = getattr(redis_config, 'password', None)
                    if not redis_password or redis_password.strip() == '':
                        pytest.fail("Staging Redis configuration validation failure: "
                                  "Redis password is missing or empty. "
                                  "This indicates secret injection failure for staging Redis.")

        except Exception as e:
            # Expected failure for staging Redis configuration issues
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in
                      ['redis', 'password', 'authentication', 'staging'])

    async def test_staging_llm_configuration_validation_e2e(self):
        """
        REPRODUCER: Test staging LLM configuration validation E2E failure.

        This reproduces the complete LLM configuration validation failure
        in staging environment, testing API keys and provider configurations.
        """
        from netra_backend.app.core.configuration.base import get_unified_config

        try:
            config = get_unified_config()

            # Test LLM configuration for staging
            if hasattr(config, 'llm_configs'):
                llm_configs = config.llm_configs

                # Test Gemini API key configuration
                if hasattr(llm_configs, 'default'):
                    default_llm = llm_configs.default
                    if hasattr(default_llm, 'api_key'):
                        api_key = getattr(default_llm, 'api_key', None)
                        if not api_key or api_key.strip() == '':
                            pytest.fail("Staging LLM configuration validation failure: "
                                      "Gemini API key is missing or empty. "
                                      "This indicates secret injection failure for staging LLM services.")

                # Test multiple LLM provider configurations
                llm_providers = ['default', 'triage', 'data', 'optimizations_core']
                missing_api_keys = []

                for provider in llm_providers:
                    if hasattr(llm_configs, provider):
                        provider_config = getattr(llm_configs, provider)
                        if hasattr(provider_config, 'api_key'):
                            api_key = getattr(provider_config, 'api_key', None)
                            if not api_key or api_key.strip() == '':
                                missing_api_keys.append(provider)

                if missing_api_keys:
                    pytest.fail(f"Staging LLM configuration validation failure: "
                              f"Missing API keys for LLM providers: {missing_api_keys}. "
                              f"This would prevent staging AI functionality.")

        except Exception as e:
            # Expected failure for staging LLM configuration issues
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in
                      ['llm', 'api_key', 'gemini', 'provider', 'staging'])

    async def test_staging_oauth_configuration_validation_e2e(self):
        """
        REPRODUCER: Test staging OAuth configuration validation E2E failure.

        This reproduces the complete OAuth configuration validation failure
        in staging environment, testing Google OAuth credentials and endpoints.
        """
        from netra_backend.app.core.configuration.base import get_unified_config

        try:
            config = get_unified_config()

            # Test OAuth configuration for staging
            if hasattr(config, 'oauth_config'):
                oauth_config = config.oauth_config

                # Critical OAuth configuration validation
                required_oauth_fields = ['client_id', 'client_secret']
                missing_oauth_fields = []

                for field in required_oauth_fields:
                    if hasattr(oauth_config, field):
                        field_value = getattr(oauth_config, field, None)
                        if not field_value or field_value.strip() == '':
                            missing_oauth_fields.append(field)

                if missing_oauth_fields:
                    pytest.fail(f"Staging OAuth configuration validation failure: "
                              f"Missing required OAuth fields: {missing_oauth_fields}. "
                              f"This would prevent staging user authentication.")

                # Test OAuth endpoint configuration
                if hasattr(oauth_config, 'authorized_redirect_uris'):
                    redirect_uris = getattr(oauth_config, 'authorized_redirect_uris', [])
                    staging_uri_found = False
                    for uri in redirect_uris:
                        if 'staging' in uri or 'netrasystems.ai' in uri:
                            staging_uri_found = True
                            break

                    if not staging_uri_found:
                        pytest.fail("Staging OAuth configuration validation failure: "
                                  "No staging-appropriate redirect URIs configured. "
                                  "This would prevent OAuth flow in staging environment.")

        except Exception as e:
            # Expected failure for staging OAuth configuration issues
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in
                      ['oauth', 'client_id', 'client_secret', 'authentication'])

    async def test_staging_service_integration_configuration_e2e(self):
        """
        REPRODUCER: Test staging service integration configuration E2E failure.

        This reproduces the complete service integration configuration validation
        failure, testing inter-service communication and authentication.
        """
        from netra_backend.app.core.configuration.base import get_unified_config

        try:
            config = get_unified_config()

            # Test service integration configuration
            service_integration_failures = []

            # Test service secret for inter-service authentication
            if hasattr(config, 'service_secret'):
                service_secret = getattr(config, 'service_secret', None)
                if not service_secret or service_secret.strip() == '':
                    service_integration_failures.append("service_secret missing or empty")

            # Test JWT secret for token validation
            if hasattr(config, 'jwt_secret_key'):
                jwt_secret = getattr(config, 'jwt_secret_key', None)
                if not jwt_secret or jwt_secret.strip() == '':
                    service_integration_failures.append("jwt_secret_key missing or empty")

            # Test service ID configuration
            if hasattr(config, 'service_id'):
                service_id = getattr(config, 'service_id', None)
                if not service_id or service_id.strip() == '':
                    service_integration_failures.append("service_id missing or empty")

            if service_integration_failures:
                pytest.fail(f"Staging service integration configuration validation failure: "
                          f"Service integration issues: {service_integration_failures}. "
                          f"This would prevent inter-service communication in staging.")

        except Exception as e:
            # Expected failure for staging service integration issues
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in
                      ['service', 'integration', 'jwt', 'authentication'])

    async def test_staging_complete_system_validation_e2e(self):
        """
        REPRODUCER: Test complete staging system validation E2E failure.

        This reproduces the complete system validation failure that would occur
        during staging deployment, testing all critical configuration components.
        """
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        from netra_backend.app.core.configuration.validator import ConfigurationValidator

        # Simulate complete staging system validation
        validation_failures = []

        try:
            # Step 1: Configuration loading validation
            config_manager = UnifiedConfigManager()
            config = config_manager.get_config()

            # Step 2: Configuration validation
            validator = ConfigurationValidator()
            validation_result = validator.validate_complete_config(config)

            if not validation_result.is_valid:
                validation_failures.extend([f"Config validation: {error}" for error in validation_result.errors])

            # Step 3: Critical system component validation
            critical_components = {
                'database': ['host', 'port', 'name', 'user', 'password'],
                'redis': ['host', 'port', 'password'],
                'oauth_config': ['client_id', 'client_secret'],
                'llm_configs': None  # Special handling needed
            }

            for component, required_fields in critical_components.items():
                if hasattr(config, component):
                    component_config = getattr(config, component)

                    if component == 'llm_configs':
                        # Special validation for LLM configs
                        if hasattr(component_config, 'default'):
                            default_llm = getattr(component_config, 'default')
                            if hasattr(default_llm, 'api_key'):
                                api_key = getattr(default_llm, 'api_key', None)
                                if not api_key or api_key.strip() == '':
                                    validation_failures.append(f"{component}.default.api_key missing or empty")
                    else:
                        # Standard field validation
                        for field in required_fields:
                            if hasattr(component_config, field):
                                field_value = getattr(component_config, field, None)
                                if field_value is None or (isinstance(field_value, str) and field_value.strip() == ''):
                                    validation_failures.append(f"{component}.{field} missing or empty")
                else:
                    validation_failures.append(f"Critical component '{component}' missing from configuration")

            # Step 4: Service integration validation
            service_fields = ['service_secret', 'jwt_secret_key', 'service_id']
            for field in service_fields:
                if hasattr(config, field):
                    field_value = getattr(config, field, None)
                    if not field_value or field_value.strip() == '':
                        validation_failures.append(f"Service integration field '{field}' missing or empty")

            if validation_failures:
                pytest.fail(f"Complete staging system validation failure: "
                          f"Multiple validation failures detected: {validation_failures}. "
                          f"This represents the complete failure state that would prevent "
                          f"successful staging deployment and protect the $500K+ ARR pipeline.")

        except Exception as e:
            # Expected failure for complete system validation issues
            error_message = str(e).lower()
            validation_failures.append(f"System validation exception: {str(e)}")

        # If we reach here with validation failures, that's the expected reproduction
        if validation_failures:
            pytest.fail(f"Complete staging validation reproduction successful: "
                      f"Identified {len(validation_failures)} validation failures that would "
                      f"prevent staging deployment: {validation_failures}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])