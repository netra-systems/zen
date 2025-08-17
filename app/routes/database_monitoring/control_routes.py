"""
Database Monitoring Control Routes
"""
from typing import Dict, Any
from fastapi import HTTPException
from app.db.observability import database_observability, setup_database_observability
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def start_monitoring_handler() -> Dict[str, Any]:
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


async def stop_monitoring_handler() -> Dict[str, Any]:
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