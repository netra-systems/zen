"""
ClickHouse Array Operations Tests
Tests array operations and query fixing functionality
"""

from unittest.mock import AsyncMock

import pytest

from netra_backend.app.db.clickhouse_query_fixer import (
    ClickHouseQueryInterceptor,
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
)

class TestClickHouseArrayOperations:
    """Test proper array operations and the query fixer"""
    
    def test_fix_incorrect_array_syntax(self):
        """Test that incorrect array syntax is fixed"""
        incorrect_query = """
        SELECT 
            metrics.name[idx] as metric_name,
            metrics.value[idx] as metric_value,
            metrics.unit[idx] as metric_unit
        FROM workload_events
        WHERE metrics.name[1] = 'latency_ms'
        """
        
        fixed_query = fix_clickhouse_array_syntax(incorrect_query)
        
        # Verify all array accesses are fixed
        assert "arrayElement(metrics.name, idx)" in fixed_query
        assert "arrayElement(metrics.value, idx)" in fixed_query
        assert "arrayElement(metrics.unit, idx)" in fixed_query
        assert "arrayElement(metrics.name, 1)" in fixed_query
        
        # Verify no incorrect syntax remains
        assert "metrics.name[idx]" not in fixed_query
        assert "metrics.value[idx]" not in fixed_query
    
    def test_validate_query_catches_errors(self):
        """Test query validation catches common errors"""
        # Test incorrect array syntax
        bad_query = "SELECT metrics.value[idx] FROM table"
        is_valid, error = validate_clickhouse_query(bad_query)
        assert not is_valid
        assert "incorrect array syntax" in error
        
        # Test correct syntax passes
        good_query = "SELECT arrayElement(metrics.value, idx) FROM table"
        is_valid, error = validate_clickhouse_query(good_query)
        assert is_valid
        assert error == ""

    async def test_query_interceptor_fixes_queries(self):
        """Test the query interceptor automatically fixes queries"""
        # Create mock client
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_client.execute_query = AsyncMock(return_value=[{"result": "success"}])
        
        # Wrap with interceptor
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        # Execute query with bad syntax
        bad_query = "SELECT metrics.value[idx] FROM workload_events"
        result = await interceptor.execute_query(bad_query)
        
        # Verify the fixed query was sent to the client
        mock_client.execute_query.assert_called_once()
        actual_query = mock_client.execute_query.call_args[0][0]
        assert "arrayElement(metrics.value, idx)" in actual_query
        assert "metrics.value[idx]" not in actual_query
        
        # Check stats
        stats = interceptor.get_stats()
        assert stats["queries_executed"] == 1
        assert stats["queries_fixed"] == 1