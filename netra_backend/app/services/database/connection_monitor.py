"""Database Connection Pool Monitoring Service

Provides comprehensive monitoring of database connection pools.
"""

from typing import Any, Dict

from netra_backend.app.config import config_manager
from netra_backend.app.core.exceptions_database import DatabaseError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.health_checker import ConnectionHealthChecker
from netra_backend.app.services.database.pool_metrics import ConnectionPoolMetrics

logger = central_logger.get_logger(__name__)

# Global instances
connection_metrics = ConnectionPoolMetrics()
health_checker = ConnectionHealthChecker(connection_metrics)

async def get_connection_status() -> Dict[str, Any]:
    """Get comprehensive connection status"""
    try:
        return {
            "pool_metrics": connection_metrics.get_pool_status(),
            "summary_stats": connection_metrics.get_summary_stats(),
            "health_check": await health_checker.perform_health_check()
        }
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise DatabaseError(
            message="Failed to get connection status",
            context={"error": str(e)}
        )

async def start_connection_monitoring() -> None:
    """Start the connection monitoring service"""
    config = config_manager.get_config()
    # Skip monitoring if database is in mock mode
    database_url = getattr(config, 'database_url', '')
    if database_url and "mock" in database_url.lower():
        logger.info("Skipping connection monitoring in mock mode")
        return
        
    try:
        await health_checker.start_monitoring()
    except Exception as e:
        logger.error(f"Error starting connection monitoring: {e}")
        raise

def stop_connection_monitoring() -> None:
    """Stop the connection monitoring service"""
    health_checker.stop_monitoring()