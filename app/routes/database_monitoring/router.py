"""
Database Monitoring API Router - Main route definitions
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, Depends

# Import auth functions (will need to be uncommented when auth is configured)
# from app.auth_integration.enhanced_auth_security import get_current_user, require_admin

from .dashboard_routes import (
    get_dashboard_handler, get_current_metrics_handler, 
    get_metrics_history_handler, get_connection_status_handler
)
from .cache_routes import (
    get_cache_metrics_handler, invalidate_cache_by_tag_handler,
    invalidate_cache_by_pattern_handler, clear_all_cache_handler
)
from .transaction_routes import (
    get_transaction_stats_handler, get_active_transactions_handler
)
from .alert_routes import get_alerts_handler, get_performance_summary_handler
from .control_routes import start_monitoring_handler, stop_monitoring_handler
from .health_routes import get_database_health_handler

router = APIRouter(prefix="/api/v1/database", tags=["database-monitoring"])


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard() -> Dict[str, Any]:
    """Get comprehensive database dashboard data."""
    return await get_dashboard_handler()


@router.get("/metrics/current", response_model=Dict[str, Any])
async def get_current_metrics() -> Dict[str, Any]:
    """Get current database metrics."""
    return await get_current_metrics_handler()


@router.get("/metrics/history", response_model=List[Dict[str, Any]])
async def get_metrics_history(
    hours: int = Query(1, ge=1, le=24, description="Hours of history to retrieve")
    # current_user: Dict = Depends(get_current_user)  # Enable when auth is ready
) -> List[Dict[str, Any]]:
    """Get database metrics history."""
    return await get_metrics_history_handler(hours)


@router.get("/connections/status", response_model=Dict[str, Any])
async def get_connection_status_endpoint(
    # current_user: Dict = Depends(get_current_user)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Get connection pool status."""
    return await get_connection_status_handler()


@router.get("/cache/metrics", response_model=Dict[str, Any])
async def get_cache_metrics(
    # current_user: Dict = Depends(get_current_user)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Get query cache metrics."""
    return await get_cache_metrics_handler()


@router.post("/cache/invalidate/tag")
async def invalidate_cache_by_tag(
    tag: str = Query(..., description="Tag to invalidate")
    # current_user: Dict = Depends(require_admin)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Invalidate cache entries by tag."""
    return await invalidate_cache_by_tag_handler(tag)


@router.post("/cache/invalidate/pattern")
async def invalidate_cache_by_pattern(
    pattern: str = Query(..., description="Pattern to match")
    # current_user: Dict = Depends(require_admin)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Invalidate cache entries by pattern."""
    return await invalidate_cache_by_pattern_handler(pattern)


@router.post("/cache/clear")
async def clear_all_cache(
    # current_user: Dict = Depends(require_admin)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Clear all cached entries."""
    return await clear_all_cache_handler()


@router.get("/transactions/stats", response_model=Dict[str, Any])
async def get_transaction_stats(
    # current_user: Dict = Depends(get_current_user)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Get transaction statistics."""
    return await get_transaction_stats_handler()


@router.get("/transactions/active", response_model=Dict[str, Any])
async def get_active_transactions(
    # current_user: Dict = Depends(get_current_user)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Get currently active transactions."""
    return await get_active_transactions_handler()


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(
    hours: int = Query(24, ge=1, le=168, description="Hours of alerts to retrieve"),
    severity: Optional[str] = Query(None, description="Filter by severity")
    # current_user: Dict = Depends(get_current_user)  # Enable when auth is ready
) -> List[Dict[str, Any]]:
    """Get database alerts."""
    return await get_alerts_handler(hours, severity)


@router.get("/performance/summary", response_model=Dict[str, Any])
async def get_performance_summary(
    # current_user: Dict = Depends(get_current_user)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Get performance summary."""
    return await get_performance_summary_handler()


@router.post("/monitoring/start")
async def start_monitoring(
    # current_user: Dict = Depends(require_admin)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Start database monitoring."""
    return await start_monitoring_handler()


@router.post("/monitoring/stop")
async def stop_monitoring(
    # current_user: Dict = Depends(require_admin)  # Enable when auth is ready
) -> Dict[str, Any]:
    """Stop database monitoring."""
    return await stop_monitoring_handler()


@router.get("/status", response_model=Dict[str, Any])
async def get_database_status() -> Dict[str, Any]:
    """Get database status (no authentication required)."""
    return await get_database_health_handler()