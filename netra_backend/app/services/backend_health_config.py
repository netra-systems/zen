"""
Backend service health check configuration.
Sets up all health checks for the backend service using the unified health system.
"""

from netra_backend.app.services.unified_health_service import UnifiedHealthService
from netra_backend.app.services.health_registry import health_registry
from netra_backend.app.core.health_types import HealthCheckConfig, CheckType
from netra_backend.app.core.health_checkers import (
    check_postgres_health,
    check_redis_health,
    check_clickhouse_health,
    check_websocket_health,
    check_system_resources,
    check_auth_service_health,
    check_discovery_service_health,
    check_database_monitoring_health,
    check_circuit_breakers_health
)


async def setup_backend_health_service() -> UnifiedHealthService:
    """Configure health checks for the backend service."""
    from shared.isolated_environment import get_env
    
    health_service = UnifiedHealthService("netra_backend", "1.0.0")
    
    # Environment-aware timeout configuration for fast staging readiness
    env = get_env().get('ENVIRONMENT', 'development').lower()
    is_staging = env == 'staging'
    
    # Use faster timeouts for staging to prevent readiness probe timeouts
    postgres_timeout = 3.0 if is_staging else 10.0
    redis_timeout = 2.0 if is_staging else 5.0
    
    # Critical infrastructure checks (Readiness)
    await health_service.register_check(HealthCheckConfig(
        name="postgres",
        description="PostgreSQL database connectivity",
        check_function=check_postgres_health,
        timeout_seconds=postgres_timeout,
        check_type=CheckType.READINESS,
        critical=True,
        priority=1,  # Critical
        labels={"component": "database", "infrastructure": "true"}
    ))
    
    await health_service.register_check(HealthCheckConfig(
        name="redis",
        description="Redis cache connectivity",
        check_function=check_redis_health,
        timeout_seconds=redis_timeout,
        check_type=CheckType.READINESS,
        critical=False,
        priority=2,  # Important but not critical
        labels={"component": "cache", "infrastructure": "true"}
    ))
    
    # Optional services - faster timeouts for staging
    clickhouse_timeout = 3.0 if is_staging else 10.0
    
    await health_service.register_check(HealthCheckConfig(
        name="clickhouse",
        description="ClickHouse analytics database",
        check_function=check_clickhouse_health,
        timeout_seconds=clickhouse_timeout,
        check_type=CheckType.COMPONENT,
        critical=False,
        priority=3,  # Optional
        labels={"component": "analytics", "infrastructure": "true"}
    ))
    
    # Application layer checks
    await health_service.register_check(HealthCheckConfig(
        name="websocket",
        description="WebSocket connection manager",
        check_function=check_websocket_health,
        timeout_seconds=5.0,
        check_type=CheckType.COMPONENT,
        critical=False,
        priority=2,
        labels={"component": "websocket", "layer": "application"}
    ))
    
    # System health checks
    await health_service.register_check(HealthCheckConfig(
        name="system_resources",
        description="System resource usage",
        check_function=check_system_resources,
        timeout_seconds=5.0,
        check_type=CheckType.LIVENESS,
        critical=False,
        priority=2,
        labels={"component": "system", "layer": "infrastructure"}
    ))
    
    # Auth service health check - reduced timeout for staging
    auth_service_timeout = 3.0 if is_staging else 8.0
    
    await health_service.register_check(HealthCheckConfig(
        name="auth_service",
        description="Auth service connectivity and configuration",
        check_function=check_auth_service_health,
        timeout_seconds=auth_service_timeout,
        check_type=CheckType.COMPONENT,
        critical=False,
        priority=2,
        labels={"component": "auth", "layer": "application"}
    ))
    
    # Discovery service health check
    await health_service.register_check(HealthCheckConfig(
        name="discovery",
        description="Service discovery directory and configuration",
        check_function=check_discovery_service_health,
        timeout_seconds=3.0,
        check_type=CheckType.COMPONENT,
        critical=False,
        priority=3,  # Optional service
        labels={"component": "discovery", "layer": "application"}
    ))
    
    # Database monitoring health check
    await health_service.register_check(HealthCheckConfig(
        name="database_monitoring",
        description="Database connection monitoring and pool metrics",
        check_function=check_database_monitoring_health,
        timeout_seconds=10.0,
        check_type=CheckType.COMPONENT,
        critical=False,
        priority=3,  # Optional monitoring service
        labels={"component": "monitoring", "layer": "application"}
    ))
    
    # Circuit breaker health check
    await health_service.register_check(HealthCheckConfig(
        name="circuit_breakers",
        description="Circuit breaker system health and resilience status",
        check_function=check_circuit_breakers_health,
        timeout_seconds=8.0,
        check_type=CheckType.READINESS,
        critical=False,
        priority=2,  # Important for system resilience
        labels={"component": "circuit_breakers", "layer": "infrastructure"}
    ))
    
    # Register with global registry
    health_registry.register_service("netra_backend", health_service)
    
    return health_service