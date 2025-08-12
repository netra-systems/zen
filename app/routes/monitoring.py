"""Database Monitoring API Endpoints

Provides REST endpoints for monitoring database connection health,
pool status, and performance metrics.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from app.services.database.connection_monitor import (
    get_connection_status,
    connection_metrics,
    health_checker
)
from app.auth.dependencies import get_current_user
from app.logging_config import central_logger
from pydantic import BaseModel, Field
from datetime import datetime
import time

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    pool_metrics: Dict[str, Any] = Field(..., description="Connection pool metrics")
    summary_stats: Dict[str, Any] = Field(..., description="Summary statistics")
    health_check: Dict[str, Any] = Field(..., description="Detailed health check results")

class PoolStatusResponse(BaseModel):
    """Response model for pool status endpoint"""
    timestamp: datetime = Field(..., description="Status timestamp")
    sync_pool: Optional[Dict[str, Any]] = Field(None, description="Synchronous pool status")
    async_pool: Optional[Dict[str, Any]] = Field(None, description="Asynchronous pool status")
    health: str = Field(..., description="Overall pool health")

class MetricsHistoryResponse(BaseModel):
    """Response model for metrics history endpoint"""
    total_readings: int = Field(..., description="Total number of readings")
    requested_limit: int = Field(..., description="Requested limit")
    returned_count: int = Field(..., description="Number of readings returned")
    metrics: List[Dict[str, Any]] = Field(..., description="Historical metrics data")

@router.get("/health", response_model=HealthCheckResponse)
async def get_database_health(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> HealthCheckResponse:
    """
    Get comprehensive database health status including:
    - Connection pool metrics
    - Connectivity tests
    - Performance tests
    - Historical statistics
    
    Requires authentication.
    """
    try:
        logger.info(f"Health check requested by user: {current_user.get('user_id', 'unknown')}")
        
        status_data = await get_connection_status()
        
        return HealthCheckResponse(
            status=status_data["health_check"]["overall_health"],
            timestamp=datetime.fromisoformat(status_data["health_check"]["timestamp"].replace('Z', '+00:00')),
            pool_metrics=status_data["pool_metrics"],
            summary_stats=status_data["summary_stats"],
            health_check=status_data["health_check"]
        )
        
    except Exception as e:
        logger.error(f"Error in health check endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database health status: {str(e)}"
        )

@router.get("/pool-status", response_model=PoolStatusResponse)
async def get_pool_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> PoolStatusResponse:
    """
    Get current connection pool status including:
    - Pool sizes and utilization
    - Active connections
    - Overflow status
    
    Requires authentication.
    """
    try:
        logger.info(f"Pool status requested by user: {current_user.get('user_id', 'unknown')}")
        
        pool_status = connection_metrics.get_pool_status()
        
        return PoolStatusResponse(
            timestamp=datetime.fromisoformat(pool_status["timestamp"].replace('Z', '+00:00')),
            sync_pool=pool_status.get("sync_pool"),
            async_pool=pool_status.get("async_pool"),
            health=pool_status["health"]
        )
        
    except Exception as e:
        logger.error(f"Error in pool status endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool status: {str(e)}"
        )

@router.get("/metrics-history", response_model=MetricsHistoryResponse)
async def get_metrics_history(
    limit: int = Query(100, ge=1, le=1000, description="Number of recent metrics to return"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> MetricsHistoryResponse:
    """
    Get historical connection metrics for trend analysis.
    
    Supports pagination with limit parameter (1-1000).
    Requires authentication.
    """
    try:
        logger.info(f"Metrics history requested by user: {current_user.get('user_id', 'unknown')}, limit: {limit}")
        
        metrics_history = connection_metrics.get_metrics_history(limit)
        
        return MetricsHistoryResponse(
            total_readings=len(connection_metrics._metrics_history),
            requested_limit=limit,
            returned_count=len(metrics_history),
            metrics=metrics_history
        )
        
    except Exception as e:
        logger.error(f"Error in metrics history endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics history: {str(e)}"
        )

@router.get("/summary-stats")
async def get_summary_statistics(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get summary statistics from recent connection metrics including:
    - Health distribution
    - Average and maximum utilization
    - Alert counts
    
    Requires authentication.
    """
    try:
        logger.info(f"Summary stats requested by user: {current_user.get('user_id', 'unknown')}")
        
        summary_stats = connection_metrics.get_summary_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "statistics": summary_stats
        }
        
    except Exception as e:
        logger.error(f"Error in summary stats endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get summary statistics: {str(e)}"
        )

@router.post("/test-connection")
async def test_database_connection(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Perform an immediate connectivity test to the database.
    
    This endpoint triggers a real-time connectivity test
    and returns the results immediately.
    
    Requires authentication.
    """
    try:
        logger.info(f"Connection test requested by user: {current_user.get('user_id', 'unknown')}")
        
        # Perform immediate health check
        health_check_result = await health_checker.perform_health_check()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "test_result": health_check_result,
            "status": health_check_result["overall_health"]
        }
        
    except Exception as e:
        logger.error(f"Error in connection test endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test database connection: {str(e)}"
        )

@router.get("/alerts")
async def get_recent_alerts(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get information about recent alerts and system warnings.
    
    Returns alert status and cooldown information.
    Requires authentication.
    """
    try:
        logger.info(f"Alerts info requested by user: {current_user.get('user_id', 'unknown')}")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "last_alert_time": connection_metrics._last_alert_time,
            "alert_cooldown_seconds": connection_metrics._alert_cooldown,
            "cooldown_remaining": max(0, connection_metrics._alert_cooldown - 
                                   (time.time() - connection_metrics._last_alert_time)),
            "alert_status": "active" if (time.time() - connection_metrics._last_alert_time) < connection_metrics._alert_cooldown else "ready"
        }
        
    except Exception as e:
        logger.error(f"Error in alerts endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alerts information: {str(e)}"
        )

# Health check endpoint for load balancers and monitoring systems
@router.get("/ping")
async def ping_database() -> Dict[str, Any]:
    """
    Simple ping endpoint for basic health checks.
    
    This endpoint does not require authentication and provides
    a quick health status for load balancers and monitoring systems.
    """
    try:
        # Quick connectivity test
        connectivity_test = await health_checker._test_connectivity()
        
        if connectivity_test["status"] == "healthy":
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": connectivity_test["response_time_ms"]
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Database connectivity test failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ping endpoint: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )