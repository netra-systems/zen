"""Reliability Types Schema Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability - Provide type definitions for reliability components
- Value Impact: Ensures type safety for reliability and circuit breaker patterns
- Strategic Impact: Prevents runtime errors through strong typing

This module provides type definitions for reliability, circuit breaker,
rate limiting, and resilience components.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel


class BackoffStrategy(str, Enum):
    """Retry backoff strategies."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    RANDOM = "random"


class JitterType(str, Enum):
    """Jitter types for retry strategies."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter_type: JitterType = JitterType.EQUAL
    enabled: bool = True


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5
    timeout_seconds: float = 30.0
    success_threshold: int = 2
    enabled: bool = True
    state: CircuitState = CircuitState.CLOSED


class CircuitBreakerMetrics(BaseModel):
    """Metrics for circuit breaker monitoring."""
    failure_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: Optional[float] = None
    state_changed_time: Optional[float] = None


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    burst_capacity: int = 20
    enabled: bool = True


class TokenBucket(BaseModel):
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    refill_rate: float
    last_refill_time: float


class HealthCheckResult(BaseModel):
    """Result of a health check operation."""
    is_healthy: bool
    response_time_ms: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = {}


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and requests are rejected."""
    
    def __init__(self, service_name: str, state: CircuitState):
        self.service_name = service_name
        self.state = state
        super().__init__(f"Circuit breaker for {service_name} is {state.value}")


class HealthChecker(ABC):
    """Abstract base class for health checkers."""
    
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Check the health of a service or component.
        
        Returns:
            HealthCheckResult: The result of the health check
        """
        pass


class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection."""
    
    def record_success(self, operation: str, duration: float) -> None:
        """Record a successful operation."""
        ...
    
    def record_failure(self, operation: str, error: str) -> None:
        """Record a failed operation."""
        ...
    
    def get_metrics(self, operation: str) -> Dict[str, Any]:
        """Get metrics for an operation."""
        ...


class RateLimiterProtocol(Protocol):
    """Protocol for rate limiting."""
    
    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed."""
        ...
    
    def consume(self, key: str, tokens: int = 1) -> bool:
        """Consume tokens from the rate limiter."""
        ...
    
    def get_remaining(self, key: str) -> int:
        """Get remaining tokens."""
        ...


class ReliabilityManager:
    """Manager for reliability components."""
    
    def __init__(self):
        """Initialize reliability manager."""
        self._circuit_breakers: Dict[str, CircuitBreakerConfig] = {}
        self._rate_limiters: Dict[str, RateLimitConfig] = {}
        self._retry_configs: Dict[str, RetryConfig] = {}
    
    def register_circuit_breaker(self, service_name: str, config: CircuitBreakerConfig) -> None:
        """Register a circuit breaker for a service."""
        self._circuit_breakers[service_name] = config
    
    def register_rate_limiter(self, service_name: str, config: RateLimitConfig) -> None:
        """Register a rate limiter for a service."""
        self._rate_limiters[service_name] = config
    
    def register_retry_config(self, service_name: str, config: RetryConfig) -> None:
        """Register retry configuration for a service."""
        self._retry_configs[service_name] = config
    
    def get_circuit_breaker_config(self, service_name: str) -> Optional[CircuitBreakerConfig]:
        """Get circuit breaker configuration for a service."""
        return self._circuit_breakers.get(service_name)
    
    def get_rate_limit_config(self, service_name: str) -> Optional[RateLimitConfig]:
        """Get rate limit configuration for a service."""
        return self._rate_limiters.get(service_name)
    
    def get_retry_config(self, service_name: str) -> Optional[RetryConfig]:
        """Get retry configuration for a service."""
        return self._retry_configs.get(service_name)


# Export all types
__all__ = [
    "BackoffStrategy",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitBreakerOpenError",
    "CircuitState",
    "HealthChecker",
    "HealthCheckResult",
    "JitterType",
    "MetricsCollectorProtocol",
    "RateLimitConfig",
    "RateLimiterProtocol",
    "ReliabilityManager",
    "RetryConfig",
    "TokenBucket",
]