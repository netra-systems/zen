"""Query validation and fixing for ClickHouse queries.

This module ensures ALL queries use correct array syntax before execution.
"""

import re
from typing import Optional
from app.logging_config import central_logger as logger


def validate_and_fix_query(query: str) -> str:
    """Validate and fix any ClickHouse query to use correct array syntax."""
    pattern = r'metrics\.(value|name|unit)\[([^\]]+)\]'
    fixed_query = re.sub(pattern, _replace_array_access, query)
    if fixed_query != query:
        _log_query_fix(query, fixed_query)
    return fixed_query

def _replace_array_access(match) -> str:
    """Replace array[index] with arrayElement(array, index)"""
    field, index = match.group(1), match.group(2)
    replacement = f"arrayElement(metrics.{field}, {index})"
    logger.debug(f"Fixed array access: metrics.{field}[{index}] -> {replacement}")
    return replacement

def _log_query_fix(original: str, fixed: str) -> None:
    """Log query fix details."""
    logger.warning(f"Fixed query with incorrect array syntax")
    logger.debug(f"Original: {original[:200]}...")
    logger.debug(f"Fixed: {fixed[:200]}...")


def ensure_query_uses_arrayElement(query: str) -> bool:
    """Check if a query uses the correct arrayElement syntax.
    
    Args:
        query: The query to check
        
    Returns:
        True if the query uses correct syntax or doesn't access arrays
    """
    # Check for incorrect array access
    if re.search(r'metrics\.\w+\[[^\]]+\]', query):
        return False
    return True


def fix_simplified_correlation_query(query: str) -> str:
    """Fix correlation queries that were simplified incorrectly.
    
    The simplification process might generate queries like:
    SELECT arrayFirstIndex... if(idx1 > 0, metrics.value[idx1], 0.)
    
    These need to be fixed to use arrayElement.
    
    Args:
        query: The simplified correlation query
        
    Returns:
        Fixed query with proper syntax
    """
    # First apply general array fix
    query = validate_and_fix_query(query)
    
    # Ensure the query doesn't get lowercased (preserve function names)
    # This is important because ClickHouse functions are case-sensitive
    
    return query