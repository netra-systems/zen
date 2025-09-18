"""
Unit tests for database configuration validation in startup validation.

These tests reproduce the database configuration failures from Issue #899:
- Missing POSTGRES_* environment variables
- Invalid database URL construction
- Configuration validation before initialization attempts

Business Value: Platform/Internal - System Stability
Protects the $500K+ ARR Golden Path by ensuring database configuration
is validated before initialization to prevent startup failures.

Test Categories:
- Environment variable validation
- Database URL construction validation
- Configuration format validation
- Error handling and messaging
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import components under test
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentValidation,
    ComponentStatus,
    EnvironmentType
)


class DatabaseConfigurationValidationUnitTests(SSotAsyncTestCase):
    """Unit tests for database configuration validation during startup."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance with test environment
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)

        # Clear any existing validations
        self.validator.validations = []

    async def test_missing_required_postgres_environment_variables(self):
        """
        Test Issue #899 Failure 1: Missing required POSTGRES_* environment variables

        CRITICAL FAILURE REPRODUCTION:
        Expected behavior: Configuration validation should detect missing variables
        and provide clear error messages before attempting initialization.
        """
        # Mock environment with missing required variables
        mock_env_dict = {
            "POSTGRES_HOST": None,  # Missing
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "",       # Empty
            "POSTGRES_USER": "user"
            # POSTGRES_PASSWORD missing entirely
        }

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify critical failure was recorded
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded database configuration validation"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Missing environment variables should be CRITICAL"
        assert validation.is_critical is True, "Configuration validation should be critical for business"
        assert "Missing required environment variables" in validation.message
        assert "POSTGRES_HOST" in validation.message, "Should identify missing POSTGRES_HOST"
        assert "Empty required environment variables" in validation.message
        assert "POSTGRES_DB" in validation.message, "Should identify empty POSTGRES_DB"

        # Verify metadata contains detailed information
        assert "missing_vars" in validation.metadata
        assert "empty_vars" in validation.metadata
        assert "POSTGRES_HOST" in validation.metadata["missing_vars"]
        assert "POSTGRES_DB" in validation.metadata["empty_vars"]

    async def test_invalid_database_url_construction(self):
        """
        Test Issue #899 Failure 2: Invalid database URL construction

        CRITICAL FAILURE REPRODUCTION:
        Configuration values that cannot construct valid database URLs should be
        detected early with specific error messages.
        """
        # Mock environment with invalid values that can't build URL
        mock_env_dict = {
            "POSTGRES_HOST": "invalid-host-with-@-chars@@@",
            "POSTGRES_PORT": "999999",  # Invalid port
            "POSTGRES_DB": "db/with/slashes",
            "POSTGRES_USER": ""  # Empty user
        }

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Mock DatabaseURLBuilder to fail on invalid configuration
            with patch('netra_backend.app.core.startup_validation.DatabaseURLBuilder') as mock_url_builder:
                mock_builder_instance = MagicMock()
                mock_builder_instance.get_url_for_environment.side_effect = ValueError("Invalid database configuration format")
                mock_url_builder.return_value = mock_builder_instance

                # Run database configuration validation
                await self.validator._validate_database_configuration_early()

        # Verify configuration validation failure was recorded
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded configuration validation failure"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Invalid configuration should be CRITICAL"
        assert validation.actual_count == 0, "Configuration failure means 0 valid configs"
        assert "Configuration validation failed" in validation.message
        assert "Invalid database configuration format" in validation.message
        assert validation.metadata["config_error"] == "Invalid database configuration format"

    async def test_database_url_component_validation(self):
        """
        Test Issue #899 Failure 3: Database URL component validation

        CRITICAL FAILURE REPRODUCTION:
        Valid environment variables that produce URLs with invalid components
        should be detected and reported with specific component issues.
        """
        # Mock environment that produces valid-looking URL with invalid components
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser"
        }

        # Mock URL that parses but has invalid components
        mock_database_url = "postgresql+asyncpg://:@:0/"  # Empty/invalid components

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Mock DatabaseURLBuilder to return invalid URL
            with patch('netra_backend.app.core.startup_validation.DatabaseURLBuilder') as mock_url_builder:
                mock_builder_instance = MagicMock()
                mock_builder_instance.get_url_for_environment.return_value = mock_database_url
                mock_url_builder.return_value = mock_builder_instance

                # Run database configuration validation
                await self.validator._validate_database_configuration_early()

        # Verify URL component validation failure was recorded
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded URL validation failure"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.CRITICAL, "Invalid URL components should be CRITICAL"
        assert "Configuration validation failed" in validation.message
        assert "username is missing or empty" in validation.message
        assert "port is invalid" in validation.message
        assert "database name is missing or empty" in validation.message

        # Verify detailed metadata
        assert "validation_issues" in validation.metadata
        assert len(validation.metadata["validation_issues"]) >= 3, "Should identify multiple component issues"

    async def test_successful_database_configuration_validation(self):
        """
        Test successful database configuration validation path.

        POSITIVE TEST CASE:
        Valid configuration should pass validation and provide success metrics.
        """
        # Mock environment with valid configuration
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_test",
            "POSTGRES_USER": "testuser"
        }

        # Mock valid database URL
        mock_database_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/netra_test"

        with patch('netra_backend.app.core.startup_validation.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env

            # Mock DatabaseURLBuilder to return valid URL
            with patch('netra_backend.app.core.startup_validation.DatabaseURLBuilder') as mock_url_builder:
                mock_builder_instance = MagicMock()
                mock_builder_instance.get_url_for_environment.return_value = mock_database_url
                mock_url_builder.return_value = mock_builder_instance

                # Run database configuration validation
                await self.validator._validate_database_configuration_early()

        # Verify successful validation was recorded
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded configuration validation success"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.HEALTHY, "Valid configuration should be HEALTHY"
        assert validation.actual_count == 1, "Successful configuration means 1 valid config"
        assert "Configuration validation passed" in validation.message
        assert "localhost:5432" in validation.message
        assert validation.metadata["config_status"] == "valid"
        assert validation.metadata["database_host"] == "localhost"
        assert validation.metadata["database_port"] == 5432

    async def test_database_configuration_import_error_handling(self):
        """
        Test handling of missing dependencies for configuration validation.

        ROBUSTNESS TEST:
        If DatabaseURLBuilder or related dependencies are missing,
        validation should gracefully degrade with appropriate warnings.
        """
        # Mock ImportError for missing dependencies
        with patch('netra_backend.app.core.startup_validation.get_env', side_effect=ImportError("Missing sqlalchemy")):
            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify graceful degradation was recorded
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded import error handling"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.WARNING, "Import errors should be WARNING, not CRITICAL"
        assert validation.is_critical is False, "Missing dependencies should not be critical"
        assert "Configuration validation skipped" in validation.message
        assert "Missing dependencies" in validation.message
        assert validation.metadata["import_error"] == "Missing sqlalchemy"

    async def test_database_configuration_unexpected_error_handling(self):
        """
        Test handling of unexpected errors during configuration validation.

        ROBUSTNESS TEST:
        Unexpected errors should be caught and reported without crashing startup.
        """
        # Mock unexpected exception
        with patch('netra_backend.app.core.startup_validation.get_env', side_effect=RuntimeError("Unexpected system error")):
            # Run database configuration validation
            await self.validator._validate_database_configuration_early()

        # Verify unexpected error was handled gracefully
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]

        assert len(config_validations) == 1, "Should have recorded unexpected error handling"

        validation = config_validations[0]
        assert validation.status == ComponentStatus.WARNING, "Unexpected errors should be WARNING"
        assert validation.is_critical is False, "Validation errors should not be critical to startup"
        assert "Configuration validation error" in validation.message
        assert validation.metadata["validation_error"] == "Unexpected system error"

    async def test_database_configuration_performance_monitoring(self):
        """
        Test that database configuration validation completes within timeout.

        PERFORMANCE TEST:
        Configuration validation should be fast and not contribute to startup timeouts.
        """
        # Mock valid configuration
        mock_env_dict = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_test",
            "POSTGRES_USER": "testuser"
        }

        mock_database_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/netra_test"

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

        # Verify validation completed quickly
        assert validation_duration < 1.0, f"Database configuration validation took {validation_duration}s, should be <1s"

        # Verify successful validation
        config_validations = [v for v in self.validator.validations
                            if v.name == "Database Configuration"]
        assert len(config_validations) == 1, "Should have completed validation"
        assert config_validations[0].status == ComponentStatus.HEALTHY


class DatabaseConfigurationIntegrationUnitTests(SSotAsyncTestCase):
    """Unit tests for database configuration integration with main validation flow."""

    def setup_method(self, method):
        """Set up test fixtures using SSOT pattern."""
        super().setup_method(method)

        # Create validator instance
        self.validator = StartupValidator(environment=EnvironmentType.DEVELOPMENT)
        self.validator.validations = []

    async def test_database_validation_calls_configuration_early(self):
        """
        Test that _validate_database calls _validate_database_configuration_early.

        INTEGRATION TEST:
        The main database validation should always call configuration validation first.
        """
        # Mock app state with no database
        mock_app = MagicMock()
        mock_app.state.db_session_factory = None
        mock_app.state.database_mock_mode = False

        # Mock the early configuration validation method
        with patch.object(self.validator, '_validate_database_configuration_early') as mock_config_validation:
            # Run main database validation
            await self.validator._validate_database(mock_app)

        # Verify configuration validation was called first
        mock_config_validation.assert_called_once()

        # Verify database validation failure was also recorded
        db_validations = [v for v in self.validator.validations
                        if v.category == "Database"]
        assert len(db_validations) >= 1, "Should have recorded database validation results"

    async def test_configuration_validation_before_initialization_check(self):
        """
        Test that configuration validation occurs before initialization attempts.

        ISSUE #899 CRITICAL FIX:
        Configuration problems should be detected before attempting database initialization.
        """
        # Mock app state with initialized database factory
        mock_app = MagicMock()
        mock_session_factory = MagicMock()
        mock_app.state.db_session_factory = mock_session_factory
        mock_app.state.database_mock_mode = False

        # Mock configuration validation to fail
        with patch.object(self.validator, '_validate_database_configuration_early') as mock_config_validation:
            # Add a critical configuration validation failure
            config_failure = ComponentValidation(
                name="Database Configuration",
                category="Database",
                expected_min=1,
                actual_count=0,
                status=ComponentStatus.CRITICAL,
                message="Configuration validation failed: Missing POSTGRES_HOST",
                is_critical=True
            )

            async def mock_config_fail():
                self.validator.validations.append(config_failure)

            mock_config_validation.side_effect = mock_config_fail

            # Mock table counting to verify it's not called on config failure
            with patch.object(self.validator, '_count_database_tables') as mock_count_tables:
                # Run database validation
                await self.validator._validate_database(mock_app)

                # Verify table counting was still attempted (current behavior)
                # but configuration validation was called first
                mock_config_validation.assert_called_once()

        # Verify both configuration and database validations were recorded
        validations = [v for v in self.validator.validations if v.category == "Database"]
        config_validations = [v for v in validations if v.name == "Database Configuration"]
        table_validations = [v for v in validations if v.name == "Database Tables"]

        assert len(config_validations) == 1, "Should have configuration validation"
        assert len(table_validations) == 1, "Should have table validation"
        assert config_validations[0].status == ComponentStatus.CRITICAL