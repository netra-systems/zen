import asyncio

"""
ClickHouse Array Operations Tests
Test proper array operations and the query fixer
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.app.db.clickhouse_query_fixer import (
    ClickHouseQueryInterceptor,
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
)
from netra_backend.tests.fixtures.realistic_test_fixtures import (
    create_query_interceptor_with_mock,
    validate_array_query_syntax,
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

    @pytest.mark.asyncio
    async def test_query_interceptor_fixes_queries(self):
        """Test the query interceptor automatically fixes queries"""
        # Create interceptor with mock client
        interceptor, mock_client = create_query_interceptor_with_mock()
        
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

    def test_complex_array_operations_syntax(self):
        """Test complex array operations are properly handled"""
        complex_query = """
        SELECT 
            arrayFirstIndex(x -> x = 'gpu_utilization', metrics.name) as gpu_idx,
            arrayFirstIndex(x -> x = 'memory_usage', metrics.name) as mem_idx,
            IF(gpu_idx > 0, arrayElement(metrics.value, gpu_idx), 0) as gpu_util,
            IF(mem_idx > 0, metrics.value[mem_idx], 0) as memory_mb
        FROM workload_events
        """
        
        # Fix the query
        fixed_query = fix_clickhouse_array_syntax(complex_query)
        
        # Validate proper syntax
        assert validate_array_query_syntax(fixed_query)
        assert "arrayElement(metrics.value, mem_idx)" in fixed_query
        assert "metrics.value[mem_idx]" not in fixed_query

    def test_nested_array_expressions(self):
        """Test handling of nested array expressions"""
        nested_query = """
        SELECT 
            tags.category[arrayFirstIndex(x -> x = 'primary', tags.type)] as primary_category,
            values.data[position] as data_value
        FROM events_table
        WHERE tags.priority[1] = 'high'
        """
        
        fixed_query = fix_clickhouse_array_syntax(nested_query)
        
        # Verify nested expressions are properly fixed
        assert "arrayElement(tags.category, arrayFirstIndex(" in fixed_query
        assert "arrayElement(values.data, position)" in fixed_query
        assert "arrayElement(tags.priority, 1)" in fixed_query
        
        # Verify validation passes
        is_valid, error = validate_clickhouse_query(fixed_query)
        assert is_valid, f"Nested array query validation failed: {error}"

    def test_array_operations_with_conditions(self):
        """Test array operations within conditional expressions"""
        conditional_query = """
        SELECT 
            CASE 
                WHEN metrics.type[1] = 'latency' THEN metrics.value[1]
                WHEN metrics.type[2] = 'throughput' THEN metrics.value[2]
                ELSE 0
            END as primary_metric
        FROM workload_events
        """
        
        fixed_query = fix_clickhouse_array_syntax(conditional_query)
        
        # Verify all array accesses in conditions are fixed
        assert "arrayElement(metrics.type, 1)" in fixed_query
        assert "arrayElement(metrics.value, 1)" in fixed_query
        assert "arrayElement(metrics.type, 2)" in fixed_query
        assert "arrayElement(metrics.value, 2)" in fixed_query