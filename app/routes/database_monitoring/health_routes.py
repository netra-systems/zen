"""
Database Health Check Routes
"""
from typing import Dict, Any
from fastapi.responses import JSONResponse
from app.services.database.connection_monitor import get_connection_status
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def extract_health_data(connection_status: Dict) -> tuple[str, Dict]:
    """Extract health data from connection status."""
    health_check = connection_status.get('health_check', {})
    overall_health = health_check.get('overall_health', 'unknown')
    return overall_health, health_check


def build_health_response(connection_status: Dict, health_check: Dict, overall_health: str) -> Dict:
    """Build health response structure."""
    return {
        "status": overall_health,
        "timestamp": connection_status.get('timestamp'),
        "details": {
            "connectivity": health_check.get('connectivity_test', {}).get('status', 'unknown'),
            "performance": health_check.get('performance_test', {}).get('status', 'unknown')
        }
    }


def create_response_based_on_health(health_response: Dict, overall_health: str):
    """Create appropriate response based on health status."""
    if overall_health in ['healthy', 'warning']:
        return health_response
    else:
        return JSONResponse(
            status_code=503,
            content=health_response
        )


def create_error_response(error_message: str) -> JSONResponse:
    """Create error response for health check failure."""
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "message": error_message,
            "timestamp": None
        }
    )


async def get_database_health_handler() -> Dict[str, Any]:
    """Get database health status (no authentication required)."""
    try:
        connection_status = await get_connection_status()
        overall_health, health_check = extract_health_data(connection_status)
        health_response = build_health_response(connection_status, health_check, overall_health)
        return create_response_based_on_health(health_response, overall_health)
        
    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        return create_error_response(f"Health check failed: {str(e)}")