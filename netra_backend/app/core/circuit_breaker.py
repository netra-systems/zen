"""Production-grade circuit breaker implementation for Netra AI platform.

This module provides a comprehensive circuit breaker system with:
- State management (closed/open/half-open) 
- Configurable thresholds and timeouts
- Metrics collection and monitoring
- Integration with external services
- Async/await support

MIGRATION NOTICE: This module now includes the NEW Unified Resilience Framework
which consolidates 181+ circuit breaker implementations. For enterprise features,
use the unified system from .resilience package.

This is the main module that re-exports all circuit breaker functionality
from both legacy and unified implementations.
"""

# Legacy circuit breaker exports for backwards compatibility
from netra_backend.app.circuit_breaker_types import (
    CircuitState,
    CircuitConfig,
    CircuitMetrics,
    CircuitBreakerOpenError
)

from netra_backend.app.circuit_breaker_core import (
    CircuitBreaker
)

from netra_backend.app.circuit_breaker_registry_adaptive import (
    CircuitBreakerRegistry,
    circuit_breaker_registry as circuit_registry,
    get_circuit_breaker,
    circuit_breaker
)

# NEW: Unified Resilience Framework exports
from netra_backend.app.resilience import (
    UnifiedCircuitBreaker,
    UnifiedRetryManager,
    UnifiedFallbackChain,
    UnifiedResilienceRegistry,
    resilience_registry,
    with_resilience,
    register_api_service,
    register_database_service,
    register_llm_service,
    EnvironmentType,
    ServiceTier
)

# Export all public interfaces (legacy + unified)
__all__ = [
    # Legacy Types and configurations
    'CircuitState',
    'CircuitConfig', 
    'CircuitMetrics',
    'CircuitBreakerOpenError',
    
    # Legacy Core circuit breaker
    'CircuitBreaker',
    
    # Legacy Registry and utilities
    'CircuitBreakerRegistry',
    'circuit_registry',
    'get_circuit_breaker',
    'circuit_breaker',
    
    # NEW: Unified Resilience Framework
    'UnifiedCircuitBreaker',
    'UnifiedRetryManager',
    'UnifiedFallbackChain', 
    'UnifiedResilienceRegistry',
    'resilience_registry',
    'with_resilience',
    'register_api_service',
    'register_database_service',
    'register_llm_service',
    'EnvironmentType',
    'ServiceTier'
]