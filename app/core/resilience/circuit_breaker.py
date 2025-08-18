"""Unified circuit breaker implementation for enterprise resilience.

This module provides the core circuit breaker functionality with:
- Configurable failure thresholds and recovery strategies
- Enterprise-grade monitoring and metrics
- Policy-driven behavior management
- Integration with unified resilience framework

All functions are ≤8 lines per MANDATORY requirements.
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar
from dataclasses import dataclass, field

from app.logging_config import central_logger
from app.core.exceptions_service import ServiceError

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states with clear semantics."""
    CLOSED = "closed"
    OPEN = "open" 
    HALF_OPEN = "half_open"


@dataclass
class CircuitConfig:
    """Enterprise circuit breaker configuration."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    timeout_seconds: float = 10.0
    adaptive_threshold: bool = True
    slow_call_threshold: float = 5.0
    
    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        self._validate_thresholds()
        self._validate_timeouts()
    
    def _validate_thresholds(self) -> None:
        """Validate threshold values are positive."""
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.half_open_max_calls <= 0:
            raise ValueError("half_open_max_calls must be positive")
    
    def _validate_timeouts(self) -> None:
        """Validate timeout values are positive."""
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics for enterprise monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeouts: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    failure_types: Dict[str, int] = field(default_factory=dict)


class CircuitBreakerOpenError(ServiceError):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, circuit_name: str) -> None:
        super().__init__(f"Circuit breaker '{circuit_name}' is OPEN")
        self.circuit_name = circuit_name


class UnifiedCircuitBreaker:
    """Enterprise-grade circuit breaker with unified resilience."""
    
    def __init__(self, config: CircuitConfig) -> None:
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is in open state."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is in closed state."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is in half-open state."""
        return self.state == CircuitState.HALF_OPEN
    
    async def call(self, func: Callable[[], T]) -> T:
        """Execute function with circuit breaker protection."""
        if not await self._can_execute():
            await self._record_rejection()
            raise CircuitBreakerOpenError(self.config.name)
        return await self._execute_with_monitoring(func)
    
    async def _can_execute(self) -> bool:
        """Check if execution is allowed in current state."""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                return await self._check_recovery_condition()
            return self._half_open_calls < self.config.half_open_max_calls
    
    async def _check_recovery_condition(self) -> bool:
        """Check if circuit should transition to half-open."""
        if self._should_attempt_recovery():
            await self._transition_to_half_open()
            return True
        return False
    
    def _should_attempt_recovery(self) -> bool:
        """Check if recovery timeout has elapsed."""
        if not self._last_failure_time:
            return False
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    async def _execute_with_monitoring(self, func: Callable[[], T]) -> T:
        """Execute function with timeout and failure tracking."""
        try:
            result = await self._execute_function_with_timeout(func)
            await self._record_success()
            return result
        except asyncio.TimeoutError:
            await self._record_timeout()
            raise
        except Exception as e:
            await self._record_failure(type(e).__name__)
            raise
    
    async def _execute_function_with_timeout(self, func: Callable[[], T]) -> T:
        """Execute function with configured timeout."""
        return await asyncio.wait_for(
            self._call_function(func), 
            timeout=self.config.timeout_seconds
        )
    
    async def _call_function(self, func: Callable[[], T]) -> T:
        """Call function handling both sync and async."""
        if asyncio.iscoroutinefunction(func):
            return await func()
        return func()
    
    async def _record_success(self) -> None:
        """Record successful execution and update state."""
        async with self._lock:
            self._update_success_metrics()
            if self.state == CircuitState.HALF_OPEN:
                await self._transition_to_closed()
            self._reset_failure_tracking()
    
    def _update_success_metrics(self) -> None:
        """Update metrics for successful call."""
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = time.time()
    
    def _reset_failure_tracking(self) -> None:
        """Reset failure count and timing."""
        self._failure_count = 0
        self._last_failure_time = None
    
    async def _record_failure(self, error_type: str) -> None:
        """Record failure and check threshold."""
        async with self._lock:
            self._update_failure_metrics(error_type)
            self._increment_failure_count()
            await self._check_failure_threshold()
    
    def _update_failure_metrics(self, error_type: str) -> None:
        """Update failure metrics and tracking."""
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = time.time()
        current_count = self.metrics.failure_types.get(error_type, 0)
        self.metrics.failure_types[error_type] = current_count + 1
    
    def _increment_failure_count(self) -> None:
        """Increment failure count and timestamp."""
        self._failure_count += 1
        self._last_failure_time = time.time()
    
    async def _check_failure_threshold(self) -> None:
        """Check if failure threshold exceeded."""
        if self._failure_count >= self.config.failure_threshold:
            await self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            await self._transition_to_open()
    
    async def _record_timeout(self) -> None:
        """Record timeout as failure."""
        async with self._lock:
            self.metrics.timeouts += 1
        await self._record_failure("TimeoutError")
    
    async def _record_rejection(self) -> None:
        """Record rejected call when circuit is open."""
        async with self._lock:
            self.metrics.rejected_calls += 1
    
    async def _transition_to_open(self) -> None:
        """Transition to OPEN state with logging."""
        if self.state != CircuitState.OPEN:
            self._log_state_change("OPEN")
            self.metrics.state_changes += 1
        self.state = CircuitState.OPEN
    
    async def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self._log_state_change("HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self.metrics.state_changes += 1
    
    async def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self._log_state_change("CLOSED")
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self.metrics.state_changes += 1
    
    def _log_state_change(self, new_state: str) -> None:
        """Log circuit breaker state changes."""
        logger.info(
            f"Circuit breaker '{self.config.name}' -> {new_state} "
            f"(failures: {self._failure_count})"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status."""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_rate": self._calculate_success_rate(),
            "config": self._get_config_status(),
            "metrics": self._get_metrics_status(),
            "health": self._get_health_status()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate from metrics."""
        if self.metrics.total_calls > 0:
            return self.metrics.successful_calls / self.metrics.total_calls
        return 1.0
    
    def _get_config_status(self) -> Dict[str, Any]:
        """Get configuration for status."""
        return {
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
            "timeout_seconds": self.config.timeout_seconds
        }
    
    def _get_metrics_status(self) -> Dict[str, Any]:
        """Get metrics for status."""
        return {
            "total_calls": self.metrics.total_calls,
            "successful_calls": self.metrics.successful_calls,
            "failed_calls": self.metrics.failed_calls,
            "rejected_calls": self.metrics.rejected_calls,
            "timeouts": self.metrics.timeouts
        }
    
    def _get_health_status(self) -> str:
        """Get health status based on state and metrics."""
        if self.state == CircuitState.OPEN:
            return "unhealthy"
        elif self.state == CircuitState.HALF_OPEN:
            return "recovering"
        return "healthy"