"""
API Health Check Endpoint
=========================

Simple health check endpoint for /api/health route.
Provides backward compatibility with existing API routing.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def api_health():
    """API health check endpoint - returns 200 OK for healthy service."""
    return {"status": "ok"}


@router.get("/ready")
async def api_ready():
    """API readiness check - returns 200 OK for healthy service."""
    return {"status": "ok"}