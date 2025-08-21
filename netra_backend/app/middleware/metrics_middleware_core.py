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

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.metrics.agent_metrics_compact import AgentMetricsCollector
from netra_backend.app.services.metrics.agent_metrics_models import FailureType
from netra_backend.app.middleware.metrics_helpers import (
    AgentNameExtractor, OperationTypeDetector, FailureClassifier,
    PerformanceUtils, ErrorHandler, OperationMetadataBuilder, TimeoutHandler
)

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
        name_from_self = AgentNameExtractor.extract_from_self_attribute(args)
        if name_from_self:
            return name_from_self
        return self._extract_agent_name_fallback(func, args, kwargs)
    
    def _extract_agent_name_fallback(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Extract agent name from alternative sources."""
        name_from_class = AgentNameExtractor.extract_from_class_name(args)
        if name_from_class:
            return name_from_class
        return self._extract_from_kwargs_or_function(func, kwargs)
    
    def _extract_from_kwargs_or_function(self, func: Callable, kwargs: dict) -> str:
        """Extract name from kwargs or function module."""
        name_from_kwargs = AgentNameExtractor.extract_from_kwargs(
            kwargs, AgentNameExtractor.get_default_kwargs_keys()
        )
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
        elif OperationTypeDetector.detect_notification_type(func_name):
            return "notification"
        return "general"
    
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
        return await self._execute_tracked_context_operation(
            agent_name, operation_type, operation_func, include_performance, timeout_seconds, args, kwargs
        )
    
    async def _execute_tracked_context_operation(
        self, agent_name: str, operation_type: str, operation_func: Callable, 
        include_performance: bool, timeout_seconds: Optional[float], args: tuple, kwargs: dict
    ) -> Any:
        """Execute operation with full context tracking."""
        operation_id, start_time, memory_before = await self._prepare_context_tracking(
            agent_name, operation_type, operation_func, include_performance
        )
        try:
            result = await self._execute_context_function(operation_func, timeout_seconds, args, kwargs)
            await self._record_context_success(operation_id, result, start_time, memory_before, include_performance)
            return result
        except asyncio.TimeoutError as e:
            await self._handle_timeout(operation_id, timeout_seconds or 0, e)
            raise
        except Exception as e:
            await self._handle_operation_error(operation_id, e, operation_func, args, kwargs)
            raise
    
    async def _prepare_context_tracking(
        self, agent_name: str, operation_type: str, operation_func: Callable, include_performance: bool
    ) -> tuple[str, float, float]:
        """Prepare context tracking with metadata."""
        operation_id = await self._start_context_operation(agent_name, operation_type, operation_func)
        start_time, memory_before = self._initialize_context_performance_tracking(include_performance)
        return operation_id, start_time, memory_before
    
    async def _start_context_operation(self, agent_name: str, operation_type: str, operation_func: Callable) -> str:
        """Start context operation with metadata."""
        metadata = OperationMetadataBuilder.create_start_metadata(operation_func)
        return await self.metrics_collector.start_operation(
            agent_name=agent_name, operation_type=operation_type, metadata=metadata
        )
    
    def _initialize_context_performance_tracking(self, include_performance: bool) -> tuple[float, float]:
        """Initialize context performance tracking variables."""
        start_time = time.time()
        memory_before = self._get_memory_usage() if include_performance else 0.0
        return start_time, memory_before
    
    async def _execute_context_function(
        self, operation_func: Callable, timeout_seconds: Optional[float], args: tuple, kwargs: dict
    ) -> Any:
        """Execute function with optional timeout."""
        if timeout_seconds:
            return await TimeoutHandler.execute_with_timeout(operation_func, timeout_seconds, *args, **kwargs)
        else:
            return await TimeoutHandler.execute_without_timeout(operation_func, *args, **kwargs)
    
    async def _record_context_success(
        self, operation_id: str, result: Any, start_time: float, memory_before: float, include_performance: bool
    ) -> None:
        """Record successful context operation."""
        execution_time_ms = PerformanceUtils.calculate_execution_time_ms(start_time)
        performance_metrics = self._collect_context_performance_metrics(memory_before, include_performance)
        metadata = OperationMetadataBuilder.create_success_metadata(execution_time_ms, result)
        await self._finalize_context_success(operation_id, performance_metrics, metadata)
    
    def _collect_context_performance_metrics(self, memory_before: float, include_performance: bool) -> dict:
        """Collect context performance metrics for operation."""
        memory_after = self._get_memory_usage() if include_performance else 0.0
        memory_delta = PerformanceUtils.calculate_memory_delta(memory_before, memory_after)
        cpu_usage = self._get_cpu_usage() if include_performance else 0.0
        return {'memory_usage_mb': memory_delta, 'cpu_usage_percent': cpu_usage}
    
    async def _finalize_context_success(self, operation_id: str, performance_metrics: dict, metadata: dict) -> None:
        """Finalize successful context operation recording."""
        await self.metrics_collector.end_operation(
            operation_id=operation_id, success=True, 
            memory_usage_mb=performance_metrics['memory_usage_mb'],
            cpu_usage_percent=performance_metrics['cpu_usage_percent'], metadata=metadata
        )