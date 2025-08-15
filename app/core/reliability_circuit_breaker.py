"""Circuit breaker pattern implementation for Netra agents.

This module provides circuit breaker functionality with state management,
metrics tracking, and automatic recovery capabilities.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from app.logging_config import central_logger
from app.core.error_codes import ErrorSeverity

logger = central_logger.get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern - optimized for responsive error handling"""
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 2
    name: str = "default"


@dataclass
class ReliabilityMetrics:
    """Metrics for reliability monitoring"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    circuit_breaker_opens: int = 0
    recovery_attempts: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    error_types: Dict[str, int] = field(default_factory=dict)


class CircuitBreaker:
    """Enhanced circuit breaker with metrics and logging"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self._initialize_state()
        self.metrics = ReliabilityMetrics()
    
    def _initialize_state(self) -> None:
        """Initialize circuit breaker state variables"""
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            return self._handle_open_state()
        else:  # HALF_OPEN
            return self._handle_half_open_state()
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is in open state"""
        return self.state == CircuitBreakerState.OPEN
    
    def _handle_open_state(self) -> bool:
        """Handle execution check for OPEN state"""
        if self._should_attempt_reset():
            self._transition_to_half_open()
            return True
        return False
    
    def _handle_half_open_state(self) -> bool:
        """Handle execution check for HALF_OPEN state"""
        return self.half_open_calls < self.config.half_open_max_calls
    
    def record_success(self) -> None:
        """Record successful execution"""
        self._update_success_metrics()
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_closed()
        self._reset_failure_state()
    
    def _update_success_metrics(self) -> None:
        """Update metrics for successful call"""
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = time.time()
    
    def _reset_failure_state(self) -> None:
        """Reset failure tracking state"""
        self.failure_count = 0
        self.last_failure_time = None
    
    def record_failure(self, error_type: str = "unknown") -> None:
        """Record failed execution"""
        self._update_failure_metrics(error_type)
        self._update_failure_count()
        self._check_failure_threshold()
    
    def _update_failure_metrics(self, error_type: str) -> None:
        """Update metrics for failed call"""
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = time.time()
        error_count = self.metrics.error_types.get(error_type, 0)
        self.metrics.error_types[error_type] = error_count + 1
    
    def _update_failure_count(self) -> None:
        """Update internal failure tracking"""
        self.failure_count += 1
        self.last_failure_time = time.time()
    
    def _check_failure_threshold(self) -> None:
        """Check if failure threshold is exceeded"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()
        elif self.failure_count >= self.config.failure_threshold:
            self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if recovery timeout has passed"""
        if not self.last_failure_time:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        if self.state != CircuitBreakerState.OPEN:
            self._log_state_transition_to_open()
            self.metrics.circuit_breaker_opens += 1
        self.state = CircuitBreakerState.OPEN
    
    def _log_state_transition_to_open(self) -> None:
        """Log transition to OPEN state"""
        logger.warning(
            f"Circuit breaker {self.config.name} OPENED after "
            f"{self.failure_count} failures"
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        logger.info(
            f"Circuit breaker {self.config.name} attempting recovery (HALF_OPEN)"
        )
        self.state = CircuitBreakerState.HALF_OPEN
        self.half_open_calls = 0
        self.metrics.recovery_attempts += 1
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        logger.info(f"Circuit breaker {self.config.name} recovered (CLOSED)")
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "config": self._get_config_dict(),
            "metrics": self._get_metrics_dict()
        }
    
    def _get_config_dict(self) -> Dict[str, Any]:
        """Get configuration dictionary"""
        return {
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
            "half_open_max_calls": self.config.half_open_max_calls
        }
    
    def _get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics dictionary"""
        success_rate = self._calculate_success_rate()
        return self._build_metrics_dict(success_rate)
    
    def _build_metrics_dict(self, success_rate: float) -> Dict[str, Any]:
        """Build metrics dictionary with success rate"""
        return {
            "total_calls": self.metrics.total_calls,
            "successful_calls": self.metrics.successful_calls,
            "failed_calls": self.metrics.failed_calls,
            "success_rate": success_rate,
            "circuit_breaker_opens": self.metrics.circuit_breaker_opens,
            "recovery_attempts": self.metrics.recovery_attempts,
            "error_types": self.metrics.error_types
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate from metrics"""
        if self.metrics.total_calls > 0:
            return self.metrics.successful_calls / self.metrics.total_calls
        return 0.0