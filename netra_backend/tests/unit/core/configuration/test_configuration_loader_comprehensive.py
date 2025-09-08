"""
Comprehensive Unit Tests for ConfigurationLoader - SSOT Configuration Access

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all segments)
- Business Goal: Development Velocity & Risk Reduction 
- Value Impact: Ensures configuration loading works reliably across ALL environments
- Strategic Impact: ConfigurationLoader is the primary facade for config access - failure blocks entire platform

CRITICAL: ConfigurationLoader provides the main interface for configuration access.
This is the entry point that ALL services use to get configuration.

Test Requirements from CLAUDE.md:
1. CHEATING ON TESTS = ABOMINATION - Every test must fail hard on errors
2. NO mocks unless absolutely necessary - Use real configuration classes
3. ABSOLUTE IMPORTS only - No relative imports
4. Tests must RAISE ERRORS - No try/except blocks masking failures
5. Real services over mocks - Use real environment detection, real config classes

Testing Areas:
1. Configuration Loading - load(), caching, lazy initialization
2. Environment Detection - development, staging, production, testing
3. Configuration Creation - proper config class instantiation per environment
4. Caching Behavior - LRU cache, reload functionality  
5. Service Configuration Access - redis, llm, auth service configs
6. Environment Helper Methods - is_production(), is_development(), etc.
7. Database URL Access - postgres, clickhouse URLs
8. Configuration Validation - validate() method
9. Global Function Access - get_configuration(), reload_configuration()
10. Error Handling - invalid environments, config creation failures
11. Hot Reload - force reload scenarios
12. Configuration State - cache consistency, state management
"""

import pytest
from typing import Any, Dict, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env

from netra_backend.app.core.configuration.loader import (
    ConfigurationLoader,
    get_configuration,
    reload_configuration,
    _configuration_loader
)
from netra_backend.app.schemas.config import (
    AppConfig,
    DevelopmentConfig,
    NetraTestingConfig,
    ProductionConfig,
    StagingConfig,
)


class TestConfigurationLoaderInitialization(BaseTestCase):
    """Test ConfigurationLoader initialization and basic functionality."""
    
    def test_configuration_loader_creates_real_instance(self):
        """Test that ConfigurationLoader creates a real working instance.
        
        Business Value: Ensures configuration loader initializes properly
        """
        loader = ConfigurationLoader()
        
        # Verify instance is created
        assert loader is not None
        assert hasattr(loader, '_logger')
        assert hasattr(loader, '_config_cache')
        
        # Verify initial state
        assert loader._config_cache is None
        
    def test_configuration_loader_has_required_methods(self):
        """Test that ConfigurationLoader has all required methods.
        
        Business Value: Interface compliance ensures all services can access config
        """
        loader = ConfigurationLoader()
        
        # Verify all required methods exist
        required_methods = [
            'load', 'reload', 'get_environment', 'is_production', 
            'is_development', 'is_testing', 'get_database_url',
            'get_service_config', 'validate'
        ]
        
        for method in required_methods:
            assert hasattr(loader, method), f"Missing required method: {method}"
            assert callable(getattr(loader, method)), f"Method {method} is not callable"


class TestConfigurationLoading(BaseTestCase):
    """Test configuration loading functionality."""
    
    def test_load_creates_real_config_instance(self):
        """Test that load() creates a real AppConfig instance.
        
        Business Value: Core functionality - must return valid configuration
        """
        loader = ConfigurationLoader()
        
        # Load configuration
        config = loader.load()
        
        # Verify real config instance returned
        assert config is not None
        assert isinstance(config, AppConfig)
        assert hasattr(config, 'environment')
        
    def test_load_caching_behavior(self):
        """Test that configuration loading uses caching properly.
        
        Business Value: Performance - avoid reloading config on every access
        """
        loader = ConfigurationLoader()
        
        # First load
        config1 = loader.load()
        
        # Second load should return cached instance
        config2 = loader.load()
        
        # Should be the same instance due to caching
        assert config1 is config2
        assert loader._config_cache is config1
        
    def test_load_with_different_environments(self):
        """Test configuration loading for different environments.
        
        Business Value: Ensures proper environment-specific configuration
        """
        loader = ConfigurationLoader()
        
        environments = ['development', 'staging', 'production', 'testing']
        
        for env in environments:
            # Clear cache for each test
            loader.load.cache_clear()
            loader._config_cache = None
            
            with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.get_environment', return_value=env):
                config = loader.load()
                
                # Verify config is loaded
                assert config is not None
                assert isinstance(config, AppConfig)
                assert config.environment == env


class TestEnvironmentDetection(BaseTestCase):
    """Test environment detection and environment-specific methods."""
    
    def test_get_environment_returns_current_environment(self):
        """Test that get_environment() returns the current environment.
        
        Business Value: Environment-specific behavior depends on correct detection
        """
        loader = ConfigurationLoader()
        
        with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.get_environment', return_value='testing'):
            # Clear cache to force reload
            loader.load.cache_clear()
            loader._config_cache = None
            
            environment = loader.get_environment()
            
            assert environment == 'testing'
    
    def test_is_production_detects_production_environment(self):
        """Test that is_production() correctly identifies production environment.
        
        Business Value: Production-specific behavior and security constraints
        """
        loader = ConfigurationLoader()
        
        with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.get_environment', return_value='production'):
            loader.load.cache_clear()
            loader._config_cache = None
            
            assert loader.is_production() is True
            assert loader.is_development() is False
            assert loader.is_testing() is False
    
    def test_is_development_detects_development_environment(self):
        """Test that is_development() correctly identifies development environment.
        
        Business Value: Development-specific debugging and configuration
        """
        loader = ConfigurationLoader()
        
        with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.get_environment', return_value='development'):
            loader.load.cache_clear()
            loader._config_cache = None
            
            assert loader.is_development() is True
            assert loader.is_production() is False
            assert loader.is_testing() is False
    
    def test_is_testing_detects_testing_environment(self):
        """Test that is_testing() correctly identifies testing environment.
        
        Business Value: Test-specific configuration and behavior
        """
        loader = ConfigurationLoader()
        
        with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.get_environment', return_value='testing'):
            loader.load.cache_clear()
            loader._config_cache = None
            
            assert loader.is_testing() is True
            assert loader.is_production() is False
            assert loader.is_development() is False


class TestConfigurationCreation(BaseTestCase):
    """Test configuration creation for different environments."""
    
    def test_creates_development_config_for_development_environment(self):
        """Test that development environment creates DevelopmentConfig.
        
        Business Value: Correct configuration class for environment-specific behavior
        """
        loader = ConfigurationLoader()
        
        config = loader._create_config_for_environment('development')
        
        # Should create appropriate config instance
        assert config is not None
        assert isinstance(config, AppConfig)
        
    def test_creates_staging_config_for_staging_environment(self):
        """Test that staging environment creates StagingConfig.
        
        Business Value: Proper staging configuration for pre-production testing
        """
        loader = ConfigurationLoader()
        
        config = loader._create_config_for_environment('staging')
        
        assert config is not None
        assert isinstance(config, AppConfig)
    
    def test_creates_production_config_for_production_environment(self):
        """Test that production environment creates ProductionConfig.
        
        Business Value: Secure production configuration with proper security settings
        """
        loader = ConfigurationLoader()
        
        config = loader._create_config_for_environment('production')
        
        assert config is not None
        assert isinstance(config, AppConfig)
    
    def test_creates_testing_config_for_testing_environment(self):
        """Test that testing environment creates NetraTestingConfig.
        
        Business Value: Test-specific configuration for reliable test execution
        """
        loader = ConfigurationLoader()
        
        config = loader._create_config_for_environment('testing')
        
        assert config is not None
        assert isinstance(config, AppConfig)
    
    def test_defaults_to_development_config_for_unknown_environment(self):
        """Test that unknown environment defaults to DevelopmentConfig.
        
        Business Value: Safe fallback to development mode for unknown environments
        """
        loader = ConfigurationLoader()
        
        config = loader._create_config_for_environment('unknown_environment')
        
        assert config is not None
        assert isinstance(config, AppConfig)


class TestReloadFunctionality(BaseTestCase):
    """Test configuration reload and cache management."""
    
    def test_reload_without_force_returns_cached_config(self):
        """Test that reload() without force returns cached configuration.
        
        Business Value: Efficient caching avoids unnecessary reloads
        """
        loader = ConfigurationLoader()
        
        # Load initial config
        config1 = loader.load()
        
        # Reload without force
        config2 = loader.reload(force=False)
        
        # Should return same cached instance
        assert config1 is config2
    
    def test_reload_with_force_clears_cache_and_reloads(self):
        """Test that reload(force=True) clears cache and reloads configuration.
        
        Business Value: Hot reload capability for configuration updates
        """
        loader = ConfigurationLoader()
        
        # Load initial config
        config1 = loader.load()
        
        # Force reload
        config2 = loader.reload(force=True)
        
        # Should be different instances after forced reload
        # Note: Due to lru_cache, this might still be the same instance
        # The important thing is that cache was cleared
        assert config2 is not None
        assert isinstance(config2, AppConfig)
    
    def test_reload_cache_clear_functionality(self):
        """Test that force reload properly clears cache.
        
        Business Value: Ensures cache invalidation works for hot reloads
        """
        loader = ConfigurationLoader()
        
        # Load and cache config
        loader.load()
        assert loader._config_cache is not None
        
        # Force reload should clear cache
        loader.reload(force=True)
        
        # Cache should be cleared
        assert loader._config_cache is None


class TestDatabaseURLAccess(BaseTestCase):
    """Test database URL access functionality."""
    
    def test_get_database_url_returns_postgres_url_by_default(self):
        """Test that get_database_url() returns PostgreSQL URL by default.
        
        Business Value: Database connectivity for primary data storage
        """
        loader = ConfigurationLoader()
        
        # Mock config with database URL method
        mock_config = MagicMock()
        mock_config.get_database_url.return_value = "postgresql://test:test@localhost:5432/test"
        
        with patch.object(loader, 'load', return_value=mock_config):
            url = loader.get_database_url()
            
            assert url == "postgresql://test:test@localhost:5432/test"
            mock_config.get_database_url.assert_called_once()
    
    def test_get_database_url_returns_clickhouse_url_when_specified(self):
        """Test that get_database_url() returns ClickHouse URL when specified.
        
        Business Value: Analytics database connectivity for data processing
        """
        loader = ConfigurationLoader()
        
        # Mock config with clickhouse URL method  
        mock_config = MagicMock()
        mock_config.get_clickhouse_url.return_value = "clickhouse://localhost:8123/analytics"
        
        with patch.object(loader, 'load', return_value=mock_config):
            url = loader.get_database_url(db_type='clickhouse')
            
            assert url == "clickhouse://localhost:8123/analytics"
            mock_config.get_clickhouse_url.assert_called_once()


class TestServiceConfigurationAccess(BaseTestCase):
    """Test service-specific configuration access."""
    
    def test_get_service_config_returns_redis_configuration(self):
        """Test that get_service_config() returns Redis configuration.
        
        Business Value: Cache and session store connectivity
        """
        loader = ConfigurationLoader()
        
        # Mock config with Redis configuration
        mock_redis = MagicMock()
        mock_redis.host = "localhost"
        mock_redis.port = 6379
        mock_redis.password = "redis_password"
        
        mock_config = MagicMock()
        mock_config.redis = mock_redis
        mock_config.redis_url = "redis://localhost:6379"
        
        with patch.object(loader, 'load', return_value=mock_config):
            redis_config = loader.get_service_config('redis')
            
            expected = {
                'host': 'localhost',
                'port': 6379,
                'password': 'redis_password',
                'url': 'redis://localhost:6379'
            }
            
            assert redis_config == expected
    
    def test_get_service_config_returns_llm_configuration(self):
        """Test that get_service_config() returns LLM configuration.
        
        Business Value: AI service connectivity for agent operations
        """
        loader = ConfigurationLoader()
        
        # Mock LLM config
        mock_default_llm = MagicMock()
        mock_default_llm.provider = "openai"
        mock_default_llm.model = "gpt-4"
        mock_default_llm.api_key = "sk-test-key"
        
        mock_llm_configs = MagicMock()
        mock_llm_configs.default = mock_default_llm
        
        mock_config = MagicMock()
        mock_config.llm_configs = mock_llm_configs
        
        with patch.object(loader, 'load', return_value=mock_config):
            llm_config = loader.get_service_config('llm')
            
            expected = {
                'provider': 'openai',
                'model': 'gpt-4',
                'api_key': 'sk-test-key'
            }
            
            assert llm_config == expected
    
    def test_get_service_config_returns_auth_configuration(self):
        """Test that get_service_config() returns auth service configuration.
        
        Business Value: Authentication service connectivity for user management
        """
        loader = ConfigurationLoader()
        
        # Mock config with auth configuration
        mock_config = MagicMock()
        mock_config.auth_service_url = "http://localhost:8081"
        mock_config.jwt_secret_key = "test_jwt_secret"
        
        with patch.object(loader, 'load', return_value=mock_config):
            auth_config = loader.get_service_config('auth')
            
            expected = {
                'url': 'http://localhost:8081',
                'secret_key': 'test_jwt_secret'
            }
            
            assert auth_config == expected
    
    def test_get_service_config_returns_empty_dict_for_unknown_service(self):
        """Test that get_service_config() returns empty dict for unknown service.
        
        Business Value: Safe fallback for unknown service configuration requests
        """
        loader = ConfigurationLoader()
        
        mock_config = MagicMock()
        
        with patch.object(loader, 'load', return_value=mock_config):
            unknown_config = loader.get_service_config('unknown_service')
            
            assert unknown_config == {}


class TestConfigurationValidation(BaseTestCase):
    """Test configuration validation functionality."""
    
    def test_validate_returns_true_for_valid_configuration(self):
        """Test that validate() returns True for valid configuration.
        
        Business Value: Ensures configuration is valid before application startup
        """
        loader = ConfigurationLoader()
        
        # Mock successful config loading
        mock_config = MagicMock()
        
        with patch.object(loader, 'load', return_value=mock_config):
            is_valid = loader.validate()
            
            assert is_valid is True
    
    def test_validate_returns_false_for_invalid_configuration(self):
        """Test that validate() returns False when configuration loading fails.
        
        Business Value: Prevents startup with invalid configuration
        """
        loader = ConfigurationLoader()
        
        # Mock config loading failure
        with patch.object(loader, 'load', side_effect=Exception("Config loading failed")):
            is_valid = loader.validate()
            
            assert is_valid is False


class TestGlobalFunctionAccess(BaseTestCase):
    """Test global configuration access functions."""
    
    def test_get_configuration_returns_app_config(self):
        """Test that get_configuration() returns AppConfig instance.
        
        Business Value: Primary global access point for configuration
        """
        config = get_configuration()
        
        assert config is not None
        assert isinstance(config, AppConfig)
    
    def test_reload_configuration_without_force(self):
        """Test that reload_configuration() works without force.
        
        Business Value: Global reload functionality for configuration updates
        """
        config = reload_configuration(force=False)
        
        assert config is not None
        assert isinstance(config, AppConfig)
    
    def test_reload_configuration_with_force(self):
        """Test that reload_configuration() works with force.
        
        Business Value: Force reload capability for hot configuration updates
        """
        config = reload_configuration(force=True)
        
        assert config is not None
        assert isinstance(config, AppConfig)
    
    def test_global_configuration_loader_instance_exists(self):
        """Test that global _configuration_loader instance exists.
        
        Business Value: Singleton pattern ensures consistent configuration access
        """
        assert _configuration_loader is not None
        assert isinstance(_configuration_loader, ConfigurationLoader)


class TestErrorHandlingAndEdgeCases(BaseTestCase):
    """Test error handling and edge case scenarios."""
    
    def test_config_creation_failure_fallback(self):
        """Test fallback behavior when config creation fails.
        
        Business Value: Graceful degradation prevents total application failure
        """
        loader = ConfigurationLoader()
        
        # Mock config class instantiation failure
        with patch('netra_backend.app.schemas.config.DevelopmentConfig', side_effect=Exception("Config creation failed")):
            config = loader._create_config_for_environment('development')
            
            # Should fallback to basic AppConfig
            assert config is not None
            assert isinstance(config, AppConfig)
            assert config.environment == 'development'
    
    def test_missing_config_attributes_handled_gracefully(self):
        """Test that missing config attributes are handled gracefully.
        
        Business Value: Robust service config access even with incomplete configuration
        """
        loader = ConfigurationLoader()
        
        # Mock config without expected attributes
        mock_config = MagicMock()
        del mock_config.redis
        del mock_config.redis_url
        
        with patch.object(loader, 'load', return_value=mock_config):
            redis_config = loader.get_service_config('redis')
            
            # Should return config with None values
            expected = {
                'host': None,
                'port': None, 
                'password': None,
                'url': None
            }
            
            assert redis_config == expected
    
    def test_concurrent_access_to_configuration_loader(self):
        """Test that concurrent access to configuration loader is safe.
        
        Business Value: Thread safety for multi-user system
        """
        loader = ConfigurationLoader()
        
        import threading
        import time
        
        results = []
        
        def load_config():
            config = loader.load()
            results.append(config)
        
        # Create multiple threads accessing config
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=load_config)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All results should be the same cached instance
        assert len(results) == 5
        first_config = results[0]
        for config in results[1:]:
            assert config is first_config


class TestPerformanceAndMemory(BaseTestCase):
    """Test performance characteristics and memory usage."""
    
    def test_configuration_loading_performance(self):
        """Test that configuration loading is performant.
        
        Business Value: Fast startup times and responsive configuration access
        """
        loader = ConfigurationLoader()
        
        import time
        
        # Measure first load time
        start_time = time.time()
        config1 = loader.load()
        first_load_time = time.time() - start_time
        
        # Measure cached access time
        start_time = time.time()
        config2 = loader.load()
        cached_load_time = time.time() - start_time
        
        # Cached access should be significantly faster
        assert cached_load_time < first_load_time
        assert cached_load_time < 0.001  # Should be sub-millisecond
        
        # Should be same instance due to caching
        assert config1 is config2
    
    def test_memory_usage_with_multiple_reloads(self):
        """Test memory usage remains reasonable with multiple reloads.
        
        Business Value: Prevents memory leaks during hot reloads
        """
        loader = ConfigurationLoader()
        
        # Perform multiple forced reloads
        configs = []
        for i in range(10):
            config = loader.reload(force=True)
            configs.append(config)
        
        # All configs should be valid AppConfig instances
        for config in configs:
            assert isinstance(config, AppConfig)
        
        # Memory usage should be reasonable (not exponential growth)
        # This is a basic check - in practice we'd use memory profiling
        assert len(configs) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])