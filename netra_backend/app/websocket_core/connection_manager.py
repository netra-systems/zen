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


class WebSocketConnectionManager(UnifiedWebSocketManager):
    """
    SSOT alias for WebSocket connection management.
    
    This class serves as the primary interface for WebSocket connection management,
    providing backward compatibility for tests that expect WebSocketConnectionManager
    while delegating to the unified implementation.
    
    Following CLAUDE.md principle: Search First, Create Second - this aliases
    existing functionality rather than duplicating it.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize WebSocket connection manager."""
        super().__init__(*args, **kwargs)
        logger.debug("WebSocketConnectionManager initialized (SSOT alias)")


# SSOT alias for backward compatibility
ConnectionManager = WebSocketConnectionManager

# Export for backward compatibility
__all__ = ['WebSocketConnectionManager', 'ConnectionManager']