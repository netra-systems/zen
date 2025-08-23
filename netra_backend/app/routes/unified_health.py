"""
Unified health check endpoints for the backend service.
Consolidates all health functionality into standardized endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from typing import Any, Dict, Optional

from netra_backend.app.services.health_registry import health_registry
from netra_backend.app.core.unified_logging import central_logger
from netra_backend.app.core.health_types import HealthStatus

logger = central_logger.get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def get_health(
    service: Optional[str] = Query(None, description="Specific service to check"),
    details: bool = Query(True, description="Include detailed information")
) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Returns overall system health with component details.
    """
    try:
        health_service = health_registry.get_service(service) if service else health_registry.get_default_service()
        if not health_service:
            # Return basic health if no service registered yet
            return {
                "status": "healthy",
                "service_name": "netra_backend",
                "version": "1.0.0",
                "message": "Service is running but health checks not configured"
            }
        
        response = await health_service.get_health(include_details=details)
        return response.to_dict()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service_name": "netra_backend"
        }


@router.get("/health/live")
async def get_liveness(
    response: Response,
    service: Optional[str] = Query(None, description="Specific service to check")
) -> Dict[str, Any]:
    """
    Liveness probe endpoint - is the service alive?
    
    Used by orchestrators to determine if the service should be restarted.
    """
    try:
        health_service = health_registry.get_service(service) if service else health_registry.get_default_service()
        if not health_service:
            # Service is alive even if health checks not configured
            return {
                "status": "healthy",
                "service_name": "netra_backend",
                "message": "Service is alive"
            }
        
        result = await health_service.get_liveness()
        response_data = result.to_dict()
        
        # Set appropriate HTTP status code
        if result.status == HealthStatus.UNHEALTHY.value:
            response.status_code = 503
        
        return response_data
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        response.status_code = 503
        return {
            "status": "unhealthy",
            "error": str(e),
            "service_name": "netra_backend"
        }


@router.get("/health/ready")
async def get_readiness(
    response: Response,
    service: Optional[str] = Query(None, description="Specific service to check")
) -> Dict[str, Any]:
    """
    Readiness probe endpoint - is the service ready to serve traffic?
    
    Used by orchestrators and load balancers to determine traffic routing.
    """
    try:
        health_service = health_registry.get_service(service) if service else health_registry.get_default_service()
        if not health_service:
            # Not ready if health checks not configured
            response.status_code = 503
            return {
                "status": "unhealthy",
                "service_name": "netra_backend",
                "message": "Service not ready - health checks not configured"
            }
        
        result = await health_service.get_readiness()
        response_data = result.to_dict()
        
        # Set appropriate HTTP status code
        if result.status == HealthStatus.UNHEALTHY.value:
            response.status_code = 503
        elif result.status == HealthStatus.DEGRADED.value:
            response.status_code = 207  # Multi-Status
        
        return response_data
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = 503
        return {
            "status": "unhealthy",
            "error": str(e),
            "service_name": "netra_backend"
        }


@router.get("/health/component/{component_name}")
async def get_component_health(
    component_name: str,
    response: Response,
    service: Optional[str] = Query(None, description="Specific service to check")
) -> Dict[str, Any]:
    """
    Individual component health check.
    
    Returns health status for a specific system component.
    """
    try:
        health_service = health_registry.get_service(service) if service else health_registry.get_default_service()
        if not health_service:
            raise HTTPException(status_code=404, detail="Health service not found")
        
        result = await health_service.run_check(component_name, force_refresh=True)
        
        # Set appropriate HTTP status code
        if result.status == HealthStatus.UNHEALTHY.value:
            response.status_code = 503
        elif result.status == HealthStatus.DEGRADED.value:
            response.status_code = 207
        
        return {
            "component": result.component_name,
            "status": result.status,
            "response_time_ms": result.response_time_ms,
            "message": result.message,
            "details": result.details,
            "labels": result.labels,
            "last_check": result.last_check
        }
    except Exception as e:
        logger.error(f"Component health check failed for {component_name}: {e}")
        response.status_code = 503
        return {
            "component": component_name,
            "status": "unhealthy",
            "error": str(e)
        }