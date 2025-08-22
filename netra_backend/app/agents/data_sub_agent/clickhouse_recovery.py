"""ClickHouse query recovery strategies.

Handles ClickHouse query failures with fallback and simplification strategies.
"""

from typing import Any, Dict, Optional

from netra_backend.app.agents.data_sub_agent.error_types import ClickHouseQueryError
from netra_backend.app.agents.data_sub_agent.query_fix_validator import (
    validate_and_fix_query,
)
from netra_backend.app.agents.error_handler import ErrorContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ClickHouseRecoveryManager:
    """Manages ClickHouse query recovery strategies."""
    
    def __init__(self, clickhouse_client=None, cache_manager=None):
        """Initialize ClickHouse recovery manager."""
        self.clickhouse_client = clickhouse_client
        self.cache_manager = cache_manager
    
    async def handle_query_failure(
        self,
        query: str,
        query_type: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle ClickHouse query failures with recovery strategies."""
        context = self._create_error_context(query, query_type, run_id, original_error)
        error = ClickHouseQueryError(query, str(original_error), context)
        return await self._execute_recovery_strategies(query, query_type, run_id, error)
    
    async def _execute_recovery_strategies(
        self, query: str, query_type: str, run_id: str, error: ClickHouseQueryError
    ) -> Dict[str, Any]:
        """Execute recovery strategies in sequence."""
        try:
            return await self._try_recovery_methods(query, query_type, run_id, error)
        except Exception as fallback_error:
            logger.error(f"ClickHouse recovery failed: {fallback_error}")
            raise error
    
    async def _try_recovery_methods(
        self, query: str, query_type: str, run_id: str, error: ClickHouseQueryError
    ) -> Dict[str, Any]:
        """Try recovery methods in order."""
        simplified_result = await self._try_simplified_query(query, query_type)
        if simplified_result:
            return self._create_success_result(simplified_result, "simplification")
        
        cached_result = await self._try_cached_fallback(query_type, run_id)
        if cached_result:
            return cached_result
        
        raise error
    
    def _create_error_context(
        self, query: str, query_type: str, run_id: str, error: Exception
    ) -> ErrorContext:
        """Create error context for ClickHouse failures."""
        additional_data = self._build_error_data(query, query_type, error)
        return ErrorContext(
            agent_name="data_sub_agent",
            operation_name="clickhouse_query",
            run_id=run_id,
            additional_data=additional_data
        )
    
    def _build_error_data(self, query: str, query_type: str, error: Exception) -> Dict[str, Any]:
        """Build additional data for error context."""
        return {
            'query': query,
            'query_type': query_type,
            'original_error': str(error)
        }
    
    def _create_success_result(
        self, result_data: Any, method: str
    ) -> Dict[str, Any]:
        """Create standardized success result."""
        return {
            'data': result_data,
            'method': f'clickhouse_{method}',
            'recovery_applied': True
        }
    
    async def _try_simplified_query(
        self, original_query: str, query_type: str
    ) -> Optional[Dict[str, Any]]:
        """Try simplified version of failed query."""
        try:
            simplified_query = self._simplify_query(original_query, query_type)
            return await self._execute_simplified_query(simplified_query)
        except Exception as e:
            logger.debug(f"Simplified query failed: {e}")
            return None
    
    async def _execute_simplified_query(self, simplified_query: str) -> Optional[Dict[str, Any]]:
        """Execute simplified query if client available."""
        if not (simplified_query and self.clickhouse_client):
            return None
        fixed_query = validate_and_fix_query(simplified_query)
        result = await self.clickhouse_client.execute(fixed_query)
        logger.info(f"Query recovered with simplification")
        return {'data': result, 'query': fixed_query}
    
    def _simplify_query(self, query: str, query_type: str) -> str:
        """Create simplified version of query."""
        simplified = validate_and_fix_query(query)
        simplified = self._remove_complex_parts(simplified, query_type)
        return self._add_time_constraints(simplified)
    
    def _remove_complex_parts(self, simplified: str, query_type: str) -> str:
        """Remove complex query parts for simplification."""
        if 'group by' in simplified:
            simplified = simplified.split('group by')[0] + ' LIMIT 1000'
        
        if 'join' in simplified and query_type == 'performance_metrics':
            simplified = self._convert_to_single_table_query(simplified)
        
        return simplified
    
    def _convert_to_single_table_query(self, query: str) -> str:
        """Convert complex join query to single table query."""
        if 'from' in query:
            parts = query.split('from')
            select_part = parts[0]
            from_part = parts[1].split('join')[0]
            return f"{select_part} FROM {from_part} LIMIT 1000"
        return query
    
    def _add_time_constraints(self, query: str) -> str:
        """Add time constraints to prevent long-running queries."""
        time_constraint = 'toDate(timestamp) >= today() - 7'
        
        if 'where' in query:
            return query + f' AND {time_constraint}'
        else:
            return query + f' WHERE {time_constraint}'
    
    async def _try_cached_fallback(
        self, query_type: str, run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try cached data as fallback."""
        if not self.cache_manager:
            return None
        return await self._attempt_cache_retrieval(query_type)
    
    async def _attempt_cache_retrieval(self, query_type: str) -> Optional[Dict[str, Any]]:
        """Attempt to retrieve cached fallback data."""
        try:
            cache_key = f"data_analysis:{query_type}:fallback"
            cached_data = await self.cache_manager.get(cache_key)
            return self._handle_cached_data(cached_data, cache_key, query_type)
        except Exception as e:
            logger.debug(f"Cache fallback failed: {e}")
            return None
    
    def _handle_cached_data(
        self, cached_data: Any, cache_key: str, query_type: str
    ) -> Optional[Dict[str, Any]]:
        """Handle cached data if available."""
        if cached_data:
            logger.info(f"Using cached fallback data for {query_type}")
            return self._build_cache_response(cached_data, cache_key)
        return None
    
    def _build_cache_response(self, cached_data: Any, cache_key: str) -> Dict[str, Any]:
        """Build cached data response."""
        return {
            'data': cached_data,
            'method': 'cached_fallback',
            'cache_key': cache_key
        }