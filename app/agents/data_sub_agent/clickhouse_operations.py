"""ClickHouse database operations for DataSubAgent."""

import json
from typing import Dict, Optional, Any, List

from app.db.clickhouse import get_clickhouse_client
from app.db.clickhouse_init import create_workload_events_table_if_missing
from app.logging_config import central_logger as logger


class ClickHouseOperations:
    """Handle ClickHouse database operations."""
    
    def _validate_table_name(self, table_name: str) -> bool:
        """Validate table name to prevent SQL injection."""
        if not table_name or not table_name.replace('_', '').replace('.', '').isalnum():
            logger.error(f"Invalid table name format: {table_name}")
            return False
        return True
    
    def _build_describe_query(self, table_name: str, client) -> str:
        """Build DESCRIBE TABLE query with escaped table name."""
        return "DESCRIBE TABLE {}".format(client.escape_identifier(table_name))
    
    async def _execute_describe_query(self, table_name: str) -> Optional[List[Any]]:
        """Execute DESCRIBE TABLE query."""
        try:
            async with get_clickhouse_client() as client:
                query = self._build_describe_query(table_name, client)
                return await client.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return None
    
    def _format_schema_result(self, result: List[Any], table_name: str) -> Dict[str, Any]:
        """Format schema query result."""
        return {
            "columns": [{"name": row[0], "type": row[1]} for row in result],
            "table": table_name
        }
    
    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get schema information for a table."""
        if not self._validate_table_name(table_name):
            return None
        result = await self._execute_describe_query(table_name)
        if result is None:
            return None
        return self._format_schema_result(result, table_name)
    
    async def _get_cached_data(self, cache_key: str, redis_manager) -> Optional[str]:
        """Get cached data from Redis."""
        try:
            return await redis_manager.get(cache_key)
        except Exception as e:
            logger.debug(f"Cache retrieval failed: {e}")
            return None
    
    async def _check_cache(self, cache_key: Optional[str], redis_manager) -> Optional[List[Dict[str, Any]]]:
        """Check Redis cache for cached query result."""
        if not cache_key or not redis_manager:
            return None
        cached = await self._get_cached_data(cache_key, redis_manager)
        return json.loads(cached) if cached else None
    
    async def _prepare_and_execute_query(self, query: str) -> Optional[List[Any]]:
        """Prepare table and execute query."""
        await create_workload_events_table_if_missing()
        async with get_clickhouse_client() as client:
            return await client.execute_query(query)
    
    async def _execute_clickhouse_query(self, query: str) -> Optional[List[Any]]:
        """Execute ClickHouse query after ensuring table exists."""
        try:
            return await self._prepare_and_execute_query(query)
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            return None
    
    def _convert_result_to_dicts(self, result: List[Any]) -> List[Dict[str, Any]]:
        """Convert query result to list of dictionaries."""
        if not result:
            return []
        columns = result[0]._fields if hasattr(result[0], '_fields') else list(range(len(result[0])))
        return [dict(zip(columns, row)) for row in result]
    
    async def _cache_result(self, data: List[Dict[str, Any]], cache_key: Optional[str], redis_manager, cache_ttl: int) -> None:
        """Cache query result in Redis."""
        if not cache_key or not redis_manager:
            return
        try:
            await redis_manager.set(cache_key, json.dumps(data, default=str), ex=cache_ttl)
        except Exception as e:
            logger.debug(f"Cache storage failed: {e}")
    
    async def fetch_data(
        self,
        query: str,
        cache_key: Optional[str] = None,
        redis_manager = None,
        cache_ttl: int = 300
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute ClickHouse query with caching support."""
        cached_result = await self._check_cache(cache_key, redis_manager)
        if cached_result is not None:
            return cached_result
        
        result = await self._execute_clickhouse_query(query)
        if result is None:
            return None
        
        data = self._convert_result_to_dicts(result)
        await self._cache_result(data, cache_key, redis_manager, cache_ttl)
        return data