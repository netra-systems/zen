"""
Core metrics middleware functionality.
Handles operation tracking and error classification.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, UTC
import traceback

from app.logging_config import central_logger
from app.services.metrics.agent_metrics_compact import AgentMetricsCollector
from app.services.metrics.agent_metrics_models import FailureType

logger = central_logger.get_logger(__name__)


class MetricsMiddlewareCore:
    """Core metrics middleware functionality."""
    
    def __init__(self, metrics_collector: Optional[AgentMetricsCollector] = None):
        self.metrics_collector = metrics_collector
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
    
    async def track_operation_with_context(
        self,
        agent_name: str,
        operation_type: str,
        operation_func: Callable,
        include_performance: bool = True,
        timeout_seconds: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """Track operation with full context and error handling."""
        if not self._enabled:
            return await operation_func(*args, **kwargs)
        
        # Start operation tracking
        operation_id = await self.metrics_collector.start_operation(
            agent_name=agent_name,
            operation_type=operation_type,
            metadata={
                "function_name": operation_func.__name__,
                "module": operation_func.__module__,
                "start_time": datetime.now(UTC)
            }
        )
        
        start_time = time.time()
        memory_before = self._get_memory_usage() if include_performance else 0.0
        
        try:
            # Execute the function with timeout if specified
            if timeout_seconds:
                result = await asyncio.wait_for(
                    operation_func(*args, **kwargs), 
                    timeout=timeout_seconds
                )
            else:
                result = await operation_func(*args, **kwargs)
            
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
            await self._handle_operation_error(operation_id, e, operation_func, args, kwargs)
            raise