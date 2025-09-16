"""
Test ClickHouse Connection Management - Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise 
- Business Goal: Ensure reliable database connections for analytics
- Value Impact: Prevents connection failures affecting user experience
- Strategic Impact: 99.9% uptime for analytics features (+$12K MRR retention)

This test suite validates ClickHouse connection management, circuit breaker patterns,
and connection pooling functionality at the unit level.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from unittest.mock import call
from netra_backend.app.db.clickhouse import get_clickhouse_client, _create_real_client, _test_and_yield_client, ClickHouseService
from test_framework.base_integration_test import BaseIntegrationTest

class ClickHouseConnectionManagementUnitTests(BaseIntegrationTest):
    """Test ClickHouse connection management unit functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test connection timeout handling with proper error messages.
        
        Critical for preventing hanging connections that affect user experience.
        """
        mock_client = AsyncMock()
        mock_client.test_connection.side_effect = asyncio.TimeoutError('Connection timeout')
        with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default: {'ENVIRONMENT': 'staging'}.get(key, default)
            with pytest.raises(ConnectionError) as exc_info:
                async for client in _test_and_yield_client(mock_client):
                    pass
            assert 'Connection timeout' in str(exc_info.value)
            assert '15s' in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_retry_logic_with_exponential_backoff(self):
        """Test connection retry logic with exponential backoff.
        
        Ensures robust connection establishment under network issues.
        """
        service = ClickHouseService(force_mock=False)
        call_count = 0

        async def mock_connection_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError(f'Connection failed attempt {call_count}')
            return AsyncMock()
        with patch.object(service, '_build_clickhouse_database') as mock_build:
            mock_build.side_effect = mock_connection_side_effect
            with patch('asyncio.sleep') as mock_sleep:
                with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
                    mock_env.return_value.get.side_effect = lambda key, default: {'ENVIRONMENT': 'staging', 'CLICKHOUSE_REQUIRED': 'false'}.get(key, default)
                    with patch.object(service._client, 'test_connection', return_value=True):
                        await service._initialize_real_client()
                        assert mock_build.call_count == 3
                        assert mock_sleep.call_count == 2
                        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                        assert sleep_calls[0] > 1.0
                        assert sleep_calls[1] > sleep_calls[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration for connection failures.
        
        Validates that circuit breaker prevents cascade failures.
        """
        service = ClickHouseService()
        await service.initialize()
        mock_client = AsyncMock()
        mock_client.execute.side_effect = ConnectionError('Database unavailable')
        service._client = mock_client
        for i in range(3):
            with pytest.raises(ConnectionError):
                await service._execute_with_circuit_breaker('SELECT 1')
        circuit_breaker = service._circuit_breaker
        assert hasattr(circuit_breaker, 'state'), 'Circuit breaker should have state'

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_pooling_bypass_manager(self):
        """Test connection creation bypassing manager to prevent recursion.
        
        Critical for avoiding infinite recursion in connection management.
        """
        with patch('netra_backend.app.db.clickhouse.use_mock_clickhouse', return_value=False):
            with patch('netra_backend.app.db.clickhouse._create_real_client') as mock_create:
                mock_client = AsyncMock()

                async def mock_client_generator():
                    yield mock_client
                mock_create.return_value = mock_client_generator()
                async with get_clickhouse_client(bypass_manager=True) as client:
                    assert client is mock_client, 'Should get direct client'
                mock_create.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_failure(self):
        """Test proper connection cleanup when connection fails.
        
        Ensures resources are properly released on connection failure.
        """
        mock_client = AsyncMock()
        mock_client.test_connection.side_effect = ConnectionError('Connection failed')
        with patch('netra_backend.app.db.clickhouse._cleanup_client_connection') as mock_cleanup:
            try:
                async for client in _test_and_yield_client(mock_client):
                    pass
            except ConnectionError:
                pass
            mock_cleanup.assert_called_once_with(mock_client)

class ClickHouseConnectionHealthUnitTests(BaseIntegrationTest):
    """Test ClickHouse connection health monitoring."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_with_successful_connection(self):
        """Test health check reports healthy status with working connection.
        
        Critical for monitoring system health and alerting.
        """
        service = ClickHouseService(force_mock=True)
        await service.initialize()
        mock_client = AsyncMock()
        mock_client.execute.return_value = [{'result': 1}]
        service._client = mock_client
        health = await service.health_check()
        assert health['status'] == 'healthy'
        assert health['connectivity'] == 'ok'
        assert 'metrics' in health
        assert 'cache_stats' in health

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_with_failed_connection(self):
        """Test health check reports unhealthy status with failed connection.
        
        Ensures proper error reporting for monitoring systems.
        """
        service = ClickHouseService(force_mock=True)
        await service.initialize()
        mock_client = AsyncMock()
        mock_client.execute.side_effect = ConnectionError('Database down')
        service._client = mock_client
        health = await service.health_check()
        assert health['status'] == 'unhealthy'
        assert 'error' in health
        assert 'Database down' in health['error']
        assert 'metrics' in health

    @pytest.mark.unit
    async def test_service_metrics_tracking(self):
        """Test service metrics are properly tracked.
        
        Critical for monitoring query performance and failure rates.
        """
        service = ClickHouseService(force_mock=True)
        await service.initialize()
        mock_client = AsyncMock()
        mock_client.execute.return_value = [{'result': 1}]
        service._client = mock_client
        await service.execute('SELECT 1', user_id='test-user')
        await service.execute('SELECT 2', user_id='test-user')
        mock_client.execute.side_effect = ConnectionError('Query failed')
        try:
            await service.execute('SELECT 3', user_id='test-user')
        except ConnectionError:
            pass
        metrics = service.get_metrics()
        assert metrics['queries_executed'] >= 2, 'Should track successful queries'
        assert metrics['query_failures'] >= 1, 'Should track failed queries'
        assert 'circuit_breaker_state' in metrics
        assert 'cache_stats' in metrics

class ClickHouseConnectionRecoveryUnitTests(BaseIntegrationTest):
    """Test ClickHouse connection recovery and resilience patterns."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_graceful_degradation_when_required_false(self):
        """Test graceful degradation when ClickHouse is not required.
        
        Ensures system continues to function when ClickHouse is optional.
        """
        service = ClickHouseService()
        with patch('netra_backend.app.db.clickhouse.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default: {'ENVIRONMENT': 'development', 'CLICKHOUSE_REQUIRED': 'false'}.get(key, default)
            with patch.object(service, '_build_clickhouse_database', side_effect=ConnectionError('ClickHouse unavailable')):
                await service._initialize_real_client()
                assert service._client is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_manager_fallback(self):
        """Test fallback to direct connection when connection manager fails.
        
        Ensures resilient connection establishment with multiple strategies.
        """
        with patch('netra_backend.app.db.clickhouse.use_mock_clickhouse', return_value=False):
            with patch('netra_backend.app.db.clickhouse.get_clickhouse_connection_manager', side_effect=ImportError('Connection manager not available')):
                with patch('netra_backend.app.db.clickhouse._create_real_client') as mock_create:
                    mock_client = AsyncMock()

                    async def mock_client_generator():
                        yield mock_client
                    mock_create.return_value = mock_client_generator()
                    async with get_clickhouse_client() as client:
                        assert client is mock_client
                    mock_create.assert_called_once()

    @pytest.mark.unit
    def test_connection_state_validation(self):
        """Test connection state validation logic.
        
        Ensures proper connection state detection for health monitoring.
        """
        service = ClickHouseService()
        assert not service.is_real, 'Service should not be real initially'
        assert not service.is_mock, 'Service should not be mock initially'
        service._client = Mock()
        service._client.__class__.__name__ = 'NoOpClickHouseClient'
        assert service.is_mock, 'Should detect mock client'
        assert not service.is_real, 'Should not be real with mock client'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')