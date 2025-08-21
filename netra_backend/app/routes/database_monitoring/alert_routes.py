"""
Database Alert and Performance Routes
"""
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from netra_backend.app.db.observability import database_observability
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def filter_alerts_by_severity(alerts: List[Dict], severity: Optional[str]) -> List[Dict]:
    """Filter alerts by severity if specified."""
    if severity:
        return [alert for alert in alerts if alert.get('severity') == severity]
    return alerts


def handle_alerts_error(e: Exception) -> None:
    """Handle alerts retrieval error."""
    logger.error(f"Error getting alerts: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to get alerts: {str(e)}"
    )


async def get_alerts_handler(hours: int, severity: Optional[str]) -> List[Dict[str, Any]]:
    """Get database alerts."""
    try:
        alerts = database_observability.get_alerts(hours=hours)
        return filter_alerts_by_severity(alerts, severity)
    except Exception as e:
        handle_alerts_error(e)


def handle_performance_error(e: Exception) -> None:
    """Handle performance summary retrieval error."""
    logger.error(f"Error getting performance summary: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to get performance summary: {str(e)}"
    )


async def get_performance_summary_handler() -> Dict[str, Any]:
    """Get performance summary."""
    try:
        return database_observability.get_performance_summary()
    except Exception as e:
        handle_performance_error(e)