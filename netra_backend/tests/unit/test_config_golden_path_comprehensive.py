
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Comprehensive Unit Tests for Configuration Golden Path SSOT Classes

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (CRITICAL INFRASTRUCTURE)
- Business Goal: Zero configuration-related system failures and 100% deployment reliability
- Value Impact: Prevents configuration cascade failures that can cause $500K+ revenue loss
- Strategic Impact: Ensures stable golden path user flow from login → AI responses
- Revenue Impact: Eliminates downtime from configuration mismatches across environments

MISSION CRITICAL: These tests validate the configuration SSOT classes that enable:
1. Unified configuration access across all environments (TEST/DEV/STAGING/PROD)
2. Environment-specific configuration loading and validation 
3. Service startup reliability through proper configuration validation
4. Golden path user flow stability (users login → get AI responses)

GOLDEN PATH CRITICAL SCENARIOS TESTED:
1. Configuration Loading: get_config() returns proper environment-specific values
2. Database Configuration: Proper connection parameters for each environment
3. Service Discovery: Correct service URLs and ports for environment
4. CORS Configuration: Proper cross-origin settings for frontend-backend communication
5. Environment Isolation: IsolatedEnvironment prevents cross-environment pollution
6. Secrets Management: Secure handling of API keys and sensitive data
7. Configuration Validation: Invalid configurations are detected and reported

TESTING APPROACH:
- Real services where possible (minimal mocks only for external dependencies)
- SSOT compliance using test_framework utilities
- Business value focus on configuration scenarios that affect system stability
- Golden path focus on environment-specific configuration loading
- Coverage target: 90%+ method coverage on critical configuration paths
"""

import pytest
import asyncio
import threading
import time
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

# SSOT imports following absolute import rules
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.config import (
    get_config,
    reload_config,
    validate_configuration,
    config_manager
)
from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_unified_config,
    reload_unified_config,
    validate_config_integrity,
    get_environment,
    is_production,
    is_development,
    is_testing
)
from netra_backend.app.schemas.config import (
from netra_backend.app.services.user_execution_context import UserExecutionContext
    AppConfig,
    DevelopmentConfig,
    ProductionConfig,
    StagingConfig,
    NetraTestingConfig
)


class TestConfigurationGoldenPath(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    Comprehensive test suite for Configuration Golden Path SSOT classes.
    
    Tests the most critical configuration components that enable proper system
    configuration across all environments and ensure golden path user flow reliability.
    """
    
    def setup_method(self, method):
        """Set up test environment with proper isolation."""
        super().setup_method(method)
        
        # Clear any cached configuration for test isolation
        if hasattr(config_manager, '_config_cache'):
            config_manager._config_cache = None
        
        # Set test environment
        self.set_env_var('ENVIRONMENT', 'testing')
        self.set_env_var('TESTING', 'true')
    
    def teardown_method(self, method):
        """Clean up test environment."""
        # Clear configuration cache
        if hasattr(config_manager, '_config_cache'):
            config_manager._config_cache = None
            
        super().teardown_method(method)
    
    @contextmanager
    def temp_env_vars(self, **kwargs):
        """Context manager for temporary environment variables."""
        original_values = {}
        for key, value in kwargs.items():
            original_values[key] = self.env.get(key)
            self.env.set(key, value, "temp_test_var")
        
        try:
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    self.env.delete(key, "temp_test_cleanup")
                else:
                    self.env.set(key, original_value, "temp_test_restore")

    # === UNIFIED CONFIGURATION INTERFACE TESTS ===
    
    def test_get_config_returns_valid_app_config(self):
        """
        Test get_config() returns valid AppConfig for golden path user flow.
        
        BVJ: This is the primary configuration access point used throughout
        the system. Failure here breaks the entire golden path user flow.
        """
        # Execute configuration loading
        config = get_config()
        
        # Validate return type and core structure
        self.assertIsInstance(config, AppConfig, "get_config() must return AppConfig instance")
        self.assertTrue(hasattr(config, 'environment'), "Config missing environment attribute")
        self.assertTrue(hasattr(config, 'app_name'), "Config missing app_name attribute")
        self.assertTrue(hasattr(config, 'database_url'), "Config missing database_url attribute")
        self.assertTrue(hasattr(config, 'secret_key'), "Config missing secret_key attribute")
        
        # Validate critical business values
        self.assertEqual(config.app_name, "netra", "App name must be 'netra' for proper service identification")
        self.assertIsNotNone(config.secret_key, "Secret key is required for authentication")
        self.assertGreaterEqual(len(config.secret_key), 16, "Secret key must be at least 16 characters for security")
        
        # Validate environment-specific configuration
        if config.environment == "testing":
            self.assertIsNotNone(config.database_url, "Database URL required for test environment")
        
        print(f"✓ Configuration loaded successfully for environment: {config.environment}")
    
    def test_get_config_environment_specific_loading(self):
        """
        Test get_config() loads correct configuration for each environment.
        
        BVJ: Environment-specific configuration is critical for golden path
        user flow stability across TEST/DEV/STAGING/PROD environments.
        """
        test_environments = [
            ('development', DevelopmentConfig),
            ('staging', StagingConfig), 
            ('production', ProductionConfig),
            ('testing', NetraTestingConfig)
        ]
        
        for env_name, expected_config_class in test_environments:
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    # Clear cache to force reload
                    if hasattr(config_manager, '_config_cache'):
                        config_manager._config_cache = None
                    
                    # Load environment-specific configuration
                    config = get_config()
                    
                    # Validate environment-specific behavior
                    self.assertIsInstance(config, AppConfig, 
                                        f"Config for {env_name} must be AppConfig instance")
                    self.assertEqual(config.environment, env_name,
                                   f"Config environment must match {env_name}")
                    
                    # Validate environment-specific requirements
                    if env_name == "production":
                        self.assertGreaterEqual(len(config.secret_key), 32,
                                              "Production secret key must be at least 32 characters")
                    elif env_name == "testing":
                        # Testing environment should have test credentials available
                        self.assertIsNotNone(config.secret_key, "Testing environment must have secret key")
                    
                    print(f"✓ Environment-specific configuration validated for: {env_name}")
    
    def test_get_config_caching_behavior(self):
        """
        Test get_config() caching behavior for performance.
        
        BVJ: Caching is critical for runtime performance to prevent
        configuration loading delays during user interactions.
        """
        # First call to populate cache
        config1 = get_config()
        
        # Second call should return cached instance
        config2 = get_config()
        
        # Validate caching works
        self.assertIs(config1, config2, "get_config() should return cached instance for performance")
        
        # Measure cache performance
        start_time = time.time()
        for _ in range(100):
            cached_config = get_config()
            self.assertIs(cached_config, config1, "Cache should remain consistent")
        cache_time = time.time() - start_time
        
        # Cache performance requirement
        self.assertLess(cache_time, 0.1, "100 cached calls should complete in under 100ms")
        print(f"✓ Configuration caching validated - 100 calls in {cache_time:.3f}s")
    
    def test_reload_config_force_reload(self):
        """
        Test reload_config() with force flag for configuration updates.
        
        BVJ: Force reload capability is critical for deployment scenarios
        where configuration must be updated without service restart.
        """
        # Get initial configuration
        initial_config = get_config()
        initial_id = id(initial_config)
        
        # Force reload configuration
        reload_config(force=True)
        
        # Get new configuration
        new_config = get_config()
        new_id = id(new_config)
        
        # Validate reload behavior
        self.assertNotEqual(initial_id, new_id, "Force reload should create new config instance")
        self.assertIsInstance(new_config, AppConfig, "Reloaded config should be valid AppConfig")
        self.assertEqual(new_config.app_name, "netra", "Reloaded config should maintain app_name")
        
        print("✓ Force reload configuration validated")
    
    def test_validate_configuration_success_scenarios(self):
        """
        Test validate_configuration() returns success for valid configurations.
        
        BVJ: Configuration validation prevents deployment of invalid
        configurations that could break the golden path user flow.
        """
        # Execute configuration validation
        is_valid, errors = validate_configuration()
        
        # Validate response format
        self.assertIsInstance(is_valid, bool, "Validation should return boolean result")
        self.assertIsInstance(errors, list, "Validation should return list of errors")
        
        # In test environment with proper setup, validation should succeed
        if not is_valid:
            # If validation fails, provide detailed error information
            error_details = "\n".join(str(error) for error in errors)
            self.fail(f"Configuration validation failed with errors:\n{error_details}")
        
        print("✓ Configuration validation passed successfully")
    
    # === UNIFIED CONFIG MANAGER TESTS ===
    
    def test_unified_config_manager_initialization(self):
        """
        Test UnifiedConfigManager initialization and basic functionality.
        
        BVJ: UnifiedConfigManager is the SSOT for configuration management.
        Proper initialization is critical for all configuration operations.
        """
        # Test manager is properly initialized
        self.assertIsInstance(config_manager, UnifiedConfigManager,
                            "config_manager should be UnifiedConfigManager instance")
        
        # Test manager methods are available
        self.assertTrue(hasattr(config_manager, 'get_config'), "Manager should have get_config method")
        self.assertTrue(hasattr(config_manager, 'reload_config'), "Manager should have reload_config method")
        self.assertTrue(hasattr(config_manager, 'validate_config_integrity'), "Manager should have validate_config_integrity method")
        
        # Test manager can provide configuration
        config = config_manager.get_config()
        self.assertIsInstance(config, AppConfig, "Manager should provide valid AppConfig")
        
        print("✓ UnifiedConfigManager initialization validated")
    
    def test_unified_config_manager_environment_detection(self):
        """
        Test UnifiedConfigManager environment detection accuracy.
        
        BVJ: Accurate environment detection is critical for loading
        the correct configuration for each deployment environment.
        """
        test_environments = ['development', 'staging', 'production', 'testing']
        
        for env_name in test_environments:
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    # Clear cache to force environment re-detection
                    config_manager._environment = None
                    if hasattr(config_manager, '_config_cache'):
                        config_manager._config_cache = None
                    
                    # Test environment detection
                    detected_env = config_manager._get_environment()
                    self.assertEqual(detected_env, env_name,
                                   f"Manager should detect {env_name} environment correctly")
                    
                    # Test environment-specific config creation
                    config = config_manager.get_config()
                    self.assertEqual(config.environment, env_name,
                                   f"Config should match detected environment {env_name}")
                    
                    print(f"✓ Environment detection validated for: {env_name}")
    
    def test_unified_config_manager_test_environment_handling(self):
        """
        Test UnifiedConfigManager handling of test environment specifics.
        
        BVJ: Test environment requires special handling to prevent
        configuration caching issues that could affect test reliability.
        """
        with self.temp_env_vars(ENVIRONMENT='testing', TESTING='true'):
            # Clear cache
            config_manager._environment = None
            if hasattr(config_manager, '_config_cache'):
                config_manager._config_cache = None
            
            # Get configuration in test environment
            config = config_manager.get_config()
            
            # Test environment should not cache configuration
            self.assertIsInstance(config, AppConfig, "Test config should be valid AppConfig")
            self.assertEqual(config.environment, "testing", "Should detect testing environment")
            
            # Get configuration again - should create new instance in test env
            config2 = config_manager.get_config()
            self.assertIsInstance(config2, AppConfig, "Second test config should be valid")
            
            print("✓ Test environment handling validated")
    
    def test_unified_config_manager_validation_integration(self):
        """
        Test UnifiedConfigManager integration with configuration validation.
        
        BVJ: Validation integration ensures invalid configurations
        are detected before they can affect system stability.
        """
        # Test validation integration
        is_valid = config_manager.validate_config_integrity()
        self.assertIsInstance(is_valid, bool, "Validation should return boolean result")
        
        # Test validation with proper configuration
        config = config_manager.get_config()
        validation_result = config_manager._validator.validate_complete_config(config)
        
        self.assertTrue(hasattr(validation_result, 'is_valid'), "Validation result should have is_valid attribute")
        self.assertTrue(hasattr(validation_result, 'errors'), "Validation result should have errors attribute")
        
        print(f"✓ Configuration validation integration validated - valid: {validation_result.is_valid}")
    
    # === ENVIRONMENT DETECTION TESTS ===
    
    def test_environment_detection_functions(self):
        """
        Test environment detection utility functions.
        
        BVJ: Environment detection functions are used throughout the system
        to make environment-specific decisions for golden path user flow.
        """
        test_cases = [
            ('development', True, False, False, False),  # is_dev, is_prod, is_staging, is_test
            ('production', False, True, False, False),
            ('staging', False, False, True, False),
            ('testing', False, False, False, True)
        ]
        
        for env_name, expected_dev, expected_prod, expected_staging, expected_test in test_cases:
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    # Clear environment cache
                    config_manager._environment = None
                    
                    # Test environment detection functions
                    self.assertEqual(get_environment(), env_name, f"get_environment() should return {env_name}")
                    self.assertEqual(is_development(), expected_dev, f"is_development() incorrect for {env_name}")
                    self.assertEqual(is_production(), expected_prod, f"is_production() incorrect for {env_name}")
                    self.assertEqual(is_testing(), expected_test, f"is_testing() incorrect for {env_name}")
                    
                    print(f"✓ Environment detection functions validated for: {env_name}")
    
    # === THREAD SAFETY TESTS ===
    
    def test_configuration_thread_safety(self):
        """
        Test configuration loading is thread-safe for concurrent access.
        
        BVJ: Thread safety is critical in production environments where
        multiple concurrent requests access configuration simultaneously.
        """
        results = []
        errors = []
        
        def config_worker():
            """Worker function for thread safety test."""
            try:
                config = get_config()
                results.append(config)
                return config
            except Exception as e:
                errors.append(e)
                raise
        
        # Execute concurrent configuration access
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(config_worker) for _ in range(20)]
            completed_configs = []
            
            for future in as_completed(futures):
                try:
                    config = future.result(timeout=5.0)
                    completed_configs.append(config)
                except Exception as e:
                    errors.append(e)
        
        # Validate thread safety
        self.assertEqual(len(errors), 0, f"Thread safety test should not have errors: {errors}")
        self.assertEqual(len(completed_configs), 20, f"Should complete all 20 operations")
        
        # All configs should be valid
        for i, config in enumerate(completed_configs):
            self.assertIsInstance(config, AppConfig, f"Config {i} should be valid AppConfig")
            self.assertEqual(config.app_name, "netra", f"Config {i} should have correct app_name")
        
        print("✓ Configuration thread safety validated")
    
    def test_concurrent_reload_operations(self):
        """
        Test concurrent reload operations don't cause race conditions.
        
        BVJ: Concurrent reload safety is critical during deployment scenarios
        where configuration updates happen while system is serving requests.
        """
        results = {'configs': [], 'errors': []}
        
        def config_accessor():
            """Worker that accesses configuration."""
            try:
                for _ in range(5):
                    config = get_config()
                    results['configs'].append(config)
                    time.sleep(0.01)
            except Exception as e:
                results['errors'].append(e)
        
        def config_reloader():
            """Worker that reloads configuration."""
            try:
                for _ in range(2):
                    time.sleep(0.05)
                    reload_config(force=True)
            except Exception as e:
                results['errors'].append(e)
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            futures.extend([executor.submit(config_accessor) for _ in range(2)])
            futures.append(executor.submit(config_reloader))
            
            for future in as_completed(futures):
                future.result(timeout=10.0)
        
        # Validate results
        self.assertEqual(len(results['errors']), 0, f"Concurrent operations should not cause errors: {results['errors']}")
        self.assertGreater(len(results['configs']), 0, "Should have accessed configurations successfully")
        
        # All configs should be valid
        for config in results['configs']:
            self.assertIsInstance(config, AppConfig, "All accessed configs should be valid")
        
        print("✓ Concurrent reload operations validated")
    
    # === ERROR HANDLING TESTS ===
    
    @patch('netra_backend.app.core.configuration.base.config_manager')
    def test_get_config_error_propagation(self, mock_config_manager):
        """
        Test get_config() properly propagates configuration errors.
        
        BVJ: Proper error propagation is critical for diagnosing
        configuration issues that could break golden path user flow.
        """
        # Configure mock to raise configuration error
        mock_config_manager.get_config.side_effect = RuntimeError("Configuration loading failed")
        
        # Test error propagation
        with self.assertRaises(RuntimeError) as context:
            get_config()
        
        self.assertIn("Configuration loading failed", str(context.exception))
        print("✓ Configuration error propagation validated")
    
    @patch('netra_backend.app.core.configuration.base.config_manager')
    def test_validate_configuration_error_handling(self, mock_config_manager):
        """
        Test validate_configuration() handles validation errors gracefully.
        
        BVJ: Graceful error handling ensures validation failures provide
        actionable information for fixing configuration issues.
        """
        # Configure mock to raise validation error
        mock_config_manager.validate_config_integrity.side_effect = Exception("Validation failed")
        
        # Test error handling
        is_valid, errors = validate_configuration()
        
        self.assertFalse(is_valid, "Should return False when validation raises exception")
        self.assertIsInstance(errors, list, "Should return list of errors")
        self.assertEqual(len(errors), 1, "Should contain exactly one error")
        self.assertIn("Validation failed", str(errors[0]))
        
        print("✓ Configuration validation error handling validated")
    
    # === PERFORMANCE TESTS ===
    
    def test_configuration_loading_performance(self):
        """
        Test configuration loading meets performance requirements.
        
        BVJ: Configuration loading performance is critical for system
        startup time and request latency in production environments.
        """
        # Test initial configuration loading performance
        start_time = time.time()
        config = get_config()
        load_time = time.time() - start_time
        
        # Performance requirement for initial load
        self.assertLess(load_time, 1.0, "Configuration loading should complete in under 1 second")
        
        # Test cached configuration access performance
        cache_start = time.time()
        for _ in range(100):
            cached_config = get_config()
            self.assertIs(cached_config, config, "Should return cached instance")
        cache_time = time.time() - cache_start
        
        # Performance requirement for cached access
        self.assertLess(cache_time, 0.1, "100 cached configuration accesses should complete in under 100ms")
        
        print(f"✓ Configuration performance validated - load: {load_time:.3f}s, cache: {cache_time:.3f}s")
    
    def test_validation_performance(self):
        """
        Test configuration validation meets performance requirements.
        
        BVJ: Validation performance is critical for deployment speed
        and system startup time in production environments.
        """
        # Test validation performance
        start_time = time.time()
        is_valid, errors = validate_configuration()
        validation_time = time.time() - start_time
        
        # Performance requirement for validation
        self.assertLess(validation_time, 0.5, "Configuration validation should complete in under 500ms")
        
        print(f"✓ Configuration validation performance validated - {validation_time:.3f}s")
    
    # === INTEGRATION TESTS ===
    
    def test_configuration_environment_integration(self):
        """
        Test configuration properly integrates with IsolatedEnvironment.
        
        BVJ: Environment integration is critical for environment variable
        access patterns that support golden path user flow across environments.
        """
        # Test environment variable integration
        with self.temp_env_vars(TEST_CONFIG_VALUE="test_value", CUSTOM_ENV_VAR="custom_value"):
            config = get_config()
            
            # Verify configuration is accessible
            self.assertIsInstance(config, AppConfig, "Config should be accessible with env vars")
            
            # Test environment variable access through isolated environment
            test_value = self.env.get("TEST_CONFIG_VALUE")
            self.assertEqual(test_value, "test_value", "Environment variables should be accessible")
            
            custom_value = self.env.get("CUSTOM_ENV_VAR")
            self.assertEqual(custom_value, "custom_value", "Custom environment variables should be accessible")
        
        print("✓ Configuration environment integration validated")
    
    def test_configuration_schema_validation(self):
        """
        Test configuration schema validation for all environment types.
        
        BVJ: Schema validation ensures configuration consistency across
        environments, preventing deployment issues that break user flows.
        """
        schema_test_cases = [
            ('development', DevelopmentConfig),
            ('staging', StagingConfig),
            ('production', ProductionConfig),
            ('testing', NetraTestingConfig)
        ]
        
        for env_name, config_class in schema_test_cases:
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    # Clear cache for clean test
                    config_manager._environment = None
                    if hasattr(config_manager, '_config_cache'):
                        config_manager._config_cache = None
                    
                    # Get environment-specific configuration
                    config = get_config()
                    
                    # Validate schema compliance
                    self.assertIsInstance(config, AppConfig, f"{env_name} config should be AppConfig")
                    self.assertEqual(config.environment, env_name, f"Environment should match {env_name}")
                    
                    # Validate required fields are present
                    required_fields = ['app_name', 'environment', 'secret_key', 'algorithm', 'log_level']
                    for field in required_fields:
                        self.assertTrue(hasattr(config, field), f"{env_name} config missing required field: {field}")
                        field_value = getattr(config, field)
                        self.assertIsNotNone(field_value, f"{env_name} config {field} should not be None")
                    
                    print(f"✓ Configuration schema validated for: {env_name}")
    
    # === BUSINESS VALUE VALIDATION ===
    
    def test_golden_path_configuration_requirements(self):
        """
        Test configuration meets golden path user flow requirements.
        
        BVJ: Golden path requirements ensure users can successfully
        login → get AI responses without configuration-related failures.
        """
        config = get_config()
        
        # Golden path requirement: App identification
        self.assertEqual(config.app_name, "netra", "App name required for service identification")
        
        # Golden path requirement: Security configuration
        self.assertIsNotNone(config.secret_key, "Secret key required for authentication")
        self.assertGreaterEqual(len(config.secret_key), 16, "Secret key must meet minimum length requirement")
        
        # Golden path requirement: Database connectivity (if configured)
        if config.database_url:
            self.assertIsInstance(config.database_url, str, "Database URL must be string")
            self.assertGreater(len(config.database_url), 0, "Database URL must not be empty")
        
        # Golden path requirement: JWT configuration (if configured)
        if config.jwt_secret_key:
            self.assertIsInstance(config.jwt_secret_key, str, "JWT secret must be string")
            self.assertGreaterEqual(len(config.jwt_secret_key), 16, "JWT secret must meet minimum length")
        
        # Golden path requirement: Logging configuration
        self.assertIsNotNone(config.log_level, "Log level required for system monitoring")
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.assertIn(config.log_level, valid_log_levels, f"Log level must be valid: {valid_log_levels}")
        
        print("✓ Golden path configuration requirements validated")
    
    def test_business_value_metrics_comprehensive(self):
        """
        Test and record comprehensive business value metrics.
        
        BVJ: Business value metrics demonstrate the configuration system's
        contribution to system reliability and golden path user flow stability.
        """
        metrics = {}
        
        # Metric 1: Configuration loading reliability
        load_attempts = 10
        successful_loads = 0
        total_load_time = 0
        
        for _ in range(load_attempts):
            try:
                start_time = time.time()
                config = get_config()
                load_time = time.time() - start_time
                total_load_time += load_time
                
                if isinstance(config, AppConfig) and config.app_name == "netra":
                    successful_loads += 1
            except Exception:
                pass
        
        load_reliability = successful_loads / load_attempts
        avg_load_time = total_load_time / successful_loads if successful_loads > 0 else 0
        
        # Metric 2: Validation reliability
        validation_attempts = 5
        successful_validations = 0
        total_validation_time = 0
        
        for _ in range(validation_attempts):
            try:
                start_time = time.time()
                is_valid, errors = validate_configuration()
                validation_time = time.time() - start_time
                total_validation_time += validation_time
                
                if isinstance(is_valid, bool) and isinstance(errors, list):
                    successful_validations += 1
            except Exception:
                pass
        
        validation_reliability = successful_validations / validation_attempts
        avg_validation_time = total_validation_time / successful_validations if successful_validations > 0 else 0
        
        # Metric 3: Cache effectiveness
        cache_hits = 0
        cache_attempts = 100
        initial_config = get_config()
        
        for _ in range(cache_attempts):
            cached_config = get_config()
            if cached_config is initial_config:
                cache_hits += 1
        
        cache_hit_rate = cache_hits / cache_attempts
        
        # Business value assertions
        self.assertGreaterEqual(load_reliability, 0.95, "Configuration loading should be 95%+ reliable")
        self.assertGreaterEqual(validation_reliability, 0.95, "Configuration validation should be 95%+ reliable")  
        self.assertGreaterEqual(cache_hit_rate, 0.90, "Configuration cache should be 90%+ effective")
        self.assertLess(avg_load_time, 0.5, "Average load time should be under 500ms")
        self.assertLess(avg_validation_time, 0.2, "Average validation time should be under 200ms")
        
        # Record metrics for business value reporting
        metrics = {
            'configuration_load_reliability': f"{load_reliability:.1%}",
            'configuration_validation_reliability': f"{validation_reliability:.1%}",
            'configuration_cache_hit_rate': f"{cache_hit_rate:.1%}",
            'avg_configuration_load_time': f"{avg_load_time:.3f}s",
            'avg_validation_time': f"{avg_validation_time:.3f}s"
        }
        
        print(f"✓ Business value metrics validated: {metrics}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])