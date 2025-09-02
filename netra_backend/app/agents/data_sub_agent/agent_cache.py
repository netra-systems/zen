"""Modern Cache Management for DataSubAgent.

Modernized with standardized execution patterns:
- Reliable execution workflows
- Integrated reliability management
- Comprehensive error handling
- Performance monitoring
- Circuit breaker protection

Business Value: Cache optimization critical for data performance - HIGH revenue impact
BVJ: Growth & Enterprise | Data Performance | +15% performance fee capture
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
    WebSocketManagerProtocol,
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.shared_types import RetryConfig


@dataclass
class CacheMetrics:
    """Cache operation metrics tracking."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    average_response_time_ms: float = 0.0
    
    def record_hit(self, response_time_ms: float) -> None:
        """Record cache hit with timing."""
        self.hits += 1
        self.total_requests += 1
        self._update_average_time(response_time_ms)
        
    def record_miss(self, response_time_ms: float) -> None:
        """Record cache miss with timing."""
        self.misses += 1
        self.total_requests += 1
        self._update_average_time(response_time_ms)
        
    def _update_average_time(self, response_time_ms: float) -> None:
        """Update average response time."""
        if self.total_requests > 0:
            prev_avg = self.average_response_time_ms * (self.total_requests - 1)
            self.average_response_time_ms = (prev_avg + response_time_ms) / self.total_requests


@runtime_checkable
class CacheStorageProtocol(Protocol):
    """Protocol for cache storage interface."""
    
    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get table schema from storage."""
        ...


class DataSubAgentCacheManager:
    """Modern cache manager with execution patterns.
    
    Provides reliable caching with monitoring and error handling.
    """
    
    def __init__(self, agent, websocket_manager: Optional[WebSocketManagerProtocol] = None):
        self.agent_name = "DataSubAgentCacheManager"
        self.websocket_manager = websocket_manager
        self.agent = agent
        self.metrics = CacheMetrics()
        self._init_modern_components()
        self._ensure_cache_initialized()
        
    def _init_modern_components(self) -> None:
        """Initialize modern cache components."""
        self._init_reliability_manager()
        self._init_monitoring()
        self._init_error_handler()
        
    def _init_reliability_manager(self) -> None:
        """Initialize reliability manager with cache-optimized settings."""
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        
    def _create_circuit_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration for cache operations."""
        return CircuitBreakerConfig(
            name="DataAgentCache",
            failure_threshold=3,
            recovery_timeout=15
        )
        
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration for cache operations."""
        return RetryConfig(
            max_retries=2,
            base_delay=0.5,
            max_delay=2.0
        )
        
    def _init_monitoring(self) -> None:
        """Initialize execution monitoring."""
        self.execution_monitor = ExecutionMonitor(max_history_size=500)
        
    def _init_error_handler(self) -> None:
        """Initialize error handling."""
        self.error_handler = ExecutionErrorHandler
        
    def _ensure_cache_initialized(self) -> None:
        """Initialize cache dictionaries if they don't exist."""
        if not hasattr(self.agent, '_schema_cache'):
            self.agent._schema_cache: Dict[str, Dict[str, Any]] = {}
            self.agent._schema_cache_timestamps: Dict[str, float] = {}
    
    async def get_cached_schema(self, table_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached schema with modern reliability patterns."""
        context = self._create_cache_context(table_name, "get_schema")
        
        try:
            return await self.reliability_manager.execute_with_reliability(
                context, lambda: self._get_schema_with_monitoring(table_name, force_refresh, context)
            )
        except Exception as e:
            return await self._handle_cache_error(context, e, table_name)
            
    async def _get_schema_with_monitoring(self, table_name: str, force_refresh: bool, 
                                        context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """Get schema with performance monitoring."""
        start_time = time.time()
        self.execution_monitor.start_execution(context)
        
        try:
            result = await self._get_schema_internal(table_name, force_refresh)
            self._complete_monitored_execution(context, result, start_time, table_name)
            return result
        except Exception as e:
            self.execution_monitor.record_error(context, e)
            raise
            
    def _complete_monitored_execution(self, context: ExecutionContext, result: Any, 
                                    start_time: float, table_name: str) -> None:
        """Complete monitored execution with metrics."""
        response_time_ms = (time.time() - start_time) * 1000
        self._record_cache_metrics(result is not None, response_time_ms)
        success_result = self._create_success_result({"table_name": table_name})
        self.execution_monitor.complete_execution(context, success_result)
            
    async def _get_schema_internal(self, table_name: str, force_refresh: bool) -> Optional[Dict[str, Any]]:
        """Internal schema retrieval with cache logic."""
        self._ensure_cache_initialized()
        current_time = time.time()
        if not force_refresh and self._is_cache_valid(table_name, current_time):
            return self.agent._schema_cache[table_name]
        return await self._fetch_and_cache_schema(table_name, current_time)
        
    def _create_cache_context(self, table_name: str, operation: str) -> ExecutionContext:
        """Create execution context for cache operation."""
        return ExecutionContext(
            run_id=f"cache_{operation}_{int(time.time())}",
            agent_name=self.agent_name,
            state=None,  # Cache operations don't need state
            metadata={"table_name": table_name, "operation": operation}
        )
        
    def _record_cache_metrics(self, cache_hit: bool, response_time_ms: float) -> None:
        """Record cache performance metrics."""
        if cache_hit:
            self.metrics.record_hit(response_time_ms)
        else:
            self.metrics.record_miss(response_time_ms)
            
    def _is_cache_valid(self, table_name: str, current_time: float) -> bool:
        """Check if cache entry exists and is still valid."""
        if table_name not in self.agent._schema_cache:
            return False
        
        cache_time = self.agent._schema_cache_timestamps.get(table_name, 0)
        cache_age = current_time - cache_time
        return cache_age < 300  # 5 minutes TTL
    
    async def _fetch_and_cache_schema(self, table_name: str, current_time: float) -> Optional[Dict[str, Any]]:
        """Fetch fresh schema with error handling."""
        try:
            schema = await self._fetch_schema_from_storage(table_name)
            if schema:
                self._update_schema_cache(table_name, schema, current_time)
                await self.cleanup_old_cache_entries(current_time)
            return schema
        except Exception as e:
            logger.warning(f"Schema fetch failed for {table_name}: {e}")
            return None
            
    async def _fetch_schema_from_storage(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Fetch schema from storage with protocol support."""
        if hasattr(self.agent, 'clickhouse_ops') and self.agent.clickhouse_ops:
            return await self.agent.clickhouse_ops.get_table_schema(table_name)
        return None
    
    def _update_schema_cache(self, table_name: str, schema: Dict[str, Any], current_time: float) -> None:
        """Update schema cache with new data."""
        self.agent._schema_cache[table_name] = schema
        self.agent._schema_cache_timestamps[table_name] = current_time
    
    async def cleanup_old_cache_entries(self, current_time: float) -> None:
        """Clean up old cache entries with monitoring."""
        max_cache_age = 3600  # 1 hour
        tables_to_remove = self._identify_expired_cache_entries(current_time, max_cache_age)
        removed_count = len(tables_to_remove)
        self._remove_expired_cache_entries(tables_to_remove)
        
        if removed_count > 0:
            self.metrics.evictions += removed_count
            logger.debug(f"Evicted {removed_count} cache entries")
    
    def _identify_expired_cache_entries(self, current_time: float, max_cache_age: float) -> List[str]:
        """Identify cache entries that have expired."""
        return [
            table_name for table_name, timestamp in self.agent._schema_cache_timestamps.items()
            if current_time - timestamp > max_cache_age
        ]
    
    def _remove_expired_cache_entries(self, tables_to_remove: List[str]) -> None:
        """Remove expired entries from cache."""
        for table_name in tables_to_remove:
            self.agent._schema_cache.pop(table_name, None)
            self.agent._schema_cache_timestamps.pop(table_name, None)
    
    async def invalidate_schema_cache(self, table_name: Optional[str] = None) -> None:
        """Invalidate schema cache with modern execution patterns."""
        context = self._create_cache_context(
            table_name or "all_tables", "invalidate"
        )
        
        try:
            return await self.reliability_manager.execute_with_reliability(
                context, lambda: self._invalidate_cache_internal(table_name, context)
            )
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            
    async def _invalidate_cache_internal(self, table_name: Optional[str], 
                                       context: ExecutionContext) -> None:
        """Internal cache invalidation logic."""
        if not hasattr(self.agent, '_schema_cache'):
            return
            
        if table_name:
            self._invalidate_single_table_cache(table_name)
        else:
            self._invalidate_all_cache_entries()
    
    def _invalidate_single_table_cache(self, table_name: str) -> None:
        """Invalidate cache for a specific table."""
        self.agent._schema_cache.pop(table_name, None)
        self.agent._schema_cache_timestamps.pop(table_name, None)
    
    def _invalidate_all_cache_entries(self) -> None:
        """Clear entire schema cache."""
        self.agent._schema_cache.clear()
        self.agent._schema_cache_timestamps.clear()
    
    def cache_clear(self) -> None:
        """Clear the schema cache with metrics reset."""
        if hasattr(self.agent, '_schema_cache'):
            entries_cleared = len(self.agent._schema_cache)
            self.agent._schema_cache.clear()
            self.metrics.evictions += entries_cleared
        if hasattr(self.agent, '_schema_cache_timestamps'):
            self.agent._schema_cache_timestamps.clear()
            
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute cache operation core logic with modern execution patterns."""
        operation = context.metadata.get('operation', 'unknown')
        table_name = context.metadata.get('table_name')
        
        return await self._execute_operation(operation, table_name, context)
        
    async def _execute_operation(self, operation: str, table_name: str, 
                               context: ExecutionContext) -> Dict[str, Any]:
        """Execute specific cache operation."""
        if operation == 'get_schema' and table_name:
            result = await self._get_schema_internal(table_name, False)
            return {"schema": result, "table_name": table_name}
        elif operation == 'invalidate':
            await self._invalidate_cache_internal(table_name, context)
            return {"invalidated": table_name or "all_tables"}
        else:
            raise ValueError(f"Unsupported cache operation: {operation}")
            
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate cache operation preconditions."""
        try:
            return self._validate_cache_preconditions(context)
        except Exception as e:
            logger.error(f"Cache precondition validation failed: {e}")
            return False
            
    def _validate_cache_preconditions(self, context: ExecutionContext) -> bool:
        """Validate cache-specific preconditions."""
        if not hasattr(self.agent, '_schema_cache'):
            return False
        operation = context.metadata.get('operation')
        if operation not in ['get_schema', 'invalidate']:
            return False
        return True
        
    async def _handle_cache_error(self, context: ExecutionContext, error: Exception,
                                table_name: str) -> Optional[Dict[str, Any]]:
        """Handle cache operation errors with fallback."""
        logger.error(f"Cache operation failed for {table_name}: {error}")
        result = await self.error_handler.handle_execution_error(error, context)
        return result.result if result else None
        
    def get_cache_health_status(self) -> Dict[str, Any]:
        """Get comprehensive cache health status."""
        return {
            "cache_manager": "healthy",
            "metrics": self._get_cache_metrics(),
            "reliability_manager": self.reliability_manager.get_health_status(),
            "execution_monitor": self.execution_monitor.get_health_status(),
            "cache_size": len(getattr(self.agent, '_schema_cache', {}))
        }
        
    def _get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        return {
            "hits": self.metrics.hits,
            "misses": self.metrics.misses,
            "hit_ratio": self._calculate_hit_ratio(),
            "average_response_time_ms": self.metrics.average_response_time_ms,
            "evictions": self.metrics.evictions
        }
        
    def _calculate_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        if self.metrics.total_requests == 0:
            return 0.0
        return self.metrics.hits / self.metrics.total_requests
        
    def _create_success_result(self, result: Dict[str, Any]) -> ExecutionResult:
        """Create successful execution result."""
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=result
        )


# Backward compatibility alias - DEPRECATED  
# Use DataSubAgentCacheManager instead for clarity
CacheManager = DataSubAgentCacheManager