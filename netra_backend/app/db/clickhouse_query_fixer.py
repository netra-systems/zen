"""
ClickHouse Query Fixer
Intercepts and fixes ClickHouse queries with incorrect array syntax
"""

import re
from typing import Tuple, Any, Dict
from app.logging_config import central_logger as logger



def _create_array_replacement(field_path: str, index_expr: str) -> str:
    """Create appropriate replacement for array access."""
    if field_path.startswith(('metrics.', 'data.')):
        return f"toFloat64OrZero(arrayElement({field_path}, {index_expr}))"
    return f"arrayElement({field_path}, {index_expr})"

def _replace_array_access(match):
    """Replace array[index] with arrayElement(array, index)."""
    field_path = match.group(1)
    index_expr = match.group(2)
    replacement = _create_array_replacement(field_path, index_expr)
    logger.debug(f"Fixed array access: {match.group(0)} -> {replacement}")
    return replacement

def _get_array_pattern() -> str:
    """Get regex pattern for array access syntax."""
    return r'([\w\.]+)\[([^\]]+)\]'

def _log_query_fix(query: str, fixed_query: str):
    """Log query fix information."""
    logger.info("Fixed ClickHouse query with incorrect array syntax")
    logger.debug(f"Original: {query[:200]}...")
    logger.debug(f"Fixed: {fixed_query[:200]}...")

def _fix_special_metrics_pattern(query: str) -> str:
    """Fix special case of toFloat64OrZero(metrics.value[idx])."""
    special_pattern = r'toFloat64OrZero\(\s*metrics\.value\[([^\]]+)\]\s*\)'
    return re.sub(special_pattern, r'arrayElement(metrics.value, \1)', query)

def _fix_regular_array_patterns(query: str) -> str:
    """Fix regular array access patterns."""
    pattern = _get_array_pattern()
    return re.sub(pattern, _replace_array_access, query)

def _log_fix_if_changed(original_query: str, fixed_query: str) -> None:
    """Log query fix if changes were made."""
    if fixed_query != original_query:
        _log_query_fix(original_query, fixed_query)

def fix_clickhouse_array_syntax(query: str) -> str:
    """Fix ClickHouse queries with incorrect array indexing syntax."""
    fixed_query = _fix_special_metrics_pattern(query)
    fixed_query = _fix_regular_array_patterns(fixed_query)
    _log_fix_if_changed(query, fixed_query)
    return fixed_query


def _has_invalid_array_syntax(query: str) -> bool:
    """Check if query has invalid array access syntax."""
    return bool(re.search(r'[\w\.]+\[[^\]]+\]', query))

def _has_metrics_access(query: str) -> bool:
    """Check if query accesses metrics fields."""
    return any(field in query for field in ['metrics.value', 'metrics.name', 'metrics.unit'])

def _has_array_functions(query: str) -> bool:
    """Check if query uses proper array functions."""
    return any(func in query for func in ['arrayElement', 'arrayFirstIndex', 'arrayExists'])

def _validate_metrics_access(query: str):
    """Validate metrics field access uses proper array functions."""
    if _has_metrics_access(query) and not _has_array_functions(query):
        logger.warning("Query accesses nested fields without proper array functions")

def _is_empty_or_whitespace(query: str) -> bool:
    """Check if query is empty or contains only whitespace."""
    return not query or not query.strip()

def _has_nested_field_access(query: str) -> bool:
    """Check if query has deeply nested field access patterns."""
    return bool(re.search(r'\w+\.\w+\.\w+\.\w+', query))

def _has_sql_injection_patterns(query: str) -> bool:
    """Check for common SQL injection patterns."""
    injection_patterns = [r';\s*DROP\s+TABLE', r';\s*DELETE\s+FROM', r';\s*INSERT\s+INTO']
    return any(re.search(pattern, query, re.IGNORECASE) for pattern in injection_patterns)

def _normalize_query_whitespace(query: str) -> str:
    """Normalize whitespace in query for consistent pattern matching."""
    return ' '.join(query.split())

def _get_malformed_sql_patterns() -> list[str]:
    """Get list of patterns that indicate malformed SQL syntax."""
    return [
        r'^\s*SELECT\s+FROM\s+',  # Missing field(s) - starts with SELECT FROM
        r'^\s*SELECT\s+\*\s+\w+\s*$',  # Missing FROM keyword - SELECT * table
        r'\bFROM\s*$',  # Missing table name after FROM
        r'\bWHERE\s*$'  # Incomplete WHERE clause
    ]

def _check_patterns_match(query_normalized: str, patterns: list[str]) -> bool:
    """Check if any malformed patterns match the normalized query."""
    return any(re.search(pattern, query_normalized, re.IGNORECASE) for pattern in patterns)

def _has_malformed_syntax(query: str) -> bool:
    """Check for basic SQL syntax errors."""
    query_normalized = _normalize_query_whitespace(query)
    malformed_patterns = _get_malformed_sql_patterns()
    return _check_patterns_match(query_normalized, malformed_patterns)

def _check_empty_query(query: str) -> tuple[bool, str]:
    """Check if query is empty or whitespace only."""
    if _is_empty_or_whitespace(query):
        return False, "Query cannot be empty"
    return True, ""

def _check_malformed_syntax(query: str) -> tuple[bool, str]:
    """Check for malformed SQL syntax."""
    if _has_malformed_syntax(query):
        return False, "Query contains malformed SQL syntax"
    return True, ""

def _check_nested_array_syntax(query: str) -> tuple[bool, str]:
    """Check for nested field access with invalid array syntax."""
    if _has_nested_field_access(query) and _has_invalid_array_syntax(query):
        return False, "Query contains deeply nested field access with incorrect array syntax"
    return True, ""

def _check_injection_patterns(query: str) -> tuple[bool, str]:
    """Check for SQL injection patterns."""
    if _has_sql_injection_patterns(query):
        return False, "Query contains potential SQL injection patterns"
    return True, ""

def _validate_query_content(query: str) -> tuple[bool, str]:
    """Validate query content for various issues."""
    for check_func in [_check_empty_query, _check_malformed_syntax, _check_nested_array_syntax, _check_injection_patterns]:
        is_valid, error_msg = check_func(query)
        if not is_valid:
            return False, error_msg
    return True, ""

def _check_content_validity(query: str) -> tuple[bool, str]:
    """Check content validity and return result."""
    content_valid, content_error = _validate_query_content(query)
    if not content_valid:
        return False, content_error
    return True, ""

def _check_array_syntax_validity(query: str) -> tuple[bool, str]:
    """Check array syntax validity."""
    if _has_invalid_array_syntax(query):
        return False, "Query uses incorrect array syntax. Use arrayElement() instead of []"
    return True, ""

def _finalize_validation(query: str) -> tuple[bool, str]:
    """Finalize validation with metrics access check."""
    _validate_metrics_access(query)
    return True, ""

def validate_clickhouse_query(query: str) -> tuple[bool, str]:
    """Validate a ClickHouse query for common syntax errors."""
    is_valid, error_msg = _check_content_validity(query)
    if not is_valid:
        return False, error_msg
    is_valid, error_msg = _check_array_syntax_validity(query)
    return (False, error_msg) if not is_valid else _finalize_validation(query)


class ClickHouseQueryInterceptor:
    """
    Intercepts and fixes ClickHouse queries before execution.
    Can be used as a wrapper around the ClickHouse client.
    """
    
    def _initialize_state(self, client: Any):
        """Initialize interceptor state."""
        self.client = client
        self.fix_enabled = True
        self.queries_fixed = 0
        self.queries_executed = 0

    def __init__(self, client: Any) -> None:
        """Initialize the interceptor with a ClickHouse client."""
        self._initialize_state(client)
    
    async def execute_query(self, query: str, *args, **kwargs) -> Any:
        """Execute a query after fixing any syntax issues."""
        self.queries_executed += 1
        processed_query = await self._process_query_pipeline(query)
        self._validate_processed_query(processed_query)
        return await self._execute_processed_query(processed_query, *args, **kwargs)
    
    async def _process_query_pipeline(self, query: str) -> str:
        """Process query through the fixing pipeline."""
        if not self.fix_enabled:
            return query
        return await self._apply_query_fixes(query)
    
    async def _apply_query_fixes(self, query: str) -> str:
        """Apply LLM and standard query fixes."""
        original_query = query
        query, llm_was_fixed = await self._apply_llm_fixes(query)
        query = self._apply_standard_fixes(query, llm_was_fixed)
        self._log_query_changes(original_query, query, llm_was_fixed)
        return query
    
    async def _apply_llm_fixes(self, query: str) -> Tuple[str, bool]:
        """Apply LLM-specific query fixes."""
        try:
            from app.agents.data_sub_agent.llm_query_detector import LLMQueryDetector
            fixed_query, metadata = LLMQueryDetector.validate_and_fix(query)
            return self._process_llm_fix_result(fixed_query, metadata)
        except ImportError:
            logger.debug("LLMQueryDetector not available, skipping LLM detection")
            return query, False
    
    def _process_llm_fix_result(self, query: str, metadata: Dict) -> Tuple[str, bool]:
        """Process LLM fix results and update statistics."""
        if metadata['is_llm_generated'] and metadata['was_fixed']:
            self.queries_fixed += 1
            return query, True
        return query, False
    
    def _apply_standard_fixes(self, query: str, llm_was_fixed: bool) -> str:
        """Apply standard query fixes if LLM didn't fix it."""
        if llm_was_fixed:
            return query
        return self._fix_array_syntax_if_needed(query)
    
    def _fix_array_syntax_if_needed(self, query: str) -> str:
        """Fix array syntax and update stats if changes made."""
        fixed_query = fix_clickhouse_array_syntax(query)
        if fixed_query != query:
            self.queries_fixed += 1
        return fixed_query
    
    def _log_query_changes(self, original: str, processed: str, llm_fixed: bool) -> None:
        """Log query changes if any were made."""
        if processed != original and not llm_fixed:
            logger.info(f"Fixed query #{self.queries_executed} (total fixed: {self.queries_fixed})")
    
    def _validate_processed_query(self, query: str) -> None:
        """Validate the processed query and log any issues."""
        is_valid, error_msg = validate_clickhouse_query(query)
        if not is_valid:
            logger.error(f"Query validation failed: {error_msg}")
    
    async def _execute_processed_query(self, query: str, *args, **kwargs) -> Any:
        """Execute the processed query using appropriate client method."""
        if hasattr(self.client, 'execute_query'):
            return await self.client.execute_query(query, *args, **kwargs)
        return await self.client.execute(query, *args, **kwargs)
    
    def _calculate_fix_rate(self) -> float:
        """Calculate fix rate percentage."""
        return self.queries_fixed / max(1, self.queries_executed)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about query fixing."""
        return {
            "queries_executed": self.queries_executed,
            "queries_fixed": self.queries_fixed,
            "fix_rate": self._calculate_fix_rate(),
            "fix_enabled": self.fix_enabled
        }
    
    def reset_stats(self) -> None:
        """Reset the statistics counters."""
        self.queries_fixed = 0
        self.queries_executed = 0
    
    def reset_statistics(self) -> None:
        """Alias for reset_stats() for compatibility."""
        self.reset_stats()
    
    def enable_fixing(self) -> None:
        """Enable automatic query fixing."""
        self.fix_enabled = True
    
    def disable_fixing(self) -> None:
        """Disable automatic query fixing."""
        self.fix_enabled = False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Alias for get_stats() for compatibility."""
        return self.get_stats()
    
    async def execute(self, query: str, *args, **kwargs) -> Any:
        """Alias for execute_query for compatibility with different client interfaces."""
        return await self.execute_query(query, *args, **kwargs)
    
    def __getattr__(self, name: str) -> Any:
        """Proxy all other methods to the wrapped client."""
        return getattr(self.client, name)