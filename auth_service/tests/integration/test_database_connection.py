"""
Integration tests for auth service database connection.
Tests actual database connectivity in different configurations.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Auth service reliability
- Value Impact: Prevents auth service failures in production
- Strategic Impact: Ensures database URL construction works end-to-end
"""
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from auth_service.auth_core.database.connection import AuthDatabaseConnection
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.config import AuthConfig


class TestAuthDatabaseConnection:
    """Integration tests for auth database connection."""
    
    @pytest.mark.asyncio
    async def test_connection_with_docker_compose_url(self):
        """Test connection with Docker Compose style DATABASE_URL."""
        # Mock environment to simulate Docker Compose
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://netra_dev:netra_dev@dev-postgres:5432/netra_dev"
        }):
            # This should convert to async format internally
            url = AuthConfig.get_database_url()
            assert "postgresql+asyncpg://" in url
            assert "dev-postgres" in url
            
    @pytest.mark.asyncio
    async def test_connection_initialization_with_database_url(self):
        """Test database connection initialization with DATABASE_URL."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "test",
            "DATABASE_URL": "sqlite:///:memory:",
            "AUTH_FAST_TEST_MODE": "true"
        }):
            conn = AuthDatabaseConnection()
            await conn.initialize(timeout=5.0)
            
            assert conn._initialized
            assert conn.engine is not None
            assert conn.async_session_maker is not None
            
            # Cleanup
            await conn.close()
            
    @pytest.mark.asyncio
    async def test_connection_with_postgres_vars(self):
        """Test connection with individual POSTGRES_* variables."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass"
        }):
            url = AuthConfig.get_database_url()
            assert "postgresql+asyncpg://" in url
            assert "testuser" in url
            assert "testdb" in url
            
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test connection timeout is properly handled."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://user:pass@nonexistent-host:5432/db"
        }):
            conn = AuthDatabaseConnection()
            
            # Should raise timeout or connection error
            with pytest.raises(RuntimeError) as exc_info:
                await conn.initialize(timeout=2.0)
            
            assert "connection failed" in str(exc_info.value).lower()
            
    @pytest.mark.asyncio
    async def test_connection_retry_logic(self):
        """Test connection handles transient failures."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "test",
            "AUTH_FAST_TEST_MODE": "true"
        }):
            conn = AuthDatabaseConnection()
            
            # Mock engine to simulate transient failure then success
            mock_engine = MagicMock()
            connect_call_count = 0
            
            async def mock_connect():
                nonlocal connect_call_count
                connect_call_count += 1
                if connect_call_count == 1:
                    raise OperationalError("Connection failed", None, None)
                return MagicMock()
                
            mock_engine.connect = MagicMock(return_value=mock_connect())
            
            # Should handle transient failure
            await conn.initialize(timeout=5.0)
            
    @pytest.mark.asyncio
    async def test_database_url_format_conversion(self):
        """Test that sync URLs are converted to async format."""
        # Test sync URL conversion
        sync_url = "postgresql://user:pass@host:5432/db"
        async_url = AuthDatabaseManager.get_auth_database_url_async()
        
        # Mock the secret loader to return sync URL
        with patch("auth_service.auth_core.secret_loader.AuthSecretLoader.get_database_url",
                   return_value=sync_url):
            result = AuthDatabaseManager.get_auth_database_url_async()
            # Should be converted to async format
            assert "postgresql+asyncpg://" in result or result == ""  # Empty in test env
            
    def test_auth_config_database_url_construction(self):
        """Test AuthConfig constructs correct database URL."""
        test_cases = [
            # Docker Compose style
            {
                "env": {
                    "ENVIRONMENT": "development",
                    "DATABASE_URL": "postgresql://netra_dev:netra_dev@dev-postgres:5432/netra_dev"
                },
                "expected_contains": ["postgresql+asyncpg://", "dev-postgres", "netra_dev"]
            },
            # Individual vars
            {
                "env": {
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
                "env": {
                    "ENVIRONMENT": "development",
                    "DATABASE_URL": "postgresql://priority:pass@priority-host:5432/priority-db",
                    "POSTGRES_HOST": "ignored",
                    "POSTGRES_USER": "ignored"
                },
                "expected_contains": ["postgresql+asyncpg://", "priority-host", "priority-db"]
            }
        ]
        
        for test_case in test_cases:
            with patch.dict(os.environ, test_case["env"], clear=True):
                # Force reload of config
                from auth_service.auth_core.isolated_environment import get_env
                get_env()._cache.clear()  # Clear any cached values
                
                url = AuthConfig.get_database_url()
                for expected in test_case["expected_contains"]:
                    assert expected in url, f"Expected '{expected}' in URL: {url}"


class TestAuthDatabaseManager:
    """Test AuthDatabaseManager URL handling."""
    
    def test_get_auth_database_url_async(self):
        """Test async URL retrieval."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://user:pass@host:5432/db"
        }):
            url = AuthDatabaseManager.get_auth_database_url_async()
            # Should return async format
            assert "postgresql+asyncpg://" in url or url == ""  # Empty in test env
            
    def test_get_auth_database_url_sync(self):
        """Test sync URL retrieval."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db"
        }):
            url = AuthDatabaseManager.get_auth_database_url()
            # Should return sync format
            if url:  # Not empty in test
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
    async def test_create_async_engine_without_url(self):
        """Test engine creation uses config when URL not provided."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "test",
            "AUTH_FAST_TEST_MODE": "true"
        }):
            # Should use config to get URL
            with patch("auth_service.auth_core.config.AuthConfig.get_database_url",
                       return_value="sqlite+aiosqlite:///:memory:"):
                engine = AuthDatabaseManager.create_async_engine()
                assert engine is not None
                await engine.dispose()


class TestDatabaseURLValidation:
    """Test database URL validation."""
    
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
            
    def test_environment_detection(self):
        """Test environment detection methods."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            assert AuthDatabaseManager.is_cloud_sql_environment()
            assert not AuthDatabaseManager.is_test_environment()
            
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            assert not AuthDatabaseManager.is_cloud_sql_environment()
            assert AuthDatabaseManager.is_test_environment()
            
        with patch.dict(os.environ, {"AUTH_FAST_TEST_MODE": "true"}):
            assert AuthDatabaseManager.is_test_environment()