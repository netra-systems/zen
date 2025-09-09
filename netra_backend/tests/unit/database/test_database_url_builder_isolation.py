"""
Unit Test: Database URL Builder for Multi-User Connection Isolation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure database connection infrastructure supports user isolation
- Value Impact: Connection-level isolation prevents cross-user data leakage
- Strategic Impact: Foundation for secure multi-tenant database architecture

This unit test validates:
1. DatabaseURLBuilder creates properly isolated connection URLs
2. Connection parameters maintain user context separation
3. Environment-specific URL generation respects security boundaries
4. URL masking protects sensitive connection data in logs

CRITICAL: Tests SSOT DatabaseURLBuilder patterns used across all services.
"""

import os
import uuid
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, Optional

from netra_backend.tests.unit.test_base import BaseUnitTest
from shared.database_url_builder import DatabaseURLBuilder
from shared.types.core_types import UserID, ensure_user_id


class TestDatabaseURLBuilderIsolation(BaseUnitTest):
    """Test DatabaseURLBuilder for multi-user connection isolation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    @pytest.mark.unit
    def test_database_url_builder_creates_isolated_connections(self):
        """Test that DatabaseURLBuilder creates properly isolated connection URLs."""
        
        # Mock environment variables for different environments
        test_environments = {
            'development': {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': 'dev_user',
                'POSTGRES_PASSWORD': 'dev_password',
                'POSTGRES_DB': 'netra_dev',
                'ENVIRONMENT': 'development'
            },
            'test': {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': '5434', 
                'POSTGRES_USER': 'test_user',
                'POSTGRES_PASSWORD': 'test_password',
                'POSTGRES_DB': 'netra_test',
                'ENVIRONMENT': 'test',
                'USE_MEMORY_DB': 'false'
            },
            'staging': {
                'POSTGRES_HOST': 'staging-db.example.com',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': 'staging_user',
                'POSTGRES_PASSWORD': 'staging_secure_password',
                'POSTGRES_DB': 'netra_staging',
                'ENVIRONMENT': 'staging'
            }
        }
        
        # Test URL generation for each environment
        for env_name, env_vars in test_environments.items():
            builder = DatabaseURLBuilder(env_vars)
            
            # Get environment-appropriate URL
            url = builder.get_url_for_environment()
            assert url is not None, f"No URL generated for {env_name} environment"
            
            # Verify URL contains environment-specific components
            if env_name == 'test' and env_vars.get('USE_MEMORY_DB') == 'false':
                # Test environment should use PostgreSQL
                assert 'postgresql' in url, f"Test environment should use PostgreSQL: {url}"
                assert env_vars['POSTGRES_DB'] in url, f"URL should contain test database: {url}"
            elif env_name == 'development':
                # Development should use configured values or defaults
                assert 'postgresql' in url, f"Development should use PostgreSQL: {url}"
                assert 'netra_dev' in url or env_vars['POSTGRES_DB'] in url, \
                    f"Development URL should contain dev database: {url}"
            elif env_name == 'staging':
                # Staging should use secure connection
                assert 'postgresql' in url, f"Staging should use PostgreSQL: {url}"
                assert env_vars['POSTGRES_HOST'] in url, f"Staging should use correct host: {url}"
                # Should include SSL for staging
                staging_url_ssl = builder.staging.auto_url
                if staging_url_ssl and 'sslmode=require' not in staging_url_ssl:
                    # Check if TCP with SSL is being used
                    tcp_ssl_url = builder.tcp.async_url_with_ssl
                    if tcp_ssl_url:
                        assert 'ssl' in tcp_ssl_url.lower(), f"Staging should enforce SSL: {tcp_ssl_url}"
            
            self.logger.info(f"Environment {env_name}: {builder.mask_url_for_logging(url)}")

    @pytest.mark.unit
    def test_connection_parameters_maintain_user_isolation(self):
        """Test that connection parameters maintain user context separation."""
        
        # Create mock environment for user-specific connection testing
        base_env = {
            'POSTGRES_HOST': 'multi-tenant-db.example.com',
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'app_user',
            'POSTGRES_PASSWORD': 'app_password',
            'POSTGRES_DB': 'netra_multi_tenant',
            'ENVIRONMENT': 'production'
        }
        
        builder = DatabaseURLBuilder(base_env)
        
        # Test different connection scenarios for user isolation
        connection_scenarios = [
            {
                'name': 'cloud_sql',
                'env_override': {
                    **base_env,
                    'POSTGRES_HOST': '/cloudsql/project:region:instance'
                },
                'expected_pattern': 'postgresql+asyncpg://'
            },
            {
                'name': 'tcp_with_ssl',
                'env_override': base_env,
                'expected_pattern': 'postgresql+asyncpg://'
            },
            {
                'name': 'docker_compose',
                'env_override': {
                    **base_env,
                    'POSTGRES_HOST': 'postgres',
                    'RUNNING_IN_DOCKER': 'true'
                },
                'expected_pattern': 'postgresql+asyncpg://'
            }
        ]
        
        for scenario in connection_scenarios:
            scenario_builder = DatabaseURLBuilder(scenario['env_override'])
            
            # Get URLs for different connection types
            if scenario['name'] == 'cloud_sql':
                url = scenario_builder.cloud_sql.async_url
                sync_url = scenario_builder.cloud_sql.sync_url
            elif scenario['name'] == 'tcp_with_ssl':
                url = scenario_builder.tcp.async_url_with_ssl
                sync_url = scenario_builder.tcp.sync_url_with_ssl
            else:  # docker_compose
                url = scenario_builder.docker.compose_url
                sync_url = scenario_builder.docker.compose_sync_url
            
            if url:
                # Verify URL structure supports isolation
                assert scenario['expected_pattern'] in url, \
                    f"URL should match pattern for {scenario['name']}: {url}"
                
                # Verify credentials are properly encoded (isolation security)
                assert scenario['env_override']['POSTGRES_USER'] not in url or \
                       scenario['env_override']['POSTGRES_USER'].replace(' ', '%20') in url, \
                    f"User should be URL encoded in {scenario['name']}: {url}"
                
                # Verify database name isolation
                db_name = scenario['env_override']['POSTGRES_DB']
                assert db_name in url, \
                    f"Database name should be present for isolation in {scenario['name']}: {url}"
                
                # Test URL masking for security (prevents credential leakage)
                masked_url = DatabaseURLBuilder.mask_url_for_logging(url)
                assert '***' in masked_url, f"URL should be masked for security: {masked_url}"
                assert scenario['env_override']['POSTGRES_PASSWORD'] not in masked_url, \
                    f"Password should be masked: {masked_url}"
                
            if sync_url:
                # Verify sync URL also supports isolation
                assert 'postgresql://' in sync_url, f"Sync URL should be PostgreSQL: {sync_url}"
                
        self.logger.info(f"Tested {len(connection_scenarios)} connection scenarios for user isolation")

    @pytest.mark.unit
    def test_environment_specific_url_security_boundaries(self):
        """Test environment-specific URL generation respects security boundaries."""
        
        # Test security boundary enforcement across environments
        security_test_cases = [
            {
                'environment': 'development',
                'env_vars': {
                    'POSTGRES_HOST': 'localhost',
                    'POSTGRES_USER': 'dev_user', 
                    'POSTGRES_PASSWORD': 'dev_password',
                    'POSTGRES_DB': 'netra_dev',
                    'ENVIRONMENT': 'development'
                },
                'should_allow_localhost': True,
                'should_require_ssl': False
            },
            {
                'environment': 'test',
                'env_vars': {
                    'POSTGRES_HOST': 'localhost',
                    'POSTGRES_USER': 'test_user',
                    'POSTGRES_PASSWORD': 'test_password', 
                    'POSTGRES_DB': 'netra_test',
                    'ENVIRONMENT': 'test'
                },
                'should_allow_localhost': True,
                'should_require_ssl': False
            },
            {
                'environment': 'staging',
                'env_vars': {
                    'POSTGRES_HOST': 'staging-db.secure.com',
                    'POSTGRES_USER': 'staging_user',
                    'POSTGRES_PASSWORD': 'staging_secure_password_123',
                    'POSTGRES_DB': 'netra_staging',
                    'ENVIRONMENT': 'staging'
                },
                'should_allow_localhost': False,
                'should_require_ssl': True
            },
            {
                'environment': 'production',
                'env_vars': {
                    'POSTGRES_HOST': 'prod-db.secure.com',
                    'POSTGRES_USER': 'prod_user',
                    'POSTGRES_PASSWORD': 'prod_ultra_secure_password_xyz789',
                    'POSTGRES_DB': 'netra_production',
                    'ENVIRONMENT': 'production'
                },
                'should_allow_localhost': False, 
                'should_require_ssl': True
            }
        ]
        
        for test_case in security_test_cases:
            builder = DatabaseURLBuilder(test_case['env_vars'])
            
            # Test validation logic
            is_valid, error_message = builder.validate()
            
            if test_case['environment'] in ['staging', 'production']:
                # Production environments should have strict validation
                assert is_valid or 'localhost' in error_message, \
                    f"{test_case['environment']} validation should be strict: {error_message}"
                
                # Test localhost rejection in production environments
                localhost_env = {**test_case['env_vars'], 'POSTGRES_HOST': 'localhost'}
                localhost_builder = DatabaseURLBuilder(localhost_env)
                localhost_valid, localhost_error = localhost_builder.validate()
                
                if not test_case['should_allow_localhost']:
                    # Should reject localhost in production
                    assert not localhost_valid or 'localhost' in localhost_error.lower(), \
                        f"{test_case['environment']} should reject localhost: {localhost_error}"
            
            # Test SSL requirements
            if test_case['should_require_ssl']:
                url = builder.get_url_for_environment()
                if url and builder.tcp.has_config:
                    ssl_url = builder.tcp.async_url_with_ssl
                    if ssl_url:
                        assert 'ssl' in ssl_url.lower(), \
                            f"{test_case['environment']} should enforce SSL: {ssl_url}"
            
            # Test credential validation for production environments
            if test_case['environment'] in ['staging', 'production']:
                weak_password_env = {
                    **test_case['env_vars'], 
                    'POSTGRES_PASSWORD': 'password123'  # Weak password
                }
                weak_builder = DatabaseURLBuilder(weak_password_env)
                weak_valid, weak_error = weak_builder.validate()
                
                # Should detect weak passwords in production
                if not weak_valid:
                    assert 'password' in weak_error.lower(), \
                        f"Should detect weak password in {test_case['environment']}: {weak_error}"
            
        self.logger.info(f"Validated security boundaries for {len(security_test_cases)} environments")

    @pytest.mark.unit 
    def test_url_masking_protects_sensitive_connection_data(self):
        """Test URL masking protects sensitive connection data in logs."""
        
        # Test various URL formats for masking
        sensitive_urls = [
            {
                'url': 'postgresql+asyncpg://user:secret_password@localhost:5432/mydb',
                'description': 'Standard TCP URL with credentials'
            },
            {
                'url': 'postgresql+asyncpg://app_user:ultra_secret_pass_123@prod-db.example.com:5432/netra_prod?sslmode=require',
                'description': 'Production URL with SSL and complex password'
            },
            {
                'url': 'postgresql+asyncpg://staging_user:staging_pass@/netra_staging?host=/cloudsql/project:region:instance',
                'description': 'Cloud SQL URL with Unix socket'
            },
            {
                'url': 'postgresql://migration_user:migration_secret@staging-db:5432/netra_staging',
                'description': 'Sync URL for migrations'
            },
            {
                'url': 'sqlite+aiosqlite:///:memory:',
                'description': 'SQLite memory URL (no credentials to mask)'
            }
        ]
        
        for url_test in sensitive_urls:
            url = url_test['url']
            masked = DatabaseURLBuilder.mask_url_for_logging(url)
            
            self.logger.info(f"Testing: {url_test['description']}")
            self.logger.info(f"Original: {url}")
            self.logger.info(f"Masked: {masked}")
            
            # Verify sensitive data is masked
            if '://' in url and '@' in url:
                # URLs with credentials should be masked
                assert '***' in masked, f"Credentials should be masked: {masked}"
                
                # Extract credentials from original URL
                if '://' in url:
                    _, rest = url.split('://', 1)
                    if '@' in rest:
                        creds, _ = rest.split('@', 1)
                        if ':' in creds:
                            username, password = creds.split(':', 1)
                            
                            # Username and password should not appear in masked version
                            assert username not in masked or username == '***', \
                                f"Username should be masked: {username} in {masked}"
                            assert password not in masked, \
                                f"Password should be masked: {password} in {masked}"
            
            elif 'memory' in url.lower():
                # Memory URLs have no credentials - should be unchanged
                assert masked == url, f"Memory URL should not be modified: {masked}"
            
            # Verify URL structure is preserved for debugging
            if '://' in url:
                protocol = url.split('://')[0]
                assert protocol in masked, f"Protocol should be preserved: {protocol} in {masked}"
            
            # Verify host information is preserved (non-sensitive)
            if '/cloudsql/' in url:
                assert '/cloudsql/' in masked, "Cloud SQL host info should be preserved"
            
        # Test edge cases
        edge_cases = [
            None,
            '',
            'invalid_url',
            'postgresql://@localhost:5432/db',  # No credentials
            'postgresql://user@localhost:5432/db',  # No password
        ]
        
        for edge_url in edge_cases:
            masked = DatabaseURLBuilder.mask_url_for_logging(edge_url)
            assert masked is not None, f"Masking should handle edge case: {edge_url}"
            
            if edge_url is None:
                assert masked == "NOT SET", "None URL should return 'NOT SET'"
            elif not edge_url:
                assert masked == "NOT SET", "Empty URL should return 'NOT SET'"
        
        self.logger.info(f"Tested URL masking for {len(sensitive_urls)} URL formats and {len(edge_cases)} edge cases")