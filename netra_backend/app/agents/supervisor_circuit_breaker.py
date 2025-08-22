"""Circuit breaker module - CONSOLIDATED: All implementations now use app.core.circuit_breaker"""

# Re-export from the canonical circuit breaker implementation
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.circuit_breaker import CircuitConfig as CircuitBreakerConfig
from netra_backend.app.schemas.core_enums import CircuitBreakerState

# Export the main classes for backwards compatibility
__all__ = ['CircuitBreaker', 'CircuitBreakerConfig', 'CircuitBreakerState']