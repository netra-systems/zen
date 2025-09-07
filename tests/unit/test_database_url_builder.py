"""
Comprehensive unit tests for DatabaseURLBuilder.
Tests all URL construction scenarios to prevent regression.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability  
- Value Impact: Prevents database connection failures in all environments
- Strategic Impact: Ensures reliable auth service across dev/staging/production
"""
import pytest
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment


class TestDatabaseURLBuilder:
    """Test DatabaseURLBuilder URL construction for all environments."""
    
    def test_development_with_database_url_async(self):
        """Test development environment with #removed-legacyreturns async format."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://user:pass@host:5432/db"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should return async format for development
        url = builder.get_url_for_environment(sync=False)
        assert url == "postgresql+asyncpg://user:pass@host:5432/db"
        
    def test_development_with_database_url_sync(self):
        """Test development environment with #removed-legacyreturns sync format when requested."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://user:pass@host:5432/db"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should return sync format when requested
        url = builder.get_url_for_environment(sync=True)
        assert url == "postgresql://user:pass@host:5432/db"
        
    def test_development_with_docker_compose_url(self):
        """Test development with Docker Compose style DATABASE_URL."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://netra_dev:netra_dev@dev-postgres:5432/netra_dev"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should return async format for asyncpg
        url = builder.get_url_for_environment(sync=False)
        assert url == "postgresql+asyncpg://netra_dev:netra_dev@dev-postgres:5432/netra_dev"
        
    def test_development_with_postgres_vars(self):
        """Test development with individual POSTGRES_* variables."""
        env_vars = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should construct URL from individual vars
        url = builder.get_url_for_environment(sync=False)
        assert url == "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
        
    def test_development_fallback_to_default(self):
        """Test development falls back to default when no config provided."""
        env_vars = {
            "ENVIRONMENT": "development"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should return default development URL
        url = builder.get_url_for_environment(sync=False)
        assert url == "postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev"
        
    def test_format_url_for_driver_asyncpg(self):
        """Test format_url_for_driver converts to asyncpg format."""
        url = "postgresql://user:pass@host:5432/db"
        result = DatabaseURLBuilder.format_url_for_driver(url, "asyncpg")
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"
        
    def test_format_url_for_driver_already_asyncpg(self):
        """Test format_url_for_driver handles already formatted URLs."""
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = DatabaseURLBuilder.format_url_for_driver(url, "asyncpg")
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"
        
    def test_staging_with_cloud_sql(self):
        """Test staging environment with Cloud SQL configuration."""
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/project:region:instance",
            "POSTGRES_DB": "staging_db",
            "POSTGRES_USER": "staging_user",
            "POSTGRES_PASSWORD": "staging_pass"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should detect Cloud SQL and format correctly
        url = builder.get_url_for_environment(sync=False)
        assert "/cloudsql/" in url
        assert "postgresql+asyncpg://" in url
        
    def test_production_with_tcp_ssl(self):
        """Test production environment with TCP and SSL."""
        env_vars = {
            "ENVIRONMENT": "production",
            "POSTGRES_HOST": "prod-db.example.com",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "prod_db",
            "POSTGRES_USER": "prod_user",
            "POSTGRES_PASSWORD": "prod_pass"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should add SSL for production TCP
        url = builder.get_url_for_environment(sync=False)
        assert "sslmode=require" in url
        assert "postgresql+asyncpg://" in url
        
    def test_test_environment_memory(self):
        """Test environment should use in-memory SQLite."""
        env_vars = {
            "ENVIRONMENT": "test"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should return SQLite memory URL for tests
        url = builder.get_url_for_environment(sync=False)
        assert url == "sqlite+aiosqlite:///:memory:"
        
    def test_validation_missing_required_vars(self):
        """Test validation catches missing required variables."""
        env_vars = {
            "ENVIRONMENT": "production",
            # Missing POSTGRES_HOST and other required vars
        }
        builder = DatabaseURLBuilder(env_vars)
        
        is_valid, error_msg = builder.validate()
        assert not is_valid
        assert "Missing required" in error_msg
        
    def test_database_url_priority_over_postgres_vars(self):
        """Test #removed-legacytakes priority when both are present."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://priority:user@priority-host:5432/priority-db",
            "POSTGRES_HOST": "ignored-host",
            "POSTGRES_USER": "ignored-user",
            "POSTGRES_DB": "ignored-db"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        url = builder.get_url_for_environment(sync=False)
        assert "priority-host" in url
        assert "priority-db" in url
        assert "postgresql+asyncpg://priority:user@priority-host:5432/priority-db" == url
        
    def test_special_characters_in_password(self):
        """Test handling of special characters in password."""
        env_vars = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "p@ss!word#123",
            "POSTGRES_DB": "testdb"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        url = builder.get_url_for_environment(sync=False)
        # Password should be URL-encoded
        assert "p%40ss%21word%23123" in url
        
    def test_empty_password_handling(self):
        """Test handling of empty password."""
        env_vars = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "",
            "POSTGRES_DB": "testdb"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        url = builder.get_url_for_environment(sync=False)
        # Should not include password separator
        assert "postgresql+asyncpg://user@localhost:5432/testdb" == url
        
    def test_development_auto_url_property(self):
        """Test DevelopmentBuilder.auto_url property directly."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://test:test@test-host:5432/testdb"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Direct property access
        url = builder.development.auto_url
        assert url == "postgresql+asyncpg://test:test@test-host:5432/testdb"
        
    def test_development_auto_sync_url_property(self):
        """Test DevelopmentBuilder.auto_sync_url property directly."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql+asyncpg://test:test@test-host:5432/testdb"
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Direct property access
        url = builder.development.auto_sync_url
        assert url == "postgresql://test:test@test-host:5432/testdb"


class TestDatabaseURLBuilderEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_none_database_url(self):
        """Test handling of None DATABASE_URL."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": None
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should fall back to default
        url = builder.get_url_for_environment(sync=False)
        assert url == "postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev"
        
    def test_empty_string_database_url(self):
        """Test handling of empty string DATABASE_URL."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": ""
        }
        builder = DatabaseURLBuilder(env_vars)
        
        # Should fall back to default
        url = builder.get_url_for_environment(sync=False)
        assert url == "postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev"
        
    def test_mixed_format_conversion(self):
        """Test conversion between different PostgreSQL URL formats."""
        test_cases = [
            ("postgresql://user:pass@host/db", "asyncpg", "postgresql+asyncpg://user:pass@host/db"),
            ("postgresql+psycopg2://user:pass@host/db", "asyncpg", "postgresql+asyncpg://user:pass@host/db"),
            ("postgresql+asyncpg://user:pass@host/db", "base", "postgresql://user:pass@host/db"),
        ]
        
        for input_url, driver, expected in test_cases:
            result = DatabaseURLBuilder.format_url_for_driver(input_url, driver)
            assert result == expected, f"Failed for {input_url} -> {driver}"
            
    def test_ssl_parameter_conversion(self):
        """Test SSL parameter conversion for asyncpg."""
        url = "postgresql://user:pass@host/db?sslmode=require"
        result = DatabaseURLBuilder.format_url_for_driver(url, "asyncpg")
        
        # asyncpg uses ssl= instead of sslmode=
        assert "ssl=require" in result
        assert "sslmode=" not in result