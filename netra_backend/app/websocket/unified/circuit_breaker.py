"""Circuit breaker implementation for WebSocket connections.

Provides resilience patterns for WebSocket connections by preventing
cascading failures and allowing graceful recovery from network issues.

Business Value: Prevents cascading failures in WebSocket system, 
maintains service availability during degraded conditions.
"""

# Import the comprehensive circuit breaker from the service layer
try:
    from netra_backend.app.services.circuit_breaker import (
        CircuitBreaker as ServiceCircuitBreaker,
        CircuitBreakerConfig,
        ServiceCircuitBreakers
    )
    HAS_SERVICE_CIRCUIT_BREAKER = True
except ImportError:
    # Fallback if service circuit breaker is not available
    HAS_SERVICE_CIRCUIT_BREAKER = False
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CircuitBreaker:
    """WebSocket-specific circuit breaker wrapper with WebSocket optimizations."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        """Initialize circuit breaker optimized for WebSocket operations."""
        if HAS_SERVICE_CIRCUIT_BREAKER:
            # Use the comprehensive service circuit breaker
            config = CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=2,  # Faster recovery for WebSocket
                timeout=5.0,  # Quick timeout for WebSocket operations
                expected_exception_types=["ConnectionError", "WebSocketDisconnect", "TimeoutError"],
                sliding_window_size=20,  # Larger window for WebSocket patterns
                error_rate_threshold=0.6,  # Allow some errors in WebSocket context
                min_requests_threshold=5  # Require more requests before considering error rate
            )
            self._circuit_breaker = ServiceCircuitBreaker("websocket", config)
            self._use_service_circuit_breaker = True
        else:
            # Fallback to simple implementation
            self.failure_threshold = failure_threshold
            self.recovery_timeout = recovery_timeout
            self._failure_count = 0
            self.last_failure_time = 0
            self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
            self._use_service_circuit_breaker = False
    
    def can_execute(self) -> bool:
        """Check if WebSocket operation can be executed based on circuit state."""
        if self._use_service_circuit_breaker:
            try:
                return self._circuit_breaker.state.value != "open"
            except Exception as e:
                logger.warning(f"Circuit breaker check failed: {e}")
                return True  # Fail open for WebSocket operations
        else:
            # Simple implementation
            if self._state == "CLOSED":
                return True
            if self._state == "OPEN":
                return self._should_attempt_reset()
            return self._state == "HALF_OPEN"
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        import time
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self._state = "HALF_OPEN"
            return True
        return False
    
    async def execute_protected(self, func, *args, **kwargs):
        """Execute WebSocket operation with circuit breaker protection."""
        if self._use_service_circuit_breaker:
            return await self._circuit_breaker.call(func, *args, **kwargs)
        else:
            # Simple execution without protection
            return await func(*args, **kwargs)
    
    def record_success(self) -> None:
        """Record successful WebSocket operation."""
        if not self._use_service_circuit_breaker:
            self._failure_count = 0
            if self._state == "HALF_OPEN":
                self._state = "CLOSED"
    
    def record_failure(self) -> None:
        """Record failed WebSocket operation."""
        if not self._use_service_circuit_breaker:
            import time
            self._failure_count += 1
            self.last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state for compatibility."""
        if self._use_service_circuit_breaker:
            return self._circuit_breaker.state.value.upper()
        else:
            return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count for compatibility."""
        if self._use_service_circuit_breaker:
            return self._circuit_breaker.metrics.current_consecutive_failures
        else:
            return self._failure_count
    
    def get_status(self) -> dict:
        """Get comprehensive circuit breaker status."""
        if self._use_service_circuit_breaker:
            return self._circuit_breaker.get_status()
        else:
            return {
                "state": self._state,
                "failure_count": self._failure_count,
                "threshold": self.failure_threshold
            }