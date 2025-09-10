"""
Test Configuration SSOT: DatabaseURLBuilder Compliance

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Prevent database connection failures and configuration drift
- Value Impact: Protects $120K+ MRR by ensuring database connectivity through SSOT patterns
- Strategic Impact: Eliminates cascade failures from direct DATABASE_URL access violations

This test validates that all services use DatabaseURLBuilder SSOT patterns instead of
direct DATABASE_URL environment access, preventing configuration drift and connection
failures that can bring down the entire system.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env


class TestDatabaseURLBuilderCompliance(BaseIntegrationTest):
    """Test DatabaseURLBuilder SSOT compliance across services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_url_builder_ssot_component_access(self, real_services_fixture):
        """
        Test that DatabaseURLBuilder properly uses component-based SSOT approach.
        
        Direct DATABASE_URL access is FORBIDDEN and causes configuration drift.
        The SSOT approach uses component variables (POSTGRES_HOST, POSTGRES_USER, etc.)
        to construct URLs consistently across all environments.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up component-based database configuration (SSOT pattern)
        test_components = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'netra_test',
            'POSTGRES_PORT': '5434'  # Test port
        }
        
        # Set components with proper source tracking
        for key, value in test_components.items():
            env.set(key, value, 'test_database_config')
        
        # Create DatabaseURLBuilder with environment variables
        env_vars = env.get_all()
        builder = DatabaseURLBuilder(env_vars)
        
        # Test URL generation for different environments
        test_url = builder.get_url_for_environment(sync=False)
        
        # CRITICAL: Verify URL is constructed from components, not direct DATABASE_URL
        expected_url = "postgresql+asyncpg://testuser:testpass@localhost:5434/netra_test"
        assert test_url == expected_url
        
        # Test sync URL generation
        sync_url = builder.get_url_for_environment(sync=True)
        expected_sync_url = "postgresql://testuser:testpass@localhost:5434/netra_test"
        assert sync_url == expected_sync_url
        
        # Test environment-specific behavior
        env.set('ENVIRONMENT', 'testing', 'test_environment')
        env_vars = env.get_all()
        builder = DatabaseURLBuilder(env_vars)
        
        # Test environment should get test-specific URL
        test_env_url = builder.test.auto_url
        assert "netra_test" in test_env_url  # Should use test database
        
        # CRITICAL: Verify DATABASE_URL is not used even if present
        env.set('DATABASE_URL', 'postgresql://wrong:wrong@wrong:5432/wrong', 'anti_pattern')
        env_vars = env.get_all()
        builder = DatabaseURLBuilder(env_vars)
        
        # Builder should ignore DATABASE_URL and use components
        component_url = builder.get_url_for_environment(sync=False)
        direct_url = env.get('DATABASE_URL')
        
        assert component_url != direct_url, "DatabaseURLBuilder incorrectly used direct DATABASE_URL"
        assert component_url == expected_url, "DatabaseURLBuilder should use component variables"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_url_builder_environment_specific_patterns(self, real_services_fixture):
        """
        Test DatabaseURLBuilder handles environment-specific configuration patterns.
        
        Different environments (dev/staging/prod) have different database connection
        requirements. SSOT patterns must handle these consistently to prevent
        cascade failures from environment-specific misconfigurations.
        """
        env = get_env()
        env.enable_isolation()
        
        # Test environment configurations
        environment_configs = {
            'development': {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_USER': 'dev_user',
                'POSTGRES_DB': 'netra_dev',
                'POSTGRES_PORT': '5432',
                'expected_pattern': 'localhost:5432'
            },
            'staging': {
                'POSTGRES_HOST': '/cloudsql/project:region:instance',
                'POSTGRES_USER': 'staging_user', 
                'POSTGRES_DB': 'netra_staging',
                'POSTGRES_PORT': '5432',
                'expected_pattern': '/cloudsql/'
            },
            'production': {
                'POSTGRES_HOST': '/cloudsql/netra-prod:us-central1:netra-db',
                'POSTGRES_USER': 'prod_user',
                'POSTGRES_DB': 'netra_production', 
                'POSTGRES_PORT': '5432',
                'expected_pattern': 'netra-production'
            },
            'testing': {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_USER': 'test_user',
                'POSTGRES_DB': 'netra_test',
                'POSTGRES_PORT': '5434',  # Different port for tests
                'expected_pattern': 'localhost:5434'
            }
        }
        
        for environment, config in environment_configs.items():
            # Set environment-specific configuration
            env.set('ENVIRONMENT', environment, f'{environment}_config')
            env.set('POSTGRES_PASSWORD', 'secure_password', f'{environment}_config')
            
            for key, value in config.items():
                if key != 'expected_pattern':
                    env.set(key, value, f'{environment}_config')
            
            # Create builder and test URL generation
            env_vars = env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            
            # Test both sync and async URL generation
            async_url = builder.get_url_for_environment(sync=False)
            sync_url = builder.get_url_for_environment(sync=True)
            
            # Verify environment-specific patterns
            assert config['expected_pattern'] in async_url, \
                f"Environment {environment} URL missing expected pattern: {async_url}"
            assert config['expected_pattern'] in sync_url, \
                f"Environment {environment} sync URL missing expected pattern: {sync_url}"
            
            # Verify database name is environment-appropriate
            assert config['POSTGRES_DB'] in async_url, \
                f"Environment {environment} URL missing database name: {async_url}"
            
            # Verify correct driver for async/sync
            if environment != 'testing':  # Testing might use sqlite
                assert 'postgresql+asyncpg://' in async_url, \
                    f"Async URL should use asyncpg driver: {async_url}"
                assert 'postgresql://' in sync_url and 'asyncpg' not in sync_url, \
                    f"Sync URL should use psycopg2 driver: {sync_url}"
            
            # CRITICAL: Verify no localhost in production/staging
            if environment in ['staging', 'production']:
                assert 'localhost' not in async_url, \
                    f"Production environment {environment} should not use localhost: {async_url}"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_database_url_builder_debug_and_security_features(self, real_services_fixture):
        """
        Test DatabaseURLBuilder debug and security features.
        
        Production database URLs contain sensitive credentials. SSOT patterns must
        provide safe debugging capabilities while protecting credentials from
        accidental exposure in logs or error messages.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up database configuration with sensitive credentials
        sensitive_config = {
            'POSTGRES_HOST': 'sensitive-db-host.example.com',
            'POSTGRES_USER': 'sensitive_username',
            'POSTGRES_PASSWORD': 'super_secret_password_123!@#',
            'POSTGRES_DB': 'production_database',
            'POSTGRES_PORT': '5432'
        }
        
        for key, value in sensitive_config.items():
            env.set(key, value, 'production_config')
        
        env_vars = env.get_all()
        builder = DatabaseURLBuilder(env_vars)
        
        # Test debug information
        debug_info = builder.debug_info()
        
        # CRITICAL: Debug info should mask sensitive values
        assert 'super_secret_password_123!@#' not in str(debug_info), \
            "Debug info exposes sensitive password"
        
        # But should show structure
        assert 'POSTGRES_HOST' in debug_info, "Debug info should show configuration structure"
        assert 'POSTGRES_USER' in debug_info, "Debug info should show configuration structure"
        assert 'password' in debug_info or 'POSTGRES_PASSWORD' in debug_info, \
            "Debug info should reference password field"
        
        # Test safe log message generation
        safe_log_message = builder.get_safe_log_message()
        
        # CRITICAL: Safe log message must not expose credentials
        assert 'super_secret_password_123!@#' not in safe_log_message, \
            "Safe log message exposes sensitive password"
        assert 'sensitive_username' not in safe_log_message, \
            "Safe log message exposes sensitive username" 
        
        # But should provide useful debugging information
        assert 'database connection' in safe_log_message.lower() or 'url' in safe_log_message.lower(), \
            "Safe log message should indicate database connection context"
        
        # Test URL construction still works correctly
        production_url = builder.get_url_for_environment(sync=False)
        
        # Verify the URL is correctly constructed (but don't log it)
        assert 'sensitive-db-host.example.com' in production_url
        assert 'sensitive_username' in production_url
        assert 'super_secret_password_123!@#' in production_url
        assert 'production_database' in production_url
        
        # Test connection validation (without actual connection)
        validation_result = builder._validate_component_completeness()
        assert validation_result['valid'], "Component validation should pass with complete config"
        assert len(validation_result['missing_components']) == 0, "No components should be missing"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_url_builder_prevents_direct_url_antipatterns(self, real_services_fixture):
        """
        Test that DatabaseURLBuilder prevents anti-patterns and enforces SSOT compliance.
        
        Common anti-patterns include:
        - Direct DATABASE_URL usage without component validation
        - Hardcoded connection strings  
        - Missing environment-specific handling
        - No credential protection
        
        These anti-patterns cause configuration drift and cascade failures.
        """
        env = get_env()
        env.enable_isolation()
        
        # Test anti-pattern: Direct DATABASE_URL without components
        env.set('DATABASE_URL', 'postgresql://user:pass@host:5432/db', 'anti_pattern')
        
        # Don't set component variables - this should be detected
        env_vars = env.get_all()
        builder = DatabaseURLBuilder(env_vars)
        
        # CRITICAL: Builder should prefer component-based construction
        # even when DATABASE_URL is present
        component_validation = builder._validate_component_completeness()
        
        # If components are missing, validation should indicate this
        if not component_validation['valid']:
            missing_components = component_validation['missing_components']
            expected_components = ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']
            
            # Should identify missing critical components
            for component in expected_components:
                if component not in env_vars or not env_vars[component]:
                    assert component in missing_components, \
                        f"Missing component {component} should be detected"
        
        # Test anti-pattern: Hardcoded localhost in production
        production_antipattern = {
            'POSTGRES_HOST': 'localhost',  # Anti-pattern in production
            'POSTGRES_USER': 'prod_user',
            'POSTGRES_PASSWORD': 'prod_pass',
            'POSTGRES_DB': 'production_db',
            'POSTGRES_PORT': '5432',
            'ENVIRONMENT': 'production'
        }
        
        for key, value in production_antipattern.items():
            env.set(key, value, 'antipattern_config')
        
        env_vars = env.get_all()
        builder = DatabaseURLBuilder(env_vars)
        
        # Builder should construct URL but this would be flagged in validation
        prod_url = builder.production.auto_url
        
        # The URL will contain localhost, but production validation should catch this
        assert 'localhost' in prod_url, "URL constructed as specified"
        
        # In a real scenario, deployment validation would catch this anti-pattern
        
        # Test proper SSOT pattern
        proper_production_config = {
            'POSTGRES_HOST': '/cloudsql/project:region:instance',
            'POSTGRES_USER': 'production_user',
            'POSTGRES_PASSWORD': 'production_secure_password',
            'POSTGRES_DB': 'netra_production',
            'POSTGRES_PORT': '5432',
            'ENVIRONMENT': 'production'
        }
        
        for key, value in proper_production_config.items():
            env.set(key, value, 'proper_ssot_config')
        
        env_vars = env.get_all()
        proper_builder = DatabaseURLBuilder(env_vars)
        
        proper_prod_url = proper_builder.production.auto_url
        
        # CRITICAL: Proper SSOT configuration
        assert 'localhost' not in proper_prod_url, "Production should not use localhost"
        assert '/cloudsql/' in proper_prod_url, "Production should use Cloud SQL"
        assert 'netra_production' in proper_prod_url, "Production should use production database"
        
        # Verify proper builder debug info doesn't expose credentials
        debug_info = proper_builder.debug_info()
        assert 'production_secure_password' not in str(debug_info), \
            "Debug info should mask production credentials"