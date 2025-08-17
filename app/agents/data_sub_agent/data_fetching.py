"""Data fetching module for DataSubAgent - handles basic data retrieval and caching."""

import json
from typing import Dict, List, Optional, Any
from functools import lru_cache

from app.db.clickhouse import get_clickhouse_client
from app.redis_manager import RedisManager
from app.db.clickhouse_init import create_workload_events_table_if_missing
from app.logging_config import central_logger as logger


class DataFetching:
    """Handles basic data fetching and caching operations"""
    
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
    
    async def check_data_availability(
        self, 
        user_id: int, 
        start_time, 
        end_time
    ) -> Dict[str, Any]:
        """Check if data is available for the specified user and time range"""
        
        query = f"""
        SELECT 
            COUNT(*) as total_records,
            MIN(timestamp) as earliest_record,
            MAX(timestamp) as latest_record,
            COUNT(DISTINCT workload_id) as unique_workloads
        FROM workload_events 
        WHERE user_id = {user_id}
        AND timestamp BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
        """
        
        cache_key = f"data_availability:{user_id}:{start_time.isoformat()}:{end_time.isoformat()}"
        data = await self.fetch_clickhouse_data(query, cache_key)
        
        if not data or not data[0]['total_records']:
            return {
                "available": False,
                "message": "No data available for the specified criteria"
            }
        
        return {
            "available": True,
            "total_records": data[0]['total_records'],
            "earliest_record": data[0]['earliest_record'],
            "latest_record": data[0]['latest_record'],
            "unique_workloads": data[0]['unique_workloads']
        }
    
    async def get_available_metrics(self, user_id: int) -> List[str]:
        """Get list of available metrics for a user"""
        
        query = f"""
        SELECT DISTINCT 
            arrayJoin(JSONExtractKeys(metrics)) as metric_name
        FROM workload_events 
        WHERE user_id = {user_id}
        AND isNotNull(metrics)
        ORDER BY metric_name
        """
        
        cache_key = f"available_metrics:{user_id}"
        data = await self.fetch_clickhouse_data(query, cache_key)
        
        if not data:
            return ["latency_ms", "throughput", "cost_cents", "error_rate"]  # Default metrics
        
        return [row['metric_name'] for row in data if row['metric_name']]
    
    async def get_workload_list(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of workloads for a user"""
        
        query = f"""
        SELECT 
            workload_id,
            COUNT(*) as event_count,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen,
            AVG(JSONExtractFloat(metrics, 'cost_cents')) as avg_cost
        FROM workload_events 
        WHERE user_id = {user_id}
        AND workload_id IS NOT NULL
        GROUP BY workload_id
        ORDER BY last_seen DESC
        LIMIT {limit}
        """
        
        cache_key = f"workload_list:{user_id}:{limit}"
        data = await self.fetch_clickhouse_data(query, cache_key)
        
        return data or []
    
    async def validate_query_parameters(
        self, 
        user_id: int, 
        workload_id: Optional[str],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Validate query parameters against available data"""
        
        validation_result = {
            "valid": True,
            "issues": [],
            "suggestions": []
        }
        
        # Check if user exists
        user_check_query = f"SELECT COUNT(*) as count FROM workload_events WHERE user_id = {user_id}"
        user_data = await self.fetch_clickhouse_data(user_check_query)
        
        if not user_data or user_data[0]['count'] == 0:
            validation_result["valid"] = False
            validation_result["issues"].append(f"No data found for user_id: {user_id}")
            return validation_result
        
        # Check if workload_id exists (if specified)
        if workload_id:
            workload_check_query = f"""
            SELECT COUNT(*) as count 
            FROM workload_events 
            WHERE user_id = {user_id} AND workload_id = '{workload_id}'
            """
            workload_data = await self.fetch_clickhouse_data(workload_check_query)
            
            if not workload_data or workload_data[0]['count'] == 0:
                validation_result["issues"].append(f"No data found for workload_id: {workload_id}")
                validation_result["suggestions"].append("Try without specifying workload_id")
        
        # Check available metrics
        available_metrics = await self.get_available_metrics(user_id)
        invalid_metrics = [m for m in metrics if m not in available_metrics]
        
        if invalid_metrics:
            validation_result["issues"].append(f"Invalid metrics: {invalid_metrics}")
            validation_result["suggestions"].append(f"Available metrics: {available_metrics}")
        
        return validation_result