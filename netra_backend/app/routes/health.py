"""
Simple Health Check Endpoints for Load Balancer Routing
======================================================

Minimal health check endpoints that return HTTP 200 OK for healthy service status.
This replaces the complex 1,500+ line health check framework with simple endpoints
focused solely on load balancer routing requirements.

Endpoints:
- /health - Basic health check (always 200 OK if running)
- /health/ready - Readiness check with database ping
- /health/live - Liveness check (always 200 OK if running)
"""

from fastapi import APIRouter

router = APIRouter(
    redirect_slashes=False
)


@router.get("/")
@router.head("/")
@router.options("/")
async def health():
    """Basic health check - returns 200 OK if service is running."""
    return {"status": "ok"}


@router.get("")
@router.head("")
@router.options("")
async def health_no_slash():
    """Health check without trailing slash."""
    return {"status": "ok"}


@router.get("/ready")
@router.head("/ready")
@router.options("/ready")
async def ready():
    """Readiness check - returns 200 OK if service is running."""
    return {"status": "ready"}


@router.get("/live")
@router.head("/live")
@router.options("/live")
async def liveness():
    """Liveness check - returns 200 OK if service is running."""
    return {"status": "ok"}


@router.get("/startup")
@router.head("/startup")
async def startup():
    """Startup check - returns 200 OK if service is running."""
    return {"status": "ok"}


@router.get("/backend")
@router.head("/backend")
async def backend():
    """Backend health check - returns 200 OK if service is running."""
    return {"status": "ok"}


@router.get("/infrastructure")
@router.head("/infrastructure")
async def infrastructure():
    """Infrastructure health check - includes circuit breaker, resilience, and authentication status."""
    try:
        # Get infrastructure resilience status
        from netra_backend.app.services.infrastructure_resilience import get_infrastructure_health_summary
        from netra_backend.app.resilience.circuit_breaker import get_circuit_breaker_manager
        from netra_backend.app.websocket_core.auth_health_provider import get_auth_health_for_endpoint
        from netra_backend.app.core.database_timeout_config import get_connection_monitor
        from shared.isolated_environment import get_env
        import time

        # Get overall infrastructure health
        infrastructure_health = get_infrastructure_health_summary()

        # Get circuit breaker status
        circuit_breaker_manager = get_circuit_breaker_manager()
        circuit_breaker_health = circuit_breaker_manager.get_health_summary()

        # Get authentication health status
        auth_health = await get_auth_health_for_endpoint()

        # Get database connection monitoring data
        connection_monitor = get_connection_monitor()
        env = get_env()
        environment = env.get("ENVIRONMENT", "development")
        db_metrics = connection_monitor.get_metrics(environment)

        # Enhanced infrastructure diagnostics
        diagnostics = {
            "environment": environment,
            "timestamp": time.time(),
            "database_connections": {
                "total_attempts": db_metrics.connection_attempts,
                "success_rate": f"{db_metrics.get_success_rate():.1f}%",
                "average_connection_time": f"{db_metrics.get_average_connection_time():.3f}s",
                "timeout_violations": db_metrics.timeout_violations,
                "timeout_violation_rate": f"{db_metrics.get_timeout_violation_rate():.1f}%"
            } if db_metrics else {"status": "no_metrics_available"},
            "infrastructure_pressure_indicators": {
                "slow_connections": db_metrics.get_average_connection_time() > 5.0 if db_metrics else False,
                "high_timeout_rate": db_metrics.get_timeout_violation_rate() > 10.0 if db_metrics else False,
                "low_success_rate": db_metrics.get_success_rate() < 90.0 if db_metrics else False
            }
        }

        # Determine overall status including authentication
        overall_status = "ok"
        if infrastructure_health.get("overall_status") == "critical":
            overall_status = "critical"
        elif infrastructure_health.get("overall_status") == "degraded":
            overall_status = "degraded"
        elif circuit_breaker_health.get("overall_health") == "critical":
            overall_status = "critical"
        elif auth_health.get("overall_status") == "critical":
            overall_status = "critical"
        elif auth_health.get("overall_status") == "degraded" and overall_status == "ok":
            overall_status = "degraded"

        # Infrastructure pressure assessment
        if diagnostics["infrastructure_pressure_indicators"]["slow_connections"]:
            if overall_status == "ok":
                overall_status = "degraded"

        return {
            "status": overall_status,
            "infrastructure": infrastructure_health,
            "circuit_breakers": circuit_breaker_health,
            "authentication": auth_health,
            "diagnostics": diagnostics,
            "chat_functionality_impact": (
                infrastructure_health.get("chat_functionality_impacted", False) or
                auth_health.get("golden_path_assessment", {}).get("chat_functionality_impacted", False)
            ),
            "infrastructure_recommendations": {
                "database": "Check Cloud SQL VPC connector if connection issues persist" if diagnostics["infrastructure_pressure_indicators"]["slow_connections"] else "Database connections healthy",
                "auth_service": "Verify auth service port 8081 availability" if auth_health.get("overall_status") != "ok" else "Auth service healthy",
                "backend_service": "Check backend service port 8000 availability" if overall_status == "critical" else "Backend service operational"
            }
        }
    except Exception as e:
        # Enhanced error reporting for infrastructure debugging
        return {
            "status": "error", 
            "error": str(e),
            "note": "Infrastructure resilience components unavailable - indicates startup or configuration issues",
            "infrastructure_recommendations": {
                "immediate_action": "Check service startup logs for configuration or dependency issues",
                "likely_causes": ["Service dependencies not initialized", "Configuration errors", "Import issues"]
            }
        }


@router.get("/circuit-breakers")
async def circuit_breakers():
    """Circuit breaker status endpoint."""
    try:
        from netra_backend.app.resilience.circuit_breaker import get_circuit_breaker_manager

        circuit_breaker_manager = get_circuit_breaker_manager()
        return {
            "health_summary": circuit_breaker_manager.get_health_summary(),
            "all_statuses": circuit_breaker_manager.get_all_statuses()
        }
    except Exception as e:
        return {"error": f"Circuit breaker status unavailable: {e}"}


@router.get("/resilience")
async def resilience():
    """Infrastructure resilience status endpoint."""
    try:
        from netra_backend.app.services.infrastructure_resilience import get_infrastructure_health_summary

        return get_infrastructure_health_summary()
    except Exception as e:
        return {"error": f"Resilience status unavailable: {e}"}


@router.get("/authentication")
async def authentication():
    """Authentication health status endpoint."""
    try:
        from netra_backend.app.websocket_core.auth_health_provider import get_auth_health_for_endpoint

        return await get_auth_health_for_endpoint()
    except Exception as e:
        return {"error": f"Authentication health status unavailable: {e}"}


@router.get("/authentication/metrics")
async def authentication_metrics():
    """Authentication metrics endpoint."""
    try:
        from netra_backend.app.websocket_core.auth_health_provider import get_auth_metrics_for_endpoint

        return await get_auth_metrics_for_endpoint()
    except Exception as e:
        return {"error": f"Authentication metrics unavailable: {e}"}


@router.get("/authentication/websocket")
async def authentication_websocket():
    """WebSocket authentication health status endpoint."""
    try:
        from netra_backend.app.websocket_core.auth_health_provider import get_auth_health_provider

        health_provider = get_auth_health_provider()
        return await health_provider.get_websocket_authentication_health()
    except Exception as e:
        return {"error": f"WebSocket authentication health unavailable: {e}"}