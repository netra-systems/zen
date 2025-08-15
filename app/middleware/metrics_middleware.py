"""
Metrics middleware for automatic agent operation tracking.
Automatically tracks all agent operations and injects metrics collection.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, UTC
import inspect
import traceback

from app.logging_config import central_logger
from app.services.metrics.agent_metrics import (
    agent_metrics_collector, FailureType, AgentMetricsCollector
)

logger = central_logger.get_logger(__name__)


class AgentMetricsMiddleware:
    """Middleware for automatic agent metrics collection."""
    
    def __init__(self, metrics_collector: Optional[AgentMetricsCollector] = None):
        self.metrics_collector = metrics_collector or agent_metrics_collector
        self._operation_context = {}
        self._enabled = True
    
    def enable(self):
        """Enable metrics collection."""
        self._enabled = True
        logger.info("Agent metrics middleware enabled")
    
    def disable(self):
        """Disable metrics collection."""
        self._enabled = False
        logger.info("Agent metrics middleware disabled")
    
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
                
                # Start operation tracking
                operation_id = await self.metrics_collector.start_operation(
                    agent_name=agent_name,
                    operation_type=op_type,
                    metadata={
                        "function_name": func.__name__,
                        "module": func.__module__,
                        "start_time": datetime.now(UTC)
                    }
                )
                
                start_time = time.time()
                memory_before = self._get_memory_usage() if include_performance else 0.0
                
                try:
                    # Execute the function with timeout if specified
                    if timeout_seconds:
                        result = await asyncio.wait_for(
                            func(*args, **kwargs), 
                            timeout=timeout_seconds
                        )
                    else:
                        result = await func(*args, **kwargs)
                    
                    # Calculate performance metrics
                    execution_time = (time.time() - start_time) * 1000
                    memory_after = self._get_memory_usage() if include_performance else 0.0
                    memory_delta = max(0, memory_after - memory_before)
                    
                    # Record successful operation
                    await self.metrics_collector.end_operation(
                        operation_id=operation_id,
                        success=True,
                        memory_usage_mb=memory_delta,
                        cpu_usage_percent=self._get_cpu_usage() if include_performance else 0.0,
                        metadata={
                            "execution_time_ms": execution_time,
                            "result_type": type(result).__name__ if result else "None"
                        }
                    )
                    
                    return result
                    
                except asyncio.TimeoutError as e:
                    await self._handle_timeout(operation_id, timeout_seconds or 0, e)
                    raise
                except Exception as e:
                    await self._handle_operation_error(operation_id, e, func, args, kwargs)
                    raise
            
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
    
    def _extract_agent_name(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Extract agent name from function context."""
        # Check if this is a method call with 'self' having a name attribute
        if args and hasattr(args[0], 'name'):
            return args[0].name
        elif args and hasattr(args[0], '__class__'):
            return args[0].__class__.__name__
        
        # Check kwargs for agent_name or similar
        for key in ['agent_name', 'name', 'agent_id']:
            if key in kwargs:
                return str(kwargs[key])
        
        # Fallback to module and function name
        module_name = func.__module__.split('.')[-1] if func.__module__ else "unknown"
        return f"{module_name}_{func.__name__}"
    
    def _extract_operation_type(self, func: Callable) -> str:
        """Extract operation type from function name."""
        func_name = func.__name__
        
        # Common operation type mappings
        if any(keyword in func_name.lower() for keyword in ['execute', 'run', 'process']):
            return "execution"
        elif any(keyword in func_name.lower() for keyword in ['validate', 'check']):
            return "validation"
        elif any(keyword in func_name.lower() for keyword in ['analyze', 'compute', 'calculate']):
            return "analysis"
        elif any(keyword in func_name.lower() for keyword in ['fetch', 'get', 'retrieve']):
            return "data_retrieval"
        elif any(keyword in func_name.lower() for keyword in ['send', 'notify', 'broadcast']):
            return "notification"
        else:
            return "general"
    
    async def _handle_timeout(
        self, 
        operation_id: str, 
        timeout_seconds: float, 
        error: asyncio.TimeoutError
    ):
        """Handle operation timeout."""
        timeout_ms = timeout_seconds * 1000
        await self.metrics_collector.record_timeout(operation_id, timeout_ms)
        logger.warning(f"Operation {operation_id} timed out after {timeout_seconds}s")
    
    async def _handle_operation_error(
        self, 
        operation_id: str, 
        error: Exception, 
        func: Callable, 
        args: tuple, 
        kwargs: dict
    ):
        """Handle operation error and classify failure type."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Classify failure type
        failure_type = self._classify_failure_type(error, error_message)
        
        # Record the error
        await self.metrics_collector.end_operation(
            operation_id=operation_id,
            success=False,
            failure_type=failure_type,
            error_message=f"{error_type}: {error_message}",
            metadata={
                "error_type": error_type,
                "function_name": func.__name__,
                "traceback": traceback.format_exc()
            }
        )
        
        logger.error(f"Operation {operation_id} failed: {error_type}: {error_message}")
    
    def _classify_failure_type(self, error: Exception, error_message: str) -> FailureType:
        """Classify error into failure type."""
        error_type = type(error).__name__.lower()
        message_lower = error_message.lower()
        
        # Classification logic (8 lines max)
        if "timeout" in error_type or "timeout" in message_lower:
            return FailureType.TIMEOUT
        elif "validation" in error_type or "validation" in message_lower:
            return FailureType.VALIDATION_ERROR
        elif "websocket" in error_type or "websocket" in message_lower:
            return FailureType.WEBSOCKET_ERROR
        elif "memory" in message_lower or "resource" in message_lower:
            return FailureType.RESOURCE_ERROR
        elif "connection" in message_lower or "network" in message_lower:
            return FailureType.DEPENDENCY_ERROR
        else:
            return FailureType.EXECUTION_ERROR
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
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