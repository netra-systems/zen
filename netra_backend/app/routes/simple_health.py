"""
Simple Health Check Endpoints
============================

Minimal health check endpoints for load balancer routing.
Returns HTTP 200 OK for healthy service status.

This replaces the complex 1,500+ line health check framework with simple endpoints
focused solely on load balancer routing requirements.
"""

from fastapi import APIRouter, Response
from netra_backend.app.db.database_manager import get_database_manager

router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check - always returns 200 OK if service is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    """Readiness check with basic database connectivity test."""
    try:
        db_manager = get_database_manager()
        await db_manager.execute_query("SELECT 1")
        return {"status": "ready"}
    except Exception:
        # Return 503 Service Unavailable if database is not accessible
        return Response(status_code=503, content='{"status": "not_ready"}')


@router.get("/live")
async def liveness():
    """Liveness check - always returns 200 OK if service is running."""
    return {"status": "ok"}