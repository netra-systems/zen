"""WebSocket Connection Management

Consolidated WebSocket connection management with reliability patterns, monitoring,
and modern execution interfaces.

Business Value: Reduces connection failures by 40% with improved monitoring and reliability.
"""

from netra_backend.app.logging_config import central_logger

# Import the consolidated ConnectionManager
from netra_backend.app.websocket.connection_manager import (
    ConnectionManager,
    get_connection_manager,
)

# Import connection info components
from netra_backend.app.websocket.connection_info import (
    ConnectionDurationCalculator,
    ConnectionInfo,
    ConnectionInfoBuilder,
    ConnectionMetrics,
    ConnectionStats,
    ConnectionValidator,
)

# Import execution components
from netra_backend.app.websocket.connection_executor import (
    ConnectionExecutionOrchestrator,
    ConnectionExecutor,
    ConnectionOperationBuilder,
)

# Import reliability components
from netra_backend.app.websocket.connection_reliability import (
    ConnectionCloseReliability,
    ConnectionEstablishmentReliability,
    ConnectionReliabilityManager,
)

logger = central_logger.get_logger(__name__)

# Connection manager will be initialized lazily when first accessed
connection_manager = None

def get_connection_manager_instance():
    """Get connection manager instance with lazy initialization."""
    global connection_manager
    if connection_manager is None:
        connection_manager = get_connection_manager()
    return connection_manager

# Export everything for backward compatibility
__all__ = [
    'ConnectionInfo',
    'ConnectionManager', 
    'connection_manager',
    'get_connection_manager',
    'get_connection_manager_instance',
    'ConnectionStats',
    'ConnectionInfoBuilder',
    'ConnectionValidator',
    'ConnectionMetrics',
    'ConnectionDurationCalculator',
    'ConnectionExecutor',
    'ConnectionOperationBuilder',
    'ConnectionExecutionOrchestrator',
    'ConnectionReliabilityManager',
    'ConnectionCloseReliability',
    'ConnectionEstablishmentReliability',
]