"""Test SSL URL generation for database connections."""

import pytest
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment

pytestmark = [
    pytest.mark.integration,
    pytest.mark.database
]


class TestDatabaseSSLUrlGeneration:
    """Test SSL URL generation functionality."""
    
    def test_staging_url_includes_ssl_requirement(self):
        """Test that staging URLs include SSL requirements."""
        mock_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-db.example.com',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_staging',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password'
        }
        
        builder = DatabaseURLBuilder(mock_env)
        staging_url = builder.staging.auto_url
        
        # Staging should automatically include SSL
        assert staging_url is not None
        assert 'staging-db.example.com' in staging_url
        assert ('ssl=require' in staging_url or 'sslmode=require' in staging_url), f"SSL not found in URL: {staging_url}"
        
    def test_production_url_includes_ssl_requirement(self):
        """Test that production URLs include SSL requirements."""
        mock_env = {
            'ENVIRONMENT': 'production',
            'POSTGRES_HOST': 'prod-db.example.com',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_prod',
            'POSTGRES_USER': 'prod_user',
            'POSTGRES_PASSWORD': 'secure_production_password'
        }
        
        builder = DatabaseURLBuilder(mock_env)
        production_url = builder.production.auto_url
        
        # Production should automatically include SSL
        assert production_url is not None
        assert 'prod-db.example.com' in production_url
        assert ('ssl=require' in production_url or 'sslmode=require' in production_url), f"SSL not found in URL: {production_url}"
        
    def test_cloud_sql_urls_do_not_need_ssl_params(self):
        """Test that Cloud SQL URLs don't include SSL parameters (Unix sockets)."""
        mock_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': '/cloudsql/project-id:region:instance-name',
            'POSTGRES_DB': 'netra_staging',
            'POSTGRES_USER': 'cloud_user',
            'POSTGRES_PASSWORD': 'cloud_password'
        }
        
        builder = DatabaseURLBuilder(mock_env)
        cloud_sql_url = builder.cloud_sql.async_url
        
        # Cloud SQL uses Unix sockets, no SSL params needed
        assert cloud_sql_url is not None
        assert '/cloudsql/' in cloud_sql_url
        assert 'ssl=' not in cloud_sql_url
        assert 'sslmode=' not in cloud_sql_url
        
    def test_tcp_ssl_url_generation(self):
        """Test explicit TCP SSL URL generation."""
        mock_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_dev',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'postgres'
        }
        
        builder = DatabaseURLBuilder(mock_env)
        
        # Test both SSL and non-SSL URLs
        regular_url = builder.tcp.async_url
        ssl_url = builder.tcp.async_url_with_ssl
        
        assert regular_url is not None
        assert ssl_url is not None
        
        # SSL URL should have SSL parameter
        assert ('ssl=require' in ssl_url or 'sslmode=require' in ssl_url), f"SSL not found in URL: {ssl_url}"
        
        # Regular URL should not have SSL parameter
        assert 'ssl=' not in regular_url
        assert 'sslmode=' not in regular_url
        
    def test_url_driver_ssl_parameter_differences(self):
        """Test that different drivers handle SSL parameters correctly."""
        base_url = "postgresql://user:pass@host:5432/db?sslmode=require"
        
        # asyncpg should convert sslmode to ssl
        asyncpg_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'asyncpg')
        assert 'postgresql+asyncpg://' in asyncpg_url
        assert 'ssl=require' in asyncpg_url
        assert 'sslmode=require' not in asyncpg_url
        
        # psycopg should keep sslmode
        psycopg_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'psycopg')
        assert 'postgresql+psycopg://' in psycopg_url
        assert 'sslmode=require' in psycopg_url
        
        # base should keep sslmode
        base_formatted = DatabaseURLBuilder.format_url_for_driver(base_url, 'base')
        assert 'postgresql://' in base_formatted
        assert 'sslmode=require' in base_formatted
        
    def test_url_normalization_removes_cloud_sql_ssl_params(self):
        """Test that Cloud SQL URL normalization removes SSL parameters."""
        # Cloud SQL URL with SSL params (incorrect)
        cloud_sql_url = "postgresql://user:pass@/db?host=/cloudsql/project:region:instance&sslmode=require"
        
        normalized = DatabaseURLBuilder.normalize_postgres_url(cloud_sql_url)
        
        # Should remove SSL parameters for Cloud SQL
        assert '/cloudsql/' in normalized
        assert 'sslmode=' not in normalized
        assert 'ssl=' not in normalized
        
    def test_production_credential_validation_rejects_weak_passwords(self):
        """Test that production environment rejects weak passwords."""
        weak_passwords = ['password', 'admin', '123456', 'dev_password']
        
        for weak_pass in weak_passwords:
            mock_env = {
                'ENVIRONMENT': 'production',
                'POSTGRES_HOST': 'prod-db.example.com',
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': 'netra_prod',
                'POSTGRES_USER': 'prod_user',
                'POSTGRES_PASSWORD': weak_pass
            }
            
            builder = DatabaseURLBuilder(mock_env)
            is_valid, error = builder.validate()
            
            # Should reject weak passwords
            assert not is_valid, f"Should reject weak password '{weak_pass}'"
            assert 'password' in error.lower(), f"Error should mention password: {error}"