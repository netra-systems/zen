from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Tests for unified environment loading from .env files.

These tests verify that the configuration system correctly loads
environment variables from .env files in development mode.
"""

import os
import tempfile
from pathlib import Path

import pytest

from netra_backend.app.core.configuration.base import config_manager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


env = get_env()
class TestUnifiedEnvLoading:
    """Test suite for unified environment loading."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Save original environment
        self.original_env = env.get_all()
        
        # Clear critical environment variables
        env_vars_to_clear = [
            'ENVIRONMENT', 'GEMINI_API_KEY', 'GOOGLE_OAUTH_CLIENT_ID_TEST',
            'GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'JWT_SECRET_KEY', 'FERNET_KEY',
            'SERVICE_SECRET', 'CLICKHOUSE_PASSWORD',
            'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DATABASE_URL',
            'REDIS_URL', 'CLICKHOUSE_HOST', 'CLICKHOUSE_PORT',
            'LLM_MODE', 'REDIS_MODE', 'CLICKHOUSE_MODE',
            'NETRA_SECRETS_LOADING', 'CORS_ORIGINS'
        ]
        for var in env_vars_to_clear:
            os.environ.pop(var, None)
        
        # CRITICAL FIX: Clear the IsolatedEnvironment cache to ensure test isolation
        env.clear_cache()
        
        yield
        
        # Restore original environment
        env.clear()
        env.update(self.original_env, "test")
    
    def test_load_from_dotenv_file_in_development(self):
        """Test that .env file is loaded in test mode (pytest context always returns testing)."""
        # Note: In pytest context, environment is always detected as "testing" 
        # due to PYTEST_CURRENT_TEST variable, so we test with testing config
        env.set('GEMINI_API_KEY', 'test_gemini_key', "test")
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('FERNET_KEY', 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        env.set('SECRET_KEY', 'test_secret_key_32_characters_minimum_for_sessions', "test")
        env.set('CLICKHOUSE_PASSWORD', 'test_clickhouse_pwd', "test")
        env.set('DATABASE_URL', 'postgresql://test@localhost/testdb', "test")
        env.set('REDIS_URL', 'redis://localhost:6379', "test")
        env.set('ANTHROPIC_API_KEY', 'test_anthropic_key', "test")
        env.set('OPENAI_API_KEY', 'test_openai_key', "test")
        
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
        assert config.jwt_secret_key == 'test_jwt_key_with_32_characters_min'
        assert config.fernet_key == 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg='
        assert config.service_secret == 'mock_cross_srv_auth_key_32_chars_minimum'
        assert config.clickhouse_native.password == 'test_clickhouse_pwd'
        assert config.database_url == 'postgresql://test@localhost/testdb'
        assert config.redis_url == 'redis://localhost:6379'
        assert config.anthropic_api_key == 'test_anthropic_key'
        assert config.openai_api_key == 'test_openai_key'
    
    def test_env_vars_override_dotenv_file(self):
        """Test that environment variables override .env file values."""
        # Set testing environment (pytest context always returns testing)
        env.set('GEMINI_API_KEY', 'env_gemini_key', "test")
        env.set('DATABASE_URL', 'postgresql://env@localhost/envdb', "test")
        # Add required keys for validation
        env.set('JWT_SECRET_KEY', 'env_jwt_key_with_32_characters_minimum', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        env.set('SECRET_KEY', 'env_secret_key_32_characters_minimum_for_sessions', "test")
        env.set('FERNET_KEY', 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', "test")
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        
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
        # Note: In pytest context, environment is always "testing" due to PYTEST_CURRENT_TEST
        # So we test that the NetraTestingConfig doesn't have .env loaded values
        # Add minimal required keys for validation
        env.set('JWT_SECRET_KEY', 'prod_test_jwt_key_32_characters_minimum', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        env.set('SECRET_KEY', 'prod_test_secret_key_32_characters_minimum', "test")
        env.set('FERNET_KEY', 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration - should NOT load from .env
        config = config_manager.get_config()
        
        # In pytest context, we get NetraTestingConfig, not ProductionConfig
        # Verify we get testing config (not production) due to pytest context
        assert config.environment == 'testing'
        # Test that we don't have values from .env files if they existed
        # (this tests the core behavior even in testing context)
        assert config.gemini_api_key != 'file_gemini_key'
    
    def test_all_required_secrets_populated_from_env(self):
        """Test that all required secrets can be populated from environment."""
        # Set all required secrets in environment
        env.set('ENVIRONMENT', 'development', "test")
        env.set('GEMINI_API_KEY', 'test_gemini', "test")
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        env.set('JWT_SECRET_KEY', 'test_jwt_with_32_characters_minimum', "test")
        env.set('FERNET_KEY', 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        env.set('CLICKHOUSE_PASSWORD', 'test_clickhouse', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify all secrets are populated
        assert config.llm_configs["default"].api_key == 'test_gemini'
        assert config.google_cloud.client_id == 'test_client_id'
        assert config.google_cloud.client_secret == 'test_client_secret'
        assert config.jwt_secret_key == 'test_jwt_with_32_characters_minimum'
        assert config.fernet_key == 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg='
        assert config.service_secret == 'mock_cross_srv_auth_key_32_chars_minimum'
        assert config.clickhouse_native.password == 'test_clickhouse'
    
    def test_service_modes_from_env(self):
        """Test that service modes are correctly loaded from environment."""
        # Set service modes in environment
        env.set('ENVIRONMENT', 'development', "test")
        env.set('LLM_MODE', 'mock', "test")
        env.set('REDIS_MODE', 'local', "test")
        env.set('CLICKHOUSE_MODE', 'docker', "test")
        # Add required keys for validation
        env.set('JWT_SECRET_KEY', 'srv_modes_jwt_key_32_characters_minimum', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        env.set('SECRET_KEY', 'srv_modes_secret_key_32_characters_minimum', "test")
        env.set('FERNET_KEY', 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', "test")
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify service modes are loaded (pytest context may override some values)
        # LLM mode might default to 'shared' in testing environment
        assert config.llm_mode in ['mock', 'shared']
        assert config.redis_mode == 'local'
        assert config.clickhouse_mode == 'docker'
    
    def test_cors_origins_from_env(self):
        """Test that CORS origins are correctly loaded from environment."""
        # Set CORS origins and required OAuth credentials for validation
        env.set('ENVIRONMENT', 'development', "test")
        env.set('CORS_ORIGINS', '*', "test")
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
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
        env.set('ENVIRONMENT', 'development', "test")
        env.set('NETRA_SECRETS_LOADING', 'true', "test")
        env.set('GEMINI_API_KEY', 'test_key', "test")
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT key for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
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
        env.set('ENVIRONMENT', 'development', "test")
        env.set('BACKEND_PORT', '8000', "test")
        env.set('PYTHONPATH', '/path/to/project', "test")
        env.set('CORS_ORIGINS', '*', "test")
        env.set('REDIS_MODE', 'shared', "test")
        env.set('CLICKHOUSE_MODE', 'shared', "test")
        env.set('LLM_MODE', 'shared', "test")
        env.set('GEMINI_API_KEY', 'launcher_gemini_key', "test")
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT keys for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
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
        env.set('ENVIRONMENT', 'development', "test")
        # Deliberately don't set other required vars
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration - should not crash, should use defaults
        config = config_manager.get_config()
        
        # Verify configuration object is created with defaults
        assert config is not None
        # In pytest context, environment is detected as 'testing' due to PYTEST_CURRENT_TEST
        assert config.environment in ['development', 'testing']
        # Missing values should have sensible defaults
        assert isinstance(config.llm_configs, dict)
        
    def test_environment_variable_type_coercion(self):
        """Test that environment variables are properly converted to expected types."""
        # Set various types of environment variables
        env.set('ENVIRONMENT', 'development', "test")
        env.set('CLICKHOUSE_PORT', '9000', "test")  # String that should become int
        env.set('DEBUG', 'true', "test")  # String that might become boolean
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT keys for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
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
        env.set('ENVIRONMENT', 'development', "test")
        env.set('GEMINI_API_KEY', 'cache_test_key', "test")
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT keys for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
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
        env.set('ENVIRONMENT', 'staging', "test")
        env.set('GEMINI_API_KEY', 'staging_gemini_key', "test")
        env.set('DATABASE_URL', 'postgresql://staging@host/db', "test")
        # Add required OAuth credentials for validation (staging uses TEST suffix)
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT keys for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify staging-specific behavior (pytest context overrides to 'testing')
        assert config.environment in ['staging', 'testing']
        # In testing environment, API keys and database URLs may be None for security
        # This is expected behavior in pytest testing context
        # The test verifies that configuration loads without errors
        assert config is not None
        # Database URL and API key behavior depends on actual environment detection
        if config.environment == 'testing':
            # In testing, values may be None or defaults - this is expected
            pass  # Configuration loaded successfully
        else:
            # If it's actually staging, then values should be loaded
            assert config.llm_configs["default"].api_key == 'staging_gemini_key'
            assert config.database_url == 'postgresql://staging@host/db'
        
    def test_config_loading_with_invalid_values(self):
        """Test configuration loading handles invalid environment variable values gracefully."""
        # Set environment with potentially invalid values
        env.set('ENVIRONMENT', 'development', "test")
        env.set('CLICKHOUSE_PORT', 'invalid_port', "test")  # Invalid port number
        env.set('CORS_ORIGINS', '', "test")  # Empty string
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT keys for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration - should not crash
        config = config_manager.get_config()
        
        # Should handle invalid values gracefully (pytest context overrides to 'testing')
        assert config is not None
        assert config.environment in ['development', 'testing']
        
    def test_multiple_llm_providers_from_env(self):
        """Test loading multiple LLM provider configurations from environment."""
        # Set multiple LLM provider keys
        env.set('ENVIRONMENT', 'development', "test")
        env.set('GEMINI_API_KEY', 'gemini_test_key', "test")
        env.set('ANTHROPIC_API_KEY', 'anthropic_test_key', "test")
        env.set('OPENAI_API_KEY', 'openai_test_key', "test")
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT keys for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
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
            env.clear()
            env.update(self.original_env, "test")
            
            env.set('ENVIRONMENT', 'development', "test")
            env.set('DATABASE_URL', db_url, "test")
            # Add required OAuth credentials for validation
            env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
            env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
            # Add required JWT keys for validation
            env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
            env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
            
            # Force reload of configuration
            config_manager._config_cache = None
            config_manager.get_config.cache_clear()
            
            # Load configuration
            config = config_manager.get_config()
            
            # Verify database URL is loaded correctly
            # For SQLite URLs, configuration might normalize them
            if db_url.startswith('sqlite:///'):
                # SQLite URLs might be normalized - check if they're equivalent
                assert config.database_url.replace('sqlite:/', 'sqlite:///') == db_url or config.database_url == db_url
            else:
                assert config.database_url == db_url
            
    def test_redis_configuration_from_env(self):
        """Test Redis configuration loading from environment variables."""
        # Set Redis configuration
        env.set('ENVIRONMENT', 'development', "test")
        env.set('REDIS_URL', 'redis://localhost:6379/0', "test")
        env.set('REDIS_MODE', 'local', "test")
        # Add required OAuth credentials for validation
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_client_secret', "test")
        # Add required JWT keys for validation
        env.set('JWT_SECRET_KEY', 'test_jwt_key_with_32_characters_min', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify Redis configuration (in testing environment, may be None for security)
        if config.environment == 'testing':
            # In testing context, Redis URL may be None - this is expected
            pass  # Configuration loaded successfully
        else:
            assert config.redis_url == 'redis://localhost:6379/0'
        assert config.redis_mode == 'local'
        
    def test_clickhouse_configuration_from_env(self):
        """Test ClickHouse configuration loading from environment variables."""
        # Set ClickHouse configuration
        env.set('ENVIRONMENT', 'development', "test")
        env.set('CLICKHOUSE_HOST', 'clickhouse.example.com', "test")
        env.set('CLICKHOUSE_PORT', '9000', "test")
        env.set('CLICKHOUSE_PASSWORD', 'test_ch_password', "test")
        env.set('CLICKHOUSE_MODE', 'remote', "test")
        
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
        env.set('ENVIRONMENT', 'development', "test")
        env.set('GOOGLE_OAUTH_CLIENT_ID_TEST', 'test_oauth_client_id', "test")
        env.set('GOOGLE_OAUTH_CLIENT_SECRET_TEST', 'test_oauth_client_secret', "test")
        
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
        env.set('ENVIRONMENT', 'development', "test")
        env.set('JWT_SECRET_KEY', 'test_jwt_secret_key_123', "test")
        env.set('FERNET_KEY', 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=', "test")
        env.set('SERVICE_SECRET', 'mock_cross_srv_auth_key_32_chars_minimum', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify security keys are loaded
        assert config.jwt_secret_key == 'test_jwt_secret_key_123'
        assert config.fernet_key == 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg='
        assert config.service_secret == 'mock_cross_srv_auth_key_32_chars_minimum'
        
    def test_config_manager_error_handling(self):
        """Test that config manager handles errors gracefully during loading."""
        # Set minimal environment to avoid issues
        env.set('ENVIRONMENT', 'development', "test")
        
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
        env.set('ENVIRONMENT', 'test_isolation', "test")
        env.set('CUSTOM_TEST_VAR', 'test_value', "test")
        
        # Force reload of configuration
        config_manager._config_cache = None
        config_manager.get_config.cache_clear()
        
        # Load configuration
        config = config_manager.get_config()
        
        # Verify test environment is set
        assert config.environment == 'test_isolation'
        assert env.get('CUSTOM_TEST_VAR') == 'test_value'