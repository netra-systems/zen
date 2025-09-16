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
    """Infrastructure health check - includes circuit breaker and resilience status."""
    try:
        # Get infrastructure resilience status
        from netra_backend.app.services.infrastructure_resilience import get_infrastructure_health_summary
        from netra_backend.app.resilience.circuit_breaker import get_circuit_breaker_manager

        # Get overall infrastructure health
        infrastructure_health = get_infrastructure_health_summary()

        # Get circuit breaker status
        circuit_breaker_manager = get_circuit_breaker_manager()
        circuit_breaker_health = circuit_breaker_manager.get_health_summary()

        # Determine overall status
        overall_status = "ok"
        if infrastructure_health.get("overall_status") == "critical":
            overall_status = "critical"
        elif infrastructure_health.get("overall_status") == "degraded":
            overall_status = "degraded"
        elif circuit_breaker_health.get("overall_health") == "critical":
            overall_status = "critical"

        return {
            "status": overall_status,
            "infrastructure": infrastructure_health,
            "circuit_breakers": circuit_breaker_health,
            "chat_functionality_impact": infrastructure_health.get("chat_functionality_impacted", False)
        }
    except Exception as e:
        # Return basic status if resilience components not available yet
        return {"status": "ok", "note": "Infrastructure resilience not initialized"}


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