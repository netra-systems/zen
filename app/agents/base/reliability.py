"""Reliability Management System

Circuit breaker and retry patterns for agent execution:
- Circuit breaker pattern implementation
- Exponential backoff retry logic
- Rate limiting and throttling
- Health monitoring integration

Business Value: Prevents cascading failures, improves system resilience.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.logging_config import central_logger
from app.agents.base.interface import ExecutionContext, ExecutionResult, ExecutionStatus
from app.schemas.shared_types import RetryConfig
# Import CircuitBreaker from canonical location - CONSOLIDATED
from app.core.circuit_breaker import CircuitBreaker as CoreCircuitBreaker, CircuitConfig
from app.core.circuit_breaker_types import CircuitState

logger = central_logger.get_logger(__name__)


# Legacy config wrapper for backward compatibility
@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60
    
    def to_circuit_config(self) -> CircuitConfig:
        """Convert to canonical CircuitConfig."""
        return CircuitConfig(
            name=self.name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=float(self.recovery_timeout),
            timeout_seconds=float(self.recovery_timeout)
        )


# RetryConfig imported from canonical location above


# Use canonical CircuitState enum
CircuitBreakerState = CircuitState


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics tracking."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    state_changes: int = 0


class CircuitBreaker(CoreCircuitBreaker):
    """Circuit breaker implementation for agent reliability - delegates to canonical implementation.
    
    Compatibility wrapper that maintains the agent-specific interface while
    delegating to the canonical CircuitBreaker implementation.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize with legacy config interface."""
        core_config = config.to_circuit_config()
        super().__init__(core_config)
        self.legacy_config = config
        self.metrics = CircuitBreakerMetrics()
        self._last_state_change = time.time()
        
    async def execute(self, func: Callable[[], Awaitable[Any]]) -> Any:
        """Execute function with circuit breaker protection."""
        try:
            return await self.call(func)
        except Exception as e:
            # Update legacy metrics for compatibility
            self._update_legacy_metrics_on_failure()
            raise
    
    def _update_legacy_metrics_on_failure(self) -> None:
        """Update legacy metrics on failure for compatibility."""
        self.metrics.failed_requests += 1
        self.metrics.total_requests += 1
        self.metrics.consecutive_failures += 1
        self.metrics.last_failure_time = datetime.utcnow()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status with legacy format."""
        core_status = super().get_status()
        return {
            "name": self.legacy_config.name,
            "state": core_status["state"],
            "failure_threshold": self.legacy_config.failure_threshold,
            "recovery_timeout": self.legacy_config.recovery_timeout,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "consecutive_failures": self.metrics.consecutive_failures,
                "state_changes": core_status.get("metrics", {}).get("state_changes", 0),
                "last_failure": self.metrics.last_failure_time.isoformat() 
                               if self.metrics.last_failure_time else None
            }
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.metrics = CircuitBreakerMetrics()
        self._last_state_change = time.time()
        # Reset core circuit breaker state would need to be implemented in core


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class RetryManager:
    """Manages retry logic with exponential backoff.
    
    Provides intelligent retry mechanisms for transient failures
    with configurable backoff strategies.
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        
    async def execute_with_retry(self, func: Callable[[], Awaitable[Any]],
                               context: ExecutionContext) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    await self._wait_for_retry(attempt)
                    context.retry_count = attempt
                    
                return await func()
                
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e, attempt):
                    break
                    
                self._log_retry_attempt(context, attempt, e)
        
        # All retries exhausted
        raise last_exception
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if operation should be retried."""
        if attempt >= self.config.max_retries:
            return False
        
        # Check if exception is retryable
        return self._is_retryable_exception(exception)
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        # Import here to avoid circular imports
        from app.agents.base.errors import AgentExecutionError
        
        if isinstance(exception, AgentExecutionError):
            return exception.is_retryable
        
        # Common retryable exceptions
        retryable_types = (
            ConnectionError,
            TimeoutError,
            CircuitBreakerOpenException
        )
        
        return isinstance(exception, retryable_types)
    
    async def _wait_for_retry(self, attempt: int) -> None:
        """Wait for exponential backoff delay."""
        delay = min(
            self.config.base_delay * (2 ** (attempt - 1)),
            self.config.max_delay
        )
        await asyncio.sleep(delay)
    
    def _log_retry_attempt(self, context: ExecutionContext, 
                          attempt: int, exception: Exception) -> None:
        """Log retry attempt details."""
        logger.warning(
            f"Retry attempt {attempt}/{self.config.max_retries} for "
            f"{context.agent_name}: {exception}"
        )


class ReliabilityManager:
    """Manages comprehensive reliability patterns.
    
    Combines circuit breaker, retry logic, and health monitoring
    for robust agent execution.
    """
    
    def __init__(self, circuit_breaker_config: CircuitBreakerConfig,
                 retry_config: RetryConfig):
        # Convert to legacy config format for compatibility
        if isinstance(circuit_breaker_config, CircuitConfig):
            legacy_config = CircuitBreakerConfig(
                name=circuit_breaker_config.name,
                failure_threshold=circuit_breaker_config.failure_threshold,
                recovery_timeout=int(circuit_breaker_config.recovery_timeout)
            )
        else:
            legacy_config = circuit_breaker_config
        self.circuit_breaker = CircuitBreaker(legacy_config)
        self.retry_manager = RetryManager(retry_config)
        self._health_stats = {
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
            result = await self._execute_with_patterns(context, execute_func)
            self._record_execution_success(result)
            return result
        except Exception as e:
            self._record_execution_failure()
            return await self._create_reliability_error_result(context, e)
    
    async def _execute_with_patterns(self, context: ExecutionContext,
                                   execute_func: Callable[[], Awaitable[ExecutionResult]]
                                   ) -> ExecutionResult:
        """Execute with circuit breaker and retry patterns."""
        # Wrap execution function with circuit breaker
        circuit_protected_func = lambda: self.circuit_breaker.execute(execute_func)
        
        # Execute with retry logic
        return await self.retry_manager.execute_with_retry(
            circuit_protected_func, context
        )
    
    async def _create_reliability_error_result(self, context: ExecutionContext,
                                             error: Exception) -> ExecutionResult:
        """Create error result for reliability failures."""
        execution_time = self._calculate_execution_time(context)
        
        error_type = "circuit_breaker" if isinstance(error, CircuitBreakerOpenException) else "retry_exhausted"
        
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=f"Reliability failure ({error_type}): {str(error)}",
            execution_time_ms=execution_time,
            retry_count=context.retry_count,
            metrics={
                "reliability_failure": error_type,
                "circuit_breaker_state": self.circuit_breaker.state.value
            }
        )
    
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
        total_executions = self._health_stats["total_executions"]
        success_rate = 0.0
        
        if total_executions > 0:
            success_rate = self._health_stats["successful_executions"] / total_executions
        
        return {
            "overall_health": "healthy" if success_rate > 0.95 else "degraded",
            "success_rate": success_rate,
            "circuit_breaker": self.circuit_breaker.get_status(),
            "statistics": self._health_stats.copy(),
            "retry_config": {
                "max_retries": self.retry_manager.config.max_retries,
                "base_delay": self.retry_manager.config.base_delay,
                "max_delay": self.retry_manager.config.max_delay
            }
        }
    
    def reset_health_tracking(self) -> None:
        """Reset health tracking statistics."""
        self._health_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "circuit_breaker_trips": 0,
            "retry_attempts": 0
        }
        self.circuit_breaker.reset()


# Import RateLimiter from canonical location - CONSOLIDATED
from app.websocket.rate_limiter import RateLimiter as CoreRateLimiter
from app.websocket.connection import ConnectionInfo

class RateLimiter:
    """Agent-specific rate limiter wrapper around WebSocket rate limiter."""
    
    def __init__(self, max_requests: int, time_window: float):
        """Initialize with agent-specific interface."""
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests = []
        
        # Use core rate limiter with conversion
        self.core_limiter = CoreRateLimiter(
            max_requests=max_requests, 
            window_seconds=int(time_window)
        )
        
        # Create a mock connection info for agent use
        self._agent_conn_info = self._create_agent_connection_info()
        
    def _create_agent_connection_info(self) -> ConnectionInfo:
        """Create mock connection info for agent rate limiting."""
        from datetime import datetime, timezone
        conn_info = ConnectionInfo(
            connection_id="agent_rate_limiter",
            user_id="system_agent",
            client_info={},
            connection_time=datetime.now(timezone.utc)
        )
        conn_info.rate_limit_count = 0
        conn_info.rate_limit_window_start = datetime.now(timezone.utc)
        return conn_info
        
    async def acquire(self) -> bool:
        """Acquire rate limit permission."""
        # Use core rate limiter logic
        is_limited = self.core_limiter.is_rate_limited(self._agent_conn_info)
        
        # Update local tracking for compatibility
        if not is_limited:
            now = time.time()
            self._cleanup_old_requests(now)
            self._requests.append(now)
        
        return not is_limited
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove requests outside time window."""
        cutoff_time = current_time - self.time_window
        self._requests = [req_time for req_time in self._requests 
                         if req_time > cutoff_time]
    
    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status."""
        # Get status from core limiter
        core_status = self.core_limiter.get_rate_limit_info(self._agent_conn_info)
        
        # Maintain compatibility with agent interface
        now = time.time()
        self._cleanup_old_requests(now)
        
        return {
            "current_requests": len(self._requests),
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "available_capacity": core_status.get("requests_remaining", 0),
            "core_status": core_status
        }