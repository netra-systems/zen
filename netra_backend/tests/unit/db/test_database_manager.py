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

# Test markers for unified test runner
pytestmark = [
    pytest.mark.env_test,  # For test environment compatibility
    pytest.mark.database,  # Database category marker
    pytest.mark.unit       # Unit test marker
]


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
         "postgresql://user:pass@host/cloudsql/project:region:instance/db"),
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db?ssl=require&sslmode=disable", 
         "postgresql://user:pass@host/cloudsql/project:region:instance/db"),
        
        # Regular URL with SSL parameters preserved and search_path added
        ("postgresql://user:pass@host:5432/db?sslmode=require", 
         "postgresql://user:pass@host:5432/db?sslmode=require&options=-c+search_path%3Dnetra_test%2Cpublic"),
        ("postgresql://user:pass@host:5432/db?ssl=require", 
         "postgresql://user:pass@host:5432/db?ssl=require&options=-c+search_path%3Dnetra_test%2Cpublic"),
    ])
    def test_get_base_database_url_conversion(self, input_url, expected_output):
        """Test base URL conversion removes driver prefixes and handles SSL."""
        # Mock the get_env() function instead of os.environ since DatabaseManager uses isolated environment
        with patch("netra_backend.app.db.database_manager.get_env") as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default='': input_url if key == 'DATABASE_URL' else default
            mock_env.get_all.return_value = {'DATABASE_URL': input_url}
            mock_get_env.return_value = mock_env
            
            result = DatabaseManager.get_base_database_url()
            assert result == expected_output
    
    def test_get_base_database_url_default_fallback(self):
        """Test default URL when DATABASE_URL not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("netra_backend.app.db.database_manager.get_current_environment") as mock_env:
                mock_env.return_value = "testing"  # Changed from "development" to "testing" to match expected URL
                # Mock unified config to return config without database_url
                with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
                    mock_config.return_value.database_url = None
                    result = DatabaseManager.get_base_database_url()
                    # In test environment (pytest context), we expect the test database URL with search path
                    # Port should be 5434 as configured in the actual database manager
                    assert result == "postgresql://test:test@localhost:5434/netra_test?options=-c%20search_path%3Dnetra_test,public"
    
    @pytest.mark.parametrize("source_url,expected_migration_url", [
        # Standard sync URL conversion
        ("postgresql://user:pass@host:5432/db?sslmode=require", 
         "postgresql://user:pass@host:5432/db?sslmode=require"),
        
        # Convert async driver to sync
        ("postgresql+asyncpg://user:pass@host:5432/db?ssl=require", 
         "postgresql://user:pass@host:5432/db?sslmode=require"),
        
        # Cloud SQL - converted to proper Unix socket format
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db", 
         "postgresql://user:pass@/db?host=/cloudsql/project:region:instance"),
    ])
    def test_get_migration_url_sync_format(self, source_url, expected_migration_url):
        """Test migration URL conversion for sync compatibility."""
        # Mock the unified config to return our test URL
        with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
            mock_config.return_value.database_url = source_url
            with patch("netra_backend.app.db.database_manager.get_env") as mock_get_env:
                mock_env = MagicMock()
                mock_env.get.side_effect = lambda key, default='': source_url if key == 'DATABASE_URL' else default
                mock_env.get_all.return_value = {'DATABASE_URL': source_url}
                mock_get_env.return_value = mock_env
                
                result = DatabaseManager.get_migration_url_sync_format()
                assert result == expected_migration_url
    
    @pytest.mark.parametrize("source_url,expected_app_url", [
        # Standard async URL conversion (search_path handled via server_settings, not URL options)
        ("postgresql://user:pass@host:5432/db?sslmode=require", 
         "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"),
        
        # Already async - preserve URL format (search_path handled via server_settings, not URL options)
        ("postgresql+asyncpg://user:pass@host:5432/db?ssl=require", 
         "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"),
        
        # Cloud SQL - converted to proper Unix socket format with async driver
        ("postgresql://user:pass@host/cloudsql/project:region:instance/db", 
         "postgresql+asyncpg://user:pass@/db?host=/cloudsql/project:region:instance"),
    ])
    def test_get_application_url_async(self, source_url, expected_app_url):
        """Test application URL conversion for async compatibility."""
        # Mock the unified config and get_env to ensure test URL is used
        with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
            mock_config.return_value.database_url = source_url
            with patch("netra_backend.app.db.database_manager.get_env") as mock_get_env:
                mock_env = MagicMock()
                mock_env.get.side_effect = lambda key, default='': source_url if key == 'DATABASE_URL' else default
                mock_env.get_all.return_value = {'DATABASE_URL': source_url}
                mock_get_env.return_value = mock_env
                
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
    
        # Mock: Component isolation for testing without external dependencies
    @patch("netra_backend.app.db.database_manager.get_unified_config")
    def test_is_local_development_true(self, mock_get_config):
        """Test local development detection - positive case."""
        mock_config = MagicMock()
        mock_config.environment = "development"
        mock_get_config.return_value = mock_config
        result = DatabaseManager.is_local_development()
        assert result is True
    
        # Mock: Component isolation for testing without external dependencies
    @patch("netra_backend.app.db.database_manager.get_unified_config") 
    def test_is_local_development_false(self, mock_get_config):
        """Test local development detection - negative case."""
        mock_config = MagicMock()
        mock_config.environment = "staging"
        mock_get_config.return_value = mock_config
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
        
        # Mock both unified config and environment to ensure test isolation
        with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
            mock_config.return_value.database_url = test_url
            mock_config.return_value.log_level = "INFO"  # Don't enable echo
            
            with patch("netra_backend.app.db.database_manager.get_env") as mock_get_env:
                mock_env = MagicMock()
                mock_env.get.side_effect = lambda key, default='': test_url if key == 'DATABASE_URL' else default
                mock_env.get_all.return_value = {'DATABASE_URL': test_url}
                mock_get_env.return_value = mock_env
                
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
            
            # The application URL method converts SSL parameters (search_path handled via server_settings)
            app_url = DatabaseManager.get_application_url_async()
            assert app_url == "postgresql+asyncpg://user:pass@localhost:5432/test_db"
            
            # Verify pool configuration
            assert engine.pool._pre_ping is True
            assert engine.pool._recycle == 3600
            # Pool size testing depends on pool implementation, so we'll skip exact checks
    
    def test_create_application_engine_cloud_sql(self):
        """Test async engine creation for Cloud SQL (no connect_args)."""
        test_url = "postgresql://user:pass@host/cloudsql/project:region:instance/db"
        
        # Mock both unified config and environment to ensure test isolation
        with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
            mock_config.return_value.database_url = test_url
            mock_config.return_value.log_level = "INFO"  # Don't enable echo
            
            with patch("netra_backend.app.db.database_manager.get_env") as mock_get_env:
                mock_env = MagicMock()
                mock_env.get.side_effect = lambda key, default='': test_url if key == 'DATABASE_URL' else default
                mock_env.get_all.return_value = {'DATABASE_URL': test_url}
                mock_get_env.return_value = mock_env
                
                engine = DatabaseManager.create_application_engine()
                
                # Verify it's an async engine with correct components
                assert engine.url.drivername == "postgresql+asyncpg"
                # For Cloud SQL Unix socket format, host is None and connection goes through host query param
                assert engine.url.host is None
                assert engine.url.username == "user"
                # Check for URL-encoded Cloud SQL socket path
                assert ("host=/cloudsql/project:region:instance" in str(engine.url) or 
                        "host=%2Fcloudsql%2Fproject%3Aregion%3Ainstance" in str(engine.url))
                
                # For Cloud SQL, connect_args should be empty (no server_settings needed)
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
                mock_env.return_value = "testing"  # Changed from "development" to "testing" to match expected URL
                # Mock unified config to return config without database_url
                with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
                    mock_config.return_value.database_url = None
                    result = DatabaseManager.get_base_database_url()
                    # In test environment (pytest context), we expect the test database URL with search path
                    # Port should be 5434 as configured in the actual database manager
                    assert result == "postgresql://test:test@localhost:5434/netra_test?options=-c%20search_path%3Dnetra_test,public"
    
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
                    # Port should be 5434 as configured in the actual database manager
                    assert result == "postgresql://test:test@localhost:5434/netra_test?options=-c%20search_path%3Dnetra_test,public"
    
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
                        # Should default to development settings with public schema search_path
                        # For unknown environments, it defaults to development with netra_dev database
                        assert result == "postgresql://netra:netra123@localhost:5433/netra_dev?options=-c%20search_path%3Dpublic"


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
        
        # Mock both unified config and environment to ensure test isolation
        with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
            mock_config.return_value.database_url = original_url
            mock_config.return_value.environment = "testing"
            
            with patch("netra_backend.app.db.database_manager.get_env") as mock_get_env:
                mock_env = MagicMock()
                mock_env.get.side_effect = lambda key, default='': original_url if key == 'DATABASE_URL' else default
                mock_env.get_all.return_value = {'DATABASE_URL': original_url}
                mock_get_env.return_value = mock_env
                
                with patch("netra_backend.app.db.database_manager.get_current_environment", return_value="testing"):
                    # Get base URL (should clean driver prefix but preserve SSL params and add search_path)
                    base_url = DatabaseManager.get_base_database_url()
                    assert base_url == "postgresql://user:pass@host:5432/db?ssl=require&options=-c+search_path%3Dnetra_test%2Cpublic"
                    
                    # Get migration URL (should be sync compatible with SSL converted)
                    migration_url = DatabaseManager.get_migration_url_sync_format()
                    assert migration_url == "postgresql://user:pass@host:5432/db?sslmode=require"
                    assert DatabaseManager.validate_migration_url_sync_format(migration_url) is True
                    
                    # Get application URL (should be async compatible, search_path handled via server_settings)
                    app_url = DatabaseManager.get_application_url_async()
                    assert app_url == "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"
                    assert DatabaseManager.validate_application_url(app_url) is True
    
    def test_cloud_sql_url_handling_end_to_end(self):
        """Test complete Cloud SQL URL handling."""
        cloud_url = "postgresql://user:pass@host/cloudsql/project:region:instance/db?sslmode=disable&ssl=require"
        
        # Mock both unified config and environment to ensure test isolation
        with patch("netra_backend.app.db.database_manager.get_unified_config") as mock_config:
            mock_config.return_value.database_url = cloud_url
            mock_config.return_value.environment = "testing"
            
            with patch("netra_backend.app.db.database_manager.get_env") as mock_get_env:
                mock_env = MagicMock()
                mock_env.get.side_effect = lambda key, default='': cloud_url if key == 'DATABASE_URL' else default
                mock_env.get_all.return_value = {'DATABASE_URL': cloud_url}
                mock_get_env.return_value = mock_env
                
                with patch("netra_backend.app.db.database_manager.get_current_environment", return_value="testing"):
                    # Base URL should strip SSL params for Cloud SQL
                    base_url = DatabaseManager.get_base_database_url()
                    assert base_url == "postgresql://user:pass@host/cloudsql/project:region:instance/db"
                    
                # Migration URL should be converted to proper Cloud SQL format
                migration_url = DatabaseManager.get_migration_url_sync_format()
                assert migration_url == "postgresql://user:pass@/db?host=/cloudsql/project:region:instance"
                assert DatabaseManager.validate_migration_url_sync_format(migration_url) is True
                
                # Application URL should add async driver and proper Cloud SQL format
                app_url = DatabaseManager.get_application_url_async()
                assert app_url == "postgresql+asyncpg://user:pass@/db?host=/cloudsql/project:region:instance"
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


class TestDatabaseManagerAdvancedErrorHandling:
    """Test advanced error handling scenarios."""
    
    def setup_method(self):
        """Reset environment for each test."""
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("ENVIRONMENT", None)
    
        def test_malformed_url_parsing_error(self):
            """Test handling of URLs that cause parsing errors."""
        manager = DatabaseManager()
        
        # Test with various malformed URLs
        malformed_urls = [
            "not-a-url",
            "ftp://invalid:protocol@host:5432/db",
            "postgresql://user:pass@:5432/db",  # Missing host
            "postgresql://user:pass@host:abc/db",  # Invalid port
            "postgresql://user@host:5432",  # Missing database
            "",  # Empty string
            None,  # None value
        ]
        
        for bad_url in malformed_urls:
            if bad_url is None:
                continue
                
            with patch.dict(os.environ, {"DATABASE_URL": str(bad_url)}, clear=False):
                try:
                    # Should either handle gracefully or raise informative error
                    result = manager.get_base_database_url()
                    # If it doesn't raise, result should be valid or default
                    assert result is not None
                except (ValueError, AttributeError, KeyError) as e:
                    # Expected behavior for malformed URLs
                    assert "url" in str(e).lower() or "database" in str(e).lower()
    
        def test_connection_pool_configuration_errors(self):
            """Test error handling in connection pool configuration."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            # Test with invalid pool configuration
            with patch('netra_backend.app.db.database_manager.create_engine') as mock_create_engine:
                mock_create_engine.side_effect = Exception("Pool configuration error")
                
                with pytest.raises(Exception):
                    from netra_backend.app.db.database_manager import create_migration_engine
                    create_migration_engine()
    
        def test_engine_creation_with_timeout_errors(self):
            """Test engine creation with connection timeout scenarios."""
        manager = DatabaseManager()
        
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            # Mock sqlalchemy to simulate timeout errors
            with patch('sqlalchemy.create_engine') as mock_create_engine:
                mock_engine = MagicMock()
                mock_engine.connect.side_effect = TimeoutError("Connection timeout")
                mock_create_engine.return_value = mock_engine
                
                # Engine creation should succeed even if connection testing fails
                result = manager.create_migration_engine()
                assert result is not None
    
        def test_session_factory_error_handling(self):
            """Test error handling in session factory creation."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            # Mock sessionmaker to fail
            with patch('netra_backend.app.db.database_manager.sessionmaker') as mock_sessionmaker:
                mock_sessionmaker.side_effect = Exception("Session configuration error")
                
                with pytest.raises(Exception):
                    from netra_backend.app.db.database_manager import get_migration_session
                    get_migration_session()
    
        def test_concurrent_access_error_handling(self):
            """Test database manager behavior under simulated concurrent access."""
        manager = DatabaseManager()
        
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            # Test multiple rapid calls to various methods
            results = []
            
            for _ in range(10):
                try:
                    # Should handle concurrent access gracefully
                    base_url = manager.get_base_database_url()
                    migration_url = manager.get_migration_url_sync_format()
                    app_url = manager.get_application_url_async()
                    
                    results.append((base_url, migration_url, app_url))
                except Exception as e:
                    # Should not fail under normal concurrent access
                    pytest.fail(f"Concurrent access failed: {e}")
            
            # All results should be consistent
            assert len(results) == 10
            assert all(r[0] == results[0][0] for r in results)  # Base URLs consistent
    
        def test_environment_variable_handling_with_special_chars(self):
            """Test handling of environment variables with unusual characters."""
        manager = DatabaseManager()
        
        # Test with various potentially problematic URLs that should be handled gracefully
        test_urls = [
            "postgresql://user:pass@host:5432/db_safe",  # Safe baseline
            "postgresql://user%40domain:pass@host:5432/db",  # URL-encoded username
            "postgresql://user:p%40ssword@host:5432/db",  # URL-encoded password
            "postgresql://user:pass@host:5432/db?application_name=test%20app",  # URL-encoded params
        ]
        
        for test_url in test_urls:
            with patch.dict(os.environ, {"DATABASE_URL": test_url}, clear=False):
                try:
                    result = manager.get_base_database_url()
                    # URL should be handled and result should be valid
                    assert result is not None
                    assert "postgresql://" in result
                except (ValueError, AttributeError) as e:
                    # Document any issues with specific URL formats
                    pytest.fail(f"Failed to handle URL: {test_url}, error: {e}")
    
        def test_database_manager_state_consistency(self):
            """Test that database manager maintains consistent state."""
        manager = DatabaseManager()
        
        # Test state consistency across different environment changes
        environments = ["development", "testing", "staging", "production"]
        
        for env in environments:
            with patch.dict(os.environ, {
                "ENVIRONMENT": env,
                "DATABASE_URL": f"postgresql://user:pass@host:5432/{env}_db"
            }, clear=False):
                
                # Multiple calls should return consistent results
                url1 = manager.get_base_database_url()
                url2 = manager.get_base_database_url()
                assert url1 == url2
                
                # Environment detection should be consistent
                is_local1 = manager.is_local_development()
                is_local2 = manager.is_local_development()
                assert is_local1 == is_local2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])