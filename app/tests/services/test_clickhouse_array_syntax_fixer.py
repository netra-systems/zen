"""
Tests for ClickHouse array syntax fixing functionality.
All functions ≤8 lines per requirements.
"""

import pytest
from app.db.clickhouse_query_fixer import fix_clickhouse_array_syntax
from .clickhouse_test_helpers import (
    assert_array_syntax_fixed,
    assert_query_structure_preserved,
    assert_multiple_replacements,
    assert_complex_query_fixes,
    get_nested_array_patterns
)
from .clickhouse_query_fixtures import get_all_test_queries


@pytest.fixture
def test_queries():
    """Get all test query fixtures"""
    return get_all_test_queries()


class TestClickHouseArraySyntaxFixer:
    """Test ClickHouse array syntax fixing functionality"""
    
    def test_basic_array_access_fix(self, test_queries):
        """Test fixing basic array access syntax"""
        original_query = test_queries['basic_array_access']
        fixed_query = fix_clickhouse_array_syntax(original_query)
        
        _assert_basic_fix(original_query, fixed_query)
        _assert_basic_structure(fixed_query)
    
    def test_multiple_array_access_fix(self, test_queries):
        """Test fixing multiple array access patterns in single query"""
        original_query = test_queries['nested_array_access']
        fixed_query = fix_clickhouse_array_syntax(original_query)
        
        assert_multiple_replacements(fixed_query, get_nested_array_patterns())
        assert 'arrayExists(x -> x > 100, metrics.value)' in fixed_query
    
    def test_complex_query_array_fix(self, test_queries):
        """Test fixing complex queries with nested array access"""
        original_query = test_queries['complex_query_with_arrays']
        fixed_query = fix_clickhouse_array_syntax(original_query)
        
        assert_complex_query_fixes(fixed_query)
    
    def test_no_changes_for_correct_syntax(self):
        """Test that correctly written queries remain unchanged"""
        correct_query = _get_correct_syntax_query()
        fixed_query = fix_clickhouse_array_syntax(correct_query)
        
        # Should be identical (whitespace normalized)
        assert fixed_query.strip() == correct_query.strip()
    
    def test_mixed_correct_and_incorrect_syntax(self):
        """Test handling queries with both correct and incorrect array syntax"""
        mixed_query = _get_mixed_syntax_query()
        fixed_query = fix_clickhouse_array_syntax(mixed_query)
        
        _assert_mixed_syntax_fixes(fixed_query)
    
    def test_nested_function_array_access(self):
        """Test fixing array access within nested functions"""
        nested_query = _get_nested_function_query()
        fixed_query = fix_clickhouse_array_syntax(nested_query)
        
        _assert_nested_function_fixes(fixed_query)
    
    def test_performance_with_large_queries(self):
        """Test performance with large queries containing many array accesses"""
        large_query = _generate_large_query()
        fixed_query = fix_clickhouse_array_syntax(large_query)
        
        _assert_large_query_fixes(fixed_query)


def _assert_basic_fix(original_query: str, fixed_query: str) -> None:
    """Assert basic array syntax fix"""
    assert_array_syntax_fixed(
        original_query, 
        fixed_query, 
        'metrics.value[1]', 
        'arrayElement(metrics.value, 1)'
    )


def _assert_basic_structure(fixed_query: str) -> None:
    """Assert basic query structure is preserved"""
    required_elements = ['SELECT', 'FROM performance_data', "timestamp > '2023-01-01'"]
    assert_query_structure_preserved(fixed_query, required_elements)


def _get_correct_syntax_query() -> str:
    """Get query with correct syntax"""
    return """
        SELECT 
            arrayElement(metrics.value, 1) as first_metric,
            arrayFirstIndex(x -> x > 100, metrics.value) as high_value_index
        FROM performance_data
        WHERE timestamp > '2023-01-01'
    """


def _get_mixed_syntax_query() -> str:
    """Get query with mixed syntax"""
    return """
        SELECT 
            toFloat64OrZero(arrayElement(metrics.correct, 1)) as correct_access,
            metrics.incorrect[2] as incorrect_access,
            arraySum(metrics.also_correct) as sum_correct
        FROM test_table
    """


def _assert_mixed_syntax_fixes(fixed_query: str) -> None:
    """Assert mixed syntax fixes are correct"""
    # Should keep correct syntax
    assert 'toFloat64OrZero(arrayElement(metrics.correct, 1))' in fixed_query
    assert 'arraySum(metrics.also_correct)' in fixed_query
    
    # Should fix incorrect syntax
    assert 'metrics.incorrect[2]' not in fixed_query
    assert 'toFloat64OrZero(arrayElement(metrics.incorrect, 2))' in fixed_query


def _get_nested_function_query() -> str:
    """Get query with nested function array access"""
    return """
        SELECT 
            CASE 
                WHEN metrics.status[idx] = 'ok' 
                THEN metrics.value[idx] 
                ELSE 0 
            END as conditional_value
        FROM system_data
    """


def _assert_nested_function_fixes(fixed_query: str) -> None:
    """Assert nested function array fixes"""
    assert 'metrics.status[idx]' not in fixed_query
    assert 'metrics.value[idx]' not in fixed_query
    assert 'arrayElement(metrics.status, idx)' in fixed_query
    assert 'arrayElement(metrics.value, idx)' in fixed_query


def _generate_large_query() -> str:
    """Generate large query with many array accesses"""
    select_items = []
    for i in range(1, 101):
        select_items.append(f"metrics.cpu[{i}] as cpu_{i}")
    
    return f"""
        SELECT {', '.join(select_items)}
        FROM large_dataset
        WHERE timestamp > now() - INTERVAL 1 DAY
    """


def _assert_large_query_fixes(fixed_query: str) -> None:
    """Assert large query array fixes"""
    # Should fix all array accesses
    assert 'metrics.cpu[' not in fixed_query
    assert fixed_query.count('arrayElement(') == 100