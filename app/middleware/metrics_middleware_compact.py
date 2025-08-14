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
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self._enabled:
                    return await func(*args, **kwargs)
                
                # Extract agent name and operation type
                agent_name = self._extract_agent_name(func, args, kwargs)
                op_type = operation_type or self._extract_operation_type(func)
                
                return await self.track_operation_with_context(
                    agent_name, op_type, func, include_performance, 
                    timeout_seconds, *args, **kwargs
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self._enabled:
                    return func(*args, **kwargs)
                
                # For sync functions, wrap in async context
                return asyncio.run(async_wrapper(*args, **kwargs))
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
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
        batch_operation_id = await self.metrics_collector.start_operation(
            agent_name=agent_name,
            operation_type=f"batch_{operation_type}",
            metadata={
                "batch_size": batch_size,
                "start_time": datetime.now(UTC)
            }
        )
        
        start_time = time.time()
        successful_items = 0
        failed_items = 0
        
        try:
            # Execute batch operation
            result = await operation_func(*args, **kwargs)
            
            # Assume result is a list or dict with success indicators
            if isinstance(result, list):
                successful_items = len([r for r in result if r])
                failed_items = len(result) - successful_items
            elif isinstance(result, dict):
                successful_items = result.get('successful', 0)
                failed_items = result.get('failed', 0)
            else:
                successful_items = 1 if result else 0
                failed_items = 1 if not result else 0
            
            execution_time = (time.time() - start_time) * 1000
            
            await self.metrics_collector.end_operation(
                operation_id=batch_operation_id,
                success=failed_items == 0,
                metadata={
                    "batch_size": batch_size,
                    "successful_items": successful_items,
                    "failed_items": failed_items,
                    "execution_time_ms": execution_time,
                    "throughput_items_per_second": batch_size / (execution_time / 1000) if execution_time > 0 else 0
                }
            )
            
            return {
                "result": result,
                "successful_items": successful_items,
                "failed_items": failed_items,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            await self._handle_operation_error(batch_operation_id, e, operation_func, args, kwargs)
            raise


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
        self.operation_id = await self.middleware.metrics_collector.start_operation(
            agent_name=self.agent_name,
            operation_type=self.operation_type,
            metadata={"context_manager": True}
        )
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End operation tracking."""
        if self.operation_id:
            if exc_type is None:
                # Success
                await self.middleware.metrics_collector.end_operation(
                    operation_id=self.operation_id,
                    success=True
                )
            else:
                # Error occurred
                failure_type = self.middleware._classify_failure_type(exc_val, str(exc_val))
                await self.middleware.metrics_collector.end_operation(
                    operation_id=self.operation_id,
                    success=False,
                    failure_type=failure_type,
                    error_message=f"{exc_type.__name__}: {exc_val}"
                )


# Global middleware instance
agent_metrics_middleware = AgentMetricsMiddleware()

# Convenience decorators
track_operation = agent_metrics_middleware.track_agent_operation
track_with_timeout = lambda timeout: agent_metrics_middleware.track_agent_operation(timeout_seconds=timeout)
track_execution = agent_metrics_middleware.track_agent_operation(operation_type="execution")
track_validation = agent_metrics_middleware.track_agent_operation(operation_type="validation")
track_analysis = agent_metrics_middleware.track_agent_operation(operation_type="analysis")