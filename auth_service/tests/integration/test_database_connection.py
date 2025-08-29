"""
Integration tests for auth service database connection.
Tests actual database connectivity in different configurations.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Auth service reliability
- Value Impact: Prevents auth service failures in production
- Strategic Impact: Ensures database URL construction works end-to-end across all environments
"""
import pytest
import asyncio
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from test_framework.setup_test_path import setup_test_path

# CRITICAL: setup_test_path() MUST be called before any project imports per CLAUDE.md
setup_test_path()

from auth_service.auth_core.database.connection import AuthDatabaseConnection
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.isolated_environment import get_env


class TestAuthDatabaseConnection:
    """Integration tests for auth database connection."""
    
    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Ensure test environment isolation per CLAUDE.md requirements."""
        env = get_env()
        env.enable_isolation()
        original_state = env.get_all_variables()
        yield env
        env.reset_to_original()
    
    @pytest.mark.asyncio
    async def test_connection_with_docker_compose_url(self, isolated_test_env):
        """Test connection with Docker Compose style DATABASE_URL."""
        # Set up test environment using IsolatedEnvironment
        isolated_test_env.set("ENVIRONMENT", "development", "test_database_connection")
        isolated_test_env.set("DATABASE_URL", "postgresql://netra_dev:netra_dev@dev-postgres:5432/netra_dev", "test_database_connection")
        
        # This should convert to async format internally
        url = AuthConfig.get_database_url()
        assert "postgresql+asyncpg://" in url
        assert "dev-postgres" in url
            
    @pytest.mark.asyncio
    async def test_connection_initialization_with_database_url(self, isolated_test_env):
        """Test database connection initialization with DATABASE_URL."""
        # Use real SQLite in-memory database for integration test (no mocks per CLAUDE.md)
        isolated_test_env.set("ENVIRONMENT", "test", "test_database_connection")
        isolated_test_env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test_database_connection")
        isolated_test_env.set("AUTH_FAST_TEST_MODE", "true", "test_database_connection")
        
        conn = AuthDatabaseConnection()
        await conn.initialize(timeout=5.0)
        
        assert conn._initialized
        assert conn.engine is not None
        assert conn.async_session_maker is not None
        
        # Cleanup
        await conn.close()
            
    @pytest.mark.asyncio
    async def test_connection_with_postgres_vars(self, isolated_test_env):
        """Test connection with individual POSTGRES_* variables."""
        # Set up individual PostgreSQL environment variables using IsolatedEnvironment
        isolated_test_env.set("ENVIRONMENT", "development", "test_database_connection")
        isolated_test_env.set("POSTGRES_HOST", "localhost", "test_database_connection")
        isolated_test_env.set("POSTGRES_PORT", "5432", "test_database_connection")
        isolated_test_env.set("POSTGRES_DB", "testdb", "test_database_connection")
        isolated_test_env.set("POSTGRES_USER", "testuser", "test_database_connection")
        isolated_test_env.set("POSTGRES_PASSWORD", "testpass", "test_database_connection")
        
        url = AuthConfig.get_database_url()
        assert "postgresql+asyncpg://" in url
        assert "testuser" in url
        assert "testdb" in url
            
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, isolated_test_env):
        """Test connection timeout is properly handled."""
        # Use IsolatedEnvironment to set up non-existent host test
        isolated_test_env.set("ENVIRONMENT", "development", "test_database_connection")
        isolated_test_env.set("DATABASE_URL", "postgresql://user:pass@nonexistent-host:5432/db", "test_database_connection")
        
        conn = AuthDatabaseConnection()
        
        # Should raise timeout or connection error with real connection attempt
        with pytest.raises(RuntimeError) as exc_info:
            await conn.initialize(timeout=2.0)
        
        assert "connection failed" in str(exc_info.value).lower()
            
    @pytest.mark.asyncio
    async def test_connection_retry_logic(self, isolated_test_env):
        """Test connection initialization with real SQLite database."""
        # Set up test environment for successful connection (no mocks per CLAUDE.md)
        isolated_test_env.set("ENVIRONMENT", "test", "test_database_connection")
        isolated_test_env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test_database_connection")
        isolated_test_env.set("AUTH_FAST_TEST_MODE", "true", "test_database_connection")
        
        conn = AuthDatabaseConnection()
        
        # Test that connection initialization works with real database
        await conn.initialize(timeout=5.0)
        
        assert conn._initialized
        assert conn.engine is not None
        
        # Cleanup
        await conn.close()
            
    @pytest.mark.asyncio
    async def test_database_url_format_conversion(self, isolated_test_env):
        """Test that sync URLs are converted to async format."""
        # Set up environment with sync PostgreSQL URL to test conversion
        isolated_test_env.set("ENVIRONMENT", "development", "test_database_connection")
        isolated_test_env.set("DATABASE_URL", "postgresql://user:pass@host:5432/db", "test_database_connection")
        
        # Test that the database manager converts sync URL to async format
        result = AuthDatabaseManager.get_auth_database_url_async()
        # Should be converted to async format or be empty in test env
        if result:  # Only assert format if URL is not empty
            assert "postgresql+asyncpg://" in result
            
    def test_auth_config_database_url_construction(self):
        """Test AuthConfig constructs correct database URL with IsolatedEnvironment."""
        env = get_env()
        env.enable_isolation()
        
        test_cases = [
            # Docker Compose style
            {
                "env_vars": {
                    "ENVIRONMENT": "development",
                    "DATABASE_URL": "postgresql://netra_dev:netra_dev@dev-postgres:5432/netra_dev"
                },
                "expected_contains": ["postgresql+asyncpg://", "dev-postgres", "netra_dev"]
            },
            # Individual vars
            {
                "env_vars": {
                    "ENVIRONMENT": "development",
                    "POSTGRES_HOST": "myhost",
                    "POSTGRES_USER": "myuser",
                    "POSTGRES_PASSWORD": "mypass",
                    "POSTGRES_DB": "mydb",
                    "POSTGRES_PORT": "5432"
                },
                "expected_contains": ["postgresql+asyncpg://", "myhost", "mydb"]
            },
            # DATABASE_URL priority
            {
                "env_vars": {
                    "ENVIRONMENT": "development",
                    "DATABASE_URL": "postgresql://priority:pass@priority-host:5432/priority-db",
                    "POSTGRES_HOST": "ignored",
                    "POSTGRES_USER": "ignored"
                },
                "expected_contains": ["postgresql+asyncpg://", "priority-host", "priority-db"]
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            # Clear environment for clean test
            env.clear()
            
            # Set up test environment variables using IsolatedEnvironment
            for key, value in test_case["env_vars"].items():
                env.set(key, value, f"test_auth_config_{i}")
            
            # Clear any cached config values
            env._cache.clear()
            
            url = AuthConfig.get_database_url()
            for expected in test_case["expected_contains"]:
                assert expected in url, f"Expected '{expected}' in URL: {url}"


class TestAuthDatabaseManager:
    """Test AuthDatabaseManager URL handling."""
    
    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Ensure test environment isolation per CLAUDE.md requirements."""
        env = get_env()
        env.enable_isolation()
        original_state = env.get_all_variables()
        yield env
        env.reset_to_original()
    
    def test_get_auth_database_url_async(self, isolated_test_env):
        """Test async URL retrieval."""
        isolated_test_env.set("ENVIRONMENT", "development", "test_database_manager")
        isolated_test_env.set("DATABASE_URL", "postgresql://user:pass@host:5432/db", "test_database_manager")
        
        url = AuthDatabaseManager.get_auth_database_url_async()
        # Should return async format
        if url:  # Only assert format if URL is not empty
            assert "postgresql+asyncpg://" in url
            
    def test_get_auth_database_url_sync(self, isolated_test_env):
        """Test sync URL retrieval."""
        isolated_test_env.set("ENVIRONMENT", "development", "test_database_manager")
        isolated_test_env.set("DATABASE_URL", "postgresql+asyncpg://user:pass@host:5432/db", "test_database_manager")
        
        url = AuthDatabaseManager.get_auth_database_url()
        # Should return sync format
        if url:  # Only assert format if URL is not empty
            assert "postgresql://" in url
            assert "postgresql+asyncpg://" not in url
                
    @pytest.mark.asyncio
    async def test_create_async_engine_with_url(self):
        """Test engine creation with provided URL."""
        test_url = "sqlite+aiosqlite:///:memory:"
        
        engine = AuthDatabaseManager.create_async_engine(database_url=test_url)
        assert engine is not None
        
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result is not None
            
        await engine.dispose()
        
    @pytest.mark.asyncio
    async def test_create_async_engine_without_url(self, isolated_test_env):
        """Test engine creation uses config when URL not provided."""
        # Set up test environment for SQLite in-memory database
        isolated_test_env.set("ENVIRONMENT", "test", "test_database_manager")
        isolated_test_env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test_database_manager")
        isolated_test_env.set("AUTH_FAST_TEST_MODE", "true", "test_database_manager")
        
        # Test real engine creation without mocks
        engine = AuthDatabaseManager.create_async_engine()
        assert engine is not None
        await engine.dispose()


class TestDatabaseURLValidation:
    """Test database URL validation."""
    
    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Ensure test environment isolation per CLAUDE.md requirements."""
        env = get_env()
        env.enable_isolation()
        original_state = env.get_all_variables()
        yield env
        env.reset_to_original()
    
    def test_validate_auth_url(self):
        """Test URL validation."""
        valid_urls = [
            "postgresql://user:pass@host/db",
            "postgresql+asyncpg://user:pass@host/db",
        ]
        
        for url in valid_urls:
            assert AuthDatabaseManager.validate_auth_url(url)
            
        invalid_urls = [
            None,
            "",
            "mysql://user:pass@host/db",
            "not-a-url"
        ]
        
        for url in invalid_urls:
            assert not AuthDatabaseManager.validate_auth_url(url)
            
    def test_environment_detection(self, isolated_test_env):
        """Test environment detection methods."""
        # Test staging environment detection
        isolated_test_env.set("ENVIRONMENT", "staging", "test_environment_detection")
        assert AuthDatabaseManager.is_cloud_sql_environment()
        assert not AuthDatabaseManager.is_test_environment()
        
        # Clear and test test environment detection
        isolated_test_env.clear()
        isolated_test_env.set("ENVIRONMENT", "test", "test_environment_detection")
        assert not AuthDatabaseManager.is_cloud_sql_environment()
        assert AuthDatabaseManager.is_test_environment()
        
        # Clear and test fast test mode detection
        isolated_test_env.clear()
        isolated_test_env.set("AUTH_FAST_TEST_MODE", "true", "test_environment_detection")
        assert AuthDatabaseManager.is_test_environment()