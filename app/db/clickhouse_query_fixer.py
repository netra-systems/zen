"""
ClickHouse Query Fixer
Intercepts and fixes ClickHouse queries with incorrect array syntax
"""

import re
from typing import Tuple, Any, Dict
from app.logging_config import central_logger as logger



def fix_clickhouse_array_syntax(query: str) -> str:
    """
    Fix ClickHouse queries that use incorrect array indexing syntax.
    Converts metrics.value[idx] to arrayElement(metrics.value, idx)
    
    Args:
        query: The original ClickHouse query
        
    Returns:
        The fixed query with proper array element access
    """
    
    # Pattern to match incorrect array access like metrics.value[idx] or metrics.value[idx-1]
    # This matches: word.word[expression] where expression can include operations
    pattern = r'(\w+)\.(\w+)\[([^\]]+)\]'
    
    def replace_array_access(match):
        """Replace array[index] with arrayElement(array, index)"""
        nested_field = match.group(1)  # e.g., 'metrics'
        array_field = match.group(2)   # e.g., 'value'
        index_expr = match.group(3)     # e.g., 'idx' or 'position-1'
        
        # Convert to proper ClickHouse syntax with type casting for metrics.value
        if nested_field == 'metrics' and array_field == 'value':
            # Cast to Float64 to avoid type mismatch errors
            replacement = f"toFloat64OrZero(arrayElement({nested_field}.{array_field}, {index_expr}))"
        else:
            replacement = f"arrayElement({nested_field}.{array_field}, {index_expr})"
        
        logger.debug(f"Fixed array access: {match.group(0)} -> {replacement}")
        
        return replacement
    
    # Apply the fix
    fixed_query = re.sub(pattern, replace_array_access, query)
    
    # Log if we made any changes
    if fixed_query != query:
        logger.info("Fixed ClickHouse query with incorrect array syntax")
        logger.debug(f"Original: {query[:200]}...")
        logger.debug(f"Fixed: {fixed_query[:200]}...")
    
    return fixed_query


def validate_clickhouse_query(query: str) -> tuple[bool, str]:
    """
    Validate a ClickHouse query for common syntax errors.
    
    Args:
        query: The ClickHouse query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    # Check for incorrect array access syntax (with any expression inside brackets)
    if re.search(r'\w+\.\w+\[[^\]]+\]', query):
        return False, "Query uses incorrect array syntax. Use arrayElement() instead of []"
    
    # Check for proper nested field access
    if 'metrics.value' in query or 'metrics.name' in query or 'metrics.unit' in query:
        # Ensure we're using proper array functions
        if not any(func in query for func in ['arrayElement', 'arrayFirstIndex', 'arrayExists']):
            logger.warning("Query accesses nested fields without proper array functions")
    
    return True, ""


class ClickHouseQueryInterceptor:
    """
    Intercepts and fixes ClickHouse queries before execution.
    Can be used as a wrapper around the ClickHouse client.
    """
    
    def __init__(self, client: Any) -> None:
        """
        Initialize the interceptor with a ClickHouse client.
        
        Args:
            client: The ClickHouse client to wrap
        """
        self.client = client
        self.fix_enabled = True
        self.queries_fixed = 0
        self.queries_executed = 0
    
    async def execute_query(self, query: str, *args, **kwargs) -> Any:
        """
        Execute a query after fixing any syntax issues.
        
        Args:
            query: The query to execute
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            Query results
        """
        self.queries_executed += 1
        
        # Fix the query if needed
        if self.fix_enabled:
            original_query = query
            llm_was_fixed = False
            
            # First check if it's LLM-generated (lazy import to avoid circular dependency)
            try:
                from app.agents.data_sub_agent.llm_query_detector import LLMQueryDetector
                query, metadata = LLMQueryDetector.validate_and_fix(query)
                if metadata['is_llm_generated']:
                    # Don't log here - LLMQueryDetector already logs
                    if metadata['was_fixed']:
                        llm_was_fixed = True
                        self.queries_fixed += 1
            except ImportError:
                logger.debug("LLMQueryDetector not available, skipping LLM detection")
            
            # Then apply standard fixes (only if LLM didn't already fix it)
            if not llm_was_fixed:
                fixed_query = fix_clickhouse_array_syntax(query)
                if fixed_query != query:
                    query = fixed_query
                    self.queries_fixed += 1
            
            if query != original_query and not llm_was_fixed:
                logger.info(f"Fixed query #{self.queries_executed} (total fixed: {self.queries_fixed})")
        
        # Validate the query
        is_valid, error_msg = validate_clickhouse_query(query)
        if not is_valid:
            logger.error(f"Query validation failed: {error_msg}")
            # Still try to execute - ClickHouse will provide detailed error
        
        # Execute the fixed query
        # Try to call execute_query if it exists, otherwise use execute
        if hasattr(self.client, 'execute_query'):
            return await self.client.execute_query(query, *args, **kwargs)
        else:
            return await self.client.execute(query, *args, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about query fixing.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "queries_executed": self.queries_executed,
            "queries_fixed": self.queries_fixed,
            "fix_rate": self.queries_fixed / max(1, self.queries_executed),
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
        """
        Proxy all other methods to the wrapped client.
        
        Args:
            name: Method name
            
        Returns:
            Method from wrapped client
        """
        return getattr(self.client, name)