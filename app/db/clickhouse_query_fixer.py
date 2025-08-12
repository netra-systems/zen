"""
ClickHouse Query Fixer
Intercepts and fixes ClickHouse queries with incorrect array syntax
"""

import re
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
    
    # Pattern to match incorrect array access like metrics.value[idx]
    # This matches: word.word[identifier]
    pattern = r'(\w+)\.(\w+)\[(\w+)\]'
    
    def replace_array_access(match):
        """Replace array[index] with arrayElement(array, index)"""
        nested_field = match.group(1)  # e.g., 'metrics'
        array_field = match.group(2)   # e.g., 'value'
        index_var = match.group(3)      # e.g., 'idx'
        
        # Convert to proper ClickHouse syntax
        replacement = f"arrayElement({nested_field}.{array_field}, {index_var})"
        
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
    
    # Check for incorrect array access syntax
    if re.search(r'\w+\.\w+\[\w+\]', query):
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
    
    def __init__(self, client):
        """
        Initialize the interceptor with a ClickHouse client.
        
        Args:
            client: The ClickHouse client to wrap
        """
        self.client = client
        self.fix_enabled = True
        self.queries_fixed = 0
        self.queries_executed = 0
    
    async def execute_query(self, query: str, *args, **kwargs):
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
            query = fix_clickhouse_array_syntax(query)
            
            if query != original_query:
                self.queries_fixed += 1
                logger.info(f"Fixed query #{self.queries_executed} (total fixed: {self.queries_fixed})")
        
        # Validate the query
        is_valid, error_msg = validate_clickhouse_query(query)
        if not is_valid:
            logger.error(f"Query validation failed: {error_msg}")
            # Still try to execute - ClickHouse will provide detailed error
        
        # Execute the fixed query
        return await self.client.execute_query(query, *args, **kwargs)
    
    def get_stats(self) -> dict:
        """
        Get statistics about query fixing.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "queries_executed": self.queries_executed,
            "queries_fixed": self.queries_fixed,
            "fix_rate": self.queries_fixed / max(1, self.queries_executed)
        }
    
    def __getattr__(self, name):
        """
        Proxy all other methods to the wrapped client.
        
        Args:
            name: Method name
            
        Returns:
            Method from wrapped client
        """
        return getattr(self.client, name)