"""
Comprehensive tests for ClickHouse Query Fixer - syntax correction and array function replacement
Tests query syntax fixing, validation, interception, and performance optimizations
"""

import pytest
import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, call
import logging

from app.db.clickhouse_query_fixer import (
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
    ClickHouseQueryInterceptor
)


class MockClickHouseClient:
    """Mock ClickHouse client for testing"""
    
    def __init__(self):
        self.executed_queries = []
        self.query_results = {}
        self.execution_times = {}
        self.should_fail = False
        self.failure_message = "Mock ClickHouse error"
        
    async def execute(self, query: str, *args, **kwargs):
        """Mock query execution"""
        self.executed_queries.append(query)
        
        if self.should_fail:
            raise Exception(self.failure_message)
        
        # Return mock result based on query
        if query in self.query_results:
            return self.query_results[query]
        
        return [{"result": "mock_data", "rows": 1}]
    
    def set_query_result(self, query: str, result: Any):
        """Set expected result for specific query"""
        self.query_results[query] = result
    
    def get_executed_queries(self) -> List[str]:
        """Get list of executed queries"""
        return self.executed_queries.copy()
    
    def clear_history(self):
        """Clear execution history"""
        self.executed_queries.clear()


class QueryTestSuite:
    """Test suite for various ClickHouse query scenarios"""
    
    def __init__(self):
        self.test_queries = self._generate_test_queries()
        self.expected_fixes = self._generate_expected_fixes()
        
    def _generate_test_queries(self) -> Dict[str, str]:
        """Generate various test queries with array syntax issues"""
        return {
            'basic_array_access': """
                SELECT metrics.value[1] as first_metric
                FROM performance_data
                WHERE timestamp > '2023-01-01'
            """,
            
            'nested_array_access': """
                SELECT 
                    metrics.name[idx] as metric_name,
                    metrics.value[idx] as metric_value,
                    metrics.unit[idx] as metric_unit
                FROM performance_logs
                WHERE arrayExists(x -> x > 100, metrics.value)
            """,
            
            'complex_query_with_arrays': """
                WITH filtered_metrics AS (
                    SELECT 
                        timestamp,
                        metrics.value[position] as current_value,
                        metrics.value[position-1] as previous_value
                    FROM system_metrics
                    WHERE position > 0
                )
                SELECT 
                    timestamp,
                    current_value,
                    current_value - previous_value as delta
                FROM filtered_metrics
                ORDER BY timestamp DESC
            """,
            
            'multiple_array_fields': """
                SELECT
                    logs.level[i] as log_level,
                    logs.message[i] as log_message,
                    logs.timestamp[i] as log_time,
                    performance.cpu[i] as cpu_usage,
                    performance.memory[i] as memory_usage
                FROM application_logs
                WHERE arrayLength(logs.level) = arrayLength(performance.cpu)
            """,
            
            'subquery_with_arrays': """
                SELECT user_id, avg_performance
                FROM (
                    SELECT 
                        user_id,
                        avg(metrics.response_time[request_idx]) as avg_performance
                    FROM user_requests
                    WHERE metrics.status[request_idx] = 200
                    GROUP BY user_id
                )
                WHERE avg_performance < 1000
            """,
            
            'join_with_array_access': """
                SELECT 
                    a.user_id,
                    a.metrics.latency[pos] as user_latency,
                    b.system.cpu[pos] as system_cpu
                FROM user_metrics a
                JOIN system_metrics b ON a.timestamp = b.timestamp
                WHERE a.metrics.status[pos] = 'active'
            """,
            
            'window_function_with_arrays': """
                SELECT 
                    timestamp,
                    metrics.value[offset] as current_value,
                    LAG(metrics.value[offset], 1) OVER (ORDER BY timestamp) as previous_value
                FROM performance_data
                WHERE metrics.type[offset] = 'latency'
            """,
            
            'aggregation_with_arrays': """
                SELECT 
                    date(timestamp) as day,
                    sum(costs.amount[item_idx]) as total_cost,
                    avg(performance.score[item_idx]) as avg_score,
                    count(*) as records
                FROM daily_reports
                WHERE costs.category[item_idx] = 'compute'
                GROUP BY date(timestamp)
                ORDER BY day DESC
            """
        }
    
    def _generate_expected_fixes(self) -> Dict[str, str]:
        """Generate expected fixed versions of test queries"""
        return {
            'basic_array_access': """
                SELECT arrayElement(metrics.value, 1) as first_metric
                FROM performance_data
                WHERE timestamp > '2023-01-01'
            """,
            
            'nested_array_access': """
                SELECT 
                    arrayElement(metrics.name, idx) as metric_name,
                    arrayElement(metrics.value, idx) as metric_value,
                    arrayElement(metrics.unit, idx) as metric_unit
                FROM performance_logs
                WHERE arrayExists(x -> x > 100, metrics.value)
            """,
            
            'complex_query_with_arrays': """
                WITH filtered_metrics AS (
                    SELECT 
                        timestamp,
                        arrayElement(metrics.value, position) as current_value,
                        arrayElement(metrics.value, position-1) as previous_value
                    FROM system_metrics
                    WHERE position > 0
                )
                SELECT 
                    timestamp,
                    current_value,
                    current_value - previous_value as delta
                FROM filtered_metrics
                ORDER BY timestamp DESC
            """
        }


class TestClickHouseArraySyntaxFixer:
    """Test ClickHouse array syntax fixing functionality"""
    
    @pytest.fixture
    def query_test_suite(self):
        """Create query test suite"""
        return QueryTestSuite()
    
    def test_basic_array_access_fix(self, query_test_suite):
        """Test fixing basic array access syntax"""
        original_query = query_test_suite.test_queries['basic_array_access']
        
        fixed_query = fix_clickhouse_array_syntax(original_query)
        
        # Should replace metrics.value[1] with arrayElement(metrics.value, 1)
        assert 'metrics.value[1]' not in fixed_query
        assert 'arrayElement(metrics.value, 1)' in fixed_query
        
        # Rest of query should remain unchanged
        assert 'SELECT' in fixed_query
        assert 'FROM performance_data' in fixed_query
        assert "timestamp > '2023-01-01'" in fixed_query
    
    def test_multiple_array_access_fix(self, query_test_suite):
        """Test fixing multiple array access patterns in single query"""
        original_query = query_test_suite.test_queries['nested_array_access']
        
        fixed_query = fix_clickhouse_array_syntax(original_query)
        
        # Should fix all three array accesses
        assert 'metrics.name[idx]' not in fixed_query
        assert 'metrics.value[idx]' not in fixed_query
        assert 'metrics.unit[idx]' not in fixed_query
        
        assert 'arrayElement(metrics.name, idx)' in fixed_query
        assert 'arrayElement(metrics.value, idx)' in fixed_query
        assert 'arrayElement(metrics.unit, idx)' in fixed_query
        
        # Existing array functions should remain unchanged
        assert 'arrayExists(x -> x > 100, metrics.value)' in fixed_query
    
    def test_complex_query_array_fix(self, query_test_suite):
        """Test fixing complex queries with nested array access"""
        original_query = query_test_suite.test_queries['complex_query_with_arrays']
        
        fixed_query = fix_clickhouse_array_syntax(original_query)
        
        # Should fix array access in WITH clause
        assert 'arrayElement(metrics.value, position)' in fixed_query
        assert 'arrayElement(metrics.value, position-1)' in fixed_query
        
        # Should not break WITH clause structure
        assert 'WITH filtered_metrics AS' in fixed_query
        assert 'ORDER BY timestamp DESC' in fixed_query
    
    def test_no_changes_for_correct_syntax(self):
        """Test that correctly written queries remain unchanged"""
        correct_query = """
            SELECT 
                arrayElement(metrics.value, 1) as first_metric,
                arrayFirstIndex(x -> x > 100, metrics.value) as high_value_index
            FROM performance_data
            WHERE timestamp > '2023-01-01'
        """
        
        fixed_query = fix_clickhouse_array_syntax(correct_query)
        
        # Should be identical (whitespace normalized)
        assert fixed_query.strip() == correct_query.strip()
    
    def test_mixed_correct_and_incorrect_syntax(self):
        """Test handling queries with both correct and incorrect array syntax"""
        mixed_query = """
            SELECT 
                metrics.value[1] as incorrect_syntax,
                arrayElement(metrics.value, 2) as correct_syntax,
                performance.cpu[idx] as another_incorrect
            FROM test_data
        """
        
        fixed_query = fix_clickhouse_array_syntax(mixed_query)
        
        # Should fix incorrect syntax
        assert 'arrayElement(metrics.value, 1)' in fixed_query
        assert 'arrayElement(performance.cpu, idx)' in fixed_query
        
        # Should preserve correct syntax
        assert 'arrayElement(metrics.value, 2)' in fixed_query
    
    def test_array_access_with_expressions(self):
        """Test fixing array access with complex expressions as indices"""
        expression_query = """
            SELECT 
                metrics.value[idx + 1] as next_value,
                metrics.value[position * 2] as double_pos_value,
                logs.message[arrayLength(logs.message) - 1] as last_message
            FROM data_table
        """
        
        fixed_query = fix_clickhouse_array_syntax(expression_query)
        
        # Should handle complex index expressions
        assert 'arrayElement(metrics.value, idx + 1)' in fixed_query
        assert 'arrayElement(metrics.value, position * 2)' in fixed_query
        assert 'arrayElement(logs.message, arrayLength(logs.message) - 1)' in fixed_query
    
    def test_edge_case_array_patterns(self):
        """Test edge cases in array access patterns"""
        edge_cases = [
            "SELECT data.items[0] FROM table",  # Zero index
            "SELECT a.b[variable_name] FROM t",   # Variable names
            "SELECT nested.deep.array[i] FROM complex",  # Deeply nested (shouldn't match)
            "SELECT simple[idx] FROM basic",     # No dot notation (shouldn't match)
        ]
        
        expected_results = [
            "arrayElement(data.items, 0)",
            "arrayElement(a.b, variable_name)",
            "arrayElement(deep.array, i)",  # Will match deep.array[i] part
            "simple[idx]"  # Should remain unchanged (no dot notation)
        ]
        
        for i, query in enumerate(edge_cases):
            fixed_query = fix_clickhouse_array_syntax(query)
            if expected_results[i].startswith("arrayElement"):
                assert expected_results[i] in fixed_query
            else:
                # Should remain unchanged for unsupported patterns
                assert query == fixed_query
    
    def test_performance_with_large_queries(self):
        """Test performance of fixing large queries"""
        import time
        
        # Generate large query with many array accesses
        large_query_parts = []
        large_query_parts.append("SELECT ")
        
        # Add 100 array access patterns
        for i in range(100):
            large_query_parts.append(f"metrics.value[{i}] as metric_{i},")
        
        large_query_parts.append("timestamp FROM large_table")
        large_query = " ".join(large_query_parts)
        
        # Measure fixing time
        start_time = time.time()
        fixed_query = fix_clickhouse_array_syntax(large_query)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete quickly (less than 100ms for 100 fixes)
        assert execution_time < 0.1
        
        # Should fix all array accesses
        assert 'metrics.value[' not in fixed_query
        assert fixed_query.count('arrayElement(') == 100


class TestClickHouseQueryValidator:
    """Test ClickHouse query validation functionality"""
    
    def test_valid_query_validation(self):
        """Test validation of syntactically correct queries"""
        valid_queries = [
            "SELECT arrayElement(metrics.value, 1) FROM table",
            "SELECT * FROM table WHERE id = 123",
            "SELECT count(*) FROM table GROUP BY category",
            """
                SELECT 
                    arrayElement(data.values, idx) as value,
                    arrayFirstIndex(x -> x > 0, data.values) as first_positive
                FROM analytics_data
            """
        ]
        
        for query in valid_queries:
            is_valid, error_message = validate_clickhouse_query(query)
            assert is_valid == True
            assert error_message == ""
    
    def test_invalid_array_syntax_detection(self):
        """Test detection of invalid array syntax"""
        invalid_queries = [
            "SELECT metrics.value[1] FROM table",
            "SELECT data.items[idx] FROM table",
            "SELECT logs.message[0], logs.level[0] FROM table"
        ]
        
        for query in invalid_queries:
            is_valid, error_message = validate_clickhouse_query(query)
            assert is_valid == False
            assert "incorrect array syntax" in error_message.lower()
            assert "arrayElement()" in error_message
    
    def test_nested_field_access_warning(self):
        """Test warning for nested field access without array functions"""
        warning_queries = [
            "SELECT metrics.value FROM table",  # Accessing nested field without array function
            "SELECT metrics.name, metrics.unit FROM logs",
            """
                SELECT timestamp, metrics.value
                FROM performance_data
                WHERE status = 'active'
            """
        ]
        
        with patch('app.db.clickhouse_query_fixer.logger') as mock_logger:
            for query in warning_queries:
                is_valid, error_message = validate_clickhouse_query(query)
                # Should be technically valid but generate warning
                assert is_valid == True
                mock_logger.warning.assert_called()
    
    def test_complex_query_validation(self):
        """Test validation of complex queries"""
        complex_valid = """
            WITH aggregated AS (
                SELECT 
                    user_id,
                    arrayElement(metrics.latency, 1) as first_latency,
                    arrayReduce('avg', metrics.latency) as avg_latency
                FROM user_sessions
                WHERE arrayLength(metrics.latency) > 0
            )
            SELECT 
                user_id,
                first_latency,
                avg_latency,
                CASE 
                    WHEN avg_latency > 1000 THEN 'slow'
                    WHEN avg_latency > 500 THEN 'medium'
                    ELSE 'fast'
                END as performance_category
            FROM aggregated
            ORDER BY avg_latency DESC
        """
        
        is_valid, error_message = validate_clickhouse_query(complex_valid)
        assert is_valid == True
        assert error_message == ""
        
        # Same query but with incorrect array syntax
        complex_invalid = complex_valid.replace(
            'arrayElement(metrics.latency, 1)',
            'metrics.latency[1]'
        )
        
        is_valid, error_message = validate_clickhouse_query(complex_invalid)
        assert is_valid == False
        assert "incorrect array syntax" in error_message.lower()


class TestClickHouseQueryInterceptor:
    """Test ClickHouse query interceptor functionality"""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock ClickHouse client"""
        return MockClickHouseClient()
    
    @pytest.fixture
    def interceptor(self, mock_client):
        """Create query interceptor with mock client"""
        return ClickHouseQueryInterceptor(mock_client)
    
    @pytest.mark.asyncio
    async def test_interceptor_fixes_and_executes_query(self, interceptor, mock_client):
        """Test that interceptor fixes query and executes it"""
        original_query = "SELECT metrics.value[1] FROM test_table"
        expected_fixed = "SELECT arrayElement(metrics.value, 1) FROM test_table"
        
        # Execute query through interceptor
        result = await interceptor.execute_query(original_query)
        
        # Should have executed fixed query
        executed_queries = mock_client.get_executed_queries()
        assert len(executed_queries) == 1
        assert expected_fixed in executed_queries[0]
        
        # Should track statistics
        assert interceptor.queries_executed == 1
        assert interceptor.queries_fixed == 1
    
    @pytest.mark.asyncio
    async def test_interceptor_passes_through_correct_queries(self, interceptor, mock_client):
        """Test that correct queries pass through unchanged"""
        correct_query = "SELECT arrayElement(metrics.value, 1) FROM test_table"
        
        # Execute correct query
        await interceptor.execute_query(correct_query)
        
        # Should execute unchanged
        executed_queries = mock_client.get_executed_queries()
        assert len(executed_queries) == 1
        assert executed_queries[0].strip() == correct_query.strip()
        
        # Should track execution but not fixing
        assert interceptor.queries_executed == 1
        assert interceptor.queries_fixed == 0
    
    @pytest.mark.asyncio
    async def test_interceptor_handles_client_errors(self, interceptor, mock_client):
        """Test interceptor handling of client execution errors"""
        # Setup client to fail
        mock_client.should_fail = True
        mock_client.failure_message = "Connection timeout"
        
        query = "SELECT * FROM test_table"
        
        # Should propagate client error
        with pytest.raises(Exception) as exc_info:
            await interceptor.execute_query(query)
        
        assert "Connection timeout" in str(exc_info.value)
        
        # Should still track execution attempt
        assert interceptor.queries_executed == 1
    
    @pytest.mark.asyncio
    async def test_interceptor_statistics_tracking(self, interceptor, mock_client):
        """Test interceptor statistics tracking"""
        queries = [
            "SELECT metrics.value[1] FROM table1",  # Needs fixing
            "SELECT arrayElement(metrics.value, 2) FROM table2",  # Correct
            "SELECT data.items[idx] FROM table3",  # Needs fixing
            "SELECT * FROM table4"  # No arrays
        ]
        
        # Execute all queries
        for query in queries:
            await interceptor.execute_query(query)
        
        # Check statistics
        assert interceptor.queries_executed == 4
        assert interceptor.queries_fixed == 2  # First and third queries needed fixing
        
        # Check all queries were executed
        executed_queries = mock_client.get_executed_queries()
        assert len(executed_queries) == 4
    
    @pytest.mark.asyncio
    async def test_interceptor_can_be_disabled(self, interceptor, mock_client):
        """Test that interceptor fixing can be disabled"""
        # Disable fixing
        interceptor.fix_enabled = False
        
        query_with_issue = "SELECT metrics.value[1] FROM test_table"
        
        # Execute query
        await interceptor.execute_query(query_with_issue)
        
        # Should execute original query without fixing
        executed_queries = mock_client.get_executed_queries()
        assert len(executed_queries) == 1
        assert 'metrics.value[1]' in executed_queries[0]
        
        # Should track execution but not fixing
        assert interceptor.queries_executed == 1
        assert interceptor.queries_fixed == 0
    
    @pytest.mark.asyncio
    async def test_interceptor_with_query_parameters(self, interceptor, mock_client):
        """Test interceptor with parameterized queries"""
        parameterized_query = "SELECT metrics.value[?] FROM table WHERE id = ?"
        params = [1, 12345]
        
        # Execute with parameters
        await interceptor.execute_query(parameterized_query, params)
        
        # Should fix query and pass parameters
        executed_queries = mock_client.get_executed_queries()
        assert len(executed_queries) == 1
        assert 'arrayElement(metrics.value, ?)' in executed_queries[0]
    
    @pytest.mark.asyncio
    async def test_concurrent_interceptor_usage(self, interceptor, mock_client):
        """Test interceptor under concurrent usage"""
        queries = [
            f"SELECT metrics.value[{i}] FROM table_{i}"
            for i in range(20)
        ]
        
        # Execute queries concurrently
        tasks = [
            interceptor.execute_query(query)
            for query in queries
        ]
        
        await asyncio.gather(*tasks)
        
        # All queries should have been executed and fixed
        assert interceptor.queries_executed == 20
        assert interceptor.queries_fixed == 20
        
        executed_queries = mock_client.get_executed_queries()
        assert len(executed_queries) == 20
        
        # All should be fixed
        for executed_query in executed_queries:
            assert 'arrayElement(' in executed_query
            assert 'metrics.value[' not in executed_query
    
    def test_interceptor_statistics_reset(self, interceptor):
        """Test resetting interceptor statistics"""
        # Set some statistics
        interceptor.queries_executed = 10
        interceptor.queries_fixed = 5
        
        # Reset
        interceptor.reset_statistics()
        
        assert interceptor.queries_executed == 0
        assert interceptor.queries_fixed == 0
    
    def test_interceptor_get_statistics(self, interceptor):
        """Test getting interceptor statistics"""
        # Set some statistics
        interceptor.queries_executed = 15
        interceptor.queries_fixed = 8
        
        stats = interceptor.get_statistics()
        
        expected_stats = {
            'queries_executed': 15,
            'queries_fixed': 8,
            'fix_rate': 8/15,  # ~0.533
            'fix_enabled': True
        }
        
        assert stats == expected_stats


class TestClickHouseQueryFixerIntegration:
    """Test integration scenarios for query fixer"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_query_processing(self):
        """Test complete query processing pipeline"""
        # Setup
        mock_client = MockClickHouseClient()
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        # Set expected result
        expected_result = [{"metric_value": 150, "timestamp": "2023-01-01"}]
        fixed_query = "SELECT arrayElement(metrics.value, 1) as metric_value, timestamp FROM performance_data"
        mock_client.set_query_result(fixed_query, expected_result)
        
        # Execute problematic query
        original_query = "SELECT metrics.value[1] as metric_value, timestamp FROM performance_data"
        result = await interceptor.execute_query(original_query)
        
        # Verify end-to-end processing
        assert result == expected_result
        assert interceptor.queries_fixed == 1
        
        # Verify correct query was executed
        executed = mock_client.get_executed_queries()
        assert len(executed) == 1
        assert "arrayElement(metrics.value, 1)" in executed[0]
    
    @pytest.mark.asyncio
    async def test_batch_query_processing(self):
        """Test processing batch of queries with mixed syntax"""
        mock_client = MockClickHouseClient()
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        batch_queries = [
            "SELECT metrics.cpu[1] FROM system_stats",  # Needs fix
            "SELECT arrayElement(metrics.memory, 1) FROM system_stats",  # Correct
            "SELECT logs.level[i], logs.message[i] FROM app_logs",  # Needs fix (2 issues)
            "SELECT count(*) FROM users",  # No arrays
            "SELECT data.values[position] FROM analytics"  # Needs fix
        ]
        
        # Process batch
        results = []
        for query in batch_queries:
            result = await interceptor.execute_query(query)
            results.append(result)
        
        # Verify statistics
        assert interceptor.queries_executed == 5
        assert interceptor.queries_fixed == 3  # 3 queries needed fixing (1st, 3rd, and 5th)
        
        # Verify all queries executed
        assert len(results) == 5
        executed_queries = mock_client.get_executed_queries()
        assert len(executed_queries) == 5
    
    def test_regex_pattern_comprehensive_coverage(self):
        """Test regex pattern coverage for various array access scenarios"""
        test_patterns = [
            ("simple.array[index]", "arrayElement(simple.array, index)"),
            ("complex_name.complex_array[complex_index]", "arrayElement(complex_name.complex_array, complex_index)"),
            ("data.items[0]", "arrayElement(data.items, 0)"),
            ("metrics.values[i+1]", "arrayElement(metrics.values, i+1)"),
            ("nested.data[position*2]", "arrayElement(nested.data, position*2)"),
            ("logs.entries[arrayLength(logs.entries)-1]", "arrayElement(logs.entries, arrayLength(logs.entries)-1)"),
        ]
        
        for original_pattern, expected_pattern in test_patterns:
            test_query = f"SELECT {original_pattern} FROM table"
            fixed_query = fix_clickhouse_array_syntax(test_query)
            
            assert expected_pattern in fixed_query
            assert original_pattern not in fixed_query
    
    def test_performance_optimization_caching(self):
        """Test performance optimization through pattern caching"""
        # This would test caching of compiled regex patterns
        # and other performance optimizations
        
        # Create many similar queries
        queries = [
            f"SELECT metrics.value[{i}] FROM table_{i % 10}"
            for i in range(100)
        ]
        
        import time
        start_time = time.time()
        
        # Process all queries
        for query in queries:
            fix_clickhouse_array_syntax(query)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 100 queries quickly
        assert processing_time < 0.5  # Less than 500ms
    
    def test_logging_and_debugging_support(self):
        """Test logging and debugging features"""
        with patch('app.db.clickhouse_query_fixer.logger') as mock_logger:
            query_with_fix = "SELECT metrics.value[1] FROM test_table"
            query_without_fix = "SELECT arrayElement(metrics.value, 1) FROM test_table"
            
            # Query that needs fixing should log
            fix_clickhouse_array_syntax(query_with_fix)
            mock_logger.info.assert_called_with("Fixed ClickHouse query with incorrect array syntax")
            mock_logger.debug.assert_called()
            
            # Reset mock
            mock_logger.reset_mock()
            
            # Query that doesn't need fixing should not log
            fix_clickhouse_array_syntax(query_without_fix)
            mock_logger.info.assert_not_called()