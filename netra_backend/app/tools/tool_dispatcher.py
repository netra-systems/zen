"""Tool Dispatcher Import Bridge - SSOT Compliance Module.

This module provides a bridge to the SSOT UnifiedToolDispatcher implementation.
All tool dispatching functionality is consolidated in the UnifiedToolDispatcher.

Business Value:
- Maintains backward compatibility for existing imports
- Redirects to SSOT implementation to eliminate code duplication
- Ensures all tool dispatching uses the same isolated, WebSocket-enabled system

Architecture:
- Bridge pattern to maintain import compatibility
- All functionality delegated to UnifiedToolDispatcher
- Factory methods preserved for proper user isolation
"""

# SSOT Import - redirect to the unified implementation
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy,
    create_request_scoped_dispatcher,
    AuthenticationError,
    PermissionError,
    SecurityViolationError
)

# For backward compatibility, alias UnifiedToolDispatcher as ToolDispatcher
ToolDispatcher = UnifiedToolDispatcher
ToolDispatcherFactory = UnifiedToolDispatcherFactory

# Legacy compatibility methods
async def create_tool_dispatcher(*args, **kwargs):
    """Legacy factory method - redirects to SSOT UnifiedToolDispatcher."""
    import warnings
    warnings.warn(
        "create_tool_dispatcher() is deprecated. Use UnifiedToolDispatcher.create_for_user() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # If user_context provided, use proper factory - CRITICAL FIX: await async method
    if 'user_context' in kwargs:
        return await UnifiedToolDispatcher.create_for_user(**kwargs)
    
    # Legacy fallback - create with minimal context (sync method)
    return ToolDispatcherFactory.create_legacy_global(*args, **kwargs)

# Export for backward compatibility
__all__ = [
    'ToolDispatcher',
    'ToolDispatcherFactory', 
    'ToolDispatchRequest',
    'ToolDispatchResponse',
    'DispatchStrategy',
    'create_request_scoped_dispatcher',
    'create_tool_dispatcher',
    'AuthenticationError',
    'PermissionError', 
    'SecurityViolationError'
]