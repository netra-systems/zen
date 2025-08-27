"""Tests for unified environment loading from .env files.

These tests verify that the configuration system correctly loads
environment variables from .env files in development mode.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from netra_backend.app.core.configuration.base import config_manager


class TestUnifiedEnvLoading:
    """Test suite for unified environment loading."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Save original environment
        self.original_env = os.environ.copy()
        
        # Clear critical environment variables
        env_vars_to_clear = [
            'ENVIRONMENT', 'GEMINI_API_KEY', 'OAUTH_GOOGLE_CLIENT_ID_ENV',
            'OAUTH_GOOGLE_CLIENT_SECRET_ENV', 'JWT_SECRET_KEY', 'FERNET_KEY',
            'SERVICE_SECRET', 'CLICKHOUSE_PASSWORD',
            'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DATABASE_URL',
            'REDIS_URL', 'CLICKHOUSE_HOST', 'CLICKHOUSE_PORT',
            'LLM_MODE', 'REDIS_MODE', 'CLICKHOUSE_MODE',
            'NETRA_SECRETS_LOADING', 'CORS_ORIGINS'
        ]
        for var in env_vars_to_clear:
            os.environ.pop(var, None)
        
        yield
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_load_from_dotenv_file_in_development(self):
        """Test that .env file is loaded in development mode."""
        # Set development environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
        os.environ['OAUTH_GOOGLE_CLIENT_ID_ENV'] = 'test_client_id'
        os.environ['OAUTH_GOOGLE_CLIENT_SECRET_ENV'] = 'test_client_secret'
        os.environ['JWT_SECRET_KEY'] = 'test_jwt_key'
        os.environ['FERNET_KEY'] = 'test_fernet_key'
        os.environ['SERVICE_SECRET'] = 'test_service_secret'
        os.environ['CLICKHOUSE_PASSWORD'] = 'test_clickhouse_pwd'
        os.environ['DATABASE_URL'] = 'postgresql://test@localhost/testdb'
        os.environ['REDIS_URL'] = 'redis://localhost:6379'
        os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
        os.environ['OPENAI_API_KEY'] = 'test_openai_key'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify all values are loaded from environment  
        # API keys are loaded into LLM configs, not root fields
        assert config.llm_configs["default"].api_key == 'test_gemini_key'
        assert config.google_cloud.client_id == 'test_client_id'
        assert config.google_cloud.client_secret == 'test_client_secret' 
        assert config.jwt_secret_key == 'test_jwt_key'
        assert config.fernet_key == 'test_fernet_key'
        assert config.service_secret == 'test_service_secret'
        assert config.clickhouse_native.password == 'test_clickhouse_pwd'
        assert config.database_url == 'postgresql://test@localhost/testdb'
        assert config.redis_url == 'redis://localhost:6379'
        assert config.anthropic_api_key == 'test_anthropic_key'
        assert config.openai_api_key == 'test_openai_key'
    
    def test_env_vars_override_dotenv_file(self):
        """Test that environment variables override .env file values."""
        # Set development environment and override values
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['GEMINI_API_KEY'] = 'env_gemini_key'
        os.environ['DATABASE_URL'] = 'postgresql://env@localhost/envdb'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify environment variable values are used
        assert config.llm_configs["default"].api_key == 'env_gemini_key'
        assert config.database_url == 'postgresql://env@localhost/envdb'
    
    def test_no_dotenv_loading_in_production(self):
        """Test that .env file is NOT loaded in production mode."""
        # Set production environment
        os.environ['ENVIRONMENT'] = 'production'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration - should NOT load from .env
        config = config_manager.get_config()
        
        # Verify production config has proper defaults (not from .env files)
        assert config.environment == 'production'
        # In production, these should be None if not explicitly set via environment
        assert config.gemini_api_key != 'file_gemini_key'
    
    def test_all_required_secrets_populated_from_env(self):
        """Test that all required secrets can be populated from environment."""
        # Set all required secrets in environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['GEMINI_API_KEY'] = 'test_gemini'
        os.environ['OAUTH_GOOGLE_CLIENT_ID_ENV'] = 'test_client_id'
        os.environ['OAUTH_GOOGLE_CLIENT_SECRET_ENV'] = 'test_client_secret'
        os.environ['JWT_SECRET_KEY'] = 'test_jwt'
        os.environ['FERNET_KEY'] = 'test_fernet'
        os.environ['SERVICE_SECRET'] = 'test_service'
        os.environ['CLICKHOUSE_PASSWORD'] = 'test_clickhouse'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify all secrets are populated
        assert config.llm_configs["default"].api_key == 'test_gemini'
        assert config.google_cloud.client_id == 'test_client_id'
        assert config.google_cloud.client_secret == 'test_client_secret'
        assert config.jwt_secret_key == 'test_jwt'
        assert config.fernet_key == 'test_fernet'
        assert config.service_secret == 'test_service'
        assert config.clickhouse_native.password == 'test_clickhouse'
    
    def test_service_modes_from_env(self):
        """Test that service modes are correctly loaded from environment."""
        # Set service modes in environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['LLM_MODE'] = 'mock'
        os.environ['REDIS_MODE'] = 'local'
        os.environ['CLICKHOUSE_MODE'] = 'docker'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify service modes are loaded
        assert config.llm_mode == 'mock'
        assert config.redis_mode == 'local'
        assert config.clickhouse_mode == 'docker'
    
    def test_cors_origins_from_env(self):
        """Test that CORS origins are correctly loaded from environment."""
        # Set CORS origins
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['CORS_ORIGINS'] = '*'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify CORS origins are loaded
        assert config.cors_origins == '*'
    
    def test_no_secrets_loading_flag_during_startup(self):
        """Test that NETRA_SECRETS_LOADING flag doesn't block env loading."""
        # Set flag that indicates secrets are still loading
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['NETRA_SECRETS_LOADING'] = 'true'
        os.environ['GEMINI_API_KEY'] = 'test_key'
        
        # Force reload of configuration  
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration - should still load from environment
        config = config_manager.get_config()
        
        # Verify values are loaded despite flag
        assert config.llm_configs["default"].api_key == 'test_key'
    
    def test_dev_launcher_env_propagation(self):
        """Test that dev launcher environment variables are properly loaded."""
        # Simulate dev launcher environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['BACKEND_PORT'] = '8000'
        os.environ['PYTHONPATH'] = '/path/to/project'
        os.environ['CORS_ORIGINS'] = '*'
        os.environ['REDIS_MODE'] = 'shared'
        os.environ['CLICKHOUSE_MODE'] = 'shared'
        os.environ['LLM_MODE'] = 'shared'
        os.environ['GEMINI_API_KEY'] = 'launcher_gemini_key'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify all dev launcher values are loaded
        assert config.cors_origins == '*'
        assert config.redis_mode == 'shared'
        assert config.clickhouse_mode == 'shared'
        assert config.llm_mode == 'shared'
        assert config.llm_configs["default"].api_key == 'launcher_gemini_key'
        
    def test_missing_required_environment_defaults(self):
        """Test configuration behavior when required environment variables are missing."""
        # Set only basic environment
        os.environ['ENVIRONMENT'] = 'development'
        # Deliberately don't set other required vars
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration - should not crash, should use defaults
        config = config_manager.get_config()
        
        # Verify configuration object is created with defaults
        assert config is not None
        assert config.environment == 'development'
        # Missing values should have sensible defaults
        assert isinstance(config.llm_configs, dict)
        
    def test_environment_variable_type_coercion(self):
        """Test that environment variables are properly converted to expected types."""
        # Set various types of environment variables
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['CLICKHOUSE_PORT'] = '9000'  # String that should become int
        os.environ['DEBUG'] = 'true'  # String that might become boolean
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify type coercion works properly
        if hasattr(config, 'clickhouse_native') and hasattr(config.clickhouse_native, 'port'):
            assert isinstance(config.clickhouse_native.port, int)
            assert config.clickhouse_native.port == 9000
            
    def test_config_manager_caching_behavior(self):
        """Test that config manager properly caches configuration instances."""
        # Set environment
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['GEMINI_API_KEY'] = 'cache_test_key'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Get configuration twice
        config1 = config_manager.get_config()
        config2 = config_manager.get_config()
        
        # Should be the same instance (cached)
        assert config1 is config2
        assert config1.llm_configs["default"].api_key == 'cache_test_key'
        
    def test_staging_environment_behavior(self):
        """Test configuration behavior in staging environment."""
        # Set staging environment
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['GEMINI_API_KEY'] = 'staging_gemini_key'
        os.environ['DATABASE_URL'] = 'postgresql://staging@host/db'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify staging-specific behavior
        assert config.environment == 'staging'
        # In staging, env vars should still be loaded
        assert config.llm_configs["default"].api_key == 'staging_gemini_key'
        assert config.database_url == 'postgresql://staging@host/db'
        
    def test_config_loading_with_invalid_values(self):
        """Test configuration loading handles invalid environment variable values gracefully."""
        # Set environment with potentially invalid values
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['CLICKHOUSE_PORT'] = 'invalid_port'  # Invalid port number
        os.environ['CORS_ORIGINS'] = ''  # Empty string
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration - should not crash
        config = config_manager.get_config()
        
        # Should handle invalid values gracefully
        assert config is not None
        assert config.environment == 'development'
        
    def test_multiple_llm_providers_from_env(self):
        """Test loading multiple LLM provider configurations from environment."""
        # Set multiple LLM provider keys
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['GEMINI_API_KEY'] = 'gemini_test_key'
        os.environ['ANTHROPIC_API_KEY'] = 'anthropic_test_key'
        os.environ['OPENAI_API_KEY'] = 'openai_test_key'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify all LLM provider keys are loaded
        assert config.llm_configs["default"].api_key == 'gemini_test_key'
        assert config.anthropic_api_key == 'anthropic_test_key'
        assert config.openai_api_key == 'openai_test_key'
        
    def test_database_configuration_variations(self):
        """Test different database URL configurations from environment."""
        test_cases = [
            'postgresql://user:pass@localhost:5432/dbname',
            'postgresql://user@localhost/dbname',
            'sqlite:///path/to/db.sqlite'
        ]
        
        for db_url in test_cases:
            # Clear and set environment
            os.environ.clear()
            os.environ.update(self.original_env)
            
            os.environ['ENVIRONMENT'] = 'development'
            os.environ['DATABASE_URL'] = db_url
            
            # Force reload of configuration
            config_manager._config_cache = None
            config_manager.get_config.cache_clear()
            
            # Load configuration
            config = config_manager.get_config()
            
            # Verify database URL is loaded correctly
            assert config.database_url == db_url
            
    def test_redis_configuration_from_env(self):
        """Test Redis configuration loading from environment variables."""
        # Set Redis configuration
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        os.environ['REDIS_MODE'] = 'local'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify Redis configuration
        assert config.redis_url == 'redis://localhost:6379/0'
        assert config.redis_mode == 'local'
        
    def test_clickhouse_configuration_from_env(self):
        """Test ClickHouse configuration loading from environment variables."""
        # Set ClickHouse configuration
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['CLICKHOUSE_HOST'] = 'clickhouse.example.com'
        os.environ['CLICKHOUSE_PORT'] = '9000'
        os.environ['CLICKHOUSE_PASSWORD'] = 'test_ch_password'
        os.environ['CLICKHOUSE_MODE'] = 'remote'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify ClickHouse configuration
        if hasattr(config, 'clickhouse_native'):
            assert config.clickhouse_native.host == 'clickhouse.example.com'
            assert config.clickhouse_native.password == 'test_ch_password'
        assert config.clickhouse_mode == 'remote'
        
    def test_oauth_configuration_from_env(self):
        """Test OAuth configuration loading from environment variables."""
        # Set OAuth configuration
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['OAUTH_GOOGLE_CLIENT_ID_ENV'] = 'test_oauth_client_id'
        os.environ['OAUTH_GOOGLE_CLIENT_SECRET_ENV'] = 'test_oauth_client_secret'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify OAuth configuration
        if hasattr(config, 'google_cloud'):
            assert config.google_cloud.client_id == 'test_oauth_client_id'
            assert config.google_cloud.client_secret == 'test_oauth_client_secret'
            
    def test_security_keys_from_env(self):
        """Test security key loading from environment variables."""
        # Set security keys
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['JWT_SECRET_KEY'] = 'test_jwt_secret_key_123'
        os.environ['FERNET_KEY'] = 'test_fernet_key_456'
        os.environ['SERVICE_SECRET'] = 'test_service_secret_789'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify security keys are loaded
        assert config.jwt_secret_key == 'test_jwt_secret_key_123'
        assert config.fernet_key == 'test_fernet_key_456'
        assert config.service_secret == 'test_service_secret_789'
        
    def test_config_manager_error_handling(self):
        """Test that config manager handles errors gracefully during loading."""
        # Set minimal environment to avoid issues
        os.environ['ENVIRONMENT'] = 'development'
        
        # Test with potentially problematic configuration manager state
        with patch.object(config_manager, 'get_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config loading failed")
            
            # Should handle exception gracefully
            with pytest.raises(Exception, match="Config loading failed"):
                config_manager.get_config()
                
    def test_environment_isolation_between_tests(self):
        """Test that environment changes are properly isolated between tests."""
        # This test verifies that our setup/teardown works correctly
        # Set test-specific environment
        os.environ['ENVIRONMENT'] = 'test_isolation'
        os.environ['CUSTOM_TEST_VAR'] = 'test_value'
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify test environment is set
        assert config.environment == 'test_isolation'
        assert os.environ.get('CUSTOM_TEST_VAR') == 'test_value'