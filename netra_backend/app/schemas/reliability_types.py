"""
Reliability Types: Single Source of Truth for Circuit Breaker, Retry, and Reliability Models

This module contains all reliability-related models and state definitions used across 
the Netra platform, ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All reliability model definitions MUST be imported from this module
- NO duplicate reliability model definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.reliability_types import CircuitBreaker, RetryConfig, RateLimiter
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union

from pydantic import BaseModel, Field

from netra_backend.app.core.exceptions_service import ServiceError

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states with clear semantics."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class BackoffStrategy(Enum):
    """Backoff strategy enumeration."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    JITTERED = "jittered"


class JitterType(Enum):
    """Jitter type enumeration."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


@dataclass
class CircuitBreakerConfig:
    """Unified configuration for circuit breaker behavior - consolidates all variants."""
    # Basic circuit breaker settings
    name: str
    failure_threshold: int = 5
    success_threshold: int = 3
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    
    # Advanced settings for adaptive behavior
    timeout_seconds: float = 60.0
    health_check_interval: int = 30
    slow_call_threshold: float = 5.0
    max_wait_duration: int = 300
    adaptive_threshold: bool = True
    
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
class CircuitBreakerMetrics:
    """Circuit breaker metrics for monitoring - consolidated from all variants."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeouts: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    failure_types: Dict[str, int] = field(default_factory=dict)
    circuit_breaker_opens: int = 0
    recovery_attempts: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)


class CircuitBreakerOpenError(ServiceError):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, circuit_name: str) -> None:
        super().__init__(f"Circuit breaker '{circuit_name}' is OPEN")
        self.circuit_name = circuit_name


class RetryConfig(BaseModel):
    """Centralized retry configuration for all components."""
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    base_delay: float = Field(default=1.0, description="Base delay between retries")
    max_delay: float = Field(default=300.0, description="Maximum delay between retries")
    backoff_strategy: BackoffStrategy = Field(default=BackoffStrategy.EXPONENTIAL, description="Backoff strategy")
    jitter_type: JitterType = Field(default=JitterType.FULL, description="Jitter type")
    backoff_factor: float = Field(default=2.0, description="Exponential backoff factor")
    timeout_seconds: int = Field(default=600, description="Operation timeout")
    jitter: bool = Field(default=True, description="Add jitter to delays")


class RateLimitConfig(BaseModel):
    """Rate limiter configuration."""
    requests_per_second: float = Field(default=10.0, description="Requests per second limit")
    burst_capacity: int = Field(default=20, description="Maximum burst size")
    window_size: int = Field(default=60, description="Rate limiting window in seconds")
    enable_adaptive: bool = Field(default=True, description="Enable adaptive rate limiting")
    backoff_factor: float = Field(default=1.5, description="Backoff factor for adaptive limiting")


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    status: str
    response_time: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class HealthChecker(Protocol):
    """Protocol for health checking implementations."""
    
    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return result."""
        ...


class RateLimiterProtocol(Protocol):
    """Protocol for rate limiter implementations."""
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from rate limiter."""
        ...
    
    async def reset(self) -> None:
        """Reset rate limiter state."""
        ...
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get rate limiter statistics."""
        ...


class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection implementations."""
    
    def record_metric(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        ...
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        ...
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value."""
        ...
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        ...


@dataclass
class TokenBucket:
    """Token bucket rate limiter implementation."""
    capacity: float
    tokens: float
    refill_rate: float
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: float = 1.0) -> bool:
        """Consume tokens from bucket."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class ReliabilityManager:
    """Unified reliability manager combining circuit breaker, retry, and rate limiting."""
    
    def __init__(self, circuit_config: CircuitBreakerConfig, retry_config: RetryConfig, 
                 rate_limit_config: Optional[RateLimitConfig] = None) -> None:
        self.circuit_config = circuit_config
        self.retry_config = retry_config
        self.rate_limit_config = rate_limit_config
        self._circuit_breaker: Optional[Any] = None
        self._rate_limiter: Optional[TokenBucket] = None
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize reliability components."""
        if self.rate_limit_config:
            self._rate_limiter = TokenBucket(
                capacity=self.rate_limit_config.burst_capacity,
                tokens=self.rate_limit_config.burst_capacity,
                refill_rate=self.rate_limit_config.requests_per_second
            )
    
    async def execute_with_reliability(self, func: Callable[[], T]) -> T:
        """Execute function with full reliability protection."""
        if self._rate_limiter and not self._rate_limiter.consume():
            raise ServiceError("Rate limit exceeded")
        
        # Implementation would use circuit breaker and retry logic
        return await func()


# Export all reliability types
__all__ = [
    "CircuitState",
    "BackoffStrategy", 
    "JitterType",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitBreakerOpenError",
    "RetryConfig",
    "RateLimitConfig",
    "HealthCheckResult",
    "HealthChecker",
    "RateLimiterProtocol",
    "MetricsCollectorProtocol",
    "TokenBucket",
    "ReliabilityManager"
]