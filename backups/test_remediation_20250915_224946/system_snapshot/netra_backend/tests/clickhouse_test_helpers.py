"""
Helper functions for ClickHouse array syntax testing.
All functions  <= 8 lines per requirements.
"""

from typing import List

def assert_array_syntax_fixed(original_query: str, fixed_query: str, old_pattern: str, new_pattern: str) -> None:
    """Assert that array syntax was properly fixed"""
    assert old_pattern in original_query, f"Original query should contain {old_pattern}"
    assert old_pattern not in fixed_query, f"Fixed query should not contain {old_pattern}"
    assert new_pattern in fixed_query, f"Fixed query should contain {new_pattern}"

def assert_complex_query_fixes(fixed_query: str) -> None:
    """Assert that complex query array syntax was fixed correctly"""
    _assert_no_bracket_syntax(fixed_query)
    _assert_array_function_syntax(fixed_query)

def _assert_no_bracket_syntax(fixed_query: str) -> None:
    """Assert no bracket array access remains"""
    bracket_patterns = ['events.type[1]', 'events.timestamp[1]', 'stats.activity_score[7]']
    for pattern in bracket_patterns:
        assert pattern not in fixed_query, f"Bracket syntax {pattern} should be fixed"

def _assert_array_function_syntax(fixed_query: str) -> None:
    """Assert proper array function syntax is used"""
    expected_patterns = [
        'arrayElement(events.type, 1)',
        'arrayElement(events.timestamp, 1)',
        'arrayElement(stats.activity_score, 7)'
    ]
    for pattern in expected_patterns:
        assert pattern in fixed_query, f"Should contain {pattern}"

def assert_multiple_replacements(fixed_query: str, patterns: List[str]) -> None:
    """Assert multiple array patterns were replaced"""
    for pattern in patterns:
        assert pattern not in fixed_query, f"Pattern {pattern} should be replaced"

def assert_query_structure_preserved(fixed_query: str, required_elements: List[str]) -> None:
    """Assert that query structure is preserved after fixing"""
    for element in required_elements:
        assert element in fixed_query, f"Query should preserve {element}"

def get_nested_array_patterns() -> List[str]:
    """Get list of nested array patterns to test"""
    return [
        'metrics.cpu[1]',
        'metrics.memory[2]',
        'session_data.pages[1]',
        'user_metrics.clicks[idx]'
    ]