"""
Unified circuit breaker implementation.
Enhanced implementation with proper status and metrics tracking.
"""

import time
import asyncio
from collections import deque
from enum import Enum
from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel


# Public API - explicit exports for clarity
__all__ = [
    'UnifiedCircuitBreakerState',
    'UnifiedCircuitConfig',
    'CircuitBreakerMetrics',
    'UnifiedCircuitBreaker',
    'UnifiedCircuitBreakerManager',
    'UnifiedServiceCircuitBreakers',
    'get_unified_circuit_breaker_manager',
    'unified_circuit_breaker',
    'unified_circuit_breaker_context'
]


class UnifiedCircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class UnifiedCircuitConfig(BaseModel):
    """Configuration for unified circuit breaker."""
    name: str = "default"
    failure_threshold: int = 5
    success_threshold: int = 2
    recovery_timeout: int = 60
    timeout_seconds: float = 30.0
    slow_call_threshold: float = 5.0
    adaptive_threshold: bool = False
    exponential_backoff: bool = True
    expected_exception: Optional[type] = None


class CircuitBreakerMetrics:
    """Metrics tracking for circuit breaker."""
    
    def __init__(self, failure_threshold: int):
        self.consecutive_failures = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_calls = 0
        self.slow_requests = 0
        self.adaptive_failure_threshold = failure_threshold
        self.last_failure_time = None
        self.average_response_time = 0.0


class UnifiedCircuitBreaker:
    """Enhanced unified circuit breaker implementation with metrics and status tracking."""
    
    def __init__(self, config: UnifiedCircuitConfig, health_checker=None):
        self.config = config
        self.state = UnifiedCircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_calls = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.last_state_change = time.time()
        self.opened_at = None
        self.health_checker = health_checker
        self.last_health_check = None
        self._response_times = deque(maxlen=100)
        self._health_check_task = None
        
        # Initialize metrics
        self.metrics = CircuitBreakerMetrics(config.failure_threshold)
        
        # Start health check task if health checker is provided
        if self.health_checker:
            self._start_health_check_task()
    
    def _start_health_check_task(self):
        """Start background health check task."""
        if self.health_checker:
            self._health_check_task = asyncio.create_task(self._periodic_health_check())
    
    async def _periodic_health_check(self):
        """Periodic health check task."""
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds
                if self.health_checker:
                    try:
                        self.last_health_check = await self.health_checker.check_health()
                    except Exception:
                        pass  # Ignore health check failures
        except asyncio.CancelledError:
            pass
    
    def cleanup(self):
        """Clean up resources."""
        if self._health_check_task:
            self._health_check_task.cancel()
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        can_execute = await self._can_execute()
        if not can_execute:
            from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
            raise CircuitBreakerOpenError(f"Circuit breaker {self.config.name} is OPEN")
        
        self.metrics.total_calls += 1
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Record success
            response_time = time.time() - start_time
            await self._record_success(response_time)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            await self._record_failure(response_time, str(e))
            raise
    
    async def _can_execute(self) -> bool:
        """Check if circuit can execute requests."""
        if self.state == UnifiedCircuitBreakerState.OPEN:
            if self._is_recovery_timeout_elapsed():
                await self._transition_to_half_open()
                return True
            return False
        return True
    
    def _is_recovery_timeout_elapsed(self) -> bool:
        """Check if recovery timeout has elapsed."""
        if not self.metrics.last_failure_time:
            return False
        return (time.time() - self.metrics.last_failure_time) >= self.config.recovery_timeout
    
    async def _transition_to_half_open(self):
        """Transition circuit to half-open state."""
        self.state = UnifiedCircuitBreakerState.HALF_OPEN
        self.last_state_change = time.time()
    
    async def _record_success(self, response_time: float):
        """Record successful operation."""
        self.metrics.successful_calls += 1
        self.metrics.consecutive_failures = 0
        self.last_success_time = time.time()
        self._response_times.append(response_time)
        self._update_average_response_time()
        
        if response_time > self.config.slow_call_threshold:
            self.metrics.slow_requests += 1
        
        # Close circuit if in half-open state and we have enough successes
        if self.state == UnifiedCircuitBreakerState.HALF_OPEN:
            success_count = sum(1 for _ in range(min(len(self._response_times), self.config.success_threshold)))
            if success_count >= self.config.success_threshold:
                await self._close_circuit()
    
    async def _record_failure(self, response_time: float, error: str):
        """Record failed operation."""
        self.metrics.failed_calls += 1
        self.metrics.consecutive_failures += 1
        self.metrics.last_failure_time = time.time()
        self.last_failure_time = time.time()
        self._response_times.append(response_time)
        self._update_average_response_time()
        
        # Open circuit if failure threshold reached
        if self.metrics.consecutive_failures >= self.metrics.adaptive_failure_threshold:
            await self._open_circuit()
    
    async def _open_circuit(self):
        """Open the circuit."""
        if self.state != UnifiedCircuitBreakerState.OPEN:
            self.state = UnifiedCircuitBreakerState.OPEN
            self.opened_at = time.time()
            self.last_state_change = time.time()
    
    async def _close_circuit(self):
        """Close the circuit."""
        self.state = UnifiedCircuitBreakerState.CLOSED
        self.opened_at = None
        self.last_state_change = time.time()
    
    def _update_average_response_time(self):
        """Update average response time."""
        if self._response_times:
            self.metrics.average_response_time = sum(self._response_times) / len(self._response_times)
    
    def _adapt_threshold_if_enabled(self):
        """Adapt failure threshold based on performance."""
        if not self.config.adaptive_threshold:
            return
        
        if self._response_times:
            avg_response = sum(self._response_times) / len(self._response_times)
            
            # Adapt threshold based on response time and health
            if avg_response > self.config.slow_call_threshold or (
                self.last_health_check and hasattr(self.last_health_check, 'health_score') and 
                self.last_health_check.health_score < 0.8
            ):
                # Decrease threshold when performance is poor
                self.metrics.adaptive_failure_threshold = max(1, 
                    int(self.metrics.adaptive_failure_threshold * 0.8))
            elif avg_response < (self.config.slow_call_threshold * 0.5):
                # Increase threshold when performance is good
                max_threshold = self.config.failure_threshold * 3
                new_threshold = max(self.metrics.adaptive_failure_threshold + 1,
                                  int(self.metrics.adaptive_failure_threshold * 1.2))
                self.metrics.adaptive_failure_threshold = min(max_threshold, new_threshold)
    
    async def force_open(self):
        """Force circuit to open state."""
        await self._open_circuit()
        self.metrics.last_failure_time = time.time()
    
    async def reset(self):
        """Reset circuit to closed state."""
        await self._close_circuit()
        self.metrics.consecutive_failures = 0
        self.metrics.last_failure_time = None
            
    def get_state(self) -> UnifiedCircuitBreakerState:
        """Get current state."""
        return self.state
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed circuit breaker status and metrics."""
        now = time.time()
        
        return {
            "state": self.state.value,
            "status": self.state.value,
            "name": self.config.name,
            "is_healthy": self.state == UnifiedCircuitBreakerState.CLOSED,
            "can_execute": self.state != UnifiedCircuitBreakerState.OPEN,
            "metrics": {
                "failure_count": self.metrics.consecutive_failures,
                "success_count": self.metrics.successful_calls,
                "total_calls": self.metrics.total_calls,
                "failure_threshold": self.config.failure_threshold,
                "success_rate": self.metrics.successful_calls / max(1, self.metrics.total_calls),
                "error_rate": self.metrics.failed_calls / max(1, self.metrics.total_calls),
                "last_failure_time": self.metrics.last_failure_time,
                "last_success_time": self.last_success_time,
                "opened_at": self.opened_at,
                "time_since_opened": (now - self.opened_at) if self.opened_at else None,
                "recovery_timeout": self.config.recovery_timeout
            },
            "domain": "unified"
        }
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution."""
        if self.state == UnifiedCircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if self.metrics.last_failure_time and (time.time() - self.metrics.last_failure_time) > self.config.recovery_timeout:
                return True
            return False
        return True

    def record_success(self) -> None:
        """Record a successful operation."""
        self.metrics.successful_calls += 1
        self.metrics.consecutive_failures = 0
        self.last_success_time = time.time()
        
        if self.state == UnifiedCircuitBreakerState.HALF_OPEN:
            self.state = UnifiedCircuitBreakerState.CLOSED
            self.opened_at = None

    def record_failure(self, error_type: str = "Exception") -> None:
        """Record a failed operation."""
        self.metrics.failed_calls += 1
        self.metrics.consecutive_failures += 1
        self.metrics.last_failure_time = time.time()
        
        # Check if we should open the circuit
        if self.metrics.consecutive_failures >= self.metrics.adaptive_failure_threshold:
            if self.state == UnifiedCircuitBreakerState.CLOSED:
                self.opened_at = time.time()
                self.last_state_change = time.time()
            self.state = UnifiedCircuitBreakerState.OPEN
    
    # Backward compatibility properties for tests
    @property
    def failure_threshold(self) -> int:
        """Get failure threshold (backward compatibility)."""
        return self.config.failure_threshold
        
    @failure_threshold.setter
    def failure_threshold(self, value: int) -> None:
        """Set failure threshold (backward compatibility)."""
        self.config.failure_threshold = value
        
    @property
    def timeout(self) -> float:
        """Get timeout (backward compatibility)."""
        return self.config.timeout_seconds
        
    @timeout.setter
    def timeout(self, value: float) -> None:
        """Set timeout (backward compatibility)."""
        self.config.timeout_seconds = value


class UnifiedCircuitBreakerManager:
    """Manager for unified circuit breakers."""
    
    def __init__(self):
        self.breakers: Dict[str, UnifiedCircuitBreaker] = {}
    
    def get_breaker(self, name: str) -> UnifiedCircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.breakers:
            config = UnifiedCircuitConfig()
            self.breakers[name] = UnifiedCircuitBreaker(config)
        return self.breakers[name]
    
    def create_breaker(self, name: str, config: UnifiedCircuitConfig) -> UnifiedCircuitBreaker:
        """Create a circuit breaker with specific config."""
        self.breakers[name] = UnifiedCircuitBreaker(config)
        return self.breakers[name]
    
    def create_circuit_breaker(self, name: str, config: UnifiedCircuitConfig) -> UnifiedCircuitBreaker:
        """Alias for create_breaker for backward compatibility."""
        return self.create_breaker(name, config)


class UnifiedServiceCircuitBreakers:
    """Service-level circuit breakers."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.manager = UnifiedCircuitBreakerManager()
    
    def get_breaker(self, operation: str) -> UnifiedCircuitBreaker:
        """Get circuit breaker for specific operation."""
        return self.manager.get_breaker(f"{self.service_name}_{operation}")


# Global manager instance
_unified_manager = UnifiedCircuitBreakerManager()


def get_unified_circuit_breaker_manager() -> UnifiedCircuitBreakerManager:
    """Get global unified circuit breaker manager."""
    return _unified_manager


def unified_circuit_breaker(name: str, config: Optional[UnifiedCircuitConfig] = None):
    """Decorator for applying circuit breaker protection to functions.
    
    Args:
        name: Name of the circuit breaker
        config: Optional configuration for the circuit breaker
    
    Returns:
        Decorator function that wraps the target function with circuit breaker protection
    """
    import functools
    import asyncio
    from typing import Callable
    
    def decorator(func: Callable):
        # Create or get the circuit breaker for this function
        if config:
            breaker = _unified_manager.create_breaker(name, config)
        else:
            breaker = _unified_manager.get_breaker(name)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """Wrapper for async functions."""
            # Check if circuit is open before attempting
            if breaker.state == UnifiedCircuitBreakerState.OPEN:
                # Check if we should transition to half-open
                if breaker.last_failure_time and (time.time() - breaker.last_failure_time) > breaker.config.recovery_timeout:
                    breaker.state = UnifiedCircuitBreakerState.HALF_OPEN
                else:
                    from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
                    raise CircuitBreakerOpenError(f"Circuit breaker {name} is open")
            
            breaker.total_calls += 1
            
            try:
                # Execute the wrapped function
                result = await func(*args, **kwargs)
                
                # Success - update metrics
                breaker.success_count += 1
                breaker.failure_count = 0
                breaker.last_success_time = time.time()
                
                # Close circuit if it was half-open
                if breaker.state == UnifiedCircuitBreakerState.HALF_OPEN:
                    breaker.state = UnifiedCircuitBreakerState.CLOSED
                    breaker.opened_at = None
                
                return result
                
            except Exception as e:
                # Failure - update metrics
                breaker.failure_count += 1
                breaker.last_failure_time = time.time()
                
                # Check if we should open the circuit
                if breaker.failure_count >= breaker.config.failure_threshold:
                    if breaker.state == UnifiedCircuitBreakerState.CLOSED:
                        breaker.opened_at = time.time()
                    breaker.state = UnifiedCircuitBreakerState.OPEN
                
                # Re-raise the original exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Wrapper for sync functions."""
            # Check if circuit is open before attempting
            if breaker.state == UnifiedCircuitBreakerState.OPEN:
                # Check if we should transition to half-open
                if breaker.last_failure_time and (time.time() - breaker.last_failure_time) > breaker.config.recovery_timeout:
                    breaker.state = UnifiedCircuitBreakerState.HALF_OPEN
                else:
                    from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
                    raise CircuitBreakerOpenError(f"Circuit breaker {name} is open")
            
            breaker.total_calls += 1
            
            try:
                # Execute the wrapped function
                result = func(*args, **kwargs)
                
                # Success - update metrics
                breaker.success_count += 1
                breaker.failure_count = 0
                breaker.last_success_time = time.time()
                
                # Close circuit if it was half-open
                if breaker.state == UnifiedCircuitBreakerState.HALF_OPEN:
                    breaker.state = UnifiedCircuitBreakerState.CLOSED
                    breaker.opened_at = None
                
                return result
                
            except Exception as e:
                # Failure - update metrics
                breaker.failure_count += 1
                breaker.last_failure_time = time.time()
                
                # Check if we should open the circuit
                if breaker.failure_count >= breaker.config.failure_threshold:
                    if breaker.state == UnifiedCircuitBreakerState.CLOSED:
                        breaker.opened_at = time.time()
                    breaker.state = UnifiedCircuitBreakerState.OPEN
                
                # Re-raise the original exception
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def unified_circuit_breaker_context(name: str):
    """Context manager for unified circuit breaker."""
    class UnifiedCircuitBreakerContext:
        def __init__(self, breaker_name: str):
            self.breaker = unified_circuit_breaker(breaker_name)
        
        def __enter__(self):
            return self.breaker
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                self.breaker.failure_count += 1
    
    return UnifiedCircuitBreakerContext(name)