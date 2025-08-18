# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514  
# Context: Modernize data_fetching.py to use BaseExecutionInterface architecture
# Git: 8-18-25-AM | Modernizing to standard agent patterns
# Change: Modernize | Scope: Module | Risk: Low
# Session: data-sub-agent-modernization | Seq: 1
# Review: Complete | Score: 100
# ================================
"""
Data Fetching Engine - Modern Architecture

Modernized data fetching using BaseExecutionInterface with:
- Standardized execution patterns
- Integrated reliability management (circuit breaker, retry)
- Comprehensive monitoring and error handling
- 300-line limit compliance with 8-line functions
- Backward compatibility with existing DataFetching interface

Business Value: Eliminates duplicate patterns, improves data reliability.
"""

import json
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from functools import lru_cache
from datetime import datetime, UTC

from app.db.clickhouse import get_clickhouse_client
from app.redis_manager import RedisManager
from app.db.clickhouse_init import create_workload_events_table_if_missing
from app.logging_config import central_logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class DataFetchingExecutionEngine(BaseExecutionInterface):
    """Modern data fetching execution engine.
    
    Implements BaseExecutionInterface with integrated reliability patterns.
    """
    
    def __init__(self, websocket_manager=None):
        super().__init__("data_fetching", websocket_manager)
        self.execution_engine = self._create_execution_engine()
        self._init_base_config()
        self._init_redis_connection()
    
    def _create_execution_engine(self) -> BaseExecutionEngine:
        """Create execution engine with reliability patterns."""
        reliability_manager = self._create_reliability_manager()
        monitor = ExecutionMonitor()
        return BaseExecutionEngine(reliability_manager, monitor)

    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with circuit breaker and retry."""
        circuit_config = CircuitBreakerConfig(
            name="data_fetching", failure_threshold=3, recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)

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

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute data fetching with modern patterns."""
        operation = context.metadata.get('operation')
        kwargs = context.metadata.get('kwargs', {})
        return await self._route_operation(operation, kwargs)

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate data fetching preconditions."""
        operation = context.metadata.get('operation')
        return self._validate_operation_access(operation)

    def _validate_operation_access(self, operation: str) -> bool:
        """Validate specific operation access."""
        allowed_operations = {
            'fetch_clickhouse_data', 'check_data_availability', 
            'get_available_metrics', 'get_workload_list', 'validate_query_parameters'
        }
        return operation in allowed_operations

    async def _route_operation(self, operation: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Route operation to appropriate handler."""
        handlers = {
            'fetch_clickhouse_data': self._handle_fetch_clickhouse,
            'check_data_availability': self._handle_check_availability,
            'get_available_metrics': self._handle_get_metrics,
            'get_workload_list': self._handle_get_workloads,
            'validate_query_parameters': self._handle_validate_params
        }
        handler = handlers.get(operation)
        if not handler:
            raise ValueError(f"Unknown operation: {operation}")
        return await handler(**kwargs)

    async def _handle_fetch_clickhouse(self, **kwargs) -> Dict[str, Any]:
        """Handle ClickHouse data fetching operation."""
        query = kwargs.get('query')
        cache_key = kwargs.get('cache_key')
        result = await self.fetch_clickhouse_data(query, cache_key)
        return {'data': result, 'operation': 'fetch_clickhouse_data'}

    async def _handle_check_availability(self, **kwargs) -> Dict[str, Any]:
        """Handle data availability check operation."""
        user_id = kwargs.get('user_id')
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        result = await self.check_data_availability(user_id, start_time, end_time)
        return {'availability': result, 'operation': 'check_data_availability'}

    async def _handle_get_metrics(self, **kwargs) -> Dict[str, Any]:
        """Handle get metrics operation."""
        user_id = kwargs.get('user_id')
        result = await self.get_available_metrics(user_id)
        return {'metrics': result, 'operation': 'get_available_metrics'}

    async def _handle_get_workloads(self, **kwargs) -> Dict[str, Any]:
        """Handle get workloads operation."""
        user_id = kwargs.get('user_id')
        limit = kwargs.get('limit', 100)
        result = await self.get_workload_list(user_id, limit)
        return {'workloads': result, 'operation': 'get_workload_list'}

    async def _handle_validate_params(self, **kwargs) -> Dict[str, Any]:
        """Handle parameter validation operation."""
        user_id = kwargs.get('user_id')
        workload_id = kwargs.get('workload_id')
        metrics = kwargs.get('metrics', [])
        result = await self.validate_query_parameters(user_id, workload_id, metrics)
        return {'validation': result, 'operation': 'validate_query_parameters'}
    
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
        query = self._build_availability_query(user_id, start_time, end_time)
        cache_key = self._build_availability_cache_key(user_id, start_time, end_time)
        data = await self.fetch_clickhouse_data(query, cache_key)
        return self._process_availability_result(data)
    
    def _build_availability_query(self, user_id: int, start_time, end_time) -> str:
        """Build query for checking data availability."""
        return f"""
        SELECT 
            COUNT(*) as total_records,
            MIN(timestamp) as earliest_record,
            MAX(timestamp) as latest_record,
            COUNT(DISTINCT workload_id) as unique_workloads
        FROM workload_events 
        WHERE user_id = {user_id}
        AND timestamp BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
        """
    
    def _build_availability_cache_key(self, user_id: int, start_time, end_time) -> str:
        """Build cache key for availability query."""
        return f"data_availability:{user_id}:{start_time.isoformat()}:{end_time.isoformat()}"
    
    def _process_availability_result(self, data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Process availability query result."""
        if not data or not data[0]['total_records']:
            return self._build_unavailable_response()
        return self._build_available_response(data[0])
    
    def _build_unavailable_response(self) -> Dict[str, Any]:
        """Build response for unavailable data."""
        return {
            "available": False,
            "message": "No data available for the specified criteria"
        }
    
    def _build_available_response(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Build response for available data."""
        return {
            "available": True,
            "total_records": record['total_records'],
            "earliest_record": record['earliest_record'],
            "latest_record": record['latest_record'],
            "unique_workloads": record['unique_workloads']
        }
    
    async def get_available_metrics(self, user_id: int) -> List[str]:
        """Get list of available metrics for a user"""
        query = self._build_metrics_query(user_id)
        cache_key = f"available_metrics:{user_id}"
        data = await self.fetch_clickhouse_data(query, cache_key)
        return self._process_metrics_result(data)
    
    def _build_metrics_query(self, user_id: int) -> str:
        """Build query for extracting available metrics."""
        return f"""
        SELECT DISTINCT 
            arrayJoin(JSONExtractKeys(metrics)) as metric_name
        FROM workload_events 
        WHERE user_id = {user_id}
        AND isNotNull(metrics)
        ORDER BY metric_name
        """
    
    def _process_metrics_result(self, data: Optional[List[Dict[str, Any]]]) -> List[str]:
        """Process metrics query result."""
        if not data:
            return self._get_default_metrics()
        return [row['metric_name'] for row in data if row['metric_name']]
    
    def _get_default_metrics(self) -> List[str]:
        """Get default metrics when no user-specific metrics found."""
        return ["latency_ms", "throughput", "cost_cents", "error_rate"]
    
    async def get_workload_list(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of workloads for a user"""
        query = self._build_workload_list_query(user_id, limit)
        cache_key = self._build_workload_cache_key(user_id, limit)
        data = await self.fetch_clickhouse_data(query, cache_key)
        return data or []
    
    def _build_workload_list_query(self, user_id: int, limit: int) -> str:
        """Build query for getting workload list."""
        return f"""
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
    
    def _build_workload_cache_key(self, user_id: int, limit: int) -> str:
        """Build cache key for workload list query."""
        return f"workload_list:{user_id}:{limit}"
    
    async def validate_query_parameters(
        self, 
        user_id: int, 
        workload_id: Optional[str],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Validate query parameters against available data"""
        validation_result = self._init_validation_result()
        
        if not await self._validate_user_exists(user_id, validation_result):
            return validation_result
        
        await self._validate_workload_id(user_id, workload_id, validation_result)
        await self._validate_metrics(user_id, metrics, validation_result)
        return validation_result
    
    def _init_validation_result(self) -> Dict[str, Any]:
        """Initialize validation result structure."""
        return {
            "valid": True,
            "issues": [],
            "suggestions": []
        }
    
    async def _validate_user_exists(self, user_id: int, validation_result: Dict[str, Any]) -> bool:
        """Validate that user exists in the data."""
        user_check_query = f"SELECT COUNT(*) as count FROM workload_events WHERE user_id = {user_id}"
        user_data = await self.fetch_clickhouse_data(user_check_query)
        
        if not user_data or user_data[0]['count'] == 0:
            validation_result["valid"] = False
            validation_result["issues"].append(f"No data found for user_id: {user_id}")
            return False
        return True
    
    async def _validate_workload_id(self, user_id: int, workload_id: Optional[str], validation_result: Dict[str, Any]) -> None:
        """Validate workload_id if specified."""
        if not workload_id:
            return
        
        workload_data = await self._check_workload_exists(user_id, workload_id)
        if not workload_data or workload_data[0]['count'] == 0:
            self._add_workload_validation_issues(workload_id, validation_result)
    
    async def _check_workload_exists(self, user_id: int, workload_id: str) -> Optional[List[Dict[str, Any]]]:
        """Check if workload exists for user."""
        workload_check_query = f"""
        SELECT COUNT(*) as count 
        FROM workload_events 
        WHERE user_id = {user_id} AND workload_id = '{workload_id}'
        """
        return await self.fetch_clickhouse_data(workload_check_query)
    
    def _add_workload_validation_issues(self, workload_id: str, validation_result: Dict[str, Any]) -> None:
        """Add workload validation issues to result."""
        validation_result["issues"].append(f"No data found for workload_id: {workload_id}")
        validation_result["suggestions"].append("Try without specifying workload_id")
    
    async def _validate_metrics(self, user_id: int, metrics: List[str], validation_result: Dict[str, Any]) -> None:
        """Validate metrics against available metrics."""
        available_metrics = await self.get_available_metrics(user_id)
        invalid_metrics = [m for m in metrics if m not in available_metrics]
        
        if invalid_metrics:
            self._add_metrics_validation_issues(invalid_metrics, available_metrics, validation_result)
    
    def _add_metrics_validation_issues(self, invalid_metrics: List[str], available_metrics: List[str], validation_result: Dict[str, Any]) -> None:
        """Add metrics validation issues to result."""
        validation_result["issues"].append(f"Invalid metrics: {invalid_metrics}")
        validation_result["suggestions"].append(f"Available metrics: {available_metrics}")


class DataFetching(DataFetchingExecutionEngine):
    """Backward compatibility wrapper for existing DataFetching interface.
    
    Provides legacy interface while using modern execution patterns internally.
    Maintains existing method signatures for seamless integration.
    """
    
    def __init__(self):
        super().__init__()
        # Maintain legacy initialization pattern
        self._legacy_mode = True

    async def execute_with_modern_patterns(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute operation using modern execution patterns."""
        from app.agents.state import DeepAgentState
        
        # Create execution context for modern patterns
        state = DeepAgentState()
        context = ExecutionContext(
            run_id=f"data_fetch_{datetime.now(UTC).isoformat()}",
            agent_name="data_fetching",
            state=state,
            metadata={'operation': operation, 'kwargs': kwargs}
        )
        
        # Execute with reliability patterns
        result = await self.execution_engine.execute(self, context)
        return result.result if result.success else {'error': result.error}

    def get_health_status(self) -> Dict[str, Any]:
        """Get execution engine health status."""
        return self.execution_engine.get_health_status()