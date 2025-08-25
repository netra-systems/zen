"""Production-grade circuit breaker implementation for Netra AI platform.

This module provides a comprehensive circuit breaker system with:
- State management (closed/open/half-open) 
- Configurable thresholds and timeouts
- Metrics collection and monitoring
- Integration with external services
- Async/await support

MIGRATION COMPLETE: This module now uses the Unified Resilience Framework
which has replaced all legacy circuit breaker implementations. All legacy
implementations have been consolidated into the unified system.

Use the unified system from .resilience package for all circuit breaker functionality.
"""

# Import core types that are still used across the system
from netra_backend.app.core.circuit_breaker_types import (
    CircuitBreakerOpenError,
    CircuitConfig,
    CircuitMetrics,
    CircuitState,
)

# Import unified circuit breaker system
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerManager,
    get_unified_circuit_breaker_manager,
    unified_circuit_breaker,
    unified_circuit_breaker_context,
    UnifiedServiceCircuitBreakers,
)

# NEW: Unified Resilience Framework exports (if available)
try:
    from netra_backend.app.core.resilience import (
        EnvironmentType,
        ServiceTier,
        UnifiedFallbackChain,
        UnifiedResilienceRegistry,
        UnifiedRetryManager,
        register_api_service,
        register_database_service,
        register_llm_service,
        resilience_registry,
        with_resilience,
    )
    _HAS_RESILIENCE_FRAMEWORK = True
except ImportError:
    _HAS_RESILIENCE_FRAMEWORK = False

# Compatibility aliases - map legacy to unified
CircuitBreaker = UnifiedCircuitBreaker  # Legacy compatibility
CircuitBreakerRegistry = UnifiedCircuitBreakerManager  # Legacy compatibility
circuit_registry = get_unified_circuit_breaker_manager()  # Legacy compatibility

def get_circuit_breaker(name: str, config=None):
    """Legacy compatibility function."""
    manager = get_unified_circuit_breaker_manager()
    unified_config = None
    if config:
        # Convert legacy config to unified config if needed
        if hasattr(config, 'failure_threshold'):
            unified_config = UnifiedCircuitConfig(
                name=name,
                failure_threshold=getattr(config, 'failure_threshold', 5),
                recovery_timeout=getattr(config, 'recovery_timeout', 60.0),
                timeout_seconds=getattr(config, 'timeout_seconds', 30.0)
            )
    return manager.create_circuit_breaker(name, unified_config)

def circuit_breaker(name=None, config=None):
    """Legacy compatibility decorator."""
    return unified_circuit_breaker(name, config)

# Export all public interfaces
__all__ = [
    # Core Types (preserved)
    'CircuitState',
    'CircuitConfig', 
    'CircuitMetrics',
    'CircuitBreakerOpenError',
    
    # Unified Circuit Breaker System
    'UnifiedCircuitBreaker',
    'UnifiedCircuitConfig',
    'UnifiedCircuitBreakerManager',
    'get_unified_circuit_breaker_manager',
    'unified_circuit_breaker',
    'unified_circuit_breaker_context',
    'UnifiedServiceCircuitBreakers',
    
    # Legacy Compatibility Aliases
    'CircuitBreaker',  # -> UnifiedCircuitBreaker
    'CircuitBreakerRegistry',  # -> UnifiedCircuitBreakerManager
    'circuit_registry',
    'get_circuit_breaker',
    'circuit_breaker',
]

# Add resilience framework exports if available
if _HAS_RESILIENCE_FRAMEWORK:
    __all__.extend([
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
    ])