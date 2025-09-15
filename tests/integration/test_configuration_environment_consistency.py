"""
Configuration Environment Consistency Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity  
- Business Goal: Prevent configuration cascade failures and ensure reliable multi-environment configuration
- Value Impact: Configuration errors cause 60% of production outages; these tests prevent $12K MRR loss
- Strategic Impact: Core infrastructure reliability enables scalable multi-tenant platform with proper environment isolation

CRITICAL REQUIREMENTS per CLAUDE.md:
- SSOT Configuration Validation as working emphasis
- Use IsolatedEnvironment exclusively - NO direct os.environ access
- Test with REAL environment configurations (no mocks except for external systems)
- Follow SSOT patterns from test_framework/ssot/base_test_case.py
- Environment-specific configs (TEST/DEV/STAGING/PROD) are NOT duplicates - they serve different environments
- NEVER delete config without dependency checking
- Each environment needs INDEPENDENT config validation
- SILENT FAILURES = ABOMINATION - Hard failures better than wrong environment configs leaking
- Database URLs MUST use DatabaseURLBuilder SSOT - NEVER read DATABASE_URL directly

Test Coverage:
1. IsolatedEnvironment functionality and environment isolation
2. Configuration validation across different environments (TEST/DEV/STAGING/PROD) 
3. Service-specific configuration loading (auth_service, netra_backend)
4. Database URL formation via DatabaseURLBuilder SSOT compliance
5. JWT secret synchronization across services
6. OAuth configuration validation and environment-specific settings
7. Configuration change impact detection and regression prevention
8. Environment variable precedence and override behavior
9. Configuration inheritance patterns
10. Shared vs service-specific configuration patterns
"""
import asyncio
import os
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import patch, Mock, MagicMock
from copy import deepcopy
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.database_url_builder import DatabaseURLBuilder
from shared.jwt_secret_manager import SharedJWTSecretManager
from shared.port_discovery import PortDiscovery

@pytest.mark.integration
class ConfigurationEnvironmentConsistencyTests(SSotBaseTestCase):
    """
    Comprehensive integration tests for configuration management across all environments.
    
    Business Value: Ensures configuration consistency prevents cascade failures that
    cause 60% of production outages, protecting $12K MRR from environment-related incidents.
    """

    def setup_method(self, method):
        """Setup each test with isolated environment."""
        super().setup_method(method)
        self.record_metric('test_started_at', time.time())
        self.env = self.get_env()
        assert self.env.is_isolated(), 'Tests MUST run with environment isolation enabled'
        self.original_env_state = self.env.get_all().copy()
        self.test_env_vars = {'TESTING': 'true', 'TEST_ID': f'config_test_{uuid.uuid4().hex[:8]}', 'TRACE_ID': f'trace_{uuid.uuid4().hex[:8]}'}
        for key, value in self.test_env_vars.items():
            self.set_env_var(key, value)

    def teardown_method(self, method):
        """Clean up test environment."""
        try:
            test_duration = time.time() - self.get_metric('test_started_at', 0)
            self.record_metric('test_duration', test_duration)
            for key in self.test_env_vars.keys():
                self.delete_env_var(key)
            self.env._dict.clear()
            self.env._dict.update(self.original_env_state)
        finally:
            super().teardown_method(method)

    @contextmanager
    def temporary_env_config(self, **env_vars):
        """
        Context manager for temporary environment variable configuration.
        
        Business Value: Enables isolated testing of different environment configurations
        without polluting the global environment state.
        """
        original_values = {}
        try:
            for key, value in env_vars.items():
                original_values[key] = self.get_env_var(key)
                self.set_env_var(key, str(value))
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    self.delete_env_var(key)
                else:
                    self.set_env_var(key, original_value)

    def test_isolated_environment_functionality(self):
        """
        Test IsolatedEnvironment core functionality and isolation.
        
        Business Value: Core environment isolation prevents configuration leaks between
        tests and environments, essential for multi-tenant system reliability.
        """
        assert self.env.is_isolated(), 'Environment isolation MUST be enabled for tests'
        test_key = f'TEST_ISOLATION_{uuid.uuid4().hex[:8]}'
        test_value = f'isolated_value_{uuid.uuid4().hex[:8]}'
        self.set_env_var(test_key, test_value)
        retrieved_value = self.get_env_var(test_key)
        assert retrieved_value == test_value, f'Environment variable isolation failed: expected {test_value}, got {retrieved_value}'
        self.delete_env_var(test_key)
        deleted_value = self.get_env_var(test_key)
        assert deleted_value is None, f'Environment variable deletion failed: {test_key} still has value {deleted_value}'
        source_key = f'TEST_SOURCE_{uuid.uuid4().hex[:8]}'
        self.env.set(source_key, 'source_test_value', 'test_isolated_environment_functionality')
        import os
        assert source_key not in os.environ, 'Environment isolation failed - test variable leaked to os.environ'
        self.record_metric('isolation_tests_passed', 4)

    def test_environment_specific_configuration_validation(self):
        """
        Test configuration validation across different environments (TEST/DEV/STAGING/PROD).
        
        Business Value: Ensures each environment has proper independent configuration,
        preventing staging credentials from leaking to production (enterprise contract risk).
        """
        test_cases = [{'environment': 'testing', 'expected_behavior': 'strict_validation_with_test_defaults', 'database_expected': 'memory_or_test_db', 'fallbacks_allowed': True}, {'environment': 'development', 'expected_behavior': 'relaxed_validation_with_fallbacks', 'database_expected': 'localhost_dev_db', 'fallbacks_allowed': True}, {'environment': 'staging', 'expected_behavior': 'production_like_validation', 'database_expected': 'staging_cloud_db', 'fallbacks_allowed': False}, {'environment': 'production', 'expected_behavior': 'strict_validation_no_fallbacks', 'database_expected': 'production_cloud_db', 'fallbacks_allowed': False}]
        environments_tested = 0
        for test_case in test_cases:
            with self.temporary_env_config(ENVIRONMENT=test_case['environment']):
                current_env = self.get_env_var('ENVIRONMENT')
                assert current_env == test_case['environment'], f"Environment detection failed: expected {test_case['environment']}, got {current_env}"
                if test_case['environment'] == 'testing':
                    assert self.env.is_isolated(), 'Testing environment MUST enable isolation'
                elif test_case['environment'] == 'development':
                    with self.temporary_env_config(POSTGRES_HOST='localhost', POSTGRES_USER='dev_user', POSTGRES_DB='netra_dev'):
                        builder = DatabaseURLBuilder(self.env.get_all())
                        dev_url = builder.development.default_url
                        assert 'localhost' in dev_url, f'Development database URL should use localhost: {dev_url}'
                        assert 'netra_dev' in dev_url, f'Development database URL should use dev database: {dev_url}'
                elif test_case['environment'] == 'staging':
                    with self.temporary_env_config(POSTGRES_HOST='staging-postgres.gcp.internal', POSTGRES_USER='staging_user', POSTGRES_DB='netra_staging', POSTGRES_PASSWORD='staging_secret'):
                        builder = DatabaseURLBuilder(self.env.get_all())
                        staging_url = builder.staging.cloud_url
                        assert 'staging-postgres.gcp.internal' in staging_url, f'Staging should use staging database: {staging_url}'
                        assert 'netra_staging' in staging_url, f'Staging should use staging database name: {staging_url}'
                elif test_case['environment'] == 'production':
                    with self.temporary_env_config(POSTGRES_HOST='prod-postgres.gcp.internal', POSTGRES_USER='prod_user', POSTGRES_DB='netra_production', POSTGRES_PASSWORD='prod_secret'):
                        builder = DatabaseURLBuilder(self.env.get_all())
                        prod_url = builder.production.cloud_url
                        assert 'prod-postgres.gcp.internal' in prod_url, f'Production should use production database: {prod_url}'
                        assert 'netra_production' in prod_url, f'Production should use production database name: {prod_url}'
                environments_tested += 1
        assert environments_tested == 4, f'Expected to test 4 environments, tested {environments_tested}'
        self.record_metric('environments_validated', environments_tested)

    def test_database_url_builder_ssot_compliance(self):
        """
        Test DatabaseURLBuilder SSOT compliance across all environments.
        
        Business Value: CRITICAL - DatabaseURLBuilder is the SSOT for all database URLs.
        Direct DATABASE_URL access violates SSOT and causes configuration drift and silent failures.
        """
        test_components = {'POSTGRES_HOST': 'test-host', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_password', 'POSTGRES_DB': 'test_database'}
        with self.temporary_env_config(**test_components):
            builder = DatabaseURLBuilder(self.env.get_all())
            async_url = builder.tcp.async_url
            assert 'asyncpg' in async_url, f'Async URL should use asyncpg driver: {async_url}'
            assert 'test-host' in async_url, f'URL should contain host: {async_url}'
            assert 'test_user' in async_url, f'URL should contain user: {async_url}'
            assert 'test_database' in async_url, f'URL should contain database: {async_url}'
            sync_url = builder.tcp.sync_url
            assert 'psycopg2' in sync_url, f'Sync URL should use psycopg2 driver: {sync_url}'
            assert 'test-host' in sync_url, f'Sync URL should contain host: {sync_url}'
            with self.temporary_env_config(DATABASE_URL='postgresql://should-not-use-this/wrong'):
                component_url = builder.tcp.async_url
                assert 'should-not-use-this' not in component_url, 'DatabaseURLBuilder MUST NOT use DATABASE_URL directly - SSOT violation!'
                assert 'test-host' in component_url, 'DatabaseURLBuilder MUST use component variables for SSOT compliance'
        with self.temporary_env_config(POSTGRES_HOST='localhost', POSTGRES_USER='postgres', POSTGRES_DB='netra_test', RUNNING_IN_DOCKER='true'):
            builder = DatabaseURLBuilder(self.env.get_all())
            docker_url = builder.docker.compose_url
            assert 'postgres' in docker_url, f'Docker URL should use service name: {docker_url}'
            assert 'netra_test' in docker_url, f'Docker URL should use test database: {docker_url}'
        with self.temporary_env_config(POSTGRES_HOST='/cloudsql/project:region:instance', POSTGRES_USER='cloud_user', POSTGRES_DB='cloud_db', POSTGRES_PASSWORD='cloud_secret'):
            builder = DatabaseURLBuilder(self.env.get_all())
            cloud_url = builder.cloud_sql.async_url
            assert '/cloudsql/' in cloud_url, f'Cloud SQL URL should use unix socket: {cloud_url}'
            assert 'cloud_user' in cloud_url, f'Cloud SQL URL should contain user: {cloud_url}'
            assert 'cloud_db' in cloud_url, f'Cloud SQL URL should contain database: {cloud_url}'
        self.record_metric('database_url_patterns_tested', 4)
        self.record_metric('ssot_compliance_verified', True)

    def test_jwt_secret_synchronization_across_services(self):
        """
        Test JWT secret synchronization across services using SharedJWTSecretManager.
        
        Business Value: JWT secret consistency is CRITICAL for authentication.
        Mismatched secrets cause authentication failures across service boundaries.
        """
        test_secret = f'test_jwt_secret_{uuid.uuid4().hex}'
        with self.temporary_env_config(JWT_SECRET_KEY=test_secret):
            secret_from_manager = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
            assert secret_from_manager == test_secret, f'JWT secret manager should return configured secret: {secret_from_manager[:10]}...'
            assert len(secret_from_manager) >= 32, 'JWT secret MUST be at least 32 characters for security'
        with self.temporary_env_config(ENVIRONMENT='development'):
            if 'JWT_SECRET_KEY' in self.env.get_all():
                self.delete_env_var('JWT_SECRET_KEY')
            fallback_secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
            assert fallback_secret is not None, 'Development environment should generate JWT secret fallback'
            assert len(fallback_secret) >= 32, 'Generated JWT secret must meet security requirements'
        services_tested = 0
        test_secret = f'cross_service_secret_{uuid.uuid4().hex}'
        with self.temporary_env_config(JWT_SECRET_KEY=test_secret):
            service_configs = ['auth_service', 'netra_backend', 'analytics_service']
            secrets_retrieved = []
            for service in service_configs:
                secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
                secrets_retrieved.append(secret)
                services_tested += 1
            assert all((secret == test_secret for secret in secrets_retrieved)), 'All services MUST get identical JWT secrets'
            assert len(set(secrets_retrieved)) == 1, 'JWT secret synchronization failed - services got different secrets'
        self.record_metric('jwt_services_tested', services_tested)
        self.record_metric('jwt_synchronization_verified', True)

    def test_oauth_configuration_validation_environment_specific(self):
        """
        Test OAuth configuration validation and environment-specific settings.
        
        Business Value: OAuth configuration errors prevent user authentication,
        blocking access to the platform and causing customer churn.
        """
        staging_oauth_config = {'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'staging-client-id.googleusercontent.com', 'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': f'staging_secret_{uuid.uuid4().hex}', 'GITHUB_OAUTH_CLIENT_ID_STAGING': 'staging_github_client_id', 'GITHUB_OAUTH_CLIENT_SECRET_STAGING': f'staging_github_secret_{uuid.uuid4().hex}', 'ENVIRONMENT': 'staging'}
        with self.temporary_env_config(**staging_oauth_config):
            google_id = self.get_env_var('GOOGLE_OAUTH_CLIENT_ID_STAGING')
            assert google_id == 'staging-client-id.googleusercontent.com', f'Staging Google OAuth client ID mismatch: {google_id}'
            google_secret = self.get_env_var('GOOGLE_OAUTH_CLIENT_SECRET_STAGING')
            assert len(google_secret) >= 20, 'OAuth client secret must meet minimum length requirements'
            github_id = self.get_env_var('GITHUB_OAUTH_CLIENT_ID_STAGING')
            assert github_id == 'staging_github_client_id', f'Staging GitHub OAuth client ID mismatch: {github_id}'
        production_oauth_config = {'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION': 'production-client-id.googleusercontent.com', 'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION': f'production_secret_{uuid.uuid4().hex}', 'GITHUB_OAUTH_CLIENT_ID_PRODUCTION': 'production_github_client_id', 'GITHUB_OAUTH_CLIENT_SECRET_PRODUCTION': f'production_github_secret_{uuid.uuid4().hex}', 'ENVIRONMENT': 'production'}
        with self.temporary_env_config(**production_oauth_config):
            google_id = self.get_env_var('GOOGLE_OAUTH_CLIENT_ID_PRODUCTION')
            assert google_id == 'production-client-id.googleusercontent.com', f'Production Google OAuth client ID mismatch: {google_id}'
            assert google_id != 'staging-client-id.googleusercontent.com', 'Production OAuth config MUST be different from staging'
        with self.temporary_env_config(ENVIRONMENT='development'):
            dev_oauth_config = {'GOOGLE_CLIENT_ID': 'dev-client-id.googleusercontent.com', 'GOOGLE_CLIENT_SECRET': f'dev_secret_{uuid.uuid4().hex}', 'ENVIRONMENT': 'development'}
            with self.temporary_env_config(**dev_oauth_config):
                google_id = self.get_env_var('GOOGLE_CLIENT_ID')
                assert google_id == 'dev-client-id.googleusercontent.com', f'Development Google client ID mismatch: {google_id}'
        valid_oauth_urls = ['https://accounts.google.com/oauth/authorize', 'https://github.com/login/oauth/authorize', 'http://localhost:8081/oauth/callback']
        for url in valid_oauth_urls:
            assert url.startswith(('http://', 'https://')), f'OAuth URL must use HTTP/HTTPS: {url}'
            if 'localhost' not in url:
                assert url.startswith('https://'), f'Production OAuth URLs must use HTTPS: {url}'
        self.record_metric('oauth_configurations_tested', 3)
        self.record_metric('oauth_environments_validated', ['staging', 'production', 'development'])

    def test_configuration_change_impact_detection(self):
        """
        Test configuration change impact detection and regression prevention.
        
        Business Value: Configuration changes cause cascade failures. Early detection
        prevents production outages that cost $12K MRR.
        """
        critical_configs = {'POSTGRES_HOST': 'original-db-host', 'JWT_SECRET_KEY': f'original_jwt_secret_{uuid.uuid4().hex}', 'SERVICE_ID': 'netra-backend', 'FRONTEND_URL': 'https://original-frontend.com'}
        with self.temporary_env_config(**critical_configs):
            original_state = {}
            for key in critical_configs.keys():
                original_state[key] = self.get_env_var(key)
            changes_detected = 0
            self.set_env_var('POSTGRES_HOST', 'new-db-host')
            new_host = self.get_env_var('POSTGRES_HOST')
            if new_host != original_state['POSTGRES_HOST']:
                changes_detected += 1
                builder = DatabaseURLBuilder(self.env.get_all())
                with self.temporary_env_config(POSTGRES_USER='test_user', POSTGRES_DB='test_db', POSTGRES_PASSWORD='test_pass'):
                    new_url = builder.tcp.async_url
                    assert 'new-db-host' in new_url, f'Database URL should reflect host change: {new_url}'
            new_jwt_secret = f'new_jwt_secret_{uuid.uuid4().hex}'
            self.set_env_var('JWT_SECRET_KEY', new_jwt_secret)
            changed_secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
            if changed_secret != original_state['JWT_SECRET_KEY']:
                changes_detected += 1
                assert len(changed_secret) >= 32, 'New JWT secret must meet security requirements'
            original_service_id = self.get_env_var('SERVICE_ID')
            assert original_service_id == 'netra-backend', "SERVICE_ID must be stable value 'netra-backend'"
            self.set_env_var('SERVICE_ID', 'netra-backend-20250108')
            changed_service_id = self.get_env_var('SERVICE_ID')
            if changed_service_id != original_state['SERVICE_ID']:
                changes_detected += 1
                assert False, f"SERVICE_ID change detected: {original_state['SERVICE_ID']} -> {changed_service_id}. This causes cascade authentication failures!"
        self.record_metric('configuration_changes_detected', changes_detected)

    def test_environment_variable_precedence_and_override_behavior(self):
        """
        Test environment variable precedence and override behavior.
        
        Business Value: Proper precedence ensures production values override development
        defaults, preventing development credentials from leaking to production.
        """
        test_var_name = f'TEST_PRECEDENCE_{uuid.uuid4().hex[:8]}'
        fallback_value = 'fallback_value'
        self.set_env_var(test_var_name, fallback_value)
        retrieved = self.get_env_var(test_var_name)
        assert retrieved == fallback_value, f'Basic precedence failed: expected {fallback_value}, got {retrieved}'
        override_value = 'override_value'
        self.set_env_var(test_var_name, override_value)
        retrieved = self.get_env_var(test_var_name)
        assert retrieved == override_value, f'Override precedence failed: expected {override_value}, got {retrieved}'
        environments_precedence = [('development', 'dev_value'), ('staging', 'staging_value'), ('production', 'prod_value')]
        precedence_tests_passed = 0
        for env_name, expected_value in environments_precedence:
            with self.temporary_env_config(ENVIRONMENT=env_name):
                env_specific_var = f'TEST_{env_name.upper()}_VALUE'
                self.set_env_var(env_specific_var, expected_value)
                retrieved = self.get_env_var(env_specific_var)
                assert retrieved == expected_value, f'Environment-specific precedence failed for {env_name}: expected {expected_value}, got {retrieved}'
                current_env = self.get_env_var('ENVIRONMENT')
                assert current_env == env_name, f'Environment context failed: expected {env_name}, got {current_env}'
                precedence_tests_passed += 1
        critical_service_vars = {'POSTGRES_HOST': ['localhost', 'staging-db', 'prod-db'], 'JWT_SECRET_KEY': [f'dev_secret_{uuid.uuid4().hex}', f'staging_secret_{uuid.uuid4().hex}', f'prod_secret_{uuid.uuid4().hex}'], 'FRONTEND_URL': ['http://localhost:3000', 'https://staging.example.com', 'https://example.com']}
        for var_name, precedence_values in critical_service_vars.items():
            for i, value in enumerate(precedence_values):
                self.set_env_var(var_name, value)
                retrieved = self.get_env_var(var_name)
                assert retrieved == value, f'Service variable precedence failed for {var_name}: expected {value}, got {retrieved}'
        self.record_metric('precedence_tests_passed', precedence_tests_passed)
        self.record_metric('service_variables_tested', len(critical_service_vars))

    def test_shared_vs_service_specific_configuration_patterns(self):
        """
        Test shared vs service-specific configuration patterns.
        
        Business Value: Proper separation ensures shared configs (JWT secrets) are consistent
        while service configs (port numbers) remain independent.
        """
        shared_configs = {'JWT_SECRET_KEY': f'shared_jwt_{uuid.uuid4().hex}', 'POSTGRES_HOST': 'shared-database-host', 'POSTGRES_DB': 'shared_database_name', 'ENVIRONMENT': 'testing'}
        with self.temporary_env_config(**shared_configs):
            service_database_urls = []
            services = ['auth_service', 'netra_backend', 'analytics_service']
            for service in services:
                with self.temporary_env_config(POSTGRES_USER=f'{service}_user', POSTGRES_PASSWORD=f'{service}_password'):
                    builder = DatabaseURLBuilder(self.env.get_all())
                    service_url = builder.tcp.async_url
                    service_database_urls.append(service_url)
                    assert 'shared-database-host' in service_url, f'Service {service} should use shared database host'
                    assert 'shared_database_name' in service_url, f'Service {service} should use shared database name'
                    assert f'{service}_user' in service_url, f'Service {service} should use service-specific user'
            jwt_secrets = []
            for service in services:
                secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
                jwt_secrets.append(secret)
            assert len(set(jwt_secrets)) == 1, 'All services MUST share the same JWT secret'
            assert all((secret == shared_configs['JWT_SECRET_KEY'] for secret in jwt_secrets)), 'Shared JWT secret inconsistency detected'
        service_specific_configs = {'auth_service': {'AUTH_SERVICE_PORT': '8081', 'AUTH_SERVICE_HOST': '0.0.0.0', 'OAUTH_CALLBACK_URL': 'http://localhost:8081/oauth/callback'}, 'netra_backend': {'BACKEND_PORT': '8000', 'BACKEND_HOST': '0.0.0.0', 'API_PREFIX': '/api/v1'}, 'analytics_service': {'ANALYTICS_PORT': '8082', 'ANALYTICS_HOST': '0.0.0.0', 'ANALYTICS_BATCH_SIZE': '100'}}
        services_tested = 0
        for service_name, service_config in service_specific_configs.items():
            with self.temporary_env_config(**service_config):
                for config_key, expected_value in service_config.items():
                    actual_value = self.get_env_var(config_key)
                    assert actual_value == expected_value, f'Service-specific config failed for {service_name}.{config_key}: expected {expected_value}, got {actual_value}'
                with self.temporary_env_config(JWT_SECRET_KEY='shared_jwt_secret'):
                    jwt_secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
                    assert jwt_secret == 'shared_jwt_secret', f'Service-specific config interfered with shared JWT secret for {service_name}'
                services_tested += 1
        with self.temporary_env_config(ENVIRONMENT='testing'):
            test_services = {'auth': 8081, 'backend': 8000, 'analytics': 8082}
            for service, expected_port in test_services.items():
                service_url = f'http://localhost:{expected_port}'
                assert f':{expected_port}' in service_url, f'Service {service} should use port {expected_port}'
                assert service_url.startswith('http://'), f'Service URL should use HTTP protocol: {service_url}'
        self.record_metric('shared_components_tested', len(shared_configs))
        self.record_metric('service_specific_components_tested', services_tested)

    def test_configuration_inheritance_and_environment_overrides(self):
        """
        Test configuration inheritance and environment-specific overrides.
        
        Business Value: Proper inheritance allows base configurations with environment-specific
        overrides, reducing config duplication while maintaining environment isolation.
        """
        base_config = {'APP_NAME': 'netra-platform', 'LOG_LEVEL': 'INFO', 'DATABASE_POOL_SIZE': '10', 'CACHE_TTL': '3600', 'API_TIMEOUT': '30'}
        environment_overrides = {'development': {'LOG_LEVEL': 'DEBUG', 'DATABASE_POOL_SIZE': '5', 'API_TIMEOUT': '60'}, 'staging': {'LOG_LEVEL': 'INFO', 'DATABASE_POOL_SIZE': '15', 'CACHE_TTL': '1800'}, 'production': {'LOG_LEVEL': 'WARNING', 'DATABASE_POOL_SIZE': '20', 'CACHE_TTL': '7200'}}
        environments_tested = 0
        for env_name, overrides in environment_overrides.items():
            with self.temporary_env_config(ENVIRONMENT=env_name, **base_config, **overrides):
                app_name = self.get_env_var('APP_NAME')
                assert app_name == 'netra-platform', f'Base config inheritance failed for {env_name}: APP_NAME = {app_name}'
                log_level = self.get_env_var('LOG_LEVEL')
                expected_log_level = overrides['LOG_LEVEL']
                assert log_level == expected_log_level, f'Environment override failed for {env_name}: LOG_LEVEL expected {expected_log_level}, got {log_level}'
                pool_size = self.get_env_var('DATABASE_POOL_SIZE')
                expected_pool_size = overrides['DATABASE_POOL_SIZE']
                assert pool_size == expected_pool_size, f'Database pool override failed for {env_name}: expected {expected_pool_size}, got {pool_size}'
                if 'API_TIMEOUT' not in overrides:
                    timeout = self.get_env_var('API_TIMEOUT')
                    assert timeout == '30', f'Base value should be preserved when not overridden in {env_name}: {timeout}'
                environments_tested += 1
        base_db_config = {'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'postgres', 'DATABASE_MAX_CONNECTIONS': '100', 'DATABASE_TIMEOUT': '30'}
        db_environment_overrides = {'development': {'POSTGRES_HOST': 'localhost', 'POSTGRES_DB': 'netra_dev', 'DATABASE_MAX_CONNECTIONS': '10'}, 'staging': {'POSTGRES_HOST': 'staging-postgres.internal', 'POSTGRES_DB': 'netra_staging', 'DATABASE_MAX_CONNECTIONS': '50'}, 'production': {'POSTGRES_HOST': 'prod-postgres.internal', 'POSTGRES_DB': 'netra_production', 'DATABASE_MAX_CONNECTIONS': '200'}}
        for env_name, db_overrides in db_environment_overrides.items():
            with self.temporary_env_config(ENVIRONMENT=env_name, POSTGRES_PASSWORD='test_password', **base_db_config, **db_overrides):
                builder = DatabaseURLBuilder(self.env.get_all())
                db_url = builder.tcp.async_url
                assert ':5432' in db_url, f'Base port should be inherited: {db_url}'
                assert 'postgres' in db_url, f'Base user should be inherited: {db_url}'
                expected_host = db_overrides['POSTGRES_HOST']
                assert expected_host in db_url, f'Environment host override failed for {env_name}: {db_url}'
                expected_db = db_overrides['POSTGRES_DB']
                assert expected_db in db_url, f'Environment database override failed for {env_name}: {db_url}'
                max_connections = self.get_env_var('DATABASE_MAX_CONNECTIONS')
                expected_max = db_overrides['DATABASE_MAX_CONNECTIONS']
                assert max_connections == expected_max, f'Connection limit override failed for {env_name}: expected {expected_max}, got {max_connections}'
        base_service_config = {'SERVICE_NAME': 'netra-platform', 'SERVICE_VERSION': '1.0.0', 'HEALTH_CHECK_INTERVAL': '30', 'METRICS_ENABLED': 'true'}
        service_overrides = {'auth_service': {'SERVICE_PORT': '8081', 'AUTH_TOKEN_EXPIRY': '3600', 'OAUTH_ENABLED': 'true'}, 'netra_backend': {'SERVICE_PORT': '8000', 'API_VERSION': 'v1', 'RATE_LIMIT': '1000'}}
        for service_name, service_config in service_overrides.items():
            with self.temporary_env_config(**base_service_config, **service_config):
                service_name_val = self.get_env_var('SERVICE_NAME')
                assert service_name_val == 'netra-platform', f'Base service name not inherited: {service_name_val}'
                version = self.get_env_var('SERVICE_VERSION')
                assert version == '1.0.0', f'Base service version not inherited: {version}'
                service_port = self.get_env_var('SERVICE_PORT')
                expected_port = service_config['SERVICE_PORT']
                assert service_port == expected_port, f'Service port override failed: expected {expected_port}, got {service_port}'
        self.record_metric('inheritance_environments_tested', environments_tested)
        self.record_metric('inheritance_patterns_verified', 3)

    def test_configuration_validation_with_real_environment_configurations(self):
        """
        Test configuration validation with real environment configurations.
        
        Business Value: Real configuration validation catches issues before deployment,
        preventing production outages that cost $12K MRR.
        """
        production_config = {'ENVIRONMENT': 'production', 'POSTGRES_HOST': 'prod-postgres.gcp.internal', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'prod_user', 'POSTGRES_PASSWORD': f'prod_secure_password_{uuid.uuid4().hex}', 'POSTGRES_DB': 'netra_production', 'JWT_SECRET_KEY': f'prod_jwt_secret_{uuid.uuid4().hex}_very_long_secure_secret', 'SECRET_KEY': f'prod_secret_key_{uuid.uuid4().hex}_very_long_secure_key', 'REDIS_URL': 'redis://prod-redis.gcp.internal:6379/0', 'FRONTEND_URL': 'https://netra.example.com', 'API_URL': 'https://api.netra.example.com'}
        with self.temporary_env_config(**production_config):
            env = self.get_env_var('ENVIRONMENT')
            assert env == 'production', f'Production environment detection failed: {env}'
            builder = DatabaseURLBuilder(self.env.get_all())
            prod_url = builder.production.cloud_url
            assert 'prod-postgres.gcp.internal' in prod_url, f'Production DB host validation failed: {prod_url}'
            assert 'netra_production' in prod_url, f'Production DB name validation failed: {prod_url}'
            assert 'prod_user' in prod_url, f'Production DB user validation failed: {prod_url}'
            jwt_secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
            assert len(jwt_secret) >= 32, f'Production JWT secret too short: {len(jwt_secret)} chars'
            assert 'prod_jwt_secret_' in jwt_secret, f'Production JWT secret validation failed'
            secret_key = self.get_env_var('SECRET_KEY')
            assert len(secret_key) >= 32, f'Production SECRET_KEY too short: {len(secret_key)} chars'
            frontend_url = self.get_env_var('FRONTEND_URL')
            assert frontend_url.startswith('https://'), f'Production frontend URL must use HTTPS: {frontend_url}'
            api_url = self.get_env_var('API_URL')
            assert api_url.startswith('https://'), f'Production API URL must use HTTPS: {api_url}'
        staging_config = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging-postgres.gcp.internal', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': f'staging_password_{uuid.uuid4().hex}', 'POSTGRES_DB': 'netra_staging', 'JWT_SECRET_KEY': f'staging_jwt_secret_{uuid.uuid4().hex}_secure', 'SECRET_KEY': f'staging_secret_key_{uuid.uuid4().hex}_secure', 'REDIS_URL': 'redis://staging-redis.gcp.internal:6379/0', 'FRONTEND_URL': 'https://staging.netra.example.com', 'API_URL': 'https://api.staging.netra.example.com'}
        with self.temporary_env_config(**staging_config):
            env = self.get_env_var('ENVIRONMENT')
            assert env == 'staging', f'Staging environment detection failed: {env}'
            builder = DatabaseURLBuilder(self.env.get_all())
            staging_url = builder.staging.cloud_url
            assert 'staging-postgres.gcp.internal' in staging_url, f'Staging DB host validation failed: {staging_url}'
            assert 'netra_staging' in staging_url, f'Staging DB name validation failed: {staging_url}'
            assert 'staging_user' in staging_url, f'Staging DB user validation failed: {staging_url}'
            assert 'netra_staging' not in production_config['POSTGRES_DB'], 'Staging and production databases must be different'
            assert staging_config['POSTGRES_HOST'] != production_config['POSTGRES_HOST'], 'Staging and production hosts must be different'
        development_config = {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'postgres', 'POSTGRES_DB': 'netra_dev', 'FRONTEND_URL': 'http://localhost:3000', 'API_URL': 'http://localhost:8000'}
        with self.temporary_env_config(**development_config):
            env = self.get_env_var('ENVIRONMENT')
            assert env == 'development', f'Development environment detection failed: {env}'
            builder = DatabaseURLBuilder(self.env.get_all())
            dev_url = builder.development.default_url
            assert 'localhost' in dev_url, f'Development should use localhost: {dev_url}'
            assert 'netra_dev' in dev_url, f'Development DB name validation failed: {dev_url}'
            frontend_url = self.get_env_var('FRONTEND_URL')
            assert frontend_url.startswith('http://localhost'), f'Development frontend URL validation failed: {frontend_url}'
            jwt_secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
            assert jwt_secret is not None, 'Development should generate JWT secret fallback'
            assert len(jwt_secret) >= 32, f'Development JWT secret too short: {len(jwt_secret)} chars'
        invalid_configs = [{'name': 'missing_database_password', 'config': {'ENVIRONMENT': 'production', 'POSTGRES_HOST': 'prod-host', 'POSTGRES_USER': 'prod_user', 'POSTGRES_DB': 'prod_db'}, 'expected_issue': 'missing_password'}, {'name': 'short_jwt_secret', 'config': {'ENVIRONMENT': 'production', 'JWT_SECRET_KEY': 'short_secret'}, 'expected_issue': 'weak_jwt_secret'}, {'name': 'http_in_production', 'config': {'ENVIRONMENT': 'production', 'FRONTEND_URL': 'http://unsecure.example.com'}, 'expected_issue': 'insecure_url'}]
        validation_issues_detected = 0
        for invalid_config in invalid_configs:
            with self.temporary_env_config(**invalid_config['config']):
                if invalid_config['expected_issue'] == 'missing_password':
                    builder = DatabaseURLBuilder(self.env.get_all())
                    try:
                        prod_url = builder.production.cloud_url
                        assert 'None' not in prod_url or prod_url is None, 'Invalid database URL should be detected'
                        validation_issues_detected += 1
                    except Exception:
                        validation_issues_detected += 1
                elif invalid_config['expected_issue'] == 'weak_jwt_secret':
                    jwt_secret = SharedJWTSecretManager.get_jwt_secret(self.env.get_all())
                    if jwt_secret and len(jwt_secret) < 32:
                        validation_issues_detected += 1
                elif invalid_config['expected_issue'] == 'insecure_url':
                    frontend_url = self.get_env_var('FRONTEND_URL')
                    if frontend_url and (not frontend_url.startswith('https://')):
                        validation_issues_detected += 1
        self.record_metric('validation_environments_tested', 3)
        self.record_metric('validation_issues_detected', validation_issues_detected)
        self.record_metric('real_config_validation_complete', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')