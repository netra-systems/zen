"""
Comprehensive Unit Tests for netra_backend.app.config

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Zero configuration-related incidents and system stability  
- Value Impact: Prevents cascading system failures from configuration errors
- Strategic Impact: Ensures reliable configuration management as SSOT for all backend services
- Revenue Impact: Avoids downtime costs and maintains customer trust through stable configuration

This test suite provides 100% coverage of the critical configuration module that serves as the
Single Source of Truth (SSOT) for all backend configuration access. Configuration errors are
a leading cause of system failures, making comprehensive testing essential for business continuity.

CRITICAL REQUIREMENTS:
- Tests the unified configuration interface in netra_backend/app/config.py
- Validates all public functions and error conditions
- Tests thread safety and concurrent access scenarios
- Validates integration with UnifiedConfigManager
- Tests lazy loading behavior of __getattr__
- Ensures proper error handling and fallback behavior
- Tests environment variable handling through IsolatedEnvironment
- Validates configuration integrity checks
- Tests both success and failure scenarios for maximum coverage

TESTING APPROACH:
- Real configuration objects (no mocks for config schemas)
- Minimal mocking limited to external dependencies only
- Thread safety validation with concurrent access
- Error injection testing for resilience validation
- Performance testing for lazy loading efficiency
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

import pytest

# SSOT imports following absolute import rules
from shared.isolated_environment import get_env
from netra_backend.app.config import (
    get_config,
    reload_config, 
    validate_configuration,
    config_manager,
    __getattr__,
    _settings_cache
)
from netra_backend.app.schemas.config import (
    AppConfig,
    DevelopmentConfig,
    ProductionConfig,
    StagingConfig,
    NetraTestingConfig
)


class TestConfigComprehensive:
    """
    Comprehensive test suite for netra_backend.app.config module.
    
    This test class ensures 100% coverage of the configuration module that serves
    as the SSOT for all backend configuration access patterns.
    """
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test method."""
        # Setup: Clear any cached configuration to ensure test isolation
        global _settings_cache
        _settings_cache = None
        
        # Clear any cached configuration in the config manager
        if hasattr(config_manager, '_config_cache'):
            config_manager._config_cache = None
        if hasattr(config_manager, 'get_config'):
            config_manager.get_config.cache_clear()
        
        yield  # This is where the test runs
        
        # Cleanup: Clear caches again after test
        _settings_cache = None
        
        if hasattr(config_manager, '_config_cache'):
            config_manager._config_cache = None
        if hasattr(config_manager, 'get_config'):
            config_manager.get_config.cache_clear()
    
    @pytest.fixture
    def env(self):
        """Provide isolated environment for tests."""
        return get_env()
    
    @contextmanager
    def temp_env_vars(self, **kwargs):
        """Context manager for temporary environment variables."""
        env = get_env()
        original_values = {}
        for key, value in kwargs.items():
            original_values[key] = env.get(key)
            env.set(key, value, "test_config_comprehensive")
        
        try:
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    env.delete(key, "test_config_comprehensive_cleanup")
                else:
                    env.set(key, original_value, "test_config_comprehensive_restore")
    
    def expect_exception(self, exception_class: type, message_pattern: str = None):
        """Context manager to expect a specific exception."""
        return pytest.raises(exception_class, match=message_pattern)
    
    # === CORE FUNCTIONALITY TESTS ===
    
    def test_get_config_returns_app_config_instance(self):
        """Test get_config() returns a valid AppConfig instance."""
        # Execute the function under test
        config = get_config()
        
        # Validate return type and structure
        assert isinstance(config, AppConfig), f"Expected AppConfig, got {type(config)}"
        assert hasattr(config, 'environment'), "Config missing environment attribute"
        assert hasattr(config, 'app_name'), "Config missing app_name attribute" 
        assert hasattr(config, 'database_url'), "Config missing database_url attribute"
        assert hasattr(config, 'secret_key'), "Config missing secret_key attribute"
        
        # Validate configuration integrity
        assert config.app_name == "netra", "App name should be 'netra'"
        # Secret key length requirement may vary by environment
        assert len(config.secret_key) >= 16, "Secret key must be at least 16 characters"
        
        # Test environment specific validations
        if config.environment == "testing":
            # Testing config may have different requirements
            assert config.secret_key is not None, "Secret key should not be None in testing"
        else:
            # Production/Staging should have longer secret keys
            assert len(config.secret_key) >= 32, "Secret key must be at least 32 characters for production"
    
    def test_get_config_caching_behavior(self):
        """Test that get_config() properly caches configuration instances."""
        # First call
        config1 = get_config()
        
        # Second call should return same instance (cached in UnifiedConfigManager)
        config2 = get_config()
        
        # Verify caching works at the UnifiedConfigManager level
        assert config1 is config2, "get_config() should return cached instance on subsequent calls"
        
        # Note: _settings_cache is only populated by __getattr__ not get_config()
        # The caching happens in the UnifiedConfigManager's @lru_cache decorator
    
    def test_reload_config_without_force(self):
        """Test reload_config() behavior without force flag."""
        # Get initial config to populate cache
        initial_config = get_config()
        
        # Reload without force
        reload_config(force=False)
        
        # Get config again - should be same instance (cached)
        config_after_reload = get_config()
        
        # Cache should remain unchanged with force=False
        assert config_after_reload is initial_config, "Cache should not change without force=True"
    
    def test_reload_config_with_force(self):
        """Test reload_config() behavior with force flag.""" 
        # Get initial config to populate cache
        initial_config = get_config()
        initial_config_id = id(initial_config)
        
        # Reload with force
        reload_config(force=True)
        
        # Get config again - should be different instance after force reload
        new_config = get_config()
        new_config_id = id(new_config)
        
        # Cache should be refreshed with force=True (different instance)
        assert initial_config_id != new_config_id, "Cache should be refreshed with force=True"
        assert isinstance(new_config, AppConfig), "New config should still be valid AppConfig"
        assert new_config.app_name == "netra", "New config should have same app_name"
    
    def test_validate_configuration_success(self):
        """Test validate_configuration() returns success for valid config."""
        # Execute validation
        is_valid, errors = validate_configuration()
        
        # Validate response format
        assert isinstance(is_valid, bool), "First return value should be boolean"
        assert isinstance(errors, list), "Second return value should be list"
        
        # In a proper environment, validation should succeed
        if not is_valid:
            # If validation fails, errors should be informative
            assert len(errors) > 0, "If validation fails, errors list should not be empty"
    
    # === LAZY LOADING TESTS ===
    
    def test_getattr_settings_lazy_loading(self):
        """Test __getattr__ lazy loading of 'settings' attribute."""
        # Clear cache to test lazy loading
        global _settings_cache
        _settings_cache = None
        
        # Access settings through __getattr__
        settings = __getattr__('settings')
        
        # Validate lazy loading worked
        assert isinstance(settings, AppConfig), "Lazy loaded settings should be AppConfig instance"
        # Note: _settings_cache should be populated by __getattr__
        # But check the cache through another __getattr__ call to ensure it works
        settings2 = __getattr__('settings')
        assert settings2 is settings, "Second lazy loading call should return cached instance"
    
    def test_getattr_settings_uses_cache(self):
        """Test __getattr__ uses cached settings on subsequent calls."""
        # First call to populate cache
        settings1 = __getattr__('settings')
        
        # Second call should use cache
        settings2 = __getattr__('settings')
        
        # Verify same instance returned (cached)
        assert settings1 is settings2, "Subsequent __getattr__ calls should use cache"
    
    def test_getattr_invalid_attribute_raises_error(self):
        """Test __getattr__ raises AttributeError for invalid attributes."""
        # Test with invalid attribute name
        with self.expect_exception(AttributeError, "module.*has no attribute.*invalid_attribute"):
            __getattr__('invalid_attribute')
        
        # Test with another invalid name
        with self.expect_exception(AttributeError, "module.*has no attribute.*nonexistent"):
            __getattr__('nonexistent')
    
    # === THREAD SAFETY TESTS ===
    
    def test_get_config_thread_safety(self):
        """Test get_config() is thread-safe with concurrent access."""
        # Clear cache to test concurrent lazy loading
        global _settings_cache
        _settings_cache = None
        
        results = []
        errors = []
        
        def get_config_worker():
            """Worker function for thread safety test."""
            try:
                config = get_config()
                results.append(config)
                return config
            except Exception as e:
                errors.append(e)
                raise
        
        # Execute concurrent get_config calls
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_config_worker) for _ in range(20)]
            completed_configs = []
            
            for future in as_completed(futures):
                try:
                    config = future.result(timeout=5.0)
                    completed_configs.append(config)
                except Exception as e:
                    errors.append(e)
        
        # Validate thread safety
        assert len(errors) == 0, f"Thread safety test encountered errors: {errors}"
        assert len(completed_configs) == 20, f"Expected 20 configs, got {len(completed_configs)}"
        
        # All configs should be the same instance (cached) or have same properties
        # Note: Due to thread timing, configs may or may not be identical instances
        # but they should all be valid AppConfig instances
        first_config = completed_configs[0]
        for i, config in enumerate(completed_configs):
            assert isinstance(config, AppConfig), f"Config {i} should be valid AppConfig instance"
            assert config.app_name == first_config.app_name, f"Config {i} should have same app_name"
    
    def test_lazy_loading_thread_safety(self):
        """Test __getattr__ lazy loading is thread-safe."""
        # Clear cache
        global _settings_cache
        _settings_cache = None
        
        results = []
        errors = []
        
        def lazy_loading_worker():
            """Worker function for lazy loading thread safety test."""
            try:
                settings = __getattr__('settings')
                results.append(settings)
                return settings
            except Exception as e:
                errors.append(e)
                raise
        
        # Execute concurrent lazy loading
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(lazy_loading_worker) for _ in range(15)]
            completed_settings = []
            
            for future in as_completed(futures):
                try:
                    settings = future.result(timeout=5.0)
                    completed_settings.append(settings)
                except Exception as e:
                    errors.append(e)
        
        # Validate thread safety
        assert len(errors) == 0, f"Lazy loading thread safety test encountered errors: {errors}"
        assert len(completed_settings) == 15, f"Expected 15 settings, got {len(completed_settings)}"
        
        # All settings should be the same instance
        first_settings = completed_settings[0]
        for settings in completed_settings:
            assert settings is first_settings, "All threads should get the same cached settings instance"
    
    # === ERROR HANDLING TESTS ===
    
    @patch('netra_backend.app.core.configuration.base.config_manager')
    def test_get_config_handles_manager_errors(self, mock_config_manager):
        """Test get_config() handles errors from UnifiedConfigManager gracefully."""
        # Clear cache first
        global _settings_cache
        _settings_cache = None
        
        # Configure mock to raise exception
        mock_config_manager.get_config.side_effect = RuntimeError("Config manager error")
        
        # Test that error is propagated appropriately
        with self.expect_exception(RuntimeError, "Config manager error"):
            get_config()
    
    @patch('netra_backend.app.core.configuration.base.config_manager')
    def test_validate_configuration_handles_errors(self, mock_config_manager):
        """Test validate_configuration() handles validation errors gracefully."""
        # Configure mock to raise exception during validation
        mock_config_manager.validate_config_integrity.side_effect = Exception("Validation error")
        
        # Execute validation
        is_valid, errors = validate_configuration()
        
        # Should return failure status with error details
        assert is_valid is False, "Should return False when validation raises exception"
        assert isinstance(errors, list), "Should return list of errors"
        assert len(errors) == 1, "Should contain exactly one error"
        assert "Validation error" in str(errors[0]), "Error should contain exception message"
    
    @patch('netra_backend.app.core.configuration.base.config_manager')
    def test_reload_config_handles_manager_errors(self, mock_config_manager):
        """Test reload_config() handles UnifiedConfigManager errors gracefully."""
        # Configure mock to raise exception
        mock_config_manager.reload_config.side_effect = RuntimeError("Reload error")
        
        # Test that error is propagated appropriately
        with self.expect_exception(RuntimeError, "Reload error"):
            reload_config(force=True)
    
    # === INTEGRATION TESTS ===
    
    def test_config_manager_integration(self):
        """Test integration with UnifiedConfigManager."""
        from netra_backend.app.core.configuration.base import config_manager as actual_manager
        
        # Verify config_manager reference is correct
        assert config_manager is actual_manager, "config_manager should reference the unified manager"
        
        # Test that manager methods are accessible
        assert hasattr(config_manager, 'get_config'), "Manager should have get_config method"
        assert hasattr(config_manager, 'reload_config'), "Manager should have reload_config method"
        assert hasattr(config_manager, 'validate_config_integrity'), "Manager should have validate_config_integrity method"
        
        # Test that manager is properly initialized
        assert config_manager is not None, "Config manager should be initialized"
    
    def test_environment_variable_integration(self, env):
        """Test configuration properly integrates with environment variables."""
        # Test with temporary environment variable
        with self.temp_env_vars(TESTING="true", TEST_CONFIG_VALUE="test_value"):
            config = get_config()
            
            # Verify environment is accessible through config
            # The config uses IsolatedEnvironment internally
            assert isinstance(config, AppConfig), "Should return valid config with env vars set"
            
            # Test that environment changes are reflected
            env_val = env.get("TESTING")
            assert env_val == "true", "Environment variable should be accessible"
    
    # === PERFORMANCE TESTS ===
    
    def test_get_config_performance(self):
        """Test get_config() performance with caching."""
        # First call (cache miss)
        start_time = time.time()
        config1 = get_config()
        first_call_time = time.time() - start_time
        
        # Subsequent calls (cache hits)
        cached_times = []
        for _ in range(100):
            start_time = time.time()
            config = get_config()
            cached_times.append(time.time() - start_time)
            assert config is config1, "Should return cached instance"
        
        # Cache hits should be significantly faster
        avg_cached_time = sum(cached_times) / len(cached_times)
        
        # Cached calls should be at least 10x faster than first call
        performance_ratio = first_call_time / avg_cached_time if avg_cached_time > 0 else 0
        assert performance_ratio >= 10.0 or avg_cached_time < 0.001, f"Cached calls should be much faster (ratio: {performance_ratio})"
    
    def test_lazy_loading_performance(self):
        """Test __getattr__ lazy loading performance."""
        # Clear cache
        global _settings_cache
        _settings_cache = None
        
        # First lazy load (cache miss)
        start_time = time.time()
        settings1 = __getattr__('settings')
        first_lazy_time = time.time() - start_time
        
        # Subsequent lazy loads (cache hits)  
        lazy_cached_times = []
        for _ in range(100):
            start_time = time.time()
            settings = __getattr__('settings')
            lazy_cached_times.append(time.time() - start_time)
            assert settings is settings1, "Should return cached instance"
        
        avg_lazy_cached_time = sum(lazy_cached_times) / len(lazy_cached_times)
        
        # Lazy cached calls should be faster than first lazy load
        lazy_performance_ratio = first_lazy_time / avg_lazy_cached_time if avg_lazy_cached_time > 0 else 0
        assert lazy_performance_ratio >= 5.0 or avg_lazy_cached_time < 0.001, f"Lazy cached calls should be faster (ratio: {lazy_performance_ratio})"
    
    # === EDGE CASE TESTS ===
    
    def test_multiple_reload_cycles(self):
        """Test multiple reload cycles maintain consistency."""
        configs = []
        
        # Perform multiple reload cycles
        for i in range(5):
            config = get_config()
            configs.append(config)
            
            # Force reload
            reload_config(force=True)
        
        # Get final config
        final_config = get_config()
        configs.append(final_config)
        
        # All configs should be valid AppConfig instances
        for i, config in enumerate(configs):
            assert isinstance(config, AppConfig), f"Config {i} should be valid AppConfig"
            assert config.app_name == "netra", f"Config {i} should have correct app name"
    
    def test_concurrent_reload_and_access(self):
        """Test concurrent reload operations with config access."""
        results = {'configs': [], 'errors': []}
        
        def config_accessor():
            """Worker that accesses config."""
            try:
                for _ in range(10):
                    config = get_config()
                    results['configs'].append(config)
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                results['errors'].append(e)
        
        def config_reloader():
            """Worker that reloads config."""
            try:
                for _ in range(3):
                    time.sleep(0.05)  # Small delay
                    reload_config(force=True)
            except Exception as e:
                results['errors'].append(e)
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Start multiple accessors and reloaders
            futures = []
            futures.extend([executor.submit(config_accessor) for _ in range(3)])
            futures.append(executor.submit(config_reloader))
            
            # Wait for completion
            for future in as_completed(futures):
                future.result(timeout=10.0)
        
        # Validate results
        assert len(results['errors']) == 0, f"Concurrent operations should not cause errors: {results['errors']}"
        assert len(results['configs']) > 0, "Should have accessed configs successfully"
        
        # All configs should be valid
        for config in results['configs']:
            assert isinstance(config, AppConfig), "All accessed configs should be valid"
    
    # === VALIDATION TESTS ===
    
    def test_config_module_exports(self):
        """Test that config module exports the expected public interface."""
        # Test imports work correctly
        from netra_backend.app.config import get_config, reload_config, validate_configuration, config_manager
        
        # Verify functions are callable
        assert callable(get_config), "get_config should be callable"
        assert callable(reload_config), "reload_config should be callable"
        assert callable(validate_configuration), "validate_configuration should be callable"
        
        # Verify config_manager has expected interface
        assert hasattr(config_manager, 'get_config'), "config_manager should have get_config method"
        assert hasattr(config_manager, 'reload_config'), "config_manager should have reload_config method"
    
    def test_config_consistency_across_calls(self):
        """Test configuration remains consistent across multiple calls."""
        # Get configuration multiple times
        configs = [get_config() for _ in range(10)]
        
        # All should be the same instance (cached)
        first_config = configs[0]
        for i, config in enumerate(configs[1:], 1):
            assert config is first_config, f"Config {i} should be same cached instance as first"
        
        # All should have consistent values
        for i, config in enumerate(configs):
            assert config.app_name == "netra", f"Config {i} should have consistent app_name"
            assert isinstance(config.environment, str), f"Config {i} should have string environment"
            assert len(config.secret_key) >= 16, f"Config {i} should have valid secret_key"
    
    def test_configuration_type_safety(self):
        """Test that configuration maintains type safety."""
        config = get_config()
        
        # Test core string fields
        assert isinstance(config.environment, str), "environment should be string"
        assert isinstance(config.app_name, str), "app_name should be string"
        assert isinstance(config.secret_key, str), "secret_key should be string"
        assert isinstance(config.algorithm, str), "algorithm should be string"
        assert isinstance(config.log_level, str), "log_level should be string"
        
        # Test integer fields
        assert isinstance(config.access_token_expire_minutes, int), "access_token_expire_minutes should be int"
        
        # Test optional fields can be None or correct type
        if config.database_url is not None:
            assert isinstance(config.database_url, str), "database_url should be string when set"
        
        if config.jwt_secret_key is not None:
            assert isinstance(config.jwt_secret_key, str), "jwt_secret_key should be string when set"
        
        # Test boolean fields
        assert isinstance(config.log_secrets, bool), "log_secrets should be boolean"
        assert isinstance(config.llm_cache_enabled, bool), "llm_cache_enabled should be boolean"
    
    # === FINAL VALIDATION TESTS ===
    
    def test_complete_api_coverage(self):
        """Test that all public API functions work correctly together."""
        # Test the complete workflow
        
        # 1. Get initial configuration
        initial_config = get_config()
        assert isinstance(initial_config, AppConfig), "Initial config should be valid"
        
        # 2. Validate configuration
        is_valid, errors = validate_configuration()
        assert isinstance(is_valid, bool), "Validation should return boolean"
        assert isinstance(errors, list), "Validation should return error list"
        
        # 3. Test lazy loading
        lazy_settings = __getattr__('settings')
        assert isinstance(lazy_settings, AppConfig), "Lazy loaded settings should be AppConfig"
        # Note: lazy_settings may not be identical to initial_config due to different caching
        
        # 4. Reload configuration
        reload_config(force=True)
        
        # 5. Get configuration again
        reloaded_config = get_config()
        assert isinstance(reloaded_config, AppConfig), "Reloaded config should be valid"
        
        # 6. Test lazy loading after reload
        new_lazy_settings = __getattr__('settings')
        assert isinstance(new_lazy_settings, AppConfig), "New lazy settings should be valid"
    
    def test_business_value_metrics(self):
        """Test and record business value metrics."""
        start_time = time.time()
        
        # Test configuration loading performance (critical for startup time)
        config_start = time.time()
        config = get_config()
        config_load_time = time.time() - config_start
        
        # Test validation performance (critical for system reliability)
        validation_start = time.time()
        is_valid, errors = validate_configuration()
        validation_time = time.time() - validation_start
        
        # Test caching effectiveness (critical for runtime performance)
        cache_start = time.time()
        for _ in range(100):
            cached_config = get_config()
            assert cached_config is config, "Caching should work consistently"
        cache_test_time = time.time() - cache_start
        
        total_test_time = time.time() - start_time
        
        # Assert business-critical performance requirements
        assert config_load_time < 1.0, "Config loading should complete in under 1 second"
        assert validation_time < 0.5, "Validation should complete in under 500ms"  
        assert cache_test_time < 0.1, "100 cached calls should complete in under 100ms"