"""
Circuit breaker module - CONSOLIDATED: All implementations now use app.core.circuit_breaker

This module previously contained a duplicate CircuitBreaker implementation.
All circuit breaker functionality has been consolidated to app.core.circuit_breaker
for single source of truth compliance.
"""

# Re-export from the canonical circuit breaker implementation
from app.core.circuit_breaker import CircuitBreaker, CircuitConfig, CircuitState, circuit_registry

# Export main classes for backwards compatibility
__all__ = ['CircuitBreaker', 'CircuitConfig', 'CircuitState', 'circuit_registry']