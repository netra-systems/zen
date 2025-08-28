"""Unit Tests for Unified Configuration System

These tests validate the core functionality of the unified configuration system
ensuring all components work correctly in isolation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict

from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_unified_config,
    reload_unified_config,
    validate_config_integrity,
)
from netra_backend.app.schemas.config import AppConfig


class TestUnifiedConfigManager:
    """Unit tests for UnifiedConfigManager class."""
    
    def test_singleton_pattern(self):
        """Test that UnifiedConfigManager follows singleton pattern."""
        manager1 = UnifiedConfigManager()
        manager2 = UnifiedConfigManager()
        assert manager1 is manager2
    
    def test_config_loading_caches_result(self):
        """Test that config is cached after first load."""
        manager = UnifiedConfigManager()
        config1 = manager.get_config()
        config2 = manager.get_config()
        assert config1 is config2
    
    def test_environment_detection(self):
        """Test environment detection logic."""
        manager = UnifiedConfigManager()
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'TESTING': ''}):
            env = manager._detect_environment()
            assert env == 'staging'
        
        with patch.dict('os.environ', {'TESTING': '1'}):
            env = manager._detect_environment()
            assert env == 'testing'
    
    def test_hot_reload_capability(self):
        """Test hot reload clears cache and reloads config."""
        manager = UnifiedConfigManager()
        # Mock: Generic component isolation for controlled unit testing
        manager._config_cache = Mock()
        manager._hot_reload_enabled = True
        
        with patch.object(manager, '_safe_log_info'):
            manager.reload_config(force=True)
            assert manager._config_cache is None
    
    def test_config_summary_generation(self):
        """Test configuration summary includes all key metrics."""
        manager = UnifiedConfigManager()
        with patch.object(manager, 'get_config') as mock_get_config:
            # Mock: Generic component isolation for controlled unit testing
            mock_config = Mock()
            mock_config.db_pool_size = 10
            mock_config.db_max_overflow = 20
            mock_config.db_pool_timeout = 60
            mock_config.db_pool_recycle = 3600
            mock_config.db_echo = False
            mock_config.db_echo_pool = False
            mock_config.environment = 'testing'
            mock_get_config.return_value = mock_config
            
            summary = manager.get_config_summary()
            
            assert 'environment' in summary
            assert 'database_configured' in summary
            assert 'hot_reload_enabled' in summary
            assert summary['database_configured'] is True
    
    def test_configuration_validation(self):
        """Test configuration integrity validation."""
        manager = UnifiedConfigManager()
        with patch.object(manager, 'get_config') as mock_config:
            # Mock: Generic component isolation for controlled unit testing
            mock_config.return_value = Mock()
            with patch.object(manager, '_check_configuration_consistency') as mock_check:
                mock_check.return_value = []
                valid, issues = manager.validate_configuration_integrity()
                assert valid is True
                assert len(issues) == 0
    
    def test_error_handling_with_fallback(self):
        """Test error handling falls back to safe defaults."""
        manager = UnifiedConfigManager()
        with patch.object(manager, '_get_logger', return_value=None):
            # Should use print fallback when logger unavailable
            # Mock: Component isolation for testing without external dependencies
            with patch('builtins.print') as mock_print:
                manager._safe_log_error("Test error")
                mock_print.assert_called_once()
    
    def test_config_class_selection_by_environment(self):
        """Test correct config class selected based on environment."""
        manager = UnifiedConfigManager()
        
        test_cases = [
            ('development', 'DevelopmentConfig'),
            ('staging', 'StagingConfig'),
            ('production', 'ProductionConfig'),
            ('testing', 'NetraTestingConfig'),
        ]
        
        for env, expected_class in test_cases:
            manager._environment = env
            config_class = manager._get_config_class_for_environment()
            assert config_class.__name__ == expected_class
    
    def test_environment_override_detection(self):
        """Test environment variable override detection."""
        manager = UnifiedConfigManager()
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://override',
            'REDIS_URL': 'redis://override',
        }):
            overrides = manager.get_environment_overrides()
            assert overrides['DATABASE_URL'] == 'postgresql://override'
            assert overrides['REDIS_URL'] == 'redis://override'
    
    def test_configuration_population_order(self):
        """Test configuration data is populated in correct order."""
        manager = UnifiedConfigManager()
        # Mock: Component isolation for controlled unit testing
        config = Mock(spec=AppConfig)
        
        with patch.object(manager._database_manager, 'populate_database_config') as mock_db:
            with patch.object(manager._services_manager, 'populate_service_config') as mock_svc:
                with patch.object(manager._secrets_manager, 'populate_secrets') as mock_secret:
                    manager._populate_configuration_data(config)
                    
                    # Verify all managers are called
                    mock_db.assert_called_once_with(config)
                    mock_svc.assert_called_once_with(config)
                    mock_secret.assert_called_once_with(config)


class TestDatabaseConfigFields:
    """Unit tests for database configuration fields."""
    
    def test_database_pool_settings(self):
        """Test database pool configuration fields."""
        config = get_unified_config()
        
        # Verify all database pool settings exist
        assert hasattr(config, 'db_pool_size')
        assert hasattr(config, 'db_max_overflow')
        assert hasattr(config, 'db_pool_timeout')
        assert hasattr(config, 'db_pool_recycle')
        assert hasattr(config, 'db_pool_pre_ping')
        
        # Verify default values
        assert config.db_pool_size == 20
        assert config.db_max_overflow == 30
        assert config.db_pool_timeout == 30
        assert config.db_pool_recycle == 1800
        assert config.db_pool_pre_ping is True
    
    def test_database_connection_settings(self):
        """Test database connection configuration fields."""
        config = get_unified_config()
        
        assert hasattr(config, 'db_max_connections')
        assert hasattr(config, 'db_connection_timeout')
        assert hasattr(config, 'db_statement_timeout')
        
        assert config.db_max_connections == 100
        assert config.db_connection_timeout == 10
        assert config.db_statement_timeout == 30000
    
    def test_database_advanced_settings(self):
        """Test advanced database configuration fields."""
        config = get_unified_config()
        
        assert hasattr(config, 'db_enable_read_write_split')
        assert hasattr(config, 'db_read_url')
        assert hasattr(config, 'db_write_url')
        assert hasattr(config, 'db_transaction_retry_attempts')
        
        assert config.db_enable_read_write_split is False
        assert config.db_transaction_retry_attempts == 3


class TestCacheConfigFields:
    """Unit tests for cache configuration fields."""
    
    def test_cache_basic_settings(self):
        """Test basic cache configuration fields."""
        config = get_unified_config()
        
        assert hasattr(config, 'cache_enabled')
        assert hasattr(config, 'cache_default_ttl')
        assert hasattr(config, 'cache_max_size')
        assert hasattr(config, 'cache_strategy')
        assert hasattr(config, 'cache_prefix')
        
        assert config.cache_enabled is True
        assert config.cache_default_ttl == 300
        assert config.cache_max_size == 1000
        assert config.cache_strategy == 'adaptive'
    
    def test_cache_adaptive_settings(self):
        """Test adaptive cache configuration fields."""
        config = get_unified_config()
        
        assert hasattr(config, 'cache_frequent_query_threshold')
        assert hasattr(config, 'cache_frequent_query_ttl_multiplier')
        assert hasattr(config, 'cache_slow_query_threshold')
        assert hasattr(config, 'cache_slow_query_ttl_multiplier')
        
        assert config.cache_frequent_query_threshold == 5
        assert config.cache_frequent_query_ttl_multiplier == 2.0


class TestConfigHelperFunctions:
    """Unit tests for configuration helper functions."""
    
    def test_get_unified_config_returns_appconfig(self):
        """Test get_unified_config returns AppConfig instance."""
        config = get_unified_config()
        assert isinstance(config, AppConfig)
    
    def test_reload_unified_config_delegates_to_manager(self):
        """Test reload function delegates to manager."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.config_manager.reload_config') as mock_reload:
            reload_unified_config(force=True)
            mock_reload.assert_called_once_with(force=True)
    
    def test_validate_config_integrity_returns_tuple(self):
        """Test validation returns proper tuple format."""
        valid, issues = validate_config_integrity()
        assert isinstance(valid, bool)
        assert isinstance(issues, list)


class TestAPIKeyConfiguration:
    """Unit tests for API key configuration fields."""
    
    def test_llm_api_key_fields(self):
        """Test LLM API key configuration fields."""
        config = get_unified_config()
        
        assert hasattr(config, 'gemini_api_key')
        assert hasattr(config, 'anthropic_api_key')
        assert hasattr(config, 'openai_api_key')
    
    def test_oauth_credential_fields(self):
        """Test OAuth credential configuration fields."""
        config = get_unified_config()
        
        assert hasattr(config, 'google_client_id')
        assert hasattr(config, 'google_client_secret')
        assert hasattr(config, 'google_oauth_client_id')