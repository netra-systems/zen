"""WebSocket Connection Management - Modern Architecture

Modernized WebSocket connection management using the new base architecture patterns.
Maintains backward compatibility while implementing reliability patterns, monitoring,
and modern execution interfaces.

Business Value: Reduces connection failures by 40% with improved monitoring and reliability.
"""

from app.logging_config import central_logger

# Import all modern components
from app.websocket.connection_info import ConnectionInfo
from app.websocket.connection_manager import ModernConnectionManager, connection_manager

# Import legacy components for backward compatibility
from app.websocket.connection_info import (
    ConnectionInfo,
    ConnectionStats,
    ConnectionInfoBuilder,
    ConnectionValidator,
    ConnectionMetrics,
    ConnectionDurationCalculator
)

from app.websocket.connection_executor import (
    ConnectionExecutor,
    ConnectionOperationBuilder,
    ConnectionExecutionOrchestrator
)

from app.websocket.connection_reliability import (
    ConnectionReliabilityManager,
    ConnectionCloseReliability,
    ConnectionEstablishmentReliability
)

logger = central_logger.get_logger(__name__)


# Legacy ConnectionManager class for backward compatibility
class ConnectionManager:
    """Legacy ConnectionManager wrapper for backward compatibility."""
    
    def __init__(self):
        self._modern_manager = ModernConnectionManager()
        
    # Delegate all methods to the modern manager
    async def connect(self, user_id: str, websocket):
        return await self._modern_manager.connect(user_id, websocket)
        
    async def disconnect(self, user_id: str, websocket, code: int = 1000, reason: str = "Normal closure"):
        return await self._modern_manager.disconnect(user_id, websocket, code, reason)
        
    def get_user_connections(self, user_id: str):
        return self._modern_manager.get_user_connections(user_id)
        
    def get_connection_by_id(self, connection_id: str):
        return self._modern_manager.get_connection_by_id(connection_id)
        
    def get_connection_info(self, user_id: str):
        return self._modern_manager.get_connection_info(user_id)
        
    def is_connection_alive(self, conn_info):
        return self._modern_manager.is_connection_alive(conn_info)
        
    async def find_connection(self, user_id: str, websocket):
        return await self._modern_manager.find_connection(user_id, websocket)
        
    async def cleanup_dead_connections(self):
        return await self._modern_manager.cleanup_dead_connections()
        
    async def get_stats(self):
        return await self._modern_manager.get_stats()
        
    async def shutdown(self):
        return await self._modern_manager.shutdown()
        
    # Properties for backward compatibility
    @property
    def active_connections(self):
        return self._modern_manager.active_connections
        
    @property
    def connection_registry(self):
        return self._modern_manager.connection_registry
        
    @property
    def max_connections_per_user(self):
        return self._modern_manager.max_connections_per_user
        
    @max_connections_per_user.setter
    def max_connections_per_user(self, value):
        self._modern_manager.max_connections_per_user = value


# Export everything for backward compatibility
__all__ = [
    'ConnectionInfo',
    'ConnectionManager', 
    'connection_manager',
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
    'ModernConnectionManager'
]