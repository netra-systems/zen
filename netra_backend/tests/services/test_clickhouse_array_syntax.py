"""
Focused tests for ClickHouse array syntax fixing functionality
Tests array access pattern correction and syntax transformation
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import pytest
from typing import Dict, List, Any

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.db.clickhouse_query_fixer import fix_clickhouse_array_syntax

# Add project root to path


def assert_array_syntax_fixed(original_query: str, fixed_query: str, original_pattern: str, expected_pattern: str) -> None:
    """Assert that array syntax was properly fixed"""
    assert original_pattern not in fixed_query
    assert expected_pattern in fixed_query


def assert_query_structure_preserved(fixed_query: str, required_elements: list) -> None:
    """Assert that query structure is preserved after fixing"""
    for element in required_elements:
        assert element in fixed_query


def assert_multiple_replacements(fixed_query: str, pattern_pairs: list) -> None:
    """Assert multiple pattern replacements occurred"""
    for original_pattern, expected_pattern in pattern_pairs:
        assert original_pattern not in fixed_query
        assert expected_pattern in fixed_query


def get_nested_array_patterns() -> list:
    """Get pattern pairs for nested array access test"""
    return [
        ('metrics.name[idx]', 'arrayElement(metrics.name, idx)'),
        ('metrics.value[idx]', 'arrayElement(metrics.value, idx)'),
        ('metrics.unit[idx]', 'arrayElement(metrics.unit, idx)')
    ]


def assert_complex_query_fixes(fixed_query: str) -> None:
    """Assert complex query array fixes are correct"""
    expected_fixes = [
        'arrayElement(metrics.value, position)',
        'arrayElement(metrics.value, position-1)'
    ]
    preserved_structure = ['WITH filtered_metrics AS', 'ORDER BY timestamp DESC']
    
    for fix in expected_fixes:
        assert fix in fixed_query
    assert_query_structure_preserved(fixed_query, preserved_structure)


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
            """
        }
    
    def _generate_expected_fixes(self) -> Dict[str, str]:
        """Generate expected fixed versions of test queries"""
        return {
            'basic_array_access': """
                SELECT arrayElement(metrics.value, 1) as first_metric
                FROM performance_data
                WHERE timestamp > '2023-01-01'
            """
        }


class TestClickHouseArraySyntaxFixer:
    """Test ClickHouse array syntax fixing functionality"""
    
    @pytest.fixture
    def query_test_suite(self):
        """Provide query test suite for testing"""
        return QueryTestSuite()
    
    def _get_basic_query_and_expectation(self, query_test_suite):
        """Get basic query and expected pattern for testing"""
        query = query_test_suite.test_queries['basic_array_access']
        expected_pattern = 'arrayElement(metrics.value, 1)'
        return query, expected_pattern
    
    def test_basic_array_access_fix(self, query_test_suite):
        """Test basic array access pattern fixing"""
        query, expected_pattern = self._get_basic_query_and_expectation(query_test_suite)
        fixed_query = fix_clickhouse_array_syntax(query)
        assert_array_syntax_fixed(query, fixed_query, 'metrics.value[1]', expected_pattern)

    def _get_nested_query_and_patterns(self, query_test_suite):
        """Get nested query and expected patterns for testing"""
        query = query_test_suite.test_queries['nested_array_access']
        pattern_pairs = get_nested_array_patterns()
        return query, pattern_pairs

    def test_multiple_array_access_fix(self, query_test_suite):
        """Test fixing multiple array access patterns"""
        query, pattern_pairs = self._get_nested_query_and_patterns(query_test_suite)
        fixed_query = fix_clickhouse_array_syntax(query)
        assert_multiple_replacements(fixed_query, pattern_pairs)

    def test_complex_query_array_fix(self, query_test_suite):
        """Test complex query with multiple array accesses"""
        complex_query = query_test_suite.test_queries['complex_query_with_arrays']
        fixed_query = fix_clickhouse_array_syntax(complex_query)
        assert_complex_query_fixes(fixed_query)

    def _get_correct_syntax_query(self):
        """Get query with already correct syntax"""
        return "SELECT arrayElement(metrics.value, 1) FROM table"

    def test_no_changes_for_correct_syntax(self):
        """Test that correct syntax is not modified"""
        correct_query = self._get_correct_syntax_query()
        fixed_query = fix_clickhouse_array_syntax(correct_query)
        assert fixed_query == correct_query

    def _get_mixed_syntax_query(self):
        """Get query with mixed correct and incorrect syntax"""
        return """
            SELECT 
                toFloat64OrZero(arrayElement(metrics.correct, 1)) as correct_field,
                metrics.incorrect[2] as incorrect_field
            FROM test_table
        """

    def _assert_mixed_syntax_fixes(self, fixed_query):
        """Assert mixed syntax query fixes"""
        assert 'toFloat64OrZero(arrayElement(metrics.correct, 1))' in fixed_query
        assert 'toFloat64OrZero(arrayElement(metrics.incorrect, 2))' in fixed_query
        assert 'metrics.incorrect[2]' not in fixed_query

    def test_mixed_correct_and_incorrect_syntax(self):
        """Test handling of mixed correct and incorrect syntax"""
        mixed_query = self._get_mixed_syntax_query()
        fixed_query = fix_clickhouse_array_syntax(mixed_query)
        self._assert_mixed_syntax_fixes(fixed_query)

    def _get_expression_array_query(self):
        """Get query with array access using expressions"""
        return """
            SELECT 
                metrics.value[idx + 1] as next_value,
                metrics.value[position * 2] as doubled_position
            FROM analytics
        """

    def test_array_access_with_expressions(self):
        """Test array access with complex expressions"""
        expression_query = self._get_expression_array_query()
        fixed_query = fix_clickhouse_array_syntax(expression_query)
        assert 'arrayElement(metrics.value, idx + 1)' in fixed_query
        assert 'arrayElement(metrics.value, position * 2)' in fixed_query

    def _get_edge_case_queries(self):
        """Get edge case queries for testing"""
        return [
            "SELECT data.field[0] FROM table",  # Zero index
            "SELECT nested.deep.field[idx] FROM table",  # Deep nesting
            "SELECT array_field[variable_name] FROM table"  # Variable index
        ]

    def _assert_edge_case_fixes(self, queries, fixed_queries):
        """Assert edge case fixes are correct"""
        assert 'toFloat64OrZero(arrayElement(data.field, 0))' in fixed_queries[0]
        assert 'arrayElement(nested.deep.field, idx)' in fixed_queries[1]
        assert 'arrayElement(array_field, variable_name)' in fixed_queries[2]

    def test_edge_case_array_patterns(self):
        """Test edge cases in array access patterns"""
        edge_queries = self._get_edge_case_queries()
        fixed_queries = [fix_clickhouse_array_syntax(q) for q in edge_queries]
        self._assert_edge_case_fixes(edge_queries, fixed_queries)

    def _generate_large_query_parts(self):
        """Generate parts for large query performance test"""
        large_query_parts = ["SELECT "]
        for i in range(100):
            large_query_parts.append(f"metrics.value[{i}] as metric_{i},")
        large_query_parts.append("timestamp FROM large_table")
        return " ".join(large_query_parts)

    def _assert_performance_metrics(self, execution_time, fixed_query):
        """Assert performance metrics are acceptable"""
        assert execution_time < 0.1
        assert 'metrics.value[' not in fixed_query
        assert fixed_query.count('arrayElement(') == 100

    def test_performance_with_large_queries(self):
        """Test performance of fixing large queries"""
        import time
        large_query = self._generate_large_query_parts()
        start_time = time.time()
        fixed_query = fix_clickhouse_array_syntax(large_query)
        end_time = time.time()
        execution_time = end_time - start_time
        self._assert_performance_metrics(execution_time, fixed_query)