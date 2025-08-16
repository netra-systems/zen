"""Production-grade circuit breaker implementation for Netra AI platform.

This module provides a comprehensive circuit breaker system with:
- State management (closed/open/half-open)
- Configurable thresholds and timeouts
- Metrics collection and monitoring
- Integration with external services
- Async/await support

This is the main module that re-exports all circuit breaker functionality
from the modular implementation.
"""

# Re-export all types and classes for backwards compatibility
from .circuit_breaker_types import (
    CircuitState,
    CircuitConfig,
    CircuitMetrics,
    CircuitBreakerOpenError
)

from .circuit_breaker_core import (
    CircuitBreaker
)

from .circuit_breaker_registry_adaptive import (
    CircuitBreakerRegistry,
    circuit_breaker_registry as circuit_registry,
    get_circuit_breaker,
    circuit_breaker
)

# Export all public interfaces
__all__ = [
    # Types and configurations
    'CircuitState',
    'CircuitConfig', 
    'CircuitMetrics',
    'CircuitBreakerOpenError',
    
    # Core circuit breaker
    'CircuitBreaker',
    
    # Registry and utilities
    'CircuitBreakerRegistry',
    'circuit_registry',
    'get_circuit_breaker',
    'circuit_breaker'
]