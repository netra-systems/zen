"""Adaptive circuit breakers - main module with imports from focused modules.

Imports from split modules to maintain backward compatibility while enforcing
300-line limit and 8-line function limit. All functions ≤8 lines.
"""

# Import types and health checkers
from .shared_health_types import HealthChecker, HealthStatus
from .circuit_breaker_health_checkers import ApiHealthChecker, ServiceHealthChecker

# Import core circuit breaker
from .adaptive_circuit_breaker_core import AdaptiveCircuitBreaker

# Import registry and convenience functions
from .circuit_breaker_registry_adaptive import (
    CircuitBreakerRegistry, circuit_breaker_registry,
    get_circuit_breaker, remove_circuit_breaker,
    get_all_circuit_breaker_metrics, cleanup_all_circuit_breakers,
    circuit_breaker, with_health_check, circuit_breaker_sync
)

# Import unified types from single source of truth
from app.schemas.core_enums import CircuitBreakerState
from app.schemas.core_models import CircuitBreakerConfig, HealthCheckResult

# Use CircuitBreakerState as CircuitState for backward compatibility
CircuitState = CircuitBreakerState

# Export all for backward compatibility
__all__ = [
    'HealthChecker', 'HealthStatus', 'ApiHealthChecker', 'ServiceHealthChecker',
    'AdaptiveCircuitBreaker', 'CircuitBreakerRegistry', 'circuit_breaker_registry',
    'get_circuit_breaker', 'remove_circuit_breaker', 'get_all_circuit_breaker_metrics',
    'cleanup_all_circuit_breakers', 'circuit_breaker', 'with_health_check',
    'circuit_breaker_sync', 'CircuitBreakerState', 'CircuitState',
    'CircuitBreakerConfig', 'HealthCheckResult'
]


def create_database_health_checker(db_pool):
    """Create database health checker from unified types."""
    from .shared_health_types import DatabaseHealthChecker
    return DatabaseHealthChecker(db_pool)


def create_api_health_checker(endpoint: str, timeout: float = 5.0) -> ApiHealthChecker:
    """Create API health checker instance."""
    return ApiHealthChecker(endpoint, timeout)


def create_service_health_checker(service_name: str, check_function) -> ServiceHealthChecker:
    """Create service health checker instance."""
    return ServiceHealthChecker(service_name, check_function)


def create_adaptive_circuit_breaker(name: str, config: CircuitBreakerConfig = None, 
                                   health_checker: HealthChecker = None) -> AdaptiveCircuitBreaker:
    """Create adaptive circuit breaker instance."""
    return AdaptiveCircuitBreaker(name, config or CircuitBreakerConfig(), health_checker)