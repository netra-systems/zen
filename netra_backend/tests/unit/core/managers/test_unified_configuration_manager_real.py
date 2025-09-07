"""
Comprehensive Unit Tests for UnifiedConfigurationManager SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction
- Business Goal: Ensure reliable configuration management across all services and environments  
- Value Impact: Validates SSOT configuration consolidation prevents drift and inconsistencies
- Strategic Impact: Tests P0 priority SSOT class managing 50+ configuration operations for operational simplicity

CRITICAL: This is a P0 priority SSOT class that consolidates ALL configuration operations.
Tests focus on REAL business value using actual UnifiedConfigurationManager instances.

Key Testing Areas:
1. Basic configuration operations (get, set, delete, exists)
2. Multi-environment support and detection
3. Configuration validation and type coercion
4. User-scoped and service-scoped configurations  
5. Factory pattern multi-user isolation
6. Thread safety and concurrent access
7. Sensitive value masking and security
8. Configuration change tracking and auditing
9. Caching functionality and invalidation
10. Service-specific configuration methods
11. WebSocket integration and notifications
12. Error handling and edge cases
13. Mission critical values validation
14. Performance characteristics
15. Configuration file loading and merging
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
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

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


class TestUnifiedConfigurationManagerBasicOperations(SSotBaseTestCase):
    """Test basic configuration operations using real UnifiedConfigurationManager."""
    
    def setup_method(self, method=None):
        """Set up test with real configuration manager."""
        super().setup_method(method)
        
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
        self.record_metric("config_manager_created", True)
    
    def teardown_method(self, method=None):
        """Clean up test resources."""
        if hasattr(self, 'config_manager'):
            self.config_manager.clear_cache()
        super().teardown_method(method)
    
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
        
        self.record_metric("initialization_test_passed", True)
    
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
        
        self.record_metric("basic_get_operations", 4)
    
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
        
        self.record_metric("basic_set_operations", 4)
    
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
        
        self.record_metric("delete_operations", 2)
    
    def test_type_coercion_real_manager(self):
        """Test type coercion with real configuration manager."""
        # Set string values that should be coerced
        self.config_manager.set("test.string_int", "123")
        self.config_manager.set("test.string_float", "3.14")
        self.config_manager.set("test.string_bool_true", "true")
        self.config_manager.set("test.string_bool_false", "false")
        
        # Test type coercion
        assert self.config_manager.get_int("test.string_int") == 123
        assert self.config_manager.get_float("test.string_float") == 3.14
        assert self.config_manager.get_bool("test.string_bool_true") is True
        assert self.config_manager.get_bool("test.string_bool_false") is False
        
        self.record_metric("type_coercion_tests", 4)
    
    def test_list_and_dict_operations_real_manager(self):
        """Test list and dictionary operations with real configuration manager."""
        # Test list operations
        self.config_manager.set("test.csv_list", "item1,item2,item3")
        self.config_manager.set("test.json_list", '["json1", "json2", "json3"]')
        
        csv_list = self.config_manager.get_list("test.csv_list")
        assert csv_list == ["item1", "item2", "item3"]
        
        json_list = self.config_manager.get_list("test.json_list")
        assert json_list == ["json1", "json2", "json3"]
        
        # Test dict operations
        test_dict = {"key1": "value1", "key2": "value2"}
        self.config_manager.set("test.json_dict", json.dumps(test_dict))
        
        retrieved_dict = self.config_manager.get_dict("test.json_dict")
        assert retrieved_dict == test_dict
        
        self.record_metric("list_dict_operations", 3)


class TestConfigurationValidationAndSecurity(SSotBaseTestCase):
    """Test configuration validation and security features."""
    
    def setup_method(self, method=None):
        """Set up test with validation-enabled manager."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            user_id="test_user_validation",
            enable_validation=True,
            enable_caching=False  # Disable caching for validation tests
        )
    
    def test_configuration_entry_validation_real(self):
        """Test ConfigurationEntry validation with real instances."""
        # Test valid entry
        valid_entry = ConfigurationEntry(
            key="test.valid",
            value=42,
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.USER,
            data_type=int,
            validation_rules=["min_value:1", "max_value:100"]
        )
        
        assert valid_entry.validate() is True
        
        # Test invalid entry - value out of range
        invalid_entry = ConfigurationEntry(
            key="test.invalid",
            value=150,
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.USER,
            data_type=int,
            validation_rules=["min_value:1", "max_value:100"]
        )
        
        assert invalid_entry.validate() is False
        
        self.record_metric("validation_entry_tests", 2)
    
    def test_sensitive_value_masking_real(self):
        """Test sensitive value masking with real configuration manager."""
        # Set sensitive values
        self.config_manager.set("security.api_key", "sk-1234567890abcdef")
        self.config_manager.set("security.password", "supersecret123")
        self.config_manager.set("security.token", "jwt_token_here")
        
        # Mark as sensitive
        self.config_manager._sensitive_keys.update([
            "security.api_key", "security.password", "security.token"
        ])
        
        # Get all configurations without sensitive values
        all_configs = self.config_manager.get_all(include_sensitive=False)
        
        # Values should be masked in the output
        assert all_configs["security.api_key"] != "sk-1234567890abcdef"
        assert "*" in str(all_configs["security.api_key"])
        
        # But direct get should return actual value
        assert self.config_manager.get("security.api_key") == "sk-1234567890abcdef"
        
        self.record_metric("sensitive_masking_tests", 3)
    
    def test_validation_rules_real(self):
        """Test various validation rules with real configuration manager."""
        # Test schema validation
        schema = {
            "test.min_length": {
                "type": str,
                "validation_rules": ["min_length:5"],
                "required": True
            },
            "test.positive_number": {
                "type": int,
                "validation_rules": ["positive"],
                "required": False
            },
            "test.regex_email": {
                "type": str,
                "validation_rules": ["regex:^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"],
                "required": False
            }
        }
        
        self.config_manager.add_validation_schema(schema)
        
        # Test valid values
        self.config_manager.set("test.min_length", "valid_string")
        self.config_manager.set("test.positive_number", 42)
        self.config_manager.set("test.regex_email", "test@example.com")
        
        # Test validation
        validation_result = self.config_manager.validate_all_configurations()
        
        # Should have some errors from other configurations but these should be valid
        assert isinstance(validation_result, ConfigurationValidationResult)
        
        self.record_metric("validation_rules_tests", 3)
    
    def test_configuration_change_tracking_real(self):
        """Test configuration change tracking with real manager."""
        # Set initial value
        self.config_manager.set("test.tracked", "initial_value")
        
        # Change the value multiple times
        self.config_manager.set("test.tracked", "second_value")
        self.config_manager.set("test.tracked", "third_value")
        
        # Get change history
        history = self.config_manager.get_change_history(limit=10)
        
        # Should have tracked changes
        assert len(history) >= 3
        
        # Verify change structure
        for change in history[-3:]:
            assert "timestamp" in change
            assert "key" in change
            assert "old_value" in change
            assert "new_value" in change
            assert "source" in change
            assert "user_id" in change
            
        self.record_metric("change_tracking_tests", len(history))


class TestMultiUserIsolationAndFactory(SSotBaseTestCase):
    """Test multi-user isolation via factory pattern."""
    
    def setup_method(self, method=None):
        """Set up test for factory pattern testing."""
        super().setup_method(method)
        # Clear any existing managers for clean test
        ConfigurationManagerFactory._user_managers.clear()
        ConfigurationManagerFactory._service_managers.clear()
        ConfigurationManagerFactory._global_manager = None
    
    def test_factory_global_manager_real(self):
        """Test factory pattern for global manager."""
        # Get global manager
        manager1 = ConfigurationManagerFactory.get_global_manager()
        manager2 = ConfigurationManagerFactory.get_global_manager()
        
        # Should be the same instance (singleton pattern)
        assert manager1 is manager2
        assert manager1.user_id is None
        assert manager1.service_name is None
        
        self.record_metric("global_manager_singleton", True)
    
    def test_factory_user_specific_managers_real(self):
        """Test factory pattern for user-specific managers."""
        # Get managers for different users
        user1_manager = ConfigurationManagerFactory.get_user_manager("user_001")
        user2_manager = ConfigurationManagerFactory.get_user_manager("user_002")
        user1_manager_2 = ConfigurationManagerFactory.get_user_manager("user_001")
        
        # User-specific managers should be isolated
        assert user1_manager is not user2_manager
        assert user1_manager is user1_manager_2  # Same user should get same instance
        
        assert user1_manager.user_id == "user_001"
        assert user2_manager.user_id == "user_002"
        
        self.record_metric("user_specific_managers", 2)
    
    def test_factory_service_specific_managers_real(self):
        """Test factory pattern for service-specific managers."""
        # Get managers for different services
        backend_manager = ConfigurationManagerFactory.get_service_manager("backend")
        auth_manager = ConfigurationManagerFactory.get_service_manager("auth_service")
        backend_manager_2 = ConfigurationManagerFactory.get_service_manager("backend")
        
        # Service-specific managers should be isolated
        assert backend_manager is not auth_manager
        assert backend_manager is backend_manager_2  # Same service should get same instance
        
        assert backend_manager.service_name == "backend"
        assert auth_manager.service_name == "auth_service"
        
        self.record_metric("service_specific_managers", 2)
    
    def test_factory_combined_user_service_managers_real(self):
        """Test factory pattern for combined user+service managers."""
        # Get combined managers
        user1_backend = ConfigurationManagerFactory.get_manager(
            user_id="user_001", service_name="backend"
        )
        user1_auth = ConfigurationManagerFactory.get_manager(
            user_id="user_001", service_name="auth_service"  
        )
        user2_backend = ConfigurationManagerFactory.get_manager(
            user_id="user_002", service_name="backend"
        )
        
        # All should be different instances (full isolation)
        assert user1_backend is not user1_auth
        assert user1_backend is not user2_backend
        assert user1_auth is not user2_backend
        
        # Verify properties
        assert user1_backend.user_id == "user_001"
        assert user1_backend.service_name == "backend"
        assert user1_auth.user_id == "user_001"
        assert user1_auth.service_name == "auth_service"
        
        self.record_metric("combined_managers", 3)
    
    def test_user_isolation_configuration_real(self):
        """Test that user configurations are properly isolated."""
        user1_manager = ConfigurationManagerFactory.get_user_manager("isolated_user_1")
        user2_manager = ConfigurationManagerFactory.get_user_manager("isolated_user_2")
        
        # Set different values for same key in different user contexts
        user1_manager.set("user.preference", "user1_value")
        user2_manager.set("user.preference", "user2_value")
        
        # Values should be isolated
        assert user1_manager.get("user.preference") == "user1_value"
        assert user2_manager.get("user.preference") == "user2_value"
        
        # Verify isolation in key listing
        user1_keys = set(user1_manager.keys())
        user2_keys = set(user2_manager.keys())
        
        # Should have mostly same default keys but user-specific values
        default_keys_count = len(user1_keys.intersection(user2_keys))
        assert default_keys_count > 0  # Should have default configurations
        
        self.record_metric("user_isolation_verified", True)


class TestThreadSafetyAndConcurrency(SSotBaseTestCase):
    """Test thread safety and concurrent access patterns."""
    
    def setup_method(self, method=None):
        """Set up test for concurrency testing."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            user_id="concurrent_test_user",
            enable_caching=True,
            cache_ttl=10  # Short TTL for testing
        )
    
    def test_thread_safety_basic_operations(self):
        """Test thread safety of basic configuration operations."""
        def worker_thread(thread_id: int, iterations: int):
            """Worker thread that performs configuration operations."""
            for i in range(iterations):
                key = f"thread_{thread_id}.iteration_{i}"
                value = f"value_from_thread_{thread_id}_iteration_{i}"
                
                # Set value
                self.config_manager.set(key, value)
                
                # Immediately get value
                retrieved = self.config_manager.get(key)
                assert retrieved == value, f"Thread {thread_id} failed at iteration {i}"
                
                # Delete value
                self.config_manager.delete(key)
        
        # Run multiple threads concurrently
        threads = []
        num_threads = 5
        iterations_per_thread = 20
        
        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=worker_thread, 
                args=(thread_id, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        self.record_metric("concurrent_threads", num_threads)
        self.record_metric("concurrent_operations", num_threads * iterations_per_thread * 3)
    
    def test_concurrent_cache_operations(self):
        """Test thread safety of cache operations."""
        cache_key = "concurrent.cache.test"
        
        def cache_worker(worker_id: int):
            """Worker that performs cache operations."""
            for i in range(10):
                # Set value with caching enabled
                value = f"worker_{worker_id}_value_{i}"
                self.config_manager.set(cache_key, value)
                
                # Get value (should be cached)
                retrieved = self.config_manager.get(cache_key)
                assert retrieved == value
                
                # Clear cache occasionally
                if i % 3 == 0:
                    self.config_manager.clear_cache(cache_key)
        
        # Run concurrent cache operations
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cache_worker, i) for i in range(4)]
            
            # Wait for completion
            for future in as_completed(futures):
                future.result()  # Will raise exception if worker failed
        
        self.record_metric("concurrent_cache_operations", True)
    
    def test_concurrent_validation_operations(self):
        """Test thread safety of validation operations."""
        def validation_worker(worker_id: int):
            """Worker that performs validation operations."""
            # Add validation schema
            schema = {
                f"worker_{worker_id}.test_key": {
                    "type": str,
                    "required": False,
                    "validation_rules": ["min_length:5"]
                }
            }
            self.config_manager.add_validation_schema(schema)
            
            # Set valid and invalid values
            self.config_manager.set(f"worker_{worker_id}.test_key", "valid_long_string")
            
            # Run validation
            result = self.config_manager.validate_all_configurations()
            assert isinstance(result, ConfigurationValidationResult)
        
        # Run concurrent validation operations
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=validation_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        self.record_metric("concurrent_validation", True)


class TestServiceSpecificConfigurations(SSotBaseTestCase):
    """Test service-specific configuration methods."""
    
    def setup_method(self, method=None):
        """Set up test for service-specific configurations."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            service_name="test_service",
            enable_validation=False  # Disable for cleaner testing
        )
        
        # Set up test values for service configurations
        self.config_manager.set("database.url", "postgresql://test:test@localhost:5432/test")
        self.config_manager.set("database.pool_size", 15)
        self.config_manager.set("redis.url", "redis://localhost:6379/0")
        self.config_manager.set("redis.max_connections", 100)
    
    def test_database_configuration_real(self):
        """Test database configuration retrieval with real values."""
        db_config = self.config_manager.get_database_config()
        
        # Verify structure and types
        assert isinstance(db_config, dict)
        assert "url" in db_config
        assert "pool_size" in db_config
        assert "max_overflow" in db_config
        assert "pool_timeout" in db_config
        assert "pool_recycle" in db_config
        assert "echo" in db_config
        
        # Verify values and types
        assert db_config["url"] == "postgresql://test:test@localhost:5432/test"
        assert db_config["pool_size"] == 15
        assert isinstance(db_config["max_overflow"], int)
        assert isinstance(db_config["pool_timeout"], int)
        assert isinstance(db_config["echo"], bool)
        
        self.record_metric("database_config_fields", len(db_config))
    
    def test_redis_configuration_real(self):
        """Test Redis configuration retrieval with real values."""
        redis_config = self.config_manager.get_redis_config()
        
        # Verify structure
        assert isinstance(redis_config, dict)
        expected_keys = [
            "url", "max_connections", "socket_timeout", 
            "socket_connect_timeout", "retry_on_timeout", "health_check_interval"
        ]
        for key in expected_keys:
            assert key in redis_config
        
        # Verify values and types
        assert redis_config["url"] == "redis://localhost:6379/0"
        assert redis_config["max_connections"] == 100
        assert isinstance(redis_config["socket_timeout"], float)
        assert isinstance(redis_config["retry_on_timeout"], bool)
        
        self.record_metric("redis_config_fields", len(redis_config))
    
    def test_llm_configuration_real(self):
        """Test LLM configuration retrieval with real values."""
        llm_config = self.config_manager.get_llm_config()
        
        # Verify structure
        assert isinstance(llm_config, dict)
        assert "timeout" in llm_config
        assert "max_retries" in llm_config
        assert "openai" in llm_config
        assert "anthropic" in llm_config
        
        # Verify nested structures
        assert isinstance(llm_config["openai"], dict)
        assert isinstance(llm_config["anthropic"], dict)
        
        # Verify types
        assert isinstance(llm_config["timeout"], float)
        assert isinstance(llm_config["max_retries"], int)
        
        self.record_metric("llm_config_nested_structures", 2)
    
    def test_agent_configuration_real(self):
        """Test agent configuration retrieval with real values."""
        agent_config = self.config_manager.get_agent_config()
        
        # Verify structure
        assert isinstance(agent_config, dict)
        assert "execution_timeout" in agent_config
        assert "max_concurrent" in agent_config
        assert "circuit_breaker" in agent_config
        
        # Verify circuit breaker nested config
        cb_config = agent_config["circuit_breaker"]
        assert isinstance(cb_config, dict)
        assert "failure_threshold" in cb_config
        assert "recovery_timeout" in cb_config
        assert "half_open_max_calls" in cb_config
        
        self.record_metric("agent_config_test", True)
    
    def test_websocket_configuration_real(self):
        """Test WebSocket configuration retrieval with real values."""
        ws_config = self.config_manager.get_websocket_config()
        
        # Verify structure and types
        assert isinstance(ws_config, dict)
        expected_keys = [
            "ping_interval", "ping_timeout", "max_connections", 
            "message_queue_size", "close_timeout"
        ]
        
        for key in expected_keys:
            assert key in ws_config
            assert isinstance(ws_config[key], int)
        
        self.record_metric("websocket_config_fields", len(expected_keys))
    
    def test_security_configuration_real(self):
        """Test security configuration retrieval with real values."""
        security_config = self.config_manager.get_security_config()
        
        # Verify structure
        assert isinstance(security_config, dict)
        assert "jwt_algorithm" in security_config
        assert "jwt_expire_minutes" in security_config
        assert "password_min_length" in security_config
        assert "require_https" in security_config
        
        # Verify types
        assert isinstance(security_config["jwt_algorithm"], str)
        assert isinstance(security_config["jwt_expire_minutes"], int)
        assert isinstance(security_config["require_https"], bool)
        
        self.record_metric("security_config_test", True)
    
    def test_dashboard_configuration_real(self):
        """Test dashboard configuration retrieval (consolidated from DashboardConfigManager)."""
        dashboard_config = self.config_manager.get_dashboard_config()
        
        # Verify structure
        assert isinstance(dashboard_config, dict)
        assert "refresh_interval" in dashboard_config
        assert "charts" in dashboard_config
        
        # Verify nested charts config
        charts_config = dashboard_config["charts"]
        assert isinstance(charts_config, dict)
        assert "animation_duration" in charts_config
        assert "show_legends" in charts_config
        
        self.record_metric("dashboard_config_consolidated", True)


class TestCachingFunctionality(SSotBaseTestCase):
    """Test configuration caching functionality."""
    
    def setup_method(self, method=None):
        """Set up test for caching functionality."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            enable_caching=True,
            cache_ttl=2  # 2 second TTL for testing
        )
    
    def test_cache_hit_miss_behavior_real(self):
        """Test cache hit and miss behavior with real manager."""
        key = "test.cache.behavior"
        value = "cached_value"
        
        # First set should not be cached
        self.config_manager.set(key, value)
        
        # First get should populate cache
        result1 = self.config_manager.get(key)
        assert result1 == value
        
        # Second get should hit cache (assuming same value in cache)
        result2 = self.config_manager.get(key)
        assert result2 == value
        
        self.record_metric("cache_operations", 3)
    
    def test_cache_invalidation_on_set_real(self):
        """Test cache invalidation when setting new values."""
        key = "test.cache.invalidation"
        
        # Set initial value
        self.config_manager.set(key, "initial_value")
        cached_value1 = self.config_manager.get(key)
        assert cached_value1 == "initial_value"
        
        # Set new value should invalidate cache
        self.config_manager.set(key, "updated_value")
        cached_value2 = self.config_manager.get(key)
        assert cached_value2 == "updated_value"
        
        self.record_metric("cache_invalidation_test", True)
    
    def test_cache_ttl_expiration_real(self):
        """Test cache TTL expiration with real manager."""
        key = "test.cache.ttl"
        value = "ttl_test_value"
        
        # Set value
        self.config_manager.set(key, value)
        
        # Get value immediately (should be fresh)
        result1 = self.config_manager.get(key)
        assert result1 == value
        
        # Wait for cache TTL to expire
        time.sleep(3)  # TTL is 2 seconds
        
        # Get value after expiration - should still work but fetch fresh
        result2 = self.config_manager.get(key)
        assert result2 == value
        
        self.record_metric("cache_ttl_test", True)
    
    def test_cache_clear_operations_real(self):
        """Test cache clearing operations."""
        # Set multiple values
        self.config_manager.set("cache.clear.test1", "value1")
        self.config_manager.set("cache.clear.test2", "value2")
        
        # Get values to populate cache
        self.config_manager.get("cache.clear.test1")
        self.config_manager.get("cache.clear.test2")
        
        # Clear specific key
        self.config_manager.clear_cache("cache.clear.test1")
        
        # Values should still be retrievable
        assert self.config_manager.get("cache.clear.test1") == "value1"
        assert self.config_manager.get("cache.clear.test2") == "value2"
        
        # Clear all cache
        self.config_manager.clear_cache()
        
        # Values should still be retrievable from source
        assert self.config_manager.get("cache.clear.test1") == "value1"
        assert self.config_manager.get("cache.clear.test2") == "value2"
        
        self.record_metric("cache_clear_operations", 2)


class TestWebSocketIntegrationAndNotifications(SSotAsyncTestCase):
    """Test WebSocket integration and change notifications."""
    
    async def setup_method(self, method=None):
        """Set up test for WebSocket integration."""
        await super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            user_id="websocket_test_user",
            enable_validation=False
        )
        
        # Mock WebSocket manager
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.broadcast_system_message = AsyncMock()
        self.received_messages = []
        
        # Set up message capture
        async def capture_message(message):
            self.received_messages.append(message)
        
        self.mock_websocket_manager.broadcast_system_message.side_effect = capture_message
    
    async def test_websocket_manager_integration_real(self):
        """Test WebSocket manager integration with real configuration manager."""
        # Set WebSocket manager
        self.config_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Verify WebSocket events are enabled
        assert self.config_manager._websocket_manager is self.mock_websocket_manager
        assert self.config_manager._enable_websocket_events is True
        
        # Verify change listener was added
        assert len(self.config_manager._change_listeners) > 0
        
        self.record_metric("websocket_integration", True)
    
    async def test_configuration_change_notifications_real(self):
        """Test configuration change notifications via WebSocket."""
        # Set up WebSocket manager
        self.config_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Make a configuration change
        self.config_manager.set("websocket.test.key", "test_value")
        
        # Allow async operations to complete
        await asyncio.sleep(0.1)
        
        # Verify message was broadcast
        assert len(self.received_messages) > 0
        
        # Verify message structure
        message = self.received_messages[-1]
        assert "type" in message
        assert message["type"] == "configuration_changed"
        assert "data" in message
        assert message["data"]["key"] == "websocket.test.key"
        assert message["data"]["new_value"] == "test_value"
        
        self.record_metric("websocket_notifications", len(self.received_messages))
    
    async def test_sensitive_value_masking_in_notifications_real(self):
        """Test that sensitive values are masked in WebSocket notifications."""
        # Set up WebSocket manager
        self.config_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Set sensitive value
        self.config_manager._sensitive_keys.add("secret.api.key")
        self.config_manager.set("secret.api.key", "super_secret_key_12345")
        
        # Allow async operations to complete
        await asyncio.sleep(0.1)
        
        # Verify message was sent but value is masked
        assert len(self.received_messages) > 0
        message = self.received_messages[-1]
        
        assert message["data"]["key"] == "secret.api.key"
        # Value should be masked, not the original
        assert message["data"]["new_value"] != "super_secret_key_12345"
        assert "*" in str(message["data"]["new_value"])
        
        self.record_metric("sensitive_masking_websocket", True)
    
    async def test_websocket_event_toggle_real(self):
        """Test enabling/disabling WebSocket events."""
        # Set up WebSocket manager
        self.config_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Disable WebSocket events
        self.config_manager.enable_websocket_events(False)
        
        # Make changes - should not trigger notifications
        initial_count = len(self.received_messages)
        self.config_manager.set("toggle.test.key", "no_notification")
        
        await asyncio.sleep(0.1)
        
        # Should not have new messages
        assert len(self.received_messages) == initial_count
        
        # Re-enable and test
        self.config_manager.enable_websocket_events(True)
        self.config_manager.set("toggle.test.key", "with_notification")
        
        await asyncio.sleep(0.1)
        
        # Should have new message now
        assert len(self.received_messages) > initial_count
        
        self.record_metric("websocket_toggle_test", True)


class TestErrorHandlingAndEdgeCases(SSotBaseTestCase):
    """Test error handling and edge cases."""
    
    def setup_method(self, method=None):
        """Set up test for error handling."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            enable_validation=True
        )
    
    def test_invalid_validation_rules_real(self):
        """Test handling of invalid validation rules."""
        # Create entry with invalid validation rule
        entry = ConfigurationEntry(
            key="test.invalid_rule",
            value="test_value",
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            validation_rules=["invalid_rule:parameter"]
        )
        
        # Invalid rule should not prevent validation (rule is ignored)
        result = entry.validate()
        assert result is True  # Should still pass since invalid rules are ignored
        
        self.record_metric("invalid_validation_rules", 1)
    
    def test_type_coercion_failures_real(self):
        """Test type coercion failure handling."""
        # Set string value
        self.config_manager.set("test.coercion.string", "not_a_number")
        
        # Try to get as int with default
        result = self.config_manager.get_int("test.coercion.string", 42)
        # Should return default when coercion fails
        assert result == 42
        
        # Try boolean coercion with invalid value
        self.config_manager.set("test.coercion.bool", "maybe")
        result = self.config_manager.get_bool("test.coercion.bool", False)
        assert result is False
        
        self.record_metric("coercion_failures", 2)
    
    def test_validation_failure_on_set_real(self):
        """Test validation failure when setting values."""
        # Add strict validation schema
        schema = {
            "test.strict": {
                "type": int,
                "validation_rules": ["min_value:10", "max_value:20"],
                "required": True
            }
        }
        self.config_manager.add_validation_schema(schema)
        
        # Try to set invalid value
        with self.expect_exception(ValueError):
            self.config_manager.set("test.strict", 5)  # Below minimum
        
        self.record_metric("validation_failures_caught", 1)
    
    def test_concurrent_modification_resilience_real(self):
        """Test resilience against concurrent modifications."""
        key = "test.concurrent.resilience"
        
        def modifier_thread(value_suffix):
            """Thread that modifies configuration."""
            try:
                self.config_manager.set(key, f"value_{value_suffix}")
                result = self.config_manager.get(key)
                # Result might be from this thread or another, but should be valid
                assert result.startswith("value_")
            except Exception as e:
                # Should not have exceptions
                assert False, f"Unexpected exception: {e}"
        
        # Run multiple modifiers concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=modifier_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Final state should be valid
        final_value = self.config_manager.get(key)
        assert final_value.startswith("value_")
        
        self.record_metric("concurrent_resilience", True)
    
    def test_large_configuration_values_real(self):
        """Test handling of large configuration values."""
        # Test large string value
        large_value = "x" * 10000  # 10KB string
        self.config_manager.set("test.large.string", large_value)
        
        result = self.config_manager.get("test.large.string")
        assert result == large_value
        assert len(result) == 10000
        
        # Test large dict as JSON
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        self.config_manager.set("test.large.dict", json.dumps(large_dict))
        
        result_dict = self.config_manager.get_dict("test.large.dict")
        assert len(result_dict) == 1000
        assert result_dict["key_500"] == "value_500"
        
        self.record_metric("large_value_size_kb", 10)


class TestStatusMonitoringAndHealth(SSotBaseTestCase):
    """Test status monitoring and health check capabilities."""
    
    def setup_method(self, method=None):
        """Set up test for status monitoring."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            user_id="monitoring_test_user",
            service_name="monitoring_service",
            enable_validation=True,
            enable_caching=True
        )
    
    def test_status_reporting_real(self):
        """Test comprehensive status reporting."""
        # Add some configurations to get meaningful status
        self.config_manager.set("monitor.test.key1", "value1")
        self.config_manager.set("monitor.test.key2", 42)
        
        status = self.config_manager.get_status()
        
        # Verify status structure
        assert isinstance(status, dict)
        expected_keys = [
            "user_id", "environment", "service_name", "total_configurations",
            "validation_enabled", "caching_enabled", "cache_size", "cache_ttl",
            "validation_status", "sources", "scopes", "sensitive_key_count",
            "required_key_count", "deprecated_key_count", "change_history_count",
            "change_listeners_count"
        ]
        
        for key in expected_keys:
            assert key in status, f"Missing status key: {key}"
        
        # Verify status values
        assert status["user_id"] == "monitoring_test_user"
        assert status["service_name"] == "monitoring_service"
        assert status["total_configurations"] > 0
        assert status["validation_enabled"] is True
        assert status["caching_enabled"] is True
        
        self.record_metric("status_fields_count", len(expected_keys))
    
    def test_health_status_real(self):
        """Test health status reporting."""
        health_status = self.config_manager.get_health_status()
        
        # Verify health structure
        assert isinstance(health_status, dict)
        assert "status" in health_status
        assert "validation_result" in health_status
        assert "critical_errors" in health_status
        assert "missing_required" in health_status
        assert "total_configurations" in health_status
        
        # Status should be healthy or unhealthy
        assert health_status["status"] in ["healthy", "unhealthy"]
        
        # Counts should be non-negative integers
        assert isinstance(health_status["critical_errors"], int)
        assert isinstance(health_status["missing_required"], int)
        assert isinstance(health_status["total_configurations"], int)
        assert health_status["critical_errors"] >= 0
        assert health_status["missing_required"] >= 0
        assert health_status["total_configurations"] > 0
        
        self.record_metric("health_check", health_status["status"] == "healthy")
    
    def test_validation_status_reporting_real(self):
        """Test validation status in monitoring."""
        # Add some invalid configurations to test validation reporting
        self.config_manager.set("invalid.test", "value")
        
        # Add validation schema that will fail
        schema = {
            "invalid.test": {
                "type": int,  # Will fail since we set string
                "required": True
            },
            "missing.required": {
                "type": str,
                "required": True  # Will be missing
            }
        }
        self.config_manager.add_validation_schema(schema)
        
        # Get status with validation issues
        status = self.config_manager.get_status()
        validation_status = status["validation_status"]
        
        # Should report validation issues
        assert isinstance(validation_status, dict)
        assert "is_valid" in validation_status
        assert "error_count" in validation_status
        assert "critical_error_count" in validation_status
        assert "missing_required_count" in validation_status
        
        # Should have detected issues
        assert validation_status["is_valid"] is False
        assert validation_status["error_count"] > 0 or validation_status["critical_error_count"] > 0
        
        self.record_metric("validation_issues_detected", True)
    
    def test_source_and_scope_distribution_real(self):
        """Test source and scope distribution in status."""
        # Set values from different sources
        self.config_manager.set("override.test", "value", ConfigurationSource.OVERRIDE)
        
        status = self.config_manager.get_status()
        
        # Verify source distribution
        sources = status["sources"]
        assert isinstance(sources, dict)
        for source in ConfigurationSource:
            assert source.value in sources
            assert isinstance(sources[source.value], int)
        
        # Should have some default configurations
        assert sources["default"] > 0
        
        # Verify scope distribution  
        scopes = status["scopes"]
        assert isinstance(scopes, dict)
        for scope in ConfigurationScope:
            assert scope.value in scopes
            assert isinstance(scopes[scope.value], int)
        
        self.record_metric("source_distribution", len(sources))


class TestLegacyCompatibilityFunctions(SSotBaseTestCase):
    """Test legacy compatibility functions."""
    
    def test_legacy_dashboard_config_manager_real(self):
        """Test legacy dashboard config manager compatibility."""
        dashboard_manager = get_dashboard_config_manager()
        
        # Should return UnifiedConfigurationManager instance
        assert isinstance(dashboard_manager, UnifiedConfigurationManager)
        assert dashboard_manager.service_name == "dashboard"
        
        # Should work with dashboard config method
        dashboard_config = dashboard_manager.get_dashboard_config()
        assert isinstance(dashboard_config, dict)
        assert "refresh_interval" in dashboard_config
        
        self.record_metric("legacy_dashboard_manager", True)
    
    def test_legacy_data_agent_config_manager_real(self):
        """Test legacy data agent config manager compatibility."""
        data_agent_manager = get_data_agent_config_manager()
        
        # Should return UnifiedConfigurationManager instance
        assert isinstance(data_agent_manager, UnifiedConfigurationManager)
        assert data_agent_manager.service_name == "data_agent"
        
        self.record_metric("legacy_data_agent_manager", True)
    
    def test_legacy_llm_config_manager_real(self):
        """Test legacy LLM config manager compatibility."""
        llm_manager = get_llm_config_manager()
        
        # Should return UnifiedConfigurationManager instance  
        assert isinstance(llm_manager, UnifiedConfigurationManager)
        assert llm_manager.service_name == "llm"
        
        # Should work with LLM config method
        llm_config = llm_manager.get_llm_config()
        assert isinstance(llm_config, dict)
        assert "timeout" in llm_config
        assert "openai" in llm_config
        
        self.record_metric("legacy_llm_manager", True)
    
    def test_generic_configuration_manager_function_real(self):
        """Test generic configuration manager function."""
        # Test various parameter combinations
        global_manager = get_configuration_manager()
        assert global_manager.user_id is None
        assert global_manager.service_name is None
        
        user_manager = get_configuration_manager(user_id="test_user")
        assert user_manager.user_id == "test_user"
        assert user_manager.service_name is None
        
        service_manager = get_configuration_manager(service_name="test_service")
        assert service_manager.user_id is None
        assert service_manager.service_name == "test_service"
        
        combined_manager = get_configuration_manager(
            user_id="test_user", service_name="test_service"
        )
        assert combined_manager.user_id == "test_user"
        assert combined_manager.service_name == "test_service"
        
        self.record_metric("generic_manager_combinations", 4)


class TestPerformanceCharacteristics(SSotBaseTestCase):
    """Test performance characteristics of configuration manager."""
    
    def setup_method(self, method=None):
        """Set up test for performance testing."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigurationManager(
            enable_caching=True,
            cache_ttl=60  # Longer TTL for performance testing
        )
    
    def test_bulk_operations_performance_real(self):
        """Test performance of bulk configuration operations."""
        num_operations = 1000
        
        start_time = time.time()
        
        # Bulk set operations
        for i in range(num_operations):
            key = f"perf.test.{i:04d}"
            value = f"value_{i}"
            self.config_manager.set(key, value)
        
        set_time = time.time() - start_time
        
        start_time = time.time()
        
        # Bulk get operations
        for i in range(num_operations):
            key = f"perf.test.{i:04d}"
            value = self.config_manager.get(key)
            assert value == f"value_{i}"
        
        get_time = time.time() - start_time
        
        # Performance should be reasonable
        assert set_time < 10.0, f"Set operations took too long: {set_time:.2f}s"
        assert get_time < 5.0, f"Get operations took too long: {get_time:.2f}s"
        
        self.record_metric("bulk_set_time_seconds", set_time)
        self.record_metric("bulk_get_time_seconds", get_time)
        self.record_metric("operations_per_second_set", num_operations / set_time)
        self.record_metric("operations_per_second_get", num_operations / get_time)
    
    def test_large_key_space_performance_real(self):
        """Test performance with large number of configuration keys."""
        num_keys = 5000
        
        # Create large key space
        for i in range(num_keys):
            self.config_manager.set(f"large.keyspace.{i:05d}", f"value_{i}")
        
        start_time = time.time()
        
        # Test key listing performance
        all_keys = self.config_manager.keys()
        
        keys_time = time.time() - start_time
        
        # Should complete reasonably quickly
        assert keys_time < 2.0, f"Key listing took too long: {keys_time:.2f}s"
        assert len(all_keys) >= num_keys
        
        start_time = time.time()
        
        # Test pattern matching performance
        pattern_keys = self.config_manager.keys("large\\.keyspace\\..*")
        
        pattern_time = time.time() - start_time
        
        assert pattern_time < 5.0, f"Pattern matching took too long: {pattern_time:.2f}s"
        assert len(pattern_keys) == num_keys
        
        self.record_metric("large_keyspace_keys", num_keys)
        self.record_metric("key_listing_time", keys_time)
        self.record_metric("pattern_matching_time", pattern_time)
    
    def test_validation_performance_real(self):
        """Test validation performance with many configurations."""
        num_configs = 1000
        
        # Set up many configurations with validation
        for i in range(num_configs):
            key = f"validation.perf.{i:04d}"
            self.config_manager.set(key, f"value_{i:04d}")
        
        # Add validation schema
        schema = {}
        for i in range(0, num_configs, 10):  # Every 10th config
            key = f"validation.perf.{i:04d}"
            schema[key] = {
                "type": str,
                "validation_rules": ["min_length:5"],
                "required": False
            }
        
        self.config_manager.add_validation_schema(schema)
        
        start_time = time.time()
        
        # Run validation
        validation_result = self.config_manager.validate_all_configurations()
        
        validation_time = time.time() - start_time
        
        # Should complete reasonably quickly
        assert validation_time < 5.0, f"Validation took too long: {validation_time:.2f}s"
        assert isinstance(validation_result, ConfigurationValidationResult)
        
        self.record_metric("validation_configs", num_configs)
        self.record_metric("validation_time_seconds", validation_time)
        self.record_metric("validations_per_second", num_configs / validation_time)


class TestEnvironmentDetectionAndManagement(SSotBaseTestCase):
    """Test environment detection and management capabilities."""
    
    def test_environment_detection_real(self):
        """Test environment detection from various sources."""
        # Test with explicit environment
        manager_explicit = UnifiedConfigurationManager(environment="production")
        assert manager_explicit.environment == "production"
        
        # Test with environment detection from IsolatedEnvironment
        with self.temp_env_vars(ENVIRONMENT="staging"):
            manager_detected = UnifiedConfigurationManager()
            assert manager_detected.environment == "staging"
        
        with self.temp_env_vars(STAGE="development"):
            manager_stage = UnifiedConfigurationManager()  
            assert manager_stage.environment == "development"
        
        # Test fallback to development
        with self.temp_env_vars():
            # Clear any environment variables that might affect detection
            for var in ["ENVIRONMENT", "STAGE", "ENV", "DEPLOYMENT_ENV"]:
                self.delete_env_var(var)
            
            manager_default = UnifiedConfigurationManager()
            assert manager_default.environment == "development"
        
        self.record_metric("environment_detection_tests", 4)
    
    def test_environment_specific_configurations_real(self):
        """Test environment-specific configuration handling."""
        # Create managers for different environments
        dev_manager = UnifiedConfigurationManager(environment="development")
        staging_manager = UnifiedConfigurationManager(environment="staging") 
        prod_manager = UnifiedConfigurationManager(environment="production")
        
        # Each should have environment properly set
        assert dev_manager.environment == "development"
        assert staging_manager.environment == "staging"
        assert prod_manager.environment == "production"
        
        # Set environment-specific values
        dev_manager.set("app.debug", True)
        staging_manager.set("app.debug", False)  
        prod_manager.set("app.debug", False)
        
        # Values should be isolated by environment context
        assert dev_manager.get("app.debug") is True
        assert staging_manager.get("app.debug") is False
        assert prod_manager.get("app.debug") is False
        
        self.record_metric("environment_isolation", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])