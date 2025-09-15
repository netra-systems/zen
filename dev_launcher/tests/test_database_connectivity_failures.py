"""
Test suite for reproducing database connectivity failures in DevLauncher.

This test suite creates failing tests that reproduce the specific database 
connectivity issues experienced during DevLauncher initialization:

1. ClickHouse connection fails due to port mismatch (using port 9000 for native protocol in URL but health checks expect HTTP on port 8123)
2. PostgreSQL initialization fails with "Cannot connect to PostgreSQL" when using port 5433  
3. Resilient validation cascade fails after retries

These tests are designed to FAIL with the current implementation to prove they 
correctly reproduce the issues. They serve as regression tests that will pass
once the issues are fixed.

Business Value:
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Stability  
- Value Impact: Prevents database connection startup failures that block development
- Strategic Impact: Reduces developer friction and improves time-to-productivity
"""
import asyncio
import pytest
from pathlib import Path
from typing import Dict, Optional, Tuple
import os
from shared.isolated_environment import IsolatedEnvironment
from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus
from dev_launcher.network_resilience import NetworkResilientClient, RetryPolicy

class TestClickHousePortMismatchFailures:
    """
    Test suite for ClickHouse port mismatch failures.
    
    ClickHouse has two main protocols:
    - Native protocol (default port 9000) - used by clickhouse-client and some drivers
    - HTTP protocol (default port 8123) - used by REST API and health checks
    
    The issue occurs when the URL uses port 9000 but health checks try to connect via HTTP.
    """

    @pytest.mark.asyncio
    async def test_clickhouse_http_ping_on_native_port_fails(self):
        """
        Test ClickHouse connection failure when trying HTTP ping on native protocol port.
        
        This test SHOULD FAIL because the current implementation attempts to use
        HTTP health checks on port 9000 (native protocol) instead of port 8123 (HTTP).
        """
        connector = DatabaseConnector(use_emoji=False)
        with patch('aiohttp.ClientSession') as mock_session:

            async def mock_get(*args, **kwargs):
                url = args[0] if args else kwargs.get('url', '')
                if ':9000' in url and '/ping' in url:
                    raise ConnectionError('Connection refused - HTTP on native protocol port')
                elif ':8123' in url:
                    mock_response = AsyncMock()
                    mock_response.status = 200
                    return mock_response
                else:
                    raise ConnectionError('Unexpected URL format')
            mock_session.return_value.__aenter__.return_value.get = mock_get
            mock_session.return_value.__aexit__ = AsyncMock()
            clickhouse_url = 'http://localhost:9000/default'
            connection = connector.connections.get('main_clickhouse')
            if not connection:
                connector._add_connection('test_clickhouse', DatabaseType.CLICKHOUSE, clickhouse_url)
                connection = connector.connections.get('test_clickhouse')
            success = await connector._test_clickhouse_connection(connection)
            assert success is False, 'Expected ClickHouse connection test to fail due to port mismatch'
            assert connection.last_error is not None
            assert 'connection' in connection.last_error.lower() or 'refused' in connection.last_error.lower()

    @pytest.mark.asyncio
    async def test_clickhouse_url_should_use_http_port_for_health_checks(self):
        """
        Test that ClickHouse URL construction should use HTTP port (8123) for health checks.
        
        This test verifies the expectation that health checks should use the HTTP interface,
        not the native protocol interface.
        """
        connector = DatabaseConnector(use_emoji=False)
        clickhouse_url = connector._construct_clickhouse_url_from_env()
        if clickhouse_url:
            from urllib.parse import urlparse
            parsed = urlparse(clickhouse_url)
            expected_http_port = 8123
            if parsed.port and parsed.port != expected_http_port:
                pytest.fail(f'ClickHouse URL uses port {parsed.port}, expected {expected_http_port} for HTTP health checks')

class TestPostgreSQLConnectionFailures:
    """
    Test suite for PostgreSQL connection failures.
    
    Tests scenarios where PostgreSQL connections fail due to configuration issues.
    """

    @pytest.mark.asyncio
    async def test_postgres_connection_with_asyncpg_import_error(self):
        """
        Test PostgreSQL connection handling when asyncpg is not available.
        
        This test SHOULD document behavior when asyncpg import fails.
        """
        connector = DatabaseConnector(use_emoji=False)
        postgres_url = 'postgresql://user:pass@localhost:5432/testdb'
        connector._add_connection('test_postgres', DatabaseType.POSTGRESQL, postgres_url)
        connection = connector.connections.get('test_postgres')
        with patch('builtins.__import__') as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == 'asyncpg':
                    raise ImportError("No module named 'asyncpg'")
                return __import__(name, *args, **kwargs)
            mock_import.side_effect = import_side_effect
            success = await connector._test_postgresql_connection(connection)
            assert isinstance(success, bool), 'Expected boolean result from PostgreSQL connection test'

    @pytest.mark.asyncio
    async def test_postgres_connection_refused_error_handling(self):
        """
        Test that PostgreSQL connection refusal is handled properly.
        
        This test SHOULD FAIL if connection refusal isn't handled gracefully.
        """
        connector = DatabaseConnector(use_emoji=False)
        postgres_url = 'postgresql://user:pass@nonexistent_host:5432/db'
        connector._add_connection('failing_postgres', DatabaseType.POSTGRESQL, postgres_url)
        connection = connector.connections.get('failing_postgres')
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = ConnectionRefusedError('Connection refused')
            success = await connector._test_postgresql_connection(connection)
            assert success is False, 'Expected PostgreSQL connection to fail'
            assert connection.last_error is not None, 'Expected error to be recorded'
            assert 'refused' in connection.last_error.lower()

class TestDatabaseConnectorTimeoutHandling:
    """
    Test suite for database connector timeout handling.
    """

    @pytest.mark.asyncio
    async def test_database_connection_timeout_handling(self):
        """
        Test that database connection timeouts are handled properly.
        
        This test SHOULD FAIL if timeout handling is not implemented correctly.
        """
        connector = DatabaseConnector(use_emoji=False)
        test_url = 'postgresql://user:pass@slow_host:5432/db'
        connector._add_connection('timeout_test', DatabaseType.POSTGRESQL, test_url)
        connection = connector.connections.get('timeout_test')
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError('Connection timeout')
            success = await connector._test_postgresql_connection(connection)
            assert success is False, 'Expected connection to fail due to timeout'
            assert connection.last_error is not None
            assert 'timeout' in connection.last_error.lower()

    @pytest.mark.asyncio
    async def test_retry_mechanism_respects_timeout_limits(self):
        """
        Test that retry mechanism respects timeout limits properly.
        
        This test SHOULD FAIL if retry timeout logic is incorrect.
        """
        connector = DatabaseConnector(use_emoji=False)
        retry_config = connector.retry_config
        for attempt in range(10):
            delay = connector._calculate_retry_delay(attempt)
            assert delay <= retry_config.max_delay, f'Delay {delay} exceeds max_delay {retry_config.max_delay} at attempt {attempt}'
            assert delay >= 0, f'Delay should be non-negative, got {delay}'

class TestResilientValidationCascadeFailures:
    """
    Test suite for resilient validation cascade failures.
    """

    @pytest.mark.asyncio
    async def test_validation_cascade_with_all_databases_failing(self):
        """
        Test validation behavior when all databases fail.
        
        This test documents the expected behavior when all database connections fail.
        """
        connector = DatabaseConnector(use_emoji=False)
        failing_urls = [('failing_postgres', DatabaseType.POSTGRESQL, 'postgresql://user:pass@unreachable:5432/db'), ('failing_redis', DatabaseType.REDIS, 'redis://unreachable:6379/0'), ('failing_clickhouse', DatabaseType.CLICKHOUSE, 'http://unreachable:8123/default')]
        for name, db_type, url in failing_urls:
            connector._add_connection(name, db_type, url)
        with patch('asyncpg.connect') as mock_pg, patch('redis.asyncio.from_url') as mock_redis, patch('aiohttp.ClientSession') as mock_http:
            mock_pg.side_effect = ConnectionRefusedError('Postgres unreachable')
            mock_redis_client = AsyncMock()
            mock_redis_client.ping.side_effect = ConnectionRefusedError('Redis unreachable')
            mock_redis.return_value = mock_redis_client
            mock_http.return_value.__aenter__.return_value.get.side_effect = ConnectionRefusedError('ClickHouse unreachable')
            result = await connector.validate_all_connections()
            assert result is False, 'Expected validation to fail when all databases are unreachable'
            for name, _, _ in failing_urls:
                connection = connector.connections.get(name)
                if connection:
                    assert connection.status in [ConnectionStatus.FAILED, ConnectionStatus.FALLBACK_AVAILABLE]

class TestNetworkResilientClientRetryBehavior:
    """
    Test suite for NetworkResilientClient retry behavior.
    """

    @pytest.mark.asyncio
    async def test_retry_policy_exhaustion_behavior(self):
        """
        Test that retry policy exhaustion is handled correctly.
        
        This test SHOULD FAIL if retry exhaustion logic is incorrect.
        """
        client = NetworkResilientClient(use_emoji=False)
        retry_policy = RetryPolicy(max_attempts=3, initial_delay=0.01, max_delay=0.05, timeout_per_attempt=0.1)
        with patch.object(client, '_check_database_specific') as mock_check:
            mock_check.side_effect = ConnectionRefusedError('Persistent failure')
            success, error = await client.resilient_database_check('postgresql://user:pass@unreachable:5432/db', db_type='postgresql', retry_policy=retry_policy)
            assert success is False, 'Expected database check to fail after retry exhaustion'
            assert error is not None, 'Expected error message'
            assert 'failed after' in error and '3 attempts' in error
            assert mock_check.call_count == 3, f'Expected 3 attempts, got {mock_check.call_count}'

    @pytest.mark.asyncio
    async def test_critical_database_error_stops_retries(self):
        """
        Test that critical database errors stop retries immediately.
        
        This test SHOULD FAIL if critical error detection is not working.
        """
        client = NetworkResilientClient(use_emoji=False)
        attempt_counter = [0]
        with patch.object(client, '_check_database_specific') as mock_check:

            def check_side_effect(*args, **kwargs):
                attempt_counter[0] += 1
                return (False, 'password authentication failed')
            mock_check.side_effect = check_side_effect
            success, error = await client.resilient_database_check('postgresql://user:wrongpass@localhost:5432/db', db_type='postgresql', retry_policy=RetryPolicy(max_attempts=5))
            assert success is False, 'Expected connection to fail due to critical error'
            assert 'Critical database error' in error
            assert attempt_counter[0] == 1, f'Expected 1 attempt for critical error, got {attempt_counter[0]}'

class TestDatabaseURLHandling:
    """
    Test suite for database URL handling and normalization.
    """

    def test_postgres_url_normalization_for_asyncpg(self):
        """
        Test that PostgreSQL URL normalization works correctly for asyncpg.
        
        This test SHOULD FAIL if URL normalization breaks asyncpg compatibility.
        """
        connector = DatabaseConnector(use_emoji=False)
        test_urls = ['postgresql+asyncpg://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db', 'postgres://user:pass@localhost:5432/db']
        for test_url in test_urls:
            normalized = connector._normalize_postgres_url(test_url)
            assert normalized.startswith('postgresql://'), f'Normalized URL should start with postgresql://, got: {normalized}'
            assert '+asyncpg' not in normalized, f"Normalized URL should not contain '+asyncpg', got: {normalized}"
            assert '+psycopg2' not in normalized, f"Normalized URL should not contain '+psycopg2', got: {normalized}"

    def test_clickhouse_url_construction_consistency(self):
        """
        Test that ClickHouse URL construction is consistent.
        
        This test documents expected ClickHouse URL format.
        """
        connector = DatabaseConnector(use_emoji=False)
        test_url = connector._construct_clickhouse_url_from_env()
        if test_url:
            from urllib.parse import urlparse
            parsed = urlparse(test_url)
            assert parsed.scheme in ['http', 'https'], f'Expected http/https scheme, got: {parsed.scheme}'
            assert parsed.hostname is not None, 'URL should have a hostname'
            assert parsed.port is not None, 'URL should have a port'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')