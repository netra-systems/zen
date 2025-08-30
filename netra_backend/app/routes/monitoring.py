"""Database Monitoring API Endpoints

Provides REST endpoints for monitoring database connection health,
pool status, and performance metrics.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.connection_monitor import (
    connection_metrics,
    get_connection_status,
    health_checker,
)

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

def _log_health_check_request(current_user: Dict[str, Any]) -> None:
    """Log health check request."""
    logger.info(f"Health check requested by user: {current_user.get('user_id', 'unknown')}")

def _build_health_check_response(status_data: Dict[str, Any]) -> HealthCheckResponse:
    """Build health check response from status data."""
    return HealthCheckResponse(
        status=status_data["health_check"]["overall_health"],
        timestamp=datetime.fromisoformat(status_data["health_check"]["timestamp"].replace('Z', '+00:00')),
        pool_metrics=status_data["pool_metrics"], summary_stats=status_data["summary_stats"],
        health_check=status_data["health_check"]
    )

def _handle_health_check_error(e: Exception) -> None:
    """Handle health check errors."""
    logger.error(f"Error in health check endpoint: {e}")
    raise HTTPException(
        status_code=500, detail=f"Failed to get database health status: {str(e)}"
    )

@router.get("/health", response_model=HealthCheckResponse)
@router.head("/health", response_model=HealthCheckResponse)
@router.options("/health")
async def get_database_health(current_user: Dict[str, Any] = Depends(get_current_user)) -> HealthCheckResponse:
    """Get comprehensive database health status."""
    try:
        _log_health_check_request(current_user)
        status_data = await get_connection_status()
        return _build_health_check_response(status_data)
    except Exception as e:
        _handle_health_check_error(e)

def _log_pool_status_request(current_user: Dict[str, Any]) -> None:
    """Log pool status request."""
    logger.info(f"Pool status requested by user: {current_user.get('user_id', 'unknown')}")

def _build_pool_status_response(pool_status: Dict[str, Any]) -> PoolStatusResponse:
    """Build pool status response."""
    return PoolStatusResponse(
        timestamp=datetime.fromisoformat(pool_status["timestamp"].replace('Z', '+00:00')),
        sync_pool=pool_status.get("sync_pool"), async_pool=pool_status.get("async_pool"),
        health=pool_status["health"]
    )

def _handle_pool_status_error(e: Exception) -> None:
    """Handle pool status errors."""
    logger.error(f"Error in pool status endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get pool status: {str(e)}")

@router.get("/pool-status", response_model=PoolStatusResponse)
async def get_pool_status(current_user: Dict[str, Any] = Depends(get_current_user)) -> PoolStatusResponse:
    """Get current connection pool status."""
    try:
        _log_pool_status_request(current_user)
        pool_status = connection_metrics.get_pool_status()
        return _build_pool_status_response(pool_status)
    except Exception as e:
        _handle_pool_status_error(e)

def _log_metrics_history_request(current_user: Dict[str, Any], limit: int) -> None:
    """Log metrics history request."""
    logger.info(f"Metrics history requested by user: {current_user.get('user_id', 'unknown')}, limit: {limit}")

def _build_metrics_history_response(metrics_history: List[Dict[str, Any]], limit: int) -> MetricsHistoryResponse:
    """Build metrics history response."""
    return MetricsHistoryResponse(
        total_readings=len(connection_metrics._metrics_history), requested_limit=limit,
        returned_count=len(metrics_history), metrics=metrics_history
    )

def _handle_metrics_history_error(e: Exception) -> None:
    """Handle metrics history errors."""
    logger.error(f"Error in metrics history endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get metrics history: {str(e)}")

async def _get_metrics_history_safe(limit: int, current_user: Dict[str, Any]) -> MetricsHistoryResponse:
    """Get metrics history with error handling."""
    try:
        _log_metrics_history_request(current_user, limit)
        metrics_history = connection_metrics.get_metrics_history(limit)
        return _build_metrics_history_response(metrics_history, limit)
    except Exception as e:
        _handle_metrics_history_error(e)

@router.get("/metrics-history", response_model=MetricsHistoryResponse)
async def get_metrics_history(limit: int = Query(100, ge=1, le=1000), current_user: Dict[str, Any] = Depends(get_current_user)) -> MetricsHistoryResponse:
    """Get historical connection metrics for trend analysis."""
    return await _get_metrics_history_safe(limit, current_user)

def _log_summary_stats_request(current_user: Dict[str, Any]) -> None:
    """Log summary stats request."""
    logger.info(f"Summary stats requested by user: {current_user.get('user_id', 'unknown')}")

def _build_summary_stats_response(summary_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Build summary stats response."""
    return {"timestamp": datetime.now().isoformat(), "statistics": summary_stats}

def _handle_summary_stats_error(e: Exception) -> None:
    """Handle summary stats errors."""
    logger.error(f"Error in summary stats endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get summary statistics: {str(e)}")

@router.get("/summary-stats")
async def get_summary_statistics(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get summary statistics from recent connection metrics."""
    try:
        _log_summary_stats_request(current_user)
        summary_stats = connection_metrics.get_summary_stats()
        return _build_summary_stats_response(summary_stats)
    except Exception as e:
        _handle_summary_stats_error(e)

def _log_connection_test_request(current_user: Dict[str, Any]) -> None:
    """Log connection test request."""
    logger.info(f"Connection test requested by user: {current_user.get('user_id', 'unknown')}")

def _build_connection_test_response(health_check_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build connection test response."""
    return {
        "timestamp": datetime.now().isoformat(), "test_result": health_check_result,
        "status": health_check_result["overall_health"]
    }

def _handle_connection_test_error(e: Exception) -> None:
    """Handle connection test errors."""
    logger.error(f"Error in connection test endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to test database connection: {str(e)}")

@router.post("/test-connection")
async def test_database_connection(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Perform an immediate connectivity test to the database."""
    try:
        _log_connection_test_request(current_user)
        health_check_result = await health_checker.perform_health_check()
        return _build_connection_test_response(health_check_result)
    except Exception as e:
        _handle_connection_test_error(e)

def _log_alerts_request(current_user: Dict[str, Any]) -> None:
    """Log alerts request."""
    logger.info(f"Alerts info requested by user: {current_user.get('user_id', 'unknown')}")

def _calculate_cooldown_remaining() -> float:
    """Calculate remaining cooldown time."""
    return max(0, connection_metrics._alert_cooldown - (time.time() - connection_metrics._last_alert_time))

def _get_alert_status() -> str:
    """Get current alert status."""
    return "active" if (time.time() - connection_metrics._last_alert_time) < connection_metrics._alert_cooldown else "ready"

def _build_alerts_response() -> Dict[str, Any]:
    """Build alerts response."""
    return {
        "timestamp": datetime.now().isoformat(), "last_alert_time": connection_metrics._last_alert_time,
        "alert_cooldown_seconds": connection_metrics._alert_cooldown, "cooldown_remaining": _calculate_cooldown_remaining(),
        "alert_status": _get_alert_status()
    }

def _handle_alerts_error(e: Exception) -> None:
    """Handle alerts errors."""
    logger.error(f"Error in alerts endpoint: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get alerts information: {str(e)}")

@router.get("/alerts")
async def get_recent_alerts(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get information about recent alerts and system warnings."""
    try:
        _log_alerts_request(current_user)
        return _build_alerts_response()
    except Exception as e:
        _handle_alerts_error(e)

# Health check endpoint for load balancers and monitoring systems
def _build_ping_success_response(connectivity_test: Dict[str, Any]) -> Dict[str, Any]:
    """Build successful ping response."""
    return {
        "status": "ok", "timestamp": datetime.now().isoformat(),
        "response_time_ms": connectivity_test["response_time_ms"]
    }

def _handle_connectivity_failure() -> None:
    """Handle connectivity test failure."""
    raise HTTPException(status_code=503, detail="Database connectivity test failed")

def _handle_ping_error(e: Exception) -> None:
    """Handle ping endpoint errors."""
    logger.error(f"Error in ping endpoint: {e}")
    raise HTTPException(status_code=503, detail="Service unavailable")

async def _test_database_connectivity() -> Dict[str, Any]:
    """Test database connectivity and return response."""
    connectivity_test = await health_checker._test_connectivity()
    if connectivity_test["status"] == "healthy":
        return _build_ping_success_response(connectivity_test)
    _handle_connectivity_failure()

@router.get("/ping")
async def ping_database() -> Dict[str, Any]:
    """Simple ping endpoint for basic health checks."""
    try:
        return await _test_database_connectivity()
    except HTTPException:
        raise
    except Exception as e:
        _handle_ping_error(e)