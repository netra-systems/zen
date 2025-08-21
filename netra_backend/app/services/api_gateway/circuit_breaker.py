"""API Gateway Circuit Breaker implementation."""

import time
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    timeout: int = 30
    enabled: bool = True


class CircuitBreakerStats:
    """Tracks circuit breaker statistics."""
    
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.last_failure_time = 0.0
        self.last_success_time = 0.0
    
    def record_success(self) -> None:
        """Record a successful request."""
        self.success_count += 1
        self.total_requests += 1
        self.last_success_time = time.time()
    
    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.total_requests += 1
        self.last_failure_time = time.time()
    
    def reset(self) -> None:
        """Reset statistics."""
        self.failure_count = 0
        self.success_count = 0
        # Keep total_requests for overall stats


class ApiFallbackService:
    """Provides fallback responses when circuit is open."""
    
    def __init__(self):
        self.fallback_responses: Dict[str, Any] = {}
        self.default_response = {"error": "Service temporarily unavailable"}
    
    def set_fallback(self, endpoint: str, response: Any) -> None:
        """Set fallback response for an endpoint."""
        self.fallback_responses[endpoint] = response
    
    def get_fallback(self, endpoint: str) -> Any:
        """Get fallback response for an endpoint."""
        return self.fallback_responses.get(endpoint, self.default_response)


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different endpoints."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, 'ApiCircuitBreaker'] = {}
        self.fallback_service = ApiFallbackService()
    
    def get_circuit_breaker(self, endpoint: str, config: Optional[CircuitBreakerConfig] = None) -> 'ApiCircuitBreaker':
        """Get or create circuit breaker for endpoint."""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = ApiCircuitBreaker(
                name=endpoint,
                config=config or CircuitBreakerConfig()
            )
        return self.circuit_breakers[endpoint]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stats for all circuit breakers."""
        return {
            endpoint: cb.get_stats()
            for endpoint, cb in self.circuit_breakers.items()
        }


class ApiCircuitBreaker:
    """Circuit breaker for API endpoints."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.last_state_change = time.time()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if not self.config.enabled:
            return func(*args, **kwargs)
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (time.time() - self.last_state_change) >= self.config.recovery_timeout
    
    def _record_success(self) -> None:
        """Record successful request and update state."""
        self.stats.record_success()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.stats.reset()
                self.last_state_change = time.time()
    
    def _record_failure(self) -> None:
        """Record failed request and update state."""
        self.stats.record_failure()
        
        if self.state == CircuitState.CLOSED:
            if self.stats.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.stats.failure_count,
            'success_count': self.stats.success_count,
            'total_requests': self.stats.total_requests,
            'last_failure_time': self.stats.last_failure_time,
            'last_success_time': self.stats.last_success_time,
            'last_state_change': self.last_state_change
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.stats.reset()
        self.last_state_change = time.time()
    
    def force_open(self) -> None:
        """Manually open circuit breaker."""
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
