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
    EnhancedToolExecutionEngine,  # Already available as alias
    enhance_tool_dispatcher_with_notifications,
    ToolExecutionResult,
    NetraException  # Use base exception from the SSOT module
)

# Export for backward compatibility
__all__ = [
    'EnhancedToolExecutionEngine',
    'UnifiedToolExecutionEngine', 
    'enhance_tool_dispatcher_with_notifications',
    'ToolExecutionResult',
    'NetraException'
]