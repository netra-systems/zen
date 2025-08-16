"""
ClickHouse Query Fixer
Intercepts and fixes ClickHouse queries with incorrect array syntax
"""

import re
from typing import Tuple, Any, Dict
from app.logging_config import central_logger as logger



def _create_array_replacement(field_path: str, index_expr: str) -> str:
    """Create appropriate replacement for array access."""
    if field_path == 'metrics.value':
        # metrics.value is already Float64 in ClickHouse Nested structure
        return f"arrayElement({field_path}, {index_expr})"
    elif field_path.startswith(('metrics.', 'data.')):
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

def fix_clickhouse_array_syntax(query: str) -> str:
    """Fix ClickHouse queries with incorrect array indexing syntax."""
    # First fix the special case of toFloat64OrZero(metrics.value[idx])
    special_pattern = r'toFloat64OrZero\(\s*metrics\.value\[([^\]]+)\]\s*\)'
    fixed_query = re.sub(special_pattern, r'arrayElement(metrics.value, \1)', query)
    
    # Then fix regular array access patterns
    pattern = _get_array_pattern()
    fixed_query = re.sub(pattern, _replace_array_access, fixed_query)
    
    if fixed_query != query:
        _log_query_fix(query, fixed_query)
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

def validate_clickhouse_query(query: str) -> tuple[bool, str]:
    """Validate a ClickHouse query for common syntax errors."""
    if _has_invalid_array_syntax(query):
        return False, "Query uses incorrect array syntax. Use arrayElement() instead of []"
    _validate_metrics_access(query)
    return True, ""


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