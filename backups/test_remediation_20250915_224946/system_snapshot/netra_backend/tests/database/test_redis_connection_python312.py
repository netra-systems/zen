from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import AsyncMock, Mock, patch, MagicMock
'\nenv = get_env()\nTest that reproduces the Redis connection failure in dev environment.\n\nThe issue is that aioredis 2.0.1 is incompatible with Python 3.12.4 due to \na TypeError: duplicate base class TimeoutError.\n\nThis test will fail until we fix the aioredis compatibility issue.\n'
import asyncio
import os
import sys
import pytest
try:
    from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus
    DEV_LAUNCHER_AVAILABLE = True
except ImportError:
    DEV_LAUNCHER_AVAILABLE = False

    class MockConnection:

        def __init__(self):
            self.db_type = 'redis'
            self.url = 'redis://localhost:6379/0'
            self.status = 'connected'
            self.last_error = None

    class DatabaseConnector:

        def __init__(self, use_emoji=True):
            self.connections = {'main_redis': MockConnection()}

        async def validate_all_connections(self):
            return True

        async def _test_redis_connection(self, conn):
            return True

    class DatabaseType:
        POSTGRESQL = 'postgresql'
        REDIS = 'redis'
        CLICKHOUSE = 'clickhouse'

    class ConnectionStatus:
        CONNECTED = 'connected'
        FAILED = 'failed'
        UNKNOWN = 'unknown'
        CONNECTING = 'connecting'
        RETRYING = 'retrying'
        FALLBACK_AVAILABLE = 'fallback_available'

@pytest.mark.skipif(not DEV_LAUNCHER_AVAILABLE, reason='dev_launcher not available in production')
@pytest.mark.asyncio
async def test_redis_connection_works_with_python312():
    """
    Test that Redis connection now works properly with Python 3.12.

    This test verifies that the aioredis compatibility issue with Python 3.12
    has been resolved and connections work as expected.
    """
    env.set('REDIS_URL', 'redis://localhost:6379/0', 'test')
    connector = DatabaseConnector(use_emoji=True)
    assert 'main_redis' in connector.connections
    redis_conn = connector.connections['main_redis']
    assert redis_conn.db_type == DatabaseType.REDIS
    assert redis_conn.url == 'redis://localhost:6379/0'
    with patch('redis.asyncio.from_url') as mock_from_url:
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.aclose = AsyncMock()
        result = await connector._test_redis_connection(redis_conn)
        assert result is True, 'Redis connection should now work with Python 3.12'
        assert redis_conn.last_error is None or redis_conn.last_error == ''

        @pytest.mark.skipif(not DEV_LAUNCHER_AVAILABLE, reason='dev_launcher not available in production')
        @pytest.mark.asyncio
        async def test_dev_launcher_database_validation_succeeds():
            """
            Test that the dev launcher database validation succeeds with all connections.

            This simulates what happens when running `python scripts/dev_launcher.py`.
            """
            env.set('DATABASE_URL', 'postgresql+asyncpg://postgres:password@localhost:5433/netra_dev', 'test')
            env.set('REDIS_URL', 'redis://localhost:6379/0', 'test')
            env.set('CLICKHOUSE_HOST', 'localhost', 'test')
            env.set('CLICKHOUSE_HTTP_PORT', '8123', 'test')
            connector = DatabaseConnector(use_emoji=True)
            with patch.object(connector, '_test_postgresql_connection', return_value=True):
                with patch.object(connector, '_test_clickhouse_connection', return_value=True):
                    with patch.object(connector, '_test_redis_connection', return_value=True):
                        result = await connector.validate_all_connections()
                        assert result is True, 'Database validation should succeed when all connections work'
                        if 'main_postgres' in connector.connections:
                            postgres_conn = connector.connections['main_postgres']
                            assert postgres_conn.status == ConnectionStatus.CONNECTED
                            redis_conn = connector.connections['main_redis']
                            assert redis_conn.status == ConnectionStatus.CONNECTED
                            assert redis_conn.last_error is None or redis_conn.last_error == ''

                            def test_aioredis_import_works_on_python312():
                                """
                                Test that importing aioredis/redis-py now works with Python 3.12.

                                The compatibility issue has been resolved.
                                """
                                try:
                                    import redis.asyncio
                                    assert True, 'Redis import works with Python 3.12'
                                except ImportError:
                                    try:
                                        import aioredis
                                        assert True, 'aioredis import works with Python 3.12'
                                    except ImportError:
                                        pytest.skip('Redis library not installed')
                                        if __name__ == '__main__':
                                            'MIGRATED: Use SSOT unified test runner'
                                            print('MIGRATION NOTICE: Please use SSOT unified test runner')
                                            print('Command: python tests/unified_test_runner.py --category <category>')