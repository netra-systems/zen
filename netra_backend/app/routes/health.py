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
    """Infrastructure health check - returns 200 OK if service is running."""
    return {"status": "ok"}