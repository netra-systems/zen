"""Integration test for DatabaseURLBuilder across environments."""

import pytest
import os
from test_framework.database.test_database_manager import TestDatabaseManager

from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment
from shared.isolated_environment import get_env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.environment,
]


env = get_env()
class TestDatabaseURLBuilderIntegration:
    """Test DatabaseURLBuilder integration with real environment configurations."""
    
    def test_development_environment_url_resolution(self):
        """Test URL resolution in development environment."""
        # This should pass - development has defaults
        mock_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_dev',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'postgres',
}
        
        builder = DatabaseURLBuilder(mock_env)
        url = builder.get_url_for_environment()
        
        assert url is not None
        assert 'postgresql+asyncpg' in url
        assert 'localhost' in url
        assert 'netra_dev' in url
        
    def test_staging_environment_ssl_requirement(self):
        """Test that staging environment requires SSL configuration."""
        # This test should initially fail - expecting SSL enforcement
        mock_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-db.example.com',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password',
}
        
        builder = DatabaseURLBuilder(mock_env)
        url = builder.get_url_for_environment()
        
        # Should enforce SSL in staging
        assert url is not None
        assert 'sslmode = require' in url or 'ssl = require' in url
        
    def test_production_credential_validation(self):
        """Test production environment credential validation."""
        # This should fail initially - no credential validation
        mock_env = {
            'ENVIRONMENT': 'production',
            'POSTGRES_HOST': 'localhost',  # Invalid for production
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_prod',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'password'  # Weak password,
}
        
        builder = DatabaseURLBuilder(mock_env)
        is_valid, error = builder.validate()
        
        # Should reject localhost and weak passwords in production
        assert not is_valid
        assert 'localhost' in error.lower() or 'password' in error.lower()
        
    def test_cloud_sql_url_format_validation(self):
        """Test Cloud SQL URL format validation."""
        # This should initially fail - incomplete Cloud SQL validation
        mock_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': '/cloudsql/invalid-format',  # Invalid format
            'POSTGRES_DB': 'netra_staging',
            'POSTGRES_USER': 'cloud_user',
            'POSTGRES_PASSWORD': 'cloud_password',
}
        
        builder = DatabaseURLBuilder(mock_env)
        is_valid, error = builder.validate()
        
        # Should validate Cloud SQL format properly
        assert not is_valid
        assert 'cloud sql' in error.lower() or 'format' in error.lower()
        
    def test_environment_variable_integration(self):
        """Test integration with actual environment variables."""
        # This test checks real environment integration
        env = IsolatedEnvironment()
        
        # Get current environment type
        current_env = env.get('ENVIRONMENT', 'development')
        
        # Create builder with OS environment
        builder = DatabaseURLBuilder(env.get_all())
        url = builder.get_url_for_environment()
        
        # Should always be able to generate some URL
        assert url is not None
        
        # Log the configuration for debugging
        debug_info = builder.debug_info()
        print(f"Environment: {current_env}")
        print(f"Debug info: {debug_info}")
        print(f"Safe log message: {builder.get_safe_log_message()}")
        
    def test_url_normalization_consistency(self):
        """Test URL normalization is consistent across environments."""
        # This should initially fail - no comprehensive normalization
        test_urls = [
            "postgres://user:pass@host:5432/db",
            "postgresql://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db?sslmode = require",
        ]
        
        for url in test_urls:
            normalized = DatabaseURLBuilder.normalize_postgres_url(url)
            
            # Should normalize to postgresql://
            assert normalized.startswith('postgresql://') or normalized.startswith('postgresql+')
            
            # Should not have old postgres:// prefix
            assert not normalized.startswith('postgres://')
            
    def test_driver_specific_formatting(self):
        """Test driver-specific URL formatting."""
        # This should initially fail - incomplete driver formatting
        base_url = "postgresql://user:pass@host:5432/db?sslmode = require"
        
        # Test asyncpg formatting
        asyncpg_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'asyncpg')
        assert asyncpg_url.startswith('postgresql+asyncpg://')
        
        # asyncpg should use ssl =  not sslmode = 
        if 'ssl' in asyncpg_url:
            assert 'ssl==' in asyncpg_url
            assert 'sslmode = ' not in asyncpg_url
        
        # Test psycopg formatting  
        psycopg_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'psycopg')
        assert psycopg_url.startswith('postgresql+psycopg://')
        
        # psycopg should use sslmode = 
        if 'ssl' in psycopg_url:
            assert 'sslmode = ' in psycopg_url