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
from typing import Dict, Any, Optional
from datetime import datetime

logger = central_logger.get_logger(__name__)


class ConnectionInfo:
    """Information about a WebSocket connection."""
    
    def __init__(self, connection_id: str, user_id: str = None, metadata: Dict[str, Any] = None):
        self.connection_id = connection_id
        self.user_id = user_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }


# SSOT COMPLIANCE: Use direct alias instead of class inheritance
# DEPRECATED: WebSocketConnectionManager is now an alias to UnifiedWebSocketManager
# Use UnifiedWebSocketManager directly for new code
# This eliminates the duplicate class definition while maintaining backward compatibility
WebSocketConnectionManager = UnifiedWebSocketManager


# SSOT alias for backward compatibility
ConnectionManager = WebSocketConnectionManager

# Export for backward compatibility
__all__ = ['WebSocketConnectionManager', 'ConnectionManager', 'ConnectionInfo']