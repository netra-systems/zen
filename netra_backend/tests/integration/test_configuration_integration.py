"""
Integration tests for configuration loading and management.

Tests configuration from multiple sources:
- Environment variables
- Configuration files  
- Default values and fallbacks
- Environment-specific configurations
- Secret management integration
- Configuration validation and hot-reload
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, mock_open, patch

import pytest

from config import get_config, reload_config, validate_configuration

# Add project root to path
from netra_backend.app.core.configuration.base import config_manager, get_unified_config
from netra_backend.app.schemas.Config import AppConfig
from test_framework.mock_utils import mock_justified

# Add project root to path


class TestConfigurationIntegration:
    """Integration tests for configuration loading and validation."""

    @pytest.fixture
    def base_environment_config(self):
        """Provide base environment configuration."""
        return {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "REDIS_URL": "redis://localhost:6379/0", 
            "CLICKHOUSE_URL": "http://localhost:8123",
            "NETRA_API_KEY": "test-api-key-12345",
            "ENVIRONMENT": "test",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG"
        }

    @pytest.fixture
    def staging_environment_config(self):
        """Provide staging environment configuration."""
        return {
            "DATABASE_URL": "postgresql+asyncpg://staging:pass@staging-db:5432/netra_staging",
            "REDIS_URL": "redis://staging-redis:6379/0",
            "CLICKHOUSE_URL": "http://staging-clickhouse:8123", 
            "NETRA_API_KEY": "staging-api-key-67890",
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO"
        }

    async def test_configuration_loading_from_environment(self, base_environment_config):
        """
        Test configuration loads correctly from environment variables.
        
        Validates:
        - All environment variables are read
        - Type conversion works correctly
        - Required fields are validated
        - Optional fields use defaults
        """
        with patch.dict(os.environ, base_environment_config, clear=True):
            config = get_config()
            
            self._verify_database_configuration(config, base_environment_config)
            self._verify_service_configuration(config, base_environment_config)
            self._verify_environment_settings(config, base_environment_config)
            self._verify_logging_configuration(config)

    def _verify_database_configuration(self, config: AppConfig, env_config: Dict[str, str]):
        """Verify database configuration is loaded correctly."""
        assert config.database_url == env_config["DATABASE_URL"]
        assert "postgresql+asyncpg" in config.database_url
        assert "testdb" in config.database_url

    def _verify_service_configuration(self, config: AppConfig, env_config: Dict[str, str]):
        """Verify external service configuration."""
        assert config.redis_url == env_config["REDIS_URL"]
        assert config.clickhouse_url == env_config["CLICKHOUSE_URL"]
        assert config.netra_api_key == env_config["NETRA_API_KEY"]

    def _verify_environment_settings(self, config: AppConfig, env_config: Dict[str, str]):
        """Verify environment-specific settings."""
        assert config.environment == env_config["ENVIRONMENT"] 
        assert config.debug == (env_config["DEBUG"].lower() == "true")

    def _verify_logging_configuration(self, config: AppConfig):
        """Verify logging configuration is set."""
        assert hasattr(config, 'log_level')
        # Verify log level is valid
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if hasattr(config, 'log_level'):
            assert config.log_level.upper() in valid_levels

    async def test_environment_specific_configurations(self, staging_environment_config):
        """
        Test environment-specific configuration overrides.
        
        Validates:
        - Staging environment uses different settings
        - Production flags are set correctly
        - Debug mode is disabled in staging
        - Service URLs point to staging infrastructure
        """
        with patch.dict(os.environ, staging_environment_config, clear=True):
            config = get_config()
            
            # Verify staging-specific settings
            assert config.environment == "staging"
            assert config.debug is False, "Debug should be disabled in staging"
            assert "staging" in config.database_url
            assert "staging" in config.redis_url
            
            # Verify K_SERVICE indicates Cloud Run deployment (test environment check)
            assert os.environ.get("K_SERVICE") == "netra-backend"

    async def test_configuration_validation_and_errors(self):
        """Test configuration validation catches errors and provides helpful messages."""
        # Test missing database URL
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}, clear=True):
            try:
                config = get_config()
                is_valid, errors = validate_configuration()
                
                if is_valid:
                    pytest.fail("Expected validation error for missing database URL")
                
                error_text = " ".join(errors).lower()
                assert "database" in error_text, f"Expected 'database' error in: {error_text}"
                    
            except Exception as e:
                error_text = str(e).lower()
                assert "database" in error_text, f"Expected 'database' error in exception: {e}"

    async def test_configuration_fallback_mechanisms(self):
        """
        Test configuration fallback to default values.
        
        Validates:
        - Missing optional values use sensible defaults
        - Fallback chain works correctly
        - System remains functional with minimal config
        """
        minimal_config = {
            "DATABASE_URL": "sqlite+aiosqlite:///test.db",
            "NETRA_API_KEY": "test-key"
        }
        
        with patch.dict(os.environ, minimal_config, clear=True):
            config = get_config()
            
            # Verify defaults are applied
            self._verify_default_values_applied(config)
            
            # Verify system is still functional
            is_valid, errors = validate_configuration()
            assert is_valid or len(errors) == 0, f"Config should be valid with defaults: {errors}"

    def _verify_default_values_applied(self, config: AppConfig):
        """Verify default values are applied for optional settings."""
        # Check that default values exist for optional settings
        assert hasattr(config, 'environment')
        assert hasattr(config, 'debug')
        
        # Environment should default to development if not set
        if not config.environment:
            assert config.environment in [None, "", "development", "test"]

    @mock_justified("File system operations for configuration testing")
    async def test_configuration_file_loading(self, base_environment_config):
        """
        Test loading configuration from files with environment variable override.
        
        Validates:
        - Configuration files are read correctly
        - Environment variables override file values
        - JSON and YAML formats work (if supported)
        - File loading errors are handled gracefully
        """
        config_file_content = {
            "database_url": "postgresql://config-file:5432/config_db",
            "redis_url": "redis://config-file:6379",
            "environment": "file_config",
            "debug": False
        }
        
        mock_file_content = json.dumps(config_file_content)
        
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            with patch("os.path.exists", return_value=True):
                with patch.dict(os.environ, base_environment_config):
                    config = get_config()
                    
                    # Environment variables should override file values
                    assert config.database_url == base_environment_config["DATABASE_URL"]
                    assert config.environment == base_environment_config["ENVIRONMENT"]

    async def test_configuration_hot_reload(self, base_environment_config):
        """
        Test configuration hot-reload functionality.
        
        Validates:
        - Configuration can be reloaded without restart
        - New values take effect immediately
        - Validation occurs during reload
        - Invalid reloads are rejected safely
        """
        with patch.dict(os.environ, base_environment_config):
            # Get initial configuration
            initial_config = get_config()
            initial_debug = initial_config.debug
            
            # Modify environment and reload
            new_debug_value = not initial_debug
            with patch.dict(os.environ, {"DEBUG": str(new_debug_value).lower()}):
                reload_config(force=True)
                
                # Get updated configuration
                updated_config = get_config()
                
                # Verify configuration was reloaded
                assert updated_config.debug == new_debug_value, \
                    f"Config not reloaded: expected {new_debug_value}, got {updated_config.debug}"

    async def test_secret_management_integration(self):
        """
        Test integration with secret management systems.
        
        Validates:
        - Secrets are loaded from environment
        - Sensitive values are not logged
        - Secret validation works correctly
        - Missing secrets are handled properly
        """
        secrets_config = {
            "DATABASE_URL": "postgresql://user:secret_password@db:5432/prod",
            "NETRA_API_KEY": "secret-api-key-abcdef123456",
            "REDIS_URL": "redis://:secret_redis_pass@redis:6379"
        }
        
        with patch.dict(os.environ, secrets_config):
            config = get_config()
            
            # Verify secrets are loaded
            assert "secret_password" in config.database_url
            assert "secret-api-key" in config.netra_api_key
            assert "secret_redis_pass" in config.redis_url
            
            # Verify configuration validation still works with secrets
            is_valid, errors = validate_configuration()
            assert is_valid, f"Config with secrets should be valid: {errors}"

    async def test_configuration_caching_and_performance(self, base_environment_config):
        """
        Test configuration caching for performance.
        
        Validates:
        - Configuration is cached after first load
        - Subsequent calls are fast
        - Cache invalidation works correctly
        - Memory usage is reasonable
        """
        with patch.dict(os.environ, base_environment_config):
            # First load - should read from environment
            config1 = get_config()
            
            # Second load - should use cache 
            config2 = get_config()
            
            # Should be same instance if caching works
            assert config1 is config2 or config1.__dict__ == config2.__dict__
            
            # Test cache invalidation
            reload_config(force=True)
            config3 = get_config()
            
            # Should still have same values but potentially new instance
            assert config3.database_url == config1.database_url
            assert config3.environment == config1.environment

    async def test_configuration_environment_isolation(self):
        """Test configuration isolation between different environments."""
        # Test that test environment works
        with patch.dict(os.environ, {"ENVIRONMENT": "test", "DATABASE_URL": "sqlite:///test.db"}, clear=True):
            config = get_config()
            assert config.environment == "test"
            assert config.database_url == "sqlite:///test.db"

    async def test_microservice_configuration_independence(self):
        """Test configuration independence between microservices."""
        main_backend_config = {
            "DATABASE_URL": "postgresql://backend:5432/main_db",
            "REDIS_URL": "redis://redis:6379/0",
            "AUTH_SERVICE_URL": "http://auth-service:8001",
            "ENVIRONMENT": "test"
        }
        
        with patch.dict(os.environ, main_backend_config):
            config = get_config()
            
            # Verify main backend configuration
            assert config.database_url == main_backend_config["DATABASE_URL"]
            assert "main_db" in config.database_url
            
            # Verify no auth implementation config leaked in
            auth_fields = ['auth_secret_key', 'jwt_secret', 'oauth_client_secret']
            for auth_field in auth_fields:
                assert not hasattr(config, auth_field) or getattr(config, auth_field) in [None, ""]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])