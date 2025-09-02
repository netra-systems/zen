"""Circuit Breaker Implementation for Agent Reliability

Circuit breaker pattern implementation with metrics tracking:
- Legacy compatibility wrapper around core circuit breaker
- Metrics and health status tracking
- Exception handling for circuit breaker states

Business Value: Prevents cascading failures, improves system resilience.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState,
)
from netra_backend.app.core.circuit_breaker_types import CircuitState
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.reliability_types import CircuitBreakerMetrics

logger = central_logger.get_logger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior - delegates to UnifiedCircuitConfig."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3
    
    def to_unified_config(self) -> UnifiedCircuitConfig:
        """Convert to UnifiedCircuitConfig for SSOT compliance."""
        return UnifiedCircuitConfig(
            name=self.name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=float(self.recovery_timeout),
            success_threshold=self.success_threshold,
            timeout_seconds=self.timeout_seconds,
            half_open_max_calls=self.half_open_max_calls
        )


# Use canonical CircuitState enum
CircuitBreakerState = CircuitState




class CircuitBreaker:
    """Circuit breaker implementation for agent reliability - uses UnifiedCircuitBreaker.
    
    Compatibility wrapper that maintains the agent-specific interface while
    delegating to the UnifiedCircuitBreaker for SSOT compliance.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize with config, using UnifiedCircuitBreaker internally."""
        unified_config = config.to_unified_config()
        self._unified_breaker = UnifiedCircuitBreaker(unified_config)
        self.legacy_config = config
        self.metrics = CircuitBreakerMetrics()
        self._last_state_change = time.time()
        
    async def execute(self, func: Callable[[], Awaitable[Any]]) -> Any:
        """Execute function with circuit breaker protection."""
        try:
            return await self._unified_breaker.call(func)
        except Exception as e:
            # Update legacy metrics for compatibility
            self._update_legacy_metrics_on_failure()
            raise
    
    def _update_legacy_metrics_on_failure(self) -> None:
        """Update legacy metrics on failure for compatibility."""
        self.metrics.failed_calls += 1
        self.metrics.total_calls += 1
        self.metrics.last_failure_time = time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status with legacy format."""
        unified_status = self._unified_breaker.get_status()
        basic_status = self._build_basic_status(unified_status)
        metrics_data = self._build_metrics_data(unified_status)
        
        return {
            **basic_status,
            "metrics": metrics_data
        }
    
    def _build_basic_status(self, unified_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build basic status information from unified breaker."""
        return {
            "name": self.legacy_config.name,
            "state": unified_status["state"],
            "failure_threshold": self.legacy_config.failure_threshold,
            "recovery_timeout": self.legacy_config.recovery_timeout
        }
    
    def _build_metrics_data(self, unified_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build metrics data from unified breaker and legacy compatibility."""
        unified_metrics = unified_status.get("metrics", {})
        return {
            "total_calls": self.metrics.total_calls + unified_metrics.get("total_calls", 0),
            "successful_calls": self.metrics.successful_calls + unified_metrics.get("successful_calls", 0),
            "failed_calls": self.metrics.failed_calls + unified_metrics.get("failed_calls", 0),
            "circuit_breaker_opens": self.metrics.circuit_breaker_opens + unified_metrics.get("circuit_opened_count", 0),
            "state_changes": unified_metrics.get("state_changes", 0),
            "last_failure": self._format_last_failure_time()
        }
    
    def _format_last_failure_time(self) -> Optional[str]:
        """Format last failure time for status display."""
        if not self.metrics.last_failure_time:
            return None
        return self.metrics.last_failure_time.isoformat()
    
    async def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        await self._unified_breaker.reset()
        self._reset_metrics()
        self._reset_state_tracking()
    
    def _reset_metrics(self) -> None:
        """Reset circuit breaker metrics to initial state."""
        self.metrics = CircuitBreakerMetrics()
    
    def _reset_state_tracking(self) -> None:
        """Reset state change tracking."""
        self._last_state_change = time.time()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state from unified breaker."""
        return self._unified_breaker.state
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self._unified_breaker.is_open
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed."""
        return self._unified_breaker.is_closed
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open."""
        return self._unified_breaker.is_half_open
    
    def can_execute(self) -> bool:
        """Check if operation can be executed through unified breaker."""
        return self._unified_breaker.can_execute()


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Legacy compatibility alias - use CircuitBreakerOpenError from core types
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError