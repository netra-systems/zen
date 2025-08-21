"""
Database Monitoring Control Routes
"""
from typing import Dict, Any
from fastapi import HTTPException
from app.db.observability import database_observability, setup_database_observability
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def build_monitoring_start_response() -> Dict[str, Any]:
    """Build monitoring start success response."""
    return {
        "success": True,
        "message": "Database monitoring started successfully"
    }


def handle_monitoring_start_error(e: Exception) -> None:
    """Handle monitoring start error."""
    logger.error(f"Error starting monitoring: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to start monitoring: {str(e)}"
    )


async def start_monitoring_handler() -> Dict[str, Any]:
    """Start database monitoring."""
    try:
        await setup_database_observability()
        return build_monitoring_start_response()
    except Exception as e:
        handle_monitoring_start_error(e)


def build_monitoring_stop_response() -> Dict[str, Any]:
    """Build monitoring stop success response."""
    return {
        "success": True,
        "message": "Database monitoring stopped successfully"
    }


def handle_monitoring_stop_error(e: Exception) -> None:
    """Handle monitoring stop error."""
    logger.error(f"Error stopping monitoring: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to stop monitoring: {str(e)}"
    )


async def stop_monitoring_handler() -> Dict[str, Any]:
    """Stop database monitoring."""
    try:
        await database_observability.stop_monitoring()
        return build_monitoring_stop_response()
    except Exception as e:
        handle_monitoring_stop_error(e)