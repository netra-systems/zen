from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Critical Test: Staging Configuration Must Not Use Localhost Defaults

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Enterprise (prevents $12K MRR loss)
    # REMOVED_SYNTAX_ERROR: - Business Goal: System Stability & Reliability
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents staging/production configuration errors
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Ensures proper cloud configuration in non-dev environments

    # REMOVED_SYNTAX_ERROR: This test suite prevents regression where staging/production environments
    # REMOVED_SYNTAX_ERROR: accidentally use localhost as default values for database hosts.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.exceptions_config import ConfigurationError
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.config import ( )
    # REMOVED_SYNTAX_ERROR: ClickHouseNativeConfig,
    # REMOVED_SYNTAX_ERROR: ClickHouseHTTPConfig,
    # REMOVED_SYNTAX_ERROR: ClickHouseHTTPSConfig,
    # REMOVED_SYNTAX_ERROR: StagingConfig,
    # REMOVED_SYNTAX_ERROR: ProductionConfig,
    


# REMOVED_SYNTAX_ERROR: class TestNoLocalhostDefaults:
    # REMOVED_SYNTAX_ERROR: """Test that ClickHouse configs don't have localhost defaults."""

# REMOVED_SYNTAX_ERROR: def test_clickhouse_native_config_no_localhost_default(self):
    # REMOVED_SYNTAX_ERROR: """ClickHouseNativeConfig must not default to localhost."""
    # REMOVED_SYNTAX_ERROR: config = ClickHouseNativeConfig()
    # REMOVED_SYNTAX_ERROR: assert config.host == "", "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert config.host != "localhost", "ClickHouseNativeConfig must not default to localhost"

# REMOVED_SYNTAX_ERROR: def test_clickhouse_http_config_no_localhost_default(self):
    # REMOVED_SYNTAX_ERROR: """ClickHouseHTTPConfig must not default to localhost."""
    # REMOVED_SYNTAX_ERROR: config = ClickHouseHTTPConfig()
    # REMOVED_SYNTAX_ERROR: assert config.host == "", "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert config.host != "localhost", "ClickHouseHTTPConfig must not default to localhost"

# REMOVED_SYNTAX_ERROR: def test_clickhouse_https_config_no_localhost_default(self):
    # REMOVED_SYNTAX_ERROR: """ClickHouseHTTPSConfig must not default to localhost."""
    # REMOVED_SYNTAX_ERROR: config = ClickHouseHTTPSConfig()
    # REMOVED_SYNTAX_ERROR: assert config.host == "", "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert config.host != "localhost", "ClickHouseHTTPSConfig must not default to localhost"


# REMOVED_SYNTAX_ERROR: class TestStagingConfigurationValidation:
    # REMOVED_SYNTAX_ERROR: """Test that staging configuration properly validates database hosts."""

# REMOVED_SYNTAX_ERROR: def test_staging_requires_explicit_clickhouse_host(self):
    # REMOVED_SYNTAX_ERROR: """Staging must require explicit CLICKHOUSE_HOST configuration."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
        # Mock environment without CLICKHOUSE_HOST
# REMOVED_SYNTAX_ERROR: def mock_env_get(key, default=None):
    # REMOVED_SYNTAX_ERROR: env_values = { )
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_USER": "staging_user",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_DB": "staging_db",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_PASSWORD": "staging_pass",
    # Explicitly NO CLICKHOUSE_HOST
    
    # REMOVED_SYNTAX_ERROR: return env_values.get(key, default)

    # REMOVED_SYNTAX_ERROR: mock_get.side_effect = mock_env_get

    # Create database config manager
    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "staging"

    # Should raise ConfigurationError when CLICKHOUSE_HOST is missing
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ConfigurationError) as exc_info:
        # REMOVED_SYNTAX_ERROR: db_manager._get_clickhouse_configuration()

        # REMOVED_SYNTAX_ERROR: assert "CLICKHOUSE_HOST not configured for staging environment" in str(exc_info.value)

# REMOVED_SYNTAX_ERROR: def test_staging_accepts_explicit_clickhouse_host(self):
    # REMOVED_SYNTAX_ERROR: """Staging should accept explicitly configured CLICKHOUSE_HOST."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
        # Mock environment with CLICKHOUSE_HOST
# REMOVED_SYNTAX_ERROR: def mock_env_get(key, default=None):
    # REMOVED_SYNTAX_ERROR: env_values = { )
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_HOST": "clickhouse.staging.example.com",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_USER": "staging_user",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_DB": "staging_db",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_PASSWORD": "staging_pass",
    
    # REMOVED_SYNTAX_ERROR: return env_values.get(key, default)

    # REMOVED_SYNTAX_ERROR: mock_get.side_effect = mock_env_get

    # Create database config manager
    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "staging"

    # Should not raise error
    # REMOVED_SYNTAX_ERROR: config = db_manager._get_clickhouse_configuration()
    # REMOVED_SYNTAX_ERROR: assert config["host"] == "clickhouse.staging.example.com"
    # REMOVED_SYNTAX_ERROR: assert config["host"] != "localhost"

# REMOVED_SYNTAX_ERROR: def test_production_requires_explicit_clickhouse_host(self):
    # REMOVED_SYNTAX_ERROR: """Production must require explicit CLICKHOUSE_HOST configuration."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
        # Mock environment without CLICKHOUSE_HOST
# REMOVED_SYNTAX_ERROR: def mock_env_get(key, default=None):
    # REMOVED_SYNTAX_ERROR: env_values = { )
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "production",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_USER": "prod_user",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_DB": "prod_db",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_PASSWORD": "prod_pass",
    # Explicitly NO CLICKHOUSE_HOST
    
    # REMOVED_SYNTAX_ERROR: return env_values.get(key, default)

    # REMOVED_SYNTAX_ERROR: mock_get.side_effect = mock_env_get

    # Create database config manager
    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "production"

    # Should raise ConfigurationError when CLICKHOUSE_HOST is missing
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ConfigurationError) as exc_info:
        # REMOVED_SYNTAX_ERROR: db_manager._get_clickhouse_configuration()

        # REMOVED_SYNTAX_ERROR: assert "CLICKHOUSE_HOST not configured for production environment" in str(exc_info.value)


# REMOVED_SYNTAX_ERROR: class TestDevelopmentConfigurationDefaults:
    # REMOVED_SYNTAX_ERROR: """Test that development configuration properly handles defaults."""

# REMOVED_SYNTAX_ERROR: def test_development_uses_localhost_when_not_configured(self):
    # REMOVED_SYNTAX_ERROR: """Development should use localhost when CLICKHOUSE_HOST is not set."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
        # Mock environment without CLICKHOUSE_HOST
# REMOVED_SYNTAX_ERROR: def mock_env_get(key, default=None):
    # REMOVED_SYNTAX_ERROR: env_values = { )
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "development",
    # No CLICKHOUSE_HOST
    
    # REMOVED_SYNTAX_ERROR: return env_values.get(key, default)

    # REMOVED_SYNTAX_ERROR: mock_get.side_effect = mock_env_get

    # Create database config manager
    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "development"

    # Should not raise error and should use localhost
    # REMOVED_SYNTAX_ERROR: config = db_manager._get_clickhouse_configuration()
    # REMOVED_SYNTAX_ERROR: assert config["host"] == "localhost", "Development should default to localhost when CLICKHOUSE_HOST not set"

# REMOVED_SYNTAX_ERROR: def test_testing_uses_localhost_when_not_configured(self):
    # REMOVED_SYNTAX_ERROR: """Testing environment should use localhost when CLICKHOUSE_HOST is not set."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
        # Mock environment without CLICKHOUSE_HOST
# REMOVED_SYNTAX_ERROR: def mock_env_get(key, default=None):
    # REMOVED_SYNTAX_ERROR: env_values = { )
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "testing",
    # No CLICKHOUSE_HOST
    
    # REMOVED_SYNTAX_ERROR: return env_values.get(key, default)

    # REMOVED_SYNTAX_ERROR: mock_get.side_effect = mock_env_get

    # Create database config manager
    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "testing"

    # Should not raise error and should use localhost
    # REMOVED_SYNTAX_ERROR: config = db_manager._get_clickhouse_configuration()
    # REMOVED_SYNTAX_ERROR: assert config["host"] == "localhost", "Testing should default to localhost when CLICKHOUSE_HOST not set"


# REMOVED_SYNTAX_ERROR: class TestPostgreSQLValidation:
    # REMOVED_SYNTAX_ERROR: """Test PostgreSQL configuration validation for staging/production."""

# REMOVED_SYNTAX_ERROR: def test_staging_rejects_localhost_postgres(self):
    # REMOVED_SYNTAX_ERROR: """Staging should reject localhost for PostgreSQL connections."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "staging"

    # Test with localhost URL with SSL to bypass SSL check
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ConfigurationError) as exc_info:
        # REMOVED_SYNTAX_ERROR: db_manager._validate_postgres_url("postgresql://user:pass@localhost:5432/db?sslmode=require")

        # REMOVED_SYNTAX_ERROR: assert "Localhost not allowed in staging" in str(exc_info.value)

# REMOVED_SYNTAX_ERROR: def test_staging_accepts_cloudsql_postgres(self):
    # REMOVED_SYNTAX_ERROR: """Staging should accept Cloud SQL Unix socket connections."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "staging"

    # Test with Cloud SQL socket - should not raise
    # REMOVED_SYNTAX_ERROR: cloud_sql_url = "postgresql://user:pass@/db?host=/cloudsql/project:region:instance"
    # REMOVED_SYNTAX_ERROR: db_manager._validate_postgres_url(cloud_sql_url)  # Should not raise

# REMOVED_SYNTAX_ERROR: def test_production_rejects_localhost_postgres(self):
    # REMOVED_SYNTAX_ERROR: """Production should reject localhost for PostgreSQL connections."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: db_manager = DatabaseConfigManager()
    # REMOVED_SYNTAX_ERROR: db_manager._environment = "production"

    # Test with localhost URL with SSL to bypass SSL check
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ConfigurationError) as exc_info:
        # REMOVED_SYNTAX_ERROR: db_manager._validate_postgres_url("postgresql://user:pass@localhost:5432/db?sslmode=require")

        # REMOVED_SYNTAX_ERROR: assert "Localhost not allowed in production" in str(exc_info.value)


# REMOVED_SYNTAX_ERROR: class TestConfigurationIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for complete configuration loading."""

# REMOVED_SYNTAX_ERROR: def test_staging_config_creation_validates_hosts(self):
    # REMOVED_SYNTAX_ERROR: """Creating StagingConfig should validate database hosts."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.base import UnifiedConfigManager

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
        # Mock minimal staging environment
# REMOVED_SYNTAX_ERROR: def mock_env_get(key, default=None):
    # REMOVED_SYNTAX_ERROR: env_values = { )
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_HOST": "/cloudsql/project:region:instance",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_USER": "staging_user",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_DB": "staging_db",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_PASSWORD": "staging_pass",
    # No CLICKHOUSE_HOST - should fail
    
    # REMOVED_SYNTAX_ERROR: return env_values.get(key, default)

    # REMOVED_SYNTAX_ERROR: mock_get.side_effect = mock_env_get

    # Attempting to get config should fail due to missing ClickHouse host
    # REMOVED_SYNTAX_ERROR: config_manager = UnifiedConfigManager()
    # REMOVED_SYNTAX_ERROR: config_manager._environment = "staging"

    # REMOVED_SYNTAX_ERROR: with pytest.raises(ConfigurationError) as exc_info:
        # REMOVED_SYNTAX_ERROR: config_manager.get_config()

        # REMOVED_SYNTAX_ERROR: error_msg = str(exc_info.value)
        # REMOVED_SYNTAX_ERROR: assert "CLICKHOUSE_HOST" in error_msg or "Configuration" in error_msg


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])
