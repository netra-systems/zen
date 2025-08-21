"""
Focused tests for ClickHouse query validation functionality
Tests query syntax validation, error detection, and validation rules
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import pytest
from typing import List

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.db.clickhouse_query_fixer import validate_clickhouse_query

# Add project root to path


class TestClickHouseQueryValidator:
    """Test ClickHouse query validation functionality"""
    
    def _get_valid_queries(self):
        """Get list of valid queries for testing"""
        return [
            "SELECT arrayElement(metrics.value, 1) FROM table",
            "SELECT * FROM table WHERE id = 123",
            "SELECT count(*) FROM table GROUP BY category"
        ]

    def test_valid_query_validation(self):
        """Test validation of syntactically correct queries"""
        valid_queries = self._get_valid_queries()
        for query in valid_queries:
            is_valid, error_message = validate_clickhouse_query(query)
            assert is_valid == True

    def _get_invalid_queries(self):
        """Get list of invalid queries for testing"""
        return [
            "SELECT metrics.value[1] FROM table",  # Old array syntax
            "SELECT data.field[idx] FROM table",   # Needs fixing
        ]

    def test_invalid_array_syntax_detection(self):
        """Test detection of invalid array syntax"""
        invalid_queries = self._get_invalid_queries()
        for query in invalid_queries:
            is_valid, error_message = validate_clickhouse_query(query)
            assert is_valid == False
            assert 'array syntax' in error_message.lower()

    def _get_nested_field_query(self):
        """Get query with nested field access for testing"""
        return "SELECT very.deeply.nested.field[idx] FROM table"

    def test_nested_field_access_warning(self):
        """Test warning for deeply nested field access"""
        nested_query = self._get_nested_field_query()
        is_valid, error_message = validate_clickhouse_query(nested_query)
        assert is_valid == False
        assert 'nested' in error_message.lower()

    def _get_complex_validation_query(self):
        """Get complex query for validation testing"""
        return """
            WITH subquery AS (
                SELECT arrayElement(data.values, 1) as first_value
                FROM analytics
            )
            SELECT * FROM subquery
        """

    def test_complex_query_validation(self):
        """Test validation of complex queries"""
        complex_query = self._get_complex_validation_query()
        is_valid, error_message = validate_clickhouse_query(complex_query)
        assert is_valid == True

    def _get_empty_query(self):
        """Get empty query for validation testing"""
        return ""

    def test_empty_query_validation(self):
        """Test validation of empty queries"""
        empty_query = self._get_empty_query()
        is_valid, error_message = validate_clickhouse_query(empty_query)
        assert is_valid == False
        assert error_message != ""

    def _get_whitespace_only_query(self):
        """Get whitespace-only query for testing"""
        return "   \n\t   "

    def test_whitespace_only_query_validation(self):
        """Test validation of whitespace-only queries"""
        whitespace_query = self._get_whitespace_only_query()
        is_valid, error_message = validate_clickhouse_query(whitespace_query)
        assert is_valid == False
        assert "empty" in error_message.lower() or "invalid" in error_message.lower()

    def _get_sql_injection_attempt(self):
        """Get potential SQL injection query for testing"""
        return "SELECT * FROM table WHERE id = 1; DROP TABLE users; --"

    def test_sql_injection_detection(self):
        """Test detection of potential SQL injection attempts"""
        injection_query = self._get_sql_injection_attempt()
        is_valid, error_message = validate_clickhouse_query(injection_query)
        # Should detect multiple statements or suspicious patterns
        assert is_valid == False or "injection" in error_message.lower()

    def _get_very_long_query(self):
        """Get very long query for length validation testing"""
        base_query = "SELECT "
        fields = [f"field_{i}" for i in range(1000)]
        return base_query + ", ".join(fields) + " FROM large_table"

    def test_query_length_validation(self):
        """Test validation of extremely long queries"""
        long_query = self._get_very_long_query()
        is_valid, error_message = validate_clickhouse_query(long_query)
        # Should handle long queries gracefully
        assert isinstance(is_valid, bool)
        assert isinstance(error_message, str)

    def _get_malformed_syntax_queries(self):
        """Get queries with malformed syntax for testing"""
        return [
            "SELECT FROM table",  # Missing field
            "SELECT * table",     # Missing FROM
            "SELECT * FROM",      # Missing table name
            "SELECT *\nFROM table WHERE",  # Incomplete WHERE clause
        ]

    def test_malformed_syntax_detection(self):
        """Test detection of malformed SQL syntax"""
        malformed_queries = self._get_malformed_syntax_queries()
        for query in malformed_queries:
            is_valid, error_message = validate_clickhouse_query(query)
            assert is_valid == False
            assert error_message != ""

    def _get_case_sensitive_queries(self):
        """Get queries with different case variations"""
        return [
            "select * from table",
            "SELECT * FROM TABLE",
            "Select * From Table"
        ]

    def test_case_insensitive_validation(self):
        """Test case-insensitive query validation"""
        case_queries = self._get_case_sensitive_queries()
        for query in case_queries:
            is_valid, error_message = validate_clickhouse_query(query)
            # All should be treated equally
            assert is_valid == True

    def _get_unicode_query(self):
        """Get query with unicode characters for testing"""
        return "SELECT 'héllo wörld' as greeting FROM table"

    def test_unicode_character_handling(self):
        """Test handling of unicode characters in queries"""
        unicode_query = self._get_unicode_query()
        is_valid, error_message = validate_clickhouse_query(unicode_query)
        assert is_valid == True

    def _get_performance_heavy_query(self):
        """Get performance-heavy query for validation testing"""
        return """
            SELECT 
                count(*), 
                avg(metrics.value[1]),
                max(metrics.value[2])
            FROM large_table 
            WHERE timestamp > '2023-01-01'
            GROUP BY category
            ORDER BY count(*) DESC
        """

    def test_performance_query_validation(self):
        """Test validation of performance-intensive queries"""
        heavy_query = self._get_performance_heavy_query()
        is_valid, error_message = validate_clickhouse_query(heavy_query)
        # Should identify array syntax issues
        assert is_valid == False
        assert 'array syntax' in error_message.lower()

    def _get_subquery_with_arrays(self):
        """Get subquery containing array syntax issues"""
        return """
            SELECT outer.*
            FROM (
                SELECT metrics.value[1] as inner_field
                FROM inner_table
            ) as outer
        """

    def test_nested_subquery_validation(self):
        """Test validation of nested subqueries with array issues"""
        subquery = self._get_subquery_with_arrays()
        is_valid, error_message = validate_clickhouse_query(subquery)
        assert is_valid == False
        assert 'array syntax' in error_message.lower()