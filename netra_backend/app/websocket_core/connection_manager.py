"""
WebSocket Connection Manager - SSOT Alias

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Development Velocity & Backward Compatibility
- Value Impact: Prevents test failures from broken imports, maintains test reliability
- Strategic Impact: Critical for WebSocket thread routing tests to run properly

This module provides the SSOT alias for WebSocketConnectionManager imports that tests expect.
Following CLAUDE.md SSOT principles by creating proper aliases rather than duplicating code.
"""

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# SSOT COMPLIANCE: Use direct alias instead of class inheritance
# DEPRECATED: WebSocketConnectionManager is now an alias to UnifiedWebSocketManager
# Use UnifiedWebSocketManager directly for new code
# This eliminates the duplicate class definition while maintaining backward compatibility
WebSocketConnectionManager = UnifiedWebSocketManager


# SSOT alias for backward compatibility
ConnectionManager = WebSocketConnectionManager


# ===== COMPATIBILITY CLASSES =====

class ConnectionInfo:
    """
    COMPATIBILITY CLASS: Connection information for legacy test compatibility.
    
    This class provides backward compatibility for tests that expect connection
    information objects. In the SSOT implementation, connection info is handled
    directly by the WebSocketManager.
    """
    
    def __init__(self, connection_id: str, user_id: str, connected_at: float = None):
        import time
        self.connection_id = connection_id
        self.user_id = user_id
        self.connected_at = connected_at or time.time()
        self.is_active = True
        self.last_activity = self.connected_at
    
    def update_activity(self):
        """Update last activity timestamp."""
        import time
        self.last_activity = time.time()
    
    def disconnect(self):
        """Mark connection as disconnected."""
        self.is_active = False
    
    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at,
            "is_active": self.is_active,
            "last_activity": self.last_activity
        }


# Export for backward compatibility
__all__ = ['WebSocketConnectionManager', 'ConnectionManager', 'ConnectionInfo']