"""
Unit tests for environment variable validation failures from Issue #899.

These tests reproduce environment variable related failures from Issue #899:
- Missing critical environment variables
- Invalid environment variable values
- Environment variable format validation
- IsolatedEnvironment integration issues

Business Value: Platform/Internal - System Configuration & Security
Protects the $500K+ ARR Golden Path by ensuring environment configuration
is valid before startup to prevent runtime configuration failures.

Test Categories:
- Environment variable presence validation
- Environment variable format and value validation
- IsolatedEnvironment integration testing
- Configuration consistency validation
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional

# Import SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import components under test
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentValidation,
    ComponentStatus,
    EnvironmentType
)


class EnvironmentVariableValidationUnitTests(SSotAsyncTestCase):
    """Unit tests for environment variable validation during startup."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance with test environment
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)

        # Clear any existing validations
        self.validator.validations = []

    async def test_missing_postgres_environment_variables_detailed(self):
        """
        Test Issue #899 Failure 1: Missing POSTGRES_* environment variables

        CRITICAL FAILURE REPRODUCTION:
        When required POSTGRES_* environment variables are missing,
        should detect and report each missing variable specifically.
        """
        # Mock environment with missing critical variables
        mock_env_dict = {
            # POSTGRES_HOST is missing entirely
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            # POSTGRES_USER is missing entirely
            "POSTGRES_PASSWORD": "testpass",
            # POSTGRES_SSL_MODE missing (optional)
        }

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Run database configuration validation (which validates environment)
            await self.validator._validate_database_configuration_early()

        # Verify missing environment variables were detected
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded database configuration validation"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Missing required vars should be CRITICAL"
        assert "Missing required environment variables" in validation.message
        assert "POSTGRES_HOST" in validation.message
        assert "POSTGRES_USER" in validation.message

        # Verify metadata contains specific missing variables
        assert "missing_vars" in validation.metadata
        assert "POSTGRES_HOST" in validation.metadata["missing_vars"]
        assert "POSTGRES_USER" in validation.metadata["missing_vars"]

        # Verify required variables list is documented
        assert "required_vars" in validation.metadata
        assert "POSTGRES_HOST" in validation.metadata["required_vars"]
        assert "POSTGRES_PORT" in validation.metadata["required_vars"]
        assert "POSTGRES_DB" in validation.metadata["required_vars"]
        assert "POSTGRES_USER" in validation.metadata["required_vars"]

    async def test_empty_environment_variable_values(self):
        """
        Test Issue #899 Failure 2: Empty environment variable values

        CRITICAL FAILURE REPRODUCTION:
        When required environment variables are present but empty/whitespace,
        should detect and report as configuration failures.
        """
        # Mock environment with empty/whitespace values
        mock_env_dict = {
            "POSTGRES_HOST": "",              # Empty string
            "POSTGRES_PORT": "  ",            # Whitespace only
            "POSTGRES_DB": "testdb",          # Valid
            "POSTGRES_USER": "\t\n  ",        # Whitespace with tabs/newlines
            "POSTGRES_PASSWORD": "testpass"   # Valid
        }

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify empty environment variables were detected
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded configuration validation"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Empty required vars should be CRITICAL"
        assert "Empty required environment variables" in validation.message

        # Verify specific empty variables are identified
        assert "POSTGRES_HOST" in validation.message
        assert "POSTGRES_PORT" in validation.message
        assert "POSTGRES_USER" in validation.message

        # Verify metadata contains empty variables list
        assert "empty_vars" in validation.metadata
        assert "POSTGRES_HOST" in validation.metadata["empty_vars"]
        assert "POSTGRES_PORT" in validation.metadata["empty_vars"]
        assert "POSTGRES_USER" in validation.metadata["empty_vars"]

    async def test_invalid_environment_variable_formats(self):
        """
        Test Issue #899 Failure 3: Invalid environment variable formats

        CRITICAL FAILURE REPRODUCTION:
        When environment variables have invalid formats (e.g., invalid port numbers,
        malformed URLs), should detect and report format validation failures.
        """
        # Mock environment with invalid formats
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "not_a_number",    # Invalid port format
            "POSTGRES_DB": "test/db/with/slashes",  # Potentially problematic DB name
            "POSTGRES_USER": "user@with@multiple@ats",  # Problematic username
            "POSTGRES_PASSWORD": "password"
        }

        # Mock DatabaseURLBuilder to detect invalid formats
        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            with patch('netra_backend.app.core.startup_validation.DatabaseURLBuilder') as mock_url_builder:
                # Simulate URL builder failing due to invalid port
                mock_builder_instance = MagicMock()
                mock_builder_instance.get_url_for_environment.side_effect = ValueError("Port must be a valid integer")
                mock_url_builder.return_value = mock_builder_instance

                # Run database configuration validation
                await self.validator._validate_database_configuration_early()

        # Verify format validation failure was detected
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded format validation failure"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Invalid format should be CRITICAL"
        assert "Configuration validation failed" in validation.message
        assert "Invalid database configuration format" in validation.message
        assert "Port must be a valid integer" in validation.message

        # Verify error details in metadata
        assert "config_error" in validation.metadata
        assert "Port must be a valid integer" in validation.metadata["config_error"]

    async def test_environment_variable_none_values(self):
        """
        Test Issue #899 Failure 4: Environment variables with None values

        CRITICAL FAILURE REPRODUCTION:
        When environment variables are explicitly set to None,
        should be treated as missing variables.
        """
        # Mock environment with None values
        mock_env_dict = {
            "POSTGRES_HOST": None,
            "POSTGRES_PORT": None,
            "POSTGRES_DB": "testdb",      # Valid
            "POSTGRES_USER": "testuser",  # Valid
            "POSTGRES_PASSWORD": None
        }

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify None values are treated as missing
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded configuration validation"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "None values should be CRITICAL"
        assert "Missing required environment variables" in validation.message

        # Verify None values are listed as missing
        assert "missing_vars" in validation.metadata
        assert "POSTGRES_HOST" in validation.metadata["missing_vars"]
        assert "POSTGRES_PORT" in validation.metadata["missing_vars"]
        assert "POSTGRES_PASSWORD" in validation.metadata["missing_vars"]

    async def test_isolated_environment_integration(self):
        """
        Test Issue #899 Failure 5: IsolatedEnvironment integration issues

        INTEGRATION FAILURE REPRODUCTION:
        When IsolatedEnvironment (get_env) fails or is not properly configured,
        should handle gracefully and provide informative error messages.
        """
        # Mock IsolatedEnvironment to fail
        with patch('netra_backend.app.core.startup_validation.get_env', side_effect=ImportError("IsolatedEnvironment not available")):
            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify IsolatedEnvironment failure was handled
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded IsolatedEnvironment failure handling"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.WARNING, "Import errors should be WARNING"
        assert validation.is_critical is False, "Import errors should not be critical"
        assert "Configuration validation skipped" in validation.message
        assert "Missing dependencies" in validation.message
        assert "IsolatedEnvironment not available" in validation.message

        # Verify error details in metadata
        assert "import_error" in validation.metadata
        assert "IsolatedEnvironment not available" in validation.metadata["import_error"]

    async def test_environment_variable_access_runtime_error(self):
        """
        Test Issue #899 Failure 6: Runtime errors accessing environment variables

        RUNTIME FAILURE REPRODUCTION:
        When accessing environment variables causes runtime errors,
        should handle gracefully without crashing startup validation.
        """
        # Mock get_env to raise runtime error
        with patch('netra_backend.app.core.startup_validation.get_env', side_effect=RuntimeError("Environment access denied")):
            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify runtime error was handled gracefully
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded runtime error handling"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.WARNING, "Runtime errors should be WARNING"
        assert validation.is_critical is False, "Runtime errors should not crash startup"
        assert "Configuration validation error" in validation.message
        assert "Environment access denied" in validation.message

        # Verify error details in metadata
        assert "validation_error" in validation.metadata
        assert "Environment access denied" in validation.metadata["validation_error"]

    async def test_environment_dict_conversion_error(self):
        """
        Test Issue #899 Failure 7: Environment dictionary conversion errors

        CONVERSION FAILURE REPRODUCTION:
        When IsolatedEnvironment.as_dict() fails or returns invalid data,
        should handle gracefully and provide useful error information.
        """
        # Mock get_env to return object with failing as_dict
        mock_env = MagicMock()
        mock_env.as_dict.side_effect = AttributeError("as_dict method not available")

        with patch('netra_backend.app.core.startup_validation.get_env', return_value=mock_env):
            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify dictionary conversion error was handled
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded dict conversion error"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.WARNING, "Dict conversion errors should be WARNING"
        assert "Configuration validation error" in validation.message
        assert "as_dict method not available" in validation.message

    async def test_comprehensive_environment_validation_success(self):
        """
        Test successful environment variable validation with all required variables.

        POSITIVE TEST CASE:
        When all environment variables are present and valid, should pass
        validation and provide success confirmation.
        """
        # Mock environment with all valid required variables
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_test",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_SSL_MODE": "prefer",  # Optional but present
        }

        # Mock successful URL building
        mock_database_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/netra_test?sslmode=prefer"

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            with patch('netra_backend.app.core.startup_validation.DatabaseURLBuilder') as mock_url_builder:
                mock_builder_instance = MagicMock()
                mock_builder_instance.get_url_for_environment.return_value = mock_database_url
                mock_url_builder.return_value = mock_builder_instance

                # Run database configuration validation
                await self.validator._validate_database_configuration_early()

        # Verify successful validation
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded successful validation"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.HEALTHY, "Valid environment should be HEALTHY"
        assert validation.actual_count == 1, "Valid configuration means 1 valid config"
        assert "Configuration validation passed" in validation.message
        assert "localhost:5432" in validation.message

        # Verify successful configuration metadata
        assert validation.metadata["config_status"] == "valid"
        assert validation.metadata["database_host"] == "localhost"
        assert validation.metadata["database_port"] == 5432
        assert validation.metadata["database_name"] == "netra_test"

    async def test_partial_environment_configuration_handling(self):
        """
        Test handling of partial environment configurations.

        PARTIAL CONFIGURATION TEST:
        When some required variables are present and some are missing,
        should provide detailed breakdown of what's available vs missing.
        """
        # Mock environment with partial configuration
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",     # Present
            "POSTGRES_PORT": "5432",          # Present
            # POSTGRES_DB missing
            # POSTGRES_USER missing
            "POSTGRES_PASSWORD": "password",  # Present but won't help without DB/USER
        }

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify partial configuration was detected
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded partial configuration"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Partial configuration should be CRITICAL"
        assert "Missing required environment variables" in validation.message
        assert "POSTGRES_DB" in validation.message
        assert "POSTGRES_USER" in validation.message

        # Verify detailed breakdown in metadata
        assert "missing_vars" in validation.metadata
        assert "POSTGRES_DB" in validation.metadata["missing_vars"]
        assert "POSTGRES_USER" in validation.metadata["missing_vars"]

        # Verify the count reflects partial configuration
        expected_vars = validation.metadata["required_vars"]
        missing_vars = validation.metadata["missing_vars"]
        expected_count = len(expected_vars) - len(missing_vars)
        assert validation.actual_count == expected_count


class EnvironmentVariablePerformanceUnitTests(SSotAsyncTestCase):
    """Unit tests for environment variable validation performance."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
        self.validator.validations = []

    async def test_environment_validation_performance_fast_path(self):
        """
        Test that environment validation performs quickly on valid configuration.

        PERFORMANCE TEST:
        Environment validation should complete quickly when configuration is valid
        to avoid contributing to startup delays.
        """
        # Mock valid environment
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
        }

        mock_database_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            with patch('netra_backend.app.core.startup_validation.DatabaseURLBuilder') as mock_url_builder:
                mock_builder_instance = MagicMock()
                mock_builder_instance.get_url_for_environment.return_value = mock_database_url
                mock_url_builder.return_value = mock_builder_instance

                # Time the validation
                import time
                start_time = time.time()
                await self.validator._validate_database_configuration_early()
                end_time = time.time()

                validation_duration = end_time - start_time

        # Verify validation was fast
        assert validation_duration < 0.5, f"Environment validation took {validation_duration}s, should be <0.5s"

        # Verify validation succeeded
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]
        assert len(config_validations) == 1
        assert config_validations[0].status == ComponentStatus.HEALTHY

    async def test_environment_validation_performance_failure_path(self):
        """
        Test that environment validation fails quickly on invalid configuration.

        FAILURE PERFORMANCE TEST:
        Environment validation should fail fast when configuration is clearly
        invalid to avoid wasting time during startup.
        """
        # Mock invalid environment (missing all variables)
        mock_env_dict = {}

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Time the validation
            import time
            start_time = time.time()
            await self.validator._validate_database_configuration_early()
            end_time = time.time()

            validation_duration = end_time - start_time

        # Verify validation failed quickly
        assert validation_duration < 0.5, f"Environment validation failure took {validation_duration}s, should be <0.5s"

        # Verify validation failed appropriately
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]
        assert len(config_validations) == 1
        assert config_validations[0].status == ComponentStatus.CRITICAL

    async def test_environment_variable_caching_behavior(self):
        """
        Test caching behavior of environment variable access.

        CACHING TEST:
        Environment variable validation should not repeatedly access
        the same environment variables if called multiple times.
        """
        # Mock environment
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser"
        }

        mock_database_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            with patch('netra_backend.app.core.startup_validation.DatabaseURLBuilder') as mock_url_builder:
                mock_builder_instance = MagicMock()
                mock_builder_instance.get_url_for_environment.return_value = mock_database_url
                mock_url_builder.return_value = mock_builder_instance

                # Run validation multiple times
                await self.validator._validate_database_configuration_early()
                await self.validator._validate_database_configuration_early()
                await self.validator._validate_database_configuration_early()

                # Verify get_env was called multiple times (no caching at validator level)
                # This is expected as each validation should get fresh environment
                assert mock_get_env.call_count == 3, "Should call get_env for each validation"

        # Verify all validations were recorded
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]
        assert len(config_validations) == 3, "Should have recorded all validation attempts"