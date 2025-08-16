"""Circuit breaker types, configurations, and data classes.

This module contains all the type definitions, enums, configurations,
and data classes used by the circuit breaker system.
"""

import time
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass, field

from app.core.exceptions_service import ServiceError


class CircuitState(Enum):
    """Circuit breaker states with clear semantics."""
    CLOSED = "closed"     # Normal operation
    OPEN = "open"         # Failing - reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitConfig:
    """Circuit breaker configuration with production defaults."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    timeout_seconds: float = 10.0
    adaptive_threshold: bool = True
    slow_call_threshold: float = 5.0
    
    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        self._validate_threshold()
        self._validate_timeout()
        self._validate_half_open()
    
    def _validate_threshold(self) -> None:
        """Validate failure threshold is positive."""
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
    
    def _validate_timeout(self) -> None:
        """Validate timeouts are positive."""
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
    
    def _validate_half_open(self) -> None:
        """Validate half-open configuration."""
        if self.half_open_max_calls <= 0:
            raise ValueError("half_open_max_calls must be positive")


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics for monitoring."""
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