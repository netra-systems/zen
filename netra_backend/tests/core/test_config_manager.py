"""Tests for the configuration management system."""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from netra_backend.app.core.config import get_config, reload_config
from netra_backend.app.core.config_validator import (
    ConfigurationValidationError,
    ConfigValidator,
)
# ConfigManager import removed - class doesn't exist in base module
# from netra_backend.app.core.configuration.base import ConfigManager
from netra_backend.app.core.exceptions_config import ConfigurationError

# Add project root to path
from netra_backend.app.core.secret_manager import SecretManager, SecretManagerError
from netra_backend.app.schemas.Config import AppConfig, DevelopmentConfig

# Add project root to path


class TestSecretManager:
    """Test the SecretManager class."""
    
    def test_initialization(self):
        """Test SecretManager initialization."""
        manager = SecretManager()
        assert manager._project_id == "304612253870"
        assert manager._client == None
    
    @patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test-gemini-key',
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'JWT_SECRET_KEY': 'test-jwt-secret'
    })
    def test_load_from_environment(self):
        """Test loading secrets from environment variables."""
        manager = SecretManager()
        secrets = manager._load_from_environment()
        
        assert 'gemini-api-key' in secrets
        assert secrets['gemini-api-key'] == 'test-gemini-key'
        assert 'google-client-id' in secrets
        assert secrets['google-client-id'] == 'test-client-id'
        assert 'jwt-secret-key' in secrets
        assert secrets['jwt-secret-key'] == 'test-jwt-secret'
    
    @patch('app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    def test_secret_manager_client_creation_success(self, mock_client_class):
        """Test successful Secret Manager client creation."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        manager = SecretManager()
        client = manager._get_secret_client()
        
        assert client == mock_client
        mock_client_class.assert_called_once()
    
    @patch('app.core.secret_manager.secretmanager.SecretManagerServiceClient')
    def test_secret_manager_client_creation_failure(self, mock_client_class):
        """Test Secret Manager client creation failure."""
        mock_client_class.side_effect = Exception("Connection failed")
        
        manager = SecretManager()
        
        # The retry decorator wraps the exception in tenacity.RetryError
        from tenacity import RetryError
        with pytest.raises(RetryError):
            manager._get_secret_client()
    
    @patch.object(SecretManager, '_get_secret_client')
    @patch.object(SecretManager, '_fetch_secret')
    def test_load_from_secret_manager_success(self, mock_fetch, mock_client):
        """Test successful loading from Secret Manager."""
        mock_client.return_value = MagicMock()
        mock_fetch.side_effect = lambda client, name: f"secret-{name}"
        
        manager = SecretManager()
        secrets = manager._load_from_secret_manager()
        
        assert len(secrets) > 0
        assert all(value.startswith("secret-") for value in secrets.values())
    
    @patch.object(SecretManager, '_load_from_secret_manager')
    @patch.object(SecretManager, '_load_from_environment')
    def test_load_secrets_fallback_to_env(self, mock_env, mock_sm):
        """Test fallback to environment when Secret Manager fails."""
        mock_sm.side_effect = Exception("SM failed")
        mock_env.return_value = {'test-secret': 'test-value'}
        
        manager = SecretManager()
        secrets = manager.load_secrets()
        
        assert secrets == {'test-secret': 'test-value'}
        mock_env.assert_called_once()


class TestConfigValidator:
    """Test the ConfigValidator class."""
    
    def test_initialization(self):
        """Test ConfigValidator initialization."""
        validator = ConfigValidator()
        assert validator._logger != None
    
    def test_validate_valid_config(self):
        """Test validation of a valid configuration."""
        config = DevelopmentConfig()
        validator = ConfigValidator()
        
        # Should not raise an exception
        validator.validate_config(config)
    
    def test_validate_database_config_missing_url(self):
        """Test validation fails when database URL is missing."""
        config = DevelopmentConfig()
        config.database_url = None
        
        validator = ConfigValidator()
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            validator.validate_config(config)
        
        assert "Database URL is not configured" in str(exc_info.value)
    
    def test_validate_database_config_invalid_url(self):
        """Test validation fails with invalid database URL."""
        config = DevelopmentConfig()
        config.database_url = "mysql://invalid"
        
        validator = ConfigValidator()
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            validator.validate_config(config)
        
        assert "Database URL must be a PostgreSQL connection string" in str(exc_info.value)
    
    def test_validate_auth_config_missing_jwt_secret(self):
        """Test validation fails when JWT secret is missing."""
        config = DevelopmentConfig()
        config.jwt_secret_key = None
        
        validator = ConfigValidator()
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            validator.validate_config(config)
        
        assert "JWT secret key is not configured" in str(exc_info.value)
    
    def test_validate_auth_config_production_dev_secret(self):
        """Test validation fails when using dev JWT secret in production."""
        config = DevelopmentConfig()
        config.environment = "production"
        config.jwt_secret_key = "development_secret_key_for_jwt_do_not_use_in_production"
        
        # Set required production database passwords to avoid validation failures
        config.clickhouse_native.password = "production_password"
        config.clickhouse_https.password = "production_password"
        
        validator = ConfigValidator()
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            validator.validate_config(config)
        
        assert "JWT secret key appears to be a development/test key" in str(exc_info.value)
    
    def test_get_validation_report_success(self):
        """Test getting validation report for successful validation."""
        config = DevelopmentConfig()
        validator = ConfigValidator()
        
        report = validator.get_validation_report(config)
        
        assert isinstance(report, list)
        assert len(report) > 0
        assert "✓ All configuration checks passed" in report[0]
    
    def test_get_validation_report_failure(self):
        """Test getting validation report for failed validation."""
        config = DevelopmentConfig()
        config.database_url = None
        
        validator = ConfigValidator()
        report = validator.get_validation_report(config)
        
        assert isinstance(report, list)
        assert any("✗ Configuration validation failed" in line for line in report)


class TestConfigManager:
    """Test the ConfigManager class."""
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'development'})
    def test_initialization(self):
        """Test ConfigManager initialization."""
        manager = ConfigManager()
        assert manager._config == None
        assert manager._secrets_manager != None
        assert manager._validator != None
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=False)
    def test_get_environment_development(self):
        """Test environment detection for development."""
        # Temporarily remove TESTING env var if it exists
        with patch.dict(os.environ, {'TESTING': ''}, clear=False):
            if 'TESTING' in os.environ:
                del os.environ['TESTING']
            manager = ConfigManager()
            env = manager._get_environment()
            assert env == "development"
    
    @patch.dict(os.environ, {'TESTING': '1'})
    def test_get_environment_testing(self):
        """Test environment detection for testing."""
        manager = ConfigManager()
        env = manager._get_environment()
        assert env == "testing"
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=False)
    def test_get_environment_production(self):
        """Test environment detection for production."""
        # Temporarily remove TESTING env var if it exists
        with patch.dict(os.environ, {'TESTING': ''}, clear=False):
            if 'TESTING' in os.environ:
                del os.environ['TESTING']
            manager = ConfigManager()
            env = manager._get_environment()
            assert env == "production"
    
    def test_create_base_config_development(self):
        """Test creating development configuration."""
        manager = ConfigManager()
        config = manager._create_base_config("development")
        assert isinstance(config, DevelopmentConfig)
        assert config.environment == "development"
    
    def test_create_base_config_unknown_defaults_to_dev(self):
        """Test unknown environment defaults to development."""
        manager = ConfigManager()
        config = manager._create_base_config("unknown")
        assert isinstance(config, DevelopmentConfig)
    
    @patch.object(ConfigManager, '_load_secrets_into_config')
    @patch.object(ConfigValidator, 'validate_config')
    def test_load_configuration_success(self, mock_validate, mock_load_secrets):
        """Test successful configuration loading."""
        manager = ConfigManager()
        
        config = manager._load_configuration()
        
        assert isinstance(config, AppConfig)
        mock_load_secrets.assert_called_once()
        mock_validate.assert_called_once_with(config)
    
    @patch.object(ConfigValidator, 'validate_config')
    def test_load_configuration_validation_failure(self, mock_validate):
        """Test configuration loading with validation failure."""
        mock_validate.side_effect = ConfigurationValidationError("Validation failed")
        
        manager = ConfigManager()
        
        with pytest.raises(ConfigurationError):
            manager._load_configuration()
    
    @patch.object(ConfigManager, '_load_configuration')
    def test_get_config_caching(self, mock_load):
        """Test configuration caching."""
        mock_config = DevelopmentConfig()
        mock_load.return_value = mock_config
        
        manager = ConfigManager()
        
        # First call should load configuration
        config1 = manager.get_config()
        assert config1 == mock_config
        mock_load.assert_called_once()
        
        # Second call should use cached config
        config2 = manager.get_config()
        assert config2 == mock_config
        assert config1 is config2
        mock_load.assert_called_once()  # Still only called once
    
    def test_reload_config(self):
        """Test configuration reloading."""
        manager = ConfigManager()
        manager._config = DevelopmentConfig()
        
        # Cache should be cleared
        manager.reload_config()
        assert manager._config == None


class TestConfigurationFunctions:
    """Test global configuration functions."""
    
    @patch('app.config.config_manager')
    def test_get_config(self, mock_manager):
        """Test global get_config function."""
        mock_config = DevelopmentConfig()
        mock_manager.get_config.return_value = mock_config
        
        config = get_config()
        
        assert config == mock_config
        mock_manager.get_config.assert_called_once()
    
    @patch('app.config.config_manager')
    def test_reload_config(self, mock_manager):
        """Test global reload_config function."""
        reload_config()
        mock_manager.reload_config.assert_called_once()


class TestConfigurationIntegration:
    """Integration tests for configuration system."""
    
    def test_full_configuration_flow(self):
        """Test complete configuration loading flow."""
        # Clear the environment and set specific values
        test_env = {
            'ENVIRONMENT': 'development',
            'GEMINI_API_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/test'
        }
        
        # Use clear=True to ensure only our test env vars are set
        with patch.dict(os.environ, test_env, clear=True):
            # Create a new config manager to avoid cached config
            # ConfigManager import removed - class doesn't exist in base module
# from netra_backend.app.core.configuration.base import ConfigManager
            manager = ConfigManager()
            
            # Override the _load_secrets_into_config to apply our DATABASE_URL
            def mock_load_secrets(config):
                # Load secrets from environment
                try:
                    secrets = manager._secrets_manager.load_secrets()
                    manager._apply_secrets_to_config(config, secrets)
                except Exception:
                    pass
                # Always load environment variables including DATABASE_URL
                manager._load_from_environment_variables(config)
                
            with patch.object(manager, '_load_secrets_into_config', side_effect=mock_load_secrets):
                config = manager.get_config()
                
                assert isinstance(config, AppConfig)
                assert config.environment == "development"
                assert config.database_url == 'postgresql+asyncpg://user:pass@localhost/test'
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'testing'
    })
    def test_testing_configuration(self):
        """Test testing environment configuration."""
        # Reload to pick up new environment
        reload_config()
        config = get_config()
        
        assert config.environment == "testing"
    
    def test_configuration_error_handling(self):
        """Test configuration error handling."""
        # Create a config manager with invalid setup
        manager = ConfigManager()
        
        # Mock validation to fail
        with patch.object(manager._validator, 'validate_config') as mock_validate:
            mock_validate.side_effect = ConfigurationValidationError("Test error")
            
            with pytest.raises(ConfigurationError):
                manager.get_config()


@pytest.fixture
def clean_config():
    """Fixture to clean configuration state between tests."""
    # Clear any cached configuration
    reload_config()
    yield
    # Clean up after test
    reload_config()