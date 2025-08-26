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
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from typing import Dict, Optional, Tuple
import os

from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus
from dev_launcher.network_resilience import NetworkResilientClient, RetryPolicy, NetworkErrorType
from dev_launcher.launcher import DevLauncher
from dev_launcher.config import LauncherConfig


class TestClickHousePortMismatchFailures:
    """
    Test suite for ClickHouse port mismatch failures.
    
    ClickHouse has two main protocols:
    - Native protocol (default port 9000) - used by clickhouse-client and some drivers
    - HTTP protocol (default port 8123) - used by REST API and health checks
    
    The issue occurs when the URL uses port 9000 but health checks try to connect via HTTP.
    """

    @pytest.fixture
    def mock_env_clickhouse_native_port(self):
        """Mock environment with ClickHouse configured for native protocol port."""
        return {
            'CLICKHOUSE_HOST': 'localhost',
            'CLICKHOUSE_PORT': '9000',  # Native protocol port
            'CLICKHOUSE_HTTP_PORT': '8123',  # HTTP port (for health checks)
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': 'test_password',
            'CLICKHOUSE_DB': 'default',
            'ENVIRONMENT': 'development'
        }

    @pytest.mark.asyncio
    async def test_clickhouse_port_mismatch_native_url_http_health_check(self, mock_env_clickhouse_native_port):
        """
        Test ClickHouse connection failure when URL uses native port (9000) 
        but health checks expect HTTP port (8123).
        
        This test SHOULD FAIL with current implementation due to the port mismatch.
        """
        with patch('dev_launcher.database_connector.get_env') as mock_get_env, \
             patch.object(DatabaseConnector, '_ensure_env_loaded'):  # Skip environment loading
            # Mock environment manager
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env_clickhouse_native_port
            env_mock.get.side_effect = lambda key, default=None: mock_env_clickhouse_native_port.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Create database connector
            connector = DatabaseConnector(use_emoji=False)
            
            # Mock aiohttp to simulate the port mismatch issue
            with patch('aiohttp.ClientSession') as mock_session:
                # Configure mock to simulate connection refused on port 9000 via HTTP
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.__aenter__ = AsyncMock(return_value=mock_response)
                mock_response.__aexit__ = AsyncMock(return_value=None)
                
                # Simulate connection error when trying HTTP on native protocol port
                async def mock_get(*args, **kwargs):
                    url = args[0] if args else kwargs.get('url', '')
                    if ':9000' in url and '/ping' in url:
                        # This is the issue: trying HTTP ping on native protocol port
                        raise ConnectionError("Connection refused - wrong protocol for port")
                    return mock_response
                
                mock_session.return_value.__aenter__.return_value.get = mock_get
                
                # Test validation - this should FAIL due to port mismatch
                result = await connector.validate_all_connections()
                
                # Assert that validation fails due to ClickHouse port mismatch
                assert result is False, "Expected validation to fail due to ClickHouse port mismatch"
                
                # Check that ClickHouse connection is marked as failed or fallback available
                clickhouse_conn = connector.connections.get('main_clickhouse')
                assert clickhouse_conn is not None
                assert clickhouse_conn.status in [ConnectionStatus.FAILED, ConnectionStatus.FALLBACK_AVAILABLE]
                assert 'wrong protocol' in clickhouse_conn.last_error.lower() or 'connection refused' in clickhouse_conn.last_error.lower()

    @pytest.mark.asyncio
    async def test_clickhouse_url_construction_uses_wrong_port_for_http(self, mock_env_clickhouse_native_port):
        """
        Test that ClickHouse URL construction incorrectly uses native port for HTTP health checks.
        
        This test SHOULD FAIL because the current implementation might construct URLs
        using the wrong port for HTTP-based health checks.
        """
        with patch('dev_launcher.database_connector.get_env') as mock_get_env, \
             patch.object(DatabaseConnector, '_ensure_env_loaded'):  # Skip environment loading
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env_clickhouse_native_port
            env_mock.get.side_effect = lambda key, default=None: mock_env_clickhouse_native_port.get(key, default)
            mock_get_env.return_value = env_mock
            
            connector = DatabaseConnector(use_emoji=False)
            
            # Get the constructed ClickHouse connection
            clickhouse_conn = connector.connections.get('main_clickhouse')
            assert clickhouse_conn is not None
            
            # The URL should use HTTP port (8123) for health checks, not native port (9000)
            # This assertion SHOULD FAIL if the implementation incorrectly uses port 9000
            assert ':8123' in clickhouse_conn.url, f"ClickHouse URL should use HTTP port 8123, got: {clickhouse_conn.url}"

    @pytest.mark.asyncio
    async def test_clickhouse_health_check_on_wrong_protocol_port_timeout(self, mock_env_clickhouse_native_port):
        """
        Test that ClickHouse health check times out when trying HTTP on native protocol port.
        
        This test SHOULD FAIL due to timeout/connection issues when HTTP health check
        is attempted on the native protocol port.
        """
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env_clickhouse_native_port
            env_mock.get.side_effect = lambda key, default=None: mock_env_clickhouse_native_port.get(key, default)
            mock_get_env.return_value = env_mock
            
            connector = DatabaseConnector(use_emoji=False)
            
            # Mock aiohttp to simulate timeout on wrong port
            with patch('aiohttp.ClientSession') as mock_session:
                async def mock_get_timeout(*args, **kwargs):
                    # Simulate timeout when trying HTTP on native protocol port
                    raise asyncio.TimeoutError("HTTP health check timeout on native protocol port")
                
                mock_session.return_value.__aenter__.return_value.get = mock_get_timeout
                mock_session.return_value.__aexit__ = AsyncMock()
                
                # Test individual ClickHouse connection - should fail with timeout
                clickhouse_conn = connector.connections.get('main_clickhouse')
                success = await connector._test_clickhouse_connection(clickhouse_conn)
                
                # This should FAIL due to timeout
                assert success is False, "Expected ClickHouse connection test to fail due to timeout"
                assert 'timeout' in clickhouse_conn.last_error.lower()


class TestPostgreSQLConnectionFailures:
    """
    Test suite for PostgreSQL connection failures.
    
    Tests scenarios where PostgreSQL is configured with non-standard ports
    or unavailable databases, leading to connection failures.
    """

    @pytest.fixture
    def mock_env_postgres_nonstandard_port(self):
        """Mock environment with PostgreSQL on non-standard port."""
        return {
            'DATABASE_URL': 'postgresql://test_user:test_pass@localhost:5433/test_db',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5433',  # Non-standard port
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'POSTGRES_DB': 'test_db',
            'ENVIRONMENT': 'development'
        }

    @pytest.fixture  
    def mock_env_postgres_unavailable(self):
        """Mock environment with PostgreSQL that doesn't exist."""
        return {
            'DATABASE_URL': 'postgresql://user:pass@nonexistent_host:5432/nonexistent_db',
            'POSTGRES_HOST': 'nonexistent_host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'user',
            'POSTGRES_PASSWORD': 'pass', 
            'POSTGRES_DB': 'nonexistent_db',
            'ENVIRONMENT': 'development'
        }

    @pytest.mark.asyncio
    async def test_postgres_connection_refused_nonstandard_port(self, mock_env_postgres_nonstandard_port):
        """
        Test PostgreSQL connection failure when database is not running on configured port.
        
        This test SHOULD FAIL because it simulates PostgreSQL not being available 
        on the configured non-standard port (5433).
        """
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env_postgres_nonstandard_port
            env_mock.get.side_effect = lambda key, default=None: mock_env_postgres_nonstandard_port.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Mock DatabaseURLBuilder to return the configured URL
            with patch('dev_launcher.database_connector.DatabaseURLBuilder') as mock_builder:
                builder_instance = MagicMock()
                builder_instance.get_url_for_environment.return_value = mock_env_postgres_nonstandard_port['DATABASE_URL']
                mock_builder.return_value = builder_instance
                
                connector = DatabaseConnector(use_emoji=False)
                
                # Mock asyncpg to simulate connection refused
                with patch('asyncpg.connect') as mock_connect:
                    mock_connect.side_effect = ConnectionRefusedError("Connection refused on port 5433")
                    
                    # Test validation - should FAIL
                    result = await connector.validate_all_connections()
                    
                    # Assert that validation fails due to PostgreSQL connection refusal
                    assert result is False, "Expected validation to fail due to PostgreSQL connection refused"
                    
                    # Check PostgreSQL connection status
                    postgres_conn = connector.connections.get('main_postgres')
                    assert postgres_conn is not None
                    assert postgres_conn.status == ConnectionStatus.FAILED
                    assert 'connection refused' in postgres_conn.last_error.lower()

    @pytest.mark.asyncio
    async def test_postgres_database_does_not_exist(self, mock_env_postgres_unavailable):
        """
        Test PostgreSQL failure when connecting to non-existent database/host.
        
        This test SHOULD FAIL because it simulates connecting to a database
        that doesn't exist.
        """
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env_postgres_unavailable
            env_mock.get.side_effect = lambda key, default=None: mock_env_postgres_unavailable.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Mock DatabaseURLBuilder
            with patch('dev_launcher.database_connector.DatabaseURLBuilder') as mock_builder:
                builder_instance = MagicMock()
                builder_instance.get_url_for_environment.return_value = mock_env_postgres_unavailable['DATABASE_URL']
                mock_builder.return_value = builder_instance
                
                connector = DatabaseConnector(use_emoji=False)
                
                # Mock asyncpg to simulate database does not exist
                with patch('asyncpg.connect') as mock_connect:
                    import asyncpg
                    # Simulate the specific error PostgreSQL returns for non-existent databases
                    mock_connect.side_effect = asyncpg.InvalidCatalogNameError("database \"nonexistent_db\" does not exist")
                    
                    # Test individual PostgreSQL connection
                    postgres_conn = connector.connections.get('main_postgres')
                    success = await connector._test_postgresql_connection(postgres_conn)
                    
                    # This should FAIL due to non-existent database
                    assert success is False, "Expected PostgreSQL connection to fail due to non-existent database"
                    assert 'does not exist' in postgres_conn.last_error

    @pytest.mark.asyncio
    async def test_postgres_authentication_failure(self):
        """
        Test PostgreSQL authentication failure with wrong credentials.
        
        This test SHOULD FAIL because it simulates authentication failure.
        """
        mock_env = {
            'DATABASE_URL': 'postgresql://wrong_user:wrong_pass@localhost:5432/test_db',
            'ENVIRONMENT': 'development'
        }
        
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env
            env_mock.get.side_effect = lambda key, default=None: mock_env.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Mock DatabaseURLBuilder
            with patch('dev_launcher.database_connector.DatabaseURLBuilder') as mock_builder:
                builder_instance = MagicMock()
                builder_instance.get_url_for_environment.return_value = mock_env['DATABASE_URL']
                mock_builder.return_value = builder_instance
                
                connector = DatabaseConnector(use_emoji=False)
                
                # Mock asyncpg to simulate authentication failure
                with patch('asyncpg.connect') as mock_connect:
                    import asyncpg
                    mock_connect.side_effect = asyncpg.InvalidAuthorizationSpecificationError("password authentication failed for user \"wrong_user\"")
                    
                    # Test individual PostgreSQL connection
                    postgres_conn = connector.connections.get('main_postgres')
                    success = await connector._test_postgresql_connection(postgres_conn)
                    
                    # This should FAIL due to authentication failure
                    assert success is False, "Expected PostgreSQL connection to fail due to authentication failure"
                    assert 'authentication failed' in postgres_conn.last_error


class TestResilientValidationCascadeFailures:
    """
    Test suite for resilient validation cascade failures.
    
    Tests scenarios where the resilient validation system fails to handle
    multiple database failures and doesn't fall back properly.
    """

    @pytest.fixture
    def mock_env_all_databases_failing(self):
        """Mock environment where all databases are configured but failing."""
        return {
            'DATABASE_URL': 'postgresql://user:pass@unreachable:5432/db',
            'REDIS_URL': 'redis://unreachable:6379/0', 
            'CLICKHOUSE_URL': 'clickhouse://unreachable:9000/default',
            'CLICKHOUSE_HOST': 'unreachable',
            'CLICKHOUSE_PORT': '9000',
            'CLICKHOUSE_HTTP_PORT': '8123',
            'ENVIRONMENT': 'development'
        }

    @pytest.mark.asyncio
    async def test_resilient_validation_cascade_fails_all_databases(self, mock_env_all_databases_failing):
        """
        Test that resilient validation cascade fails when all databases are unreachable.
        
        This test SHOULD FAIL because the resilient validation should handle
        multiple database failures gracefully, but currently it doesn't.
        """
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env_all_databases_failing
            env_mock.get.side_effect = lambda key, default=None: mock_env_all_databases_failing.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Mock DatabaseURLBuilder
            with patch('dev_launcher.database_connector.DatabaseURLBuilder') as mock_builder:
                builder_instance = MagicMock()
                builder_instance.get_url_for_environment.return_value = mock_env_all_databases_failing['DATABASE_URL']
                mock_builder.return_value = builder_instance
                
                connector = DatabaseConnector(use_emoji=False)
                
                # Mock all database connections to fail
                with patch('asyncpg.connect') as mock_pg_connect, \
                     patch('aiohttp.ClientSession') as mock_http_session, \
                     patch('redis.asyncio.from_url') as mock_redis_from_url:
                    
                    # PostgreSQL fails
                    mock_pg_connect.side_effect = ConnectionRefusedError("Connection refused")
                    
                    # ClickHouse fails  
                    mock_http_get = AsyncMock()
                    mock_http_get.side_effect = ConnectionRefusedError("Connection refused")
                    mock_http_session.return_value.__aenter__.return_value.get = mock_http_get
                    
                    # Redis fails
                    mock_redis_client = AsyncMock()
                    mock_redis_client.ping.side_effect = ConnectionRefusedError("Connection refused")
                    mock_redis_from_url.return_value = mock_redis_client
                    
                    # Test validation - should handle cascade failure gracefully
                    # But current implementation might not handle this correctly
                    result = await connector.validate_all_connections()
                    
                    # This should FAIL if resilient cascade handling is broken
                    # The system should continue even if all databases fail, but it might not
                    assert result is False, "Expected validation to fail when all databases are unreachable"
                    
                    # Check that all connections are properly marked as failed or fallback available
                    postgres_conn = connector.connections.get('main_postgres')
                    clickhouse_conn = connector.connections.get('main_clickhouse') 
                    redis_conn = connector.connections.get('main_redis')
                    
                    if postgres_conn:
                        assert postgres_conn.status in [ConnectionStatus.FAILED, ConnectionStatus.FALLBACK_AVAILABLE]
                    if clickhouse_conn:
                        assert clickhouse_conn.status in [ConnectionStatus.FAILED, ConnectionStatus.FALLBACK_AVAILABLE]
                    if redis_conn:
                        assert redis_conn.status in [ConnectionStatus.FAILED, ConnectionStatus.FALLBACK_AVAILABLE]

    @pytest.mark.asyncio
    async def test_network_resilient_client_exceeds_retry_limits(self):
        """
        Test that network resilient client fails when retry limits are exceeded.
        
        This test SHOULD FAIL because the retry mechanism should eventually
        give up after max attempts, but the error handling might not be correct.
        """
        client = NetworkResilientClient(use_emoji=False)
        
        # Mock all database checks to fail consistently
        with patch.object(client, '_check_database_specific') as mock_check:
            mock_check.side_effect = ConnectionRefusedError("Persistent connection failure")
            
            # Test with aggressive retry policy
            retry_policy = RetryPolicy(
                max_attempts=3,
                initial_delay=0.1,  # Fast for testing
                max_delay=0.5,
                timeout_per_attempt=1.0
            )
            
            # This should eventually fail after exhausting retries
            success, error = await client.resilient_database_check(
                'postgresql://user:pass@unreachable:5432/db',
                db_type='postgresql',
                retry_policy=retry_policy
            )
            
            # Should FAIL after retries are exhausted
            assert success is False, "Expected database check to fail after retry exhaustion"
            assert 'failed after 3 attempts' in error
            
            # Verify that exactly 3 attempts were made
            assert mock_check.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_handling_in_cascade_validation(self, mock_env_all_databases_failing):
        """
        Test that cascade validation properly handles timeout scenarios.
        
        This test SHOULD FAIL if timeout handling in the validation cascade
        is not properly implemented.
        """
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env_all_databases_failing
            env_mock.get.side_effect = lambda key, default=None: mock_env_all_databases_failing.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Mock DatabaseURLBuilder
            with patch('dev_launcher.database_connector.DatabaseURLBuilder') as mock_builder:
                builder_instance = MagicMock()
                builder_instance.get_url_for_environment.return_value = mock_env_all_databases_failing['DATABASE_URL']
                mock_builder.return_value = builder_instance
                
                connector = DatabaseConnector(use_emoji=False)
                
                # Mock all connections to timeout
                with patch('asyncpg.connect') as mock_pg_connect, \
                     patch('aiohttp.ClientSession') as mock_http_session, \
                     patch('redis.asyncio.from_url') as mock_redis:
                    
                    # All database connections timeout
                    mock_pg_connect.side_effect = asyncio.TimeoutError("Connection timeout")
                    
                    mock_http_get = AsyncMock()
                    mock_http_get.side_effect = asyncio.TimeoutError("HTTP timeout") 
                    mock_http_session.return_value.__aenter__.return_value.get = mock_http_get
                    
                    mock_redis_client = AsyncMock()
                    mock_redis_client.ping.side_effect = asyncio.TimeoutError("Redis timeout")
                    mock_redis.return_value = mock_redis_client
                    
                    # Test that validation handles timeouts correctly
                    # This might FAIL if timeout handling is broken
                    result = await connector.validate_all_connections()
                    
                    # Should handle timeouts gracefully
                    assert result is False, "Expected validation to fail due to timeouts"
                    
                    # Check that timeout errors are properly recorded
                    for conn_name, conn in connector.connections.items():
                        if conn.last_error:
                            assert 'timeout' in conn.last_error.lower(), f"Expected timeout error for {conn_name}, got: {conn.last_error}"


class TestDatabaseConnectorRetryBehavior:
    """
    Test suite for database connector retry behavior.
    
    Tests that retry logic works correctly and fails appropriately.
    """

    @pytest.mark.asyncio
    async def test_retry_backoff_exceeds_max_delay(self):
        """
        Test that retry backoff calculation respects max delay limits.
        
        This test SHOULD FAIL if retry backoff calculation is incorrect.
        """
        connector = DatabaseConnector(use_emoji=False)
        
        # Test exponential backoff calculation
        retry_config = connector.retry_config
        
        # Calculate delays for multiple attempts
        delays = []
        for attempt in range(10):  # Test many attempts
            delay = connector._calculate_retry_delay(attempt)
            delays.append(delay)
        
        # Later delays should not exceed max_delay
        max_delay = retry_config.max_delay
        excessive_delays = [d for d in delays if d > max_delay]
        
        # This should FAIL if backoff calculation doesn't respect max_delay
        assert len(excessive_delays) == 0, f"Found delays exceeding max_delay ({max_delay}): {excessive_delays}"

    @pytest.mark.asyncio  
    async def test_connection_failure_count_tracking(self):
        """
        Test that connection failure counts are properly tracked.
        
        This test SHOULD FAIL if failure counting logic is broken.
        """
        mock_env = {
            'DATABASE_URL': 'postgresql://user:pass@unreachable:5432/db',
            'ENVIRONMENT': 'development'
        }
        
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env
            env_mock.get.side_effect = lambda key, default=None: mock_env.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Mock DatabaseURLBuilder
            with patch('dev_launcher.database_connector.DatabaseURLBuilder') as mock_builder:
                builder_instance = MagicMock()
                builder_instance.get_url_for_environment.return_value = mock_env['DATABASE_URL']
                mock_builder.return_value = builder_instance
                
                connector = DatabaseConnector(use_emoji=False)
                
                # Mock PostgreSQL to always fail
                with patch('asyncpg.connect') as mock_connect:
                    mock_connect.side_effect = ConnectionRefusedError("Connection refused")
                    
                    # Test validation
                    await connector.validate_all_connections()
                    
                    # Check failure count tracking
                    postgres_conn = connector.connections.get('main_postgres')
                    assert postgres_conn is not None
                    
                    # Should have recorded failures (should be > 0)
                    # This might FAIL if failure counting is broken
                    assert postgres_conn.failure_count > 0, f"Expected failure count > 0, got: {postgres_conn.failure_count}"
                    assert postgres_conn.retry_count > 0, f"Expected retry count > 0, got: {postgres_conn.retry_count}"


class TestDatabaseConnectorFallbackBehavior:
    """
    Test suite for database connector fallback behavior.
    
    Tests scenarios where fallback mechanisms should activate but might fail.
    """

    @pytest.mark.asyncio
    async def test_clickhouse_fallback_mode_not_activated(self):
        """
        Test that ClickHouse fallback mode is properly activated on connection failure.
        
        This test SHOULD FAIL if ClickHouse fallback logic is not working correctly.
        """
        mock_env = {
            'CLICKHOUSE_URL': 'clickhouse://unreachable:9000/default',
            'CLICKHOUSE_HOST': 'unreachable', 
            'CLICKHOUSE_PORT': '9000',
            'CLICKHOUSE_HTTP_PORT': '8123',
            'ENVIRONMENT': 'development'
        }
        
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env
            env_mock.get.side_effect = lambda key, default=None: mock_env.get(key, default)
            mock_get_env.return_value = env_mock
            
            connector = DatabaseConnector(use_emoji=False)
            
            # Mock ClickHouse to fail
            with patch('aiohttp.ClientSession') as mock_session:
                mock_get = AsyncMock()
                mock_get.side_effect = ConnectionRefusedError("ClickHouse unreachable")
                mock_session.return_value.__aenter__.return_value.get = mock_get
                
                # Test validation
                result = await connector.validate_all_connections()
                
                # Check that ClickHouse is marked as FALLBACK_AVAILABLE, not just FAILED
                clickhouse_conn = connector.connections.get('main_clickhouse')
                assert clickhouse_conn is not None
                
                # This should FAIL if fallback logic doesn't work properly
                assert clickhouse_conn.status == ConnectionStatus.FALLBACK_AVAILABLE, \
                    f"Expected ClickHouse status to be FALLBACK_AVAILABLE, got: {clickhouse_conn.status}"

    @pytest.mark.asyncio
    async def test_database_url_normalization_breaks_connections(self):
        """
        Test that database URL normalization doesn't break actual connections.
        
        This test SHOULD FAIL if URL normalization logic is incorrect.
        """
        # Test with SQLAlchemy-style URL that needs normalization
        mock_env = {
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost:5432/db',
            'ENVIRONMENT': 'development'
        }
        
        with patch('dev_launcher.database_connector.get_env') as mock_get_env:
            env_mock = MagicMock()
            env_mock.get_all.return_value = mock_env
            env_mock.get.side_effect = lambda key, default=None: mock_env.get(key, default)
            mock_get_env.return_value = env_mock
            
            # Mock DatabaseURLBuilder to test normalization
            with patch('dev_launcher.database_connector.DatabaseURLBuilder') as mock_builder:
                builder_instance = MagicMock()
                builder_instance.get_url_for_environment.return_value = mock_env['DATABASE_URL']
                mock_builder.return_value = builder_instance
                
                # Mock format_for_asyncpg_driver method
                mock_builder.format_for_asyncpg_driver.return_value = 'postgresql://user:pass@localhost:5432/db'
                
                connector = DatabaseConnector(use_emoji=False)
                
                # Get normalized URL
                postgres_conn = connector.connections.get('main_postgres')
                normalized_url = connector._normalize_postgres_url(postgres_conn.url)
                
                # This should FAIL if normalization breaks the URL
                assert normalized_url.startswith('postgresql://'), f"Normalized URL should start with postgresql://, got: {normalized_url}"
                assert 'asyncpg' not in normalized_url, f"Normalized URL should not contain 'asyncpg', got: {normalized_url}"


if __name__ == '__main__':
    # Run tests with verbose output to see failure details
    pytest.main([__file__, '-v', '--tb=short'])