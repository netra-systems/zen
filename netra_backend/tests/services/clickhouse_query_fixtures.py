"""
Query fixtures for ClickHouse Query Fixer tests.
All functions ≤8 lines per requirements.
"""

from typing import Dict


def get_basic_array_query() -> str:
    """Get basic array access query"""
    return """
            SELECT metrics.value[1] as first_metric
            FROM performance_data
            WHERE timestamp > '2023-01-01'
        """


def get_nested_array_query() -> str:
    """Get nested array access query"""
    return """
            SELECT 
                metrics.name[idx] as metric_name,
                metrics.value[idx] as metric_value,
                metrics.unit[idx] as metric_unit
            FROM performance_logs
            WHERE arrayExists(x -> x > 100, metrics.value)
        """


def get_complex_query() -> str:
    """Get complex query with arrays"""
    return """
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
        """


def get_multiple_fields_query() -> str:
    """Get multiple array fields query"""
    return """
            SELECT
                logs.level[i] as log_level,
                logs.message[i] as log_message,
                logs.timestamp[i] as log_time,
                performance.cpu[i] as cpu_usage,
                performance.memory[i] as memory_usage
            FROM application_logs
            WHERE arrayLength(logs.level) = arrayLength(performance.cpu)
        """


def get_subquery() -> str:
    """Get subquery with arrays"""
    return """
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
        """


def get_join_query() -> str:
    """Get join query with array access"""
    return """
            SELECT 
                a.user_id,
                a.metrics.latency[pos] as user_latency,
                b.system.cpu[pos] as system_cpu
            FROM user_metrics a
            JOIN system_metrics b ON a.timestamp = b.timestamp
            WHERE a.metrics.status[pos] = 'active'
        """


def get_window_query() -> str:
    """Get window function query with arrays"""
    return """
            SELECT 
                timestamp,
                metrics.value[offset] as current_value,
                LAG(metrics.value[offset], 1) OVER (ORDER BY timestamp) as previous_value
            FROM performance_data
            WHERE metrics.type[offset] = 'latency'
        """


def get_aggregation_query() -> str:
    """Get aggregation query with arrays"""
    return """
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


def get_all_test_queries() -> Dict[str, str]:
    """Get all test queries"""
    return {
        'basic_array_access': get_basic_array_query(),
        'nested_array_access': get_nested_array_query(),
        'complex_query_with_arrays': get_complex_query(),
        'multiple_array_fields': get_multiple_fields_query(),
        'subquery_with_arrays': get_subquery(),
        'join_with_array_access': get_join_query(),
        'window_function_with_arrays': get_window_query(),
        'aggregation_with_arrays': get_aggregation_query()
    }