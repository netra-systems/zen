"""
Integration tests for ClickHouse Query Fixer.
All functions ≤8 lines per requirements.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import patch

# Add project root to path

from netra_backend.app.db.clickhouse_query_fixer import (

# Add project root to path
    fix_clickhouse_array_syntax,
    ClickHouseQueryInterceptor
)
from netra_backend.tests.clickhouse_test_mocks import MockClickHouseClient


class TestClickHouseQueryFixerIntegration:
    """Test integration scenarios for query fixer"""
    
    async def test_end_to_end_query_processing(self):
        """Test complete query processing pipeline"""
        mock_client, interceptor = _setup_integration_test()
        expected_result = [{"metric_value": 150, "timestamp": "2023-01-01"}]
        
        _setup_expected_result(mock_client, expected_result)
        
        result = await _execute_problematic_query(interceptor)
        _verify_end_to_end_processing(result, expected_result, interceptor, mock_client)
    
    async def test_batch_query_processing(self):
        """Test processing batch of queries with mixed syntax"""
        mock_client = MockClickHouseClient()
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        batch_queries = _get_batch_queries()
        results = await _process_batch_queries(interceptor, batch_queries)
        _verify_batch_statistics(interceptor, results)
    
    async def test_performance_monitoring_integration(self):
        """Test integration with performance monitoring"""
        mock_client = MockClickHouseClient()
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        performance_queries = _get_performance_queries()
        await _process_performance_queries(interceptor, performance_queries)
        _verify_performance_monitoring(interceptor)
    
    async def test_logging_integration(self):
        """Test integration with logging system"""
        with patch('app.db.clickhouse_query_fixer.logger') as mock_logger:
            mock_client = MockClickHouseClient()
            interceptor = ClickHouseQueryInterceptor(mock_client)
            
            await _execute_logged_queries(interceptor)
            _verify_logging_integration(mock_logger)
    
    async def test_error_recovery_integration(self):
        """Test error recovery in integration scenarios"""
        mock_client = MockClickHouseClient()
        interceptor = ClickHouseQueryInterceptor(mock_client)
        
        _setup_client_error_recovery(mock_client)
        await _test_error_recovery_scenarios(interceptor)
        _verify_error_recovery_behavior(interceptor, mock_client)


def _setup_integration_test() -> tuple:
    """Setup integration test environment"""
    mock_client = MockClickHouseClient()
    interceptor = ClickHouseQueryInterceptor(mock_client)
    return mock_client, interceptor


def _setup_expected_result(mock_client, expected_result: list) -> None:
    """Setup expected query result"""
    fixed_query = "SELECT toFloat64OrZero(arrayElement(metrics.value, 1)) as metric_value, timestamp FROM performance_data"
    mock_client.set_query_result(fixed_query, expected_result)


async def _execute_problematic_query(interceptor) -> list:
    """Execute problematic query through interceptor"""
    original_query = "SELECT metrics.value[1] as metric_value, timestamp FROM performance_data"
    return await interceptor.execute_query(original_query)


def _verify_end_to_end_processing(result, expected_result, interceptor, mock_client) -> None:
    """Verify end-to-end processing results"""
    assert result == expected_result
    assert interceptor.queries_fixed == 1
    
    executed = mock_client.get_executed_queries()
    assert len(executed) == 1
    assert "toFloat64OrZero(arrayElement(metrics.value, 1))" in executed[0]


def _get_batch_queries() -> list:
    """Get batch queries for testing"""
    return [
        "SELECT metrics.cpu[1] FROM system_stats",  # Needs fix
        "SELECT arrayElement(metrics.memory, 1) FROM system_stats",  # Correct
        "SELECT logs.level[i], logs.message[i] FROM app_logs",  # Needs fix (2 issues)
        "SELECT count(*) FROM users",  # No arrays
        "SELECT data.values[position] FROM analytics"  # Needs fix
    ]


async def _process_batch_queries(interceptor, batch_queries: list) -> list:
    """Process batch of queries"""
    results = []
    for query in batch_queries:
        result = await interceptor.execute_query(query)
        results.append(result)
    return results


def _verify_batch_statistics(interceptor, results: list) -> None:
    """Verify batch processing statistics"""
    assert interceptor.queries_executed == 5
    assert interceptor.queries_fixed == 3  # 3 queries needed fixing (1st, 3rd, and 5th)
    assert len(results) == 5


def _get_performance_queries() -> list:
    """Get performance testing queries"""
    return [
        "SELECT metrics.latency[i] FROM performance_logs",
        "SELECT data.cpu[idx], data.memory[idx] FROM system_metrics",
        "SELECT response.time[pos] FROM api_logs"
    ]


async def _process_performance_queries(interceptor, queries: list) -> None:
    """Process performance queries"""
    for query in queries:
        await interceptor.execute_query(query)


def _verify_performance_monitoring(interceptor) -> None:
    """Verify performance monitoring results"""
    stats = interceptor.get_statistics()
    assert stats['queries_executed'] == 3
    assert stats['queries_fixed'] == 3
    assert stats['fix_rate'] == 1.0


async def _execute_logged_queries(interceptor) -> None:
    """Execute queries that should generate logs"""
    queries_with_fixes = [
        "SELECT metrics.value[1] FROM table",
        "SELECT data.items[0] FROM logs"
    ]
    
    for query in queries_with_fixes:
        await interceptor.execute_query(query)


def _verify_logging_integration(mock_logger) -> None:
    """Verify logging integration"""
    mock_logger.info.assert_called()
    mock_logger.debug.assert_called()


def _setup_client_error_recovery(mock_client) -> None:
    """Setup client for error recovery testing"""
    mock_client.should_fail = True
    mock_client.failure_message = "Temporary connection failure"


async def _test_error_recovery_scenarios(interceptor) -> None:
    """Test error recovery scenarios"""
    test_query = "SELECT metrics.value[1] FROM test_table"
    
    with pytest.raises(Exception) as exc_info:
        await interceptor.execute_query(test_query)
    
    assert "Temporary connection failure" in str(exc_info.value)


def _verify_error_recovery_behavior(interceptor, mock_client) -> None:
    """Verify error recovery behavior"""
    # Should still track execution attempt despite error
    assert interceptor.queries_executed == 1
    
    # Query should have been fixed before execution attempt
    executed_queries = mock_client.get_executed_queries()
    assert len(executed_queries) == 1
    assert "arrayElement(metrics.value," in executed_queries[0]