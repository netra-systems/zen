"""
Test case to reproduce and fix the metrics.value type mismatch issue.
This test verifies that queries with incorrect array syntax are properly fixed
before being sent to ClickHouse.
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment


import pytest

from netra_backend.app.db.clickhouse_query_fixer import (
    ClickHouseQueryInterceptor,
    fix_clickhouse_array_syntax,
)

class TestMetricsValueTypeMismatch:
    """Test suite for metrics.value type mismatch issue from issue7.txt"""
    
    def test_fix_metrics_value_array_syntax(self):
        """Test that metrics.value[idx] is fixed to arrayElement(metrics.value, idx)"""
        # This is the exact problematic query from issue7.txt
        bad_query = """
        SELECT *, 
        arrayFirstIndex(x -> (x = 'latency_ms'), metrics.name) AS idx, 
        arrayFirstIndex(x -> (x = 'throughput'), metrics.name) AS idx2, 
        arrayFirstIndex(x -> (x = 'cost_cents'), metrics.name) AS idx3, 
        if(idx > 0, metrics.value[idx], 0.) AS metric_value, 
        if(idx2 > 0, metrics.value[idx2], 0.) AS throughput_value, 
        if(idx3 > 0, metrics.value[idx3], 0.) AS cost_value, 
        idx > 0 AS has_latency, 
        idx2 > 0 AS has_throughput, 
        idx3 > 0 AS has_cost 
        FROM workload_events 
        WHERE (user_id = 1) AND (timestamp >= '2025-08-14T20:58:23.809078+00:00') 
        AND (timestamp <= '2025-08-15T20:58:23.809078+00:00')
        """
        
        # Apply the fix
        fixed_query = fix_clickhouse_array_syntax(bad_query)
        
        # Verify all array accesses are fixed
        assert "metrics.value[idx]" not in fixed_query
        assert "metrics.value[idx2]" not in fixed_query
        assert "metrics.value[idx3]" not in fixed_query
        
        # Verify correct syntax is present
        assert "arrayElement(metrics.value, idx)" in fixed_query
        assert "arrayElement(metrics.value, idx2)" in fixed_query
        assert "arrayElement(metrics.value, idx3)" in fixed_query
    
    def test_second_problematic_query_from_issue(self):
        """Test the second query pattern from issue7.txt"""
        bad_query = """
        SELECT *, 
        arrayFirstIndex(x -> (x = 'cost_cents'), metrics.name) AS idx, 
        if(idx > 0, metrics.value[idx], 0.) AS cost_value, 
        idx > 0 AS has_cost 
        FROM workload_events 
        WHERE (user_id = 1) AND (timestamp >= (now() - toIntervalDay(7)))
        """
        
        fixed_query = fix_clickhouse_array_syntax(bad_query)
        
        assert "metrics.value[idx]" not in fixed_query
        assert "arrayElement(metrics.value, idx)" in fixed_query
    @pytest.mark.asyncio
    async def test_query_interceptor_fixes_queries(self):
        """Test that the ClickHouseQueryInterceptor properly fixes queries"""
        # Mock client
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncNone  # TODO: Use real service instance
        # Mock: Async component isolation for testing without real async operations
        mock_client.execute_query = AsyncMock(return_value=[])
        
        # Create interceptor
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        # Bad query that needs fixing
        bad_query = "SELECT metrics.value[idx] FROM workload_events"
        
        # Execute through interceptor
        await interceptor.execute_query(bad_query)
        
        # Verify the fixed query was sent to the actual client
        mock_client.execute_query.assert_called_once()
        actual_query = mock_client.execute_query.call_args[0][0]
        
        assert "metrics.value[idx]" not in actual_query
        assert "arrayElement(metrics.value, idx)" in actual_query
    
    def test_complex_nested_array_access(self):
        """Test fixing complex nested array access patterns"""
        bad_query = """
        SELECT 
            metrics.name[1] as first_name,
            metrics.value[arrayFirstIndex(x -> x = 'latency', metrics.name)] as latency,
            if(idx > 0, metrics.unit[idx], 'unknown') as unit
        FROM workload_events
        """
        
        fixed_query = fix_clickhouse_array_syntax(bad_query)
        
        # All array accesses should be fixed
        assert "metrics.name[1]" not in fixed_query
        assert "metrics.value[arrayFirstIndex" not in fixed_query
        assert "metrics.unit[idx]" not in fixed_query
        
        # Should have proper arrayElement calls
        assert "arrayElement(metrics.name, 1)" in fixed_query
        assert "arrayElement(metrics.unit, idx)" in fixed_query
    
    def test_query_with_arithmetic_in_index(self):
        """Test fixing queries with arithmetic operations in array index"""
        bad_query = "SELECT metrics.value[idx - 1], metrics.value[idx + 1] FROM workload_events"
        
        fixed_query = fix_clickhouse_array_syntax(bad_query)
        
        assert "metrics.value[idx - 1]" not in fixed_query
        assert "metrics.value[idx + 1]" not in fixed_query
        assert "arrayElement(metrics.value, idx - 1)" in fixed_query
        assert "arrayElement(metrics.value, idx + 1)" in fixed_query
    @pytest.mark.asyncio
    async def test_interceptor_statistics(self):
        """Test that interceptor tracks statistics correctly"""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncNone  # TODO: Use real service instance
        # Mock: Async component isolation for testing without real async operations
        mock_client.execute_query = AsyncMock(return_value=[])
        
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        # Execute queries - some need fixing, some don't
        await interceptor.execute_query("SELECT * FROM workload_events")  # No fix needed
        await interceptor.execute_query("SELECT metrics.value[1] FROM workload_events")  # Needs fix
        await interceptor.execute_query("SELECT metrics.name[idx] FROM workload_events")  # Needs fix
        
        stats = interceptor.get_stats()
        assert stats["queries_executed"] == 3
        # With LLM detection, we may count fixes twice (once for LLM, once for syntax)
        assert stats["queries_fixed"] >= 2  # At least 2 queries needed fixing
        assert stats["fix_rate"] > 0  # Some queries were fixed