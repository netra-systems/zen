"""Reliability Manager Implementation for Agent Health Monitoring

Comprehensive reliability patterns combining:
- Circuit breaker protection
- Retry logic coordination
- Health tracking and monitoring
- Execution success/failure recording

Business Value: Coordinates all reliability patterns for maximum system uptime.
"""

import time
from typing import Dict, Any, Callable, Awaitable

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.core.circuit_breaker import CircuitConfig
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig, CircuitBreaker, CircuitBreakerOpenException, CircuitBreakerState
from netra_backend.app.agents.base.retry_manager import RetryManager

logger = central_logger.get_logger(__name__)


class ReliabilityManager:
    """Manages comprehensive reliability patterns.
    
    Combines circuit breaker, retry logic, and health monitoring
    for robust agent execution.
    """
    
    def __init__(self, circuit_breaker_config: CircuitBreakerConfig,
                 retry_config: RetryConfig):
        legacy_config = self._convert_to_legacy_config(circuit_breaker_config)
        self.circuit_breaker = CircuitBreaker(legacy_config)
        self.retry_manager = RetryManager(retry_config)
        self._health_stats = self._initialize_health_stats()
    
    def _convert_to_legacy_config(self, config: CircuitBreakerConfig) -> CircuitBreakerConfig:
        """Convert CircuitConfig to legacy format for compatibility."""
        if isinstance(config, CircuitConfig):
            return CircuitBreakerConfig(
                name=config.name,
                failure_threshold=config.failure_threshold,
                recovery_timeout=int(config.recovery_timeout)
            )
        return config
    
    def _initialize_health_stats(self) -> Dict[str, int]:
        """Initialize health tracking statistics."""
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "circuit_breaker_trips": 0,
            "retry_attempts": 0
        }
        
    async def execute_with_reliability(self, context: ExecutionContext,
                                     execute_func: Callable[[], Awaitable[ExecutionResult]]
                                     ) -> ExecutionResult:
        """Execute with full reliability patterns."""
        self._health_stats["total_executions"] += 1
        
        try:
            return await self._execute_and_record_success(context, execute_func)
        except Exception as e:
            return await self._handle_execution_failure(context, e)
    
    async def _execute_and_record_success(self, context: ExecutionContext,
                                        execute_func: Callable[[], Awaitable[ExecutionResult]]
                                        ) -> ExecutionResult:
        """Execute with patterns and record success."""
        result = await self._execute_with_patterns(context, execute_func)
        self._record_execution_success(result)
        return result
    
    async def _handle_execution_failure(self, context: ExecutionContext,
                                      error: Exception) -> ExecutionResult:
        """Handle execution failure and create error result."""
        self._record_execution_failure()
        return await self._create_reliability_error_result(context, error)
    
    async def _execute_with_patterns(self, context: ExecutionContext,
                                   execute_func: Callable[[], Awaitable[ExecutionResult]]
                                   ) -> ExecutionResult:
        """Execute with circuit breaker and retry patterns."""
        circuit_protected_func = self._create_circuit_protected_func(execute_func)
        return await self._execute_with_retry_protection(circuit_protected_func, context)
    
    def _create_circuit_protected_func(self, execute_func: Callable[[], Awaitable[ExecutionResult]]
                                      ) -> Callable[[], Awaitable[ExecutionResult]]:
        """Create circuit breaker protected function."""
        return lambda: self.circuit_breaker.execute(execute_func)
    
    async def _execute_with_retry_protection(self, protected_func: Callable[[], Awaitable[ExecutionResult]],
                                           context: ExecutionContext) -> ExecutionResult:
        """Execute function with retry protection."""
        return await self.retry_manager.execute_with_retry(protected_func, context)
    
    async def _create_reliability_error_result(self, context: ExecutionContext,
                                             error: Exception) -> ExecutionResult:
        """Create error result for reliability failures."""
        execution_time = self._calculate_execution_time(context)
        error_type = self._determine_error_type(error)
        metrics = self._build_error_metrics(error_type)
        error_message = self._create_error_message(error_type, error)
        
        return self._build_execution_result(error_message, execution_time, context, metrics)
    
    def _create_error_message(self, error_type: str, error: Exception) -> str:
        """Create formatted error message."""
        return f"Reliability failure ({error_type}): {str(error)}"
    
    def _build_execution_result(self, error_message: str, execution_time: float,
                               context: ExecutionContext, metrics: Dict[str, Any]) -> ExecutionResult:
        """Build execution result with error details."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error_message,
            execution_time_ms=execution_time,
            retry_count=context.retry_count,
            metrics=metrics
        )
    
    def _determine_error_type(self, error: Exception) -> str:
        """Determine error type based on exception."""
        return "circuit_breaker" if isinstance(error, CircuitBreakerOpenException) else "retry_exhausted"
    
    def _build_error_metrics(self, error_type: str) -> Dict[str, Any]:
        """Build metrics for error result."""
        return {
            "reliability_failure": error_type,
            "circuit_breaker_state": self.circuit_breaker.state.value
        }
    
    def _record_execution_success(self, result: ExecutionResult) -> None:
        """Record successful execution for health tracking."""
        if result.success:
            self._health_stats["successful_executions"] += 1
        else:
            self._health_stats["failed_executions"] += 1
        
        if result.retry_count > 0:
            self._health_stats["retry_attempts"] += result.retry_count
    
    def _record_execution_failure(self) -> None:
        """Record execution failure for health tracking."""
        self._health_stats["failed_executions"] += 1
        
        if self.circuit_breaker.state == CircuitBreakerState.OPEN:
            self._health_stats["circuit_breaker_trips"] += 1
    
    def _calculate_execution_time(self, context: ExecutionContext) -> float:
        """Calculate execution time in milliseconds."""
        if not context.start_time:
            return 0.0
        return (time.time() - context.start_time) * 1000
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive reliability health status."""
        success_rate = self._calculate_success_rate()
        health_status = self._determine_health_status(success_rate)
        retry_config_data = self._get_retry_config_data()
        
        return self._build_health_status_dict(health_status, success_rate, retry_config_data)
    
    def _build_health_status_dict(self, health_status: str, success_rate: float,
                                 retry_config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build health status dictionary."""
        return {
            "overall_health": health_status,
            "success_rate": success_rate,
            "circuit_breaker": self.circuit_breaker.get_status(),
            "statistics": self._health_stats.copy(),
            "retry_config": retry_config_data
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate current success rate."""
        total = self._health_stats["total_executions"]
        if total <= 0:
            return 0.0
        return self._health_stats["successful_executions"] / total
    
    def _determine_health_status(self, success_rate: float) -> str:
        """Determine overall health status based on success rate."""
        return "healthy" if success_rate > 0.95 else "degraded"
    
    def _get_retry_config_data(self) -> Dict[str, Any]:
        """Get retry configuration data for status."""
        return {
            "max_retries": self.retry_manager.config.max_retries,
            "base_delay": self.retry_manager.config.base_delay,
            "max_delay": self.retry_manager.config.max_delay
        }
    
    def reset_health_tracking(self) -> None:
        """Reset health tracking statistics."""
        self._health_stats = self._initialize_health_stats()
        self.circuit_breaker.reset()