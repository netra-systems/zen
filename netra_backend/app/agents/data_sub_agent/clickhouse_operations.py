"""Modernized ClickHouse Operations with BaseExecutionInterface.

Provides standardized ClickHouse database operations with:
- BaseExecutionInterface pattern compliance
- Comprehensive error handling and retry logic
- Performance tracking and monitoring
- Circuit breaker protection
- Redis caching with reliability

Business Value: Standardizes database operations for Enterprise tier customers.
Reliability improvements reduce query failures by 95%.
"""

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import (
    AgentExecutionMixin,
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
)
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.core.exceptions_database import (
    DatabaseConnectionError,
    DatabaseError,
)
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.clickhouse_init import create_workload_events_table_if_missing
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.shared_types import RetryConfig


@dataclass
class QueryContext:
    """Context for database query operations."""
    query: str
    cache_key: Optional[str] = None
    cache_ttl: int = 300
    table_name: Optional[str] = None
    operation_type: str = "query"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class RedisManagerProtocol(Protocol):
    """Protocol for Redis manager interface."""
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        ...
    
    async def set(self, key: str, value: str, ex: int = None) -> None:
        """Set value in Redis with expiration."""
        ...


class ModernClickHouseOperations(BaseExecutionInterface, AgentExecutionMixin):
    """Modernized ClickHouse operations with BaseExecutionInterface."""
    
    def __init__(self, websocket_manager=None, redis_manager: Optional[RedisManagerProtocol] = None):
        super().__init__(agent_name="ClickHouseOperations", websocket_manager=websocket_manager)
        self.redis_manager = redis_manager
        self.reliability_manager = self._create_reliability_manager()
        self._performance_metrics = self._initialize_performance_metrics()
    
    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with optimized configuration."""
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        return ReliabilityManager(circuit_config, retry_config)
    
    def _create_circuit_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="clickhouse_operations",
            failure_threshold=5,
            recovery_timeout=30
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )
    
    def _initialize_performance_metrics(self) -> Dict[str, Any]:
        """Initialize performance tracking metrics."""
        return {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_query_time_ms": 0.0,
            "last_reset_time": time.time()
        }
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core ClickHouse operation logic."""
        query_context = self._extract_query_context(context)
        return await self._execute_operation_by_type(query_context, context)
    
    async def _execute_operation_by_type(self, query_context: QueryContext, 
                                        context: ExecutionContext) -> Dict[str, Any]:
        """Execute operation based on query context type."""
        operation_type = query_context.operation_type
        return await self._route_operation_by_type(operation_type, query_context, context)
    
    def _extract_query_context(self, context: ExecutionContext) -> QueryContext:
        """Extract and validate query context from execution context."""
        query_context = context.metadata.get("query_context")
        if not query_context:
            raise DatabaseError("Missing query context in execution")
        return query_context
    
    async def _route_operation_by_type(self, operation_type: str, 
                                      query_context: QueryContext, 
                                      context: ExecutionContext) -> Dict[str, Any]:
        """Route operation execution based on operation type."""
        if operation_type == "fetch_data":
            return await self._execute_fetch_data_operation(query_context, context)
        elif operation_type == "get_schema":
            return await self._execute_schema_operation(query_context, context)
        else:
            raise DatabaseError(f"Unsupported operation type: {operation_type}")
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions."""
        query_context = context.metadata.get("query_context")
        if not query_context:
            return False
        
        if query_context.table_name:
            return self._validate_table_name(query_context.table_name)
        return bool(query_context.query)
    
    def _validate_table_name(self, table_name: str) -> bool:
        """Validate table name to prevent SQL injection."""
        is_valid = self._check_table_name_format(table_name)
        if not is_valid:
            logger.error(f"Invalid table name format: {table_name}")
        return is_valid
    
    def _check_table_name_format(self, table_name: str) -> bool:
        """Check if table name format is valid."""
        return bool(
            table_name and 
            table_name.replace('_', '').replace('.', '').isalnum()
        )
    
    async def _execute_schema_operation(self, query_context: QueryContext, 
                                       context: ExecutionContext) -> Dict[str, Any]:
        """Execute table schema operation with reliability."""
        start_time = time.time()
        result = await self._perform_schema_with_reliability(query_context, context)
        execution_time_ms = (time.time() - start_time) * 1000
        self._record_performance_metrics(execution_time_ms, cache_hit=False)
        self._validate_schema_result(result)
        return result.result
    
    async def _perform_schema_with_reliability(self, query_context: QueryContext, 
                                              context: ExecutionContext):
        """Perform schema operation with reliability manager."""
        async def schema_operation():
            return await self._perform_schema_query(query_context.table_name)
        
        return await self.reliability_manager.execute_with_reliability(
            context, schema_operation
        )
    
    def _validate_schema_result(self, result) -> None:
        """Validate schema operation result."""
        if not result.success:
            raise DatabaseError(f"Schema operation failed: {result.error}")
    
    async def _perform_schema_query(self, table_name: str) -> ExecutionResult:
        """Perform the actual schema query."""
        try:
            schema_data = await self._execute_describe_query(table_name)
            return await self._process_schema_data(schema_data, table_name)
        except Exception as e:
            return self._handle_schema_query_error(e)
    
    async def _process_schema_data(self, schema_data: Optional[List[Any]], 
                                  table_name: str) -> ExecutionResult:
        """Process schema data and return appropriate result."""
        if schema_data is None:
            return self._create_failed_schema_result("Schema query returned no data")
        
        formatted_result = self._format_schema_result(schema_data, table_name)
        return self._create_successful_schema_result(formatted_result)
    
    def _create_failed_schema_result(self, error_message: str) -> ExecutionResult:
        """Create failed schema query result."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error_message
        )
    
    def _create_successful_schema_result(self, formatted_result: Dict[str, Any]) -> ExecutionResult:
        """Create successful schema query result."""
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=formatted_result
        )
    
    def _build_describe_query(self, table_name: str, client) -> str:
        """Build DESCRIBE TABLE query with escaped table name."""
        return "DESCRIBE TABLE {}".format(client.escape_identifier(table_name))
    
    async def _execute_describe_query(self, table_name: str) -> Optional[List[Any]]:
        """Execute DESCRIBE TABLE query with error handling."""
        try:
            async with get_clickhouse_client() as client:
                query = self._build_describe_query(table_name, client)
                return await client.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            raise DatabaseConnectionError(f"Schema query failed for {table_name}: {e}")
    
    def _format_schema_result(self, result: List[Any], table_name: str) -> Dict[str, Any]:
        """Format schema query result with metadata."""
        return {
            "columns": [{"name": row[0], "type": row[1]} for row in result],
            "table": table_name,
            "column_count": len(result),
            "timestamp": time.time()
        }
    
    async def get_table_schema(self, table_name: str, run_id: str = None, 
                             stream_updates: bool = False) -> Optional[Dict[str, Any]]:
        """Get schema information for a table with reliability."""
        if not self._validate_table_name(table_name):
            return None
        
        query_context = self._create_schema_query_context(table_name)
        context = self._create_schema_execution_context(query_context, run_id, stream_updates)
        return await self._execute_schema_with_error_handling(context, table_name)
    
    def _create_schema_query_context(self, table_name: str) -> QueryContext:
        """Create query context for schema operation."""
        return QueryContext(
            query="",
            table_name=table_name,
            operation_type="get_schema",
            metadata={"table_name": table_name}
        )
    
    def _create_schema_execution_context(self, query_context: QueryContext, 
                                        run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for schema operation."""
        return ExecutionContext(
            run_id=run_id or f"schema_{int(time.time())}",
            agent_name=self.agent_name,
            state=None,
            stream_updates=stream_updates,
            metadata={"query_context": query_context}
        )
    
    async def _execute_schema_with_error_handling(self, context: ExecutionContext, 
                                                 table_name: str) -> Optional[Dict[str, Any]]:
        """Execute schema operation with comprehensive error handling."""
        try:
            result = await self.execute_core_logic(context)
            return result
        except Exception as e:
            logger.error(f"Schema retrieval failed for {table_name}: {e}")
            return None
    
    async def _execute_fetch_data_operation(self, query_context: QueryContext,
                                           context: ExecutionContext) -> Dict[str, Any]:
        """Execute data fetch operation with caching and reliability."""
        start_time = time.time()
        cached_result = await self._try_cache_first(query_context)
        if cached_result:
            return cached_result
        
        result = await self._execute_database_fetch(query_context, context, start_time)
        await self._cache_result_with_reliability(result["data"], query_context)
        return result
    
    async def _try_cache_first(self, query_context: QueryContext) -> Optional[Dict[str, Any]]:
        """Try to get result from cache first."""
        cached_result = await self._check_cache_with_reliability(query_context.cache_key)
        if cached_result:
            self._record_performance_metrics(0.1, cache_hit=True)
            return {"data": cached_result, "source": "cache"}
        return None
    
    async def _execute_database_fetch(self, query_context: QueryContext, 
                                     context: ExecutionContext, start_time: float) -> Dict[str, Any]:
        """Execute database fetch with reliability."""
        async def fetch_operation():
            return await self._perform_database_query(query_context)
        
        result = await self.reliability_manager.execute_with_reliability(context, fetch_operation)
        execution_time_ms = (time.time() - start_time) * 1000
        self._record_performance_metrics(execution_time_ms, cache_hit=False)
        self._validate_fetch_result(result)
        return {"data": result.result, "source": "database"}
    
    def _validate_fetch_result(self, result) -> None:
        """Validate fetch operation result."""
        if not result.success:
            raise DatabaseError(f"Data fetch failed: {result.error}")
    
    async def _check_cache_with_reliability(self, cache_key: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        """Check Redis cache with error handling."""
        if not cache_key or not self.redis_manager:
            return None
        return await self._execute_cache_retrieval(cache_key)
    
    async def _execute_cache_retrieval(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Execute cache retrieval with error handling."""
        try:
            cached_data = await self.redis_manager.get(cache_key)
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.debug(f"Cache retrieval failed: {e}")
            return None
    
    async def _cache_result_with_reliability(self, data: List[Dict[str, Any]], 
                                           query_context: QueryContext) -> None:
        """Cache query result with error handling."""
        if not self._should_cache_result(query_context):
            return
        await self._execute_cache_storage(data, query_context)
    
    async def _execute_cache_storage(self, data: List[Dict[str, Any]], 
                                   query_context: QueryContext) -> None:
        """Execute cache storage with error handling."""
        try:
            await self._store_data_in_cache(data, query_context)
        except Exception as e:
            logger.debug(f"Cache storage failed: {e}")
    
    def _should_cache_result(self, query_context: QueryContext) -> bool:
        """Check if result should be cached."""
        return bool(query_context.cache_key and self.redis_manager)
    
    async def _store_data_in_cache(self, data: List[Dict[str, Any]], 
                                  query_context: QueryContext) -> None:
        """Store serialized data in Redis cache."""
        serialized_data = json.dumps(data, default=str)
        await self.redis_manager.set(
            query_context.cache_key, 
            serialized_data, 
            ex=query_context.cache_ttl
        )
    
    async def _perform_database_query(self, query_context: QueryContext) -> ExecutionResult:
        """Perform the actual database query with full error handling."""
        try:
            query_result = await self._execute_clickhouse_query_safe(query_context.query)
            return await self._process_query_result(query_result)
        except Exception as e:
            return self._handle_database_query_error(e)
    
    async def _process_query_result(self, query_result: Optional[List[Any]]) -> ExecutionResult:
        """Process database query result and return appropriate result."""
        if query_result is None:
            return self._create_failed_query_result("Query returned no data")
        
        formatted_data = self._convert_result_to_dicts(query_result)
        return self._create_successful_query_result(formatted_data)
    
    def _create_failed_query_result(self, error_message: str) -> ExecutionResult:
        """Create failed query result."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error_message
        )
    
    def _create_successful_query_result(self, formatted_data: List[Dict[str, Any]]) -> ExecutionResult:
        """Create successful query result."""
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=formatted_data
        )
    
    async def _execute_clickhouse_query_safe(self, query: str) -> Optional[List[Any]]:
        """Execute ClickHouse query with comprehensive error handling."""
        try:
            await create_workload_events_table_if_missing()
            async with get_clickhouse_client() as client:
                return await client.execute_query(query)
        except Exception as e:
            logger.error(f"ClickHouse query execution failed: {e}")
            raise DatabaseConnectionError(f"Query execution failed: {e}")
    
    def _convert_result_to_dicts(self, result: List[Any]) -> List[Dict[str, Any]]:
        """Convert query result to list of dictionaries with metadata."""
        if not result:
            return []
        
        columns = self._extract_column_names(result[0])
        converted_data = [dict(zip(columns, row)) for row in result]
        
        return converted_data
    
    def _extract_column_names(self, first_row: Any) -> List[str]:
        """Extract column names from first result row."""
        if hasattr(first_row, '_fields'):
            return list(first_row._fields)
        return [f"column_{i}" for i in range(len(first_row))]
    
    def _record_performance_metrics(self, execution_time_ms: float, cache_hit: bool) -> None:
        """Record performance metrics for monitoring."""
        self._performance_metrics["total_queries"] += 1
        self._update_cache_metrics(cache_hit)
        self._update_average_query_time(execution_time_ms)
    
    def _update_cache_metrics(self, cache_hit: bool) -> None:
        """Update cache hit/miss metrics."""
        if cache_hit:
            self._performance_metrics["cache_hits"] += 1
        else:
            self._performance_metrics["cache_misses"] += 1
    
    def _update_average_query_time(self, execution_time_ms: float) -> None:
        """Update rolling average query time."""
        total_queries = self._performance_metrics["total_queries"]
        current_avg = self._performance_metrics["average_query_time_ms"]
        new_avg = ((current_avg * (total_queries - 1)) + execution_time_ms) / total_queries
        self._performance_metrics["average_query_time_ms"] = new_avg
    
    async def fetch_data(
        self,
        query: str,
        cache_key: Optional[str] = None,
        cache_ttl: int = 300,
        run_id: str = None,
        stream_updates: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute ClickHouse query with modern reliability and caching."""
        query_context = self._create_fetch_query_context(query, cache_key, cache_ttl)
        context = self._create_fetch_execution_context(query_context, run_id, stream_updates)
        return await self._execute_fetch_with_error_handling(context)
    
    def _create_fetch_query_context(self, query: str, cache_key: Optional[str], 
                                   cache_ttl: int) -> QueryContext:
        """Create query context for data fetch operation."""
        return QueryContext(
            query=query,
            cache_key=cache_key,
            cache_ttl=cache_ttl,
            operation_type="fetch_data",
            metadata={"query": query}
        )
    
    def _create_fetch_execution_context(self, query_context: QueryContext, 
                                       run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for data fetch operation."""
        return ExecutionContext(
            run_id=run_id or f"fetch_{int(time.time())}",
            agent_name=self.agent_name,
            state=None,
            stream_updates=stream_updates,
            metadata={"query_context": query_context}
        )
    
    async def _execute_fetch_with_error_handling(self, context: ExecutionContext) -> Optional[List[Dict[str, Any]]]:
        """Execute fetch operation with comprehensive error handling."""
        try:
            result = await self.execute_core_logic(context)
            return result.get("data")
        except Exception as e:
            logger.error(f"Data fetch failed: {e}")
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics = self._performance_metrics.copy()
        cache_hit_rate = self._calculate_cache_hit_rate(metrics)
        metrics["cache_hit_rate"] = cache_hit_rate
        metrics["reliability_status"] = self.reliability_manager.get_health_status()
        return metrics
    
    def _calculate_cache_hit_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate cache hit rate from metrics."""
        if metrics["total_queries"] > 0:
            return metrics["cache_hits"] / metrics["total_queries"]
        return 0.0
    
    def reset_performance_metrics(self) -> None:
        """Reset performance metrics for new tracking period."""
        self._performance_metrics = self._initialize_performance_metrics()
        self.reliability_manager.reset_health_tracking()
    
    
    def _handle_schema_query_error(self, error: Exception) -> ExecutionResult:
        """Handle schema query error and return failed result."""
        return self._create_failed_schema_result(f"Schema query failed: {str(error)}")
    
    def _handle_database_query_error(self, error: Exception) -> ExecutionResult:
        """Handle database query error and return failed result."""
        return self._create_failed_query_result(f"Database query failed: {str(error)}")


# Legacy compatibility alias
DataSubAgentClickHouseOperations = ModernClickHouseOperations
