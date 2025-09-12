"""Production-grade circuit breaker implementation for Netra AI platform.

This module provides a comprehensive circuit breaker system with:
- State management (closed/open/half-open) 
- Configurable thresholds and timeouts
- Metrics collection and monitoring
- Integration with external services
- Async/await support

STRATEGIC COMPATIBILITY LAYER: This module provides a strategic compatibility
layer that bridges existing code to the Unified Resilience Framework. The
compatibility layer adds significant business value by:
- Enabling seamless migration without breaking changes
- Maintaining API stability for downstream consumers  
- Providing gradual transition path to unified system
- Preserving enterprise customer integrations

Use the unified system from .resilience package for all new circuit breaker functionality.
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

# Strategic compatibility aliases - preserve API stability while enabling unified system
CircuitBreaker = UnifiedCircuitBreaker  # Strategic compatibility for existing integrations
CircuitBreakerRegistry = UnifiedCircuitBreakerManager  # Strategic compatibility for existing integrations
circuit_registry = get_unified_circuit_breaker_manager()  # Strategic compatibility for existing integrations

def get_circuit_breaker(name: str, config=None):
    """Strategic compatibility function providing seamless access to unified circuit breakers."""
    manager = get_unified_circuit_breaker_manager()
    unified_config = None
    if config:
        # Convert existing config to unified config if needed for backward compatibility
        if hasattr(config, 'failure_threshold'):
            unified_config = UnifiedCircuitConfig(
                name=name,
                failure_threshold=getattr(config, 'failure_threshold', 5),
                recovery_timeout=getattr(config, 'recovery_timeout', 60.0),
                timeout_seconds=getattr(config, 'timeout_seconds', 30.0)
            )
    # 🔧 FIX: Ensure unified_config is never None to prevent AttributeError
    if unified_config is None:
        unified_config = UnifiedCircuitConfig(name=name)
    return manager.create_circuit_breaker(name, unified_config)

def circuit_breaker(name=None, config=None):
    """Strategic compatibility decorator providing seamless access to unified circuit breaker functionality."""
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
    
    # Strategic Compatibility Aliases (preserve API stability)
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