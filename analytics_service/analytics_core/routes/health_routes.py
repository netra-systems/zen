"""
Analytics Service Health Check Routes
Comprehensive health monitoring for ClickHouse, Redis, and service components
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from analytics_service.analytics_core.config import AnalyticsConfig
from analytics_service.analytics_core.isolated_environment import get_env
from analytics_service.analytics_core.database.connection import (
    get_clickhouse_session,
    get_redis_connection,
    ClickHouseHealthChecker,
    RedisHealthChecker
)
from analytics_service.analytics_core.services.health_service import HealthService
from analytics_service.analytics_core.utils.system_monitor import SystemMonitor
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["health"])

# Initialize health service
health_service = HealthService()
system_monitor = SystemMonitor()

# Health Response Models
class ComponentHealth(BaseModel):
    """Individual component health status"""
    name: str
    status: str  # "healthy", "unhealthy", "degraded", "unknown"
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    last_check: datetime
    details: Dict[str, Any] = {}

class HealthResponse(BaseModel):
    """Main health check response"""
    status: str  # "healthy", "unhealthy", "degraded" 
    service: str = "analytics-service"
    version: str = "1.0.0"
    environment: str
    timestamp: datetime
    uptime_seconds: float
    components: List[ComponentHealth]
    system_metrics: Dict[str, Any] = {}

class ReadinessResponse(BaseModel):
    """Readiness probe response"""
    ready: bool
    service: str = "analytics-service"
    timestamp: datetime
    environment: str
    dependencies: Dict[str, bool]
    initialization_status: Dict[str, Any]

class LivenessResponse(BaseModel):
    """Liveness probe response"""  
    alive: bool
    service: str = "analytics-service"
    timestamp: datetime
    process_info: Dict[str, Any]


def _create_error_response(status_code: int, response_data: Dict[str, Any]) -> Response:
    """Create a JSON error response with proper status code."""
    return Response(
        content=json.dumps(response_data),
        status_code=status_code,
        media_type="application/json"
    )


async def _check_clickhouse_health() -> ComponentHealth:
    """Check ClickHouse database health with timeout protection."""
    start_time = time.time()
    
    try:
        config = AnalyticsConfig.get_instance()
        
        # Skip ClickHouse in environments where it's not available
        if config.environment == "staging" and not config.clickhouse_required:
            logger.info("ClickHouse check skipped in staging environment (optional service)")
            return ComponentHealth(
                name="clickhouse",
                status="skipped",
                last_check=datetime.now(timezone.utc),
                details={"reason": "Optional service in staging environment"}
            )
        
        # Set timeout based on environment
        timeout = 3.0 if config.environment in ["staging", "development"] else 8.0
        
        health_checker = ClickHouseHealthChecker()
        
        try:
            # Perform health check with timeout
            health_result = await asyncio.wait_for(
                health_checker.check_health(),
                timeout=timeout
            )
            
            latency = (time.time() - start_time) * 1000
            
            if health_result["healthy"]:
                return ComponentHealth(
                    name="clickhouse",
                    status="healthy",
                    latency_ms=latency,
                    last_check=datetime.now(timezone.utc),
                    details=health_result.get("details", {})
                )
            else:
                return ComponentHealth(
                    name="clickhouse",
                    status="unhealthy",
                    latency_ms=latency,
                    error_message=health_result.get("error", "Health check failed"),
                    last_check=datetime.now(timezone.utc),
                    details=health_result.get("details", {})
                )
                
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="clickhouse",
                status="unhealthy",
                error_message=f"Health check timeout after {timeout}s",
                last_check=datetime.now(timezone.utc),
                details={"timeout_seconds": timeout}
            )
            
    except Exception as e:
        logger.error(f"ClickHouse health check failed: {e}")
        
        # Graceful degradation for optional environments
        config = AnalyticsConfig.get_instance()
        if config.environment in ["staging", "development"] and not config.clickhouse_required:
            return ComponentHealth(
                name="clickhouse",
                status="degraded",
                error_message=f"Optional service unavailable: {str(e)}",
                last_check=datetime.now(timezone.utc),
                details={"optional": True}
            )
        
        return ComponentHealth(
            name="clickhouse",
            status="unhealthy",
            error_message=str(e),
            last_check=datetime.now(timezone.utc)
        )


async def _check_redis_health() -> ComponentHealth:
    """Check Redis connection health with timeout protection."""
    start_time = time.time()
    
    try:
        config = AnalyticsConfig.get_instance()
        
        # Skip Redis in environments where it's not available  
        if config.environment == "staging" and not config.redis_required:
            logger.info("Redis check skipped in staging environment (optional service)")
            return ComponentHealth(
                name="redis",
                status="skipped",
                last_check=datetime.now(timezone.utc),
                details={"reason": "Optional service in staging environment"}
            )
        
        # Set timeout based on environment
        timeout = 2.0 if config.environment in ["staging", "development"] else 5.0
        
        health_checker = RedisHealthChecker()
        
        try:
            # Perform health check with timeout
            health_result = await asyncio.wait_for(
                health_checker.check_health(),
                timeout=timeout
            )
            
            latency = (time.time() - start_time) * 1000
            
            if health_result["healthy"]:
                return ComponentHealth(
                    name="redis",
                    status="healthy",
                    latency_ms=latency,
                    last_check=datetime.now(timezone.utc),
                    details=health_result.get("details", {})
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status="unhealthy",
                    latency_ms=latency,
                    error_message=health_result.get("error", "Health check failed"),
                    last_check=datetime.now(timezone.utc),
                    details=health_result.get("details", {})
                )
                
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="redis",
                status="unhealthy", 
                error_message=f"Health check timeout after {timeout}s",
                last_check=datetime.now(timezone.utc),
                details={"timeout_seconds": timeout}
            )
            
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        
        # Graceful degradation for optional environments
        config = AnalyticsConfig.get_instance()
        if config.environment in ["staging", "development"] and not config.redis_required:
            return ComponentHealth(
                name="redis",
                status="degraded",
                error_message=f"Optional service unavailable: {str(e)}",
                last_check=datetime.now(timezone.utc),
                details={"optional": True}
            )
        
        return ComponentHealth(
            name="redis",
            status="unhealthy",
            error_message=str(e),
            last_check=datetime.now(timezone.utc)
        )


async def _check_service_components() -> List[ComponentHealth]:
    """Check internal service component health."""
    components = []
    
    # Event ingestion service
    try:
        ingestion_health = await health_service.check_event_ingestion_health()
        components.append(ComponentHealth(
            name="event_ingestion",
            status="healthy" if ingestion_health["healthy"] else "unhealthy",
            last_check=datetime.now(timezone.utc),
            details=ingestion_health.get("details", {})
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="event_ingestion",
            status="unhealthy",
            error_message=str(e),
            last_check=datetime.now(timezone.utc)
        ))
    
    # Analytics processing service
    try:
        analytics_health = await health_service.check_analytics_processing_health()
        components.append(ComponentHealth(
            name="analytics_processing",
            status="healthy" if analytics_health["healthy"] else "unhealthy",
            last_check=datetime.now(timezone.utc),
            details=analytics_health.get("details", {})
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="analytics_processing",
            status="unhealthy",
            error_message=str(e),
            last_check=datetime.now(timezone.utc)
        ))
    
    # Metrics service
    try:
        metrics_health = await health_service.check_metrics_service_health()
        components.append(ComponentHealth(
            name="metrics_service",
            status="healthy" if metrics_health["healthy"] else "unhealthy",
            last_check=datetime.now(timezone.utc),
            details=metrics_health.get("details", {})
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="metrics_service",
            status="unhealthy",
            error_message=str(e),
            last_check=datetime.now(timezone.utc)
        ))
    
    return components


def _determine_overall_status(components: List[ComponentHealth]) -> str:
    """Determine overall service status from component health."""
    if not components:
        return "unknown"
    
    healthy_count = 0
    unhealthy_count = 0
    degraded_count = 0
    
    for component in components:
        if component.status == "healthy":
            healthy_count += 1
        elif component.status == "unhealthy":
            unhealthy_count += 1
        elif component.status in ["degraded", "skipped"]:
            degraded_count += 1
    
    # If any critical components are unhealthy, overall status is unhealthy
    critical_components = ["event_ingestion", "analytics_processing"]
    for component in components:
        if component.name in critical_components and component.status == "unhealthy":
            return "unhealthy"
    
    # If all components are healthy, overall status is healthy
    if unhealthy_count == 0:
        return "healthy"
    
    # If some components are degraded but none are unhealthy, status is degraded
    if unhealthy_count == 0 and degraded_count > 0:
        return "degraded"
    
    # Otherwise, status is unhealthy
    return "unhealthy"


@router.get("/health", response_model=HealthResponse)
@router.head("/health", response_model=HealthResponse)
@router.options("/health")
async def comprehensive_health_check(request: Request, response: Response) -> HealthResponse:
    """
    Comprehensive health check endpoint.
    
    Checks all critical components: ClickHouse, Redis, and internal services.
    Returns detailed health information for monitoring and debugging.
    """
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return {"status": "ok", "message": "CORS preflight"}
    
    start_time = time.time()
    config = AnalyticsConfig.get_instance()
    
    try:
        # Check all components in parallel for better performance
        clickhouse_task = asyncio.create_task(_check_clickhouse_health())
        redis_task = asyncio.create_task(_check_redis_health())
        services_task = asyncio.create_task(_check_service_components())
        
        # Wait for all health checks with timeout
        try:
            clickhouse_health, redis_health, service_components = await asyncio.wait_for(
                asyncio.gather(clickhouse_task, redis_task, services_task),
                timeout=15.0  # Overall timeout for all checks
            )
        except asyncio.TimeoutError:
            logger.error("Health check exceeded 15 second timeout")
            return _create_error_response(503, {
                "status": "unhealthy",
                "message": "Health check timeout",
                "timeout_seconds": 15
            })
        
        # Combine all component results
        all_components = [clickhouse_health, redis_health] + service_components
        
        # Determine overall status
        overall_status = _determine_overall_status(all_components)
        
        # Get system metrics
        system_metrics = await system_monitor.get_system_metrics()
        
        # Calculate uptime
        uptime_seconds = health_service.get_uptime_seconds()
        
        health_response = HealthResponse(
            status=overall_status,
            environment=config.environment,
            timestamp=datetime.now(timezone.utc),
            uptime_seconds=uptime_seconds,
            components=all_components,
            system_metrics=system_metrics
        )
        
        # Set HTTP status code based on health
        if overall_status == "unhealthy":
            response.status_code = 503
        elif overall_status == "degraded":
            response.status_code = 200  # Still operational but degraded
        else:
            response.status_code = 200
        
        # Add API version header
        requested_version = request.headers.get("Accept-Version") or request.headers.get("API-Version", "current")
        response.headers["API-Version"] = requested_version
        
        return health_response
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return _create_error_response(500, {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "service": "analytics-service"
        })


@router.get("/health/ready", response_model=ReadinessResponse)
@router.head("/health/ready", response_model=ReadinessResponse)
@router.options("/health/ready")
async def readiness_probe(request: Request) -> ReadinessResponse:
    """
    Kubernetes readiness probe.
    
    Checks if the service is ready to accept requests.
    Verifies that all critical dependencies are available.
    """
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return {"status": "ok", "message": "CORS preflight"}
    
    config = AnalyticsConfig.get_instance()
    
    try:
        # Quick dependency checks (faster than full health check)
        dependencies = {}
        
        # ClickHouse readiness
        try:
            clickhouse_checker = ClickHouseHealthChecker()
            clickhouse_result = await asyncio.wait_for(
                clickhouse_checker.check_connectivity(),
                timeout=3.0
            )
            dependencies["clickhouse"] = clickhouse_result
        except Exception:
            dependencies["clickhouse"] = False
        
        # Redis readiness
        try:
            redis_checker = RedisHealthChecker()
            redis_result = await asyncio.wait_for(
                redis_checker.check_connectivity(),
                timeout=2.0
            )
            dependencies["redis"] = redis_result
        except Exception:
            dependencies["redis"] = False
        
        # Check initialization status
        initialization_status = await health_service.get_initialization_status()
        
        # Determine readiness
        critical_deps = ["clickhouse"] if config.clickhouse_required else []
        if config.redis_required:
            critical_deps.append("redis")
        
        ready = all(dependencies.get(dep, False) for dep in critical_deps)
        ready = ready and initialization_status.get("initialized", False)
        
        readiness_response = ReadinessResponse(
            ready=ready,
            timestamp=datetime.now(timezone.utc),
            environment=config.environment,
            dependencies=dependencies,
            initialization_status=initialization_status
        )
        
        # Return 503 if not ready
        if not ready:
            return _create_error_response(503, readiness_response.model_dump())
        
        return readiness_response
        
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}", exc_info=True)
        return _create_error_response(503, {
            "ready": False,
            "service": "analytics-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        })


@router.get("/health/live", response_model=LivenessResponse)
@router.head("/health/live", response_model=LivenessResponse)
@router.options("/health/live")
async def liveness_probe(request: Request) -> LivenessResponse:
    """
    Kubernetes liveness probe.
    
    Simple check to verify the service process is alive and responsive.
    Should not depend on external dependencies.
    """
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return {"status": "ok", "message": "CORS preflight"}
    
    config = AnalyticsConfig.get_instance()
    
    try:
        # Get basic process information
        process_info = await system_monitor.get_process_info()
        
        return LivenessResponse(
            alive=True,
            timestamp=datetime.now(timezone.utc),
            process_info=process_info
        )
        
    except Exception as e:
        logger.error(f"Liveness probe failed: {e}", exc_info=True)
        return _create_error_response(500, {
            "alive": False,
            "service": "analytics-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        })


@router.get("/health/components/{component_name}")
async def get_component_health(component_name: str):
    """
    Get detailed health information for a specific component.
    
    Useful for debugging specific component issues.
    """
    try:
        if component_name == "clickhouse":
            health_info = await _check_clickhouse_health()
        elif component_name == "redis":
            health_info = await _check_redis_health()
        elif component_name in ["event_ingestion", "analytics_processing", "metrics_service"]:
            service_components = await _check_service_components()
            health_info = next(
                (comp for comp in service_components if comp.name == component_name), 
                None
            )
            if not health_info:
                raise HTTPException(status_code=404, detail=f"Component {component_name} not found")
        else:
            raise HTTPException(status_code=404, detail=f"Unknown component: {component_name}")
        
        return health_info.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Component health check failed for {component_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Component health check failed: {str(e)}"
        )


@router.get("/health/diagnostics")
async def get_health_diagnostics():
    """
    Get detailed diagnostics information for troubleshooting.
    
    Only available in development and staging environments for security.
    """
    config = AnalyticsConfig.get_instance()
    
    # Restrict to non-production environments
    if config.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="Diagnostics endpoint not available in production"
        )
    
    try:
        # Gather comprehensive diagnostics
        diagnostics = {
            "service": "analytics-service",
            "environment": config.environment,
            "timestamp": datetime.now(timezone.utc),
            "configuration": {
                "clickhouse_enabled": config.clickhouse_enabled,
                "redis_enabled": config.redis_enabled,
                "data_retention_days": config.data_retention_days,
                "max_events_per_batch": config.max_events_per_batch
            },
            "system_info": await system_monitor.get_detailed_system_info(),
            "connection_pools": await health_service.get_connection_pool_stats(),
            "performance_metrics": await health_service.get_performance_metrics(),
            "recent_errors": await health_service.get_recent_errors(limit=10)
        }
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"Diagnostics collection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Diagnostics collection failed: {str(e)}"
        )