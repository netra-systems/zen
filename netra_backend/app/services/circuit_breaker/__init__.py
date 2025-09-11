"""Circuit Breaker Service Package

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable test execution and prevent circuit breaker import errors  
- Value Impact: Ensures test suite can import circuit breaker dependencies
- Strategic Impact: Maintains compatibility for circuit breaker functionality

DEPRECATED: Use UnifiedCircuitBreaker from core.resilience.unified_circuit_breaker instead.

NOTE: For circuit breaker classes, import from the main module directly:
    from netra_backend.app.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
"""

# Legacy import removed - circuit_breaker_manager no longer exists
# from netra_backend.app.services.circuit_breaker.circuit_breaker_manager import (
#     CircuitBreakerManager,
# )
# Import from SSOT location
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker as CircuitBreakerManager,
    UnifiedCircuitBreaker as CircuitBreaker,  # Alias for backward compatibility
    UnifiedCircuitConfig as CircuitBreakerConfig,  # Alias for backward compatibility
)
from netra_backend.app.services.circuit_breaker.failure_detector import FailureDetector
from netra_backend.app.services.circuit_breaker.service_health_monitor import (
    ServiceHealthMonitor,
)

__all__ = [
    "CircuitBreakerManager", 
    "CircuitBreaker", 
    "CircuitBreakerConfig",
    "ServiceHealthMonitor", 
    "FailureDetector"
]