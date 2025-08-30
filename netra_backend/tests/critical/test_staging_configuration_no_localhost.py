"""
Critical Test: Staging Configuration Must Not Use Localhost Defaults

Business Value Justification (BVJ):
- Segment: Enterprise (prevents $12K MRR loss)
- Business Goal: System Stability & Reliability
- Value Impact: Prevents staging/production configuration errors
- Strategic Impact: Ensures proper cloud configuration in non-dev environments

This test suite prevents regression where staging/production environments
accidentally use localhost as default values for database hosts.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from netra_backend.app.core.exceptions_config import ConfigurationError
from netra_backend.app.schemas.config import (
    ClickHouseNativeConfig,
    ClickHouseHTTPConfig,
    ClickHouseHTTPSConfig,
    StagingConfig,
    ProductionConfig,
)


class TestNoLocalhostDefaults:
    """Test that ClickHouse configs don't have localhost defaults."""
    
    def test_clickhouse_native_config_no_localhost_default(self):
        """ClickHouseNativeConfig must not default to localhost."""
        config = ClickHouseNativeConfig()
        assert config.host == "", f"ClickHouseNativeConfig.host defaults to '{config.host}' instead of empty string"
        assert config.host != "localhost", "ClickHouseNativeConfig must not default to localhost"
    
    def test_clickhouse_http_config_no_localhost_default(self):
        """ClickHouseHTTPConfig must not default to localhost."""
        config = ClickHouseHTTPConfig()
        assert config.host == "", f"ClickHouseHTTPConfig.host defaults to '{config.host}' instead of empty string"
        assert config.host != "localhost", "ClickHouseHTTPConfig must not default to localhost"
    
    def test_clickhouse_https_config_no_localhost_default(self):
        """ClickHouseHTTPSConfig must not default to localhost."""
        config = ClickHouseHTTPSConfig()
        assert config.host == "", f"ClickHouseHTTPSConfig.host defaults to '{config.host}' instead of empty string"
        assert config.host != "localhost", "ClickHouseHTTPSConfig must not default to localhost"


class TestStagingConfigurationValidation:
    """Test that staging configuration properly validates database hosts."""
    
    @patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False)
    def test_staging_requires_explicit_clickhouse_host(self):
        """Staging must require explicit CLICKHOUSE_HOST configuration."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
            # Mock environment without CLICKHOUSE_HOST
            def mock_env_get(key, default=None):
                env_values = {
                    "ENVIRONMENT": "staging",
                    "CLICKHOUSE_USER": "staging_user",
                    "CLICKHOUSE_DB": "staging_db",
                    "CLICKHOUSE_PASSWORD": "staging_pass",
                    # Explicitly NO CLICKHOUSE_HOST
                }
                return env_values.get(key, default)
            
            mock_get.side_effect = mock_env_get
            
            # Create database config manager
            db_manager = DatabaseConfigManager()
            db_manager._environment = "staging"
            
            # Should raise ConfigurationError when CLICKHOUSE_HOST is missing
            with pytest.raises(ConfigurationError) as exc_info:
                db_manager._get_clickhouse_configuration()
            
            assert "CLICKHOUSE_HOST not configured for staging environment" in str(exc_info.value)
    
    @patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False)
    def test_staging_accepts_explicit_clickhouse_host(self):
        """Staging should accept explicitly configured CLICKHOUSE_HOST."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
            # Mock environment with CLICKHOUSE_HOST
            def mock_env_get(key, default=None):
                env_values = {
                    "ENVIRONMENT": "staging",
                    "CLICKHOUSE_HOST": "clickhouse.staging.example.com",
                    "CLICKHOUSE_USER": "staging_user",
                    "CLICKHOUSE_DB": "staging_db",
                    "CLICKHOUSE_PASSWORD": "staging_pass",
                }
                return env_values.get(key, default)
            
            mock_get.side_effect = mock_env_get
            
            # Create database config manager
            db_manager = DatabaseConfigManager()
            db_manager._environment = "staging"
            
            # Should not raise error
            config = db_manager._get_clickhouse_configuration()
            assert config["host"] == "clickhouse.staging.example.com"
            assert config["host"] != "localhost"
    
    @patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False)
    def test_production_requires_explicit_clickhouse_host(self):
        """Production must require explicit CLICKHOUSE_HOST configuration."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
            # Mock environment without CLICKHOUSE_HOST
            def mock_env_get(key, default=None):
                env_values = {
                    "ENVIRONMENT": "production",
                    "CLICKHOUSE_USER": "prod_user",
                    "CLICKHOUSE_DB": "prod_db",
                    "CLICKHOUSE_PASSWORD": "prod_pass",
                    # Explicitly NO CLICKHOUSE_HOST
                }
                return env_values.get(key, default)
            
            mock_get.side_effect = mock_env_get
            
            # Create database config manager
            db_manager = DatabaseConfigManager()
            db_manager._environment = "production"
            
            # Should raise ConfigurationError when CLICKHOUSE_HOST is missing
            with pytest.raises(ConfigurationError) as exc_info:
                db_manager._get_clickhouse_configuration()
            
            assert "CLICKHOUSE_HOST not configured for production environment" in str(exc_info.value)


class TestDevelopmentConfigurationDefaults:
    """Test that development configuration properly handles defaults."""
    
    @patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False)
    def test_development_uses_localhost_when_not_configured(self):
        """Development should use localhost when CLICKHOUSE_HOST is not set."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
            # Mock environment without CLICKHOUSE_HOST
            def mock_env_get(key, default=None):
                env_values = {
                    "ENVIRONMENT": "development",
                    # No CLICKHOUSE_HOST
                }
                return env_values.get(key, default)
            
            mock_get.side_effect = mock_env_get
            
            # Create database config manager
            db_manager = DatabaseConfigManager()
            db_manager._environment = "development"
            
            # Should not raise error and should use localhost
            config = db_manager._get_clickhouse_configuration()
            assert config["host"] == "localhost", "Development should default to localhost when CLICKHOUSE_HOST not set"
    
    @patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=False)
    def test_testing_uses_localhost_when_not_configured(self):
        """Testing environment should use localhost when CLICKHOUSE_HOST is not set."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
            # Mock environment without CLICKHOUSE_HOST
            def mock_env_get(key, default=None):
                env_values = {
                    "ENVIRONMENT": "testing",
                    # No CLICKHOUSE_HOST
                }
                return env_values.get(key, default)
            
            mock_get.side_effect = mock_env_get
            
            # Create database config manager
            db_manager = DatabaseConfigManager()
            db_manager._environment = "testing"
            
            # Should not raise error and should use localhost
            config = db_manager._get_clickhouse_configuration()
            assert config["host"] == "localhost", "Testing should default to localhost when CLICKHOUSE_HOST not set"


class TestPostgreSQLValidation:
    """Test PostgreSQL configuration validation for staging/production."""
    
    @patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False)
    def test_staging_rejects_localhost_postgres(self):
        """Staging should reject localhost for PostgreSQL connections."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        db_manager = DatabaseConfigManager()
        db_manager._environment = "staging"
        
        # Test with localhost URL with SSL to bypass SSL check
        with pytest.raises(ConfigurationError) as exc_info:
            db_manager._validate_postgres_url("postgresql://user:pass@localhost:5432/db?sslmode=require")
        
        assert "Localhost not allowed in staging" in str(exc_info.value)
    
    @patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False)
    def test_staging_accepts_cloudsql_postgres(self):
        """Staging should accept Cloud SQL Unix socket connections."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        db_manager = DatabaseConfigManager()
        db_manager._environment = "staging"
        
        # Test with Cloud SQL socket - should not raise
        cloud_sql_url = "postgresql://user:pass@/db?host=/cloudsql/project:region:instance"
        db_manager._validate_postgres_url(cloud_sql_url)  # Should not raise
    
    @patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False)
    def test_production_rejects_localhost_postgres(self):
        """Production should reject localhost for PostgreSQL connections."""
        from netra_backend.app.core.configuration.database import DatabaseConfigManager
        
        db_manager = DatabaseConfigManager()
        db_manager._environment = "production"
        
        # Test with localhost URL with SSL to bypass SSL check
        with pytest.raises(ConfigurationError) as exc_info:
            db_manager._validate_postgres_url("postgresql://user:pass@localhost:5432/db?sslmode=require")
        
        assert "Localhost not allowed in production" in str(exc_info.value)


class TestConfigurationIntegration:
    """Integration tests for complete configuration loading."""
    
    @patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False)
    def test_staging_config_creation_validates_hosts(self):
        """Creating StagingConfig should validate database hosts."""
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        
        with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment.get') as mock_get:
            # Mock minimal staging environment
            def mock_env_get(key, default=None):
                env_values = {
                    "ENVIRONMENT": "staging",
                    "POSTGRES_HOST": "/cloudsql/project:region:instance",
                    "POSTGRES_USER": "staging_user",
                    "POSTGRES_DB": "staging_db",
                    "POSTGRES_PASSWORD": "staging_pass",
                    # No CLICKHOUSE_HOST - should fail
                }
                return env_values.get(key, default)
            
            mock_get.side_effect = mock_env_get
            
            # Attempting to get config should fail due to missing ClickHouse host
            config_manager = UnifiedConfigManager()
            config_manager._environment = "staging"
            
            with pytest.raises(ConfigurationError) as exc_info:
                config_manager.get_config()
            
            error_msg = str(exc_info.value)
            assert "CLICKHOUSE_HOST" in error_msg or "Configuration" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])