"""
Enhanced Database Health Check Endpoints
========================================

CRITICAL MISSION: Comprehensive database connectivity monitoring for staging.
Provides detailed health checks for PostgreSQL, Redis, ClickHouse with 
real-time connection validation, performance metrics, and error detection.

This module replaces basic health checks with comprehensive database
monitoring suitable for production staging environments.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Database connectivity monitoring
- Value Impact: Early detection of database issues prevents service outages
- Strategic Impact: Foundation for monitoring and alerting systems
"""

import asyncio
import os
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from netra_backend.app.auth_integration import get_current_user_optional
from netra_backend.app.logging_config import central_logger

# Import our comprehensive health check system
from netra_backend.app.api.health_checks import (
    health_manager,
    DatabaseHealthStatus,
    SystemHealthStatus
)

logger = central_logger.get_logger(__name__)
router = APIRouter()

# Track startup time
STARTUP_TIME = time.time()
STARTUP_COMPLETE = False


class HealthStatus(BaseModel):
    """Enhanced health check response model."""
    status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    timestamp: str = Field(..., description="Check timestamp")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    checks: Dict[str, Dict[str, Any]] = Field(..., description="Individual check results")
    database_details: Optional[Dict[str, Any]] = Field(None, description="Detailed database health information")
    version: Optional[str] = Field(None, description="Service version")
    environment: Optional[str] = Field(None, description="Environment name")


@router.get("/ready", response_model=HealthStatus)
@router.head("/ready", response_model=HealthStatus)
@router.options("/ready")
async def readiness_probe(
    user: Optional[Dict] = Depends(get_current_user_optional),
    force: bool = Query(False, description="Force fresh health checks")
) -> HealthStatus:
    """
    Enhanced readiness probe with comprehensive database health checks.
    
    Returns 200 if ready, 503 if critical services are failing.
    CRITICAL MISSION: Detect staging database connectivity issues.
    """
    try:
        # Get comprehensive system health
        system_health = await health_manager.check_overall_health(force_check=force)
        
        # Convert to legacy format for compatibility
        checks = {}
        database_details = {}
        
        for service_name, health_status in system_health.services.items():
            checks[service_name] = {
                "status": health_status.status,
                "connected": health_status.connected,
                "response_time_ms": health_status.response_time_ms,
                "error": health_status.error
            }
            
            # Add detailed information for databases
            database_details[service_name] = {
                "status": health_status.status,
                "details": health_status.details,
                "checked_at": health_status.checked_at.isoformat()
            }
        
        # Determine overall status and HTTP status code
        if system_health.overall_status == "failed":
            # Critical services failed - service not ready
            http_status = 503
            overall_status = "unhealthy"
        elif system_health.overall_status == "degraded":
            # Some services degraded but still functional
            http_status = 200
            overall_status = "degraded"
        else:
            # All services healthy
            http_status = 200
            overall_status = "healthy"
        
        uptime = time.time() - STARTUP_TIME
        
        health_response = HealthStatus(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=uptime,
            checks=checks,
            database_details=database_details,
            version="1.0.0",
            environment=health_manager.environment
        )
        
        if http_status == 503:
            raise HTTPException(status_code=503, detail=health_response.dict())
        
        return health_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        # Return unhealthy status
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Health check system failed: {str(e)}",
                "uptime_seconds": time.time() - STARTUP_TIME
            }
        )


@router.get("/live", response_model=HealthStatus)
@router.head("/live", response_model=HealthStatus) 
@router.options("/live")
async def liveness_probe(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> HealthStatus:
    """
    Liveness probe - basic application health check.
    
    Returns 200 if application is running, regardless of external dependencies.
    This endpoint should always return 200 unless the application is crashed.
    """
    uptime = time.time() - STARTUP_TIME
    
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=uptime,
        checks={
            "application": {
                "status": "healthy",
                "connected": True,
                "response_time_ms": 0,
                "error": None
            }
        },
        database_details={
            "liveness_check": {
                "status": "healthy", 
                "details": {"message": "Application is running"},
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        },
        version="1.0.0",
        environment=health_manager.environment
    )


@router.get("/startup", response_model=HealthStatus)
@router.head("/startup", response_model=HealthStatus)
@router.options("/startup") 
async def startup_probe(
    user: Optional[Dict] = Depends(get_current_user_optional),
    force: bool = Query(True, description="Force fresh checks for startup validation")
) -> HealthStatus:
    """
    Startup probe - comprehensive startup validation.
    
    Returns 200 when startup is complete and all critical systems are ready.
    Returns 503 if startup is still in progress or failed.
    CRITICAL MISSION: Validate staging database connectivity during startup.
    """
    try:
        # Force comprehensive health checks for startup validation
        system_health = await health_manager.check_overall_health(force_check=force)
        
        # For startup, we're more strict about what's considered "ready"
        startup_ready = True
        startup_issues = []
        
        # Check each service
        for service_name, health_status in system_health.services.items():
            if health_status.status == "failed":
                # Determine if this service is critical for startup
                if service_name == "postgresql":
                    startup_ready = False
                    startup_issues.append(f"Critical service {service_name} failed: {health_status.error}")
                elif service_name == "redis" and health_manager.env.get("REDIS_REQUIRED", "false").lower() == "true":
                    startup_ready = False
                    startup_issues.append(f"Required service {service_name} failed: {health_status.error}")
                elif service_name == "clickhouse" and health_manager.env.get("CLICKHOUSE_REQUIRED", "false").lower() == "true":
                    startup_ready = False
                    startup_issues.append(f"Required service {service_name} failed: {health_status.error}")
        
        # Build response
        checks = {}
        database_details = {}
        
        for service_name, health_status in system_health.services.items():
            checks[service_name] = {
                "status": health_status.status,
                "connected": health_status.connected,
                "response_time_ms": health_status.response_time_ms,
                "error": health_status.error
            }
            
            database_details[service_name] = {
                "status": health_status.status,
                "details": health_status.details,
                "checked_at": health_status.checked_at.isoformat()
            }
        
        # Add startup-specific information
        checks["startup"] = {
            "status": "healthy" if startup_ready else "failed",
            "connected": startup_ready,
            "response_time_ms": None,
            "error": "; ".join(startup_issues) if startup_issues else None
        }
        
        database_details["startup_validation"] = {
            "status": "ready" if startup_ready else "not_ready",
            "details": {
                "startup_complete": startup_ready,
                "startup_issues": startup_issues,
                "critical_services_checked": ["postgresql", "redis", "clickhouse"]
            },
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
        uptime = time.time() - STARTUP_TIME
        overall_status = "healthy" if startup_ready else "unhealthy"
        
        health_response = HealthStatus(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=uptime,
            checks=checks,
            database_details=database_details,
            version="1.0.0",
            environment=health_manager.environment
        )
        
        if not startup_ready:
            # Mark global startup as incomplete
            global STARTUP_COMPLETE
            STARTUP_COMPLETE = False
            raise HTTPException(status_code=503, detail=health_response.dict())
        else:
            # Mark global startup as complete
            STARTUP_COMPLETE = True
        
        return health_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Startup probe failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy", 
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Startup validation failed: {str(e)}",
                "uptime_seconds": time.time() - STARTUP_TIME
            }
        )


# Additional endpoints for comprehensive database monitoring
@router.get("/database", response_model=Dict[str, Any])
async def database_health_detailed(
    force: bool = Query(False, description="Force fresh health checks"),
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Detailed database health information.
    
    CRITICAL MISSION: Comprehensive database connectivity monitoring for staging.
    Returns detailed information about all database services.
    """
    try:
        # Get individual database health checks
        postgresql_health = await health_manager.check_postgresql_health(force_check=force)
        redis_health = await health_manager.check_redis_health(force_check=force)  
        clickhouse_health = await health_manager.check_clickhouse_health(force_check=force)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": health_manager.environment,
            "databases": {
                "postgresql": postgresql_health.dict(),
                "redis": redis_health.dict(),
                "clickhouse": clickhouse_health.dict()
            },
            "summary": {
                "total_databases": 3,
                "healthy_count": sum(1 for health in [postgresql_health, redis_health, clickhouse_health] 
                                   if health.status == "healthy"),
                "degraded_count": sum(1 for health in [postgresql_health, redis_health, clickhouse_health] 
                                    if health.status == "degraded"), 
                "failed_count": sum(1 for health in [postgresql_health, redis_health, clickhouse_health] 
                                  if health.status == "failed"),
                "not_configured_count": sum(1 for health in [postgresql_health, redis_health, clickhouse_health] 
                                          if health.status == "not_configured")
            }
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database health check failed: {str(e)}"
        )


@router.get("/config", response_model=Dict[str, Any])
async def health_configuration(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Health check system configuration and diagnostics.
    
    Returns information about health check configuration,
    environment setup, and system diagnostics.
    """
    try:
        # Get basic configuration info
        config_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": health_manager.environment,
            "health_system": {
                "cache_ttl_seconds": health_manager._cache_ttl,
                "max_response_samples": health_manager._max_samples,
                "startup_time": STARTUP_TIME,
                "startup_complete": STARTUP_COMPLETE,
                "uptime_seconds": time.time() - STARTUP_TIME
            },
            "services_configured": {},
            "environment_variables": {},
            "endpoints": [
                "/ready - Readiness probe with database health",
                "/live - Liveness probe (basic)",
                "/startup - Startup validation",
                "/database - Detailed database health",
                "/config - This configuration endpoint"
            ]
        }
        
        # Check which services are configured
        env_dict = health_manager.env.as_dict()
        config_info["services_configured"] = {
            "postgresql": bool(env_dict.get("POSTGRES_HOST") or env_dict.get("DATABASE_URL")),
            "redis": bool(env_dict.get("REDIS_HOST") or env_dict.get("REDIS_URL")),
            "clickhouse": bool(env_dict.get("CLICKHOUSE_HOST") or env_dict.get("CLICKHOUSE_URL"))
        }
        
        # Add relevant (non-sensitive) environment variables
        config_info["environment_variables"] = {
            "ENVIRONMENT": env_dict.get("ENVIRONMENT", "unknown"),
            "REDIS_REQUIRED": env_dict.get("REDIS_REQUIRED", "false"),
            "CLICKHOUSE_REQUIRED": env_dict.get("CLICKHOUSE_REQUIRED", "false"),
            "POSTGRES_PORT": env_dict.get("POSTGRES_PORT", "5432"),
            "REDIS_PORT": env_dict.get("REDIS_PORT", "6379"),
            "CLICKHOUSE_PORT": env_dict.get("CLICKHOUSE_PORT", "8123")
        }
        
        return config_info
        
    except Exception as e:
        logger.error(f"Health configuration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health configuration failed: {str(e)}"
        )


# Legacy compatibility endpoints
@router.get("/", response_model=HealthStatus)
async def health_root(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> HealthStatus:
    """Root health endpoint - redirects to readiness probe."""
    return await readiness_probe(user=user, force=False)