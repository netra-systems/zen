"""Database Monitoring API Routes

Provides REST endpoints for database observability, metrics,
and performance monitoring.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

# Auth imports - will be enabled when auth is properly configured
# from app.auth.enhanced_auth_security import get_current_user, require_admin
from app.db.observability import (
    database_observability,
    get_database_dashboard,
    setup_database_observability
)
from app.db.query_cache import query_cache
from app.db.transaction_manager import transaction_manager
from app.services.database.connection_monitor import get_connection_status
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/api/v1/database", tags=["database-monitoring"])


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard() -> Dict[str, Any]:
    """Get comprehensive database dashboard data."""
    try:
        dashboard_data = await get_database_dashboard()
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting database dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database dashboard: {str(e)}"
        )


@router.get("/metrics/current", response_model=Dict[str, Any])
async def get_current_metrics() -> Dict[str, Any]:
    """Get current database metrics."""
    try:
        return database_observability.get_current_metrics()
        
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current metrics: {str(e)}"
        )


@router.get("/metrics/history", response_model=List[Dict[str, Any]])
async def get_metrics_history(
    hours: int = Query(1, ge=1, le=24, description="Hours of history to retrieve"),
    current_user: Dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get database metrics history."""
    try:
        return database_observability.get_metrics_history(hours=hours)
        
    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics history: {str(e)}"
        )


@router.get("/connections/status", response_model=Dict[str, Any])
async def get_connection_status_endpoint(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get connection pool status."""
    try:
        return await get_connection_status()
        
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get connection status: {str(e)}"
        )


@router.get("/cache/metrics", response_model=Dict[str, Any])
async def get_cache_metrics(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get query cache metrics."""
    try:
        return query_cache.get_metrics()
        
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache metrics: {str(e)}"
        )


@router.post("/cache/invalidate/tag")
async def invalidate_cache_by_tag(
    tag: str = Query(..., description="Tag to invalidate"),
    current_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Invalidate cache entries by tag."""
    try:
        invalidated_count = await query_cache.invalidate_by_tag(tag)
        
        return {
            "success": True,
            "message": f"Invalidated {invalidated_count} cache entries with tag '{tag}'",
            "invalidated_count": invalidated_count
        }
        
    except Exception as e:
        logger.error(f"Error invalidating cache by tag: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.post("/cache/invalidate/pattern")
async def invalidate_cache_by_pattern(
    pattern: str = Query(..., description="Pattern to match"),
    current_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Invalidate cache entries by pattern."""
    try:
        invalidated_count = await query_cache.invalidate_pattern(pattern)
        
        return {
            "success": True,
            "message": f"Invalidated {invalidated_count} cache entries matching pattern '{pattern}'",
            "invalidated_count": invalidated_count
        }
        
    except Exception as e:
        logger.error(f"Error invalidating cache by pattern: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_all_cache(
    current_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Clear all cached entries."""
    try:
        cleared_count = await query_cache.clear_all()
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cache entries",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/transactions/stats", response_model=Dict[str, Any])
async def get_transaction_stats(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get transaction statistics."""
    try:
        return transaction_manager.get_transaction_stats()
        
    except Exception as e:
        logger.error(f"Error getting transaction stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get transaction stats: {str(e)}"
        )


@router.get("/transactions/active", response_model=Dict[str, Any])
async def get_active_transactions(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get currently active transactions."""
    try:
        active_transactions = transaction_manager.get_active_transactions()
        
        # Convert TransactionMetrics to dict for JSON serialization
        serialized_transactions = {}
        for tx_id, metrics in active_transactions.items():
            serialized_transactions[tx_id] = {
                "transaction_id": metrics.transaction_id,
                "start_time": metrics.start_time,
                "duration": metrics.duration,
                "retry_count": metrics.retry_count,
                "error_count": metrics.error_count,
                "success": metrics.success,
                "isolation_level": metrics.isolation_level
            }
        
        return {
            "active_transactions": serialized_transactions,
            "count": len(serialized_transactions)
        }
        
    except Exception as e:
        logger.error(f"Error getting active transactions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active transactions: {str(e)}"
        )


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(
    hours: int = Query(24, ge=1, le=168, description="Hours of alerts to retrieve"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    current_user: Dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get database alerts."""
    try:
        alerts = database_observability.get_alerts(hours=hours)
        
        # Filter by severity if specified
        if severity:
            alerts = [alert for alert in alerts if alert.get('severity') == severity]
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.get("/performance/summary", response_model=Dict[str, Any])
async def get_performance_summary(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get performance summary."""
    try:
        return database_observability.get_performance_summary()
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance summary: {str(e)}"
        )


@router.post("/monitoring/start")
async def start_monitoring(
    current_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Start database monitoring."""
    try:
        await setup_database_observability()
        
        return {
            "success": True,
            "message": "Database monitoring started successfully"
        }
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@router.post("/monitoring/stop")
async def stop_monitoring(
    current_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Stop database monitoring."""
    try:
        await database_observability.stop_monitoring()
        
        return {
            "success": True,
            "message": "Database monitoring stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop monitoring: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def get_database_health() -> Dict[str, Any]:
    """Get database health status (no authentication required)."""
    try:
        connection_status = await get_connection_status()
        health_check = connection_status.get('health_check', {})
        
        # Determine overall health
        overall_health = health_check.get('overall_health', 'unknown')
        
        # Basic health response
        health_response = {
            "status": overall_health,
            "timestamp": connection_status.get('timestamp'),
            "details": {
                "connectivity": health_check.get('connectivity_test', {}).get('status', 'unknown'),
                "performance": health_check.get('performance_test', {}).get('status', 'unknown')
            }
        }
        
        # Set HTTP status based on health
        if overall_health in ['healthy', 'warning']:
            return health_response
        else:
            return JSONResponse(
                status_code=503,
                content=health_response
            )
        
    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "timestamp": None
            }
        )