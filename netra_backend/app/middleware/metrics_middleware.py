"""
Metrics middleware for automatic agent operation tracking.
Automatically tracks all agent operations and injects metrics collection.
"""

import asyncio
import inspect
import time
import traceback
from datetime import UTC, datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.middleware.metrics_helpers import (
    AgentNameExtractor,
    BatchResultProcessor,
    ErrorHandler,
    FailureClassifier,
    OperationMetadataBuilder,
    OperationTypeDetector,
    PerformanceUtils,
    TimeoutHandler,
    WrapperUtils,
)
from netra_backend.app.services.metrics.agent_metrics import (
    AgentMetricsCollector,
    FailureType,
    agent_metrics_collector,
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
        return self._create_tracking_decorator(
            operation_type, include_performance, timeout_seconds
        )
    
    def _create_tracking_decorator(
        self,
        operation_type: Optional[str],
        include_performance: bool,
        timeout_seconds: Optional[float]
    ):
        """Create tracking decorator with parameters."""
        def decorator(func: Callable):
            return self._create_function_wrapper(func, operation_type, include_performance, timeout_seconds)
        return decorator
    
    def _create_function_wrapper(self, func: Callable, operation_type: Optional[str], include_performance: bool, timeout_seconds: Optional[float]) -> Callable:
        """Create appropriate wrapper for function."""
        async_wrapper = self._create_async_wrapper(func, operation_type, include_performance, timeout_seconds)
        sync_wrapper = self._create_sync_wrapper(func, async_wrapper)
        return async_wrapper if WrapperUtils.is_async_function(func) else sync_wrapper
    
    def _create_async_wrapper(self, func: Callable, operation_type: Optional[str], include_performance: bool, timeout_seconds: Optional[float]) -> Callable:
        """Create async wrapper for function."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if WrapperUtils.should_skip_tracking(self._enabled):
                return await func(*args, **kwargs)
            return await self._execute_tracked_operation(func, args, kwargs, operation_type, include_performance, timeout_seconds)
        return async_wrapper
    
    def _create_sync_wrapper(self, func: Callable, async_wrapper: Callable) -> Callable:
        """Create sync wrapper for function."""
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if WrapperUtils.should_skip_tracking(self._enabled):
                return func(*args, **kwargs)
            return WrapperUtils.run_sync_as_async(async_wrapper, *args, **kwargs)
        return sync_wrapper
    
    async def _execute_tracked_operation(self, func: Callable, args: tuple, kwargs: dict, operation_type: Optional[str], include_performance: bool, timeout_seconds: Optional[float]) -> Any:
        """Execute operation with full tracking."""
        operation_id, start_time, memory_before = await self._prepare_operation_tracking(
            func, args, kwargs, operation_type, include_performance
        )
        try:
            return await self._execute_and_record_operation(
                func, timeout_seconds, args, kwargs, operation_id, start_time, memory_before, include_performance
            )
        except Exception as e:
            await self._handle_tracked_exception(operation_id, e, func, args, kwargs, timeout_seconds)
            raise
    
    async def _execute_and_record_operation(self, func: Callable, timeout_seconds: Optional[float], args: tuple, kwargs: dict, operation_id: str, start_time: float, memory_before: float, include_performance: bool) -> Any:
        """Execute function and record successful operation."""
        result = await self._execute_tracked_function(func, timeout_seconds, args, kwargs)
        await self._record_successful_operation(operation_id, result, start_time, memory_before, include_performance)
        return result
    
    async def _handle_tracked_exception(self, operation_id: str, e: Exception, func: Callable, args: tuple, kwargs: dict, timeout_seconds: Optional[float]) -> None:
        """Handle tracked operation exceptions."""
        if isinstance(e, asyncio.TimeoutError):
            await self._handle_timeout(operation_id, timeout_seconds or 0, e)
        else:
            await self._handle_operation_error(operation_id, e, func, args, kwargs)
    
    def _extract_agent_name(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Extract agent name from function context."""
        name_from_self = AgentNameExtractor.extract_from_self_attribute(args)
        if name_from_self:
            return name_from_self
        return self._extract_agent_name_fallback(func, args, kwargs)
    
    def _extract_agent_name_fallback(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Extract agent name from alternative sources."""
        name_from_class = AgentNameExtractor.extract_from_class_name(args)
        if name_from_class:
            return name_from_class
        return self._extract_from_kwargs_or_module(func, kwargs)
    
    def _extract_from_kwargs_or_module(self, func: Callable, kwargs: dict) -> str:
        """Extract from kwargs or fallback to module."""
        name_from_kwargs = AgentNameExtractor.extract_from_kwargs(kwargs, AgentNameExtractor.get_default_kwargs_keys())
        if name_from_kwargs:
            return name_from_kwargs
        return AgentNameExtractor.extract_from_function_module(func)
    
    def _extract_operation_type(self, func: Callable) -> str:
        """Extract operation type from function name."""
        func_name = func.__name__
        if self._is_execution_or_validation_type(func_name):
            return self._get_execution_or_validation_type(func_name)
        return self._get_other_operation_type(func_name)
    
    def _is_execution_or_validation_type(self, func_name: str) -> bool:
        """Check if function is execution or validation type."""
        return (OperationTypeDetector.detect_execution_type(func_name) or
                OperationTypeDetector.detect_validation_type(func_name))
    
    def _get_execution_or_validation_type(self, func_name: str) -> str:
        """Get execution or validation operation type."""
        if OperationTypeDetector.detect_execution_type(func_name):
            return "execution"
        return "validation"
    
    def _get_other_operation_type(self, func_name: str) -> str:
        """Get analysis, data retrieval, notification, or general type."""
        if OperationTypeDetector.detect_analysis_type(func_name):
            return "analysis"
        elif OperationTypeDetector.detect_data_retrieval_type(func_name):
            return "data_retrieval"
        return self._get_notification_or_general_type(func_name)
    
    def _get_notification_or_general_type(self, func_name: str) -> str:
        """Get notification or general operation type."""
        if OperationTypeDetector.detect_notification_type(func_name):
            return "notification"
        return "general"
    
    async def _prepare_operation_tracking(
        self, func: Callable, args: tuple, kwargs: dict, operation_type: Optional[str], include_performance: bool
    ) -> tuple[str, float, float]:
        """Prepare operation tracking with metadata."""
        agent_name = self._extract_agent_name(func, args, kwargs)
        op_type = operation_type or self._extract_operation_type(func)
        operation_id = await self._start_metrics_operation(agent_name, op_type, func)
        start_time, memory_before = self._initialize_performance_tracking(include_performance)
        return operation_id, start_time, memory_before
    
    async def _start_metrics_operation(self, agent_name: str, op_type: str, func: Callable) -> str:
        """Start metrics operation with metadata."""
        metadata = OperationMetadataBuilder.create_start_metadata(func)
        return await self.metrics_collector.start_operation(
            agent_name=agent_name, operation_type=op_type, metadata=metadata
        )
    
    def _initialize_performance_tracking(self, include_performance: bool) -> tuple[float, float]:
        """Initialize performance tracking variables."""
        start_time = time.time()
        memory_before = self._get_memory_usage() if include_performance else 0.0
        return start_time, memory_before
    
    async def _execute_tracked_function(
        self, func: Callable, timeout_seconds: Optional[float], args: tuple, kwargs: dict
    ) -> Any:
        """Execute function with optional timeout."""
        if timeout_seconds:
            return await TimeoutHandler.execute_with_timeout(func, timeout_seconds, *args, **kwargs)
        else:
            return await TimeoutHandler.execute_without_timeout(func, *args, **kwargs)
    
    async def _record_successful_operation(
        self, operation_id: str, result: Any, start_time: float, memory_before: float, include_performance: bool
    ) -> None:
        """Record successful operation with performance metrics."""
        execution_time_ms = PerformanceUtils.calculate_execution_time_ms(start_time)
        performance_metrics = self._collect_performance_metrics(memory_before, include_performance)
        metadata = OperationMetadataBuilder.create_success_metadata(execution_time_ms, result)
        await self._finalize_successful_operation(operation_id, performance_metrics, metadata)
    
    def _collect_performance_metrics(self, memory_before: float, include_performance: bool) -> dict:
        """Collect performance metrics for operation."""
        memory_after = self._get_memory_usage() if include_performance else 0.0
        memory_delta = PerformanceUtils.calculate_memory_delta(memory_before, memory_after)
        cpu_usage = self._get_cpu_usage() if include_performance else 0.0
        return {'memory_usage_mb': memory_delta, 'cpu_usage_percent': cpu_usage}
    
    async def _finalize_successful_operation(self, operation_id: str, performance_metrics: dict, metadata: dict) -> None:
        """Finalize successful operation recording."""
        await self.metrics_collector.end_operation(
            operation_id=operation_id, success=True, 
            memory_usage_mb=performance_metrics['memory_usage_mb'],
            cpu_usage_percent=performance_metrics['cpu_usage_percent'], metadata=metadata
        )
    
    async def _handle_timeout(
        self, 
        operation_id: str, 
        timeout_seconds: float, 
        error: asyncio.TimeoutError
    ):
        """Handle operation timeout."""
        timeout_ms = TimeoutHandler.convert_timeout_to_ms(timeout_seconds)
        await self.metrics_collector.record_timeout(operation_id, timeout_ms)
        ErrorHandler.log_timeout_error(operation_id, timeout_seconds)
    
    async def _handle_operation_error(
        self, 
        operation_id: str, 
        error: Exception, 
        func: Callable, 
        args: tuple, 
        kwargs: dict
    ):
        """Handle operation error and classify failure type."""
        error_info = self._extract_and_classify_error(error)
        metadata = ErrorHandler.create_error_metadata(error_info['type'], func)
        await self._record_operation_failure(operation_id, error_info, metadata)
        ErrorHandler.log_operation_error(operation_id, error_info['type'], error_info['message'])
    
    def _extract_and_classify_error(self, error: Exception) -> dict:
        """Extract error information and classify failure type."""
        error_type, error_message = ErrorHandler.extract_error_info(error)
        failure_type = self._classify_failure_type(error, error_message)
        formatted_message = ErrorHandler.format_error_message(error_type, error_message)
        return {'type': error_type, 'message': error_message, 'formatted': formatted_message, 'failure_type': failure_type}
    
    async def _record_operation_failure(self, operation_id: str, error_info: dict, metadata: dict) -> None:
        """Record operation failure in metrics."""
        await self.metrics_collector.end_operation(
            operation_id=operation_id, success=False, failure_type=error_info['failure_type'],
            error_message=error_info['formatted'], metadata=metadata
        )
    
    def _classify_failure_type(self, error: Exception, error_message: str) -> FailureType:
        """Classify error into failure type."""
        error_type = type(error).__name__.lower()
        message_lower = error_message.lower()
        if self._is_timeout_or_validation_error(error_type, message_lower):
            return self._get_timeout_or_validation_failure_type(error_type, message_lower)
        return self._get_other_failure_type(message_lower)
    
    def _is_timeout_or_validation_error(self, error_type: str, message_lower: str) -> bool:
        """Check if error is timeout or validation type."""
        return (FailureClassifier.is_timeout_error(error_type, message_lower) or
                FailureClassifier.is_validation_error(error_type, message_lower))
    
    def _get_timeout_or_validation_failure_type(self, error_type: str, message_lower: str) -> FailureType:
        """Get timeout or validation failure type."""
        if FailureClassifier.is_timeout_error(error_type, message_lower):
            return FailureType.TIMEOUT
        return FailureType.VALIDATION_ERROR
    
    def _get_other_failure_type(self, message_lower: str) -> FailureType:
        """Get websocket, resource, dependency, or execution failure type."""
        if FailureClassifier.is_websocket_error('', message_lower):
            return FailureType.WEBSOCKET_ERROR
        elif FailureClassifier.is_resource_error(message_lower):
            return FailureType.RESOURCE_ERROR
        elif FailureClassifier.is_dependency_error(message_lower):
            return FailureType.DEPENDENCY_ERROR
        return FailureType.EXECUTION_ERROR
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        return PerformanceUtils.get_memory_usage_mb()
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return PerformanceUtils.get_cpu_usage_percent()
    
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
        batch_operation_id, start_time = await self._initialize_batch_tracking(agent_name, operation_type, batch_size)
        try:
            result = await operation_func(*args, **kwargs)
            return await self._finalize_batch_operation(batch_operation_id, batch_size, result, start_time)
        except Exception as e:
            await self._handle_operation_error(batch_operation_id, e, operation_func, args, kwargs)
            raise
    
    async def _initialize_batch_tracking(self, agent_name: str, operation_type: str, batch_size: int) -> tuple[str, float]:
        """Initialize batch operation tracking."""
        batch_operation_id = await self._start_batch_operation(agent_name, operation_type, batch_size)
        start_time = time.time()
        return batch_operation_id, start_time
    
    async def _start_batch_operation(self, agent_name: str, operation_type: str, batch_size: int) -> str:
        """Start batch operation tracking."""
        metadata = OperationMetadataBuilder.create_batch_start_metadata(batch_size)
        return await self.metrics_collector.start_operation(
            agent_name=agent_name, operation_type=f"batch_{operation_type}", metadata=metadata
        )
    
    async def _finalize_batch_operation(
        self, operation_id: str, batch_size: int, result: Any, start_time: float
    ) -> Dict[str, Any]:
        """Finalize batch operation with metrics."""
        batch_metrics = self._calculate_batch_metrics(result, batch_size, start_time)
        metadata = self._create_batch_metadata(batch_metrics)
        await self._complete_batch_operation(operation_id, batch_metrics, metadata)
        return self._create_batch_result(result, batch_metrics)
    
    def _calculate_batch_metrics(self, result: Any, batch_size: int, start_time: float) -> dict:
        """Calculate batch operation metrics."""
        successful_items, failed_items = self._count_batch_results(result)
        execution_time_ms = PerformanceUtils.calculate_execution_time_ms(start_time)
        throughput = PerformanceUtils.calculate_throughput(batch_size, execution_time_ms)
        return {'successful': successful_items, 'failed': failed_items, 'time_ms': execution_time_ms, 'throughput': throughput, 'size': batch_size}
    
    def _create_batch_metadata(self, batch_metrics: dict) -> dict:
        """Create metadata for batch operation."""
        return BatchResultProcessor.create_batch_metadata(
            batch_metrics['size'], batch_metrics['successful'], batch_metrics['failed'], 
            batch_metrics['time_ms'], batch_metrics['throughput']
        )
    
    async def _complete_batch_operation(self, operation_id: str, batch_metrics: dict, metadata: dict) -> None:
        """Complete batch operation recording."""
        await self.metrics_collector.end_operation(
            operation_id=operation_id, success=batch_metrics['failed'] == 0, metadata=metadata
        )
    
    def _create_batch_result(self, result: Any, batch_metrics: dict) -> Dict[str, Any]:
        """Create batch operation result."""
        return BatchResultProcessor.create_batch_result(
            result, batch_metrics['successful'], batch_metrics['failed'], batch_metrics['time_ms']
        )
    
    def _count_batch_results(self, result: Any) -> tuple[int, int]:
        """Count successful and failed items from batch result."""
        if isinstance(result, list):
            return BatchResultProcessor.count_list_results(result)
        elif isinstance(result, dict):
            return BatchResultProcessor.count_dict_results(result)
        return BatchResultProcessor.count_single_result(result)


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
        self.operation_id = await self._start_operation_tracking()
        self.start_time = time.time()
        return self
    
    async def _start_operation_tracking(self) -> str:
        """Start operation tracking and return operation ID."""
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
        error_message = f"{exc_type.__name__}: {exc_val}"
        await self.middleware.metrics_collector.end_operation(
            operation_id=self.operation_id, success=False,
            failure_type=failure_type, error_message=error_message
        )


# Global middleware instance
agent_metrics_middleware = AgentMetricsMiddleware()

# Convenience decorators
track_operation = agent_metrics_middleware.track_agent_operation
track_with_timeout = lambda timeout: agent_metrics_middleware.track_agent_operation(timeout_seconds=timeout)
track_execution = agent_metrics_middleware.track_agent_operation(operation_type="execution")
track_validation = agent_metrics_middleware.track_agent_operation(operation_type="validation")
track_analysis = agent_metrics_middleware.track_agent_operation(operation_type="analysis")