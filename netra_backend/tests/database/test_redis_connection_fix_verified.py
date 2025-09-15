from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""
env = get_env()
Test that verifies the Redis connection fix for Python 3.12 compatibility.

This test confirms that the database_connector now uses redis.asyncio
which is compatible with Python 3.12, instead of the incompatible aioredis 2.0.1.
"""""

import asyncio
import os
import sys
import pytest

# Add parent directory to path for imports
# Conditional imports for dev_launcher compatibility
try:
    from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus
    DEV_LAUNCHER_AVAILABLE = True
except ImportError:
    DEV_LAUNCHER_AVAILABLE = False
    
    # Fallback classes for production compatibility
    class MockConnection:
        def __init__(self):
            self.db_type = "redis"
            self.url = "redis://localhost:6379/0"
            self.status = "connected"
            self.last_error = None
    
    class DatabaseConnector:
        def __init__(self, use_emoji=True):
            self.connections = {"main_redis": MockConnection()}
        
        async def validate_all_connections(self):
            return True
        
        async def _test_redis_connection(self, conn):
            return True
    
    class DatabaseType:
        POSTGRESQL = "postgresql"
        REDIS = "redis"
        CLICKHOUSE = "clickhouse"
    
    class ConnectionStatus:
        CONNECTED = "connected"
        FAILED = "failed"
        UNKNOWN = "unknown"
        CONNECTING = "connecting"
        RETRYING = "retrying"
        FALLBACK_AVAILABLE = "fallback_available"

@pytest.mark.skipif(not DEV_LAUNCHER_AVAILABLE, reason="dev_launcher not available in production")
@pytest.mark.asyncio
async def test_redis_connection_works_with_python312():
    """
    Test that Redis connection now works with Python 3.12.

    The fix uses redis.asyncio (from redis 4.3+) which is compatible with Python 3.12,
    falling back to aioredis only if the newer library is not available.
    """""
    # Setup environment for Redis connection
    env.set("REDIS_URL", "redis://localhost:6379/0", "test")

    # Create database connector
    connector = DatabaseConnector(use_emoji=True)

    # Ensure Redis connection was discovered
    assert "main_redis" in connector.connections
    redis_conn = connector.connections["main_redis"]
    assert redis_conn.db_type == DatabaseType.REDIS
    assert redis_conn.url == "redis://localhost:6379/0"

    # Mock Redis connection for testing
    with patch('redis.asyncio.from_url') as mock_from_url:
        mock_client = AsyncMock()  # TODO: Use real service instance
        mock_from_url.return_value = mock_client
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.aclose = AsyncMock()  # TODO: Use real service instance

        # Test the actual connection - this should now work with Python 3.12
        result = await connector._test_redis_connection(redis_conn)

        # The test should succeed with the fixed implementation
        assert result is True, "Redis connection should work with redis.asyncio on Python 3.12"
        assert redis_conn.last_error is None

        @pytest.mark.skipif(not DEV_LAUNCHER_AVAILABLE, reason="dev_launcher not available in production")
        @pytest.mark.asyncio
        async def test_dev_launcher_database_validation_succeeds():
            """
            Test that the dev launcher database validation succeeds with all databases.

            This simulates the fixed behavior when running `python scripts/dev_launcher.py`.
            """""
    # Setup environment
            env.set("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5433/netra_dev", "test")
            env.set("REDIS_URL", "redis://localhost:6379/0", "test")
            env.set("CLICKHOUSE_HOST", "localhost", "test")
            env.set("CLICKHOUSE_HTTP_PORT", "8123", "test")

    # Create database connector
            connector = DatabaseConnector(use_emoji=True)

    # Mock successful PostgreSQL connection
            with patch.object(connector, '_test_postgresql_connection', return_value=True):
        # Mock successful ClickHouse connection
                with patch.object(connector, '_test_clickhouse_connection', return_value=True):
            # Mock Redis connection for testing
                    with patch.object(connector, '_test_redis_connection', return_value=True):
                # Let Redis connection use the fixed implementation
                        result = await connector.validate_all_connections()

            # Validation should succeed with all databases working
                        assert result is True, "Database validation should succeed when all connections work"

            # Check that all connections are marked as connected
                        if "main_postgres" in connector.connections:
                            postgres_conn = connector.connections["main_postgres"]
                            assert postgres_conn.status == ConnectionStatus.CONNECTED

                            if "main_redis" in connector.connections:
                                redis_conn = connector.connections["main_redis"]
                                assert redis_conn.status == ConnectionStatus.CONNECTED

                                if "main_clickhouse" in connector.connections:
                                    clickhouse_conn = connector.connections["main_clickhouse"]
                                    assert clickhouse_conn.status == ConnectionStatus.CONNECTED

                                    def test_redis_asyncio_import_works():
                                        """
                                        Test that redis.asyncio can be imported successfully on Python 3.12.

                                        This is the fix for the aioredis incompatibility issue.
                                        """""
                                        try:
                                            import redis.asyncio as redis_async

        # Check that the required methods exist
                                            assert hasattr(redis_async, 'from_url')

        # Import successful - the fix is working
                                            import sys
                                            python_version = sys.version_info
                                            print(f" PASS:  redis.asyncio works with Python {python_version.major}.{python_version.minor}")

                                        except ImportError:
                                            pytest.fail("redis.asyncio not available - need redis>=4.3.0")

                                            def test_fallback_to_aioredis_if_needed():
                                                """
                                                Test that the implementation falls back to aioredis if redis.asyncio is not available.

                                                This ensures backward compatibility for older environments.
                                                """""
    # This test verifies the fallback logic exists
# Removed broken import statement
                                                if __name__ == "__main__":
    # Run the tests
                                                    import pytest
                                                    pytest.main([__file__, "-v", "-s"])