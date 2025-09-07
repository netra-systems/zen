"""Tool Dispatcher Facade - Public API for tool dispatching operations.

CONSOLIDATION COMPLETE: Single source of truth in unified_tool_dispatcher.py

Architecture:
- UnifiedToolDispatcher: Core implementation with factory-enforced isolation
- UnifiedAdminToolDispatcher: Admin tools extending base dispatcher
- Request-scoped isolation by default (no shared state)
- WebSocket events for ALL tool executions
- Clean separation: Registry, Execution, Events, Permissions

Migration from legacy:
- tool_dispatcher_core.py → Merged into UnifiedToolDispatcher
- tool_dispatcher_unified.py → Refactored as netra_backend.app.core.tools.unified_tool_dispatcher
- admin_tool_dispatcher/* (24 files) → netra_backend.app.admin.tools.unified_admin_dispatcher
- request_scoped patterns → Built into factory

USAGE:
- NEW CODE: Use UnifiedToolDispatcherFactory.create_for_request()
- LEGACY: Backward compatibility maintained with deprecation warnings
"""

import warnings
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager

from langchain_core.tools import BaseTool

# Import from new consolidated location
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy,
    create_request_scoped_dispatcher,
)

# Import core tool models (SSOT for tool execution results)
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool

# Import production tool support
try:
    from netra_backend.app.agents.production_tool import ProductionTool, ToolExecuteResponse
except ImportError:
    # Production tool may not be available in all environments
    ProductionTool = None
    ToolExecuteResponse = None

# Backward compatibility alias
ToolDispatcher = UnifiedToolDispatcher

# Factory methods for different usage patterns
def create_tool_dispatcher(
    tools: List[BaseTool] = None,
    websocket_bridge = None,
    permission_service = None
) -> UnifiedToolDispatcher:
    """Create legacy global tool dispatcher (DEPRECATED).
    
    WARNING: This creates a global dispatcher that may cause isolation issues.
    Use UnifiedToolDispatcherFactory.create_for_request() for new code.
    
    Args:
        tools: List of tools to register initially
        websocket_bridge: Legacy WebSocket bridge (DEPRECATED)
        permission_service: Permission service for security
        
    Returns:
        UnifiedToolDispatcher: Global dispatcher instance (with warnings)
    """
    warnings.warn(
        "create_tool_dispatcher() creates global state and may cause isolation issues. "
        "Use UnifiedToolDispatcherFactory.create_for_request() for new code.",
        DeprecationWarning,
        stacklevel=2
    )
    return UnifiedToolDispatcherFactory.create_legacy_global(tools)

def create_request_scoped_tool_dispatcher(
    user_context: 'UserExecutionContext',
    websocket_manager: Optional['WebSocketManager'] = None,
    tools: Optional[List[BaseTool]] = None
) -> UnifiedToolDispatcher:
    """Create a request-scoped tool dispatcher (RECOMMENDED).
    
    Args:
        user_context: User execution context for isolation
        websocket_manager: WebSocket manager for events
        tools: Initial tools to register
        
    Returns:
        Request-scoped UnifiedToolDispatcher
    """
    return UnifiedToolDispatcherFactory.create_for_request(
        user_context=user_context,
        websocket_manager=websocket_manager,
        tools=tools
    )

# Export public interfaces with clear migration path
__all__ = [
    # Backward compatibility (shows warnings for legacy usage)
    "ToolDispatcher", 
    "create_tool_dispatcher",
    
    # Modern unified implementation (RECOMMENDED)
    "UnifiedToolDispatcher",
    "UnifiedToolDispatcherFactory", 
    "create_request_scoped_tool_dispatcher",
    "create_request_scoped_dispatcher",
    
    # Models and types
    "ToolDispatchRequest", 
    "ToolDispatchResponse",
    "DispatchStrategy",
    "ToolExecutionResult",
    "UnifiedTool",
]

# Add production tool exports if available
if ProductionTool is not None:
    __all__.extend(["ProductionTool", "ToolExecuteResponse"])

# Migration guidance notice
def _emit_migration_notice():
    """Emit informational notice about successful migration."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        "✅ Tool dispatcher consolidation complete. "
        "Using netra_backend.app.core.tools.unified_tool_dispatcher as SSOT. "
        "Admin tools in netra_backend.app.admin.tools.unified_admin_dispatcher. "
        "Legacy patterns emit deprecation warnings."
    )

# Emit migration notice on module import
_emit_migration_notice()