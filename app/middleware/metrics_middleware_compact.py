"""
Compact metrics middleware with decorators and context manager.
Main interface for agent operation tracking.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, UTC

from app.logging_config import central_logger
from app.services.metrics.agent_metrics_compact import agent_metrics_collector
from .metrics_middleware_core import MetricsMiddlewareCore

logger = central_logger.get_logger(__name__)


class AgentMetricsMiddleware(MetricsMiddlewareCore):
    """Compact metrics middleware with decorators."""
    
    def __init__(self):
        super().__init__(agent_metrics_collector)
    
    def track_agent_operation(
        self, 
        operation_type: Optional[str] = None,
        include_performance: bool = True,
        timeout_seconds: Optional[float] = None
    ):
        """Decorator to track agent operations."""
        return self._build_operation_decorator(
            operation_type, include_performance, timeout_seconds
        )
    
    def _build_operation_decorator(
        self,
        operation_type: Optional[str],
        include_performance: bool,
        timeout_seconds: Optional[float]
    ):
        """Build decorator for operation tracking."""
        def decorator(func: Callable):
            return self._create_tracking_wrapper(
                func, operation_type, include_performance, timeout_seconds
            )
        return decorator
        
    def _create_tracking_wrapper(self, func: Callable, operation_type: Optional[str], 
                               include_performance: bool, timeout_seconds: Optional[float]):
        """Create tracking wrapper for function."""
        async_wrapper = self._create_async_wrapper(
            func, operation_type, include_performance, timeout_seconds
        )
        sync_wrapper = self._create_sync_wrapper(func, async_wrapper)
        return self._select_wrapper(func, async_wrapper, sync_wrapper)
        
    def _create_async_wrapper(self, func: Callable, operation_type: Optional[str],
                            include_performance: bool, timeout_seconds: Optional[float]):
        """Create async wrapper for function."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self._enabled:
                return await func(*args, **kwargs)
            return await self._execute_wrapped_operation(
                func, operation_type, include_performance, timeout_seconds, *args, **kwargs
            )
        return async_wrapper
    
    async def _execute_wrapped_operation(
        self,
        func: Callable,
        operation_type: Optional[str],
        include_performance: bool,
        timeout_seconds: Optional[float],
        *args,
        **kwargs
    ):
        """Execute wrapped operation with tracking."""
        return await self._execute_tracked_operation(
            func, operation_type, include_performance, timeout_seconds, *args, **kwargs
        )
        
    def _create_sync_wrapper(self, func: Callable, async_wrapper):
        """Create sync wrapper for function."""
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self._enabled:
                return func(*args, **kwargs)
            return asyncio.run(async_wrapper(*args, **kwargs))
        return sync_wrapper
        
    def _select_wrapper(self, func: Callable, async_wrapper, sync_wrapper):
        """Select appropriate wrapper based on function type."""
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
    async def _execute_tracked_operation(self, func: Callable, operation_type: Optional[str],
                                       include_performance: bool, timeout_seconds: Optional[float],
                                       *args, **kwargs):
        """Execute function with tracking."""
        agent_name = self._extract_agent_name(func, args, kwargs)
        op_type = operation_type or self._extract_operation_type(func)
        return await self._track_with_extracted_context(
            agent_name, op_type, func, include_performance, timeout_seconds, *args, **kwargs
        )
    
    async def _track_with_extracted_context(
        self,
        agent_name: str,
        op_type: str,
        func: Callable,
        include_performance: bool,
        timeout_seconds: Optional[float],
        *args,
        **kwargs
    ):
        """Track operation with extracted context."""
        return await self.track_operation_with_context(
            agent_name, op_type, func, include_performance, 
            timeout_seconds, *args, **kwargs
        )
    
    async def track_batch_operation(
        self, 
        agent_name: str, 
        operation_type: str, 
        batch_size: int,
        operation_func: Callable,
        *args, 
        **kwargs
    ) -> Dict[str, Any]:
        """Track a batch operation with multiple items."""
        batch_operation_id, start_time = await self._prepare_batch_tracking(
            agent_name, operation_type, batch_size
        )
        return await self._execute_batch_tracking(
            batch_operation_id, batch_size, operation_func, start_time, *args, **kwargs
        )
    
    async def _prepare_batch_tracking(self, agent_name: str, operation_type: str, batch_size: int):
        """Prepare batch tracking initialization."""
        batch_operation_id = await self._start_batch_tracking(agent_name, operation_type, batch_size)
        start_time = time.time()
        return batch_operation_id, start_time
    
    async def _execute_batch_tracking(
        self, batch_operation_id: str, batch_size: int, operation_func: Callable, start_time: float, *args, **kwargs
    ) -> Dict[str, Any]:
        """Execute batch tracking operation."""
        try:
            result = await operation_func(*args, **kwargs)
            return await self._finalize_batch_tracking(batch_operation_id, batch_size, result, start_time)
        except Exception as e:
            await self._handle_operation_error(batch_operation_id, e, operation_func, args, kwargs)
            raise
    
    async def _start_batch_tracking(self, agent_name: str, operation_type: str, batch_size: int) -> str:
        """Start batch operation tracking."""
        return await self.metrics_collector.start_operation(
            agent_name=agent_name,
            operation_type=f"batch_{operation_type}",
            metadata={"batch_size": batch_size, "start_time": datetime.now(UTC)}
        )
    
    async def _finalize_batch_tracking(self, batch_operation_id: str, batch_size: int, result: Any, start_time: float) -> Dict[str, Any]:
        """Finalize batch operation tracking."""
        successful_items, failed_items = self._count_batch_results(result)
        execution_time = (time.time() - start_time) * 1000
        await self._record_batch_metrics(batch_operation_id, batch_size, successful_items, failed_items, execution_time)
        return self._create_batch_result(result, successful_items, failed_items, execution_time)
    
    def _count_batch_results(self, result: Any) -> tuple[int, int]:
        """Count successful and failed items from batch result."""
        if isinstance(result, list):
            successful_items = len([r for r in result if r])
            return successful_items, len(result) - successful_items
        elif isinstance(result, dict):
            return result.get('successful', 0), result.get('failed', 0)
        return (1, 0) if result else (0, 1)
    
    async def _record_batch_metrics(self, batch_operation_id: str, batch_size: int, successful_items: int, failed_items: int, execution_time: float) -> None:
        """Record batch operation metrics."""
        await self.metrics_collector.end_operation(
            operation_id=batch_operation_id, success=failed_items == 0,
            metadata=self._create_batch_metadata(batch_size, successful_items, failed_items, execution_time)
        )
    
    def _create_batch_metadata(self, batch_size: int, successful_items: int, failed_items: int, execution_time: float) -> dict:
        """Create batch operation metadata."""
        throughput = batch_size / (execution_time / 1000) if execution_time > 0 else 0
        return {
            "batch_size": batch_size, "successful_items": successful_items,
            "failed_items": failed_items, "execution_time_ms": execution_time,
            "throughput_items_per_second": throughput
        }
    
    def _create_batch_result(self, result: Any, successful_items: int, failed_items: int, execution_time: float) -> Dict[str, Any]:
        """Create batch operation result."""
        return {
            "result": result, "successful_items": successful_items,
            "failed_items": failed_items, "execution_time_ms": execution_time
        }


class AgentMetricsContextManager:
    """Context manager for tracking agent operations."""
    
    def __init__(
        self, 
        agent_name: str, 
        operation_type: str, 
        middleware: Optional[AgentMetricsMiddleware] = None
    ):
        self.agent_name = agent_name
        self.operation_type = operation_type
        self.middleware = middleware or agent_metrics_middleware
        self.operation_id: Optional[str] = None
        self.start_time = 0.0
    
    async def __aenter__(self):
        """Start operation tracking."""
        self.operation_id = await self._start_context_tracking()
        self.start_time = time.time()
        return self
    
    async def _start_context_tracking(self) -> str:
        """Start context manager tracking."""
        return await self.middleware.metrics_collector.start_operation(
            agent_name=self.agent_name,
            operation_type=self.operation_type,
            metadata={"context_manager": True}
        )
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End operation tracking."""
        if self.operation_id:
            if exc_type is None:
                await self._handle_successful_exit()
            else:
                await self._handle_error_exit(exc_type, exc_val)
    
    async def _handle_successful_exit(self) -> None:
        """Handle successful context exit."""
        await self.middleware.metrics_collector.end_operation(
            operation_id=self.operation_id, success=True
        )
    
    async def _handle_error_exit(self, exc_type, exc_val) -> None:
        """Handle error context exit."""
        failure_type = self.middleware._classify_failure_type(exc_val, str(exc_val))
        await self.middleware.metrics_collector.end_operation(
            operation_id=self.operation_id, success=False,
            failure_type=failure_type, error_message=f"{exc_type.__name__}: {exc_val}"
        )


# Global middleware instance
agent_metrics_middleware = AgentMetricsMiddleware()

# Convenience decorators
track_operation = agent_metrics_middleware.track_agent_operation
track_with_timeout = lambda timeout: agent_metrics_middleware.track_agent_operation(timeout_seconds=timeout)
track_execution = agent_metrics_middleware.track_agent_operation(operation_type="execution")
track_validation = agent_metrics_middleware.track_agent_operation(operation_type="validation")
track_analysis = agent_metrics_middleware.track_agent_operation(operation_type="analysis")