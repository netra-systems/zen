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
    from app.core.resilience import with_resilience, register_api_service
    
    # Register service
    register_api_service("user_api", EnvironmentType.PRODUCTION)
    
    # Execute with protection
    result = await with_resilience("user_api", lambda: api_call())
"""

# Core resilience components
from .circuit_breaker import (
    UnifiedCircuitBreaker,
    CircuitConfig,
    CircuitState,
    CircuitMetrics,
    CircuitBreakerOpenError
)

from .retry_manager import (
    UnifiedRetryManager,
    RetryConfig,
    BackoffStrategy,
    JitterType,
    RetryPresets,
    RetryExhaustedException
)

from .fallback import (
    UnifiedFallbackChain,
    FallbackHandler,
    StaticResponseFallback,
    CacheLastKnownFallback,
    AlternativeServiceFallback,
    FallbackConfig,
    FallbackStrategy,
    FallbackPriority,
    FallbackPresets,
    fallback_manager
)

from .monitor import (
    UnifiedResilienceMonitor,
    AlertSeverity,
    HealthStatus,
    Alert,
    AlertThreshold,
    HealthMetric,
    ServiceHealth,
    resilience_monitor
)

from .policy import (
    ResiliencePolicy,
    PolicyTemplate,
    ServiceTier,
    EnvironmentType,
    UnifiedPolicyManager,
    policy_manager,
    create_api_service_policy,
    create_database_service_policy,
    create_llm_service_policy
)

from .registry import (
    UnifiedResilienceRegistry,
    ServiceResilienceComponents,
    resilience_registry,
    with_resilience,
    register_api_service,
    register_database_service,
    register_llm_service
)

# Export all public interfaces
__all__ = [
    # Core Components
    "UnifiedCircuitBreaker",
    "UnifiedRetryManager", 
    "UnifiedFallbackChain",
    "UnifiedResilienceMonitor",
    "UnifiedResilienceRegistry",
    
    # Configuration Classes
    "CircuitConfig",
    "RetryConfig", 
    "FallbackConfig",
    "ResiliencePolicy",
    "AlertThreshold",
    
    # Enums
    "CircuitState",
    "BackoffStrategy",
    "JitterType", 
    "FallbackStrategy",
    "FallbackPriority",
    "AlertSeverity",
    "HealthStatus",
    "ServiceTier",
    "EnvironmentType",
    
    # Data Classes
    "CircuitMetrics",
    "Alert",
    "HealthMetric", 
    "ServiceHealth",
    "ServiceResilienceComponents",
    
    # Exceptions
    "CircuitBreakerOpenError",
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
    "resilience_registry",
    "resilience_monitor",
    "policy_manager",
    "fallback_manager",
    
    # Convenience Functions
    "with_resilience",
    "register_api_service",
    "register_database_service",
    "register_llm_service",
    "create_api_service_policy",
    "create_database_service_policy", 
    "create_llm_service_policy"
]