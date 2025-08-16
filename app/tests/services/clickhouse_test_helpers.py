"""
Helper functions for ClickHouse Query Fixer tests.
All functions ≤8 lines per requirements.
"""

from typing import List, Tuple


def assert_array_syntax_fixed(original_query: str, fixed_query: str, original_pattern: str, expected_pattern: str) -> None:
    """Assert that array syntax was properly fixed"""
    assert original_pattern not in fixed_query
    assert expected_pattern in fixed_query


def assert_query_structure_preserved(fixed_query: str, required_elements: List[str]) -> None:
    """Assert that query structure is preserved after fixing"""
    for element in required_elements:
        assert element in fixed_query


def assert_multiple_replacements(fixed_query: str, pattern_pairs: List[Tuple[str, str]]) -> None:
    """Assert multiple pattern replacements occurred"""
    for original_pattern, expected_pattern in pattern_pairs:
        assert original_pattern not in fixed_query
        assert expected_pattern in fixed_query


def get_nested_array_patterns() -> List[Tuple[str, str]]:
    """Get pattern pairs for nested array access test"""
    return [
        ('metrics.name[idx]', 'arrayElement(metrics.name, idx)'),
        ('metrics.value[idx]', 'arrayElement(metrics.value, idx)'),
        ('metrics.unit[idx]', 'arrayElement(metrics.unit, idx)')
    ]


def _get_expected_fixes() -> List[str]:
    """Get expected fixes for complex query validation"""
    return [
        'arrayElement(metrics.value, position)',
        'arrayElement(metrics.value, position-1)'
    ]


def _get_preserved_structure() -> List[str]:
    """Get preserved structure elements for validation"""
    return ['WITH filtered_metrics AS', 'ORDER BY timestamp DESC']


def assert_complex_query_fixes(fixed_query: str) -> None:
    """Assert complex query array fixes are correct"""
    expected_fixes = _get_expected_fixes()
    preserved_structure = _get_preserved_structure()
    
    for fix in expected_fixes:
        assert fix in fixed_query
    assert_query_structure_preserved(fixed_query, preserved_structure)