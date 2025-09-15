from shared.isolated_environment import get_env
"""Comprehensive unit tests for Analytics Service Isolated Environment Management.

BUSINESS VALUE: Ensures environment management reliability and independence for
analytics service operations. Critical for configuration management, testing
isolation, and service independence.

Tests cover:
- Singleton pattern implementation
- Environment variable get/set operations
- Isolation mode for testing
- Thread safety
- Cache management
- Environment detection methods

NO MOCKS POLICY: Tests the real IsolatedEnvironment implementation with
controlled test scenarios.
"""

import os
import threading
import time
# NO MOCKS - removed all mock imports per NO MOCKS POLICY
from concurrent.futures import ThreadPoolExecutor

import pytest

from shared.isolated_environment import (
    IsolatedEnvironment,
    get_env,
)


class IsolatedEnvironmentSingletonTests:
    """Test suite for IsolatedEnvironment singleton behavior."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Reset singleton
        IsolatedEnvironment._instance = None
        
        # Clear any global environment manager
        import analytics_service.analytics_core.isolated_environment as env_module
        env_module._env_manager = None

    def teardown_method(self):
        """Clean up after each test."""
        # Reset singleton
        IsolatedEnvironment._instance = None
        
        # Clear any global environment manager
        import analytics_service.analytics_core.isolated_environment as env_module
        env_module._env_manager = None

    def test_singleton_instance(self):
        """Test that IsolatedEnvironment follows singleton pattern."""
        env1 = IsolatedEnvironment()
        env2 = IsolatedEnvironment()
        
        assert env1 is env2
        assert id(env1) == id(env2)

    def test_get_env_singleton(self):
        """Test that get_env returns the same singleton instance."""
        env1 = get_env()
        env2 = get_env()
        
        assert env1 is env2
        assert isinstance(env1, IsolatedEnvironment)

    def test_singleton_thread_safety(self):
        """Test singleton pattern is thread-safe."""
        instances = []
        
        def create_instance():
            instances.append(IsolatedEnvironment())
        
        # Create instances from multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

    def test_get_env_thread_safety(self):
        """Test get_env function is thread-safe."""
        instances = []
        
        def get_instance():
            instances.append(get_env())
        
        # Create instances from multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_instance) for _ in range(20)]
            for future in futures:
                future.result()
        
        # All instances should be the same
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance


class IsolatedEnvironmentBasicOperationsTests:
    """Test suite for basic environment variable operations."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Reset singleton
        IsolatedEnvironment._instance = None
        
        # Get fresh environment
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.clear_cache()

    def test_get_with_default(self):
        """Test getting environment variables with default values."""
        env = self.env
        
        # Test with non-existent key
        value = env.get("NONEXISTENT_KEY", "default_value")
        assert value == "default_value"
        
        # Test with None default
        value = env.get("NONEXISTENT_KEY", None)
        assert value is None
        
        # Test without default (should return None)
        value = env.get("NONEXISTENT_KEY")
        assert value is None

    def test_set_and_get(self):
        """Test setting and getting environment variables."""
        env = self.env
        
        # Set a value
        env.set("TEST_KEY", "test_value")
        
        # Get the value
        value = env.get("TEST_KEY")
        assert value == "test_value"
        
        # Get with default (should return actual value)
        value = env.get("TEST_KEY", "default")
        assert value == "test_value"

    def test_overwrite_existing_value(self):
        """Test overwriting existing environment variables."""
        env = self.env
        
        # Set initial value
        env.set("TEST_KEY", "initial_value")
        assert env.get("TEST_KEY") == "initial_value"
        
        # Overwrite value
        env.set("TEST_KEY", "new_value")
        assert env.get("TEST_KEY") == "new_value"

    def test_set_with_category(self):
        """Test setting environment variables with category (should be ignored)."""
        env = self.env
        
        # Set with category (compatibility parameter)
        env.set("TEST_KEY", "test_value", category="test_category")
        
        # Should still work normally
        value = env.get("TEST_KEY")
        assert value == "test_value"

    def test_is_set(self):
        """Test checking if environment variables are set."""
        env = self.env
        
        # Test non-existent key
        assert env.is_set("NONEXISTENT_KEY") is False
        
        # Set a key and test
        env.set("TEST_KEY", "test_value")
        assert env.is_set("TEST_KEY") is True

    def test_unset(self):
        """Test unsetting environment variables."""
        env = self.env
        
        # Set a key
        env.set("TEST_KEY", "test_value")
        assert env.is_set("TEST_KEY") is True
        
        # Unset the key
        env.unset("TEST_KEY")
        assert env.is_set("TEST_KEY") is False
        assert env.get("TEST_KEY") is None

    def test_unset_nonexistent(self):
        """Test unsetting non-existent environment variables."""
        env = self.env
        
        # Should not raise error
        env.unset("NONEXISTENT_KEY")
        assert env.is_set("NONEXISTENT_KEY") is False


class IsolatedEnvironmentIsolationModeTests:
    """Test suite for isolation mode functionality."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Reset singleton
        IsolatedEnvironment._instance = None
        
        # Get fresh environment
        self.env = get_env()
        self.env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.clear_cache()

    def test_isolation_mode_toggle(self):
        """Test enabling and disabling isolation mode."""
        env = self.env
        
        # Initially not isolated (depends on initialization)
        env.disable_isolation()  # Ensure we start from known state
        
        # Enable isolation
        env.enable_isolation()
        assert env._isolation_enabled is True
        
        # Disable isolation
        env.disable_isolation()
        assert env._isolation_enabled is False

    def test_isolation_mode_behavior(self):
        """Test isolation mode behavior for environment variables."""
        env = self.env
        
        # Disable isolation first
        env.disable_isolation()
        
        # Set a value without isolation
        test_key = f"TEST_ANALYTICS_ISOLATION_{int(time.time())}"
        env.set(test_key, "non_isolated_value")
        
        # Should be in actual environment
        assert env.get(test_key) == "non_isolated_value"
        
        # Enable isolation
        env.enable_isolation()
        
        # Set a value with isolation
        env.set(test_key, "isolated_value")
        
        # Should get isolated value
        assert env.get(test_key) == "isolated_value"
        
        # But actual environment should still have old value
        assert env.get(test_key) == "non_isolated_value"
        
        # Clean up
        os.environ.pop(test_key, None)

    def test_isolation_overrides_real_environment(self):
        """Test that isolation overrides real environment variables."""
        env = self.env
        test_key = f"TEST_ANALYTICS_OVERRIDE_{int(time.time())}"
        
        # Set value in real environment
        os.environ[test_key] = "real_value"
        
        # Enable isolation
        env.enable_isolation()
        
        # Set override value
        env.set(test_key, "override_value")
        
        # Should get override value
        assert env.get(test_key) == "override_value"
        
        # Clean up
        os.environ.pop(test_key, None)

    def test_isolation_disable_clears_overrides(self):
        """Test that disabling isolation clears overrides."""
        env = self.env
        
        # Enable isolation
        env.enable_isolation()
        
        # Set some overrides
        env.set("TEST_KEY_1", "value_1")
        env.set("TEST_KEY_2", "value_2")
        
        assert env.get("TEST_KEY_1") == "value_1"
        assert env.get("TEST_KEY_2") == "value_2"
        
        # Disable isolation
        env.disable_isolation()
        
        # Overrides should be cleared
        assert env.get("TEST_KEY_1") is None
        assert env.get("TEST_KEY_2") is None

    def test_unset_in_isolation_mode(self):
        """Test unsetting variables in isolation mode."""
        env = self.env
        test_key = f"TEST_ANALYTICS_UNSET_{int(time.time())}"
        
        # Enable isolation
        env.enable_isolation()
        
        # Set a value
        env.set(test_key, "test_value")
        assert env.get(test_key) == "test_value"
        
        # Unset the value
        env.unset(test_key)
        assert env.is_set(test_key) is False
        assert env.get(test_key) is None


class IsolatedEnvironmentCachingTests:
    """Test suite for environment caching functionality."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Reset singleton
        IsolatedEnvironment._instance = None
        
        # Get fresh environment
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.clear_cache()

    def test_cache_behavior(self):
        """Test that values are cached properly."""
        env = self.env
        test_key = f"TEST_ANALYTICS_CACHE_{int(time.time())}"
        
        # Set value in real environment
        os.environ[test_key] = "cached_value"
        
        # Get value (should be cached)
        value1 = env.get(test_key)
        assert value1 == "cached_value"
        
        # Change real environment
        os.environ[test_key] = "new_value"
        
        # Get value again (should return cached value)
        value2 = env.get(test_key)
        assert value2 == "cached_value"  # Should be cached, not new value
        
        # Clear cache
        env.clear_cache()
        
        # Now should get new value
        value3 = env.get(test_key)
        assert value3 == "new_value"
        
        # Clean up
        os.environ.pop(test_key, None)

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        env = self.env
        
        # Set some values to populate cache
        env.set("TEST_KEY_1", "value_1")
        env.set("TEST_KEY_2", "value_2")
        
        # Verify values are accessible
        assert env.get("TEST_KEY_1") == "value_1"
        assert env.get("TEST_KEY_2") == "value_2"
        
        # Clear cache
        env.clear_cache()
        
        # Values should still be accessible (from overrides)
        assert env.get("TEST_KEY_1") == "value_1"
        assert env.get("TEST_KEY_2") == "value_2"

    def test_cache_thread_safety(self):
        """Test that cache operations are thread-safe."""
        env = self.env
        results = []
        
        def cache_operations():
            # Set and get values
            env.set("THREAD_TEST_KEY", f"value_{threading.current_thread().ident}")
            value = env.get("THREAD_TEST_KEY")
            results.append(value)
            
            # Clear cache
            env.clear_cache()
        
        # Run operations from multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=cache_operations)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have results from all threads
        assert len(results) == 5
        
        # Each result should be valid
        for result in results:
            assert result.startswith("value_")


class IsolatedEnvironmentPrefixOperationsTests:
    """Test suite for prefix-based operations."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Reset singleton
        IsolatedEnvironment._instance = None
        
        # Get fresh environment
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.clear_cache()

    def test_get_all_with_prefix(self):
        """Test getting all environment variables with specific prefix."""
        env = self.env
        
        # Set some values with specific prefix
        env.set("ANALYTICS_TEST_KEY_1", "value_1")
        env.set("ANALYTICS_TEST_KEY_2", "value_2")
        env.set("ANALYTICS_OTHER_KEY", "other_value")
        env.set("OTHER_PREFIX_KEY", "different_value")
        
        # Get all with prefix
        analytics_vars = env.get_all_with_prefix("ANALYTICS_")
        
        # Should contain analytics variables
        assert "ANALYTICS_TEST_KEY_1" in analytics_vars
        assert "ANALYTICS_TEST_KEY_2" in analytics_vars
        assert "ANALYTICS_OTHER_KEY" in analytics_vars
        assert analytics_vars["ANALYTICS_TEST_KEY_1"] == "value_1"
        assert analytics_vars["ANALYTICS_TEST_KEY_2"] == "value_2"
        assert analytics_vars["ANALYTICS_OTHER_KEY"] == "other_value"
        
        # Should not contain other variables
        assert "OTHER_PREFIX_KEY" not in analytics_vars

    def test_get_all_with_prefix_mixed_sources(self):
        """Test prefix matching with both overrides and real environment."""
        env = self.env
        test_key_base = f"ANALYTICS_TEST_{int(time.time())}"
        
        # Set value in real environment
        real_key = f"{test_key_base}_REAL"
        os.environ[real_key] = "real_value"
        
        # Set value in overrides (isolation mode)
        override_key = f"{test_key_base}_OVERRIDE"
        env.set(override_key, "override_value")
        
        # Get all with prefix
        result = env.get_all_with_prefix(test_key_base)
        
        # Should contain both
        assert real_key in result
        assert override_key in result
        assert result[real_key] == "real_value"
        assert result[override_key] == "override_value"
        
        # Clean up
        os.environ.pop(real_key, None)

    def test_get_all_with_prefix_empty_result(self):
        """Test prefix matching with no matches."""
        env = self.env
        
        # Set some unrelated variables
        env.set("OTHER_KEY_1", "value_1")
        env.set("DIFFERENT_PREFIX_KEY", "value_2")
        
        # Get with non-matching prefix
        result = env.get_all_with_prefix("NONEXISTENT_PREFIX_")
        
        # Should be empty
        assert result == {}


class IsolatedEnvironmentEnvironmentDetectionTests:
    """Test suite for environment detection methods."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Reset singleton
        IsolatedEnvironment._instance = None
        
        # Get fresh environment
        self.env = get_env()
        self.env.enable_isolation()
        self.env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        self.env.disable_isolation()
        self.env.clear_cache()

    def test_environment_name_detection(self):
        """Test environment name detection and normalization."""
        env = self.env
        
        # Test development variants
        for dev_env in ["development", "dev", "local"]:
            env.set("ENVIRONMENT", dev_env)
            assert env.get_environment_name() == "development"
        
        # Test test variants
        for test_env in ["test", "testing"]:
            env.set("ENVIRONMENT", test_env)
            assert env.get_environment_name() == "test"
        
        # Test staging
        env.set("ENVIRONMENT", "staging")
        assert env.get_environment_name() == "staging"
        
        # Test production variants
        for prod_env in ["production", "prod"]:
            env.set("ENVIRONMENT", prod_env)
            assert env.get_environment_name() == "production"
        
        # Test unknown environment (should default to development)
        env.set("ENVIRONMENT", "unknown")
        assert env.get_environment_name() == "development"

    def test_environment_boolean_methods(self):
        """Test environment boolean detection methods."""
        env = self.env
        
        # Test development
        env.set("ENVIRONMENT", "development")
        assert env.is_development() is True
        assert env.is_staging() is False
        assert env.is_production() is False
        assert env.is_test() is False
        
        # Test test
        env.set("ENVIRONMENT", "test")
        assert env.is_development() is False
        assert env.is_staging() is False
        assert env.is_production() is False
        assert env.is_test() is True
        
        # Test staging
        env.set("ENVIRONMENT", "staging")
        assert env.is_development() is False
        assert env.is_staging() is True
        assert env.is_production() is False
        assert env.is_test() is False
        
        # Test production
        env.set("ENVIRONMENT", "production")
        assert env.is_development() is False
        assert env.is_staging() is False
        assert env.is_production() is True
        assert env.is_test() is False

    def test_environment_name_case_insensitive(self):
        """Test that environment detection is case insensitive."""
        env = self.env
        
        # Test uppercase
        env.set("ENVIRONMENT", "PRODUCTION")
        assert env.get_environment_name() == "production"
        assert env.is_production() is True
        
        # Test mixed case
        env.set("ENVIRONMENT", "Staging")
        assert env.get_environment_name() == "staging"
        assert env.is_staging() is True

    def test_default_environment(self):
        """Test default environment when ENVIRONMENT is not set."""
        env = self.env
        
        # Ensure ENVIRONMENT is not set
        env.unset("ENVIRONMENT")
        
        # Should default to development
        assert env.get_environment_name() == "development"
        assert env.is_development() is True


class IsolatedEnvironmentIntegrationTests:
    """Integration tests for IsolatedEnvironment with real scenarios."""

    def test_real_environment_interaction(self):
        """Test interaction with real environment variables."""
        # Don't use isolation for this test
        env = get_env()
        env.disable_isolation()
        env.clear_cache()
        
        test_key = f"ANALYTICS_REAL_TEST_{int(time.time())}"
        
        try:
            # Set in real environment via env manager
            env.set(test_key, "real_test_value")
            
            # Should be in actual environment
            assert env.get(test_key) == "real_test_value"
            
            # Should be retrievable
            assert env.get(test_key) == "real_test_value"
            
        finally:
            # Clean up
            os.environ.pop(test_key, None)

    def test_environment_isolation_independence(self):
        """Test that multiple instances maintain proper isolation."""
        # Reset to ensure clean state
        IsolatedEnvironment._instance = None
        
        env1 = get_env()
        env1.enable_isolation()
        
        # This should be the same instance due to singleton
        env2 = get_env()
        
        # Both should reference the same object
        assert env1 is env2
        
        # Set value through env1
        env1.set("TEST_ISOLATION", "value_1")
        
        # Should be accessible through env2
        assert env2.get("TEST_ISOLATION") == "value_1"
        
        # Disable isolation
        env1.disable_isolation()
        
        # Should affect env2 as well (same instance)
        assert not env2._isolation_enabled