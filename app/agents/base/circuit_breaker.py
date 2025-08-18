"""Circuit Breaker Implementation for Agent Reliability

Circuit breaker pattern implementation with metrics tracking:
- Legacy compatibility wrapper around core circuit breaker
- Metrics and health status tracking
- Exception handling for circuit breaker states

Business Value: Prevents cascading failures, improves system resilience.
"""

import time
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime

from app.logging_config import central_logger
from app.core.circuit_breaker import CircuitBreaker as CoreCircuitBreaker, CircuitConfig
from app.core.circuit_breaker_types import CircuitState

logger = central_logger.get_logger(__name__)


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
        basic_status = self._build_basic_status(core_status)
        metrics_data = self._build_metrics_data(core_status)
        
        return {
            **basic_status,
            "metrics": metrics_data
        }
    
    def _build_basic_status(self, core_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build basic status information."""
        return {
            "name": self.legacy_config.name,
            "state": core_status["state"],
            "failure_threshold": self.legacy_config.failure_threshold,
            "recovery_timeout": self.legacy_config.recovery_timeout
        }
    
    def _build_metrics_data(self, core_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build metrics data for status."""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "consecutive_failures": self.metrics.consecutive_failures,
            "state_changes": core_status.get("metrics", {}).get("state_changes", 0),
            "last_failure": self._format_last_failure_time()
        }
    
    def _format_last_failure_time(self) -> Optional[str]:
        """Format last failure time for status display."""
        if not self.metrics.last_failure_time:
            return None
        return self.metrics.last_failure_time.isoformat()
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._reset_metrics()
        self._reset_state_tracking()
        # Reset core circuit breaker state would need to be implemented in core
    
    def _reset_metrics(self) -> None:
        """Reset circuit breaker metrics to initial state."""
        self.metrics = CircuitBreakerMetrics()
    
    def _reset_state_tracking(self) -> None:
        """Reset state change tracking."""
        self._last_state_change = time.time()


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass