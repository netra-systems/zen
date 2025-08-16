"""Circuit breaker module - CONSOLIDATED: All implementations now use app.core.circuit_breaker"""

# Re-export from the canonical circuit breaker implementation
from app.core.circuit_breaker import CircuitBreaker, CircuitConfig as CircuitBreakerConfig
from app.schemas.core_enums import CircuitBreakerState

# Export the main classes for backwards compatibility
__all__ = ['CircuitBreaker', 'CircuitBreakerConfig', 'CircuitBreakerState']