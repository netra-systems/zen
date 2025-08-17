"""
Database Monitoring Dashboard Routes
"""
from typing import Dict, Any, List
from fastapi import HTTPException, Query, Depends
from app.db.observability import database_observability, get_database_dashboard
from app.services.database.connection_monitor import get_connection_status
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def get_dashboard_handler() -> Dict[str, Any]:
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


async def get_current_metrics_handler() -> Dict[str, Any]:
    """Get current database metrics."""
    try:
        return database_observability.get_current_metrics()
        
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current metrics: {str(e)}"
        )


async def get_metrics_history_handler(hours: int) -> List[Dict[str, Any]]:
    """Get database metrics history."""
    try:
        return database_observability.get_metrics_history(hours=hours)
        
    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics history: {str(e)}"
        )


async def get_connection_status_handler() -> Dict[str, Any]:
    """Get connection pool status."""
    try:
        return await get_connection_status()
        
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get connection status: {str(e)}"
        )