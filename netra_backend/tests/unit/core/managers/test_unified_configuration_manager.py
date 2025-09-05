"""
Comprehensive Unit Tests for UnifiedConfigurationManager SSOT class.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction
- Business Goal: Ensure reliable configuration management across all services
- Value Impact: Prevents configuration drift and environment inconsistencies
- Strategic Impact: Validates SSOT configuration consolidation for operational stability

CRITICAL: These tests focus on basic functionality and normal use cases.
Tests are designed to be failing initially to identify gaps in the implementation.
"""

import pytest
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import Dict, Any, List, Optional

# Under test
from netra_backend.app.core.managers.unified_configuration_manager import (
    UnifiedConfigurationManager,
    ConfigurationManagerFactory,
    ConfigurationEntry,
    ConfigurationScope,
    ConfigurationSource,
    ConfigurationStatus,
    ConfigurationValidationResult,
    get_configuration_manager,
    get_dashboard_config_manager,
    get_data_agent_config_manager,
    get_llm_config_manager
)


class TestConfigurationEntry:
    """Test ConfigurationEntry class functionality."""
    
    def test_configuration_entry_creation_with_all_fields(self):
        """Test creating a ConfigurationEntry with all fields populated."""
        entry = ConfigurationEntry(
            key="test.key",
            value="test_value",
            source=ConfigurationSource.ENVIRONMENT,
            scope=ConfigurationScope.USER,
            data_type=str,
            required=True,
            sensitive=False,
            description="Test configuration",
            validation_rules=["not_empty"],
            environment="staging",
            service="backend",
            user_id="user123"
        )
        
        assert entry.key == "test.key"
        assert entry.value == "test_value"
        assert entry.source == ConfigurationSource.ENVIRONMENT
        assert entry.scope == ConfigurationScope.USER
        assert entry.data_type == str
        assert entry.required is True
        assert entry.sensitive is False
        assert entry.description == "Test configuration"
        assert entry.validation_rules == ["not_empty"]
        assert entry.environment == "staging"
        assert entry.service == "backend"
        assert entry.user_id == "user123"
    
    def test_configuration_entry_sensitive_value_masking(self):
        """Test that sensitive values are properly masked for display."""
        entry = ConfigurationEntry(
            key="secret.key",
            value="super_secret_password",
            source=ConfigurationSource.ENVIRONMENT,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            sensitive=True
        )
        
        # Display value should be masked
        display_value = entry.get_display_value()
        assert display_value != "super_secret_password"
        assert "su" in display_value  # First two chars
        assert "rd" in display_value  # Last two chars
        assert "*" in display_value   # Masked portion
        
        # But original value should still be accessible
        assert entry.value == "super_secret_password"
    
    def test_configuration_entry_short_sensitive_value_masking(self):
        """Test sensitive value masking for short values."""
        entry = ConfigurationEntry(
            key="secret.key",
            value="abc",
            source=ConfigurationSource.ENVIRONMENT,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            sensitive=True
        )
        
        display_value = entry.get_display_value()
        assert display_value == "***"
    
    def test_configuration_entry_validate_type_coercion_int(self):
        """Test type validation and coercion for integer values."""
        entry = ConfigurationEntry(
            key="num.key",
            value="123",
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int
        )
        
        # Should validate and convert string to int
        assert entry.validate() is True
        assert entry.value == 123
        assert isinstance(entry.value, int)
    
    def test_configuration_entry_validate_type_coercion_float(self):
        """Test type validation and coercion for float values."""
        entry = ConfigurationEntry(
            key="float.key",
            value="123.45",
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=float
        )
        
        assert entry.validate() is True
        assert entry.value == 123.45
        assert isinstance(entry.value, float)
    
    def test_configuration_entry_validate_type_coercion_bool_true(self):
        """Test type validation and coercion for boolean true values."""
        for true_value in ["true", "1", "yes", "on"]:
            entry = ConfigurationEntry(
                key="bool.key",
                value=true_value,
                source=ConfigurationSource.DEFAULT,
                scope=ConfigurationScope.GLOBAL,
                data_type=bool
            )
            
            assert entry.validate() is True
            assert entry.value is True
    
    def test_configuration_entry_validate_type_coercion_bool_false(self):
        """Test type validation and coercion for boolean false values."""
        for false_value in ["false", "0", "no", "off"]:
            entry = ConfigurationEntry(
                key="bool.key",
                value=false_value,
                source=ConfigurationSource.DEFAULT,
                scope=ConfigurationScope.GLOBAL,
                data_type=bool
            )
            
            assert entry.validate() is True
            assert entry.value is False
    
    def test_configuration_entry_validate_invalid_type_conversion(self):
        """Test validation fails for invalid type conversion."""
        entry = ConfigurationEntry(
            key="invalid.key",
            value="not_a_number",
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int
        )
        
        assert entry.validate() is False
    
    def test_configuration_entry_validate_min_length_rule(self):
        """Test validation rule: min_length."""
        entry = ConfigurationEntry(
            key="string.key",
            value="short",
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            validation_rules=["min_length:10"]
        )
        
        assert entry.validate() is False
        
        entry.value = "long_enough_string"
        assert entry.validate() is True
    
    def test_configuration_entry_validate_max_length_rule(self):
        """Test validation rule: max_length."""
        entry = ConfigurationEntry(
            key="string.key",
            value="very_long_string_that_exceeds_limit",
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            validation_rules=["max_length:10"]
        )
        
        assert entry.validate() is False
        
        entry.value = "short"
        assert entry.validate() is True
    
    def test_configuration_entry_validate_min_value_rule(self):
        """Test validation rule: min_value."""
        entry = ConfigurationEntry(
            key="num.key",
            value=5,
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            validation_rules=["min_value:10"]
        )
        
        assert entry.validate() is False
        
        entry.value = 15
        assert entry.validate() is True
    
    def test_configuration_entry_validate_max_value_rule(self):
        """Test validation rule: max_value."""
        entry = ConfigurationEntry(
            key="num.key",
            value=15,
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            validation_rules=["max_value:10"]
        )
        
        assert entry.validate() is False
        
        entry.value = 5
        assert entry.validate() is True
    
    def test_configuration_entry_validate_not_empty_rule(self):
        """Test validation rule: not_empty."""
        entry = ConfigurationEntry(
            key="string.key",
            value="",
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            validation_rules=["not_empty"]
        )
        
        assert entry.validate() is False
        
        entry.value = "not empty"
        assert entry.validate() is True
    
    def test_configuration_entry_validate_positive_rule(self):
        """Test validation rule: positive."""
        entry = ConfigurationEntry(
            key="num.key",
            value=-5,
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            validation_rules=["positive"]
        )
        
        assert entry.validate() is False
        
        entry.value = 5
        assert entry.validate() is True
    
    def test_configuration_entry_validate_non_negative_rule(self):
        """Test validation rule: non_negative."""
        entry = ConfigurationEntry(
            key="num.key",
            value=-1,
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            validation_rules=["non_negative"]
        )
        
        assert entry.validate() is False
        
        entry.value = 0
        assert entry.validate() is True
        
        entry.value = 5
        assert entry.validate() is True
    
    def test_configuration_entry_validate_regex_rule(self):
        """Test validation rule: regex."""
        entry = ConfigurationEntry(
            key="email.key",
            value="invalid-email",
            source=ConfigurationSource.DEFAULT,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            validation_rules=[r"regex:^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"]
        )
        
        assert entry.validate() is False
        
        entry.value = "user@example.com"
        assert entry.validate() is True


class TestUnifiedConfigurationManagerBasic:
    """Test basic functionality of UnifiedConfigurationManager."""
    
    @patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment')
    def test_manager_initialization_defaults(self, mock_env):
        """Test manager initialization with default parameters."""
        mock_env_instance = Mock()
        mock_env_instance.get.return_value = None
        mock_env.return_value = mock_env_instance
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('pathlib.Path.exists', return_value=False):
                manager = UnifiedConfigurationManager()
        
        assert manager.user_id is None
        assert manager.service_name is None
        assert manager.enable_validation is True
        assert manager.enable_caching is True
        assert manager.cache_ttl == 300
        assert manager.environment == 'development'  # Default fallback
    
    @patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment')
    def test_manager_initialization_with_parameters(self, mock_env):
        """Test manager initialization with custom parameters."""
        mock_env_instance = Mock()
        mock_env_instance.get.return_value = None
        mock_env.return_value = mock_env_instance
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('pathlib.Path.exists', return_value=False):
                manager = UnifiedConfigurationManager(
                    user_id="test_user",
                    environment="staging",
                    service_name="test_service",
                    enable_validation=False,
                    enable_caching=False,
                    cache_ttl=600
                )
        
        assert manager.user_id == "test_user"
        assert manager.service_name == "test_service"
        assert manager.enable_validation is False
        assert manager.enable_caching is False
        assert manager.cache_ttl == 600
        assert manager.environment == "staging"
    
    @patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment')
    def test_environment_detection_from_environment_var(self, mock_env):
        """Test environment detection from ENVIRONMENT variable."""
        mock_env_instance = Mock()
        mock_env_instance.get.side_effect = lambda key: {
            'ENVIRONMENT': 'production',
            'STAGE': None,
            'ENV': None,
            'DEPLOYMENT_ENV': None
        }.get(key)
        mock_env.return_value = mock_env_instance
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('pathlib.Path.exists', return_value=False):
                manager = UnifiedConfigurationManager()
        
        assert manager.environment == "production"
    
    @patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment')
    def test_environment_detection_fallback_chain(self, mock_env):
        """Test environment detection fallback chain."""
        mock_env_instance = Mock()
        mock_env_instance.get.side_effect = lambda key: {
            'ENVIRONMENT': None,
            'STAGE': None,
            'ENV': 'test',
            'DEPLOYMENT_ENV': None
        }.get(key)
        mock_env.return_value = mock_env_instance
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('pathlib.Path.exists', return_value=False):
                manager = UnifiedConfigurationManager()
        
        assert manager.environment == "test"
    
    @patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment')
    def test_default_configurations_loaded(self, mock_env):
        """Test that default configurations are loaded during initialization."""
        mock_env_instance = Mock()
        mock_env_instance.get.return_value = None
        mock_env.return_value = mock_env_instance
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('pathlib.Path.exists', return_value=False):
                manager = UnifiedConfigurationManager()
        
        # Check some default configurations exist
        assert manager.exists("system.debug")
        assert manager.exists("database.pool_size")
        assert manager.exists("redis.max_connections")
        assert manager.exists("llm.timeout")
        
        # Verify default values
        assert manager.get("system.debug") is False
        assert manager.get("database.pool_size") == 10
        assert manager.get("redis.max_connections") == 50
        assert manager.get("llm.timeout") == 30.0


class TestConfigurationAccess:
    """Test configuration access methods."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mocked configuration manager."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager()
        return manager
    
    def test_get_existing_configuration(self, mock_manager):
        """Test getting an existing configuration value."""
        value = mock_manager.get("system.debug")
        assert value is False  # Default value
    
    def test_get_nonexistent_configuration_with_default(self, mock_manager):
        """Test getting a non-existent configuration with default."""
        value = mock_manager.get("nonexistent.key", "default_value")
        assert value == "default_value"
    
    def test_get_nonexistent_configuration_without_default(self, mock_manager):
        """Test getting a non-existent configuration without default."""
        value = mock_manager.get("nonexistent.key")
        assert value is None
    
    def test_get_with_type_coercion_int(self, mock_manager):
        """Test getting value with integer type coercion."""
        # Set a string value
        mock_manager.set("test.number", "123")
        
        # Get with int coercion
        value = mock_manager.get("test.number", data_type=int)
        assert value == 123
        assert isinstance(value, int)
    
    def test_get_with_type_coercion_bool_true(self, mock_manager):
        """Test getting value with boolean type coercion for true values."""
        mock_manager.set("test.bool", "true")
        value = mock_manager.get("test.bool", data_type=bool)
        assert value is True
    
    def test_get_with_type_coercion_bool_false(self, mock_manager):
        """Test getting value with boolean type coercion for false values."""
        mock_manager.set("test.bool", "false")
        value = mock_manager.get("test.bool", data_type=bool)
        assert value is False
    
    def test_get_with_failed_type_coercion(self, mock_manager):
        """Test getting value with failed type coercion."""
        mock_manager.set("test.invalid", "not_a_number")
        
        # Should log warning and return original value
        with patch('netra_backend.app.core.managers.unified_configuration_manager.logger') as mock_logger:
            value = mock_manager.get("test.invalid", data_type=int)
            assert value == "not_a_number"
            mock_logger.warning.assert_called_once()
    
    def test_get_int_method(self, mock_manager):
        """Test get_int convenience method."""
        mock_manager.set("test.number", "456")
        value = mock_manager.get_int("test.number")
        assert value == 456
        assert isinstance(value, int)
    
    def test_get_int_method_with_default(self, mock_manager):
        """Test get_int method with default value."""
        value = mock_manager.get_int("nonexistent.key", 999)
        assert value == 999
    
    def test_get_float_method(self, mock_manager):
        """Test get_float convenience method."""
        mock_manager.set("test.float", "123.45")
        value = mock_manager.get_float("test.float")
        assert value == 123.45
        assert isinstance(value, float)
    
    def test_get_bool_method(self, mock_manager):
        """Test get_bool convenience method."""
        mock_manager.set("test.bool", "yes")
        value = mock_manager.get_bool("test.bool")
        assert value is True
    
    def test_get_str_method(self, mock_manager):
        """Test get_str convenience method."""
        mock_manager.set("test.string", 123)
        value = mock_manager.get_str("test.string")
        assert value == "123"
        assert isinstance(value, str)
    
    def test_get_list_method_json_array(self, mock_manager):
        """Test get_list method with JSON array string."""
        mock_manager.set("test.list", '["item1", "item2", "item3"]')
        value = mock_manager.get_list("test.list")
        assert value == ["item1", "item2", "item3"]
    
    def test_get_list_method_comma_separated(self, mock_manager):
        """Test get_list method with comma-separated string."""
        mock_manager.set("test.list", "item1, item2, item3")
        value = mock_manager.get_list("test.list")
        assert value == ["item1", "item2", "item3"]
    
    def test_get_list_method_single_value(self, mock_manager):
        """Test get_list method with single value."""
        mock_manager.set("test.list", "single_item")
        value = mock_manager.get_list("test.list")
        assert value == ["single_item"]
    
    def test_get_dict_method_json(self, mock_manager):
        """Test get_dict method with JSON string."""
        mock_manager.set("test.dict", '{"key": "value", "number": 123}')
        value = mock_manager.get_dict("test.dict")
        assert value == {"key": "value", "number": 123}
    
    def test_get_dict_method_invalid_json(self, mock_manager):
        """Test get_dict method with invalid JSON."""
        mock_manager.set("test.dict", "not json")
        value = mock_manager.get_dict("test.dict", {"default": "value"})
        assert value == {"default": "value"}
    
    def test_set_configuration_basic(self, mock_manager):
        """Test setting a configuration value."""
        mock_manager.set("new.config", "test_value")
        
        assert mock_manager.exists("new.config")
        assert mock_manager.get("new.config") == "test_value"
    
    def test_set_configuration_with_source(self, mock_manager):
        """Test setting configuration with specific source."""
        mock_manager.set("new.config", "test_value", ConfigurationSource.ENVIRONMENT)
        
        # Get the configuration entry to verify source
        entry = mock_manager._configurations.get("new.config")
        assert entry is not None
        assert entry.source == ConfigurationSource.ENVIRONMENT
    
    def test_set_configuration_overwrites_existing(self, mock_manager):
        """Test setting configuration overwrites existing value."""
        mock_manager.set("test.key", "original")
        assert mock_manager.get("test.key") == "original"
        
        mock_manager.set("test.key", "updated")
        assert mock_manager.get("test.key") == "updated"
    
    def test_delete_existing_configuration(self, mock_manager):
        """Test deleting an existing configuration."""
        mock_manager.set("temp.key", "temp_value")
        assert mock_manager.exists("temp.key")
        
        result = mock_manager.delete("temp.key")
        assert result is True
        assert not mock_manager.exists("temp.key")
    
    def test_delete_nonexistent_configuration(self, mock_manager):
        """Test deleting a non-existent configuration."""
        result = mock_manager.delete("nonexistent.key")
        assert result is False
    
    def test_exists_method(self, mock_manager):
        """Test configuration existence check."""
        assert mock_manager.exists("system.debug") is True
        assert mock_manager.exists("nonexistent.key") is False
    
    def test_keys_method_no_pattern(self, mock_manager):
        """Test getting all configuration keys without pattern."""
        keys = mock_manager.keys()
        assert isinstance(keys, list)
        assert len(keys) > 0
        assert "system.debug" in keys
        assert "database.pool_size" in keys
    
    def test_keys_method_with_pattern(self, mock_manager):
        """Test getting configuration keys with regex pattern."""
        keys = mock_manager.keys(pattern="system\\..*")
        assert isinstance(keys, list)
        assert all(key.startswith("system.") for key in keys)
        assert "system.debug" in keys
    
    def test_get_all_configurations_exclude_sensitive(self, mock_manager):
        """Test getting all configurations excluding sensitive values."""
        # Add a sensitive configuration
        mock_manager.set("secret.key", "secret_value")
        mock_manager._sensitive_keys.add("secret.key")
        mock_manager._configurations["secret.key"].sensitive = True
        
        all_configs = mock_manager.get_all(include_sensitive=False)
        assert isinstance(all_configs, dict)
        assert "system.debug" in all_configs
        
        # Sensitive value should be masked
        if "secret.key" in all_configs:
            assert all_configs["secret.key"] != "secret_value"
    
    def test_get_all_configurations_include_sensitive(self, mock_manager):
        """Test getting all configurations including sensitive values."""
        mock_manager.set("secret.key", "secret_value")
        
        all_configs = mock_manager.get_all(include_sensitive=True)
        assert isinstance(all_configs, dict)
        assert "secret.key" in all_configs
        assert all_configs["secret.key"] == "secret_value"


class TestConfigurationCaching:
    """Test configuration caching functionality."""
    
    @pytest.fixture
    def cached_manager(self):
        """Create a configuration manager with caching enabled."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager(enable_caching=True, cache_ttl=1)
        return manager
    
    def test_cache_stores_retrieved_values(self, cached_manager):
        """Test that cache stores retrieved values."""
        # First access
        value1 = cached_manager.get("system.debug")
        
        # Value should be in cache
        assert "system.debug" in cached_manager._cache
        assert cached_manager._cache["system.debug"] == value1
    
    def test_cache_returns_cached_values(self, cached_manager):
        """Test that subsequent accesses return cached values."""
        # First access
        value1 = cached_manager.get("system.debug")
        
        # Modify the underlying configuration
        cached_manager._configurations["system.debug"].value = "modified"
        
        # Second access should return cached value
        value2 = cached_manager.get("system.debug")
        assert value2 == value1  # Should be cached value, not modified
    
    def test_cache_ttl_expiration(self, cached_manager):
        """Test that cache entries expire after TTL."""
        # First access
        value1 = cached_manager.get("system.debug")
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Modify underlying value
        cached_manager._configurations["system.debug"].value = "modified"
        
        # Second access should get updated value
        value2 = cached_manager.get("system.debug")
        assert value2 == "modified"
    
    def test_set_clears_cache_for_key(self, cached_manager):
        """Test that setting a value clears cache for that key."""
        # Get value to cache it
        original_value = cached_manager.get("system.debug")
        assert "system.debug" in cached_manager._cache
        
        # Set new value
        cached_manager.set("system.debug", True)
        
        # Cache should be cleared for this key
        assert "system.debug" not in cached_manager._cache
        
        # Get should return new value
        assert cached_manager.get("system.debug") is True
    
    def test_delete_clears_cache_for_key(self, cached_manager):
        """Test that deleting a value clears cache for that key."""
        cached_manager.set("temp.key", "temp_value")
        
        # Get value to cache it
        cached_manager.get("temp.key")
        assert "temp.key" in cached_manager._cache
        
        # Delete the configuration
        cached_manager.delete("temp.key")
        
        # Cache should be cleared for this key
        assert "temp.key" not in cached_manager._cache
    
    def test_clear_cache_single_key(self, cached_manager):
        """Test clearing cache for a single key."""
        cached_manager.get("system.debug")
        cached_manager.get("database.pool_size")
        
        assert "system.debug" in cached_manager._cache
        assert "database.pool_size" in cached_manager._cache
        
        cached_manager.clear_cache("system.debug")
        
        assert "system.debug" not in cached_manager._cache
        assert "database.pool_size" in cached_manager._cache
    
    def test_clear_cache_all_keys(self, cached_manager):
        """Test clearing entire cache."""
        cached_manager.get("system.debug")
        cached_manager.get("database.pool_size")
        
        assert len(cached_manager._cache) > 0
        
        cached_manager.clear_cache()
        
        assert len(cached_manager._cache) == 0
    
    def test_disabled_caching(self):
        """Test manager with caching disabled."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager(enable_caching=False)
        
        # Access value multiple times
        value1 = manager.get("system.debug")
        value2 = manager.get("system.debug")
        
        # Cache should remain empty
        assert len(manager._cache) == 0


class TestServiceSpecificConfigurations:
    """Test service-specific configuration methods."""
    
    @pytest.fixture
    def manager(self):
        """Create a configuration manager for testing."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as mock_env_class:
            mock_env_instance = Mock()
            mock_env_instance.get.return_value = None
            mock_env_class.return_value = mock_env_instance
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager()
        return manager
    
    def test_get_database_config_defaults(self, manager):
        """Test getting database configuration with defaults."""
        config = manager.get_database_config()
        
        assert isinstance(config, dict)
        assert config["pool_size"] == 10  # Default
        assert config["max_overflow"] == 20  # Default
        assert config["pool_timeout"] == 30  # Default
        assert config["pool_recycle"] == 3600  # Default
        assert config["echo"] is False  # Default
    
    def test_get_database_config_custom_values(self, manager):
        """Test getting database configuration with custom values."""
        manager.set("database.url", "postgresql://test:test@localhost/test")
        manager.set("database.pool_size", 20)
        manager.set("database.echo", True)
        
        config = manager.get_database_config()
        
        assert config["url"] == "postgresql://test:test@localhost/test"
        assert config["pool_size"] == 20
        assert config["echo"] is True
    
    def test_get_redis_config_defaults(self, manager):
        """Test getting Redis configuration with defaults."""
        config = manager.get_redis_config()
        
        assert isinstance(config, dict)
        assert config["max_connections"] == 50  # Default
        assert config["socket_timeout"] == 5.0  # Default
        assert config["socket_connect_timeout"] == 5.0  # Default
        assert config["retry_on_timeout"] is True  # Default
        assert config["health_check_interval"] == 30  # Default
    
    def test_get_redis_config_custom_values(self, manager):
        """Test getting Redis configuration with custom values."""
        manager.set("redis.url", "redis://localhost:6379")
        manager.set("redis.max_connections", 100)
        manager.set("redis.socket_timeout", 10.0)
        
        config = manager.get_redis_config()
        
        assert config["url"] == "redis://localhost:6379"
        assert config["max_connections"] == 100
        assert config["socket_timeout"] == 10.0
    
    def test_get_llm_config_structure(self, manager):
        """Test getting LLM configuration structure."""
        config = manager.get_llm_config()
        
        assert isinstance(config, dict)
        assert "timeout" in config
        assert "max_retries" in config
        assert "retry_delay" in config
        assert "openai" in config
        assert "anthropic" in config
        
        # Check nested OpenAI config
        assert isinstance(config["openai"], dict)
        assert "api_key" in config["openai"]
        assert "model" in config["openai"]
        
        # Check nested Anthropic config
        assert isinstance(config["anthropic"], dict)
        assert "api_key" in config["anthropic"]
        assert "model" in config["anthropic"]
    
    def test_get_agent_config_defaults(self, manager):
        """Test getting agent configuration with defaults."""
        config = manager.get_agent_config()
        
        assert isinstance(config, dict)
        assert config["execution_timeout"] == 300.0  # Default
        assert config["max_concurrent"] == 5  # Default
        assert config["health_check_interval"] == 30.0  # Default
        
        # Check circuit breaker config
        assert "circuit_breaker" in config
        cb_config = config["circuit_breaker"]
        assert cb_config["failure_threshold"] == 5
        assert cb_config["recovery_timeout"] == 60
    
    def test_get_websocket_config_defaults(self, manager):
        """Test getting WebSocket configuration with defaults."""
        config = manager.get_websocket_config()
        
        assert isinstance(config, dict)
        assert config["ping_interval"] == 20  # Default
        assert config["ping_timeout"] == 10  # Default
        assert config["max_connections"] == 1000  # Default
        assert config["message_queue_size"] == 100  # Default
        assert config["close_timeout"] == 10  # Default
    
    def test_get_security_config_defaults(self, manager):
        """Test getting security configuration with defaults."""
        config = manager.get_security_config()
        
        assert isinstance(config, dict)
        assert config["jwt_algorithm"] == "HS256"  # Default
        assert config["jwt_expire_minutes"] == 30  # Default
        assert config["password_min_length"] == 8  # Default
        assert config["max_login_attempts"] == 5  # Default
        assert config["require_https"] is True  # Default
    
    def test_get_dashboard_config_defaults(self, manager):
        """Test getting dashboard configuration with defaults."""
        config = manager.get_dashboard_config()
        
        assert isinstance(config, dict)
        assert config["refresh_interval"] == 30  # Default
        assert config["max_data_points"] == 1000  # Default
        assert config["auto_refresh"] is True  # Default
        assert config["theme"] == "light"  # Default
        
        # Check charts config
        assert "charts" in config
        charts_config = config["charts"]
        assert charts_config["animation_duration"] == 300
        assert charts_config["show_legends"] is True


class TestConfigurationValidation:
    """Test configuration validation functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a configuration manager for validation testing."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager(enable_validation=True)
        return manager
    
    def test_validate_all_configurations_success(self, manager):
        """Test validating all configurations when everything is valid."""
        result = manager.validate_all_configurations()
        
        assert isinstance(result, ConfigurationValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.critical_errors) == 0
    
    def test_validation_disabled_manager(self):
        """Test that validation can be disabled."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager(enable_validation=False)
        
        # Set an invalid value that would normally fail validation
        manager.set("invalid.key", "")
        # Should succeed since validation is disabled
        assert manager.get("invalid.key") == ""
    
    def test_add_validation_schema(self, manager):
        """Test adding a validation schema."""
        schema = {
            "test.required_key": {
                "required": True,
                "sensitive": False,
                "deprecated": False
            },
            "test.sensitive_key": {
                "required": False,
                "sensitive": True,
                "deprecated": False
            },
            "test.deprecated_key": {
                "required": False,
                "sensitive": False,
                "deprecated": True
            }
        }
        
        manager.add_validation_schema(schema)
        
        # Check that schema is applied
        assert "test.required_key" in manager._required_keys
        assert "test.sensitive_key" in manager._sensitive_keys
        assert "test.deprecated_key" in manager._deprecated_keys
    
    def test_set_with_validation_failure(self, manager):
        """Test setting value that fails validation."""
        # Create a configuration entry that will fail validation
        manager.set("test.key", "valid_value")
        
        # Add validation rule that will cause failure
        manager._configurations["test.key"].validation_rules = ["min_length:20"]
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            manager.set("test.key", "short")


class TestConfigurationChangeTracking:
    """Test configuration change tracking and auditing."""
    
    @pytest.fixture
    def manager(self):
        """Create a configuration manager for change tracking testing."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager()
        return manager
    
    def test_change_tracking_on_set(self, manager):
        """Test that configuration changes are tracked when values are set."""
        initial_history_length = len(manager._change_history)
        
        manager.set("test.key", "new_value")
        
        assert len(manager._change_history) == initial_history_length + 1
        
        # Check the change record
        change_record = manager._change_history[-1]
        assert change_record["key"] == "test.key"
        assert change_record["new_value"] == "new_value"
        assert change_record["old_value"] is None  # First time setting
        assert "timestamp" in change_record
    
    def test_change_tracking_on_update(self, manager):
        """Test that configuration changes are tracked when values are updated."""
        manager.set("test.key", "original_value")
        initial_history_length = len(manager._change_history)
        
        manager.set("test.key", "updated_value")
        
        assert len(manager._change_history) == initial_history_length + 1
        
        # Check the change record
        change_record = manager._change_history[-1]
        assert change_record["key"] == "test.key"
        assert change_record["old_value"] == "original_value"
        assert change_record["new_value"] == "updated_value"
    
    def test_change_tracking_on_delete(self, manager):
        """Test that configuration changes are tracked when values are deleted."""
        manager.set("test.key", "to_be_deleted")
        initial_history_length = len(manager._change_history)
        
        manager.delete("test.key")
        
        assert len(manager._change_history) == initial_history_length + 1
        
        # Check the change record
        change_record = manager._change_history[-1]
        assert change_record["key"] == "test.key"
        assert change_record["old_value"] == "to_be_deleted"
        assert change_record["new_value"] is None
    
    def test_get_change_history_with_limit(self, manager):
        """Test getting change history with limit."""
        # Make several changes
        for i in range(5):
            manager.set(f"test.key{i}", f"value{i}")
        
        history = manager.get_change_history(limit=3)
        
        assert len(history) == 3
        # Should get the 3 most recent changes
        assert history[-1]["key"] == "test.key4"
    
    def test_get_change_history_unlimited(self, manager):
        """Test getting all change history."""
        initial_count = len(manager.get_change_history(limit=-1))
        
        # Make some changes
        manager.set("test.key1", "value1")
        manager.set("test.key2", "value2")
        
        history = manager.get_change_history(limit=-1)
        assert len(history) >= initial_count + 2
    
    def test_change_listeners(self, manager):
        """Test configuration change listeners."""
        listener_calls = []
        
        def test_listener(key: str, old_value: Any, new_value: Any):
            listener_calls.append((key, old_value, new_value))
        
        manager.add_change_listener(test_listener)
        
        # Make a change
        manager.set("test.key", "test_value")
        
        assert len(listener_calls) == 1
        assert listener_calls[0] == ("test.key", None, "test_value")
        
        # Update the value
        manager.set("test.key", "updated_value")
        
        assert len(listener_calls) == 2
        assert listener_calls[1] == ("test.key", "test_value", "updated_value")
    
    def test_remove_change_listener(self, manager):
        """Test removing configuration change listeners."""
        listener_calls = []
        
        def test_listener(key: str, old_value: Any, new_value: Any):
            listener_calls.append((key, old_value, new_value))
        
        manager.add_change_listener(test_listener)
        manager.set("test.key1", "value1")
        assert len(listener_calls) == 1
        
        # Remove the listener
        manager.remove_change_listener(test_listener)
        manager.set("test.key2", "value2")
        
        # Listener should not have been called for the second change
        assert len(listener_calls) == 1
    
    def test_listener_exception_handling(self, manager):
        """Test that listener exceptions don't break configuration changes."""
        def failing_listener(key: str, old_value: Any, new_value: Any):
            raise Exception("Listener failed!")
        
        def working_listener(key: str, old_value: Any, new_value: Any):
            working_listener.called = True
        
        working_listener.called = False
        
        manager.add_change_listener(failing_listener)
        manager.add_change_listener(working_listener)
        
        # Change should succeed despite failing listener
        with patch('netra_backend.app.core.managers.unified_configuration_manager.logger') as mock_logger:
            manager.set("test.key", "test_value")
            
            # Configuration should be set
            assert manager.get("test.key") == "test_value"
            
            # Working listener should have been called
            assert working_listener.called is True
            
            # Warning should have been logged
            mock_logger.warning.assert_called()


class TestThreadSafety:
    """Test thread safety of configuration operations."""
    
    @pytest.fixture
    def manager(self):
        """Create a configuration manager for thread safety testing."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager()
        return manager
    
    def test_concurrent_reads(self, manager):
        """Test concurrent read operations are thread-safe."""
        manager.set("test.key", "test_value")
        results = []
        
        def read_config():
            for _ in range(10):
                value = manager.get("test.key")
                results.append(value)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=read_config)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All reads should return the same value
        assert len(results) == 50
        assert all(result == "test_value" for result in results)
    
    def test_concurrent_writes(self, manager):
        """Test concurrent write operations are thread-safe."""
        results = []
        
        def write_config(thread_id):
            for i in range(10):
                key = f"test.key_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                manager.set(key, value)
                results.append((key, value))
        
        # Start multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=write_config, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all writes were successful
        assert len(results) == 50
        for key, expected_value in results:
            actual_value = manager.get(key)
            assert actual_value == expected_value
    
    def test_concurrent_cache_operations(self, manager):
        """Test concurrent cache operations are thread-safe."""
        manager.set("test.key", "initial_value")
        cache_results = []
        
        def cache_operations():
            # Get value (should cache it)
            value1 = manager.get("test.key")
            cache_results.append(("get", value1))
            
            # Clear cache
            manager.clear_cache("test.key")
            cache_results.append(("clear", None))
            
            # Get value again (should re-cache)
            value2 = manager.get("test.key")
            cache_results.append(("get", value2))
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=cache_operations)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify operations completed without errors
        assert len(cache_results) == 9  # 3 operations * 3 threads


class TestConfigurationManagerFactory:
    """Test ConfigurationManagerFactory functionality."""
    
    def test_get_global_manager_singleton(self):
        """Test that global manager is a singleton."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager') as MockManager:
            mock_instance = Mock()
            MockManager.return_value = mock_instance
            
            # Clear any existing global manager
            ConfigurationManagerFactory._global_manager = None
            
            manager1 = ConfigurationManagerFactory.get_global_manager()
            manager2 = ConfigurationManagerFactory.get_global_manager()
            
            assert manager1 is manager2
            # Constructor should only be called once
            MockManager.assert_called_once()
    
    def test_get_user_manager_per_user(self):
        """Test that each user gets their own manager."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager') as MockManager:
            # Clear existing managers
            ConfigurationManagerFactory._user_managers.clear()
            
            # Configure mock to return different instances for different calls
            mock_manager1 = Mock()
            mock_manager2 = Mock()
            MockManager.side_effect = [mock_manager1, mock_manager2]
            
            manager1 = ConfigurationManagerFactory.get_user_manager("user1")
            manager2 = ConfigurationManagerFactory.get_user_manager("user2")
            manager1_again = ConfigurationManagerFactory.get_user_manager("user1")
            
            assert manager1 is not manager2  # Different users get different managers
            assert manager1 is manager1_again  # Same user gets same manager
    
    def test_get_service_manager_per_service(self):
        """Test that each service gets their own manager."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager') as MockManager:
            # Clear existing managers
            ConfigurationManagerFactory._service_managers.clear()
            
            # Configure mock to return different instances for different calls
            mock_manager1 = Mock()
            mock_manager2 = Mock()
            MockManager.side_effect = [mock_manager1, mock_manager2]
            
            manager1 = ConfigurationManagerFactory.get_service_manager("service1")
            manager2 = ConfigurationManagerFactory.get_service_manager("service2")
            manager1_again = ConfigurationManagerFactory.get_service_manager("service1")
            
            assert manager1 is not manager2  # Different services get different managers
            assert manager1 is manager1_again  # Same service gets same manager
    
    def test_get_manager_combined_user_service(self):
        """Test getting manager with both user_id and service_name."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager') as MockManager:
            # Clear existing managers
            ConfigurationManagerFactory._user_managers.clear()
            
            manager = ConfigurationManagerFactory.get_manager(
                user_id="test_user",
                service_name="test_service"
            )
            
            # Should be called with both parameters
            MockManager.assert_called_with(user_id="test_user", service_name="test_service")
    
    def test_get_manager_user_only(self):
        """Test getting manager with only user_id."""
        with patch.object(ConfigurationManagerFactory, 'get_user_manager') as mock_get_user:
            ConfigurationManagerFactory.get_manager(user_id="test_user")
            mock_get_user.assert_called_once_with("test_user")
    
    def test_get_manager_service_only(self):
        """Test getting manager with only service_name."""
        with patch.object(ConfigurationManagerFactory, 'get_service_manager') as mock_get_service:
            ConfigurationManagerFactory.get_manager(service_name="test_service")
            mock_get_service.assert_called_once_with("test_service")
    
    def test_get_manager_none(self):
        """Test getting manager with no parameters returns global manager."""
        with patch.object(ConfigurationManagerFactory, 'get_global_manager') as mock_get_global:
            ConfigurationManagerFactory.get_manager()
            mock_get_global.assert_called_once()
    
    def test_get_manager_count(self):
        """Test getting count of active managers."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager'):
            # Set up some managers
            ConfigurationManagerFactory._global_manager = Mock()
            ConfigurationManagerFactory._user_managers = {
                "user1": Mock(),
                "user2": Mock(),
                "user1:service1": Mock()  # Combined user+service
            }
            ConfigurationManagerFactory._service_managers = {
                "service1": Mock(),
                "service2": Mock()
            }
            
            counts = ConfigurationManagerFactory.get_manager_count()
            
            assert counts["global"] == 1
            assert counts["user_specific"] == 2  # user1, user2
            assert counts["service_specific"] == 2  # service1, service2
            assert counts["combined"] == 1  # user1:service1
            assert counts["total"] == 6
    
    def test_clear_all_caches(self):
        """Test clearing caches for all managers."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager'):
            # Set up mock managers
            global_manager = Mock()
            user_manager = Mock()
            service_manager = Mock()
            
            ConfigurationManagerFactory._global_manager = global_manager
            ConfigurationManagerFactory._user_managers = {"user1": user_manager}
            ConfigurationManagerFactory._service_managers = {"service1": service_manager}
            
            ConfigurationManagerFactory.clear_all_caches()
            
            # All managers should have clear_cache called
            global_manager.clear_cache.assert_called_once()
            user_manager.clear_cache.assert_called_once()
            service_manager.clear_cache.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_configuration_manager_function(self):
        """Test get_configuration_manager convenience function."""
        with patch.object(ConfigurationManagerFactory, 'get_manager') as mock_get_manager:
            get_configuration_manager(user_id="test_user", service_name="test_service")
            mock_get_manager.assert_called_once_with("test_user", "test_service")
    
    def test_get_dashboard_config_manager(self):
        """Test legacy compatibility function for dashboard config manager."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.get_configuration_manager') as mock_get:
            get_dashboard_config_manager()
            mock_get.assert_called_once_with(service_name="dashboard")
    
    def test_get_data_agent_config_manager(self):
        """Test legacy compatibility function for data agent config manager."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.get_configuration_manager') as mock_get:
            get_data_agent_config_manager()
            mock_get.assert_called_once_with(service_name="data_agent")
    
    def test_get_llm_config_manager(self):
        """Test legacy compatibility function for LLM config manager."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.get_configuration_manager') as mock_get:
            get_llm_config_manager()
            mock_get.assert_called_once_with(service_name="llm")


class TestStatusAndMonitoring:
    """Test status and monitoring functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a configuration manager for status testing."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager(
                        user_id="test_user",
                        service_name="test_service",
                        environment="test_env"
                    )
        return manager
    
    def test_get_status_basic_information(self, manager):
        """Test getting basic status information."""
        status = manager.get_status()
        
        assert isinstance(status, dict)
        assert status["user_id"] == "test_user"
        assert status["environment"] == "test_env"
        assert status["service_name"] == "test_service"
        assert isinstance(status["total_configurations"], int)
        assert status["total_configurations"] > 0
        assert status["validation_enabled"] is True
        assert status["caching_enabled"] is True
        assert status["cache_ttl"] == 300
    
    def test_get_status_validation_information(self, manager):
        """Test getting validation status information."""
        status = manager.get_status()
        
        assert "validation_status" in status
        validation_status = status["validation_status"]
        assert isinstance(validation_status["is_valid"], bool)
        assert isinstance(validation_status["error_count"], int)
        assert isinstance(validation_status["warning_count"], int)
        assert isinstance(validation_status["critical_error_count"], int)
        assert isinstance(validation_status["missing_required_count"], int)
    
    def test_get_status_source_breakdown(self, manager):
        """Test getting configuration source breakdown."""
        status = manager.get_status()
        
        assert "sources" in status
        sources = status["sources"]
        for source in ConfigurationSource:
            assert source.value in sources
            assert isinstance(sources[source.value], int)
    
    def test_get_status_scope_breakdown(self, manager):
        """Test getting configuration scope breakdown."""
        status = manager.get_status()
        
        assert "scopes" in status
        scopes = status["scopes"]
        for scope in ConfigurationScope:
            assert scope.value in scopes
            assert isinstance(scopes[scope.value], int)
    
    def test_get_health_status_healthy(self, manager):
        """Test getting health status when system is healthy."""
        health = manager.get_health_status()
        
        assert isinstance(health, dict)
        assert health["status"] == "healthy"
        assert health["validation_result"] is True
        assert health["critical_errors"] == 0
        assert health["missing_required"] == 0
        assert isinstance(health["total_configurations"], int)
    
    def test_get_health_status_unhealthy(self, manager):
        """Test getting health status when system is unhealthy."""
        # Add a required key that's missing
        manager._required_keys.add("missing.required.key")
        
        health = manager.get_health_status()
        
        assert health["status"] == "unhealthy"
        assert health["validation_result"] is False
        assert health["missing_required"] > 0


class TestWebSocketIntegration:
    """Test WebSocket integration functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a configuration manager for WebSocket testing."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager()
        return manager
    
    def test_set_websocket_manager(self, manager):
        """Test setting WebSocket manager."""
        mock_websocket_manager = Mock()
        
        manager.set_websocket_manager(mock_websocket_manager)
        
        assert manager._websocket_manager is mock_websocket_manager
        # Should have added WebSocket change listener
        assert len(manager._change_listeners) > 0
    
    def test_enable_disable_websocket_events(self, manager):
        """Test enabling/disabling WebSocket events."""
        # Default should be enabled
        assert manager._enable_websocket_events is True
        
        manager.enable_websocket_events(False)
        assert manager._enable_websocket_events is False
        
        manager.enable_websocket_events(True)
        assert manager._enable_websocket_events is True
    
    def test_websocket_change_notification(self, manager):
        """Test WebSocket change notifications."""
        mock_websocket_manager = Mock()
        mock_websocket_manager.broadcast_system_message = Mock()
        
        manager.set_websocket_manager(mock_websocket_manager)
        
        # Make a configuration change
        with patch('asyncio.create_task') as mock_create_task:
            manager.set("test.key", "test_value")
            
            # Should have attempted to create task for broadcasting
            mock_create_task.assert_called_once()
    
    def test_websocket_notification_disabled(self, manager):
        """Test WebSocket notifications when disabled."""
        mock_websocket_manager = Mock()
        manager.set_websocket_manager(mock_websocket_manager)
        manager.enable_websocket_events(False)
        
        # Make a configuration change
        with patch('asyncio.create_task') as mock_create_task:
            manager.set("test.key", "test_value")
            
            # Should not attempt to broadcast
            mock_create_task.assert_not_called()


class TestEnvironmentVariableLoading:
    """Test environment variable loading functionality."""
    
    def test_environment_variable_mapping(self):
        """Test that environment variables are correctly mapped to configuration keys."""
        mock_env_data = {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'REDIS_URL': 'redis://localhost:6379',
            'OPENAI_API_KEY': 'sk-test-key',
            'DEBUG': 'true',
            'LOG_LEVEL': 'DEBUG'
        }
        
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as MockEnv:
            mock_env_instance = Mock()
            mock_env_instance.get.side_effect = lambda key: mock_env_data.get(key)
            MockEnv.return_value = mock_env_instance
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager()
            
            # Check that environment variables were loaded
            assert manager.get("database.url") == "postgresql://test:test@localhost/test"
            assert manager.get("redis.url") == "redis://localhost:6379"
            assert manager.get("llm.openai.api_key") == "sk-test-key"
            assert manager.get("system.debug") is True  # Should be converted to boolean
            assert manager.get("system.log_level") == "DEBUG"
    
    def test_sensitive_environment_variables(self):
        """Test that sensitive environment variables are marked as sensitive."""
        mock_env_data = {
            'OPENAI_API_KEY': 'sk-secret-key',
            'JWT_SECRET_KEY': 'super-secret-jwt-key'
        }
        
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as MockEnv:
            mock_env_instance = Mock()
            mock_env_instance.get.side_effect = lambda key: mock_env_data.get(key)
            MockEnv.return_value = mock_env_instance
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('pathlib.Path.exists', return_value=False):
                    manager = UnifiedConfigurationManager()
            
            # Check that sensitive keys are in the sensitive set
            assert "llm.openai.api_key" in manager._sensitive_keys
            assert "security.jwt_secret" in manager._sensitive_keys


class TestConfigurationFileLoading:
    """Test configuration file loading functionality."""
    
    def test_json_configuration_file_loading(self):
        """Test loading configuration from JSON files."""
        config_data = {
            "database": {
                "pool_size": 25,
                "timeout": 60
            },
            "custom": {
                "setting": "value"
            }
        }
        
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as mock_env_class:
            mock_env_instance = Mock()
            mock_env_instance.get.return_value = None
            mock_env_class.return_value = mock_env_instance
            
            with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
                with patch('pathlib.Path.exists', return_value=True):
                    manager = UnifiedConfigurationManager()
            
            # Check that file configurations were loaded and flattened
            assert manager.get("database.pool_size") == 25
            assert manager.get("database.timeout") == 60
            assert manager.get("custom.setting") == "value"
    
    def test_configuration_file_not_found(self):
        """Test handling when configuration files don't exist."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('pathlib.Path.exists', return_value=False):
                # Should not raise exception when config files don't exist
                manager = UnifiedConfigurationManager()
                # Should still have default configurations
                assert manager.get("system.debug") is False
    
    def test_invalid_json_configuration_file(self):
        """Test handling of invalid JSON in configuration files."""
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment'):
            with patch('builtins.open', mock_open(read_data='invalid json {')):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('netra_backend.app.core.managers.unified_configuration_manager.logger') as mock_logger:
                        # Should not crash, but should log warning
                        manager = UnifiedConfigurationManager()
                        mock_logger.warning.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])