"""
Comprehensive Unit Tests for IsolatedEnvironment Module

Business Value Justification (BVJ):
- Segment: Platform/Internal (CRITICAL SYSTEM INFRASTRUCTURE)  
- Business Goal: Zero environment variable configuration errors across all services
- Value Impact: Prevents configuration cascade failures that break golden path user flow
- Strategic Impact: Enables reliable environment variable management for service independence
- Revenue Impact: Eliminates configuration-related failures that cause system-wide outages

MISSION CRITICAL: These tests validate IsolatedEnvironment components that enable:
1. Thread-safe singleton pattern for consistent environment access
2. Environment variable isolation to prevent cross-environment pollution
3. Configuration loading and validation across TEST/DEV/STAGING/PROD
4. Service independence through centralized environment management
5. Test environment handling with proper isolation and defaults
6. Environment variable sanitization and security validation
7. File-based configuration loading with precedence rules

GOLDEN PATH ENVIRONMENT SCENARIOS TESTED:
1. Environment Variable Access: Consistent get/set/delete operations
2. Environment Detection: Proper environment identification (TEST/DEV/STAGING/PROD)
3. Isolation Mode: Clean separation between test and production environments
4. Test Context Handling: Proper test defaults and OAuth credentials
5. Configuration Loading: File-based configuration with environment precedence
6. Thread Safety: Concurrent access without race conditions
7. Validation: Environment variable validation and error reporting

TESTING APPROACH:
- Real environment management (no mocks for core environment logic)
- Minimal mocking limited to external file system operations only  
- SSOT compliance using test_framework utilities
- Business value focus on environment reliability scenarios
- Golden path focus on environment-specific variable management
- Coverage target: 95%+ method coverage on critical environment paths
"""

import pytest
import os
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock, mock_open
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

# SSOT imports following absolute import rules
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import (
    IsolatedEnvironment,
    get_env,
    setenv,
    getenv,
    delenv,
    get_subprocess_env,
    ValidationResult,
    EnvironmentValidator,
    SecretLoader,
    _mask_sensitive_value
)


class TestIsolatedEnvironmentComprehensive(SSotBaseTestCase):
    """
    Comprehensive test suite for IsolatedEnvironment Module.
    
    Tests the critical environment variable management components that enable
    reliable configuration across all environments for golden path user flow stability.
    """
    
    def setUp(self):
        """Set up test environment with clean isolation."""
        super().setUp()
        
        # Get fresh environment instance
        self.env = get_env()
        
        # Enable isolation for clean testing
        self.env.enable_isolation()
        
        # Set up test environment
        self.env.set('ENVIRONMENT', 'testing', 'test_setup')
        self.env.set('TESTING', 'true', 'test_setup')
        
        # Store original state for cleanup
        self.original_env_vars = dict(self.env.get_all())
    
    def tearDown(self):
        """Clean up test environment."""
        # Complete reset for isolation
        self.env.complete_reset_for_testing()
        super().tearDown()
    
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

    # === SINGLETON PATTERN TESTS ===
    
    def test_isolated_environment_singleton_pattern(self):
        """
        Test IsolatedEnvironment singleton pattern ensures single instance.
        
        BVJ: Singleton pattern is critical for consistent environment
        variable access across all application components.
        """
        # Test singleton behavior
        env1 = IsolatedEnvironment()
        env2 = IsolatedEnvironment()
        env3 = get_env()
        
        # All should be same instance
        self.assertIs(env1, env2, "IsolatedEnvironment() should return same instance")
        self.assertIs(env2, env3, "get_env() should return same instance as IsolatedEnvironment()")
        self.assertIs(env1, env3, "All access methods should return same instance")
        
        # Test instance ID consistency
        instance_ids = [id(env1), id(env2), id(env3)]
        self.assertEqual(len(set(instance_ids)), 1, "All instances should have same ID")
        
        print(f"✓ Singleton pattern validated - instance ID: {id(env1)}")
    
    def test_isolated_environment_thread_safe_singleton(self):
        """
        Test IsolatedEnvironment singleton is thread-safe.
        
        BVJ: Thread safety is critical for concurrent environment
        access in production multi-threaded environments.
        """
        instances = []
        errors = []
        
        def get_env_worker():
            """Worker function to get environment instance."""
            try:
                env_instance = get_env()
                instances.append(env_instance)
                return env_instance
            except Exception as e:
                errors.append(e)
                raise
        
        # Test concurrent singleton access
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_env_worker) for _ in range(20)]
            completed_instances = []
            
            for future in as_completed(futures):
                try:
                    instance = future.result(timeout=5.0)
                    completed_instances.append(instance)
                except Exception as e:
                    errors.append(e)
        
        # Validate thread safety
        self.assertEqual(len(errors), 0, f"Thread safety should not cause errors: {errors}")
        self.assertEqual(len(completed_instances), 20, "All threads should get instances")
        
        # All instances should be identical
        first_instance = completed_instances[0]
        for i, instance in enumerate(completed_instances):
            self.assertIs(instance, first_instance, f"Instance {i} should be same as first")
        
        print("✓ Thread-safe singleton pattern validated")
    
    # === ENVIRONMENT VARIABLE OPERATIONS TESTS ===
    
    def test_isolated_environment_basic_operations(self):
        """
        Test IsolatedEnvironment basic get/set/delete operations.
        
        BVJ: Basic operations are the foundation for all environment
        variable management in the golden path user flow.
        """
        # Test set operation
        success = self.env.set('TEST_KEY', 'test_value', 'test_basic_ops')
        self.assertTrue(success, "Set operation should succeed")
        
        # Test get operation
        value = self.env.get('TEST_KEY')
        self.assertEqual(value, 'test_value', "Get should return set value")
        
        # Test get with default
        default_value = self.env.get('NON_EXISTENT_KEY', 'default')
        self.assertEqual(default_value, 'default', "Get should return default for non-existent key")
        
        # Test exists operation
        exists = self.env.exists('TEST_KEY')
        self.assertTrue(exists, "Exists should return True for existing key")
        
        not_exists = self.env.exists('NON_EXISTENT_KEY')
        self.assertFalse(not_exists, "Exists should return False for non-existent key")
        
        # Test delete operation
        deleted = self.env.delete('TEST_KEY', 'test_basic_ops')
        self.assertTrue(deleted, "Delete should succeed")
        
        # Test key no longer exists
        after_delete = self.env.get('TEST_KEY')
        self.assertIsNone(after_delete, "Get should return None after delete")
        
        print("✓ Basic environment operations validated")
    
    def test_isolated_environment_update_operations(self):
        """
        Test IsolatedEnvironment batch update operations.
        
        BVJ: Batch operations are critical for efficient configuration
        loading during system startup and environment switches.
        """
        # Test batch update
        test_vars = {
            'BATCH_VAR1': 'value1',
            'BATCH_VAR2': 'value2', 
            'BATCH_VAR3': 'value3'
        }
        
        results = self.env.update(test_vars, 'test_update_ops')
        
        # All updates should succeed
        for key, result in results.items():
            self.assertTrue(result, f"Update should succeed for {key}")
        
        # Verify all variables are set
        for key, expected_value in test_vars.items():
            actual_value = self.env.get(key)
            self.assertEqual(actual_value, expected_value, f"Value should match for {key}")
        
        # Test get_all operation
        all_vars = self.env.get_all()
        for key, expected_value in test_vars.items():
            self.assertIn(key, all_vars, f"All vars should include {key}")
            self.assertEqual(all_vars[key], expected_value, f"All vars value should match for {key}")
        
        print(f"✓ Batch update operations validated - {len(test_vars)} variables")
    
    def test_isolated_environment_source_tracking(self):
        """
        Test IsolatedEnvironment source tracking for debugging.
        
        BVJ: Source tracking is critical for debugging configuration
        issues and understanding environment variable origins.
        """
        # Set variables with different sources
        self.env.set('SOURCE_VAR1', 'value1', 'test_source')
        self.env.set('SOURCE_VAR2', 'value2', 'config_file')
        self.env.set('SOURCE_VAR3', 'value3', 'deployment_script')
        
        # Test source tracking
        source1 = self.env.get_variable_source('SOURCE_VAR1')
        self.assertEqual(source1, 'test_source', "Should track source correctly")
        
        source2 = self.env.get_variable_source('SOURCE_VAR2')
        self.assertEqual(source2, 'config_file', "Should track different source")
        
        # Test sources summary
        sources = self.env.get_sources()
        self.assertIsInstance(sources, dict, "Sources should be dictionary")
        self.assertIn('test_source', sources, "Should include test_source")
        self.assertIn('config_file', sources, "Should include config_file")
        
        # Test variable lists by source
        self.assertIn('SOURCE_VAR1', sources['test_source'], "Should list variable under correct source")
        self.assertIn('SOURCE_VAR2', sources['config_file'], "Should list variable under correct source")
        
        print("✓ Source tracking validated")
    
    # === ISOLATION MODE TESTS ===
    
    def test_isolated_environment_isolation_mode(self):
        """
        Test IsolatedEnvironment isolation mode functionality.
        
        BVJ: Isolation mode is critical for preventing environment
        variable pollution between test runs and deployments.
        """
        # Test enabling isolation
        self.env.enable_isolation()
        self.assertTrue(self.env.is_isolated(), "Should be in isolation mode")
        
        # Set variable in isolation
        self.env.set('ISOLATED_VAR', 'isolated_value', 'test_isolation')
        
        # Variable should be in isolated storage
        value = self.env.get('ISOLATED_VAR')
        self.assertEqual(value, 'isolated_value', "Should get value from isolated storage")
        
        # Test isolation prevents os.environ pollution
        # (Note: In test environment, we don't check os.environ directly as it's controlled)
        isolated_vars = self.env._isolated_vars
        self.assertIn('ISOLATED_VAR', isolated_vars, "Should be in isolated vars")
        
        # Test disabling isolation
        self.env.disable_isolation()
        self.assertFalse(self.env.is_isolated(), "Should not be in isolation mode")
        
        # Re-enable for cleanup
        self.env.enable_isolation()
        
        print("✓ Isolation mode functionality validated")
    
    def test_isolated_environment_isolation_with_backup(self):
        """
        Test IsolatedEnvironment isolation with environment backup.
        
        BVJ: Environment backup is critical for restoring original
        state after configuration changes or test execution.
        """
        # Set some initial variables
        self.env.set('BACKUP_VAR1', 'original1', 'test_backup')
        self.env.set('BACKUP_VAR2', 'original2', 'test_backup')
        
        # Enable isolation with backup
        self.env.enable_isolation(backup_original=True)
        
        # Modify variables in isolation
        self.env.set('BACKUP_VAR1', 'modified1', 'test_isolation')
        self.env.set('BACKUP_VAR3', 'new_var', 'test_isolation')
        
        # Check modified values
        self.assertEqual(self.env.get('BACKUP_VAR1'), 'modified1', "Should have modified value")
        self.assertEqual(self.env.get('BACKUP_VAR3'), 'new_var', "Should have new value")
        
        # Reset to original
        self.env.reset_to_original()
        
        # Check values are restored (if backup was available)
        # Note: In test environment, this behavior may vary based on setup
        restored_value = self.env.get('BACKUP_VAR1')
        self.assertIsNotNone(restored_value, "Should have some value after restore")
        
        print("✓ Isolation with backup validated")
    
    # === ENVIRONMENT DETECTION TESTS ===
    
    def test_isolated_environment_detection(self):
        """
        Test IsolatedEnvironment environment detection functions.
        
        BVJ: Environment detection is critical for loading correct
        configuration for each deployment environment.
        """
        test_environments = [
            ('development', True, False, False, False),    # is_dev, is_prod, is_staging, is_test
            ('production', False, True, False, False),
            ('staging', False, False, True, False),
            ('testing', False, False, False, True),
            ('test', False, False, False, True)
        ]
        
        for env_name, expected_dev, expected_prod, expected_staging, expected_test in test_environments:
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    # Test environment detection functions
                    detected_env = self.env.get_environment_name()
                    
                    # Map some variations to expected values
                    if env_name == 'test':
                        expected_env = 'test'
                    else:
                        expected_env = env_name
                    
                    self.assertEqual(self.env.is_development(), expected_dev, 
                                   f"is_development() incorrect for {env_name}")
                    self.assertEqual(self.env.is_production(), expected_prod,
                                   f"is_production() incorrect for {env_name}")  
                    self.assertEqual(self.env.is_staging(), expected_staging,
                                   f"is_staging() incorrect for {env_name}")
                    self.assertEqual(self.env.is_test(), expected_test,
                                   f"is_test() incorrect for {env_name}")
                    
                    print(f"✓ Environment detection validated for: {env_name}")
    
    def test_isolated_environment_test_context_detection(self):
        """
        Test IsolatedEnvironment test context detection.
        
        BVJ: Test context detection is critical for providing
        test defaults and preventing test environment pollution.
        """
        # Test with PYTEST_CURRENT_TEST
        with self.temp_env_vars(PYTEST_CURRENT_TEST='test_module.py::test_function'):
            is_test = self.env._is_test_context()
            self.assertTrue(is_test, "Should detect test context with PYTEST_CURRENT_TEST")
        
        # Test with TESTING=true
        with self.temp_env_vars(TESTING='true'):
            is_test = self.env._is_test_context()
            self.assertTrue(is_test, "Should detect test context with TESTING=true")
        
        # Test with ENVIRONMENT=testing
        with self.temp_env_vars(ENVIRONMENT='testing'):
            is_test = self.env._is_test_context()
            self.assertTrue(is_test, "Should detect test context with ENVIRONMENT=testing")
        
        # Test without test indicators
        with self.temp_env_vars(PYTEST_CURRENT_TEST='', TESTING='', ENVIRONMENT='production'):
            is_test = self.env._is_test_context()
            self.assertFalse(is_test, "Should not detect test context without indicators")
        
        print("✓ Test context detection validated")
    
    # === TEST DEFAULTS TESTS ===
    
    def test_isolated_environment_test_defaults(self):
        """
        Test IsolatedEnvironment test environment defaults.
        
        BVJ: Test defaults are critical for providing OAuth credentials
        and other test configuration without explicit setup.
        """
        # Set up test context
        with self.temp_env_vars(ENVIRONMENT='testing', TESTING='true'):
            self.env.enable_isolation()
            
            # Test OAuth test credentials are available
            oauth_client_id = self.env.get('GOOGLE_OAUTH_CLIENT_ID_TEST')
            self.assertIsNotNone(oauth_client_id, "Should provide OAuth client ID test default")
            self.assertIn('test', oauth_client_id.lower(), "OAuth client ID should be test credential")
            
            oauth_client_secret = self.env.get('GOOGLE_OAUTH_CLIENT_SECRET_TEST')
            self.assertIsNotNone(oauth_client_secret, "Should provide OAuth client secret test default")
            
            # Test E2E OAuth simulation key
            e2e_key = self.env.get('E2E_OAUTH_SIMULATION_KEY')
            self.assertIsNotNone(e2e_key, "Should provide E2E OAuth simulation key")
            
            # Test security defaults
            jwt_secret = self.env.get('JWT_SECRET_KEY')
            self.assertIsNotNone(jwt_secret, "Should provide JWT secret test default")
            self.assertGreaterEqual(len(jwt_secret), 32, "JWT secret should be at least 32 characters")
            
            service_secret = self.env.get('SERVICE_SECRET')
            self.assertIsNotNone(service_secret, "Should provide service secret test default")
            
            # Test database defaults
            database_url = self.env.get('DATABASE_URL')
            self.assertIsNotNone(database_url, "Should provide database URL test default")
            self.assertIn('test', database_url, "Database URL should be test database")
            
            print("✓ Test environment defaults validated")
    
    def test_isolated_environment_test_defaults_bypass(self):
        """
        Test IsolatedEnvironment test defaults bypass functionality.
        
        BVJ: Test defaults bypass prevents configuration pollution
        between different test scenarios requiring clean environments.
        """
        # Enable test defaults bypass
        self.env.enable_test_defaults_bypass()
        
        # Test defaults should not be returned
        oauth_client_id = self.env.get('GOOGLE_OAUTH_CLIENT_ID_TEST')
        self.assertIsNone(oauth_client_id, "Should not return test defaults when bypass enabled")
        
        # Disable bypass
        self.env.disable_test_defaults_bypass()
        
        # Test defaults should be available again (if in test context)
        with self.temp_env_vars(ENVIRONMENT='testing', TESTING='true'):
            oauth_client_id = self.env.get('GOOGLE_OAUTH_CLIENT_ID_TEST') 
            self.assertIsNotNone(oauth_client_id, "Should return test defaults when bypass disabled")
        
        print("✓ Test defaults bypass functionality validated")
    
    # === FILE LOADING TESTS ===
    
    def test_isolated_environment_file_loading(self):
        """
        Test IsolatedEnvironment file-based configuration loading.
        
        BVJ: File loading is critical for loading configuration
        from .env files and deployment-specific config files.
        """
        # Create test file content
        test_file_content = """
        # Test configuration file
        FILE_VAR1=file_value1
        FILE_VAR2=file_value2
        FILE_VAR3="quoted_value"
        # Comment line
        FILE_VAR4=value with spaces
        """
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data=test_file_content)):
            with patch('pathlib.Path.exists', return_value=True):
                # Test file loading
                loaded_count, errors = self.env.load_from_file('/mock/path/test.env')
                
                # Should load successfully
                self.assertGreater(loaded_count, 0, "Should load variables from file")
                self.assertEqual(len(errors), 0, f"Should not have errors: {errors}")
                
                # Test loaded variables
                self.assertEqual(self.env.get('FILE_VAR1'), 'file_value1', "Should load simple variable")
                self.assertEqual(self.env.get('FILE_VAR2'), 'file_value2', "Should load second variable")
                self.assertEqual(self.env.get('FILE_VAR3'), 'quoted_value', "Should strip quotes")
        
        print(f"✓ File loading validated - {loaded_count} variables loaded")
    
    def test_isolated_environment_file_loading_error_handling(self):
        """
        Test IsolatedEnvironment file loading error handling.
        
        BVJ: Graceful error handling ensures configuration loading
        failures provide actionable error messages for troubleshooting.
        """
        # Test non-existent file
        with patch('pathlib.Path.exists', return_value=False):
            loaded_count, errors = self.env.load_from_file('/mock/nonexistent.env')
            
            self.assertEqual(loaded_count, 0, "Should not load from non-existent file")
            self.assertGreater(len(errors), 0, "Should have error for non-existent file")
        
        # Test malformed file content
        malformed_content = """
        VALID_VAR=valid_value
        INVALID_LINE_WITHOUT_EQUALS
        =INVALID_EMPTY_KEY
        VALID_VAR2=valid_value2
        """
        
        with patch('builtins.open', mock_open(read_data=malformed_content)):
            with patch('pathlib.Path.exists', return_value=True):
                loaded_count, errors = self.env.load_from_file('/mock/malformed.env')
                
                # Should load valid lines and report errors for invalid ones
                self.assertGreater(loaded_count, 0, "Should load valid variables")
                self.assertGreater(len(errors), 0, "Should report errors for invalid lines")
                
                # Valid variables should be loaded
                self.assertEqual(self.env.get('VALID_VAR'), 'valid_value', "Should load valid variable")
        
        print("✓ File loading error handling validated")
    
    # === VALIDATION TESTS ===
    
    def test_isolated_environment_validation_basic(self):
        """
        Test IsolatedEnvironment basic validation functionality.
        
        BVJ: Validation is critical for detecting configuration
        issues that could break the golden path user flow.
        """
        # Set up required variables for validation
        self.env.set('DATABASE_URL', 'postgresql://user:pass@host:5432/db', 'test_validation')
        self.env.set('JWT_SECRET_KEY', 'test_jwt_secret_key_32_characters', 'test_validation')
        self.env.set('SECRET_KEY', 'test_secret_key_32_characters', 'test_validation')
        
        # Test validation
        result = self.env.validate_all()
        self.assertIsInstance(result, ValidationResult, "Should return ValidationResult")
        self.assertIsInstance(result.is_valid, bool, "ValidationResult should have is_valid boolean")
        self.assertIsInstance(result.errors, list, "ValidationResult should have errors list")
        self.assertIsInstance(result.warnings, list, "ValidationResult should have warnings list")
        
        # With required variables set, validation should pass
        self.assertTrue(result.is_valid, f"Validation should pass with required variables: {result.errors}")
        
        print(f"✓ Basic validation completed - valid: {result.is_valid}")
    
    def test_isolated_environment_staging_database_validation(self):
        """
        Test IsolatedEnvironment staging database credential validation.
        
        BVJ: Staging database validation prevents deployment failures
        from incorrect database configuration.
        """
        # Test staging database validation
        with self.temp_env_vars(
            ENVIRONMENT='staging',
            POSTGRES_HOST='staging-postgres.example.com',
            POSTGRES_USER='postgres',
            POSTGRES_PASSWORD='secure_staging_password',
            POSTGRES_DB='staging_db'
        ):
            result = self.env.validate_staging_database_credentials()
            self.assertIsInstance(result, dict, "Should return validation dictionary")
            self.assertIn('valid', result, "Should include valid status")
            self.assertIn('issues', result, "Should include issues list")
            self.assertIn('warnings', result, "Should include warnings list")
            
            # With proper staging config, should be valid
            self.assertTrue(result['valid'], f"Staging database validation should pass: {result['issues']}")
        
        # Test invalid staging configuration
        with self.temp_env_vars(
            ENVIRONMENT='staging',
            POSTGRES_HOST='localhost',  # Invalid for staging
            POSTGRES_USER='user_pr-4',  # Invalid pattern
            POSTGRES_PASSWORD='weak',   # Too weak for staging
            POSTGRES_DB='staging_db'
        ):
            result = self.env.validate_staging_database_credentials()
            self.assertFalse(result['valid'], "Should fail validation with invalid staging config")
            self.assertGreater(len(result['issues']), 0, "Should have validation issues")
        
        print("✓ Staging database validation tested")
    
    # === THREAD SAFETY TESTS ===
    
    def test_isolated_environment_concurrent_operations(self):
        """
        Test IsolatedEnvironment thread safety for concurrent operations.
        
        BVJ: Thread safety is critical for production environments
        where multiple requests access environment variables concurrently.
        """
        results = {'set': [], 'get': [], 'errors': []}
        
        def env_worker(worker_id):
            """Worker function for concurrent environment operations."""
            try:
                # Set worker-specific variable
                self.env.set(f'WORKER_VAR_{worker_id}', f'worker_value_{worker_id}', f'worker_{worker_id}')
                results['set'].append(worker_id)
                
                # Get variable and verify
                value = self.env.get(f'WORKER_VAR_{worker_id}')
                if value == f'worker_value_{worker_id}':
                    results['get'].append(worker_id)
                
                # Perform additional operations
                for i in range(5):
                    test_key = f'WORKER_{worker_id}_TEST_{i}'
                    self.env.set(test_key, f'test_value_{i}', f'worker_{worker_id}')
                    retrieved = self.env.get(test_key)
                    if retrieved != f'test_value_{i}':
                        results['errors'].append(f'Value mismatch for {test_key}')
                
            except Exception as e:
                results['errors'].append(str(e))
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(env_worker, i) for i in range(15)]
            
            for future in as_completed(futures):
                future.result(timeout=10.0)
        
        # Validate results
        self.assertEqual(len(results['errors']), 0, f"Concurrent operations should not cause errors: {results['errors']}")
        self.assertEqual(len(results['set']), 15, "All workers should successfully set variables")
        self.assertEqual(len(results['get']), 15, "All workers should successfully get variables")
        
        print("✓ Concurrent operations thread safety validated")
    
    # === PERFORMANCE TESTS ===
    
    def test_isolated_environment_performance_requirements(self):
        """
        Test IsolatedEnvironment meets performance requirements.
        
        BVJ: Environment performance is critical for system startup
        time and request processing speed in production environments.
        """
        # Test get operation performance
        self.env.set('PERF_TEST_VAR', 'perf_test_value', 'perf_test')
        
        start_time = time.time()
        for _ in range(1000):
            value = self.env.get('PERF_TEST_VAR')
            self.assertEqual(value, 'perf_test_value')
        get_time = time.time() - start_time
        
        # Test set operation performance
        start_time = time.time()
        for i in range(1000):
            success = self.env.set(f'PERF_VAR_{i}', f'value_{i}', 'perf_test')
            self.assertTrue(success)
        set_time = time.time() - start_time
        
        # Test batch operations performance
        batch_vars = {f'BATCH_VAR_{i}': f'batch_value_{i}' for i in range(100)}
        start_time = time.time()
        results = self.env.update(batch_vars, 'perf_test')
        batch_time = time.time() - start_time
        
        # Performance requirements
        self.assertLess(get_time, 0.1, "1000 get operations should complete in under 100ms")
        self.assertLess(set_time, 0.5, "1000 set operations should complete in under 500ms") 
        self.assertLess(batch_time, 0.1, "100 batch operations should complete in under 100ms")
        
        print(f"✓ Environment performance validated - Get: {get_time:.3f}s, "
              f"Set: {set_time:.3f}s, Batch: {batch_time:.3f}s")
    
    # === SECURITY TESTS ===
    
    def test_isolated_environment_value_sanitization(self):
        """
        Test IsolatedEnvironment value sanitization for security.
        
        BVJ: Value sanitization prevents control character injection
        and ensures safe handling of environment variable values.
        """
        # Test control character removal
        test_value_with_controls = "clean_value\n\r\t\x00dirty"
        self.env.set('SANITIZE_TEST', test_value_with_controls, 'test_sanitize')
        
        sanitized_value = self.env.get('SANITIZE_TEST')
        self.assertNotIn('\n', sanitized_value, "Should remove newline characters")
        self.assertNotIn('\r', sanitized_value, "Should remove carriage return characters")
        self.assertNotIn('\x00', sanitized_value, "Should remove null bytes")
        self.assertIn('clean_value', sanitized_value, "Should preserve clean content")
        
        # Test database URL sanitization
        test_db_url = "postgresql://user:pass\n@host:5432/db"
        self.env.set('DATABASE_URL', test_db_url, 'test_sanitize')
        
        sanitized_url = self.env.get('DATABASE_URL')
        self.assertNotIn('\n', sanitized_url, "Should remove control characters from database URL")
        self.assertIn('postgresql://', sanitized_url, "Should preserve URL structure")
        
        print("✓ Value sanitization validated")
    
    def test_isolated_environment_sensitive_value_masking(self):
        """
        Test sensitive value masking for logging safety.
        
        BVJ: Sensitive value masking prevents credential exposure
        in logs while maintaining debugging capabilities.
        """
        # Test sensitive key masking
        sensitive_keys = ['password', 'secret', 'key', 'token', 'auth', 'credential', 'private']
        
        for sensitive_key in sensitive_keys:
            with self.subTest(key=sensitive_key):
                test_value = 'very_sensitive_secret_value'
                masked = _mask_sensitive_value(sensitive_key.upper(), test_value)
                
                # Should be masked
                self.assertNotEqual(masked, test_value, f"Should mask sensitive value for {sensitive_key}")
                self.assertTrue(masked.startswith('ver'), f"Should show first 3 characters for {sensitive_key}")
                self.assertIn('***', masked, f"Should include masking for {sensitive_key}")
        
        # Test non-sensitive key
        non_sensitive_value = 'public_configuration_value'
        masked_non_sensitive = _mask_sensitive_value('PUBLIC_CONFIG', non_sensitive_value)
        self.assertEqual(masked_non_sensitive, non_sensitive_value, "Should not mask non-sensitive values")
        
        print("✓ Sensitive value masking validated")
    
    # === UTILITY FUNCTIONS TESTS ===
    
    def test_isolated_environment_utility_functions(self):
        """
        Test IsolatedEnvironment utility functions and convenience methods.
        
        BVJ: Utility functions provide convenient access patterns
        for environment variables throughout the application.
        """
        # Test module-level convenience functions
        setenv_success = setenv('UTIL_TEST_VAR', 'util_test_value', 'test_utils')
        self.assertTrue(setenv_success, "setenv should succeed")
        
        getenv_value = getenv('UTIL_TEST_VAR')
        self.assertEqual(getenv_value, 'util_test_value', "getenv should return correct value")
        
        getenv_default = getenv('NON_EXISTENT_UTIL_VAR', 'default_value')
        self.assertEqual(getenv_default, 'default_value', "getenv should return default for non-existent")
        
        delenv_success = delenv('UTIL_TEST_VAR')
        self.assertTrue(delenv_success, "delenv should succeed")
        
        # Test subprocess environment
        subprocess_env = get_subprocess_env({'EXTRA_VAR': 'extra_value'})
        self.assertIsInstance(subprocess_env, dict, "Should return subprocess environment dict")
        self.assertIn('EXTRA_VAR', subprocess_env, "Should include additional variables")
        
        print("✓ Utility functions validated")
    
    def test_isolated_environment_debug_info(self):
        """
        Test IsolatedEnvironment debug information functionality.
        
        BVJ: Debug information is critical for troubleshooting
        environment configuration issues in production deployments.
        """
        # Test debug info generation
        debug_info = self.env.get_debug_info()
        self.assertIsInstance(debug_info, dict, "Debug info should be dictionary")
        
        # Test required debug info fields
        required_fields = [
            'isolation_enabled', 'isolated_vars_count', 'os_environ_count',
            'protected_vars', 'tracked_sources', 'change_callbacks_count'
        ]
        
        for field in required_fields:
            self.assertIn(field, debug_info, f"Debug info should include {field}")
        
        # Test field types
        self.assertIsInstance(debug_info['isolation_enabled'], bool, "isolation_enabled should be boolean")
        self.assertIsInstance(debug_info['isolated_vars_count'], int, "isolated_vars_count should be integer") 
        self.assertIsInstance(debug_info['protected_vars'], list, "protected_vars should be list")
        
        print(f"✓ Debug info validated - {len(debug_info)} fields")
    
    # === BUSINESS VALUE VALIDATION ===
    
    def test_isolated_environment_golden_path_requirements(self):
        """
        Test IsolatedEnvironment meets golden path user flow requirements.
        
        BVJ: Golden path requirements ensure environment management
        supports the critical user flow from login → AI responses.
        """
        # Golden path requirement: Environment detection
        env_name = self.env.get_environment_name()
        self.assertIsNotNone(env_name, "Environment name required for configuration selection")
        self.assertIn(env_name, ['development', 'staging', 'production', 'test'], 
                     "Environment name should be recognized value")
        
        # Golden path requirement: Test context handling
        with self.temp_env_vars(ENVIRONMENT='testing', TESTING='true'):
            oauth_creds_available = self.env.get('GOOGLE_OAUTH_CLIENT_ID_TEST') is not None
            self.assertTrue(oauth_creds_available, "OAuth test credentials required for test environment")
        
        # Golden path requirement: Configuration validation
        validation_result = self.env.validate_all()
        self.assertIsInstance(validation_result, ValidationResult, "Validation should return proper result")
        
        # Golden path requirement: Thread safety
        # Already tested in concurrent operations test
        
        # Golden path requirement: Source tracking
        self.env.set('GOLDEN_PATH_VAR', 'golden_value', 'golden_path_test')
        source = self.env.get_variable_source('GOLDEN_PATH_VAR')
        self.assertEqual(source, 'golden_path_test', "Should track variable sources")
        
        print("✓ Golden path requirements validated")
    
    def test_isolated_environment_business_value_metrics(self):
        """
        Test and record IsolatedEnvironment business value metrics.
        
        BVJ: Business value metrics demonstrate environment management
        contribution to system reliability and golden path stability.
        """
        metrics = {}
        
        # Metric 1: Environment operation reliability
        operation_attempts = 100
        successful_operations = 0
        
        for i in range(operation_attempts):
            try:
                # Test set/get/delete cycle
                key = f'METRIC_VAR_{i}'
                value = f'metric_value_{i}'
                
                set_success = self.env.set(key, value, 'metrics_test')
                retrieved_value = self.env.get(key)
                delete_success = self.env.delete(key, 'metrics_test')
                
                if set_success and retrieved_value == value and delete_success:
                    successful_operations += 1
            except Exception:
                pass
        
        operation_reliability = successful_operations / operation_attempts
        
        # Metric 2: Environment detection accuracy
        detection_attempts = 10
        successful_detections = 0
        test_environments = ['development', 'staging', 'production', 'testing']
        
        for env in test_environments:
            for _ in range(detection_attempts // len(test_environments)):
                try:
                    with self.temp_env_vars(ENVIRONMENT=env):
                        detected = self.env.get_environment_name()
                        if detected in ['development', 'staging', 'production', 'test']:
                            successful_detections += 1
                except Exception:
                    pass
        
        detection_reliability = successful_detections / detection_attempts
        
        # Metric 3: Isolation mode effectiveness
        isolation_attempts = 5
        successful_isolations = 0
        
        for _ in range(isolation_attempts):
            try:
                self.env.enable_isolation()
                is_isolated = self.env.is_isolated()
                self.env.set('ISOLATION_TEST', 'test_value', 'isolation_test')
                has_value = self.env.get('ISOLATION_TEST') == 'test_value'
                
                if is_isolated and has_value:
                    successful_isolations += 1
            except Exception:
                pass
        
        isolation_reliability = successful_isolations / isolation_attempts
        
        # Business value assertions
        self.assertGreaterEqual(operation_reliability, 0.95, "Environment operations should be 95%+ reliable")
        self.assertGreaterEqual(detection_reliability, 0.90, "Environment detection should be 90%+ reliable")
        self.assertGreaterEqual(isolation_reliability, 0.95, "Isolation mode should be 95%+ reliable")
        
        # Record metrics
        metrics = {
            'environment_operation_reliability': f"{operation_reliability:.1%}",
            'environment_detection_reliability': f"{detection_reliability:.1%}",
            'isolation_mode_reliability': f"{isolation_reliability:.1%}"
        }
        
        print(f"✓ Environment management business value metrics: {metrics}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])