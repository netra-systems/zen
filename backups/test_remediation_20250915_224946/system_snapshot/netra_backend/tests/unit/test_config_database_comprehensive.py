"""
Comprehensive Unit Tests for Database Configuration Module

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (DATABASE CONNECTIVITY CRITICAL)
- Business Goal: Zero database connectivity failures across all environments
- Value Impact: Prevents database connection failures that break golden path user flow
- Strategic Impact: Ensures reliable data access for user login  ->  AI responses workflow
- Revenue Impact: Eliminates data access failures that can cause complete system downtime

MISSION CRITICAL: These tests validate database configuration components that enable:
1. PostgreSQL connection parameter validation across environments
2. Redis configuration for caching and session management  
3. ClickHouse configuration for analytics and state persistence
4. Database URL validation and format checking
5. Environment-specific database configuration loading
6. Connection parameter sanitization and security

GOLDEN PATH DATABASE SCENARIOS TESTED:
1. Database URL Generation: Proper PostgreSQL URLs for each environment
2. Redis Configuration: Correct cache settings for performance
3. ClickHouse Setup: Analytics database configuration for state persistence
4. Connection Validation: Database parameter validation prevents failures
5. Environment Isolation: Database configs don't leak between environments
6. Security Validation: Connection strings properly sanitized
7. Backward Compatibility: Legacy database manager interface preserved

TESTING APPROACH:
- Real configuration objects (no mocks for database configs)
- Minimal mocking limited to actual database connections only
- SSOT compliance using test_framework utilities
- Business value focus on database reliability scenarios
- Golden path focus on environment-specific database configuration
- Coverage target: 95%+ method coverage on critical database configuration paths
"""
import pytest
import time
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from urllib.parse import urlparse
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.configuration.database import DatabaseConfigManager, get_database_config_manager, get_database_url, validate_database_connection, populate_database_config
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.schemas.config import AppConfig

class DatabaseConfigurationComprehensiveTests(SSotBaseTestCase):
    """
    Comprehensive test suite for Database Configuration Module.
    
    Tests the critical database configuration components that enable reliable
    data access across all environments for golden path user flow stability.
    """

    def setUp(self):
        """Set up test environment with proper database configuration."""
        super().setUp()
        self.env = get_env()
        self.env.enable_isolation()
        self.env.set('ENVIRONMENT', 'testing', 'test_setup')
        self.env.set('TESTING', 'true', 'test_setup')
        self.setup_test_database_config()

    def tearDown(self):
        """Clean up test environment."""
        self.env.reset()
        super().tearDown()

    def setup_test_database_config(self):
        """Set up comprehensive test database configuration."""
        self.env.set('POSTGRES_HOST', 'localhost', 'test_db_setup')
        self.env.set('POSTGRES_PORT', '5434', 'test_db_setup')
        self.env.set('POSTGRES_USER', 'netra_test', 'test_db_setup')
        self.env.set('POSTGRES_PASSWORD', 'netra_test_password', 'test_db_setup')
        self.env.set('POSTGRES_DB', 'netra_test', 'test_db_setup')
        self.env.set('DATABASE_URL', 'postgresql://netra_test:netra_test_password@localhost:5434/netra_test', 'test_db_setup')
        self.env.set('REDIS_HOST', 'localhost', 'test_db_setup')
        self.env.set('REDIS_PORT', '6381', 'test_db_setup')
        self.env.set('REDIS_URL', 'redis://localhost:6381/0', 'test_db_setup')
        self.env.set('CLICKHOUSE_HOST', 'localhost', 'test_db_setup')
        self.env.set('CLICKHOUSE_PORT', '9000', 'test_db_setup')
        self.env.set('CLICKHOUSE_USER', 'default', 'test_db_setup')
        self.env.set('CLICKHOUSE_PASSWORD', 'clickhouse_test_password', 'test_db_setup')
        self.env.set('CLICKHOUSE_DATABASE', 'netra_test', 'test_db_setup')

    @contextmanager
    def temp_env_vars(self, **kwargs):
        """Context manager for temporary environment variables."""
        original_values = {}
        for key, value in kwargs.items():
            original_values[key] = self.env.get(key)
            self.env.set(key, value, 'temp_test_var')
        try:
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    self.env.delete(key, 'temp_test_cleanup')
                else:
                    self.env.set(key, original_value, 'temp_test_restore')

    def test_database_config_manager_initialization(self):
        """
        Test DatabaseConfigManager initialization and basic functionality.
        
        BVJ: DatabaseConfigManager is the SSOT for database configuration.
        Proper initialization is critical for all database operations.
        """
        manager = DatabaseConfigManager()
        self.assertIsNotNone(manager, 'DatabaseConfigManager should initialize successfully')
        self.assertIsNone(manager._config, 'Config should be lazy-loaded')
        self.assertIsInstance(manager._cached_config, dict, 'Cached config should be initialized as dict')
        config = manager.get_config()
        self.assertIsInstance(config, AppConfig, 'Manager should provide valid AppConfig')
        self.assertIsNotNone(manager._config, 'Config should be cached after first access')
        print('[U+2713] DatabaseConfigManager initialization validated')

    def test_database_config_manager_get_database_url(self):
        """
        Test DatabaseConfigManager database URL retrieval.
        
        BVJ: Database URL retrieval is critical for establishing
        PostgreSQL connections in the golden path user flow.
        """
        manager = DatabaseConfigManager()
        database_url = manager.get_database_url()
        self.assertIsNotNone(database_url, 'Database URL should not be None')
        self.assertIsInstance(database_url, str, 'Database URL should be string')
        self.assertGreater(len(database_url), 0, 'Database URL should not be empty')
        self.assertTrue(database_url.startswith(('postgresql://', 'postgres://')), 'Database URL should use PostgreSQL scheme')
        parsed_url = urlparse(database_url)
        self.assertIsNotNone(parsed_url.scheme, 'Database URL should have valid scheme')
        self.assertIsNotNone(parsed_url.netloc, 'Database URL should have valid netloc')
        print(f'[U+2713] Database URL retrieval validated: {database_url[:50]}...')

    def test_database_config_manager_get_redis_config(self):
        """
        Test DatabaseConfigManager Redis configuration retrieval.
        
        BVJ: Redis configuration is critical for caching and session
        management that supports high-performance user interactions.
        """
        manager = DatabaseConfigManager()
        redis_config = manager.get_redis_config()
        self.assertIsInstance(redis_config, dict, 'Redis config should be dictionary')
        expected_fields = ['host', 'port', 'db']
        for field in expected_fields:
            self.assertIn(field, redis_config, f'Redis config should contain {field}')
        self.assertEqual(redis_config['host'], 'localhost', 'Redis host should match environment')
        self.assertEqual(redis_config['port'], 6381, 'Redis port should be integer')
        self.assertEqual(redis_config['db'], 0, 'Redis DB should default to 0')
        self.assertIn('password', redis_config, 'Redis config should include password field')
        self.assertIn('ssl', redis_config, 'Redis config should include SSL field')
        print(f'[U+2713] Redis configuration validated: {redis_config}')

    def test_database_config_manager_get_clickhouse_config(self):
        """
        Test DatabaseConfigManager ClickHouse configuration retrieval.
        
        BVJ: ClickHouse configuration is critical for analytics and
        state persistence that supports AI response generation.
        """
        manager = DatabaseConfigManager()
        clickhouse_config = manager.get_clickhouse_config()
        self.assertIsInstance(clickhouse_config, dict, 'ClickHouse config should be dictionary')
        expected_fields = ['host', 'port', 'user', 'database']
        for field in expected_fields:
            self.assertIn(field, clickhouse_config, f'ClickHouse config should contain {field}')
        self.assertEqual(clickhouse_config['host'], 'localhost', 'ClickHouse host should match environment')
        self.assertEqual(clickhouse_config['port'], 9000, 'ClickHouse port should be integer')
        self.assertEqual(clickhouse_config['user'], 'default', 'ClickHouse user should match environment')
        self.assertEqual(clickhouse_config['database'], 'netra_test', 'ClickHouse database should match environment')
        self.assertIn('password', clickhouse_config, 'ClickHouse config should include password field')
        print(f'[U+2713] ClickHouse configuration validated: {clickhouse_config}')

    def test_database_config_manager_validate_database_config(self):
        """
        Test DatabaseConfigManager database configuration validation.
        
        BVJ: Database validation prevents connection failures that
        could break the golden path user flow at startup.
        """
        manager = DatabaseConfigManager()
        is_valid = manager.validate_database_config()
        self.assertTrue(is_valid, 'Database configuration should be valid in test environment')
        with self.temp_env_vars(DATABASE_URL=''):
            manager._config = None
            is_invalid = manager.validate_database_config()
            self.assertFalse(is_invalid, 'Validation should fail with empty database URL')
        with self.temp_env_vars(DATABASE_URL='invalid-url'):
            manager._config = None
            is_malformed = manager.validate_database_config()
            self.assertFalse(is_malformed, 'Validation should fail with malformed URL')
        print('[U+2713] Database configuration validation tested')

    def test_database_config_manager_populate_database_config(self):
        """
        Test DatabaseConfigManager complete database configuration population.
        
        BVJ: Complete configuration population ensures all database
        components are properly configured for system operation.
        """
        manager = DatabaseConfigManager()
        complete_config = manager.populate_database_config()
        self.assertIsInstance(complete_config, dict, 'Complete config should be dictionary')
        self.assertIn('postgresql', complete_config, 'Complete config should include PostgreSQL')
        postgresql_config = complete_config['postgresql']
        self.assertIn('url', postgresql_config, 'PostgreSQL config should include URL')
        self.assertIn('valid', postgresql_config, 'PostgreSQL config should include validation status')
        self.assertTrue(postgresql_config['valid'], 'PostgreSQL config should be valid')
        self.assertIn('redis', complete_config, 'Complete config should include Redis')
        redis_config = complete_config['redis']
        self.assertIsInstance(redis_config, dict, 'Redis config should be dictionary')
        self.assertIn('host', redis_config, 'Redis config should include host')
        self.assertIn('clickhouse', complete_config, 'Complete config should include ClickHouse')
        clickhouse_config = complete_config['clickhouse']
        self.assertIsInstance(clickhouse_config, dict, 'ClickHouse config should be dictionary')
        self.assertIn('host', clickhouse_config, 'ClickHouse config should include host')
        print(f'[U+2713] Complete database configuration populated with {len(complete_config)} components')

    def test_get_database_config_manager_function(self):
        """
        Test get_database_config_manager() backward compatibility function.
        
        BVJ: Backward compatibility ensures existing code continues
        to work during the transition to unified configuration.
        """
        manager = get_database_config_manager()
        self.assertIsInstance(manager, DatabaseConfigManager, 'Function should return DatabaseConfigManager instance')
        config = manager.get_config()
        self.assertIsInstance(config, AppConfig, 'Manager should provide valid configuration')
        database_url = manager.get_database_url()
        self.assertIsNotNone(database_url, 'Manager should provide database URL')
        print('[U+2713] Backward compatibility function validated')

    def test_module_level_database_functions(self):
        """
        Test module-level database configuration functions.
        
        BVJ: Module-level functions provide convenient access to
        database configuration for existing code patterns.
        """
        database_url = get_database_url()
        self.assertIsNotNone(database_url, 'get_database_url() should return valid URL')
        self.assertIsInstance(database_url, str, 'Database URL should be string')
        is_valid = validate_database_connection()
        self.assertIsInstance(is_valid, bool, 'validate_database_connection() should return boolean')
        config = populate_database_config()
        self.assertIsInstance(config, dict, 'populate_database_config() should return dictionary')
        self.assertIn('postgresql', config, 'Config should include PostgreSQL')
        self.assertIn('redis', config, 'Config should include Redis')
        self.assertIn('clickhouse', config, 'Config should include ClickHouse')
        print('[U+2713] Module-level database functions validated')

    def test_database_config_environment_specificity(self):
        """
        Test database configuration across different environments.
        
        BVJ: Environment-specific database configuration is critical
        for proper database connectivity in each deployment environment.
        """
        test_environments = ['development', 'staging', 'production', 'testing']
        for env_name in test_environments:
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    manager = DatabaseConfigManager()
                    manager._config = None
                    config = manager.get_config()
                    self.assertEqual(config.environment, env_name, f'Config environment should match {env_name}')
                    database_url = manager.get_database_url(env_name)
                    if database_url:
                        self.assertIsInstance(database_url, str, f'Database URL should be string for {env_name}')
                    print(f'[U+2713] Database configuration validated for environment: {env_name}')

    def test_database_config_staging_specific_validation(self):
        """
        Test database configuration validation for staging environment.
        
        BVJ: Staging database configuration must be validated to ensure
        it connects to staging databases, not production or development.
        """
        with self.temp_env_vars(ENVIRONMENT='staging', POSTGRES_HOST='staging-postgres.example.com', POSTGRES_USER='staging_user', POSTGRES_PASSWORD='staging_secure_password', DATABASE_URL='postgresql://staging_user:staging_secure_password@staging-postgres.example.com:5432/staging_db'):
            manager = DatabaseConfigManager()
            manager._config = None
            config = manager.get_config()
            self.assertEqual(config.environment, 'staging', 'Should detect staging environment')
            database_url = manager.get_database_url('staging')
            self.assertIsNotNone(database_url, 'Staging should have database URL')
            self.assertIn('staging', database_url, 'Staging URL should contain staging identifier')
            is_valid = manager.validate_database_config('staging')
            self.assertTrue(is_valid, 'Staging database configuration should be valid')
            print('[U+2713] Staging-specific database configuration validated')

    def test_database_config_production_security_requirements(self):
        """
        Test database configuration meets production security requirements.
        
        BVJ: Production database security is critical for protecting
        customer data and maintaining system integrity.
        """
        with self.temp_env_vars(ENVIRONMENT='production', POSTGRES_HOST='prod-postgres.secure.com', POSTGRES_USER='prod_user', POSTGRES_PASSWORD='prod_very_secure_password_32_chars', DATABASE_URL='postgresql://prod_user:prod_very_secure_password_32_chars@prod-postgres.secure.com:5432/prod_db'):
            manager = DatabaseConfigManager()
            manager._config = None
            config = manager.get_config()
            self.assertEqual(config.environment, 'production', 'Should detect production environment')
            database_url = manager.get_database_url('production')
            self.assertIsNotNone(database_url, 'Production should have database URL')
            parsed_url = urlparse(database_url)
            self.assertIsNotNone(parsed_url.password, 'Production URL should have password')
            self.assertGreaterEqual(len(parsed_url.password), 16, 'Production password should be at least 16 characters')
            is_valid = manager.validate_database_config('production')
            self.assertTrue(is_valid, 'Production database configuration should be valid')
            print('[U+2713] Production security requirements validated')

    def test_database_config_missing_configuration_handling(self):
        """
        Test DatabaseConfigManager handles missing configuration gracefully.
        
        BVJ: Graceful error handling ensures meaningful error messages
        when database configuration is missing or invalid.
        """
        with self.temp_env_vars(DATABASE_URL=''):
            manager = DatabaseConfigManager()
            manager._config = None
            database_url = manager.get_database_url()
            self.assertIn(database_url, ['', None], 'Should handle missing database URL gracefully')
            is_valid = manager.validate_database_config()
            self.assertFalse(is_valid, 'Validation should fail with missing database URL')
        with self.temp_env_vars(REDIS_HOST='', REDIS_PORT=''):
            manager = DatabaseConfigManager()
            manager._config = None
            redis_config = manager.get_redis_config()
            self.assertIsInstance(redis_config, dict, 'Should return dict even with missing Redis config')
        print('[U+2713] Missing configuration handling validated')

    def test_database_config_malformed_url_handling(self):
        """
        Test DatabaseConfigManager handles malformed database URLs.
        
        BVJ: Malformed URL handling prevents system crashes during
        configuration loading and provides actionable error information.
        """
        malformed_urls = ['not-a-url', 'postgresql://incomplete', 'mysql://wrong-scheme@host:5432/db', 'postgresql://user@:5432/db', 'postgresql://user@host/db']
        for malformed_url in malformed_urls:
            with self.subTest(url=malformed_url):
                with self.temp_env_vars(DATABASE_URL=malformed_url):
                    manager = DatabaseConfigManager()
                    manager._config = None
                    is_valid = manager.validate_database_config()
                    self.assertFalse(is_valid, f'Validation should fail for malformed URL: {malformed_url}')
        print('[U+2713] Malformed URL handling validated')

    @patch('netra_backend.app.core.configuration.database.get_unified_config')
    def test_database_config_unified_config_error_handling(self, mock_get_config):
        """
        Test DatabaseConfigManager handles unified config errors gracefully.
        
        BVJ: Error handling ensures database configuration failures
        provide meaningful error messages for troubleshooting.
        """
        mock_get_config.side_effect = RuntimeError('Unified config error')
        manager = DatabaseConfigManager()
        manager._config = None
        with self.assertRaises(RuntimeError) as context:
            manager.get_config()
        self.assertIn('Unified config error', str(context.exception))
        print('[U+2713] Unified config error handling validated')

    def test_database_config_performance_requirements(self):
        """
        Test database configuration meets performance requirements.
        
        BVJ: Database configuration performance is critical for
        system startup time and connection establishment speed.
        """
        manager = DatabaseConfigManager()
        start_time = time.time()
        for _ in range(100):
            database_url = manager.get_database_url()
            self.assertIsNotNone(database_url)
        url_retrieval_time = time.time() - start_time
        start_time = time.time()
        for _ in range(100):
            redis_config = manager.get_redis_config()
            self.assertIsInstance(redis_config, dict)
        redis_config_time = time.time() - start_time
        start_time = time.time()
        for _ in range(50):
            complete_config = manager.populate_database_config()
            self.assertIsInstance(complete_config, dict)
        complete_config_time = time.time() - start_time
        self.assertLess(url_retrieval_time, 0.1, '100 database URL retrievals should complete in under 100ms')
        self.assertLess(redis_config_time, 0.1, '100 Redis config retrievals should complete in under 100ms')
        self.assertLess(complete_config_time, 0.5, '50 complete config populations should complete in under 500ms')
        print(f'[U+2713] Database configuration performance validated - URL: {url_retrieval_time:.3f}s, Redis: {redis_config_time:.3f}s, Complete: {complete_config_time:.3f}s')

    def test_database_config_unified_config_integration(self):
        """
        Test DatabaseConfigManager integration with unified configuration.
        
        BVJ: Integration with unified configuration ensures database
        settings are properly loaded from the centralized configuration system.
        """
        manager = DatabaseConfigManager()
        config = manager.get_config()
        unified_config = get_unified_config()
        self.assertEqual(config.environment, unified_config.environment, 'Database manager should use same environment as unified config')
        self.assertEqual(config.app_name, unified_config.app_name, 'Database manager should use same app_name as unified config')
        manager_url = manager.get_database_url()
        unified_url = unified_config.database_url
        if manager_url and unified_url:
            self.assertEqual(manager_url, unified_url, 'Database URLs should be consistent between manager and unified config')
        print('[U+2713] Unified configuration integration validated')

    def test_database_config_environment_variable_integration(self):
        """
        Test database configuration properly uses environment variables.
        
        BVJ: Environment variable integration ensures database configuration
        can be properly customized for each deployment environment.
        """
        custom_host = 'custom-db-host.example.com'
        custom_port = '5433'
        custom_user = 'custom_user'
        custom_password = 'custom_secure_password'
        custom_db = 'custom_database'
        custom_url = f'postgresql://{custom_user}:{custom_password}@{custom_host}:{custom_port}/{custom_db}'
        with self.temp_env_vars(POSTGRES_HOST=custom_host, POSTGRES_PORT=custom_port, POSTGRES_USER=custom_user, POSTGRES_PASSWORD=custom_password, POSTGRES_DB=custom_db, DATABASE_URL=custom_url):
            manager = DatabaseConfigManager()
            manager._config = None
            database_url = manager.get_database_url()
            self.assertEqual(database_url, custom_url, 'Should use custom database URL from environment')
            parsed_url = urlparse(database_url)
            self.assertEqual(parsed_url.hostname, custom_host, 'Should use custom host')
            self.assertEqual(parsed_url.port, int(custom_port), 'Should use custom port')
            self.assertEqual(parsed_url.username, custom_user, 'Should use custom user')
            self.assertEqual(parsed_url.password, custom_password, 'Should use custom password')
        print('[U+2713] Environment variable integration validated')

    def test_database_config_golden_path_requirements(self):
        """
        Test database configuration meets golden path user flow requirements.
        
        BVJ: Golden path requirements ensure database connectivity supports
        the critical user flow from login  ->  AI responses without failures.
        """
        manager = DatabaseConfigManager()
        database_url = manager.get_database_url()
        self.assertIsNotNone(database_url, 'PostgreSQL URL required for user data access')
        self.assertTrue(database_url.startswith(('postgresql://', 'postgres://')), 'Must use PostgreSQL for relational data')
        redis_config = manager.get_redis_config()
        self.assertIn('host', redis_config, 'Redis host required for session caching')
        self.assertIn('port', redis_config, 'Redis port required for connection')
        is_valid = manager.validate_database_config()
        self.assertTrue(is_valid, 'Database configuration must be valid for system operation')
        complete_config = manager.populate_database_config()
        required_components = ['postgresql', 'redis', 'clickhouse']
        for component in required_components:
            self.assertIn(component, complete_config, f'{component} configuration required for complete system')
        print('[U+2713] Golden path database requirements validated')

    def test_database_config_business_value_metrics(self):
        """
        Test and record database configuration business value metrics.
        
        BVJ: Business value metrics demonstrate database configuration
        contribution to system reliability and golden path user flow stability.
        """
        manager = DatabaseConfigManager()
        metrics = {}
        url_attempts = 10
        successful_url_retrievals = 0
        for _ in range(url_attempts):
            try:
                database_url = manager.get_database_url()
                if database_url and len(database_url) > 0:
                    successful_url_retrievals += 1
            except Exception:
                pass
        url_reliability = successful_url_retrievals / url_attempts
        validation_attempts = 5
        successful_validations = 0
        for _ in range(validation_attempts):
            try:
                is_valid = manager.validate_database_config()
                if isinstance(is_valid, bool):
                    successful_validations += 1
            except Exception:
                pass
        validation_reliability = successful_validations / validation_attempts
        population_attempts = 5
        successful_populations = 0
        for _ in range(population_attempts):
            try:
                config = manager.populate_database_config()
                if isinstance(config, dict) and 'postgresql' in config:
                    successful_populations += 1
            except Exception:
                pass
        population_reliability = successful_populations / population_attempts
        self.assertGreaterEqual(url_reliability, 0.95, 'Database URL retrieval should be 95%+ reliable')
        self.assertGreaterEqual(validation_reliability, 0.95, 'Database validation should be 95%+ reliable')
        self.assertGreaterEqual(population_reliability, 0.95, 'Database configuration population should be 95%+ reliable')
        metrics = {'database_url_retrieval_reliability': f'{url_reliability:.1%}', 'database_validation_reliability': f'{validation_reliability:.1%}', 'database_population_reliability': f'{population_reliability:.1%}'}
        print(f'[U+2713] Database configuration business value metrics: {metrics}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')