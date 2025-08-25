"""
Comprehensive tests for ClickHouse client functionality.

Tests connection management, error handling, and data operations.
This ensures reliable data access for performance analysis features.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, Mock

from netra_backend.app.agents.data_sub_agent.clickhouse_client import ClickHouseClient


class TestClickHouseClientComprehensive:
    """Comprehensive tests for ClickHouse client."""

    @pytest.fixture
    def client(self):
        """Create ClickHouse client for testing."""
        return ClickHouseClient()

    @pytest.fixture
    def mock_clickhouse_client(self):
        """Mock ClickHouse client for testing."""
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock()
        mock_client.execute = AsyncMock()
        return mock_client

    def test_client_initialization(self, client):
        """Test that client initializes correctly."""
        assert client is not None
        assert hasattr(client, 'logger')
        assert hasattr(client, '_health_status')
        assert client._health_status['healthy'] is False
        assert client._health_status['last_check'] is None

    @pytest.mark.asyncio
    async def test_connect_success(self, client, mock_clickhouse_client):
        """Test successful connection."""
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            # Setup mock context manager
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await client.connect()
            
            assert result is True
            assert client._health_status['healthy'] is True
            assert client._health_status['last_check'] is not None
            mock_clickhouse_client.test_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, client, mock_clickhouse_client):
        """Test connection failure handling."""
        mock_clickhouse_client.test_connection.side_effect = Exception("Connection failed")
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await client.connect()
            
            assert result is False
            assert client._health_status['healthy'] is False
            assert client._health_status['last_check'] is not None

    @pytest.mark.asyncio
    async def test_execute_query_success(self, client, mock_clickhouse_client):
        """Test successful query execution."""
        expected_result = [{"id": 1, "name": "test"}]
        mock_clickhouse_client.execute.return_value = expected_result
        
        # Set client as healthy first
        client._health_status = {"healthy": True, "last_check": datetime.now(timezone.utc)}
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await client.execute_query("SELECT * FROM test", {"param": "value"})
            
            assert result == expected_result
            mock_clickhouse_client.execute.assert_called_once_with("SELECT * FROM test", {"param": "value"})

    @pytest.mark.asyncio
    async def test_execute_query_unhealthy_client_reconnects(self, client, mock_clickhouse_client):
        """Test that unhealthy client reconnects before query execution."""
        expected_result = [{"id": 1, "name": "test"}]
        mock_clickhouse_client.execute.return_value = expected_result
        mock_clickhouse_client.test_connection.return_value = None
        
        # Set client as unhealthy
        client._health_status = {"healthy": False, "last_check": None}
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await client.execute_query("SELECT * FROM test")
            
            assert result == expected_result
            # Should have called test_connection (reconnect) and execute
            mock_clickhouse_client.test_connection.assert_called_once()
            mock_clickhouse_client.execute.assert_called_once_with("SELECT * FROM test", {})

    @pytest.mark.asyncio
    async def test_execute_query_failure(self, client, mock_clickhouse_client):
        """Test query execution failure handling."""
        mock_clickhouse_client.execute.side_effect = Exception("Query failed")
        
        # Set client as healthy first
        client._health_status = {"healthy": True, "last_check": datetime.now(timezone.utc)}
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(Exception, match="Query failed"):
                await client.execute_query("SELECT * FROM test")

    def test_is_healthy_true(self, client):
        """Test health check when client is healthy."""
        client._health_status = {"healthy": True, "last_check": datetime.now(timezone.utc)}
        assert client.is_healthy() is True

    def test_is_healthy_false(self, client):
        """Test health check when client is unhealthy."""
        client._health_status = {"healthy": False, "last_check": None}
        assert client.is_healthy() is False

    def test_is_healthy_stale_check(self, client):
        """Test health check when status is stale."""
        # Set status as healthy but with old timestamp (over 5 minutes ago)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=6)
        client._health_status = {"healthy": True, "last_check": old_time}
        
        # Should return False for stale status
        assert client.is_healthy() is False

    @pytest.mark.asyncio
    async def test_query_with_different_parameter_types(self, client, mock_clickhouse_client):
        """Test query execution with various parameter types."""
        mock_clickhouse_client.execute.return_value = []
        client._health_status = {"healthy": True, "last_check": datetime.now(timezone.utc)}
        
        test_parameters = [
            None,  # No parameters
            {},    # Empty dict
            {"string": "test", "number": 123, "bool": True},  # Mixed types
            {"date": datetime.now(), "list": [1, 2, 3]},      # Complex types
        ]
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            for params in test_parameters:
                await client.execute_query("SELECT 1", params)
                expected_params = params if params is not None else {}
                mock_clickhouse_client.execute.assert_called_with("SELECT 1", expected_params)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, client, mock_clickhouse_client):
        """Test that client handles concurrent operations correctly."""
        mock_clickhouse_client.execute.return_value = [{"result": "success"}]
        client._health_status = {"healthy": True, "last_check": datetime.now(timezone.utc)}
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Run multiple queries concurrently
            tasks = [
                client.execute_query(f"SELECT {i}") 
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 5
            assert all(result == [{"result": "success"}] for result in results)
            assert mock_clickhouse_client.execute.call_count == 5

    @pytest.mark.asyncio
    async def test_health_status_updates(self, client, mock_clickhouse_client):
        """Test that health status is updated correctly during operations."""
        initial_time = datetime.now(timezone.utc)
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test successful connection updates health status
            await client.connect()
            assert client._health_status['healthy'] is True
            assert client._health_status['last_check'] >= initial_time
            
            # Test failed connection updates health status
            mock_clickhouse_client.test_connection.side_effect = Exception("Connection failed")
            await client.connect()
            assert client._health_status['healthy'] is False
            assert client._health_status['last_check'] >= initial_time

    @pytest.mark.asyncio
    async def test_error_logging(self, client, mock_clickhouse_client):
        """Test that errors are logged appropriately."""
        mock_clickhouse_client.test_connection.side_effect = Exception("Test error")
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_clickhouse_client)
            mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(client.logger, 'error') as mock_error:
                await client.connect()
                mock_error.assert_called_once()
                error_call_args = mock_error.call_args[0][0]
                assert "ClickHouse connection failed" in error_call_args
                assert "Test error" in error_call_args

    def test_client_logger_configuration(self, client):
        """Test that logger is configured correctly."""
        assert client.logger is not None
        # Logger should have required methods for logging
        assert hasattr(client.logger, 'info')
        assert hasattr(client.logger, 'error')
        assert hasattr(client.logger, 'debug')
        assert hasattr(client.logger, 'warning')