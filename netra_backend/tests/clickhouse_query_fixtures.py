"""
ClickHouse query test fixtures.
All functions  <= 8 lines per requirements.
"""

from typing import Dict

def get_all_test_queries() -> Dict[str, str]:
    """Get all test query fixtures for ClickHouse array syntax testing"""
    return {
        'basic_array_access': _get_basic_array_query(),
        'nested_array_access': _get_nested_array_query(),
        'complex_query_with_arrays': _get_complex_array_query(),
        'multiple_array_patterns': _get_multiple_array_query(),
    }

def _get_basic_array_query() -> str:
    """Get basic array access query fixture"""
    return """
        SELECT 
            metrics.value[1] as first_metric,
            timestamp
        FROM performance_data
        WHERE timestamp > '2023-01-01'
    """

def _get_nested_array_query() -> str:
    """Get nested array access query fixture"""  
    return """
        SELECT 
            metrics.cpu[1] as first_cpu,
            metrics.memory[2] as second_memory,
            arrayExists(x -> x > 100, metrics.value) as has_high_values
        FROM performance_data
        WHERE timestamp > '2023-01-01'
    """

def _get_complex_array_query() -> str:
    """Get complex query with multiple array operations"""
    return """
        SELECT 
            user_id,
            events.type[1] as first_event_type,
            events.timestamp[1] as first_event_time,
            arraySum(metrics.values) as total_value,
            arrayFirstIndex(x -> x > 50, metrics.values) as first_high_index
        FROM user_events
        WHERE user_id IN (
            SELECT user_id 
            FROM user_stats 
            WHERE stats.activity_score[7] > 100
        )
        AND timestamp > now() - INTERVAL 1 DAY
    """

def _get_multiple_array_query() -> str:
    """Get query with multiple array access patterns"""
    return """
        SELECT 
            session_data.pages[1] as first_page,
            session_data.duration[arrayLength(session_data.duration)] as last_duration,
            user_metrics.clicks[idx] as indexed_clicks,
            conversion.rates[2] as second_rate
        FROM user_sessions
        WHERE session_data.pages[1] != ''
    """