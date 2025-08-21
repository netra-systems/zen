"""
Database Health Check Routes
"""
from typing import Dict, Any
from fastapi.responses import JSONResponse
from netra_backend.app.services.database.connection_monitor import get_connection_status
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def extract_health_data(connection_status: Dict) -> tuple[str, Dict]:
    """Extract health data from connection status."""
    health_check = connection_status.get('health_check', {})
    overall_health = health_check.get('overall_health', 'unknown')
    return overall_health, health_check


def build_health_details(health_check: Dict) -> Dict:
    """Build health details structure."""
    return {
        "connectivity": health_check.get('connectivity_test', {}).get('status', 'unknown'),
        "performance": health_check.get('performance_test', {}).get('status', 'unknown')
    }


def build_health_response(connection_status: Dict, health_check: Dict, overall_health: str) -> Dict:
    """Build health response structure."""
    return {
        "status": overall_health,
        "timestamp": connection_status.get('timestamp'),
        "details": build_health_details(health_check)
    }


def is_health_status_ok(overall_health: str) -> bool:
    """Check if health status is ok."""
    return overall_health in ['healthy', 'warning']


def create_response_based_on_health(health_response: Dict, overall_health: str):
    """Create appropriate response based on health status."""
    if is_health_status_ok(overall_health):
        return health_response
    return JSONResponse(status_code=503, content=health_response)


def build_error_content(error_message: str) -> Dict:
    """Build error response content."""
    return {
        "status": "error",
        "message": error_message,
        "timestamp": None
    }


def create_error_response(error_message: str) -> JSONResponse:
    """Create error response for health check failure."""
    content = build_error_content(error_message)
    return JSONResponse(status_code=503, content=content)


async def process_health_check(connection_status: Dict) -> Dict:
    """Process health check data."""
    overall_health, health_check = extract_health_data(connection_status)
    health_response = build_health_response(connection_status, health_check, overall_health)
    return create_response_based_on_health(health_response, overall_health)


async def get_database_health_handler() -> Dict[str, Any]:
    """Get database health status (no authentication required)."""
    try:
        connection_status = await get_connection_status()
        return await process_health_check(connection_status)
    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        return create_error_response(f"Health check failed: {str(e)}")