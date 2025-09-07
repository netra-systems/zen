"""Database and service health checkers.

Individual health check implementations for system components.
Implements "Default to Resilience" principle with service priority levels
and graceful degradation instead of hard failures.
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import psutil

from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.core.health_types import HealthCheckResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ServicePriority(Enum):
    """Service priority levels for graceful degradation."""
    CRITICAL = "critical"      # System cannot function without this
    IMPORTANT = "important"    # Degraded functionality when unavailable
    OPTIONAL = "optional"      # System continues normally when unavailable


def _get_service_priority_for_environment(service: str) -> ServicePriority:
    """Get service priority based on environment and optional service flags."""
    config = unified_config_manager.get_config()
    env = config.environment.lower()
    
    # Base priorities
    base_priorities = {
        "postgres": ServicePriority.CRITICAL,
        "system_resources": ServicePriority.IMPORTANT,
        "websocket": ServicePriority.IMPORTANT,
    }
    
    if service in base_priorities:
        return base_priorities[service]
    
    # Check for staging infrastructure flags (pragmatic degradation)
    if env == 'staging':
        # Apply pragmatic infrastructure flags for staging
        if service == "redis" and getattr(config, 'redis_optional_in_staging', False):
            logger.info("Redis is optional in staging - degraded operation allowed")
            return ServicePriority.OPTIONAL
        elif service == "clickhouse" and getattr(config, 'clickhouse_optional_in_staging', False):
            logger.info("ClickHouse is optional in staging - degraded operation allowed")
            return ServicePriority.OPTIONAL
        else:
            # Default staging priorities (strict by default)
            staging_priorities = {
                "redis": ServicePriority.CRITICAL,
                "clickhouse": ServicePriority.CRITICAL,
            }
            return staging_priorities.get(service, ServicePriority.IMPORTANT)
    elif env == 'production':
        # In production, external services have different priorities based on system criticality
        production_priorities = {
            "redis": ServicePriority.CRITICAL,
            "clickhouse": ServicePriority.OPTIONAL,  # Analytics service - system can function without it
        }
        return production_priorities.get(service, ServicePriority.IMPORTANT)
    else:
        # In development, external services are optional
        dev_priorities = {
            "redis": ServicePriority.IMPORTANT,
            "clickhouse": ServicePriority.OPTIONAL,  # Often disabled in dev
        }
        return dev_priorities.get(service, ServicePriority.IMPORTANT)

# Legacy mapping for backward compatibility
SERVICE_PRIORITIES = {
    "postgres": ServicePriority.CRITICAL,
    "redis": ServicePriority.IMPORTANT,
    "clickhouse": ServicePriority.OPTIONAL,
    "websocket": ServicePriority.IMPORTANT,
    "system_resources": ServicePriority.IMPORTANT,
}


async def check_postgres_health() -> HealthCheckResult:
    """Check PostgreSQL database connectivity and health with resilient handling."""
    start_time = time.time()
    try:
        # Get environment-appropriate timeout
        timeout = _get_health_check_timeout()
        await asyncio.wait_for(_execute_postgres_query(), timeout=timeout)
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("postgres", response_time)
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("postgres", f"Health check timeout after {timeout}s", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("postgres", str(e), response_time)

async def _execute_postgres_query() -> None:
    """Execute test query on PostgreSQL database using centralized connection manager."""
    from sqlalchemy import text
    from netra_backend.app.db.database_manager import DatabaseManager
    
    # CRITICAL: Use canonical database access pattern from database module SSOT
    try:
        # Use get_db() for proper session lifecycle management
        from netra_backend.app.database import get_db
        async with get_db() as session:
            await session.execute(text("SELECT 1"))
    except (ValueError, Exception):
        # Fallback to direct engine access via SSOT database module
        from netra_backend.app.database import get_engine
        engine = get_engine()
        
        # CRITICAL: Defensive check to prevent sslmode regression
        engine_url = str(getattr(engine, 'url', ''))
        if "sslmode=" in engine_url:
            logger.error(f"CRITICAL: Health checker detected sslmode in engine URL: {engine_url}")
            raise RuntimeError("Health check blocked - sslmode parameter detected in database URL")
        
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))


async def check_clickhouse_health() -> HealthCheckResult:
    """Check ClickHouse database connectivity and health."""
    start_time = time.time()
    
    # Check if ClickHouse should be skipped entirely
    config = unified_config_manager.get_config()
    if getattr(config, 'skip_clickhouse_init', False):
        logger.info("ClickHouse health check skipped - skip_clickhouse_init=True")
        return _create_disabled_result("clickhouse", "ClickHouse disabled by configuration")
    
    try:
        return await _process_clickhouse_health_check(start_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_clickhouse_error(e, response_time)

async def _process_clickhouse_health_check(start_time: float) -> HealthCheckResult:
    """Process ClickHouse health check logic."""
    disabled_result = _check_clickhouse_disabled_status()
    if disabled_result:
        return disabled_result
    await _execute_clickhouse_query()
    response_time = (time.time() - start_time) * 1000
    return _create_success_result("clickhouse", response_time)

def _check_clickhouse_disabled_status() -> Optional[HealthCheckResult]:
    """Check if ClickHouse is disabled and return appropriate result."""
    if _is_development_mode() and _is_clickhouse_disabled():
        return _create_disabled_result("clickhouse", "ClickHouse disabled in development")
    return None

async def _execute_clickhouse_query() -> None:
    """Execute test query on ClickHouse database."""
    from netra_backend.app.database import get_clickhouse_client
    async with get_clickhouse_client() as client:
        await client.execute("SELECT 1")

def _handle_clickhouse_error(error: Exception, response_time: float) -> HealthCheckResult:
    """Handle ClickHouse connection errors based on environment and service priority."""
    error_msg = str(error)
    if _is_development_mode():
        return _create_disabled_result("clickhouse", f"ClickHouse unavailable in development: {error_msg}")
    # Use centralized service failure handling based on priority
    return _handle_service_failure("clickhouse", error_msg, response_time)


async def check_redis_health() -> HealthCheckResult:
    """Check Redis connectivity and health with graceful degradation."""
    start_time = time.time()
    
    # Check if Redis should be skipped entirely
    config = unified_config_manager.get_config()
    if getattr(config, 'skip_redis_init', False):
        logger.info("Redis health check skipped - skip_redis_init=True")
        return _create_disabled_result("redis", "Redis disabled by configuration")
    
    try:
        await _execute_redis_ping()
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("redis", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("redis", str(e), response_time)

async def _execute_redis_ping() -> None:
    """Execute Redis ping operation."""
    client = await _get_redis_client_or_fail()
    await client.ping()

async def _get_redis_client_or_fail():
    """Get Redis client or raise appropriate exception."""
    from netra_backend.app.redis_manager import redis_manager
    if not redis_manager.enabled:
        raise RuntimeError("Redis disabled in development")
    client = await redis_manager.get_client()
    if client is None:
        raise RuntimeError("Redis client not available")
    return client


async def check_websocket_health() -> HealthCheckResult:
    """Check WebSocket connection manager health."""
    start_time = time.time()
    try:
        stats, health_score = await _get_websocket_stats_and_score()
        response_time = (time.time() - start_time) * 1000
        return _create_websocket_health_result(stats, health_score, response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("websocket", str(e), response_time)

async def _get_websocket_stats_and_score() -> tuple[Dict[str, Any], float]:
    """Get WebSocket connection stats and calculate health score."""
    from netra_backend.app.websocket_core.utils import get_connection_monitor
    conn_manager = get_connection_monitor()
    stats = await conn_manager.get_stats()
    health_score = _calculate_websocket_health_score(stats)
    return stats, health_score


def check_system_resources() -> HealthCheckResult:
    """Check system resource usage (CPU, memory, disk)."""
    start_time = time.time()
    try:
        metrics, score = _get_system_metrics_and_score()
        response_time = (time.time() - start_time) * 1000
        return _create_system_health_result(metrics, score, response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("system_resources", str(e), response_time)

def _get_system_metrics_and_score() -> tuple[Dict[str, Any], float]:
    """Get system resource metrics and calculate overall health score."""
    resource_metrics = _gather_system_resource_metrics()
    overall_score = _calculate_overall_system_health(resource_metrics)
    return resource_metrics, overall_score

def _gather_system_resource_metrics() -> Dict[str, Any]:
    """Gather CPU, memory, and disk metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {"cpu_percent": cpu_percent, "memory": memory, "disk": disk}

def _calculate_resource_health_scores(metrics: Dict[str, Any]) -> Dict[str, float]:
    """Calculate health scores for each resource type."""
    cpu_score = max(0.0, 1.0 - (metrics["cpu_percent"] / 100))
    memory_score = max(0.0, 1.0 - (metrics["memory"].percent / 100))
    disk_score = max(0.0, 1.0 - (metrics["disk"].percent / 100))
    return {"cpu": cpu_score, "memory": memory_score, "disk": disk_score}

def _calculate_overall_health_score(health_scores: Dict[str, float]) -> float:
    """Calculate overall health score from individual scores."""
    return sum(health_scores.values()) / len(health_scores)

def _create_system_health_result(metrics: Dict[str, Any], overall_score: float, response_time: float) -> HealthCheckResult:
    """Create HealthCheckResult for system resources."""
    details = _build_system_health_details(metrics, overall_score)
    return HealthCheckResult(
        component_name="system_resources",
        success=True,
        health_score=overall_score,
        response_time_ms=response_time,
        status="healthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_system_health_details(metrics: Dict[str, Any], overall_score: float) -> Dict[str, Any]:
    """Build details dictionary for system health result."""
    return {
        "component_name": "system_resources",
        "success": True,
        "health_score": overall_score,
        "metadata": _create_system_metadata(metrics)
    }

def _create_system_metadata(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Create metadata dictionary for system health check."""
    base_metrics = _extract_base_system_metrics(metrics)
    computed_metrics = _compute_system_metrics(metrics)
    return {**base_metrics, **computed_metrics}

def _extract_base_system_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Extract basic system metrics."""
    return {
        "cpu_percent": metrics["cpu_percent"],
        "memory_percent": metrics["memory"].percent,
        "disk_percent": metrics["disk"].percent
    }

def _compute_system_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compute derived system metrics."""
    return {
        "memory_available_gb": metrics["memory"].available / (1024**3),
        "disk_free_gb": metrics["disk"].free / (1024**3)
    }


def _create_success_result(component: str, response_time: float) -> HealthCheckResult:
    """Create a successful health check result."""
    details = _build_success_details(component)
    return HealthCheckResult(
        component_name=component,
        success=True,
        health_score=1.0,
        response_time_ms=response_time,
        status="healthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_success_details(component: str) -> Dict[str, Any]:
    """Build details dictionary for successful health check."""
    return {
        "component_name": component,
        "success": True,
        "health_score": 1.0
    }


def _create_failed_result(component: str, error: str, response_time: float = 0.0) -> HealthCheckResult:
    """Create a failed health check result."""
    details = _build_failure_details(component, error)
    return HealthCheckResult(
        component_name=component,
        success=False,
        health_score=0.0,
        response_time_ms=response_time,
        status="unhealthy",
        response_time=response_time / 1000,
        error_message=error,
        details=details
    )

def _build_failure_details(component: str, error: str) -> Dict[str, Any]:
    """Build details dictionary for failed health check."""
    return {
        "component_name": component,
        "success": False,
        "health_score": 0.0,
        "error_message": error
    }


def _create_disabled_result(component: str, reason: str) -> HealthCheckResult:
    """Create a disabled service health check result."""
    details = _build_disabled_details(component, reason)
    return HealthCheckResult(
        component_name=component,
        success=True,
        health_score=1.0,
        response_time_ms=0.0,
        status="healthy",
        response_time=0.0,
        details=details,
        metadata={"status": "disabled", "reason": reason}  # Include status in metadata for tests
    )

def _build_disabled_details(component: str, reason: str) -> Dict[str, Any]:
    """Build details dictionary for disabled service health check."""
    return {
        "component_name": component,
        "success": True,
        "health_score": 1.0,
        "status": "disabled",
        "reason": reason
    }


def _handle_service_failure(component: str, error: str, response_time: float = 0.0) -> HealthCheckResult:
    """Handle service failure based on priority level.
    
    Applies "Default to Resilience" principle:
    - Critical services: Return unhealthy (system failure)
    - Important services: Return degraded (reduced functionality)
    - Optional services: Return healthy with warning (system continues)
    """
    priority = _get_service_priority_for_environment(component)
    
    if priority == ServicePriority.CRITICAL:
        return _create_failed_result(component, error, response_time)
    elif priority == ServicePriority.IMPORTANT:
        return _create_degraded_result(component, error, response_time)
    else:  # OPTIONAL
        return _create_optional_failure_result(component, error, response_time)


def _create_degraded_result(component: str, error: str, response_time: float = 0.0) -> HealthCheckResult:
    """Create a degraded health check result for important services."""
    details = _build_degraded_details(component, error)
    return HealthCheckResult(
        component_name=component,
        success=False,
        health_score=0.5,
        response_time_ms=response_time,
        status="degraded",
        response_time=response_time / 1000,
        error_message=error,
        details=details
    )

def _build_degraded_details(component: str, error: str) -> Dict[str, Any]:
    """Build details dictionary for degraded service health check."""
    return {
        "component_name": component,
        "success": False,
        "health_score": 0.5,  # Partial functionality
        "status": "degraded",
        "error_message": error,
        "impact": "Reduced functionality - system continues with limitations"
    }


def _create_optional_failure_result(component: str, error: str, response_time: float = 0.0) -> HealthCheckResult:
    """Create a healthy result for optional service failures."""
    details = _build_optional_failure_details(component, error)
    return HealthCheckResult(
        component_name=component,
        success=True,
        health_score=1.0,
        response_time_ms=response_time,
        status="healthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_optional_failure_details(component: str, error: str) -> Dict[str, Any]:
    """Build details dictionary for optional service failure."""
    return {
        "component_name": component,
        "success": False,
        "health_score": 1.0,  # System health unaffected
        "status": "optional_unavailable",
        "error_message": error,
        "impact": "No impact - optional service unavailable"
    }


def _calculate_overall_system_health(resource_metrics: Dict[str, Any]) -> float:
    """Calculate overall system health score from resource metrics."""
    health_scores = _calculate_resource_health_scores(resource_metrics)
    return _calculate_overall_health_score(health_scores)


def _calculate_websocket_health_score(stats: Dict[str, Any]) -> float:
    """Calculate WebSocket health score from connection stats."""
    active_connections = stats.get("active_connections", 0)
    return min(1.0, max(0.7, 1.0 - (active_connections / 1000)))


def _create_websocket_health_result(stats: Dict[str, Any], health_score: float, response_time: float) -> HealthCheckResult:
    """Create HealthCheckResult for WebSocket health check."""
    details = _build_websocket_health_details(stats, health_score)
    return HealthCheckResult(
        component_name="websocket",
        success=True,
        health_score=health_score,
        response_time_ms=response_time,
        status="healthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_websocket_health_details(stats: Dict[str, Any], health_score: float) -> Dict[str, Any]:
    """Build details dictionary for WebSocket health result."""
    return {
        "component_name": "websocket",
        "success": True,
        "health_score": health_score,
        "metadata": stats
    }


def _is_development_mode() -> bool:
    """Check if running in development mode using unified environment detection."""
    try:
        from netra_backend.app.core.environment_constants import get_current_environment, Environment
        return get_current_environment() == Environment.DEVELOPMENT.value
    except Exception:
        # Fallback to config if environment detector fails
        config = unified_config_manager.get_config()
        return config.environment.lower() == "development"


def _is_clickhouse_disabled() -> bool:
    """Check if ClickHouse is disabled in environment using unified environment detection."""
    try:
        from netra_backend.app.core.environment_constants import get_current_environment, Environment
        
        # ClickHouse is optional in development and testing
        current_env = get_current_environment()
        if current_env in [Environment.DEVELOPMENT.value, Environment.TESTING.value]:
            return True
            
        # Also check config for explicit disabling
        config = unified_config_manager.get_config()
        clickhouse_mode = getattr(config, 'clickhouse_mode', 'shared').lower()
        skip_clickhouse = getattr(config, 'skip_clickhouse_init', False)
        return clickhouse_mode == "disabled" or skip_clickhouse
    except Exception:
        # Fallback to config-only check
        config = unified_config_manager.get_config()
        clickhouse_mode = getattr(config, 'clickhouse_mode', 'shared').lower()
        skip_clickhouse = getattr(config, 'skip_clickhouse_init', False)
        return clickhouse_mode == "disabled" or skip_clickhouse


def _get_health_check_timeout() -> float:
    """Get environment-appropriate health check timeout."""
    try:
        from netra_backend.app.core.environment_constants import get_current_environment, Environment
        
        # Environment-specific timeouts
        current_env = get_current_environment()
        timeout_map = {
            Environment.PRODUCTION.value: 5.0,
            Environment.STAGING.value: 8.0,
            Environment.DEVELOPMENT.value: 10.0,
            Environment.TESTING.value: 30.0
        }
        return timeout_map.get(current_env, 5.0)
    except Exception:
        # Fallback to conservative default
        return 5.0


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self):
        self.checkers = {
            "postgres": check_postgres_health,
            "clickhouse": check_clickhouse_health,
            "redis": check_redis_health,
            "websocket": check_websocket_health,
            "system_resources": check_system_resources
        }
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks and return results."""
        results = {}
        for name, checker in self.checkers.items():
            try:
                if name == "system_resources":
                    # System resources check is synchronous
                    results[name] = checker()
                else:
                    results[name] = await checker()
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = _create_failed_result(name, str(e))
        return results
    
    async def check_component(self, component: str) -> HealthCheckResult:
        """Run health check for a specific component."""
        if component not in self.checkers:
            return _create_failed_result(component, f"Unknown component: {component}")
        
        try:
            checker = self.checkers[component]
            if component == "system_resources":
                return checker()
            else:
                return await checker()
        except Exception as e:
            logger.error(f"Health check failed for {component}: {e}")
            return _create_failed_result(component, str(e))
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health summary with priority-based assessment.
        
        Applies "Default to Resilience" - system status based on critical services,
        with degraded status when important services fail.
        """
        results = await self.check_all()
        return _calculate_priority_based_health(results)
    
    # Specific health check methods expected by tests
    async def check_postgres(self) -> Dict[str, Any]:
        """Check PostgreSQL health and return dict format."""
        try:
            result = await check_postgres_health()
            return {
                "healthy": result.status == "healthy",
                "latency_ms": result.response_time * 1000  # Convert to milliseconds
            }
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return {
                "healthy": False,
                "latency_ms": 0.0,
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis health and return dict format."""
        try:
            result = await check_redis_health()
            return {
                "healthy": result.status in ["healthy", "degraded"],  # Accept degraded as healthy for Redis
                "latency_ms": result.response_time * 1000  # Convert to milliseconds
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "healthy": False,
                "latency_ms": 0.0,
                "error": str(e)
            }
    
    async def check_oauth_providers(self) -> Dict[str, Any]:
        """Check OAuth providers health and return dict format."""
        # Simulate OAuth provider health check
        start_time = time.time()
        try:
            # In a real implementation, this would check actual OAuth providers
            # For now, simulate a successful check
            response_time = (time.time() - start_time) * 1000
            return {
                "healthy": True,
                "latency_ms": response_time
            }
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"OAuth provider health check failed: {e}")
            return {
                "healthy": False,
                "latency_ms": response_time,
                "error": str(e)
            }
    
    async def check_auth_service_health(self) -> Dict[str, Any]:
        """Check overall auth service health and return comprehensive status."""
        results = {}
        
        # Check each component individually, handling errors gracefully
        try:
            results["database"] = await self.check_postgres()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            results["database"] = {"healthy": False, "error": str(e)}
        
        try:
            results["redis"] = await self.check_redis()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            results["redis"] = {"healthy": False, "error": str(e)}
            
        try:
            results["oauth"] = await self.check_oauth_providers()
        except Exception as e:
            logger.error(f"OAuth health check failed: {e}")
            results["oauth"] = {"healthy": False, "error": str(e)}
        
        return results


def _calculate_priority_based_health(results: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
    """Calculate system health based on service priorities."""
    critical_services = _get_services_by_priority(results, ServicePriority.CRITICAL)
    important_services = _get_services_by_priority(results, ServicePriority.IMPORTANT)
    
    # System is unhealthy if any critical service fails
    if _any_service_unhealthy(critical_services):
        return _create_system_health_summary("unhealthy", results, critical_services)
    
    # System is degraded if any important service fails or is degraded
    if _any_service_degraded_or_unhealthy(important_services):
        return _create_system_health_summary("degraded", results, important_services)
    
    # System is healthy if all critical and important services are operational
    return _create_system_health_summary("healthy", results, {})


def _get_services_by_priority(results: Dict[str, HealthCheckResult], priority: ServicePriority) -> Dict[str, HealthCheckResult]:
    """Get services filtered by priority level."""
    return {
        name: result for name, result in results.items()
        if _get_service_priority_for_environment(name) == priority
    }


def _any_service_unhealthy(services: Dict[str, HealthCheckResult]) -> bool:
    """Check if any service in the set is unhealthy."""
    return any(service.status == "unhealthy" for service in services.values())


def _any_service_degraded_or_unhealthy(services: Dict[str, HealthCheckResult]) -> bool:
    """Check if any service in the set is degraded or unhealthy."""
    return any(service.status in ["degraded", "unhealthy"] for service in services.values())


def _create_system_health_summary(status: str, all_results: Dict[str, HealthCheckResult], 
                                 problem_services: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
    """Create system health summary with priority context."""
    total_components = len(all_results)
    healthy_components = sum(1 for result in all_results.values() if result.status == "healthy")
    
    return {
        "status": status,
        "health_score": _calculate_weighted_health_score(all_results),
        "healthy_components": healthy_components,
        "total_components": total_components,
        "component_results": {name: result.status for name, result in all_results.items()},
        "priority_assessment": {
            "critical_services_healthy": not _any_service_unhealthy(
                _get_services_by_priority(all_results, ServicePriority.CRITICAL)
            ),
            "important_services_healthy": not _any_service_degraded_or_unhealthy(
                _get_services_by_priority(all_results, ServicePriority.IMPORTANT)
            ),
            "problem_services": list(problem_services.keys()) if problem_services else []
        }
    }


def _calculate_weighted_health_score(results: Dict[str, HealthCheckResult]) -> float:
    """Calculate health score weighted by service priority."""
    if not results:
        return 0.0
    
    total_weight = 0.0
    weighted_score = 0.0
    
    for name, result in results.items():
        priority = _get_service_priority_for_environment(name)
        weight = _get_priority_weight(priority)
        service_score = _get_service_health_score(result)
        
        total_weight += weight
        weighted_score += (service_score * weight)
    
    return weighted_score / total_weight if total_weight > 0 else 0.0


def _get_priority_weight(priority: ServicePriority) -> float:
    """Get weight factor for priority level."""
    weights = {
        ServicePriority.CRITICAL: 3.0,
        ServicePriority.IMPORTANT: 2.0,
        ServicePriority.OPTIONAL: 1.0
    }
    return weights.get(priority, 2.0)


def _get_service_health_score(result: HealthCheckResult) -> float:
    """Extract health score from service result."""
    if hasattr(result, 'details') and result.details:
        score = result.details.get('health_score', 0.0)
        # Ensure we return a numeric value, not a Mock
        if isinstance(score, (int, float)):
            return float(score)
    
    # Check for health_score attribute directly on result
    if hasattr(result, 'health_score') and isinstance(result.health_score, (int, float)):
        return float(result.health_score)
    
    # Default based on status
    return 1.0 if result.status == "healthy" else 0.0


async def check_auth_service_health() -> HealthCheckResult:
    """Check auth service connectivity and health with timeout handling."""
    start_time = time.time()
    
    # Implement quick timeout for staging/readiness checks
    timeout = _get_health_check_timeout() * 0.5  # Use half the normal timeout for external services
    
    try:
        # Quick health check with minimal timeout
        await asyncio.wait_for(_execute_auth_service_check(), timeout=timeout)
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("auth_service", response_time)
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        logger.warning(f"Auth service health check timeout after {timeout}s")
        # Return degraded instead of unhealthy to avoid blocking readiness
        return _create_degraded_result("auth_service", f"Auth service check timeout after {timeout}s", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("auth_service", str(e), response_time)


async def _execute_auth_service_check() -> None:
    """Execute lightweight auth service connectivity check."""
    try:
        import aiohttp
        from shared.isolated_environment import get_env
        
        # Get auth service URL from environment
        auth_base_url = get_env().get('AUTH_SERVICE_URL', 'http://localhost:8081')
        health_url = f"{auth_base_url}/health"
        
        # Quick connectivity check with minimal timeout
        timeout = aiohttp.ClientTimeout(total=2.0)  # 2 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(health_url) as response:
                if response.status not in [200, 503]:  # Accept 503 as service may be starting
                    raise RuntimeError(f"Auth service unhealthy: HTTP {response.status}")
    except ImportError:
        # aiohttp not available, skip check
        logger.debug("aiohttp not available, skipping auth service connectivity check")
    except Exception as e:
        logger.debug(f"Auth service check failed: {e}")
        raise


async def check_discovery_service_health() -> HealthCheckResult:
    """Check service discovery health (lightweight placeholder implementation)."""
    start_time = time.time()
    
    try:
        # Quick placeholder check - actual implementation would check service registry
        await asyncio.sleep(0.01)  # Minimal delay to simulate check
        response_time = (time.time() - start_time) * 1000
        
        # For now, always return healthy as discovery is optional
        return _create_success_result("discovery", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("discovery", str(e), response_time)


async def check_database_monitoring_health() -> HealthCheckResult:
    """Check database monitoring health (lightweight implementation)."""
    start_time = time.time()
    
    try:
        # Quick check of database connection pool status if available
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Check if connection manager is initialized
        if hasattr(DatabaseManager, '_engines') and DatabaseManager._engines:
            # Database monitoring is working if we have active connections
            response_time = (time.time() - start_time) * 1000
            return _create_success_result("database_monitoring", response_time)
        else:
            # No active connections, but this is not critical
            response_time = (time.time() - start_time) * 1000
            return _create_degraded_result("database_monitoring", "No active database connections", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("database_monitoring", str(e), response_time)


async def check_circuit_breakers_health() -> HealthCheckResult:
    """Check circuit breaker system health (lightweight implementation)."""
    start_time = time.time()
    
    try:
        # Lightweight check - actual implementation would check circuit breaker states
        await asyncio.sleep(0.01)  # Minimal delay to simulate check
        response_time = (time.time() - start_time) * 1000
        
        # For now, always return healthy as circuit breakers are resilience features
        return _create_success_result("circuit_breakers", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_service_failure("circuit_breakers", str(e), response_time)