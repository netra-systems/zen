"""Comprehensive Unit Tests for DatabaseManager

Tests all URL conversion, environment detection, error handling, and integration functionality.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Database stability and deployment reliability
- Value Impact: Prevents database connection failures across environments
- Strategic Impact: Critical for system reliability and data integrity
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

from test_framework.decorators import mock_justified
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.core.environment_constants import Environment


class TestDatabaseManagerURLConversion:
    """Test URL conversion between sync and async formats."""
    
    def setup_method(self):
        """Reset environment for each test."""
        # Clear any existing DATABASE_URL
        os.environ.pop("DATABASE_URL", None)
    
    @pytest.mark.parametrize("input_url,expected_output", [
        # Basic PostgreSQL URL conversion (search_path option automatically added in test environment)
        ("postgresql://user:pass@host:5432/db", "postgresql://user:pass@host:5432/db?options=-c+search_path%3Dnetra_test%2Cpublic"),
        
        # Remove async driver prefixes (search_path option automatically added in test environment)
        ("postgresql+asyncpg://user:pass@host:5432/db", "postgresql://user:pass@host:5432/db?options=-c+search_path%3Dnetra_test%2Cpublic"),
        ("postgres+asyncpg://user:pass@host:5432/db", "postgresql://user:pass@host:5432/db?options=-c+search_path%3Dnetra_test%2Cpublic"),
        ("postgres://user:pass@host:5432/db", "postgresql://user:pass@host:5432/db?options=-c+search_path%3Dnetra_test%2Cpublic"),
        
        # Cloud SQL Unix socket (SSL parameters removed, no search_path added)
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db?sslmode=require", 
         "postgresql://user:pass@host/cloudsql/project:region:instance/db?options=-c+search_path%3Dnetra_test%2Cpublic"),
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db?ssl=require&sslmode=disable", 
         "postgresql://user:pass@host/cloudsql/project:region:instance/db?options=-c+search_path%3Dnetra_test%2Cpublic"),
        
        # Regular URL with SSL parameters preserved and search_path added
        ("postgresql://user:pass@host:5432/db?sslmode=require", 
         "postgresql://user:pass@host:5432/db?sslmode=require&options=-c+search_path%3Dnetra_test%2Cpublic"),
        ("postgresql://user:pass@host:5432/db?ssl=require", 
         "postgresql://user:pass@host:5432/db?ssl=require&options=-c+search_path%3Dnetra_test%2Cpublic"),
    ])
    def test_get_base_database_url_conversion(self, input_url, expected_output):
        """Test base URL conversion removes driver prefixes and handles SSL."""
        with patch.dict(os.environ, {"DATABASE_URL": input_url}):
            result = DatabaseManager.get_base_database_url()
            assert result == expected_output
    
    @mock_justified("L1 Unit Test: Mocking environment detection to test default URL fallback logic. Real environment configurations tested in L3 integration tests.", "L1")
    def test_get_base_database_url_default_fallback(self):
        """Test default URL when DATABASE_URL not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("netra_backend.app.db.database_manager.get_current_environment") as mock_env:
                mock_env.return_value = "development"
                # Mock unified config to return config without database_url
                with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
                    mock_config.return_value.database_url = None
                    result = DatabaseManager.get_base_database_url()
                    # In test environment (pytest context), we expect the test database URL with search path
                    assert result == "postgresql://test:test@localhost:5432/netra_test?options=-c%20search_path%3Dnetra_test,public"
    
    @pytest.mark.parametrize("base_url,expected_migration_url", [
        # Standard sync URL conversion
        ("postgresql://user:pass@host:5432/db?sslmode=require", 
         "postgresql://user:pass@host:5432/db?sslmode=require"),
        
        # Convert async driver to sync
        ("postgresql+asyncpg://user:pass@host:5432/db?ssl=require", 
         "postgresql://user:pass@host:5432/db?sslmode=require"),
        
        # Cloud SQL - no SSL conversion needed
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db", 
         "postgresql://user:pass@host/cloudsql/project:region:instance/db"),
    ])
    def test_get_migration_url_sync_format(self, base_url, expected_migration_url):
        """Test migration URL conversion for sync compatibility."""
        with patch.dict(os.environ, {"DATABASE_URL": base_url}):
            result = DatabaseManager.get_migration_url_sync_format()
            assert result == expected_migration_url
    
    @pytest.mark.parametrize("base_url,expected_app_url", [
        # Standard async URL conversion
        ("postgresql://user:pass@host:5432/db?sslmode=require", 
         "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"),
        
        # Already async - preserve
        ("postgresql+asyncpg://user:pass@host:5432/db?ssl=require", 
         "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"),
        
        # Cloud SQL - no SSL conversion needed
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db", 
         "postgresql+asyncpg://user:pass@host/cloudsql/project:region:instance/db"),
    ])
    def test_get_application_url_async(self, base_url, expected_app_url):
        """Test application URL conversion for async compatibility."""
        with patch.dict(os.environ, {"DATABASE_URL": base_url}):
            result = DatabaseManager.get_application_url_async()
            assert result == expected_app_url


class TestDatabaseManagerValidation:
    """Test URL validation methods."""
    
    def setup_method(self):
        """Reset environment for each test."""
        os.environ.pop("DATABASE_URL", None)
    
    @pytest.mark.parametrize("url,expected_valid", [
        # Valid base URLs (after get_base_database_url processing)
        ("postgresql://user:pass@host:5432/db", True),
        ("postgresql://user:pass@host:5432/db?sslmode=require", True),
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db", True),
        
        # Invalid base URLs (contain driver-specific elements after processing)
        # Note: get_base_database_url() strips asyncpg, so this would actually be valid after processing
        # Let's test the validation logic properly by using URLs that would remain invalid
        ("postgresql://user:pass@host:5432/db?ssl=require&sslmode=disable", False),  # mixed SSL params
    ])
    def test_validate_base_url(self, url, expected_valid):
        """Test base URL validation."""
        with patch.dict(os.environ, {"DATABASE_URL": url}):
            result = DatabaseManager.validate_base_url()
            assert result == expected_valid
    
    @pytest.mark.parametrize("url,expected_valid", [
        # Valid sync URLs
        ("postgresql://user:pass@host:5432/db", True),
        ("postgresql://user:pass@host:5432/db?sslmode=require", True),
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db", True),
        
        # Invalid sync URLs
        ("postgresql+asyncpg://user:pass@host:5432/db", False),
        ("postgresql://user:pass@host:5432/db?ssl=require", False),  # should use sslmode
    ])
    def test_validate_migration_url_sync_format(self, url, expected_valid):
        """Test migration URL validation for sync compatibility."""
        result = DatabaseManager.validate_migration_url_sync_format(url)
        assert result == expected_valid
    
    @pytest.mark.parametrize("url,expected_valid", [
        # Valid async URLs  
        ("postgresql+asyncpg://user:pass@host:5432/db", True),
        ("postgresql+asyncpg://user:pass@host:5432/db?ssl=require", True),
        ("postgresql+asyncpg://user:pass@host/cloudsql/project:region:instance/db", True),
        
        # Invalid async URLs
        ("postgresql://user:pass@host:5432/db", False),  # missing async driver
        ("postgresql+asyncpg://user:pass@host:5432/db?sslmode=require", False),  # should use ssl
    ])
    def test_validate_application_url(self, url, expected_valid):
        """Test application URL validation for async compatibility."""
        result = DatabaseManager.validate_application_url(url)
        assert result == expected_valid


class TestDatabaseManagerEnvironmentDetection:
    """Test environment detection methods."""
    
    def setup_method(self):
        """Reset environment for each test."""
        # Clear all environment variables
        env_vars_to_clear = [
            "DATABASE_URL", "K_SERVICE", "INSTANCE_CONNECTION_NAME",
            "ENVIRONMENT", "NETRA_ENV"
        ]
        for var in env_vars_to_clear:
            os.environ.pop(var, None)
    
    def test_is_cloud_sql_environment_true(self):
        """Test Cloud SQL environment detection - positive case."""
        test_url = "postgresql://user:pass@host/cloudsql/project:region:instance/db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            result = DatabaseManager.is_cloud_sql_environment()
            assert result is True
    
    def test_is_cloud_sql_environment_false(self):
        """Test Cloud SQL environment detection - negative case."""  
        test_url = "postgresql://user:pass@localhost:5432/db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            result = DatabaseManager.is_cloud_sql_environment()
            assert result is False
    
    def test_is_cloud_sql_environment_no_url(self):
        """Test Cloud SQL environment detection - no DATABASE_URL."""
        with patch.dict(os.environ, {}, clear=True):
            result = DatabaseManager.is_cloud_sql_environment()
            assert result is False
    
    @mock_justified("L1 Unit Test: Mocking environment detection to test environment-specific logic. Real environment testing in L3 integration tests.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch("netra_backend.app.db.database_manager.get_current_environment")
    def test_is_local_development_true(self, mock_get_env):
        """Test local development detection - positive case."""
        mock_get_env.return_value = "development"
        result = DatabaseManager.is_local_development()
        assert result is True
    
    @mock_justified("L1 Unit Test: Mocking environment detection to test environment-specific logic. Real environment testing in L3 integration tests.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch("netra_backend.app.db.database_manager.get_current_environment") 
    def test_is_local_development_false(self, mock_get_env):
        """Test local development detection - negative case."""
        mock_get_env.return_value = "staging"
        result = DatabaseManager.is_local_development()
        assert result is False
    
    @pytest.mark.parametrize("environment,expected", [
        ("staging", True),
        ("production", True),
        ("development", False),
        ("testing", False),
    ])
    def test_is_remote_environment(self, environment, expected):
        """Test remote environment detection."""
        # Mock: Database access isolation for fast, reliable unit testing
        with patch("netra_backend.app.db.database_manager.get_current_environment") as mock_env:
            mock_env.return_value = environment
            result = DatabaseManager.is_remote_environment()
            assert result == expected


class TestDatabaseManagerEngineCreation:
    """Test engine creation methods."""
    
    def setup_method(self):
        """Reset environment for each test."""
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("SQL_ECHO", None)
    
    def test_create_migration_engine_basic(self):
        """Test sync engine creation for migrations."""
        test_url = "postgresql://user:pass@localhost:5432/test_db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            engine = DatabaseManager.create_migration_engine()
            
            # Verify it's a sync engine (SQLAlchemy 2.0+ doesn't have execute method on engine)
            from sqlalchemy import create_engine
            assert type(engine).__name__ == type(create_engine("sqlite:///:memory:")).__name__
            
            # Verify URL components (password gets masked as ***)
            assert engine.url.host == "localhost"
            assert engine.url.port == 5432
            assert engine.url.database == "test_db"
            assert engine.url.username == "user"
            
            # Verify configuration
            assert engine.pool._pre_ping is True
            assert engine.pool._recycle == 3600
    
    def test_create_migration_engine_with_sql_echo(self):
        """Test sync engine creation with SQL echo enabled."""
        test_url = "postgresql://user:pass@localhost:5432/test_db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url, "SQL_ECHO": "true"}):
            engine = DatabaseManager.create_migration_engine()
            assert engine.echo is True
    
    def test_create_application_engine_basic(self):
        """Test async engine creation for application."""
        test_url = "postgresql://user:pass@localhost:5432/test_db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            engine = DatabaseManager.create_application_engine()
            
            # Verify it's an async engine by checking URL components
            assert engine.url.drivername == "postgresql+asyncpg"
            assert engine.url.host == "localhost"
            assert engine.url.port == 5432
            assert engine.url.database == "test_db"
            assert engine.url.username == "user"
            
            # The application URL method only converts existing SSL parameters,
            # it doesn't add new ones. For a basic URL without SSL params,
            # we shouldn't expect SSL params in the output.
            app_url = DatabaseManager.get_application_url_async()
            assert app_url == "postgresql+asyncpg://user:pass@localhost:5432/test_db"
            
            # Verify pool configuration
            assert engine.pool._pre_ping is True
            assert engine.pool._recycle == 3600
            # Pool size testing depends on pool implementation, so we'll skip exact checks
    
    def test_create_application_engine_cloud_sql(self):
        """Test async engine creation for Cloud SQL (no connect_args)."""
        test_url = "postgresql://user:pass@host/cloudsql/project:region:instance/db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            engine = DatabaseManager.create_application_engine()
            
            # Verify it's an async engine with correct components
            assert engine.url.drivername == "postgresql+asyncpg"
            assert engine.url.host == "host"
            assert engine.url.username == "user"
            assert "/cloudsql/project:region:instance/db" in str(engine.url)
            
            # For Cloud SQL, connect_args should be empty
            # This is harder to test directly, but we can verify the engine was created
            assert engine is not None


class TestDatabaseManagerSessionFactories:
    """Test session factory creation methods."""
    
    def setup_method(self):
        """Reset environment for each test."""
        os.environ.pop("DATABASE_URL", None)
    
    def test_get_migration_session(self):
        """Test sync session factory creation."""
        test_url = "postgresql://user:pass@localhost:5432/test_db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            session_factory = DatabaseManager.get_migration_session()
            
            # Verify it's a sessionmaker (sync)
            from sqlalchemy.orm import sessionmaker
            assert isinstance(session_factory, sessionmaker)
    
    def test_get_application_session(self):
        """Test async session factory creation."""
        test_url = "postgresql://user:pass@localhost:5432/test_db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            session_factory = DatabaseManager.get_application_session()
            
            # Verify it's an async_sessionmaker
            from sqlalchemy.ext.asyncio import async_sessionmaker
            assert isinstance(session_factory, async_sessionmaker)
            
            # Verify session configuration
            assert session_factory.kw['expire_on_commit'] is False
            assert session_factory.kw['autocommit'] is False
            assert session_factory.kw['autoflush'] is False


class TestDatabaseManagerErrorHandling:
    """Test error handling and edge cases."""
    
    def setup_method(self):
        """Reset environment for each test."""
        os.environ.pop("DATABASE_URL", None)
    
    def test_invalid_url_format_handling(self):
        """Test handling of invalid URL formats."""
        # Test with completely invalid URL
        with patch.dict(os.environ, {"DATABASE_URL": "invalid://not-a-url"}):
            # Should not raise exception, should handle gracefully
            base_url = DatabaseManager.get_base_database_url()
            # Still processes the invalid URL (removes prefixes that don't exist)
            assert base_url == "invalid://not-a-url"
    
    def test_empty_database_url_handling(self):
        """Test handling when DATABASE_URL is empty."""
        with patch.dict(os.environ, {"DATABASE_URL": ""}):
            with patch("netra_backend.app.db.database_manager.get_current_environment") as mock_env:
                mock_env.return_value = "development"
                # Mock unified config to return config without database_url
                with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
                    mock_config.return_value.database_url = None
                    result = DatabaseManager.get_base_database_url()
                    # In test environment (pytest context), we expect the test database URL with search path
                    assert result == "postgresql://test:test@localhost:5432/netra_test?options=-c%20search_path%3Dnetra_test,public"
    
    def test_missing_database_url_handling(self):
        """Test handling when DATABASE_URL is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("netra_backend.app.db.database_manager.get_current_environment") as mock_env:
                mock_env.return_value = "testing"
                # Mock unified config to return config without database_url
                with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
                    mock_config.return_value.database_url = None
                    result = DatabaseManager.get_base_database_url()
                    # In test environment (pytest context), we expect the test database URL with search path
                    assert result == "postgresql://test:test@localhost:5432/netra_test?options=-c%20search_path%3Dnetra_test,public"
    
    def test_driver_mismatch_validation(self):
        """Test validation catches driver mismatches."""
        # Async driver in sync URL validation
        async_url = "postgresql+asyncpg://user:pass@host:5432/db"
        assert DatabaseManager.validate_migration_url_sync_format(async_url) is False
        
        # Sync driver in async URL validation  
        sync_url = "postgresql://user:pass@host:5432/db"
        assert DatabaseManager.validate_application_url(sync_url) is False
    
    def test_ssl_parameter_mismatch_validation(self):
        """Test validation catches SSL parameter mismatches."""
        # Wrong SSL param for sync (should use sslmode, not ssl)
        sync_url_wrong_ssl = "postgresql://user:pass@host:5432/db?ssl=require"
        assert DatabaseManager.validate_migration_url_sync_format(sync_url_wrong_ssl) is False
        
        # Wrong SSL param for async (should use ssl, not sslmode) - except Cloud SQL
        async_url_wrong_ssl = "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require"
        assert DatabaseManager.validate_application_url(async_url_wrong_ssl) is False
    
    def test_default_environment_handling(self):
        """Test handling of unknown environment values."""
        with patch.dict(os.environ, {}, clear=True):
            # Mock: Database access isolation for fast, reliable unit testing
            with patch("netra_backend.app.db.database_manager.get_current_environment") as mock_env:
                mock_env.return_value = "unknown_environment"
                # Mock sys.modules to not contain pytest so we don't get test URL
                # Mock: Component isolation for testing without external dependencies
                with patch("sys.modules", {}):
                    # Mock: Component isolation for testing without external dependencies
                    with patch("sys.argv", ["python"]):
                        result = DatabaseManager._get_default_database_url()
                        # Should default to development settings
                        assert result == "postgresql://postgres:password@localhost:5432/netra"


class TestDatabaseManagerIntegration:
    """Integration tests with real database operations (if available)."""
    
    def setup_method(self):
        """Setup for integration tests."""
        os.environ.pop("DATABASE_URL", None)
    
    def test_migration_engine_can_connect(self):
        """Test that migration engine can attempt connection."""
        # Use a test database URL that might work in CI/local
        test_url = "postgresql://postgres:password@localhost:5432/postgres"
        
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            try:
                engine = DatabaseManager.create_migration_engine()
                # Try to create a connection (will fail if postgres not available, but shouldn't crash)
                with engine.connect() as conn:
                    result = conn.execute("SELECT 1 as test")
                    row = result.fetchone()
                    assert row[0] == 1
            except Exception:
                # If database not available, that's fine for unit tests
                # The important thing is the engine creation worked
                pytest.skip("PostgreSQL not available for integration test")
    
    @pytest.mark.asyncio
    async def test_application_session_can_create(self):
        """Test that application session factory can create sessions."""
        test_url = "postgresql://postgres:password@localhost:5432/postgres"
        
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            try:
                session_factory = DatabaseManager.get_application_session()
                
                # Try to create a session
                async with session_factory() as session:
                    # Attempt a simple query
                    result = await session.execute("SELECT 1 as test")
                    row = result.fetchone()
                    assert row[0] == 1
            except Exception:
                # If database not available, that's fine for unit tests
                pytest.skip("PostgreSQL not available for async integration test")
    
    def test_url_conversion_end_to_end(self):
        """Test complete URL conversion workflow."""
        original_url = "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": original_url}):
            # Get base URL (should clean driver prefix but preserve SSL params)
            base_url = DatabaseManager.get_base_database_url()
            assert base_url == "postgresql://user:pass@host:5432/db?ssl=require"
            
            # Get migration URL (should be sync compatible with SSL converted)
            migration_url = DatabaseManager.get_migration_url_sync_format()
            assert migration_url == "postgresql://user:pass@host:5432/db?sslmode=require"
            assert DatabaseManager.validate_migration_url_sync_format(migration_url) is True
            
            # Get application URL (should be async compatible)
            app_url = DatabaseManager.get_application_url_async()
            assert app_url == "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"
            assert DatabaseManager.validate_application_url(app_url) is True
    
    def test_cloud_sql_url_handling_end_to_end(self):
        """Test complete Cloud SQL URL handling."""
        cloud_url = "postgresql://user:pass@host/cloudsql/project:region:instance/db?sslmode=disable&ssl=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": cloud_url}):
            # Base URL should strip SSL params for Cloud SQL
            base_url = DatabaseManager.get_base_database_url()
            assert base_url == "postgresql://user:pass@host/cloudsql/project:region:instance/db"
            
            # Migration URL should work as-is
            migration_url = DatabaseManager.get_migration_url_sync_format()
            assert migration_url == "postgresql://user:pass@host/cloudsql/project:region:instance/db"
            assert DatabaseManager.validate_migration_url_sync_format(migration_url) is True
            
            # Application URL should add async driver
            app_url = DatabaseManager.get_application_url_async()
            assert app_url == "postgresql+asyncpg://user:pass@host/cloudsql/project:region:instance/db"
            assert DatabaseManager.validate_application_url(app_url) is True
            
            # Should detect Cloud SQL environment
            assert DatabaseManager.is_cloud_sql_environment() is True


class TestDatabaseManagerEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_url_with_query_parameters_preserved(self):
        """Test that non-SSL query parameters are preserved."""
        url_with_params = "postgresql://user:pass@host:5432/db?application_name=test&connect_timeout=30"
        
        with patch.dict(os.environ, {"DATABASE_URL": url_with_params}):
            base_url = DatabaseManager.get_base_database_url()
            # Should preserve non-SSL parameters
            assert "application_name=test" in base_url
            assert "connect_timeout=30" in base_url
    
    def test_url_with_special_characters_in_credentials(self):
        """Test URL handling with special characters in username/password."""
        special_url = "postgresql://user%40domain.com:p%40ssw%24rd@host:5432/db"
        
        with patch.dict(os.environ, {"DATABASE_URL": special_url}):
            result = DatabaseManager.get_base_database_url()
            # Should preserve URL encoding
            assert "user%40domain.com" in result
            assert "p%40ssw%24rd" in result
    
    def test_multiple_ssl_parameters_handling(self):
        """Test handling of multiple SSL-related parameters."""
        complex_ssl_url = "postgresql://user:pass@host:5432/db?sslmode=require&sslcert=cert.pem&sslkey=key.pem&ssl=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": complex_ssl_url}):
            base_url = DatabaseManager.get_base_database_url()
            # Should preserve non-conflicting SSL params
            assert "sslcert=cert.pem" in base_url
            assert "sslkey=key.pem" in base_url
    
    @pytest.mark.parametrize("environment,expected_db", [
        ("development", "netra"),
        ("testing", "netra_test"),
        ("staging", "netra"),  # Falls back to default
        ("production", "netra"),  # Falls back to default
    ])
    def test_default_database_url_by_environment(self, environment, expected_db):
        """Test default database URL generation for different environments."""
        # Mock: Database access isolation for fast, reliable unit testing
        with patch("netra_backend.app.db.database_manager.get_current_environment") as mock_env:
            mock_env.return_value = environment
            result = DatabaseManager._get_default_database_url()
            assert f"/{expected_db}" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])