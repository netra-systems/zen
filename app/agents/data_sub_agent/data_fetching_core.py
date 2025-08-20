# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514  
# Context: Core data fetching operations module (450-line compliance)
# Git: 8-18-25-AM | Modernizing to standard agent patterns
# Change: Create | Scope: Module | Risk: Low
# Session: data-sub-agent-modernization | Seq: 2
# Review: Complete | Score: 100
# ================================
"""
Data Fetching Core Operations

Core data retrieval and caching operations for DataSubAgent.
Handles ClickHouse queries, Redis caching, and schema operations.

Business Value: Centralized data access patterns with caching optimization.
"""

import json
from typing import Dict, List, Optional, Any
from functools import lru_cache

from app.db.clickhouse import get_clickhouse_client
from app.redis_manager import RedisManager
from app.db.clickhouse_init import create_workload_events_table_if_missing
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataFetchingCore:
    """Core data fetching operations with caching."""
    
    def __init__(self):
        self._init_base_config()
        self._init_redis_connection()
    
    def _init_base_config(self) -> None:
        """Initialize base configuration parameters."""
        self.redis_manager = None
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    def _init_redis_connection(self) -> None:
        """Initialize Redis connection with error handling."""
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for DataFetching caching: {e}")
    
    @lru_cache(maxsize=128)
    async def get_cached_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get cached schema information for a table"""
        if not self._validate_table_name(table_name):
            return None
        return await self._execute_schema_query(table_name)
    
    def _validate_table_name(self, table_name: str) -> bool:
        """Validate table name to prevent SQL injection."""
        if not table_name or not table_name.replace('_', '').replace('.', '').isalnum():
            logger.error(f"Invalid table name format: {table_name}")
            return False
        return True
    
    async def _execute_schema_query(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Execute schema query and return formatted result."""
        try:
            return await self._perform_schema_query(table_name)
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return None
    
    async def _perform_schema_query(self, table_name: str) -> Dict[str, Any]:
        """Perform the actual schema query."""
        async with get_clickhouse_client() as client:
            query = "DESCRIBE TABLE {}"
            result = await client.execute_query(query.format(client.escape_identifier(table_name)))
            return self._format_schema_result(result, table_name)
    
    def _format_schema_result(self, result: List[Any], table_name: str) -> Dict[str, Any]:
        """Format schema query result into structured format."""
        return {
            "columns": [{"name": row[0], "type": row[1]} for row in result],
            "table": table_name
        }
    
    async def fetch_clickhouse_data(
        self,
        query: str,
        cache_key: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute ClickHouse query with caching support"""
        cached_result = await self._check_cache_for_query(cache_key)
        if cached_result is not None:
            return cached_result
        return await self._execute_and_cache_query(query, cache_key)
    
    async def _check_cache_for_query(self, cache_key: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        """Check cache for existing query result."""
        if not cache_key or not self.redis_manager:
            return None
        try:
            cached = await self.redis_manager.get(cache_key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.debug(f"Cache retrieval failed: {e}")
            return None
    
    async def _execute_and_cache_query(self, query: str, cache_key: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        """Execute query and cache result."""
        try:
            data = await self._execute_clickhouse_query_internal(query)
            await self._cache_query_result(data, cache_key)
            return data
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            return None
    
    async def _execute_clickhouse_query_internal(self, query: str) -> List[Dict[str, Any]]:
        """Execute ClickHouse query and convert result."""
        await create_workload_events_table_if_missing()
        async with get_clickhouse_client() as client:
            result = await client.execute_query(query)
            return self._convert_query_result_to_dicts(result)
    
    def _convert_query_result_to_dicts(self, result: List[Any]) -> List[Dict[str, Any]]:
        """Convert query result to list of dictionaries."""
        if not result:
            return []
        columns = self._extract_column_names(result[0])
        return [dict(zip(columns, row)) for row in result]
    
    def _extract_column_names(self, first_row: Any) -> List[str]:
        """Extract column names from first result row."""
        if hasattr(first_row, '_fields'):
            return first_row._fields
        return list(range(len(first_row)))
    
    async def _cache_query_result(self, data: List[Dict[str, Any]], cache_key: Optional[str]) -> None:
        """Cache query result if cache key and manager available."""
        if not cache_key or not self.redis_manager or data is None:
            return
        try:
            await self.redis_manager.set(
                cache_key, json.dumps(data, default=str), ex=self.cache_ttl
            )
        except Exception as e:
            logger.debug(f"Cache storage failed: {e}")