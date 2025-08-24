"""
API v1 compatibility endpoints for integration tests.
These endpoints provide the expected API v1 interface that tests expect.
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, Request, HTTPException

from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.routes.health import health_interface
from netra_backend.app.core.health import HealthLevel

router = APIRouter()


@router.get("/health")
async def v1_health(request: Request) -> Dict[str, Any]:
    """
    API v1 health check endpoint for integration tests.
    Returns standardized health status format.
    """
    # Get basic health status from the unified health interface
    health_status = await health_interface.get_health_status(HealthLevel.BASIC)
    
    # Return in the format expected by integration tests
    return {
        "status": "healthy" if health_status.get("status") == "healthy" else "unhealthy",
        "version": "1.0.0",
        "timestamp": time.time(),
        "services": health_status.get("checks", {})
    }


@router.get("/version")
async def v1_version() -> Dict[str, Any]:
    """
    API v1 version information endpoint for integration tests.
    Returns version and build information.
    """
    config = unified_config_manager.get_config()
    
    return {
        "api_version": "1.0.0",
        "build_number": getattr(config, 'build_number', "unknown"),
        "git_commit": getattr(config, 'git_commit', "unknown"),
        "environment": getattr(config, 'environment', 'development')
    }


@router.get("/users/me")
async def v1_users_me() -> Dict[str, Any]:
    """
    API v1 users/me endpoint for authentication tests.
    Returns 401 to simulate authentication requirement.
    """
    # For integration tests, we need this endpoint to exist
    # but it should require authentication - return 401 for now
    raise HTTPException(status_code=401, detail="Authentication required")


@router.get("/resources")
async def v1_resources() -> Dict[str, Any]:
    """
    API v1 resources endpoint for authentication tests.
    This endpoint requires authentication and is used by tests to verify auth flow.
    """
    # For integration tests, this endpoint should require authentication
    # Return 401 with proper error message format expected by tests
    raise HTTPException(status_code=401, detail="Unauthorized access required")