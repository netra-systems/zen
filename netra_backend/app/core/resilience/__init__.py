"""Unified Resilience Framework for Enterprise AI Systems.

This module consolidates all circuit breaker patterns into a single,
enterprise-grade resilience system with:

- Unified circuit breakers with configurable policies
- Intelligent retry strategies with backoff algorithms  
- Fallback chain management for graceful degradation
- Real-time monitoring and alerting
- Policy-driven configuration management

Business Value:
- Enterprise deals: +$20K MRR from reliability guarantees
- System stability: 99.99% availability target
- Operational efficiency: Single point of resilience management

Usage:
    from netra_backend.app.core.resilience import with_resilience, register_api_service
    
    # Register service
    register_api_service("user_api", EnvironmentType.PRODUCTION)
    
    # Execute with protection
    result = await with_resilience("user_api", lambda: api_call())
"""

# Core resilience components - only import available modules
# from netra_backend.app.core.resilience.circuit_breaker import (
#     CircuitBreakerOpenError,
#     CircuitConfig,
#     CircuitMetrics,
#     CircuitState,
#     UnifiedCircuitBreaker,
# )
from netra_backend.app.core.resilience.fallback import (
    AlternativeServiceFallback,
    CacheLastKnownFallback,
    FallbackConfig,
    FallbackHandler,
    FallbackPresets,
    FallbackPriority,
    FallbackStrategy,
    StaticResponseFallback,
    UnifiedFallbackChain,
    fallback_manager,
)
from netra_backend.app.core.resilience.monitor import (
    Alert,
    AlertSeverity,
    AlertThreshold,
    HealthMetric,
    HealthStatus,
    ServiceHealth,
    UnifiedResilienceMonitor,
    resilience_monitor,
)
from netra_backend.app.core.resilience.policy import (
    EnvironmentType,
    PolicyTemplate,
    ResiliencePolicy,
    ServiceTier,
    UnifiedPolicyManager,
    create_api_service_policy,
    create_database_service_policy,
    create_llm_service_policy,
    policy_manager,
)
# from netra_backend.app.core.resilience.registry import (
#     ServiceResilienceComponents,
#     UnifiedResilienceRegistry,
#     register_api_service,
#     register_database_service,
#     register_llm_service,
#     resilience_registry,
#     with_resilience,
# )
from netra_backend.app.core.resilience.retry_manager import (
    BackoffStrategy,
    JitterType,
    RetryConfig,
    RetryExhaustedException,
    RetryPresets,
    UnifiedRetryManager,
)
# from netra_backend.app.core.resilience.unified_retry_handler import (
#     UnifiedRetryHandler,
#     RetryResult,
#     RetryStrategy,
#     exponential_backoff,
#     linear_backoff,
#     default_retry_handler,
# )

# Export all public interfaces - only available modules
__all__ = [
    # Core Components
    # "UnifiedCircuitBreaker",
    "UnifiedRetryManager", 
    "UnifiedFallbackChain",
    "UnifiedResilienceMonitor",
    # "UnifiedResilienceRegistry",
    
    # Configuration Classes
    # "CircuitConfig",
    "RetryConfig", 
    "FallbackConfig",
    "ResiliencePolicy",
    "AlertThreshold",
    
    # Enums
    # "CircuitState",
    "BackoffStrategy",
    "JitterType", 
    "FallbackStrategy",
    "FallbackPriority",
    "AlertSeverity",
    "HealthStatus",
    "ServiceTier",
    "EnvironmentType",
    
    # Data Classes
    # "CircuitMetrics",
    "Alert",
    "HealthMetric", 
    "ServiceHealth",
    # "ServiceResilienceComponents",
    
    # Exceptions
    # "CircuitBreakerOpenError",
    "RetryExhaustedException",
    
    # Handlers and Strategies
    "FallbackHandler",
    "StaticResponseFallback",
    "CacheLastKnownFallback", 
    "AlternativeServiceFallback",
    
    # Presets and Factories
    "RetryPresets",
    "FallbackPresets",
    
    # Global Instances
    # "resilience_registry",
    "resilience_monitor",
    "policy_manager",
    "fallback_manager",
    
    # Convenience Functions
    # "with_resilience",
    # "register_api_service",
    # "register_database_service",
    # "register_llm_service",
    "create_api_service_policy",
    "create_database_service_policy", 
    "create_llm_service_policy",
    
    # Unified Retry Handler
    # "UnifiedRetryHandler",
    # "RetryResult",
    # "RetryStrategy",
    # "exponential_backoff",
    # "linear_backoff",
    # "default_retry_handler",
]