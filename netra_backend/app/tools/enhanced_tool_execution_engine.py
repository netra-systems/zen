"""Enhanced Tool Execution Engine - SSOT Bridge Module.

This module provides a bridge to the SSOT UnifiedToolExecutionEngine implementation.
All tool execution functionality is consolidated in the UnifiedToolExecutionEngine.

Business Value:
- Maintains backward compatibility for existing imports expecting EnhancedToolExecutionEngine
- Redirects to SSOT implementation to eliminate code duplication
- Ensures all tool execution uses the same WebSocket-enabled system

Architecture:
- Bridge pattern to maintain import compatibility
- All functionality delegated to UnifiedToolExecutionEngine
- WebSocket integration preserved from SSOT implementation
"""

# SSOT Import - redirect to the unified implementation
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications,
    ToolExecutionError,
    PermissionDeniedError,
    ToolNotFoundError,
    ToolValidationError,
    WebSocketNotificationError
)

# For backward compatibility, alias UnifiedToolExecutionEngine as EnhancedToolExecutionEngine
EnhancedToolExecutionEngine = UnifiedToolExecutionEngine

# Export for backward compatibility
__all__ = [
    'EnhancedToolExecutionEngine',
    'enhance_tool_dispatcher_with_notifications',
    'ToolExecutionError',
    'PermissionDeniedError', 
    'ToolNotFoundError',
    'ToolValidationError',
    'WebSocketNotificationError'
]