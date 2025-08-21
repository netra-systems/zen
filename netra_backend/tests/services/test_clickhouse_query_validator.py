"""
Tests for ClickHouse query validation functionality.
All functions ≤8 lines per requirements.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import patch

# Add project root to path

from netra_backend.app.db.clickhouse_query_fixer import validate_clickhouse_query

# Add project root to path


class TestClickHouseQueryValidator:
    """Test ClickHouse query validation functionality"""
    
    def test_valid_query_validation(self):
        """Test validation of syntactically correct queries"""
        valid_queries = _get_valid_queries()
        
        for query in valid_queries:
            is_valid, error_message = validate_clickhouse_query(query)
            assert is_valid == True
            assert error_message == ""
    
    def test_invalid_array_syntax_detection(self):
        """Test detection of invalid array syntax"""
        invalid_queries = _get_invalid_queries()
        
        for query in invalid_queries:
            _assert_invalid_query(query)
    
    def test_nested_field_access_warning(self):
        """Test warning for nested field access without array functions"""
        warning_queries = _get_warning_queries()
        
        with patch('app.db.clickhouse_query_fixer.logger') as mock_logger:
            for query in warning_queries:
                _assert_warning_query(query, mock_logger)
    
    def test_complex_query_validation(self):
        """Test validation of complex queries"""
        complex_valid = _get_complex_valid_query()
        is_valid, error_message = validate_clickhouse_query(complex_valid)
        
        assert is_valid == True
        assert error_message == ""
    
    def test_complex_invalid_query_validation(self):
        """Test validation of complex invalid queries"""
        complex_valid = _get_complex_valid_query()
        complex_invalid = _make_complex_invalid(complex_valid)
        
        is_valid, error_message = validate_clickhouse_query(complex_invalid)
        assert is_valid == False
        assert "incorrect array syntax" in error_message.lower()


def _get_valid_queries() -> list:
    """Get list of valid queries"""
    return [
        "SELECT arrayElement(metrics.value, 1) FROM table",
        "SELECT * FROM table WHERE id = 123",
        "SELECT count(*) FROM table GROUP BY category",
        _get_complex_array_query()
    ]


def _get_complex_array_query() -> str:
    """Get complex array query"""
    return """
        SELECT 
            arrayElement(data.values, idx) as value,
            arrayFirstIndex(x -> x > 0, data.values) as first_positive
        FROM analytics_data
    """


def _get_invalid_queries() -> list:
    """Get list of invalid queries"""
    return [
        "SELECT metrics.value[1] FROM table",
        "SELECT data.items[idx] FROM table", 
        "SELECT logs.message[0], logs.level[0] FROM table"
    ]


def _assert_invalid_query(query: str) -> None:
    """Assert query is invalid"""
    is_valid, error_message = validate_clickhouse_query(query)
    assert is_valid == False
    assert "incorrect array syntax" in error_message.lower()
    assert "arrayElement()" in error_message


def _get_warning_queries() -> list:
    """Get queries that should generate warnings"""
    return [
        "SELECT metrics.value FROM table",  # Accessing nested field without array function
        "SELECT metrics.name, metrics.unit FROM logs",
        _get_nested_field_query()
    ]


def _get_nested_field_query() -> str:
    """Get nested field access query"""
    return """
        SELECT timestamp, metrics.value
        FROM performance_data
        WHERE status = 'active'
    """


def _assert_warning_query(query: str, mock_logger) -> None:
    """Assert query generates warning"""
    is_valid, error_message = validate_clickhouse_query(query)
    # Should be technically valid but generate warning
    assert is_valid == True
    mock_logger.warning.assert_called()


def _get_complex_valid_query() -> str:
    """Get complex valid query"""
    return """
        WITH aggregated AS (
            SELECT 
                user_id,
                arrayElement(metrics.latency, 1) as first_latency,
                arraySum(metrics.cpu_usage) as total_cpu
            FROM user_metrics
            WHERE timestamp > '2023-01-01'
        )
        SELECT user_id, first_latency, total_cpu
        FROM aggregated
        WHERE first_latency < 1000
        ORDER BY total_cpu DESC
    """


def _make_complex_invalid(complex_valid: str) -> str:
    """Make complex query invalid by adding incorrect array syntax"""
    return complex_valid.replace(
        'arrayElement(metrics.latency, 1)',
        'metrics.latency[1]'
    )