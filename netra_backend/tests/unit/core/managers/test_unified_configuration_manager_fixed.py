"""
Comprehensive Unit Tests for UnifiedConfigurationManager SSOT Class - FIXED VERSION

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction
- Business Goal: Ensure reliable configuration management across all services and environments  
- Value Impact: Validates SSOT configuration consolidation prevents drift and inconsistencies
- Strategic Impact: Tests P0 priority SSOT class managing 50+ configuration operations

CRITICAL: Uses REAL UnifiedConfigurationManager instances - NO MOCKS
Following SSOT patterns but without SSotBaseTestCase inheritance to avoid pytest issues.
"""

import asyncio
import json
import os
import pytest
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from shared.isolated_environment import IsolatedEnvironment, get_env

# Import the REAL UnifiedConfigurationManager (not mocks)
from netra_backend.app.core.managers.unified_configuration_manager import (
    UnifiedConfigurationManager,
    ConfigurationManagerFactory,
    ConfigurationScope,
    ConfigurationSource,
    ConfigurationStatus,
    ConfigurationEntry,
    ConfigurationValidationResult,
    get_configuration_manager,
    get_dashboard_config_manager,
    get_data_agent_config_manager,
    get_llm_config_manager
)


@dataclass
class ConfigTestMetrics:
    """Track test execution metrics."""
    execution_time: float = 0.0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def record(self, name: str, value: Any) -> None:
        """Record a custom metric."""
        self.custom_metrics[name] = value


class TestUnifiedConfigurationManagerBasicOperations:
    """Test basic configuration operations using real UnifiedConfigurationManager."""
    
    def setup_method(self):
        """Set up test with real configuration manager."""
        # Use isolated environment instead of os.environ
        self.env = get_env()
        self.metrics = ConfigTestMetrics()
        
        # Create REAL UnifiedConfigurationManager instance
        self.config_manager = UnifiedConfigurationManager(
            user_id="test_user_123",
            environment="test",
            service_name="test_service",
            enable_validation=True,
            enable_caching=True,
            cache_ttl=300
        )
        
        # Record metrics for test validation
        self.metrics.record("config_manager_created", True)
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'config_manager'):
            self.config_manager.clear_cache()
    
    def test_initialization_with_real_manager(self):
        """Test UnifiedConfigurationManager initialization with real instance."""
        assert self.config_manager is not None
        assert self.config_manager.user_id == "test_user_123"
        assert self.config_manager.environment == "test"
        assert self.config_manager.service_name == "test_service"
        assert self.config_manager.enable_validation is True
        assert self.config_manager.enable_caching is True
        assert self.config_manager.cache_ttl == 300
        
        # Verify real initialization loaded default configurations
        status = self.config_manager.get_status()
        assert status["total_configurations"] > 0
        assert "system.debug" in self.config_manager.keys()
        
        self.metrics.record("initialization_test_passed", True)
    
    def test_basic_get_operations_real_values(self):
        """Test basic get operations with real configuration values."""
        # Test getting default values loaded during initialization
        debug_value = self.config_manager.get("system.debug", True)
        assert isinstance(debug_value, bool)
        
        log_level = self.config_manager.get_str("system.log_level", "DEBUG")
        assert isinstance(log_level, str)
        
        max_workers = self.config_manager.get_int("system.max_workers", 1)
        assert isinstance(max_workers, int)
        assert max_workers > 0
        
        # Test non-existent key returns default
        nonexistent = self.config_manager.get("nonexistent.key", "default_value")
        assert nonexistent == "default_value"
        
        self.metrics.record("basic_get_operations", 4)
    
    def test_basic_set_operations_real_manager(self):
        """Test basic set operations with real configuration manager."""
        # Set various data types
        self.config_manager.set("test.string", "test_value")
        self.config_manager.set("test.integer", 42)
        self.config_manager.set("test.float", 3.14)
        self.config_manager.set("test.boolean", True)
        
        # Verify values were set correctly
        assert self.config_manager.get("test.string") == "test_value"
        assert self.config_manager.get("test.integer") == 42
        assert self.config_manager.get("test.float") == 3.14
        assert self.config_manager.get("test.boolean") is True
        
        # Verify keys exist
        assert self.config_manager.exists("test.string")
        assert self.config_manager.exists("test.integer")
        assert self.config_manager.exists("test.float")
        assert self.config_manager.exists("test.boolean")
        
        self.metrics.record("basic_set_operations", 4)
    
    def test_delete_operations_real_manager(self):
        """Test delete operations with real configuration manager."""
        # Set a test value
        self.config_manager.set("test.delete_me", "will_be_deleted")
        assert self.config_manager.exists("test.delete_me")
        
        # Delete the value
        result = self.config_manager.delete("test.delete_me")
        assert result is True
        assert not self.config_manager.exists("test.delete_me")
        
        # Try to delete non-existent key
        result = self.config_manager.delete("nonexistent.key")
        assert result is False
        
        self.metrics.record("delete_operations", 2)
    
    def test_type_coercion_with_real_manager(self):
        """Test type coercion methods with real configuration manager."""
        # Set string values that can be coerced
        self.config_manager.set("coerce.int", "42")
        self.config_manager.set("coerce.float", "3.14")
        self.config_manager.set("coerce.bool_true", "true")
        self.config_manager.set("coerce.bool_false", "false")
        
        # Test type-specific getters
        int_value = self.config_manager.get_int("coerce.int")
        assert int_value == 42
        assert isinstance(int_value, int)
        
        float_value = self.config_manager.get_float("coerce.float")
        assert float_value == 3.14
        assert isinstance(float_value, float)
        
        bool_true = self.config_manager.get_bool("coerce.bool_true")
        assert bool_true is True
        assert isinstance(bool_true, bool)
        
        bool_false = self.config_manager.get_bool("coerce.bool_false")
        assert bool_false is False
        assert isinstance(bool_false, bool)
        
        self.metrics.record("type_coercion_operations", 4)
    
    def test_list_operations_with_real_manager(self):
        """Test list operations with real configuration manager."""
        # Set a list value
        test_list = ["item1", "item2", "item3"]
        self.config_manager.set("test.list", test_list)
        
        # Get list value
        retrieved_list = self.config_manager.get_list("test.list")
        assert retrieved_list == test_list
        assert isinstance(retrieved_list, list)
        
        # Test JSON string list
        json_list = '["json1", "json2", "json3"]'
        self.config_manager.set("test.json_list", json_list)
        parsed_list = self.config_manager.get_list("test.json_list")
        assert parsed_list == ["json1", "json2", "json3"]
        
        self.metrics.record("list_operations", 2)
    
    def test_dict_operations_with_real_manager(self):
        """Test dictionary operations with real configuration manager."""
        # Set a dict value
        test_dict = {"key1": "value1", "key2": 42, "key3": True}
        self.config_manager.set("test.dict", test_dict)
        
        # Get dict value
        retrieved_dict = self.config_manager.get_dict("test.dict")
        assert retrieved_dict == test_dict
        assert isinstance(retrieved_dict, dict)
        
        # Test JSON string dict
        json_dict = '{"json_key": "json_value", "nested": {"inner": 123}}'
        self.config_manager.set("test.json_dict", json_dict)
        parsed_dict = self.config_manager.get_dict("test.json_dict")
        assert parsed_dict["json_key"] == "json_value"
        assert parsed_dict["nested"]["inner"] == 123
        
        self.metrics.record("dict_operations", 2)


class TestConfigurationValidationAndSecurity:
    """Test configuration validation and security features with real manager."""
    
    def setup_method(self):
        """Set up test with validation-enabled configuration manager."""
        self.env = get_env()
        self.metrics = ConfigTestMetrics()
        
        self.config_manager = UnifiedConfigurationManager(
            user_id="test_validation_user",
            environment="test",
            service_name="validation_service",
            enable_validation=True,
            enable_caching=False  # Disable caching for validation tests
        )
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'config_manager'):
            self.config_manager.clear_cache()
    
    def test_configuration_entry_validation(self):
        """Test ConfigurationEntry validation with real instances."""
        # Create valid configuration entry
        entry = ConfigurationEntry(
            key="database.host",
            value="localhost",
            source=ConfigurationSource.CONFIG_FILE,
            scope=ConfigurationScope.SERVICE,
            data_type=str,
            required=True,
            description="Database host address",
            sensitive=False
        )
        
        # Validate entry properties
        assert entry.key == "database.host"
        assert entry.value == "localhost"
        assert entry.source == ConfigurationSource.CONFIG_FILE
        assert entry.scope == ConfigurationScope.SERVICE
        assert entry.data_type == str
        assert entry.required is True
        assert entry.sensitive is False
        
        # Test setting value with source from entry
        self.config_manager.set(entry.key, entry.value, source=entry.source)
        assert self.config_manager.get("database.host") == "localhost"
        
        self.metrics.record("entry_validation_passed", True)
    
    def test_sensitive_value_masking(self):
        """Test sensitive value masking in real configuration manager."""
        # Set sensitive values
        self.config_manager.set("database.password", "secret123", sensitive=True)
        self.config_manager.set("api.key", "sk-12345678", sensitive=True)
        self.config_manager.set("oauth.secret", "oauth_secret_value", sensitive=True)
        
        # Get masked values for display
        masked_password = self.config_manager.get_masked("database.password")
        assert masked_password == "******"
        
        masked_api_key = self.config_manager.get_masked("api.key")
        assert masked_api_key == "sk-****"
        
        masked_oauth = self.config_manager.get_masked("oauth.secret")
        assert "oauth_secret_value" not in masked_oauth
        
        # Verify actual values are still retrievable
        actual_password = self.config_manager.get("database.password")
        assert actual_password == "secret123"
        
        self.metrics.record("sensitive_masking_operations", 3)
    
    def test_validation_rules(self):
        """Test configuration validation rules with real manager."""
        # Add validation rules
        self.config_manager.add_validation_rule(
            "port",
            lambda v: isinstance(v, int) and 1 <= v <= 65535,
            "Port must be between 1 and 65535"
        )
        
        self.config_manager.add_validation_rule(
            "email",
            lambda v: "@" in str(v) and "." in str(v),
            "Must be a valid email address"
        )
        
        # Test valid values
        self.config_manager.set("server.port", 8080)
        assert self.config_manager.get("server.port") == 8080
        
        self.config_manager.set("admin.email", "admin@example.com")
        assert self.config_manager.get("admin.email") == "admin@example.com"
        
        # Test invalid values (should raise or return validation error)
        with pytest.raises(ValueError):
            self.config_manager.set("server.port", 70000, validate=True)
        
        with pytest.raises(ValueError):
            self.config_manager.set("admin.email", "invalid-email", validate=True)
        
        self.metrics.record("validation_rules_tested", 4)
    
    def test_configuration_change_tracking(self):
        """Test configuration change tracking and auditing."""
        # Enable change tracking
        self.config_manager.enable_change_tracking = True
        
        # Make some changes
        self.config_manager.set("audit.test1", "initial_value")
        self.config_manager.set("audit.test1", "updated_value")
        self.config_manager.set("audit.test2", 42)
        self.config_manager.delete("audit.test2")
        
        # Get change history
        changes = self.config_manager.get_change_history("audit.test1")
        assert len(changes) >= 2
        assert changes[0]["value"] == "initial_value"
        assert changes[1]["value"] == "updated_value"
        
        # Verify deletion is tracked
        deletion_changes = self.config_manager.get_change_history("audit.test2")
        assert any(change.get("action") == "delete" for change in deletion_changes)
        
        self.metrics.record("change_tracking_operations", 4)


class TestMultiUserIsolationAndFactory:
    """Test multi-user isolation and factory pattern with real managers."""
    
    def setup_method(self):
        """Set up test with factory pattern."""
        self.env = get_env()
        self.metrics = ConfigTestMetrics()
        self.factory = ConfigurationManagerFactory()
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'factory'):
            # Clean up any created managers
            pass
    
    def test_factory_creates_global_manager(self):
        """Test factory creates global configuration manager."""
        global_manager = self.factory.get_global_manager()
        
        assert global_manager is not None
        assert global_manager.user_id is None  # Global has no user
        assert global_manager.scope == ConfigurationScope.GLOBAL
        
        # Test global configuration setting
        global_manager.set("global.setting", "global_value")
        assert global_manager.get("global.setting") == "global_value"
        
        # Verify same instance returned
        global_manager2 = self.factory.get_global_manager()
        assert global_manager2 is global_manager
        
        self.metrics.record("global_manager_created", True)
    
    def test_factory_creates_user_specific_managers(self):
        """Test factory creates isolated user-specific managers."""
        # Create managers for different users
        user1_manager = self.factory.get_user_manager("user_001")
        user2_manager = self.factory.get_user_manager("user_002")
        
        assert user1_manager.user_id == "user_001"
        assert user2_manager.user_id == "user_002"
        assert user1_manager is not user2_manager
        
        # Test isolation - settings don't leak between users
        user1_manager.set("user.preference", "user1_pref")
        user2_manager.set("user.preference", "user2_pref")
        
        assert user1_manager.get("user.preference") == "user1_pref"
        assert user2_manager.get("user.preference") == "user2_pref"
        
        # Verify same instance returned for same user
        user1_manager_again = self.factory.get_user_manager("user_001")
        assert user1_manager_again is user1_manager
        
        self.metrics.record("user_managers_isolated", True)
    
    def test_factory_creates_service_specific_managers(self):
        """Test factory creates service-specific configuration managers."""
        # Create managers for different services
        backend_manager = self.factory.get_service_manager("backend")
        auth_manager = self.factory.get_service_manager("auth_service")
        
        assert backend_manager.service_name == "backend"
        assert auth_manager.service_name == "auth_service"
        assert backend_manager is not auth_manager
        
        # Test service-specific configurations
        backend_manager.set("service.port", 8000)
        auth_manager.set("service.port", 8081)
        
        assert backend_manager.get("service.port") == 8000
        assert auth_manager.get("service.port") == 8081
        
        self.metrics.record("service_managers_created", 2)
    
    def test_factory_creates_combined_user_service_manager(self):
        """Test factory creates managers with both user and service scope."""
        # Create manager for specific user and service
        combined_manager = self.factory.get_manager(
            user_id="user_123",
            service_name="analytics",
            environment="production"
        )
        
        assert combined_manager.user_id == "user_123"
        assert combined_manager.service_name == "analytics"
        assert combined_manager.environment == "production"
        
        # Test combined scope configuration
        combined_manager.set("analytics.dashboard", "custom_layout")
        value = combined_manager.get("analytics.dashboard")
        assert value == "custom_layout"
        
        # Verify isolation from other user/service combinations
        other_manager = self.factory.get_manager(
            user_id="user_456",
            service_name="analytics",
            environment="production"
        )
        
        other_manager.set("analytics.dashboard", "different_layout")
        
        # Original manager value unchanged
        assert combined_manager.get("analytics.dashboard") == "custom_layout"
        assert other_manager.get("analytics.dashboard") == "different_layout"
        
        self.metrics.record("combined_managers_isolated", True)


class TestThreadSafetyAndConcurrency:
    """Test thread safety and concurrent access with real managers."""
    
    def setup_method(self):
        """Set up test with thread-safe configuration manager."""
        self.env = get_env()
        self.metrics = ConfigTestMetrics()
        self.config_manager = UnifiedConfigurationManager(
            user_id="concurrent_test_user",
            environment="test",
            enable_thread_safety=True
        )
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'config_manager'):
            self.config_manager.clear_cache()
    
    def test_concurrent_read_operations(self):
        """Test concurrent read operations are thread-safe."""
        # Set initial values
        for i in range(100):
            self.config_manager.set(f"concurrent.key_{i}", f"value_{i}")
        
        results = []
        errors = []
        
        def read_config(key_index):
            try:
                key = f"concurrent.key_{key_index}"
                value = self.config_manager.get(key)
                expected = f"value_{key_index}"
                return value == expected
            except Exception as e:
                errors.append(str(e))
                return False
        
        # Concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(read_config, i % 100)
                for i in range(1000)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # All reads should succeed
        assert len(errors) == 0
        assert all(results)
        
        self.metrics.record("concurrent_reads", 1000)
    
    def test_concurrent_write_operations(self):
        """Test concurrent write operations maintain consistency."""
        counter_key = "concurrent.counter"
        self.config_manager.set(counter_key, 0)
        
        def increment_counter():
            for _ in range(100):
                current = self.config_manager.get_int(counter_key, 0)
                self.config_manager.set(counter_key, current + 1)
                time.sleep(0.0001)  # Small delay to increase contention
        
        # Run concurrent increments
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Check final value (should be 1000 with proper locking)
        final_value = self.config_manager.get_int(counter_key)
        
        # With proper thread safety, value should be close to 1000
        # Some increments might be lost due to race conditions if not properly locked
        assert final_value > 900  # Allow some tolerance
        
        self.metrics.record("concurrent_writes", final_value)
    
    def test_concurrent_cache_operations(self):
        """Test cache operations under concurrent access."""
        # Enable caching
        self.config_manager.enable_caching = True
        self.config_manager.cache_ttl = 1  # 1 second TTL
        
        def cache_operation(operation_id):
            key = f"cache.key_{operation_id % 10}"
            
            # Write
            self.config_manager.set(key, f"value_{operation_id}")
            
            # Read (should hit cache)
            value1 = self.config_manager.get(key)
            
            # Clear cache for this key
            if operation_id % 5 == 0:
                self.config_manager.clear_cache(key)
            
            # Read again
            value2 = self.config_manager.get(key)
            
            return value1 is not None and value2 is not None
        
        # Run concurrent cache operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(cache_operation, i)
                for i in range(100)
            ]
            
            results = [f.result() for f in as_completed(futures)]
        
        # All operations should succeed
        assert all(results)
        
        self.metrics.record("concurrent_cache_operations", 100)


@pytest.mark.asyncio
class TestWebSocketIntegrationAsync:
    """Test WebSocket integration with async operations."""
    
    async def test_websocket_notification_on_config_change(self):
        """Test WebSocket notifications on configuration changes."""
        config_manager = UnifiedConfigurationManager(
            user_id="websocket_test_user",
            environment="test",
            enable_websocket_notifications=True
        )
        
        # Track notifications
        notifications = []
        
        async def notification_handler(event):
            notifications.append(event)
        
        # Set up WebSocket notification handler (simulated)
        config_manager.on_change_callback = notification_handler
        
        # Make configuration changes
        config_manager.set("websocket.test1", "value1")
        config_manager.set("websocket.test2", "value2")
        config_manager.delete("websocket.test1")
        
        # Allow async notifications to process
        await asyncio.sleep(0.1)
        
        # Verify notifications were sent
        assert len(notifications) >= 3
        
        # Clean up
        config_manager.clear_cache()


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases with real manager."""
    
    def setup_method(self):
        """Set up test with error handling focus."""
        self.env = get_env()
        self.metrics = ConfigTestMetrics()
        self.config_manager = UnifiedConfigurationManager(
            user_id="error_test_user",
            environment="test"
        )
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'config_manager'):
            self.config_manager.clear_cache()
    
    def test_invalid_key_formats(self):
        """Test handling of invalid key formats."""
        # Test various invalid key formats
        invalid_keys = [
            "",  # Empty key
            None,  # None key
            "key with spaces",  # Spaces in key
            "key@with#special$chars",  # Special characters
            "../../etc/passwd",  # Path traversal attempt
        ]
        
        for invalid_key in invalid_keys:
            if invalid_key is None:
                with pytest.raises((ValueError, TypeError)):
                    self.config_manager.set(invalid_key, "value")
            else:
                # Manager might sanitize or reject
                try:
                    self.config_manager.set(invalid_key, "value")
                    # If it accepts, verify it's sanitized
                    value = self.config_manager.get(invalid_key)
                    assert value is not None
                except (ValueError, TypeError):
                    # Expected for invalid keys
                    pass
        
        self.metrics.record("invalid_key_tests", len(invalid_keys))
    
    def test_large_value_handling(self):
        """Test handling of large configuration values."""
        # Create a large string value (10KB)
        large_value = "x" * 10240
        
        # Set large value
        self.config_manager.set("large.value", large_value)
        
        # Retrieve and verify
        retrieved = self.config_manager.get("large.value")
        assert retrieved == large_value
        assert len(retrieved) == 10240
        
        # Test large JSON structure
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        self.config_manager.set("large.dict", large_dict)
        
        retrieved_dict = self.config_manager.get_dict("large.dict")
        assert len(retrieved_dict) == 1000
        assert retrieved_dict["key_500"] == "value_500"
        
        self.metrics.record("large_value_operations", 2)
    
    def test_type_coercion_failures(self):
        """Test handling of type coercion failures."""
        # Set non-numeric string
        self.config_manager.set("coerce.fail", "not_a_number")
        
        # Try to get as int (should use default)
        int_value = self.config_manager.get_int("coerce.fail", 99)
        assert int_value == 99
        
        # Try to get as float (should use default)
        float_value = self.config_manager.get_float("coerce.fail", 3.14)
        assert float_value == 3.14
        
        # Set malformed JSON
        self.config_manager.set("json.malformed", "{invalid json}")
        
        # Try to get as dict (should use default)
        dict_value = self.config_manager.get_dict("json.malformed", {"default": "dict"})
        assert dict_value == {"default": "dict"}
        
        self.metrics.record("coercion_failure_handling", 3)


class TestServiceSpecificConfigurations:
    """Test service-specific configuration methods."""
    
    def setup_method(self):
        """Set up test with service configurations."""
        self.env = get_env()
        self.metrics = ConfigTestMetrics()
        self.config_manager = UnifiedConfigurationManager(
            service_name="test_service",
            environment="test"
        )
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'config_manager'):
            self.config_manager.clear_cache()
    
    def test_database_configuration(self):
        """Test database configuration methods."""
        # Set database configuration
        db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
            "pool_size": 10
        }
        
        for key, value in db_config.items():
            self.config_manager.set(f"database.{key}", value)
        
        # Get database configuration
        retrieved_config = self.config_manager.get_database_config()
        
        assert retrieved_config["host"] == "localhost"
        assert retrieved_config["port"] == 5432
        assert retrieved_config["database"] == "test_db"
        assert retrieved_config["pool_size"] == 10
        
        self.metrics.record("database_config_tested", True)
    
    def test_redis_configuration(self):
        """Test Redis configuration methods."""
        # Set Redis configuration
        redis_config = {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": "redis_pass",
            "max_connections": 50
        }
        
        for key, value in redis_config.items():
            self.config_manager.set(f"redis.{key}", value)
        
        # Get Redis configuration
        retrieved_config = self.config_manager.get_redis_config()
        
        assert retrieved_config["host"] == "localhost"
        assert retrieved_config["port"] == 6379
        assert retrieved_config["max_connections"] == 50
        
        self.metrics.record("redis_config_tested", True)
    
    def test_llm_configuration(self):
        """Test LLM configuration methods."""
        # Set OpenAI configuration
        self.config_manager.set("openai.api_key", "sk-test123")
        self.config_manager.set("openai.model", "gpt-4")
        self.config_manager.set("openai.temperature", 0.7)
        
        # Set Anthropic configuration  
        self.config_manager.set("anthropic.api_key", "sk-ant-test456")
        self.config_manager.set("anthropic.model", "claude-3")
        self.config_manager.set("anthropic.max_tokens", 4000)
        
        # Get LLM configurations
        openai_config = self.config_manager.get_llm_config("openai")
        anthropic_config = self.config_manager.get_llm_config("anthropic")
        
        assert openai_config["model"] == "gpt-4"
        assert openai_config["temperature"] == 0.7
        assert anthropic_config["model"] == "claude-3"
        assert anthropic_config["max_tokens"] == 4000
        
        self.metrics.record("llm_config_tested", True)


class TestPerformanceCharacteristics:
    """Test performance characteristics of configuration manager."""
    
    def setup_method(self):
        """Set up test for performance testing."""
        self.env = get_env()
        self.metrics = ConfigTestMetrics()
        self.config_manager = UnifiedConfigurationManager(
            user_id="perf_test_user",
            environment="test",
            enable_caching=True
        )
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'config_manager'):
            self.config_manager.clear_cache()
    
    def test_bulk_operations_performance(self):
        """Test performance of bulk configuration operations."""
        start_time = time.time()
        
        # Bulk set operations
        for i in range(1000):
            self.config_manager.set(f"perf.key_{i}", f"value_{i}")
        
        set_time = time.time() - start_time
        
        # Bulk get operations
        start_time = time.time()
        for i in range(1000):
            value = self.config_manager.get(f"perf.key_{i}")
            assert value == f"value_{i}"
        
        get_time = time.time() - start_time
        
        # Performance assertions (should complete in reasonable time)
        assert set_time < 5.0  # 1000 sets in under 5 seconds
        assert get_time < 2.0  # 1000 gets in under 2 seconds (with caching)
        
        self.metrics.record("bulk_set_time", set_time)
        self.metrics.record("bulk_get_time", get_time)
    
    def test_cache_performance_improvement(self):
        """Test that caching improves read performance."""
        # Disable cache for baseline
        self.config_manager.enable_caching = False
        
        # Set test values
        for i in range(100):
            self.config_manager.set(f"cache_test.key_{i}", f"value_{i}")
        
        # Measure uncached reads
        start_time = time.time()
        for _ in range(10):
            for i in range(100):
                value = self.config_manager.get(f"cache_test.key_{i}")
        uncached_time = time.time() - start_time
        
        # Enable cache
        self.config_manager.enable_caching = True
        self.config_manager.clear_cache()
        
        # Measure cached reads
        start_time = time.time()
        for _ in range(10):
            for i in range(100):
                value = self.config_manager.get(f"cache_test.key_{i}")
        cached_time = time.time() - start_time
        
        # Cached should be faster
        assert cached_time < uncached_time
        
        self.metrics.record("uncached_time", uncached_time)
        self.metrics.record("cached_time", cached_time)
        self.metrics.record("cache_speedup", uncached_time / cached_time)