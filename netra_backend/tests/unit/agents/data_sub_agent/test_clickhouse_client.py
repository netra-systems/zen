"""
Comprehensive Unit Tests for ClickHouse Client

Tests all ClickHouse client operations including connection management,
query execution, health checks, and error handling.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Data access reliability and system stability
- Value Impact: Ensures ClickHouse operations work correctly for analytics
- Strategic Impact: Critical for performance monitoring and user insights
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

import pytest

from netra_backend.app.agents.data_sub_agent.clickhouse_client import ClickHouseClient
from test_framework.decorators import mock_justified

# Test markers for unified test runner
pytestmark = [
    pytest.mark.env_test,    # For test environment compatibility
    pytest.mark.unit,        # Unit test marker
    pytest.mark.agents       # Agents category marker
]


class TestClickHouseClientConnection:
    """Test ClickHouse connection management."""
    
    @pytest.fixture
    def clickhouse_client(self):
        """Create ClickHouse client for testing."""
        return ClickHouseClient()
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test connection logic without external dependencies.", "L1")
    @pytest.mark.asyncio
    async def test_connect_success(self, clickhouse_client):
        """Test successful connection to ClickHouse."""
        mock_client = AsyncMock()
        mock_client.test_connection.return_value = None
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            # Create a proper async context manager mock
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            result = await clickhouse_client.connect()
            
            assert result is True
            assert clickhouse_client._health_status["healthy"] is True
            assert clickhouse_client._health_status["last_check"] is not None
            mock_client.test_connection.assert_called_once()
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test connection failure handling.", "L1")
    @pytest.mark.asyncio
    async def test_connect_failure(self, clickhouse_client):
        """Test failed connection to ClickHouse."""
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            result = await clickhouse_client.connect()
            
            assert result is False
            assert clickhouse_client._health_status["healthy"] is False
            assert clickhouse_client._health_status["last_check"] is not None
    
    def test_is_healthy_no_previous_check(self, clickhouse_client):
        """Test health check with no previous connection check."""
        result = clickhouse_client.is_healthy()
        assert result is False
    
    def test_is_healthy_recent_check_healthy(self, clickhouse_client):
        """Test health check with recent healthy check."""
        clickhouse_client._health_status = {
            "healthy": True,
            "last_check": datetime.now(timezone.utc)
        }
        
        result = clickhouse_client.is_healthy()
        assert result is True
    
    def test_is_healthy_stale_check(self, clickhouse_client):
        """Test health check with stale connection check."""
        # Set check time to 6 minutes ago (stale)
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=6)
        clickhouse_client._health_status = {
            "healthy": True,
            "last_check": stale_time
        }
        
        result = clickhouse_client.is_healthy()
        assert result is False
    
    def test_get_health_status_healthy(self, clickhouse_client):
        """Test getting detailed health status when healthy."""
        check_time = datetime.now(timezone.utc)
        clickhouse_client._health_status = {
            "healthy": True,
            "last_check": check_time
        }
        
        status = clickhouse_client.get_health_status()
        
        assert status["healthy"] is True
        assert status["last_check"] == check_time.isoformat()
        assert status["using_shared_client"] is True
    
    def test_get_health_status_no_check(self, clickhouse_client):
        """Test getting detailed health status with no previous check."""
        status = clickhouse_client.get_health_status()
        
        assert status["healthy"] is False
        assert status["last_check"] is None
        assert status["using_shared_client"] is True


class TestClickHouseClientQueryExecution:
    """Test query execution functionality."""
    
    @pytest.fixture
    def clickhouse_client(self):
        """Create ClickHouse client for testing."""
        return ClickHouseClient()
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test query execution without external dependencies.", "L1")
    @pytest.mark.asyncio
    async def test_execute_query_success(self, clickhouse_client):
        """Test successful query execution."""
        mock_client = AsyncMock()
        mock_result = [{"id": 1, "name": "test"}]
        mock_client.execute.return_value = mock_result
        
        # Mock healthy client
        clickhouse_client._health_status = {
            "healthy": True,
            "last_check": datetime.now(timezone.utc)
        }
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            query = "SELECT * FROM test_table"
            parameters = {"limit": 100}
            
            result = await clickhouse_client.execute_query(query, parameters)
            
            assert result == mock_result
            mock_client.execute.assert_called_once_with(query, parameters)
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test reconnection on unhealthy connection.", "L1")
    @pytest.mark.asyncio
    async def test_execute_query_reconnect_on_unhealthy(self, clickhouse_client):
        """Test query execution triggers reconnect when client is unhealthy."""
        mock_client = AsyncMock()
        mock_result = [{"id": 1, "name": "test"}]
        mock_client.execute.return_value = mock_result
        mock_client.test_connection.return_value = None
        
        # Start with unhealthy client
        clickhouse_client._health_status = {"healthy": False, "last_check": None}
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            query = "SELECT * FROM test_table"
            
            result = await clickhouse_client.execute_query(query)
            
            assert result == mock_result
            # Should have called test_connection for reconnect
            mock_client.test_connection.assert_called_once()
            mock_client.execute.assert_called_once()
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test query execution error handling.", "L1")
    @pytest.mark.asyncio
    async def test_execute_query_failure(self, clickhouse_client):
        """Test query execution failure handling."""
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Query failed")
        
        # Mock healthy client
        clickhouse_client._health_status = {
            "healthy": True,
            "last_check": datetime.now(timezone.utc)
        }
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            query = "INVALID QUERY"
            
            with pytest.raises(Exception, match="Query failed"):
                await clickhouse_client.execute_query(query)


class TestClickHouseClientWorkloadMetrics:
    """Test workload metrics retrieval."""
    
    @pytest.fixture
    def clickhouse_client(self):
        """Create ClickHouse client for testing."""
        client = ClickHouseClient()
        # Mock healthy status
        client._health_status = {
            "healthy": True,
            "last_check": datetime.now(timezone.utc)
        }
        return client
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test workload metrics query construction and execution.", "L1")
    @pytest.mark.asyncio
    async def test_get_workload_metrics_without_user_filter(self, clickhouse_client):
        """Test getting workload metrics without user filter."""
        mock_client = AsyncMock()
        mock_result = [
            {
                "timestamp": datetime.now(timezone.utc),
                "user_id": "user1",
                "workload_id": "workload1",
                "latency_ms": 150.5,
                "cost_cents": 2.3,
                "throughput": 100.0
            }
        ]
        mock_client.execute.return_value = mock_result
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            result = await clickhouse_client.get_workload_metrics("1 HOUR")
            
            assert result == mock_result
            # Verify the query was called
            mock_client.execute.assert_called_once()
            query_call = mock_client.execute.call_args[0][0]
            
            # Verify query structure
            assert "SELECT" in query_call
            assert "FROM workload_events" in query_call
            assert "timestamp >= now() - INTERVAL 1 HOUR" in query_call
            assert "user_id =" not in query_call  # No user filter
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test workload metrics query with user filter.", "L1")
    @pytest.mark.asyncio
    async def test_get_workload_metrics_with_user_filter(self, clickhouse_client):
        """Test getting workload metrics with user filter."""
        mock_client = AsyncMock()
        mock_result = [
            {
                "timestamp": datetime.now(timezone.utc),
                "user_id": "specific_user",
                "workload_id": "workload1",
                "latency_ms": 200.0,
                "cost_cents": 3.5,
                "throughput": 80.0
            }
        ]
        mock_client.execute.return_value = mock_result
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            result = await clickhouse_client.get_workload_metrics("2 HOURS", user_id="specific_user")
            
            assert result == mock_result
            mock_client.execute.assert_called_once()
            query_call = mock_client.execute.call_args[0][0]
            
            # Verify user filter is applied
            assert "AND user_id = 'specific_user'" in query_call
            assert "timestamp >= now() - INTERVAL 2 HOURS" in query_call


class TestClickHouseClientCostBreakdown:
    """Test cost breakdown functionality."""
    
    @pytest.fixture
    def clickhouse_client(self):
        """Create ClickHouse client for testing."""
        client = ClickHouseClient()
        # Mock healthy status
        client._health_status = {
            "healthy": True,
            "last_check": datetime.now(timezone.utc)
        }
        return client
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test cost breakdown query construction.", "L1")
    @pytest.mark.asyncio
    async def test_get_cost_breakdown_without_user_filter(self, clickhouse_client):
        """Test getting cost breakdown without user filter."""
        mock_client = AsyncMock()
        mock_result = [
            {
                "user_id": "user1",
                "workload_type": "inference",
                "request_count": 100,
                "avg_cost_cents": 2.5,
                "total_cost_cents": 250.0
            }
        ]
        mock_client.execute.return_value = mock_result
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            result = await clickhouse_client.get_cost_breakdown("1 DAY")
            
            assert result == mock_result
            mock_client.execute.assert_called_once()
            
            # Verify query structure
            query_call = mock_client.execute.call_args[0][0]
            parameters = mock_client.execute.call_args[0][1]
            
            assert "GROUP BY user_id, workload_type" in query_call
            assert "ORDER BY total_cost_cents DESC" in query_call
            assert parameters["timeframe"] == "1 DAY"


class TestClickHouseClientMockData:
    """Test mock data functionality."""
    
    @pytest.fixture
    def clickhouse_client(self):
        """Create ClickHouse client for testing."""
        return ClickHouseClient()
    
    def test_mock_query_result_structure(self, clickhouse_client):
        """Test mock data structure matches expected format."""
        query = "SELECT * FROM test_table"
        
        result = clickhouse_client._mock_query_result(query)
        
        assert isinstance(result, list)
        assert len(result) == 1
        
        sample_record = result[0]
        expected_fields = ["timestamp", "user_id", "workload_id", "latency_ms", "cost_cents", "throughput"]
        
        for field in expected_fields:
            assert field in sample_record
        
        # Verify data types
        assert isinstance(sample_record["timestamp"], datetime)
        assert isinstance(sample_record["user_id"], str)
        assert isinstance(sample_record["workload_id"], str)
        assert isinstance(sample_record["latency_ms"], float)
        assert isinstance(sample_record["cost_cents"], float)
        assert isinstance(sample_record["throughput"], float)


class TestClickHouseClientConnectionManagement:
    """Test connection management and cleanup."""
    
    @pytest.fixture
    def clickhouse_client(self):
        """Create ClickHouse client for testing."""
        return ClickHouseClient()
    
    @mock_justified("L1 Unit Test: Testing connection test functionality without external dependencies.", "L1")
    @pytest.mark.asyncio
    async def test_test_connection(self, clickhouse_client):
        """Test connection testing functionality."""
        mock_client = AsyncMock()
        mock_client.execute.return_value = []
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            # This should not raise an exception
            await clickhouse_client._test_connection()
            
            mock_client.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_close_connection(self, clickhouse_client):
        """Test connection cleanup (no-op for shared client)."""
        # This should not raise any exception
        await clickhouse_client.close()
        
        # No assertions needed since this is a no-op for shared client


class TestClickHouseClientErrorHandling:
    """Test error handling in various scenarios."""
    
    @pytest.fixture
    def clickhouse_client(self):
        """Create ClickHouse client for testing."""
        return ClickHouseClient()
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test error handling scenarios.", "L1")
    @pytest.mark.asyncio
    async def test_query_execution_logs_error_details(self, clickhouse_client):
        """Test that query execution errors are logged with details."""
        mock_client = AsyncMock()
        error_message = "Table 'test_table' doesn't exist"
        mock_client.execute.side_effect = Exception(error_message)
        
        # Mock healthy client
        clickhouse_client._health_status = {
            "healthy": True,
            "last_check": datetime.now(timezone.utc)
        }
        
        with patch("netra_backend.app.agents.data_sub_agent.clickhouse_client.get_clickhouse_client") as mock_get_client:
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_get_client.return_value = mock_context_manager
            
            # Mock logger to capture log calls
            with patch.object(clickhouse_client.logger, 'error') as mock_log_error:
                query = "SELECT * FROM non_existent_table"
                
                with pytest.raises(Exception, match=error_message):
                    await clickhouse_client.execute_query(query)
                
                # Verify error logging
                assert mock_log_error.call_count == 2
                mock_log_error.assert_any_call(f"Query execution failed: {error_message}")
                mock_log_error.assert_any_call(f"Query: {query}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])