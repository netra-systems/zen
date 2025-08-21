"""Adaptive circuit breaker core with ≤8 line functions.

Core adaptive circuit breaker implementation with health monitoring and
aggressive function decomposition. All functions ≤8 lines.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
from netra_backend.app.core.shared_health_types import HealthChecker, HealthStatus
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import CircuitBreakerState
from netra_backend.app.schemas.core_models import (
    CircuitBreakerConfig,
    HealthCheckResult,
)

logger = central_logger.get_logger(__name__)


class AdaptiveCircuitBreaker:
    """Adaptive circuit breaker with health monitoring and ≤8 line functions."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig, health_checker: Optional[HealthChecker] = None):
        """Initialize adaptive circuit breaker."""
        self.name = name
        self.config = config
        self.health_checker = health_checker
        self._initialize_state()
        self._initialize_metrics()
        self._initialize_health_monitoring()
        self._start_health_monitoring()
    
    def _initialize_state(self) -> None:
        """Initialize circuit breaker state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
    
    def _initialize_metrics(self) -> None:
        """Initialize metrics tracking."""
        self.total_calls = self.successful_calls = self.failed_calls = self.slow_requests = 0
        self.adaptive_failure_threshold = self.config.failure_threshold
        self.recent_response_times: List[float] = []
    
    def _initialize_health_monitoring(self) -> None:
        """Initialize health monitoring components."""
        self.last_health_check: Optional[HealthCheckResult] = None
        self.health_history: List[HealthCheckResult] = []
        self._health_check_task: Optional[asyncio.Task] = None
    
    def _start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        if self.health_checker and not self._health_check_task:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def call(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection."""
        self.total_calls += 1
        if not self.should_allow_request():
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
        return await self._execute_protected_operation(operation, *args, **kwargs)
    
    async def _execute_protected_operation(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with timing and error handling."""
        start_time = datetime.now()
        try:
            return await self._execute_operation_and_record_success(operation, start_time, *args, **kwargs)
        except Exception as e:
            self._handle_operation_exception(e, start_time)
            raise e

    async def _execute_operation_and_record_success(self, operation: Callable, start_time: datetime, *args, **kwargs) -> Any:
        """Execute operation and record success metrics."""
        result = await operation(*args, **kwargs)
        response_time = self._calculate_response_time(start_time)
        self._record_success(response_time)
        return result

    def _handle_operation_exception(self, error: Exception, start_time: datetime) -> None:
        """Handle operation exception and record failure."""
        response_time = self._calculate_response_time(start_time)
        self._record_failure(response_time)
    
    def _calculate_response_time(self, start_time: datetime) -> float:
        """Calculate response time in seconds."""
        return (datetime.now() - start_time).total_seconds()
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed through circuit."""
        state_handlers = self._get_state_handlers()
        handler = state_handlers.get(self.state, lambda: False)
        return handler()
    
    def _get_state_handlers(self) -> Dict:
        """Get mapping of circuit states to handler functions."""
        return {
            CircuitBreakerState.CLOSED: lambda: True,
            CircuitBreakerState.OPEN: self._handle_open_state,
            CircuitBreakerState.HALF_OPEN: lambda: True
        }
    
    def _handle_open_state(self) -> bool:
        """Handle request when circuit is open."""
        if self._should_attempt_reset():
            self._transition_to_half_open()
            return True
        return False
    
    def _record_success(self, response_time: float) -> None:
        """Record successful operation."""
        self.successful_calls += 1
        self._track_response_time(response_time)
        self._handle_success_by_state()
    
    def _track_response_time(self, response_time: float) -> None:
        """Track response time and slow requests."""
        self.recent_response_times.append(response_time)
        if len(self.recent_response_times) > 100:
            self.recent_response_times = self.recent_response_times[-50:]
        if response_time > self.config.slow_call_threshold:
            self.slow_requests += 1
    
    def _handle_success_by_state(self) -> None:
        """Handle success based on current state."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._handle_half_open_success()
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _handle_half_open_success(self) -> None:
        """Handle success in half-open state."""
        self.success_count += 1
        if self.success_count >= self.config.success_threshold:
            self._transition_to_closed()
    
    def _record_failure(self, response_time: float) -> None:
        """Record failed operation."""
        self.failed_calls += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self._adapt_threshold_if_enabled()
        self._handle_failure_by_state()
    
    def _adapt_threshold_if_enabled(self) -> None:
        """Adapt threshold if adaptive behavior is enabled."""
        if self.config.adaptive_threshold:
            self._adapt_failure_threshold()
    
    def _handle_failure_by_state(self) -> None:
        """Handle failure based on current state."""
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.adaptive_failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()
    
    def _adapt_failure_threshold(self) -> None:
        """Adapt failure threshold based on system conditions."""
        self._adapt_based_on_response_time()
        self._adapt_based_on_health_check()
    
    def _adapt_based_on_response_time(self) -> None:
        """Adapt threshold based on average response time."""
        if not self.recent_response_times:
            return
        avg_response_time = sum(self.recent_response_times) / len(self.recent_response_times)
        if avg_response_time > self.config.slow_call_threshold:
            self.adaptive_failure_threshold = max(self.config.failure_threshold - 1, 2)
        else:
            self.adaptive_failure_threshold = min(self.config.failure_threshold + 1, 10)
    
    def _adapt_based_on_health_check(self) -> None:
        """Adapt threshold based on health check results."""
        if not self.last_health_check:
            return
        if self.last_health_check.status == HealthStatus.DEGRADED:
            self.adaptive_failure_threshold = max(self.adaptive_failure_threshold - 1, 2)
        elif self.last_health_check.status == HealthStatus.HEALTHY:
            self.adaptive_failure_threshold = min(self.adaptive_failure_threshold + 1, 8)
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if not self.last_failure_time:
            return False
        timeout_reached = self._is_timeout_reached()
        health_ok = self._is_health_check_ok()
        return timeout_reached and health_ok
    
    def _is_timeout_reached(self) -> bool:
        """Check if timeout period has elapsed."""
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.timeout_seconds
    
    def _is_health_check_ok(self) -> bool:
        """Check if health check status is acceptable."""
        if not self.last_health_check:
            return True
        return self.last_health_check.status != HealthStatus.UNHEALTHY
    
    def _transition_to_closed(self) -> None:
        """Transition circuit to closed state."""
        logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
        self.state = CircuitBreakerState.CLOSED
        self._reset_state_counters()
    
    def _transition_to_open(self) -> None:
        """Transition circuit to open state."""
        logger.warning(f"Circuit breaker {self.name} transitioning to OPEN")
        self.state = CircuitBreakerState.OPEN
        self.success_count = 0
        self.last_state_change = datetime.now()
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self.last_state_change = datetime.now()
    
    def _reset_state_counters(self) -> None:
        """Reset state counters for closed state."""
        self.failure_count = self.success_count = 0
        self.last_state_change = datetime.now()
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
            except Exception as e:
                logger.error(f"Health check error for {self.name}: {e}")
    
    async def _perform_health_check(self) -> None:
        """Perform health check and update status."""
        if not self.health_checker:
            return
        health_result = await self.health_checker.check_health()
        self._store_health_result(health_result)
        self._log_health_status_changes(health_result)
    
    def _store_health_result(self, health_result: HealthCheckResult) -> None:
        """Store health result and maintain history."""
        self.last_health_check = health_result
        self.health_history.append(health_result)
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-50:]
    
    def _log_health_status_changes(self, health_result: HealthCheckResult) -> None:
        """Log significant health status changes."""
        if health_result.status == HealthStatus.UNHEALTHY:
            logger.warning(f"Health check failed for {self.name}: {health_result.details}")
        elif health_result.status == HealthStatus.HEALTHY and self.state == CircuitBreakerState.OPEN:
            logger.info(f"Health recovered for {self.name}, may attempt reset")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return self._build_metrics_dict()
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status (compatibility method)."""
        return self.get_metrics()
    
    
    def _build_metrics_dict(self) -> Dict[str, Any]:
        """Build comprehensive metrics dictionary."""
        basic_metrics = self._get_basic_metrics()
        calculated_metrics = self._get_calculated_metrics()
        return {**basic_metrics, **calculated_metrics}

    def _get_basic_metrics(self) -> Dict[str, Any]:
        """Get basic circuit breaker metrics."""
        return {
            'name': self.name, 'state': self.state.value,
            'failure_count': self.failure_count, 'success_count': self.success_count,
            'total_calls': self.total_calls, 'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls, 'slow_requests': self.slow_requests
        }

    def _get_calculated_metrics(self) -> Dict[str, Any]:
        """Get calculated metrics for circuit breaker."""
        return {
            'failure_rate': self._calculate_failure_rate(),
            'adaptive_threshold': self.adaptive_failure_threshold,
            'last_state_change': self.last_state_change.isoformat(),
            'last_health_status': self._get_last_health_status(),
            'avg_response_time': self._calculate_avg_response_time()
        }
    
    def _calculate_failure_rate(self) -> float:
        """Calculate current failure rate."""
        return self.failed_calls / max(self.total_calls, 1)
    
    def _get_last_health_status(self) -> Optional[str]:
        """Get last health status as string."""
        return self.last_health_check.status.value if self.last_health_check else None
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.recent_response_times:
            return 0.0
        return sum(self.recent_response_times) / len(self.recent_response_times)
    
    def force_open(self) -> None:
        """Force circuit breaker to open state."""
        logger.warning(f"Forcing circuit breaker {self.name} to OPEN")
        self._transition_to_open()
    
    def force_close(self) -> None:
        """Force circuit breaker to closed state."""
        logger.info(f"Forcing circuit breaker {self.name} to CLOSED")
        self._transition_to_closed()
    
    def record_success(self) -> None:
        """Public method to record success (for compatibility)."""
        self._record_success(0.0)
    
    def record_failure(self, error_type: str = "generic_error") -> None:
        """Public method to record failure (for compatibility)."""
        self._record_failure(0.0)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self._health_check_task:
            self._health_check_task.cancel()