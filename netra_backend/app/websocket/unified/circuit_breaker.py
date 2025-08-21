"""Circuit breaker implementation for WebSocket connections.

Provides resilience patterns for WebSocket connections by preventing
cascading failures and allowing graceful recovery from network issues.
"""

import time
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for WebSocket resilience."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        """Initialize circuit breaker with thresholds."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit state."""
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            return self._should_attempt_reset()
        return self.state == "HALF_OPEN"

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.state = "HALF_OPEN"
            return True
        return False

    def record_success(self) -> None:
        """Record successful operation and reset if needed."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"

    def record_failure(self) -> None:
        """Record failed operation and open circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"