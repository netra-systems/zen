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
from netra_backend.app.websocket_core.types import ConnectionInfo
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# SSOT COMPLIANCE: Use direct alias instead of class inheritance
# This eliminates the duplicate class definition while maintaining backward compatibility
WebSocketConnectionManager = UnifiedWebSocketManager


# SSOT alias for backward compatibility
ConnectionManager = WebSocketConnectionManager

# Export for backward compatibility
__all__ = ['WebSocketConnectionManager', 'ConnectionManager', 'ConnectionInfo']