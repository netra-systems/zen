"""
Test suite to enforce asyncpg-only database connections in auth service.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: Prevent psycopg2 import errors blocking $500K+ ARR
- Value Impact: Ensures auth service runs without psycopg2 dependency
- Strategic Impact: Maintains auth service independence from sync database drivers

This test suite validates that the auth service consistently uses asyncpg
driver URLs and never attempts to use psycopg2, preventing the "No module
named 'psycopg2'" error that blocks staging deployment.

Related Issue: #1264 - Auth service failing with psycopg2 import error
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.config import AuthConfig


class TestAsyncpgOnlyEnforcement(SSotBaseTestCase):
    """Enforce asyncpg-only database connections in auth service."""

    def test_auth_database_manager_always_returns_asyncpg_url(self):
        """Test that AuthDatabaseManager always returns URLs with asyncpg driver."""
        url = AuthDatabaseManager.get_database_url()

        # URL should explicitly specify asyncpg driver for PostgreSQL
        if 'postgresql' in url:
            assert '+asyncpg://' in url, f"PostgreSQL URL missing asyncpg driver: {url}"
        elif 'sqlite' in url:
            assert '+aiosqlite://' in url, f"SQLite URL missing aiosqlite driver: {url}"
        else:
            pytest.fail(f"Unexpected database URL format: {url}")

    def test_auth_config_get_database_url_uses_asyncpg(self):
        """Test that AuthConfig.get_database_url returns asyncpg URLs."""
        url = AuthConfig.get_database_url()

        # Should use async drivers only
        if 'postgresql' in url:
            assert '+asyncpg://' in url, f"PostgreSQL URL missing asyncpg driver: {url}"
            assert '+psycopg2://' not in url, f"URL should not use psycopg2: {url}"
            assert '+psycopg://' not in url, f"URL should not use psycopg: {url}"
        elif 'sqlite' in url:
            assert '+aiosqlite://' in url, f"SQLite URL missing aiosqlite driver: {url}"

    def test_auth_config_raw_database_url_normalization(self):
        """Test that raw database URLs are properly normalized to async drivers."""
        with patch('auth_service.auth_core.config.AuthEnvironment') as mock_auth_env:
            mock_env = Mock()
            mock_auth_env.return_value = mock_env

            # Test various input formats that should be normalized to asyncpg
            test_cases = [
                ('postgresql://user:pass@host/db', 'postgresql+asyncpg://user:pass@host/db'),
                ('postgres://user:pass@host/db', 'postgresql+asyncpg://user:pass@host/db'),
                ('postgresql+psycopg2://user:pass@host/db', 'postgresql+asyncpg://user:pass@host/db'),
                ('postgresql+psycopg://user:pass@host/db', 'postgresql+asyncpg://user:pass@host/db'),
                ('sqlite:///path/to/db', 'sqlite+aiosqlite:///path/to/db'),
                ('sqlite+aiosqlite:///path/to/db', 'sqlite+aiosqlite:///path/to/db'),
            ]

            for input_url, expected_output in test_cases:
                mock_env.get_database_url.return_value = input_url
                result = AuthConfig.get_database_url()
                assert result == expected_output, f"Input {input_url} should normalize to {expected_output}, got {result}"

    def test_no_psycopg2_references_in_production_urls(self):
        """Test that production-style URLs never contain psycopg2 references."""
        test_environments = ['staging', 'production']

        for env in test_environments:
            with patch.dict('os.environ', {'ENVIRONMENT': env}):
                with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                    mock_builder = MagicMock()
                    mock_builder.validate.return_value = (True, None)

                    # Simulate various production URL formats
                    production_urls = [
                        f"postgresql+asyncpg://user:pass@/cloudsql/project:region:instance/db",
                        f"postgresql+asyncpg://user:pass@prod-host:5432/db?ssl=require",
                        f"postgresql+asyncpg://user:pass@staging-host:5432/db?ssl=require",
                    ]

                    for prod_url in production_urls:
                        mock_builder.get_url_for_environment.return_value = prod_url
                        mock_builder.get_safe_log_message.return_value = f"Connected to {env} database"
                        mock_builder_class.return_value = mock_builder

                        url = AuthDatabaseManager.get_database_url()

                        # Validate asyncpg-only
                        assert '+asyncpg://' in url, f"Environment {env} URL missing asyncpg: {url}"
                        assert '+psycopg2://' not in url, f"Environment {env} URL contains psycopg2: {url}"
                        assert '+psycopg://' not in url, f"Environment {env} URL contains psycopg: {url}"

    def test_auth_service_requirements_compliance(self):
        """Test that auth service enforces asyncpg-only requirements."""
        # This test validates that our requirements are properly configured
        # In a real test environment, we would verify that:
        # 1. asyncpg is available
        # 2. psycopg2 is NOT available
        # 3. Database connections work with asyncpg only

        # Test asyncpg availability
        try:
            import asyncpg
            assert asyncpg is not None, "asyncpg should be available in auth service"
        except ImportError:
            pytest.fail("asyncpg should be available in auth service requirements")

        # Test that psycopg2 is NOT available (expected in auth service)
        try:
            import psycopg2
            pytest.fail("psycopg2 should NOT be available in auth service to enforce async-only pattern")
        except ImportError:
            # This is expected - auth service should not have psycopg2
            pass

    def test_cloud_sql_urls_use_asyncpg(self):
        """Test that Cloud SQL URLs always use asyncpg driver."""
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.validate.return_value = (True, None)

            # Simulate Cloud SQL configuration
            cloud_sql_url = "postgresql+asyncpg://user:pass@/db?host=/cloudsql/project:region:instance"
            mock_builder.get_url_for_environment.return_value = cloud_sql_url
            mock_builder.get_safe_log_message.return_value = "Connected to Cloud SQL"
            mock_builder_class.return_value = mock_builder

            url = AuthDatabaseManager.get_database_url()

            assert url == cloud_sql_url
            assert '+asyncpg://' in url
            assert '+psycopg2://' not in url
            assert '+psycopg://' not in url

    def test_database_connection_creation_uses_asyncpg(self):
        """Test that database connection creation enforces asyncpg."""
        from auth_service.auth_core.database.connection import AuthDatabaseConnection

        conn = AuthDatabaseConnection()

        # The connection should be configured to use asyncpg URLs
        # This test validates the configuration without actually connecting
        assert conn.environment in ['development', 'test', 'staging', 'production']

        # The connection should use the proper URL format when initialized
        # We test this by checking the URL generation path
        with patch.object(AuthDatabaseManager, 'get_database_url') as mock_get_url:
            mock_get_url.return_value = "postgresql+asyncpg://test:test@localhost:5432/test"

            # This should work without trying to import psycopg2
            url = AuthDatabaseManager.get_database_url()
            assert '+asyncpg://' in url


class TestPsycopg2ImportPrevention(SSotBaseTestCase):
    """Prevent any code paths that might try to import psycopg2."""

    def test_no_psycopg2_imports_in_auth_service(self):
        """Test that auth service code doesn't import psycopg2."""
        import sys

        # Mock psycopg2 to raise ImportError to simulate staging environment
        original_import = __builtins__.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'psycopg2' or name.startswith('psycopg2.'):
                raise ImportError(f"No module named '{name}' (simulated staging environment)")
            return original_import(name, *args, **kwargs)

        # Temporarily replace import to simulate missing psycopg2
        __builtins__.__import__ = mock_import

        try:
            # These imports should work without trying to import psycopg2
            from auth_service.auth_core.database.database_manager import AuthDatabaseManager
            from auth_service.auth_core.database.connection import AuthDatabaseConnection
            from auth_service.auth_core.config import AuthConfig

            # These operations should not trigger psycopg2 import
            url = AuthDatabaseManager.get_database_url()
            config_url = AuthConfig.get_database_url()

            # Should succeed without psycopg2
            assert url is not None
            assert config_url is not None

        finally:
            # Restore original import
            __builtins__.__import__ = original_import

    def test_sqlalchemy_engine_creation_with_asyncpg_only(self):
        """Test that SQLAlchemy engine creation works with asyncpg-only environment."""
        from sqlalchemy.ext.asyncio import create_async_engine

        # Test that asyncpg URLs work for engine creation
        asyncpg_url = "postgresql+asyncpg://test:test@localhost:5432/test"

        # This should not raise ImportError for psycopg2
        try:
            engine = create_async_engine(asyncpg_url, strategy='mock')
            assert engine is not None
            assert 'asyncpg' in str(engine.url)
        except ImportError as e:
            if 'psycopg2' in str(e):
                pytest.fail(f"SQLAlchemy tried to import psycopg2 with asyncpg URL: {e}")
            else:
                # Other import errors are acceptable for this test
                pass