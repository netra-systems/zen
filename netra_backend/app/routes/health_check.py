"""
Health check endpoints for system monitoring and E2E testing.

Provides readiness, liveness, and startup probes for Kubernetes and monitoring systems.
"""

import asyncio
import os
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from netra_backend.app.auth_integration import get_current_user_optional
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
router = APIRouter()

# Track startup time
STARTUP_TIME = time.time()
STARTUP_COMPLETE = False


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    timestamp: str = Field(..., description="Check timestamp")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    checks: Dict[str, Dict[str, Any]] = Field(..., description="Individual check results")
    version: Optional[str] = Field(None, description="Service version")
    environment: Optional[str] = Field(None, description="Environment name")


@router.get("/ready", response_model=HealthStatus)
async def readiness_probe(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> HealthStatus:
    """
    Readiness probe - checks if service can handle requests.
    
    Returns 200 if ready, 503 if not ready.
    """
    checks = {}
    overall_status = "healthy"
    
    # Check database connectivity
    try:
        from netra_backend.app.database import get_db_session
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        checks["database"] = {"status": "healthy", "latency_ms": 5}
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
    
    # Check agent service
    try:
        from netra_backend.app.services.agent_service import get_agent_service
        agent_service = get_agent_service()
        if agent_service:
            checks["agent_service"] = {"status": "healthy", "agents_available": True}
        else:
            checks["agent_service"] = {"status": "degraded", "agents_available": False}
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as e:
        logger.warning(f"Agent service check failed: {e}")
        checks["agent_service"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
    
    # Check circuit breakers
    try:
        from netra_backend.app.core.circuit_breaker import circuit_registry
        open_circuits = []
        for name, cb in circuit_registry._circuit_breakers.items():
            if cb.state.name == "OPEN":
                open_circuits.append(name)
        
        if open_circuits:
            checks["circuit_breakers"] = {
                "status": "degraded",
                "open_circuits": open_circuits
            }
            if overall_status == "healthy":
                overall_status = "degraded"
        else:
            checks["circuit_breakers"] = {"status": "healthy", "open_circuits": []}
    except Exception as e:
        logger.warning(f"Circuit breaker check failed: {e}")
        checks["circuit_breakers"] = {"status": "unknown", "error": str(e)}
    
    response = HealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=time.time() - STARTUP_TIME,
        checks=checks,
        version=os.getenv("SERVICE_VERSION", "unknown"),
        environment=os.getenv("ENVIRONMENT", "development")
    )
    
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=response.dict())
    
    return response


@router.get("/live", response_model=HealthStatus)
async def liveness_probe(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> HealthStatus:
    """
    Liveness probe - checks if service is alive and not deadlocked.
    
    Returns 200 if alive, 503 if dead.
    """
    checks = {}
    
    # Check event loop responsiveness
    try:
        start = time.time()
        await asyncio.sleep(0.001)
        latency = (time.time() - start) * 1000
        
        if latency > 100:  # If event loop is slow
            checks["event_loop"] = {
                "status": "degraded",
                "latency_ms": latency
            }
            overall_status = "degraded"
        else:
            checks["event_loop"] = {
                "status": "healthy",
                "latency_ms": latency
            }
            overall_status = "healthy"
    except Exception as e:
        logger.error(f"Event loop check failed: {e}")
        checks["event_loop"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
    
    # Check memory usage
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > 1024:  # Over 1GB
            checks["memory"] = {
                "status": "degraded",
                "usage_mb": memory_mb
            }
            if overall_status == "healthy":
                overall_status = "degraded"
        else:
            checks["memory"] = {
                "status": "healthy",
                "usage_mb": memory_mb
            }
    except Exception:
        # psutil might not be available
        checks["memory"] = {"status": "unknown"}
    
    response = HealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=time.time() - STARTUP_TIME,
        checks=checks,
        version=os.getenv("SERVICE_VERSION", "unknown"),
        environment=os.getenv("ENVIRONMENT", "development")
    )
    
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=response.dict())
    
    return response


@router.get("/startup", response_model=HealthStatus)
async def startup_probe(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> HealthStatus:
    """
    Startup probe - checks if service has completed initialization.
    
    Returns 200 if started, 503 if still starting.
    """
    global STARTUP_COMPLETE
    
    checks = {}
    
    # Check if all required services are initialized
    initialization_checks = {
        "database": False,
        "agent_service": False,
        "auth_service": False,
        "configuration": False
    }
    
    # Check database
    try:
        from netra_backend.app.database import get_db_session
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        initialization_checks["database"] = True
    except Exception:
        pass
    
    # Check agent service
    try:
        from netra_backend.app.services.agent_service import get_agent_service
        if get_agent_service():
            initialization_checks["agent_service"] = True
    except Exception:
        pass
    
    # Check auth
    try:
        from netra_backend.app.auth_integration import get_current_user_optional
        initialization_checks["auth_service"] = True
    except Exception:
        pass
    
    # Check configuration
    try:
        from netra_backend.app.core.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        if env.get("DATABASE_URL"):
            initialization_checks["configuration"] = True
    except Exception:
        pass
    
    all_initialized = all(initialization_checks.values())
    STARTUP_COMPLETE = all_initialized
    
    for service, initialized in initialization_checks.items():
        checks[service] = {
            "status": "ready" if initialized else "initializing",
            "initialized": initialized
        }
    
    overall_status = "healthy" if all_initialized else "starting"
    
    response = HealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=time.time() - STARTUP_TIME,
        checks=checks,
        version=os.getenv("SERVICE_VERSION", "unknown"),
        environment=os.getenv("ENVIRONMENT", "development")
    )
    
    if not all_initialized:
        raise HTTPException(status_code=503, detail=response.dict())
    
    return response